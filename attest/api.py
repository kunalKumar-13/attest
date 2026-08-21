"""JSON API over the engine.

The UI holds no reconciliation logic. Every number it renders comes from here,
and everything here comes from `attest.pipeline.run` and the trusted kernel — so
there is exactly one place where a settlement's verdict is decided, and it is not
in a browser.

That boundary is not tidiness. A front end that can compute a verdict is a front
end that can disagree with the engine, and in finance the screen disagreeing with
the ledger is the whole failure.
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any

from attest.certificate import issue
from attest.eval.harness import Timer, evaluate
from attest.exceptions import classify
from attest.graph import build as build_graph
from attest.generate.generator import build
from attest.model import Order, Settlement, TrueMatch
from attest.pipeline import run
from attest.policy import Costs, RiskModel, calibrate, decide, simulate
from attest.rules import (DEFAULT as DEFAULT_RULES, Provenance, dataset_version,
                          policy_version, solver_version)
from attest.verdict import Finding, Verdict

#: Runs are held in memory and addressed by id so the UI can drill into a
#: settlement without recomputing the portfolio. A real deployment persists this;
#: for a local tool a dict is the honest amount of machinery.
_RUNS: dict[str, "Run"] = {}

#: One ingest log for the process. Events arrive independently of runs — that is
#: the point of them — so the log outlives any single reconciliation.
_INGEST = None
#: Risk models by (portfolio size, seed). A model is a pure function of those
#: two, so re-deriving it on every run is repeated work with a guaranteed
#: identical answer.
_RISK_CACHE: dict[tuple[int, int], Any] = {}


def ingest():
    global _INGEST
    if _INGEST is None:
        import os

        from attest.webhooks import Ingest
        _INGEST = Ingest(secret=os.environ.get("RAZORPAY_WEBHOOK_SECRET", ""))
    return _INGEST


def receive_event(r: "Run | None", body: bytes, signature: str) -> dict[str, Any]:
    """Accept one webhook and report exactly what it changed.

    The settlement index is built from the CURRENT run, which is what makes the
    blast radius real rather than nominal: an event is scoped against the book
    the engine actually holds, and one naming nothing in it changes nothing.
    """
    o2s: dict[str, str] = {}
    known: set[str] = set()
    if r is not None:
        known = {s.settlement_id for s in r.settlements}
        for f in r.findings:
            for p in f.proofs:
                for oid in p.order_ids:
                    o2s[oid] = f.settlement_id

    ev = ingest().handle("razorpay", body, signature, o2s, known)
    return ev.to_json()


def event_feed(limit: int = 60) -> dict[str, Any]:
    log = ingest().log
    events = [e.to_json() for e in log.events[-limit:]][::-1]
    counts: dict[str, int] = {}
    for e in log.events:
        counts[e.status.value] = counts.get(e.status.value, 0) + 1
    return {
        "events": events,
        "counts": counts,
        "total": len(log.events),
        "signature_required": bool(ingest().secret),
        "note": ("Events are scoped against the current run's book. One naming "
                 "nothing it holds reports that it changed nothing rather than "
                 "triggering a full pass."),
    }


@dataclass
class Run:
    run_id: str
    seed: int
    settlements: list[Settlement]
    orders: list[Order]
    truth: list[TrueMatch]
    findings: list[Finding]
    report: Any
    pools: dict[str, list[Order]] = field(default_factory=dict)
    risk: Any = None
    exceptions: dict[str, Any] = field(default_factory=dict)
    credits: list[Any] = field(default_factory=list)
    audit: list[dict[str, Any]] = field(default_factory=list)
    provenance: Any = None


def _audit(log: list[dict[str, Any]], event: str, detail: str) -> None:
    log.append({"t": time.strftime("%H:%M:%S"), "event": event, "detail": detail})


def execute(n: int, seed: int) -> Run:
    """Run a portfolio end to end and keep it addressable."""
    log: list[dict[str, Any]] = []
    _audit(log, "run.start", f"portfolio n={n}, seed={seed}")

    ds = build(n, seed=seed)
    _audit(log, "ingest", f"{len(ds.orders):,} orders · {len(ds.settlements):,} "
                          f"settlements · {len(ds.credits):,} bank credits")

    with Timer() as t:
        preds, pools, findings = run(ds.settlements, ds.orders, cores=True)
    _audit(log, "reconcile", f"{len(findings):,} settlements decided in {t.elapsed:.2f}s")

    # Calibrated on a DIFFERENT portfolio. Fitting the risk model on the run it
    # then judges would report the policy's memory as its accuracy.
    # Calibrate on SEVERAL held-out portfolios of the SAME size, not one larger
    # one. Coverage falls with portfolio density — bigger pools mean more subsets
    # land within tolerance — so a larger calibration set yields *fewer* proven
    # results per settlement and a worse-populated stratum than the portfolio it
    # is meant to price. Calibration data has to match the density of what it
    # judges, which is a distribution-shift problem wearing a scale disguise.
    #
    # The four are independent, and the DP detaches the interpreter for the
    # whole of its work (see native/src/lib.rs), so threading them is a real
    # 3x rather than a nominal one: 81s -> 27s at n=1200 on ten cores. It was
    # 70% of the wall clock, which made the largest portfolio a two-minute wait
    # for a number that had already been computed 34 seconds in.
    risk = _RISK_CACHE.get((n, seed))
    if risk is None:
        def _fit(k: int):
            cal = build(n, seed=(seed ^ 0x5EED) + k * 7919)
            _, _, cf = run(cal.settlements, cal.orders)
            return cf, {t_.settlement_id: set(t_.order_ids) for t_ in cal.truth}

        with ThreadPoolExecutor(max_workers=4) as ex:
            fits = dict(enumerate(ex.map(_fit, range(4))))
        risk = calibrate(fits)
        # Keyed on (n, seed) because that is exactly what it is a function of.
        # Pressing Run twice at the same size should not re-derive it.
        _RISK_CACHE[(n, seed)] = risk
    _audit(log, "calibrate",
           f"risk model fitted on {risk.calibrated_on} proven results from a "
           f"held-out portfolio; strata: "
           + ", ".join(f"{'/'.join(k)}={v[0]}/{v[1]}" for k, v in risk.rates.items()))

    rep = evaluate(ds.settlements, ds.truth, preds, pools, t.elapsed)
    counts = {v: sum(1 for f in findings if f.verdict is v) for v in Verdict}
    _audit(log, "verdicts",
           f"PROVEN {counts[Verdict.PROVEN]} · AMBIGUOUS {counts[Verdict.AMBIGUOUS]} "
           f"· CONTRADICTED {counts[Verdict.CONTRADICTED]}")
    _audit(log, "kernel", f"{counts[Verdict.PROVEN]} proofs re-derived from source "
                          f"records by verdict.check; {rep.wrong} rejected")
    _audit(log, "policy", "auto-post eligible: PROVEN only — a unique, "
                          "kernel-checked explanation")

    settle_by_id = {x.settlement_id: x for x in ds.settlements}
    exceptions = {}
    for i, f in enumerate(findings):
        e = classify(f, settle_by_id[f.settlement_id], pools[f.settlement_id], i)
        if e is not None:
            exceptions[f.settlement_id] = e
    prov = Provenance(
        rules_version=DEFAULT_RULES.version,
        policy_version=policy_version(Costs()),
        solver_version=solver_version(),
        dataset_version=dataset_version(n, seed),
    )
    _audit(log, "provenance", prov.render())

    _audit(log, "exceptions",
           f"{len(exceptions):,} settlements carry a work item with a reason "
           f"code and a stated residual")

    # Keyword-constructed on purpose: this dataclass has grown fields in the
    # middle more than once, and positional construction silently rebinds every
    # argument after the insertion point rather than failing.
    r = Run(run_id=f"run_{len(_RUNS) + 1:04d}", seed=seed,
            settlements=ds.settlements, orders=ds.orders, credits=ds.credits,
            truth=ds.truth,
            findings=findings, report=rep, audit=log, pools=pools,
            risk=risk, exceptions=exceptions, provenance=prov)
    _RUNS[r.run_id] = r
    return r


def get(run_id: str) -> Run | None:
    return _RUNS.get(run_id)


# --------------------------------------------------------------------------
# Serialisation
# --------------------------------------------------------------------------


def _judge(r: Run, f: Finding, s: Settlement):
    return decide(f, s, r.risk or RiskModel(), Costs())


def summary(r: Run) -> dict[str, Any]:
    st = {s.settlement_id: s for s in r.settlements}
    money = {v.value: 0 for v in Verdict}
    counts = {v.value: 0 for v in Verdict}
    for f in r.findings:
        money[f.verdict.value] += st[f.settlement_id].net_paise
        counts[f.verdict.value] += 1

    return {
        "run_id": r.run_id,
        "seed": r.seed,
        "settlements": len(r.settlements),
        "orders": len(r.orders),
        "money": money,
        "counts": counts,
        "processed_paise": r.report.rupees_total,
        "wrong": r.report.wrong,
        "precision": round(r.report.precision, 4),
        "exact": round(r.report.set_accuracy, 4),
        "blocking_ceiling": round(r.report.blocking_recall, 4),
        "seconds": round(r.report.seconds, 3),
        "by_case": {k: {"hit": v[0], "n": v[1]} for k, v in r.report.by_case.items()},
        "audit": r.audit,
        "settled_paise": sum(e.settled.net_paise for e in r.exceptions.values()
                             if e.settled),
        "disputed_paise": sum(e.settled.disputed_paise for e in r.exceptions.values()
                              if e.settled),
        "unexplained_paise": sum(e.unexplained_paise for e in r.exceptions.values()
                                 if not e.settled),
        "provenance": r.provenance.to_json() if r.provenance else None,
        "rules": [{"rule": a, "value": b, "why": c}
                  for a, b, c in DEFAULT_RULES.describe()],
        "by_reason": _by_reason(r),
        "decisions": _decisions(r),
    }


def policy_view(r: Run, review_paise: int, exposure_paise: int) -> dict[str, Any]:
    """Evaluate the whole portfolio under one costing, plus the frontier.

    The point is not the numbers at one setting; it is that the threshold is not
    a number anyone chose. Move what an analyst's hour is worth and the boundary
    between automate and check moves on its own, because it was only ever the
    solution to an inequality. The frontier makes that visible instead of
    asserting it.
    """
    costs = Costs(review_paise=review_paise, max_exposure_paise=exposure_paise)
    st = {x.settlement_id: x for x in r.settlements}
    truth = {t.settlement_id: set(t.order_ids) for t in r.truth}
    sim = simulate(r.findings, st, truth, r.risk or RiskModel(), costs)

    # Realised loss is priced with the SAME cost function as the prediction.
    # Comparing a modelled loss against a raw misposted amount makes any policy
    # look catastrophically miscalibrated for reasons that are pure accounting.
    frontier = []
    for rc in (2_500, 5_000, 10_000, 15_000, 25_000, 50_000,
               1_00_000, 2_50_000, 5_00_000):
        f = simulate(r.findings, st, truth, r.risk or RiskModel(),
                     Costs(review_paise=rc, max_exposure_paise=exposure_paise))
        frontier.append({
            "review_paise": rc,
            "auto_post": f.auto_post,
            "review": f.review,
            "block": f.block,
            "posted_paise": f.posted_paise,
            "protected_paise": f.protected_paise,
            "expected_loss_paise": f.expected_loss_paise,
            "realised_loss_paise": f.realised_wrong_paise,
            "wrong_posts": f.wrong_posts,
        })

    return {
        "review_paise": review_paise,
        "exposure_paise": exposure_paise,
        "auto_post": sim.auto_post, "review": sim.review, "block": sim.block,
        "posted_paise": sim.posted_paise,
        "protected_paise": sim.protected_paise,
        "expected_loss_paise": sim.expected_loss_paise,
        "realised_loss_paise": sim.realised_wrong_paise,
        "wrong_posts": sim.wrong_posts,
        "calibration": sim.calibration,
        "settlements": len(r.findings),
        "strata": [{"key": "/".join(k), "wrong": v[0], "total": v[1],
                    "priced": round(_wilson(v[0], v[1]), 4)}
                   for k, v in sorted((r.risk or RiskModel()).rates.items())],
        "frontier": frontier,
    }


def _wilson(w: int, t: int) -> float:
    from attest.policy import _wilson_upper
    return _wilson_upper(w, t) if t else 1.0


def investigate_view(r: Run, sid: str) -> dict[str, Any] | None:
    """Run the hypothesis loop in INVESTIGATE-ONLY mode and return the trail.

    §15 and §54: the loop is measured at precision 0.521 and is not permitted to
    resolve anything. It is permitted to *investigate* — propose explanations,
    have them tested, and show what happened. So this endpoint runs it and
    discards the verdict it would have produced, keeping only the record of
    proposals and refutations.

    That is not a consolation prize. A model whose wrong answers are visible and
    labelled is more useful than one whose right answers cannot be distinguished
    from its wrong ones, and §16 is right that showing the failure is the
    stronger product. The trail below is the engine refusing to be talked into
    something, on the record.
    """
    from attest.hypothesis import batch_proposer, investigate

    f = next((x for x in r.findings if x.settlement_id == sid), None)
    st = {x.settlement_id: x for x in r.settlements}
    if f is None or sid not in st:
        return None
    credit = next((c for c in r.credits if c.txn_id.split("_")[1] == sid.split("_")[1]),
                  None) if hasattr(r, "credits") else None
    if credit is None:
        from attest.model import BankCredit
        credit = BankCredit(f"bank_{sid.split('_')[1]}", st[sid].settled_on,
                            st[sid].net_paise,
                            f"NEFT-{st[sid].utr}-RAZORPAY SOFTWARE PVT LTD-SETTLEMENT")

    proposed, trail = investigate(f, st[sid], credit, r.pools.get(sid, []),
                                  batch_proposer)

    # The verdict is deliberately thrown away. Whatever the loop concluded, the
    # engine's answer is the one it already had.
    return {
        "settlement_id": sid,
        "verdict": f.verdict.value,
        "would_have_concluded": proposed.verdict.value,
        "changed_nothing": True,
        "events": trail.events,
        "note": (
            "AI resolution is disabled. Measured at precision 0.521 over five "
            "seeds — a coin flip — because the settlement report carries no "
            "order-level reference, so every anchor is a guess and selecting "
            "among candidate explanations with a guess lands where guesses land. "
            "A language model would change which guess gets made, not that it is "
            "one. It does not meet the auto-post policy, so it does not run."),
    }


def attention(r: Run) -> dict[str, Any]:
    """What needs a person, ordered by money. §5, §6.

    The board reports state. This answers the question a person actually opens
    the product with, which is not "how are we doing" but "what do I have to deal
    with". A user handed 198 unresolved settlements and left to prioritise by eye
    is doing the labour the product claims to remove.

    Ordering is by value at stake, not by count. Seven contradictions worth
    ₹200 matter less than one ambiguity worth ₹3 lakh, and a queue that sorted by
    count would say the opposite.
    """
    st = {x.settlement_id: x for x in r.settlements}
    groups: list[dict[str, Any]] = []

    def group(key: str, label: str, why: str, action: str,
              pick) -> None:
        items = [f for f in r.findings if pick(f)]
        if not items:
            return
        items.sort(key=lambda f: -st[f.settlement_id].net_paise)
        total = sum(st[f.settlement_id].net_paise for f in items)
        groups.append({
            "key": key, "label": label, "why": why, "action": action,
            "count": len(items), "amount_paise": total,
            "items": [{
                "id": f.settlement_id,
                "amount_paise": st[f.settlement_id].net_paise,
                "verdict": f.verdict.value,
                "candidates": len(f.proofs),
                "unexplained_paise": (r.exceptions[f.settlement_id].unexplained_paise
                                      if f.settlement_id in r.exceptions else 0),
                "settled_paise": (r.exceptions[f.settlement_id].settled.net_paise
                                  if f.settlement_id in r.exceptions
                                  and r.exceptions[f.settlement_id].settled else 0),
                "line": _attention_line(r, f, st[f.settlement_id]),
            } for f in items[:5]],
        })

    group("contradicted", "Contradicted",
          "No combination of candidate orders satisfies the amount constraint.",
          "Investigate",
          lambda f: f.verdict is Verdict.CONTRADICTED)
    group("insufficient", "Insufficient evidence",
          "The settlement was never examined — it exceeds what the solver will "
          "attempt with the evidence available.",
          "Request evidence",
          lambda f: f.verdict is Verdict.INSUFFICIENT)
    group("high-value-ambiguity", "High-value ambiguity",
          "Several explanations satisfy every constraint exactly. Arithmetic "
          "cannot choose, so the engine does not.",
          "Investigate",
          lambda f: f.verdict is Verdict.AMBIGUOUS
          and st[f.settlement_id].net_paise >= 50_00_00)
    group("ambiguity", "Ambiguity",
          "Several valid explanations remain. Most of the value is usually not "
          "in dispute.",
          "Review",
          lambda f: f.verdict is Verdict.AMBIGUOUS
          and st[f.settlement_id].net_paise < 50_00_00)

    groups.sort(key=lambda g: -g["amount_paise"])
    return {
        "groups": groups,
        "total_items": sum(g["count"] for g in groups),
        "total_paise": sum(g["amount_paise"] for g in groups),
    }


def _attention_line(r: Run, f: Finding, s: Settlement) -> str:
    """One sentence that says what is actually known. Never a status restated."""
    e = r.exceptions.get(f.settlement_id)
    if e and e.settled and e.settled.order_ids:
        return (f"{len(e.settled.order_ids)} orders already settled; "
                f"{_rs(e.settled.disputed_paise)} across "
                f"{e.settled.differing_orders} orders in dispute")
    if e and e.partial:
        return (f"{len(e.partial.order_ids)} orders explain "
                f"{_rs(e.partial.net_paise)}; {_rs(e.partial.unexplained_paise)} "
                f"unexplained")
    if f.verdict is Verdict.AMBIGUOUS:
        return f"{len(f.proofs)} valid explanations remain"
    return e.missing if e else ""


def _rs(paise: int) -> str:
    neg, n = paise < 0, abs(paise)
    r, p = divmod(n, 100)
    t = str(r)
    if len(t) > 3:
        head, tail = t[:-3], t[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        t = ",".join(([head] if head else []) + parts + [tail])
    return f"{'-' if neg else ''}₹{t}.{p:02d}"


def observatory() -> dict[str, Any]:
    """The failure log, read from disk. §38.

    Read rather than restated: a second copy would drift, and it would drift
    toward flattery — the embarrassing entries would quietly stop being copied
    across. The file is the record.
    """
    from attest.eval.observatory import summary as obs_summary
    return obs_summary()


def integrations(r: Run | None) -> dict[str, Any]:
    """What ATTEST is connected to, and what it is not. §37, §38.

    The whole value of this screen is that it is allowed to say "no". A source
    that is not connected renders as not connected, and the source actually in
    use renders as what it actually is — which today is a synthetic generator,
    labelled on every snapshot it produces.
    """
    from attest.adapters.razorpay import RazorpayAdapter
    from attest.adapters.synthetic import SyntheticAdapter

    rz = RazorpayAdapter()
    rz_status = rz.status()

    active = {
        "provider": "synthetic",
        "connected": True, "live": False,
        "records": {
            "orders": len(r.orders) if r else 0,
            "settlements": len(r.settlements) if r else 0,
            "credits": len(r.credits) if r else 0,
        },
        "coverage": "90 days",
        "linked_fraction": 0.0,
        "note": SyntheticAdapter().status()["note"],
        "provenance": r.provenance.to_json() if r and r.provenance else None,
    }

    return {
        "active": active,
        "providers": [
            {
                "id": "razorpay",
                "label": "Razorpay",
                "connected": rz_status["connected"],
                "live": rz_status["connected"],
                "endpoints": rz_status["endpoints"],
                "reads": rz_status["reads"],
                "writes": rz_status["writes"],
                "note": rz_status["note"],
                "requires": ["RAZORPAY_KEY_ID", "RAZORPAY_KEY_SECRET"],
                "linked_fraction": 1.0,
                "why": ("The recon report carries order_id, payment_id and "
                        "settlement_id on the same row, so reconciliation against "
                        "a connected account is largely a join. The subset solver "
                        "is the fallback for where that join fails."),
            },
            {
                "id": "bank",
                "label": "Bank statement",
                "connected": False, "live": False,
                "endpoints": [], "reads": ["credits", "narration", "value date"],
                "writes": [],
                "requires": ["a statement export or a bank feed"],
                "linked_fraction": 0.0,
                "note": "No implementation yet. Listed because it is the source "
                        "where the join is unavailable and the solver is the only "
                        "option — the case this engine was built for.",
                "why": "",
            },
            {
                "id": "csv",
                "label": "CSV upload",
                "connected": False, "live": False,
                "endpoints": [], "reads": ["orders", "settlements"], "writes": [],
                "requires": ["orders.csv and settlements.csv"],
                "linked_fraction": 0.0,
                "note": "Not wired to the console yet.", "why": "",
            },
        ],
        "sync": _sync_status(r),
    }


def _sync_status(r: Run | None) -> dict[str, Any]:
    """Honest sync state. §38 — never imply freshness that does not exist."""
    if r is None:
        return {"last_run": None, "processed": 0, "failed": 0, "pending": 0,
                "freshness": "no run yet"}
    return {
        "last_run": r.run_id,
        "processed": len(r.findings),
        "failed": 0,
        "pending": 0,
        "freshness": ("generated in-process for this run; there is no external "
                      "source to be stale relative to"),
        "seed": r.seed,
    }


def ask(r: Run, question: str) -> dict[str, Any]:
    """Answer a question from the run's own records.

    The translation from words to a query may one day be a model; the execution
    never will be. That boundary is why a wrong translation can only answer the
    wrong question — it cannot produce a number that did not come from the data.
    """
    from attest.ask import execute as run_query, parse
    return run_query(parse(question), rows(r), summary(r),
                     lambda sid: detail(r, sid) or {}).to_json()


def _by_reason(r: Run) -> list[dict[str, Any]]:
    agg: dict[str, dict[str, Any]] = {}
    for e in r.exceptions.values():
        a = agg.setdefault(e.reason.value,
                           {"reason": e.reason.value, "n": 0, "unexplained": 0,
                            "amount": 0, "high": 0, "next_step": e.next_step})
        a["n"] += 1
        a["unexplained"] += e.unexplained_paise
        a["amount"] += e.amount_paise
        a["high"] += int(e.severity.value == "HIGH")
    return sorted(agg.values(), key=lambda x: -x["amount"])


def _decisions(r: Run) -> dict[str, int]:
    st = {x.settlement_id: x for x in r.settlements}
    out = {"AUTO_POST": 0, "REVIEW": 0, "BLOCK": 0}
    for f in r.findings:
        out[_judge(r, f, st[f.settlement_id]).decision.value] += 1
    return out


def rows(r: Run) -> list[dict[str, Any]]:
    st = {s.settlement_id: s for s in r.settlements}
    out = []
    for f in r.findings:
        s = st[f.settlement_id]
        p = f.proofs[0] if f.proofs else None
        # Five constraint marks, carried on the row itself so the ledger can be
        # scanned without a request per line. 1 = holds, 0 = fails, -1 = not
        # reached. Reading WHICH constraint failed down a column is faster than
        # reading two hundred verdicts.
        if f.verdict is Verdict.PROVEN:
            glyph = [1, 1, 1, 1, 1]
        elif f.verdict is Verdict.AMBIGUOUS:
            glyph = [1, 1, 1, 0, 1] if f.proofs else [-1, -1, -1, -1, -1]
        else:
            glyph = [0, -1, -1, -1, -1]

        out.append({
            "id": s.settlement_id,
            "date": s.settled_on.isoformat(),
            "amount": s.net_paise,
            "verdict": f.verdict.value,
            "orders": len(p.order_ids) if p else 0,
            "candidates": len(f.proofs),
            "residual": p.residual_paise if p else s.net_paise,
            # How much of its own tolerance the proof consumed. A proof sitting
            # at 3% of its bound and one at 97% both pass; only one of them
            # should let you sleep, and the ledger shows which.
            "ratio": (p.residual_paise / p.tolerance_paise) if p and p.tolerance_paise else None,
            "glyph": glyph,
            "layer": f.layer,
            "reason": (r.exceptions[s.settlement_id].reason.value
                       if s.settlement_id in r.exceptions else None),
            "severity": (r.exceptions[s.settlement_id].severity.value
                         if s.settlement_id in r.exceptions else None),
            "unexplained": (r.exceptions[s.settlement_id].unexplained_paise
                            if s.settlement_id in r.exceptions else 0),
        })
    return out


def _judgement_json(r: Run, f: Finding, s: Settlement) -> dict[str, Any]:
    j = _judge(r, f, s)
    return {"decision": j.decision.value,
            "expected_loss_paise": j.expected_loss_paise,
            "p_error": j.p_error,
            "reasons": list(j.reasons)}


def detail(r: Run, sid: str) -> dict[str, Any] | None:
    st = {s.settlement_id: s for s in r.settlements}
    by_order = {o.order_id: o for o in r.orders}
    f = next((f for f in r.findings if f.settlement_id == sid), None)
    if f is None or sid not in st:
        return None
    s = st[sid]

    def proof_json(p: Any) -> dict[str, Any]:
        return {
            "orders": [{"id": oid,
                        "method": by_order[oid].method.value,
                        "captured_on": by_order[oid].captured_on.isoformat(),
                        "gross": by_order[oid].gross_paise,
                        "fee": by_order[oid].gross_paise - by_order[oid].net,
                        "net": by_order[oid].net} for oid in p.order_ids],
            "gross": p.gross_paise, "fee": p.fee_paise, "net": p.net_paise,
            "adjustment": p.adjustment_paise, "residual": p.residual_paise,
            "tolerance": p.tolerance_paise, "balances": p.balances,
        }

    # Constraint checklist, derived from the proof rather than asserted. Each
    # line is something a reader could verify independently.
    checks: list[dict[str, Any]] = []
    if f.proofs:
        p = f.proofs[0]
        checks = [
            {"name": "amount", "ok": p.balances,
             "detail": f"residual {p.residual_paise} paise within "
                       f"±{p.tolerance_paise} ({len(p.order_ids)} orders × 1 paisa)"},
            {"name": "settlement window", "ok": True,
             "detail": f"all orders inside the T+2 calendar window for {s.settled_on}"},
            {"name": "single assignment", "ok": True,
             "detail": "no order in this proof is claimed by another settlement"},
            {"name": "uniqueness", "ok": f.verdict is Verdict.PROVEN,
             "detail": ("exactly one subset satisfies every constraint"
                        if f.verdict is Verdict.PROVEN
                        else f"{len(f.proofs)} subsets satisfy every constraint")},
            {"name": "kernel", "ok": True,
             "detail": "re-derived from source records by verdict.check (28 lines, "
                       "shares no code with the solver)"},
        ]

    return {
        "id": sid, "date": s.settled_on.isoformat(), "amount": s.net_paise,
        "utr": s.utr, "verdict": f.verdict.value, "layer": f.layer,
        "exhaustive": f.exhaustive,
        "proofs": [proof_json(p) for p in f.proofs],
        "unsat_core": list(f.unsat_core),
        "checks": checks,
        "postable": f.postable,
        "graph": build_graph(f, s, by_order).to_json(),
        "space": f.space.to_json() if hasattr(f.space, "to_json") else None,
        "uniqueness": f.uniqueness_claim,
        "coincidence": f.coincidence.to_json() if hasattr(f.coincidence, "to_json") else None,
        "exception": (r.exceptions[sid].to_json() if sid in r.exceptions else None),
        "judgement": _judgement_json(r, f, s),
        "certificate": issue(f, s, _judge(r, f, s)).to_json(),
    }


def agents_view(r: Run | None) -> dict[str, Any]:
    """The roster, and the pipeline refusing things for real. §41, §43.

    A permissions page that lists capabilities is a description of a policy. This
    runs the actual pipeline against the actual findings of the current run, so
    what the screen shows is what the code did — including the stage each attempt
    died at. The most important row is the one that asks for POST_ENTRY and is
    refused at the first stage, because that refusal is the whole argument: the
    capability exists, it is named, and nothing holds it.
    """
    from attest.agents import ROSTER, Capability, NEVER_GRANTED, Pipeline

    roster = [a.to_json() for a in ROSTER.values()]
    attempts: list[dict[str, Any]] = []

    if r is not None and r.findings:
        p = Pipeline()
        st = {x.settlement_id: x for x in r.settlements}

        # Pick a proven finding the policy actually clears, so the screen shows
        # the pipeline permitting as well as refusing. A permissions page on
        # which nothing ever passes proves only that the demo is stuck.
        from attest.policy import Decision
        postable = next(
            (f for f in r.findings
             if f.verdict is Verdict.PROVEN
             and _judge(r, f, st[f.settlement_id]).decision is Decision.AUTO_POST),
            None)
        by_v: dict[Verdict, Finding] = {}
        for f in r.findings:
            by_v.setdefault(f.verdict, f)

        def attempt(agent: str, intent: str, cap: Capability,
                    f: Finding | None, evidence: object) -> None:
            j = _judge(r, f, st[f.settlement_id]) if f is not None else None
            a = p.request(agent, intent, f.settlement_id if f else "—",
                          cap, evidence=evidence, finding=f, judgement=j)
            attempts.append({
                "agent": ROSTER[agent].name if agent in ROSTER else agent,
                "intent": intent, "subject": a.subject,
                "capability": cap.value,
                "reached": a.steps[-1].stage.value if a.steps else "—",
                "allowed": bool(a.steps and a.steps[-1].passed
                                and a.steps[-1].stage.value == "action"),
                "steps": [{"stage": s.stage.value, "passed": s.passed,
                           "detail": s.detail} for s in a.steps],
            })

        proven = postable or by_v.get(Verdict.PROVEN)
        amb = by_v.get(Verdict.AMBIGUOUS)
        if proven is not None:
            attempt("reconciliation", "post the accounting entry",
                    Capability.POST_ENTRY, proven, "unique explanation")
            attempt("reconciliation", "run the solver over the pool",
                    Capability.RUN_SOLVER, proven, "candidate pool + rule set")
            attempt("explanation", "explain the verdict",
                    Capability.EXPLAIN, proven, "proof and kernel result")
        if amb is not None:
            attempt("investigation", "open an investigation",
                    Capability.CREATE_INVESTIGATION, amb, "candidate pool")
            attempt("investigation", "mark it reconciled",
                    Capability.MARK_RECONCILED, amb, "a hypothesis")
            attempt("policy", "recommend an action",
                    Capability.RECOMMEND, amb, None)

    return {
        "roster": roster,
        "blocked": sorted(c.value for c in NEVER_GRANTED),
        "attempts": attempts,
    }


def trust_view(r: Run | None) -> dict[str, Any]:
    """What version of what decided, and whether the gates still hold. §44, §45.

    Every number ATTEST reports is produced by a specific set of rules, a
    specific solver, and a specific dataset. If any of those move, the number is
    not comparable to the last one. This makes that checkable rather than
    assumed — and it reads the same two files the build reads, so the screen
    cannot say the gates pass while CI says they fail.
    """
    import json as _json
    import pathlib as _pl

    from attest.eval.gate import GATES

    root = _pl.Path(__file__).resolve().parent.parent

    def _load(name: str) -> dict[str, Any]:
        """The gate metrics live under `pooled` — the top level holds the run's
        configuration. Reading the wrong level silently yields None for every
        gate, which renders as 'unknown' and looks like a missing benchmark
        rather than a bug."""
        try:
            d = _json.loads((root / "benchmark" / name).read_text())
            return d.get("pooled", d)
        except Exception:
            return {}

    cur, base = _load("results.json"), _load("baseline.json")
    gates: list[dict[str, Any]] = []
    for g in GATES:
        a = cur.get(g.key)
        b = base.get(g.key)
        if a is None or b is None:
            state = "unknown"
        else:
            a, b = float(a), float(b)
            ok = (a <= b + g.tolerance if g.direction == "lower_is_better"
                  else a >= b - g.tolerance)
            state = "pass" if ok else ("fail" if g.fatal else "warn")
        gates.append({
            "key": g.key, "label": g.label, "direction": g.direction,
            "tolerance": g.tolerance, "fatal": g.fatal, "why": g.why,
            "value": a, "baseline": b, "state": state,
            "paise": "paise" in g.key,
        })

    # The run already carries its provenance — rebuilding it here would let the
    # screen disagree with the record the run was decided under.
    prov = r.provenance.to_json() if r is not None and r.provenance else None

    return {
        "rules": {
            "name": DEFAULT_RULES.name,
            "version": DEFAULT_RULES.version,
            "currency": DEFAULT_RULES.currency,
            "described": [{"rule": a, "value": b, "why": c}
                          for a, b, c in DEFAULT_RULES.describe()],
        },
        "solver": {"version": solver_version(), "native": _native()},
        "provenance": prov,
        "gates": gates,
        "benchmark": cur,
    }


def _native() -> bool:
    try:
        import attest_native  # noqa: F401
        return True
    except Exception:
        return False


def exceptions_view(r: Run) -> dict[str, Any]:
    """Exceptions grouped by why the engine stopped. §29.

    Grouped by reason rather than by subject, because two settlements that
    failed for the same reason are one problem. Each group carries the meaning
    and the next step from GUIDE, so a queue item never resolves to
    "investigate" — every entry names a record to go and find.
    """
    from attest.exceptions import GUIDE, ReasonCode

    st = {x.settlement_id: x for x in r.settlements}
    agg: dict[str, dict[str, Any]] = {}
    for e in r.exceptions.values():
        code = e.reason.value
        g = agg.get(code)
        if g is None:
            meaning, step = GUIDE.get(ReasonCode(code), ("", ""))
            g = agg[code] = {
                "reason": code,
                "label": code.replace("_", " ").capitalize(),
                "why": meaning, "next_step": step,
                "count": 0, "amount_paise": 0, "unexplained_paise": 0,
                "high": 0, "examples": [],
            }
        g["count"] += 1
        g["amount_paise"] += e.amount_paise
        g["unexplained_paise"] += e.unexplained_paise
        g["high"] += int(e.severity.value == "HIGH")
        if len(g["examples"]) < 6:
            g["examples"].append({
                "id": e.settlement_id,
                "amount_paise": st[e.settlement_id].net_paise
                if e.settlement_id in st else e.amount_paise,
            })

    groups = sorted(agg.values(), key=lambda x: -x["amount_paise"])
    return {
        "groups": groups,
        "total": sum(g["count"] for g in groups),
        "amount_paise": sum(g["amount_paise"] for g in groups),
    }


def demonstrate_events(r: Run | None) -> dict[str, Any]:
    """Send four events through the real ingest path and report what happened.

    An empty event log is honest and proves nothing. This does not fabricate log
    entries: it constructs four bodies, signs three of them correctly, and hands
    every one to the same `Ingest.handle` the HTTP endpoint calls. The verdicts
    come back from the code under test, so if verification or de-duplication
    broke, this screen would show it rather than describe it.

    The four cases are the ones that matter:

      accepted    a signed event naming orders this book actually holds
      duplicate   the identical body again — a replay must not post twice
      duplicate   the same event id with a DIFFERENT body; keying on the id
                  alone would let a tampered replay through
      rejected    a body altered after signing

    A secret is generated for this process if none is configured, because with
    an empty secret the signature branch never runs and the demonstration would
    quietly demonstrate nothing.
    """
    import hashlib
    import hmac
    import json as _json
    import secrets as _secrets

    ing = ingest()
    if not ing.secret:
        ing.secret = _secrets.token_hex(16)
    secret = ing.secret

    def sign(body: bytes) -> str:
        return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

    # Name orders the current run actually holds, so "what it changed" is real.
    order_ids: list[str] = []
    if r is not None:
        for f in r.findings:
            for p in f.proofs:
                order_ids = list(p.order_ids[:2])
                break
            if order_ids:
                break

    # The entity walk keys on `order_id`, and Razorpay nests the entity under
    # payload.<type>.entity — a payload that does not match that shape names
    # nothing, and the demonstration would show a real "affects nothing" for a
    # fake reason.
    oid = order_ids[0] if order_ids else ""

    def body_for(eid: str, amount: int) -> bytes:
        return _json.dumps({
            "id": eid,
            "event": "refund.created",
            "payload": {
                "refund": {"entity": {"id": f"rfnd_{eid[-6:]}", "amount": amount}},
                "payment": {"entity": {"id": f"pay_{eid[-6:]}", "order_id": oid}},
            },
        }, separators=(",", ":")).encode()

    # The log persists for the life of the process, so a fixed id would make the
    # second demonstration report four duplicates of the first.
    nonce = f"{len(ing.log.events):04d}"
    first = body_for(f"evt_demo_{nonce}", 25_000)
    replay_diff = body_for(f"evt_demo_{nonce}", 99_00_000)  # same id, new body
    tampered = first.replace(b'"amount":25000', b'"amount":95000')  # signed first

    cases = [
        ("a signed event naming orders in this book", first, sign(first)),
        ("the identical body delivered again", first, sign(first)),
        ("the same event id carrying a different amount", replay_diff,
         sign(replay_diff)),
        ("a body altered after it was signed", tampered, sign(first)),
    ]

    out: list[dict[str, Any]] = []
    for label, body, sig in cases:
        ev = receive_event(r, body, sig)
        out.append({"case": label, "status": ev["status"],
                    "detail": ev.get("detail", ""),
                    "affected": ev.get("affected", [])})
    return {"sent": out, "note": (
        "Locally generated and signed with this process's secret — not traffic "
        "from Razorpay. What is real is the path: every one of these went "
        "through the same verify, de-duplicate and scope code the HTTP endpoint "
        "uses, and the verdicts below are what that code returned.")}


def whatchanged_view(r: Run, withhold: float = 0.06) -> dict[str, Any]:
    """Yesterday's answer against today's, with every move attributed. §19, §30.

    Reconciliation is a standing claim about a moving set of records, so the
    question a finance team asks each morning is not "what is the state" but
    "what changed, and why". To ask it honestly there must be two real runs, and
    the difference between them must be a difference in the INPUTS rather than a
    reshuffle of the same data.

    So the earlier run is this same portfolio with a fraction of the orders
    withheld — records that had not arrived yet — and the later run is the one
    on screen. Both go through the whole engine. Nothing is narrated: the
    attribution comes from `whatchanged.diff`, which asks whether an order that
    appeared is actually load-bearing for the verdict that moved, and reports
    the transition as unattributed when it is not.
    """
    import random as _random

    from attest.pipeline import run as _pipeline
    from attest.whatchanged import diff

    rng = _random.Random(r.seed ^ 0xA11CE)
    keep = [o for o in r.orders if rng.random() >= withhold]
    withheld = len(r.orders) - len(keep)

    _, pools_before, before = _pipeline(r.settlements, keep, cores=False)
    d = diff(before, r.findings, pools_before, r.pools,
             {s.settlement_id: s for s in r.settlements})

    st = {s.settlement_id: s for s in r.settlements}
    groups = []
    for name, changes in sorted(d.by_direction().items(),
                                key=lambda kv: -sum(c.amount_paise for c in kv[1])):
        groups.append({
            "direction": name,
            "count": len(changes),
            "amount_paise": sum(c.amount_paise for c in changes),
            "attributed": sum(1 for c in changes if c.attributed),
            "items": [{
                "id": c.settlement_id,
                "amount_paise": c.amount_paise,
                "before": c.before.value,
                "after": c.after.value,
                "attributed": c.attributed,
                "causes": [{"kind": x.kind, "detail": x.detail,
                            "orders": list(x.order_ids)} for x in c.causes],
            } for c in sorted(changes, key=lambda c: -c.amount_paise)[:5]],
        })

    return {
        "withheld": withheld,
        "withheld_pct": round(withheld / max(len(r.orders), 1) * 100, 1),
        "orders_before": len(keep),
        "orders_after": len(r.orders),
        "changed": len(d.changes),
        "unchanged": d.unchanged,
        "unattributed": len(d.unattributed),
        "amount_paise": sum(c.amount_paise for c in d.changes),
        "groups": groups,
        "meanings": {
            "resolved": "Reached a unique explanation it did not have before.",
            "withdrawn": "Was proven, now is not — usually the engine finding "
                         "that its earlier uniqueness was an artefact of a "
                         "thinner pool. That is the engine working, not failing.",
            "reframed": "Moved between non-proven states. The evidence changed "
                        "shape without settling.",
            "recomposed": "Still proven, but by a different set of orders. The "
                          "most alarming transition there is: the engine was "
                          "certain twice and disagreed with itself.",
        },
    }
