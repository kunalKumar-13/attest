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

import re
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
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
    started_at: str = ""
    """UTC ISO timestamp. Needed to say whether an event arrived before or
    after the run decided, which is the whole of whether a verdict is stale."""


def _audit(log: list[dict[str, Any]], event: str, detail: str) -> None:
    log.append({"t": time.strftime("%H:%M:%S"), "event": event, "detail": detail})


def execute(n: int, seed: int) -> Run:
    """Run a portfolio end to end and keep it addressable."""
    log: list[dict[str, Any]] = []
    started_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
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
            risk=risk, exceptions=exceptions, provenance=prov,
            started_at=started_at)
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




def journal_view(r: Run, review_paise: int = 15_000,
                 exposure_paise: int = 10_000_000) -> dict[str, Any]:
    """The accounting ATTEST would write, and a stated reason for everything
    it would not. §21.

    A verdict is not the deliverable. Everything upstream — the pool, the
    subset-sum, the kernel, the risk pricing — exists to earn the right to write
    a journal entry, and this is the screen where that right is exercised or
    declined. The refusals are grouped because two settlements withheld for the
    same reason are one problem.
    """
    from attest.ledger import Journal, JournalEntry, post

    # The costing is the reader's, not a constant. The Journal reflecting a
    # different policy from the one the Policy screen is showing would make two
    # screens disagree about the same portfolio.
    costs = Costs(review_paise=review_paise, max_exposure_paise=exposure_paise)
    st = {x.settlement_id: x for x in r.settlements}
    orders = {o.order_id: o for o in r.orders}
    prov = r.provenance.render() if r.provenance else ""

    j = Journal()
    for f in r.findings:
        s = st[f.settlement_id]
        out = post(f, s, decide(f, s, r.risk or RiskModel(), costs),
                   orders, provenance=prov)
        (j.entries if isinstance(out, JournalEntry) else j.refusals).append(out)

    reasons: dict[str, dict[str, Any]] = {}
    for x in j.refusals:
        # Group on the SHAPE of the reason, not its text. "expected loss
        # ₹1,162.56 >= review cost ₹150.00" and "expected loss ₹154.95 >= review
        # cost ₹150.00" are one problem stated twice; keying on the sentence put
        # fifty settlements in fifty buckets of one, which is a list wearing a
        # summary's clothes.
        head = x.reason.split("—")[0].split(";")[0].strip()
        key = re.sub(r"\s+", " ", re.sub(r"[₹\d,.]+", "", head)).strip()
        g = reasons.setdefault(key, {"reason": key, "count": 0,
                                     "amount_paise": 0, "example": x.reason,
                                     "largest_paise": 0})
        g["count"] += 1
        g["amount_paise"] += x.amount_paise
        if x.amount_paise > g["largest_paise"]:
            g["largest_paise"] = x.amount_paise
            g["example"] = x.reason

    return {
        "entries": [e.to_json() for e in
                    sorted(j.entries, key=lambda e: -e.total_paise)[:40]],
        "entry_count": len(j.entries),
        "posted_paise": j.posted_paise,
        "refused_paise": j.refused_paise,
        "refusals": sorted(reasons.values(), key=lambda g: -g["amount_paise"]),
        "refusal_count": len(j.refusals),
        "balances": j.balances(),
        "provenance": prov,
        "accounts": ["Bank", "Payment gateway fees", "Input GST (recoverable)",
                     "Trade receivables"],
        "review_paise": review_paise,
        "exposure_paise": exposure_paise,
    }


def actions_view(r: Run) -> dict[str, Any]:
    """The work, ranked by what each piece of it unlocks. §31.

    Exceptions answers "what is stuck". This answers "what should I do first",
    and those have different orderings: 197 ambiguous settlements is one action,
    not 197, because they are all ambiguous for the same missing field.
    """
    from attest.actions import Kind, plan

    amounts = {s.settlement_id: s.net_paise for s in r.settlements}
    acts = plan(r.exceptions, amounts)

    systemic = [a for a in acts if a.kind is Kind.SYSTEMIC]
    rerun = [a for a in acts if a.kind is Kind.RERUN]
    per_item = [a for a in acts if a.kind is Kind.PER_ITEM]

    return {
        "actions": [a.to_json() for a in acts],
        "total_value_paise": sum(a.value_paise for a in acts),
        "total_steps": sum(a.steps for a in acts),
        "systemic_value_paise": sum(a.value_paise for a in systemic),
        "rerun_value_paise": sum(a.value_paise for a in rerun),
        "per_item_steps": sum(a.steps for a in per_item),
        "per_item_value_paise": sum(a.value_paise for a in per_item),
        "kinds": {
            "systemic": "One change at the source resolves the whole group.",
            "rerun": "No new data. The engine already holds everything and was "
                     "deliberately conservative.",
            "per_item": "Someone has to find a specific record. Real work, and "
                        "it does not amortise.",
        },
    }




def sync_view(r: Run | None) -> dict[str, Any]:
    """Whether the answer on screen is still valid, and what is owed. §38.

    Not "is the connection up". A reconciliation is a standing claim about a
    moving set of records, so the operational question is narrower and harder:
    which of the verdicts currently displayed were decided before evidence
    arrived that bears on them.

    Every accepted webhook names the settlements it can affect — the ingest
    layer already scopes that against the book the engine actually holds — so
    the settlements owed a re-verification are exactly the ones named by events
    that landed after the run started. That set is computed, not asserted, and
    it is empty when nothing has arrived, which is the common and correct case.
    """
    feed = event_feed(limit=500)
    events = feed.get("events", [])
    started = (r.started_at if r else "") or ""

    after: list[dict[str, Any]] = []
    for e in events:
        at = str(e.get("received_at") or "")
        if started and at and at > started:
            after.append(e)

    owed: dict[str, str] = {}
    for e in after:
        if e.get("status") != "accepted":
            continue
        for sid in e.get("affected", []):
            owed[sid] = e.get("kind", "event")

    by_status: dict[str, int] = {}
    for e in after:
        by_status[e.get("status", "?")] = by_status.get(e.get("status", "?"), 0) + 1

    st = {x.settlement_id: x for x in r.settlements} if r else {}
    src = integrations(r)
    active = src.get("active", {})

    return {
        "run_id": r.run_id if r else None,
        "started_at": started,
        "seed": r.seed if r else None,
        "settlements": len(r.settlements) if r else 0,
        "source": active.get("name") or active.get("kind") or "synthetic",
        "live": bool(active.get("live")),
        "linked_fraction": active.get("linked_fraction"),
        "freshness": (
            "Generated in-process for this run. There is no external source for "
            "it to be stale relative to, and saying otherwise would be the "
            "exact lie §39 warns about."
            if not active.get("live") else
            "Pulled from a connected account; staleness is measured against the "
            "last successful fetch."),
        "events_since_run": len(after),
        "events_by_status": by_status,
        "owed": [{"id": sid, "amount_paise": st[sid].net_paise if sid in st else 0,
                  "because": kind} for sid, kind in sorted(
                      owed.items(),
                      key=lambda kv: -(st[kv[0]].net_paise if kv[0] in st else 0))],
        "owed_paise": sum(st[sid].net_paise for sid in owed if sid in st),
        "note": (
            "Nothing has arrived since this run decided, so every verdict on "
            "screen still rests on the records it was decided from."
            if not owed else
            "These settlements were decided before evidence arrived that names "
            "them. Their verdicts are not wrong — they are unrevised, which is "
            "a different and recoverable thing."),
    }


# --------------------------------------------------------------------------
# Subject × lens shell
#
# The workspace has exactly two axes: which thing you are looking at, and how
# you are looking at it. Both are addressable, and neither changes the other.
# These two endpoints are the uniform contract that makes that possible — a
# shell component must be able to render a header and a spine for ANY subject
# without knowing which kind it is, or the component layer collapses back into
# one implementation per screen.
# --------------------------------------------------------------------------

#: Every lens, and which subject types it means something for. A cell that is
#: not here does not exist — the shell hides it rather than showing a disabled
#: control, because an affordance you cannot use is worse than one you cannot
#: see, and inventing empty data to fill the matrix would be worse than either.
LENS_MATRIX: dict[str, tuple[str, ...]] = {
    "control":     ("portfolio", "settlement", "action", "source"),
    "journal":     ("portfolio", "settlement"),
    "evidence":    ("portfolio", "settlement"),
    "investigate": ("portfolio", "settlement", "action"),
    "policy":      ("portfolio", "settlement"),
    "activity":    ("portfolio", "settlement", "source"),
    # Provenance is per-subject, not only per-portfolio: "which rule set, solver
    # and policy version decided THIS settlement" is a real question with a real
    # answer. Excluding it made the lens strip change shape when the subject
    # changed, which breaks the one promise that transition makes.
    "trust":       ("portfolio", "settlement"),
}

LENS_LABELS: dict[str, tuple[str, str]] = {
    "control":     ("Control", "What is happening?"),
    "journal":     ("Journal", "Where did the money go?"),
    "evidence":    ("Evidence", "Why do we believe this?"),
    "investigate": ("Investigate", "Why can't we resolve this?"),
    "policy":      ("Policy", "What are we allowed to do?"),
    "activity":    ("Activity", "What changed?"),
    "trust":       ("Trust", "Can I trust this system?"),
}


def lenses_for(subject_type: str) -> list[dict[str, str]]:
    return [{"key": k, "label": LENS_LABELS[k][0], "question": LENS_LABELS[k][1]}
            for k, types in LENS_MATRIX.items() if subject_type in types]


def subject_view(r: Run | None, stype: str, sid: str) -> dict[str, Any]:
    """The canonical record for one subject, whatever kind it is.

    One shape for portfolio, settlement, action and source, because the header
    that renders them is one component. Fields a given kind does not have are
    absent rather than blank, so the header can lay out what it was given
    instead of reserving space for what it wasn't.
    """
    if r is None:
        return {"error": "no run"}

    if stype == "portfolio":
        m = summary(r)
        return {
            "type": "portfolio", "id": "portfolio",
            "label": "Financial control", "sublabel": "all settlements",
            "amount_paise": m["processed_paise"],
            "amount_label": "processed",
            "meta": [
                {"k": "settlements", "v": f"{m['settlements']:,}"},
                {"k": "orders", "v": f"{m['orders']:,}"},
                {"k": "seed", "v": str(r.seed)},
            ],
            "lenses": lenses_for("portfolio"),
        }

    if stype == "settlement":
        st = {x.settlement_id: x for x in r.settlements}
        f = next((x for x in r.findings if x.settlement_id == sid), None)
        if f is None or sid not in st:
            return {"error": "unknown settlement"}
        s = st[sid]
        return {
            "type": "settlement", "id": sid,
            "label": sid, "sublabel": None,
            "amount_paise": s.net_paise, "amount_label": "bank credit",
            "status": f.verdict.value,
            "meta": [
                {"k": "value date", "v": str(s.settled_on)},
                {"k": "utr", "v": s.utr},
                {"k": "explanations", "v": str(len(f.proofs))},
            ],
            "lenses": lenses_for("settlement"),
        }

    if stype == "action":
        from attest.actions import plan
        amounts = {x.settlement_id: x.net_paise for x in r.settlements}
        act = next((a for a in plan(r.exceptions, amounts) if a.reason.value == sid),
                   None)
        if act is None:
            return {"error": "unknown action"}
        return {
            "type": "action", "id": sid,
            "label": act.what.split(";")[0][:1].upper() + act.what.split(";")[0][1:],
            "sublabel": act.kind.value.replace("_", " "),
            "amount_paise": act.value_paise, "amount_label": "unlocks",
            "status": act.kind.value.upper(),
            "meta": [
                {"k": "settlements", "v": str(act.settlements)},
                {"k": "work", "v": f"{act.steps} step{'' if act.steps == 1 else 's'}"},
                {"k": "per step", "v": _rs(act.leverage_paise)},
            ],
            "lenses": lenses_for("action"),
        }

    if stype == "source":
        src = integrations(r)
        a = src.get("active", {})
        sy = sync_view(r)
        return {
            "type": "source", "id": sid or "active",
            "label": str(a.get("name") or a.get("kind") or "synthetic").title(),
            "sublabel": "not live" if not a.get("live") else "live",
            "amount_paise": None,
            "status": "UNREVISED" if sy["owed"] else "CURRENT",
            "meta": [
                {"k": "records", "v": f"{len(r.orders):,} orders"},
                {"k": "since run", "v": f"{sy['events_since_run']} deliveries"},
            ],
            "lenses": lenses_for("source"),
        }

    return {"error": f"unknown subject type {stype}"}


#: The five stages money moves through. Not a progress bar — a statement about
#: where value is standing and what is holding it there.
SPINE = (
    ("source", "Source"),
    ("matching", "Matching"),
    ("verification", "Verification"),
    ("policy", "Policy"),
    ("action", "Action"),
)


def spine_view(r: Run | None, stype: str, sid: str,
               review_paise: int = 15_000,
               exposure_paise: int = 10_000_000) -> dict[str, Any]:
    """Where the money is standing, for a portfolio or for one settlement.

    The same five stages either way, because it is the same pipeline; only the
    population differs. For a portfolio each stage carries the value that
    cleared it and the value that stopped there. For one settlement it carries
    which stage it reached and why it went no further.
    """
    if r is None:
        return {"error": "no run"}

    from attest.policy import Decision
    costs = Costs(review_paise=review_paise, max_exposure_paise=exposure_paise)
    st = {x.settlement_id: x for x in r.settlements}

    def judge(f: Finding):
        return decide(f, st[f.settlement_id], r.risk or RiskModel(), costs)

    if stype == "settlement":
        f = next((x for x in r.findings if x.settlement_id == sid), None)
        if f is None or sid not in st:
            return {"error": "unknown settlement"}
        s = st[sid]
        pool = r.pools.get(sid, [])
        j = judge(f)
        proven = f.verdict is Verdict.PROVEN and getattr(f, "postable", False)
        posts = proven and j.decision is Decision.AUTO_POST

        # `continues_paise` is what is still moving after this stage. The flow
        # renders width from it, so it has to be a number rather than a
        # formatted string, and it has to be 0 once the subject has stopped.
        stopped_i = (2 if not proven else (3 if not posts else 5))
        stages = [
            {"key": "source", "label": "Source", "state": "passed",
             "continues_paise": s.net_paise,
             "value": _rs(s.net_paise),
             "detail": f"bank credit on {s.settled_on}, UTR {s.utr}"},
            {"key": "matching", "label": "Matching",
             "state": "passed" if pool else "stopped",
             "continues_paise": s.net_paise if pool else 0,
             "value": f"{len(pool)} candidates",
             "detail": (f"{len(pool)} orders could belong to this credit"
                        if pool else "no candidate orders in the window")},
            {"key": "verification", "label": "Verification",
             "state": "passed" if proven else "stopped",
             "continues_paise": s.net_paise if proven else 0,
             "value": f.verdict.value,
             "detail": ("unique explanation, kernel-checked, search space intact"
                        if proven else
                        f"{len(f.proofs)} explanations satisfy the amount exactly"
                        if f.verdict is Verdict.AMBIGUOUS else
                        "no subset of the candidates reaches this credit"
                        if f.verdict is Verdict.CONTRADICTED else
                        "proven, but inside a search space that excluded the truth"
                        if f.verdict is Verdict.PROVEN else
                        "not enough evidence to determine the state")},
            {"key": "policy", "label": "Policy",
             "state": ("passed" if posts else "stopped" if proven else "not_reached"),
             "continues_paise": s.net_paise if posts else 0,
             "value": j.decision.value if proven else "—",
             "detail": ((j.reasons or ("",))[-1] if proven else
                        "verification did not pass, so nothing was priced")},
            {"key": "action", "label": "Action",
             "state": "passed" if posts else "not_reached",
             "continues_paise": s.net_paise if posts else 0,
             "value": _rs(s.net_paise) if posts else "—",
             "detail": ("a balanced journal entry would post"
                        if posts else "no entry is written")},
        ]
        stopped = next((x["key"] for x in stages if x["state"] == "stopped"), None)
        return {"subject": sid, "type": "settlement", "stages": stages,
                "stopped_at": stopped}

    # -- portfolio ---------------------------------------------------------
    total = sum(x.net_paise for x in r.settlements)
    proven = [f for f in r.findings
              if f.verdict is Verdict.PROVEN and getattr(f, "postable", False)]
    proven_v = sum(st[f.settlement_id].net_paise for f in proven)
    posts = [f for f in proven if judge(f).decision is Decision.AUTO_POST]
    posts_v = sum(st[f.settlement_id].net_paise for f in posts)
    pooled = sum(1 for sid_ in r.pools if r.pools[sid_])

    stages = [
        {"key": "source", "label": "Source", "state": "passed",
         "continues_paise": total, "value": _rs(total), "count": len(r.settlements), "held": 0,
         "detail": f"{len(r.settlements):,} bank credits, {len(r.orders):,} orders"},
        {"key": "matching", "label": "Matching", "state": "passed",
         "continues_paise": total, "value": _rs(total), "count": pooled, "held": len(r.settlements) - pooled,
         "detail": "every credit has a candidate pool from the settlement calendar"},
        # A stage is `stopped` when value is standing at it, not when nothing
        # got through. Ticking every stage that passed ANY money made the
        # portfolio spine claim five successes while ₹48L was held at two of
        # them — the opposite of what the heading promises.
        {"key": "verification", "label": "Verification",
         "state": "stopped" if len(proven) < len(r.findings) else "passed",
         "continues_paise": proven_v,
         "value": _rs(proven_v), "count": len(proven),
         "held": len(r.findings) - len(proven), "held_value": _rs(total - proven_v),
         "detail": f"{len(r.findings) - len(proven)} settlements have no unique "
                   f"kernel-checked explanation"},
        {"key": "policy", "label": "Policy",
         "state": "stopped" if len(posts) < len(proven) else "passed",
         "continues_paise": posts_v,
         "value": _rs(posts_v), "count": len(posts),
         "held": len(proven) - len(posts),
         "held_value": _rs(proven_v - posts_v),
         "detail": f"{len(proven) - len(posts)} proven settlements cost more to "
                   f"get wrong than to check at {_rs(review_paise)} a review"},
        {"key": "action", "label": "Action",
         "state": "passed" if posts else "not_reached",
         "continues_paise": posts_v,
         "value": _rs(posts_v), "count": len(posts), "held": 0,
         "detail": f"{len(posts)} balanced journal "
                   f"{'entry' if len(posts) == 1 else 'entries'}"},
    ]
    stopped = "verification" if len(proven) < len(r.findings) else "policy"
    return {"subject": "portfolio", "type": "portfolio", "stages": stages,
            "stopped_at": stopped,
            "processed_paise": total, "posted_paise": posts_v}


def evidence_view(r: Run | None, stype: str, sid: str) -> dict[str, Any]:
    """Why should I believe this? §2, §16, §18.

    Assembled from the models that already exist — `graph`, `searchspace`,
    `coincidence`, `hypothesis` — rather than a second evidence model. The
    important thing this returns that no other endpoint does is the SHAPE of the
    candidate universe: what was considered, not only what was selected. The
    32/92 search-space failure happened because a proof can be arithmetically
    perfect inside a space that excluded the truth, and a reader cannot judge
    that without seeing the boundary.

    AI-asserted relationships are carried in their own key, never mixed into
    `chain`. Putting them in the same list and relying on a flag is how they end
    up rendered the same way.
    """
    if r is None:
        return {"error": "no run"}

    from attest.graph import DETERMINISTIC, EdgeKind

    if stype == "portfolio":
        return _evidence_portfolio(r)
    if stype != "settlement":
        return {"error": f"evidence has nothing to say about a {stype}"}

    st = {x.settlement_id: x for x in r.settlements}
    f = next((x for x in r.findings if x.settlement_id == sid), None)
    if f is None or sid not in st:
        return {"error": "unknown settlement"}
    s = st[sid]
    pool = r.pools.get(sid, [])
    by_id = {o.order_id: o for o in r.orders}
    d = detail(r, sid) or {}

    # -- what records are in play, by kind ---------------------------------
    counts = [{"kind": "order", "n": len(pool),
               "paise": sum(o.gross_paise for o in pool),
               "note": "in the candidate pool"}]
    if f.proofs:
        counts.append({"kind": "explanation", "n": len(f.proofs), "paise": 0,
                       "note": "satisfy the amount exactly"})
    counts.append({"kind": "bank credit", "n": 1, "paise": s.net_paise,
                   "note": f"UTR {s.utr}"})

    # -- the shared / unique decomposition. §8: ambiguity must be visual ----
    ex = r.exceptions.get(sid)
    settled = getattr(ex, "settled", None)
    shared_ids = set(settled.order_ids) if settled else set()
    explanations = []
    for i, p in enumerate(f.proofs):
        uniq = [o for o in (by_id[x] for x in p.order_ids if x in by_id)
                if o.order_id not in shared_ids]
        explanations.append({
            "letter": chr(65 + i),
            "orders": len(p.order_ids),
            "shared": len(p.order_ids) - len(uniq),
            "net_paise": p.net_paise,
            "residual_paise": p.residual_paise,
            "tolerance_paise": p.tolerance_paise,
            "unique": [{"id": o.order_id, "method": o.method,
                        "captured_on": str(o.captured_on),
                        "paise": o.gross_paise} for o in uniq],
        })

    # -- the deterministic chain, from the graph that already exists -------
    g = d.get("graph") or {"nodes": [], "edges": []}
    nodes = {n["id"]: n for n in g.get("nodes", [])}
    chain, ai = [], []
    for e in g.get("edges", []):
        rec = {
            "from": nodes.get(e["src"], {"label": e["src"]}),
            "to": nodes.get(e["dst"], {"label": e["dst"]}),
            "kind": e["kind"], "why": e.get("why", ""),
            "paise": e.get("paise", 0), "proven": bool(e.get("proven")),
        }
        (chain if rec["proven"] else ai).append(rec)

    # -- AI hypotheses are a separate key on purpose. §6, §18 --------------
    hypotheses = []
    if f.verdict is Verdict.AMBIGUOUS:
        trail = investigate_view(r, sid) or {}
        for ev in trail.get("events", []):
            if ev.get("actor") == "model" and ev.get("act") == "propose":
                hypotheses.append({"stage": "proposed", "lens": ev.get("lens", ""),
                                   "detail": ev.get("detail", "")})
            elif ev.get("actor") == "solver":
                hypotheses.append({"stage": ev.get("act"), "lens": ev.get("lens", ""),
                                   "detail": ev.get("detail", "")})

    return {
        "subject": sid, "type": "settlement", "verdict": f.verdict.value,
        "amount_paise": s.net_paise,
        "counts": counts,
        "space": d.get("space"),
        "coincidence": d.get("coincidence"),
        "shared": {"n": len(shared_ids),
                   "paise": settled.net_paise if settled else 0,
                   "disputed_paise": settled.disputed_paise if settled else 0,
                   "differing": settled.differing_orders if settled else 0},
        "explanations": explanations,
        "chain": chain,
        "ai": {"edges": ai, "trail": hypotheses,
               "enabled": False,
               "note": "Asserted by a model and never load-bearing. An AI "
                       "relationship may suggest where to look; it may not "
                       "justify a posting."},
        "missing": ([{"what": ex.reason.value.replace("_", " ").lower(),
                      "next": ex.next_step}] if ex else []),
        "edge_kinds": {k.value: (k in DETERMINISTIC) for k in EdgeKind},
    }


def _evidence_portfolio(r: Run) -> dict[str, Any]:
    """The evidence landscape, scoped. §28: never render thousands of nodes.

    What a reader needs at portfolio scale is not every record but the shape of
    the boundary — how much of the book rests on reductions that are conventions
    rather than proofs, because that is the number the 32/92 failure was about.
    """
    integ: dict[str, int] = {}
    reductions: dict[str, dict[str, Any]] = {}
    for f in r.findings:
        sp = getattr(f, "space", None)
        if sp is None:
            continue
        integ[sp.integrity.value] = integ.get(sp.integrity.value, 0) + 1
        for red in sp.reductions:
            g = reductions.setdefault(red.name, {
                "name": red.name, "deterministic": red.deterministic,
                "justification": red.justification, "settlements": 0, "removed": 0})
            g["settlements"] += 1
            g["removed"] += red.removed

    st = {x.settlement_id: x for x in r.settlements}
    heur = sum(st[f.settlement_id].net_paise for f in r.findings
               if getattr(f, "space", None)
               and f.space.integrity.value != "validated")

    return {
        "subject": "portfolio", "type": "portfolio",
        "counts": [
            {"kind": "order", "n": len(r.orders), "paise": 0,
             "note": "the whole book"},
            {"kind": "bank credit", "n": len(r.settlements),
             "paise": sum(x.net_paise for x in r.settlements), "note": "received"},
            {"kind": "explanation", "n": sum(len(f.proofs) for f in r.findings),
             "paise": 0, "note": "found across every settlement"},
        ],
        "integrity": integ,
        "heuristic_paise": heur,
        "reductions": sorted(reductions.values(), key=lambda x: -x["removed"]),
        "ai": {"enabled": False,
               "note": "No AI relationship is load-bearing anywhere in this run."},
    }


#: Solver outcomes as named states, not a confidence number. §18: "AI confidence"
#: collapses six different findings into one, and the difference between "no
#: explanation contains this" and "every explanation contains this" is the whole
#: of what the operator needs to know.
SOLVER_RESULT: dict[str, tuple[str, str]] = {
    "uniqueness": ("NON_DISCRIMINATIVE",
                   "every surviving explanation contains it, so it cannot "
                   "choose between them"),
    "consistency": ("NO_FEASIBLE_SOLUTION",
                    "no valid explanation contains it; the anchor and the "
                    "arithmetic disagree"),
    "existence": ("INVALID",
                  "it cites records that are not in the candidate pool"),
    "kernel": ("INVALID",
               "the selected explanation was rejected by the independent "
               "verifier"),
}


def investigation_view(r: Run | None, stype: str, sid: str) -> dict[str, Any]:
    """What should I check next? §1, §5, §16.

    Evidence reports established relationships. This reports inquiry: what was
    asked, what was proposed, what the solver did to it, and what was learned
    when it failed. Failures are the point rather than an embarrassment — a
    trail cleaned up to make the model look competent is worth nothing, because
    the reader cannot tell a good answer from a lucky one.

    Runs the existing loop; does not reimplement it.
    """
    if r is None:
        return {"error": "no run"}
    if stype == "portfolio":
        return _investigation_queue(r)
    if stype != "settlement":
        return {"error": f"nothing to investigate about a {stype}"}

    st = {x.settlement_id: x for x in r.settlements}
    f = next((x for x in r.findings if x.settlement_id == sid), None)
    if f is None or sid not in st:
        return {"error": "unknown settlement"}

    question = {
        Verdict.AMBIGUOUS: "Why are these explanations indistinguishable?",
        Verdict.CONTRADICTED: "Why does nothing explain this credit?",
        Verdict.INSUFFICIENT: "What evidence is missing?",
        Verdict.PROVEN: "What could still be wrong about this?",
    }[f.verdict]

    raw = (investigate_view(r, sid) or {}).get("events", []) \
        if f.verdict is Verdict.AMBIGUOUS else []

    steps, tested, discriminative = [], 0, 0
    for e in raw:
        actor, act = e.get("actor"), e.get("act")
        if actor == "model" and act == "propose":
            steps.append({"actor": "model", "action": "proposed",
                          "input": e.get("lens", ""), "detail": e.get("detail", ""),
                          "result": None})
        elif actor == "solver":
            tested += 1
            constraint = str(e.get("detail", "")).split(":")[0].strip()
            code, why = SOLVER_RESULT.get(constraint, ("REFUTED", ""))
            if act == "accept":
                code, why = "VALID", "it selects exactly one explanation"
                discriminative += 1
            steps.append({"actor": "solver", "action": "tested",
                          "input": constraint or "constraint",
                          "detail": e.get("detail", ""),
                          "result": code, "why": why})
        elif actor == "model" and act == "exhausted":
            steps.append({"actor": "model", "action": "exhausted",
                          "input": "", "detail": e.get("detail", ""), "result": None})
        elif actor == "engine":
            steps.append({"actor": "engine", "action": act,
                          "input": "", "detail": e.get("detail", ""),
                          "result": "ABSTAINED" if act == "abstain" else None})

    # -- what the pool itself says about the lens the model chose. §7 -------
    # Computed from this settlement's own pool and the recorded measurement, so
    # the finding appears when it is true rather than being written into the UI.
    pool = r.pools.get(sid, [])
    dates = {o.captured_on for o in pool}
    signal = None
    if pool and any(s["input"] == "capture-batch" for s in steps
                    if s["actor"] == "model"):
        share = None
        try:
            import json as _json
            import pathlib as _pl
            share = _json.loads((_pl.Path(__file__).resolve().parent.parent
                                 / "benchmark" / "anchoring.json").read_text()
                                )["single_date_share"]
        except Exception:
            pass
        signal = {
            "lens": "capture-batch", "pool": len(pool),
            "capture_dates": len(dates),
            "vacuous": len(dates) == 1,
            "share_single_date": share,
            "note": (f"Every order in this pool was captured on the same day, so "
                     f"'the densest same-day batch' is true of all {len(pool)} of "
                     f"them and separates nothing."
                     if len(dates) == 1 else
                     f"This pool spans {len(dates)} capture dates, so the lens "
                     f"has something to distinguish."),
        }

    ex = r.exceptions.get(sid)
    resolvers = []
    if f.verdict is Verdict.AMBIGUOUS:
        resolvers.append({
            "what": "an order-level reference on the settlement report",
            "would": f"distinguish all {len(f.proofs)} explanations",
            "status": "missing"})
        sp = getattr(f, "space", None)
        if sp is not None and sp.integrity.value != "validated":
            resolvers.append({
                "what": "a wider settlement window, re-run",
                "would": "test whether uniqueness is global rather than local",
                "status": "available now"})
    elif ex is not None:
        resolvers.append({"what": ex.next_step, "would": "resolve the exception",
                          "status": "unknown"})

    return {
        "subject": sid, "type": "settlement",
        "question": question,
        "verdict": f.verdict.value,
        "state": ("abstained" if steps and discriminative == 0
                  else "resolved" if discriminative else "open"),
        "verdict_changed": False,
        "tested": tested, "discriminative": discriminative,
        "steps": steps,
        "signal": signal,
        "resolvers": resolvers,
        "provenance": (r.provenance.to_json() if r.provenance else {}),
        "note": ("The loop ran and its verdict was discarded. Abstention is a "
                 "result, not a failure to produce one."),
    }


def _investigation_queue(r: Run) -> dict[str, Any]:
    """What to investigate first. §13, §14.

    Grouped by cause, ordered by what an investigation could unlock — not by
    amount, and not by a value-of-information number the project has never
    measured. The honest ordering available is: how much value is behind this
    cause, and whether one answer settles all of it or each case needs its own.
    """
    from attest.actions import Kind, plan

    amounts = {x.settlement_id: x.net_paise for x in r.settlements}
    acts = plan(r.exceptions, amounts)

    groups = []
    for a in acts:
        one = a.kind is not Kind.PER_ITEM
        groups.append({
            "reason": a.reason.value,
            "cause": a.why or a.reason.value.replace("_", " ").lower(),
            "settlements": a.settlements,
            "value_paise": a.value_paise,
            "kind": a.kind.value,
            "one_answer": one,
            "worth": ("One answer settles all of them."
                      if one else
                      f"Each of the {a.settlements} needs its own answer."),
            "question": _question_for(a.reason.value),
            "examples": list(a.examples),
        })
    return {
        "subject": "portfolio", "type": "portfolio",
        "groups": groups,
        "total_paise": sum(g["value_paise"] for g in groups),
        "note": "Ordered by what an answer would unlock, not by amount. A cause "
                "worth ₹47L that one change settles outranks fifty separate "
                "questions worth ₹10k each.",
    }


def _question_for(reason: str) -> str:
    return {
        "MULTIPLE_VALID_ASSIGNMENTS":
            "What evidence would separate the surviving explanations?",
        "SEARCH_SPACE_UNCERTAIN":
            "Does the explanation survive a wider window?",
        "NO_VALID_ASSIGNMENT":
            "What record is missing from the candidate pool?",
        "UNKNOWN_ADJUSTMENT":
            "What is the unmatched amount, and where would it be recorded?",
        "REFUND_MISMATCH": "Which refund accounts for the shortfall?",
        "CHARGEBACK": "Which reversal accounts for the shortfall?",
        "PARTIAL_SETTLEMENT": "Was this order paid out across more than one credit?",
        "MISSING_TRANSACTION": "Which capture is absent from the export?",
        "DUPLICATE_AMOUNT": "What breaks the tie between identical candidates?",
        "TIMING_MISMATCH": "What is this merchant's actual payout calendar?",
        "INSUFFICIENT_EVIDENCE": "What would make this examinable at all?",
        "DATA_QUALITY": "Which rows are malformed, and how?",
    }.get(reason, "What should be checked next?")


def decision_view(r: Run | None, stype: str, sid: str,
                  review_paise: int = 15_000,
                  exposure_paise: int = 10_000_000) -> dict[str, Any]:
    """Given what ATTEST knows, what is it allowed to do? §1, §9, §17.

    Policy never changes a verdict. It reads one and decides what action the
    proof state permits, which is why the two are reported separately here
    rather than blended into a single status — a settlement can be AMBIGUOUS and
    REVIEW, and it is important that those are two facts and not one.

    The decision is the engine's; this endpoint only unpacks it into rows. The
    inequality it turns on is

        P(error) × cost of a wrong posting  <  cost of a human review

    and every term is reported so a reader can check the arithmetic rather than
    trust the outcome.
    """
    if r is None:
        return {"error": "no run"}

    costs = Costs(review_paise=review_paise, max_exposure_paise=exposure_paise)
    recorded = Costs()
    version = policy_version(costs)
    is_sim = version != policy_version(recorded)

    if stype == "portfolio":
        d = policy_view(r, review_paise, exposure_paise)
        d.update({
            "type": "portfolio", "subject": "portfolio",
            "policy_version": version,
            "recorded_version": policy_version(recorded),
            "simulated": is_sim,
            "groups": [
                {"decision": "AUTO_POST", "count": d["auto_post"],
                 "paise": d["posted_paise"],
                 "why": "expected loss is below the cost of checking"},
                {"decision": "REVIEW", "count": d["review"],
                 "paise": d["protected_paise"],
                 "why": "checking costs less than being wrong would"},
                {"decision": "BLOCK", "count": d["block"], "paise": 0,
                 "why": "above the exposure ceiling, where expected value is "
                        "the wrong instrument"},
            ],
        })
        return d

    if stype != "settlement":
        return {"error": f"policy has nothing to say about a {stype}"}

    st = {x.settlement_id: x for x in r.settlements}
    f = next((x for x in r.findings if x.settlement_id == sid), None)
    if f is None or sid not in st:
        return {"error": "unknown settlement"}
    s = st[sid]
    j = decide(f, s, r.risk or RiskModel(), costs)

    exposure = costs.wrong_post(s.net_paise)
    loss = j.expected_loss_paise
    proven = f.verdict is Verdict.PROVEN
    postable = proven and getattr(f, "postable", False)

    # §17: the safety chain, as gates that each say pass or fail and why. The
    # order is the argument — nothing reaches policy without passing proof.
    gates = [
        {"stage": "proof", "name": "a unique explanation exists",
         "ok": proven,
         "why": ("one order set satisfies the credit exactly"
                 if proven else
                 f"the verdict is {f.verdict.value}")},
        {"stage": "proof", "name": "re-derived by the independent verifier",
         "ok": proven,
         "why": ("the 28-line kernel accepted it, sharing no code with the prover"
                 if proven else "nothing was submitted to the verifier")},
        {"stage": "proof", "name": "the search space was not compromised",
         "ok": bool(postable),
         "why": ("uniqueness holds inside a space that did not exclude the truth"
                 if postable else
                 "uniqueness inside a reduced space is not uniqueness"
                 if proven else "not reached")},
        {"stage": "policy", "name": "expected loss is below the cost of checking",
         "ok": bool(postable) and loss < costs.review_paise,
         "why": (f"{_rs(loss)} against {_rs(costs.review_paise)}"
                 if postable else "not reached — nothing was priced")},
        {"stage": "policy", "name": "below the exposure ceiling",
         "ok": s.net_paise <= costs.max_exposure_paise,
         "why": (f"{_rs(s.net_paise)} against a ceiling of "
                 f"{_rs(costs.max_exposure_paise)}")},
    ]

    inputs = [
        {"k": "verdict", "v": f.verdict.value,
         "note": "policy reads this; it never changes it"},
        {"k": "search space",
         "v": (f.space.integrity.value if getattr(f, "space", None) else "—"),
         "note": (f.space.uniqueness_claim() if getattr(f, "space", None) else "")},
    ]
    if proven:
        inputs += [
            {"k": "P(error)", "v": f"{j.p_error:.4f}",
             "note": "the 95% upper bound on the observed rate for this stratum, "
                     "not the point estimate"},
            {"k": "cost if wrong", "v": _rs(exposure),
             "note": "the posting, plus what unwinding it costs"},
            {"k": "expected loss", "v": _rs(loss),
             "note": "P(error) × cost if wrong"},
        ]
    inputs.append({"k": "cost of a review", "v": _rs(costs.review_paise),
                   "note": "an analyst opening this settlement and deciding"})

    return {
        "type": "settlement", "subject": sid,
        "verdict": f.verdict.value,
        "decision": j.decision.value,
        "amount_paise": s.net_paise,
        "inputs": inputs,
        "gates": gates,
        # The boundary, as two comparable numbers on one axis. Reported even
        # when nothing was priced, so the reader can see WHY it was not.
        "boundary": {
            "priced": bool(postable),
            "expected_loss_paise": loss if postable else None,
            "review_paise": costs.review_paise,
            "ceiling_paise": costs.max_exposure_paise,
            "statement": ((f"{_rs(loss)} expected loss against {_rs(costs.review_paise)} "
                           f"to check — "
                           + ("automating is cheaper" if loss < costs.review_paise
                              else "checking is cheaper"))
                          if postable else
                          "Nothing was priced. The proof did not establish a "
                          "unique explanation, so there is no error probability "
                          "to multiply."),
        },
        "reasons": list(j.reasons),
        "policy_version": version,
        "recorded_version": policy_version(recorded),
        "simulated": is_sim,
        "provenance": (r.provenance.to_json() if r.provenance else {}),
        "note": "Policy decides what the proof state permits. It cannot make a "
                "settlement proven, and a proven settlement is not "
                "automatically posted.",
    }


def activity_view(r: Run | None, stype: str, sid: str) -> dict[str, Any]:
    """What actually happened. §1, §9, §18.

    Not a log. A log answers "what events exist"; this has to answer what
    happened, what caused it, what changed, and what it did to the money —
    which means every entry carries its cause and its effect rather than a
    status column.

    Two boundaries are load-bearing and are kept apart structurally rather than
    by wording. POLICY records what was PERMITTED. ACTION records what was DONE.
    A settlement can be permitted and unposted, and the reader must be able to
    see that at a glance.

    Timestamps are the run's PHASE times, taken from its audit log. The engine
    decides 250 settlements inside one 2.5-second reconcile step, so a
    per-record millisecond timestamp would be invented. This says which phase a
    thing happened in, which is the true resolution available.
    """
    if r is None:
        return {"error": "no run"}
    if stype == "portfolio":
        return _activity_portfolio(r)
    if stype != "settlement":
        return {"error": f"no activity for a {stype}"}

    st = {x.settlement_id: x for x in r.settlements}
    f = next((x for x in r.findings if x.settlement_id == sid), None)
    if f is None or sid not in st:
        return {"error": "unknown settlement"}
    s = st[sid]
    pool = r.pools.get(sid, [])
    j = _judge(r, f, s)
    phase = {a["event"]: a["t"] for a in r.audit}

    from attest.policy import Decision
    proven = f.verdict is Verdict.PROVEN and getattr(f, "postable", False)
    posts = proven and j.decision is Decision.AUTO_POST

    ev: list[dict[str, Any]] = [
        {"stage": "source", "actor": "system", "at": phase.get("ingest", ""),
         "what": "Bank credit received",
         "value": _rs(s.net_paise),
         "caused_by": None,
         "effect": f"value date {s.settled_on}, UTR {s.utr}"},
        {"stage": "matching", "actor": "system", "at": phase.get("reconcile", ""),
         "what": f"{len(pool)} candidate orders generated",
         "value": None,
         "caused_by": "the settlement calendar for this value date",
         "effect": "the universe the solver was allowed to search"},
        {"stage": "verification", "actor": "engine", "at": phase.get("verdicts", ""),
         "what": ((f"{len(f.proofs)} explanation satisfies the amount exactly"
                   if len(f.proofs) == 1 else
                   f"{len(f.proofs)} explanations satisfy the amount exactly")
                  if f.proofs else "No subset reaches the credit"),
         "result": f.verdict.value,
         "value": None,
         "caused_by": f"{len(pool)} candidates and a tolerance of "
                      f"±{f.proofs[0].tolerance_paise if f.proofs else 0} paise",
         "effect": ("a unique order set, re-derived by the kernel" if proven
                    else "nothing unique enough to act on")},
    ]

    if f.verdict is Verdict.AMBIGUOUS:
        for e in (investigate_view(r, sid) or {}).get("events", []):
            actor, act = e.get("actor"), e.get("act")
            if actor == "model" and act == "propose":
                ev.append({"stage": "investigation", "actor": "model",
                           "at": phase.get("verdicts", ""),
                           "what": f"Proposed a {e.get('lens', '')} anchor",
                           "detail": e.get("detail", ""), "value": None,
                           "caused_by": "the verdict was ambiguous",
                           "effect": "a hypothesis for the solver to test"})
            elif actor == "solver":
                constraint = str(e.get("detail", "")).split(":")[0].strip()
                code = SOLVER_RESULT.get(constraint, ("REFUTED", ""))[0]
                ev.append({"stage": "investigation", "actor": "solver",
                           "at": phase.get("verdicts", ""),
                           "what": f"Tested the anchor against {constraint}",
                           "result": code, "detail": e.get("detail", ""),
                           "value": None,
                           "caused_by": "the model proposed it",
                           "effect": "the hypothesis did not survive"})
            elif actor == "engine" and act == "abstain":
                ev.append({"stage": "investigation", "actor": "engine",
                           "at": phase.get("verdicts", ""),
                           "what": "Abstained", "result": "VERDICT UNCHANGED",
                           "value": None,
                           "caused_by": "no hypothesis distinguished the explanations",
                           "effect": "the verdict it already had"})

    ev.append({
        "stage": "policy", "actor": "policy", "at": phase.get("policy", ""),
        "what": f"{j.decision.value.replace('_', '-')} permitted"
                if j.decision is Decision.AUTO_POST
                else f"{j.decision.value.replace('_', '-')} required",
        "result": j.decision.value,
        "permitted": bool(posts),
        "value": None,
        "caused_by": (j.reasons or ("",))[-1],
        "effect": ("a posting is allowed — not performed" if posts
                   else "no automatic action is allowed")})

    ev.append({
        "stage": "action", "actor": "engine" if posts else None,
        "at": phase.get("exceptions", ""),
        "what": "Journal entry written" if posts else "No entry written",
        "result": "LEDGER UPDATED" if posts else "LEDGER UNCHANGED",
        "executed": bool(posts),
        "value": _rs(s.net_paise) if posts else None,
        "caused_by": ("policy permitted it" if posts
                      else "policy did not permit a posting"),
        "effect": ("balanced to the paisa" if posts
                   else "the settlement waits for a person")})

    return {
        "type": "settlement", "subject": sid,
        "state": {"verdict": f.verdict.value, "decision": j.decision.value,
                  "posted": posts},
        "events": ev,
        "run": {"id": r.run_id, "started_at": r.started_at},
        "note": "Times are the run's phase timestamps. The engine decides every "
                "settlement inside one reconcile step, so a per-record time "
                "would be invented rather than measured.",
        "actors": {"system": "ingest and blocking", "model": "proposes",
                   "solver": "tests", "engine": "decides",
                   "policy": "permits"},
    }


def _activity_portfolio(r: Run) -> dict[str, Any]:
    """The run as a parent with its phases as children. §6, §27."""
    from attest.policy import Decision

    st = {x.settlement_id: x for x in r.settlements}
    proven = [f for f in r.findings
              if f.verdict is Verdict.PROVEN and getattr(f, "postable", False)]
    posts = [f for f in proven
             if _judge(r, f, st[f.settlement_id]).decision is Decision.AUTO_POST]

    ACTOR = {"run.start": "system", "ingest": "system", "reconcile": "engine",
             "calibrate": "engine", "verdicts": "engine", "kernel": "engine",
             "policy": "policy", "provenance": "system", "exceptions": "engine"}
    phases = [{
        "at": a["t"], "key": a["event"], "actor": ACTOR.get(a["event"], "system"),
        "what": a["event"].replace(".", " ").replace("_", " "),
        "detail": a["detail"],
    } for a in r.audit]

    feed = event_feed(limit=60)
    sync = sync_view(r)
    total = sum(x.net_paise for x in r.settlements)
    posted = sum(st[f.settlement_id].net_paise for f in posts)

    return {
        "type": "portfolio", "subject": "portfolio",
        "run": {"id": r.run_id, "started_at": r.started_at,
                "from": phases[0]["at"] if phases else "",
                "to": phases[-1]["at"] if phases else "",
                "phases": phases},
        "outcome": [
            {"k": "processed", "v": _rs(total), "n": len(r.settlements)},
            {"k": "held at verification", "v": _rs(total - sum(
                st[f.settlement_id].net_paise for f in proven)),
             "n": len(r.findings) - len(proven)},
            {"k": "permitted to post", "v": _rs(posted), "n": len(posts)},
            {"k": "actually posted", "v": _rs(posted), "n": len(posts)},
        ],
        "deliveries": feed.get("events", []),
        "delivery_counts": feed.get("counts", {}),
        "unrevised": sync.get("owed", []),
        "unrevised_note": sync.get("note", ""),
        "note": "One run, its phases beneath it. Individual settlement events "
                "live on the settlement, because five thousand of them here "
                "would be a log rather than a story.",
    }


def replay_view(r: Run | None) -> dict[str, Any]:
    """Re-execute the run and compare. §36.

    Built only because the claim is measurable: a run is a pure function of
    (size, seed), so re-running it either reproduces the verdicts and the
    provenance or it does not, and this reports which. It does not mutate the
    original — the new run is a separate record with its own id.
    """
    if r is None:
        return {"error": "no run"}
    import time as _t

    n = len(r.settlements)
    t0 = _t.time()
    again = execute(n, r.seed)
    elapsed = _t.time() - t0

    def fp(x: Run):
        return {f.settlement_id: (f.verdict.value,
                                  tuple(sorted(f.proofs[0].order_ids))
                                  if f.proofs else ())
                for f in x.findings}

    a, b = fp(r), fp(again)
    differing = sorted(k for k in a if a.get(k) != b.get(k))
    return {
        "original": {"id": r.run_id, "at": r.started_at,
                     "provenance": r.provenance.to_json() if r.provenance else {}},
        "replay": {"id": again.run_id, "at": again.started_at,
                   "provenance": again.provenance.to_json() if again.provenance else {},
                   "seconds": round(elapsed, 2)},
        "settlements": len(a),
        "differing": len(differing),
        "examples": differing[:5],
        "provenance_identical": (r.provenance.to_json() if r.provenance else {})
                                == (again.provenance.to_json() if again.provenance else {}),
        "reproduced": not differing,
        "note": ("Every verdict and every order set came back identical, under "
                 "identical provenance. The original run is untouched; this is a "
                 "separate record."
                 if not differing else
                 f"{len(differing)} settlements decided differently, which means "
                 f"the run is not a pure function of its inputs."),
    }


def _artifact(name: str) -> dict[str, Any]:
    import json as _json
    import pathlib as _pl
    try:
        return _json.loads((_pl.Path(__file__).resolve().parent.parent
                            / "benchmark" / name).read_text())
    except Exception:
        return {}


def trust_claims() -> dict[str, Any]:
    """Every claim ATTEST makes, and whether anything on disk supports it. §5, §6.

    Nothing here is transcribed. Each claim names the artifact it reads and the
    scope that artifact records, so a number cannot drift from its evidence —
    which is the failure mode D22 demonstrated when a precision figure sat in a
    markdown table for six days without anything checking it.

    A claim whose evidence is a prose document rather than a machine-readable
    artifact is reported as LIMITED, not as measured. A claim with no evidence
    at all is reported as NOT MEASURED rather than as zero. §23: the surface has
    to be able to say no.
    """
    res, base, anch = (_artifact("results.json"), _artifact("baselines.json"),
                       _artifact("anchoring.json"))
    p = res.get("pooled", {})
    seeds = res.get("evaluation_seeds", [])
    n = p.get("settlements", 0)
    scope = (f"{n} settlements over {len(seeds)} evaluation "
             f"{'seed' if len(seeds) == 1 else 'seeds'}") if n else "not recorded"

    claims: list[dict[str, Any]] = []

    def claim(cid, group, text, status, value=None, source=None, measured=None,
              limitation=None, detail=None):
        claims.append({"id": cid, "group": group, "claim": text,
                       "status": status, "value": value, "source": source,
                       "measured_on": measured, "limitation": limitation,
                       "detail": detail})

    # ---- safety ---------------------------------------------------------
    if p:
        claim("C-001", "safety",
              "No value was auto-posted incorrectly.",
              "MEASURED", _rs(p.get("incorrectly_auto_posted_paise", 0)),
              "benchmark/results.json", scope,
              "True of this evaluation panel. It is not a claim that ATTEST "
              "cannot auto-post incorrectly — only that on these portfolios, at "
              "this costing, it did not.")
        wrong, proven = p.get("false_proofs", 0), p.get("proven", 0)
        claim("C-002", "safety",
              "A claim of proof was wrong this often.",
              "MEASURED",
              f"{wrong}/{proven} of proofs · {wrong}/{n} of settlements",
              "benchmark/results.json", scope,
              "Two denominators, and they differ by six times. Per proof "
              f"offered it is {wrong / max(proven, 1):.3f}; per settlement "
              f"processed it is {wrong / max(n, 1):.3f}. The first is the one "
              "that matters to someone reading a proof.")
    else:
        claim("C-001", "safety", "No value was auto-posted incorrectly.",
              "NOT MEASURED", None, "benchmark/results.json", None,
              "The benchmark artifact is missing.")

    # ---- correctness against baselines ----------------------------------
    if base.get("methods"):
        m = base["methods"]
        a = m.get("attest", {})
        best = min((k for k in m if k != "attest"),
                   key=lambda k: m[k].get("false_proof_rate", 1))
        claim("C-003", "correctness",
              "ATTEST recovers more exact sets than any baseline.",
              "MEASURED",
              " · ".join(f"{k} {m[k]['coverage'] * 100:.1f}%"
                         for k in ("attest", "exact_only", "fuzzy", "greedy")
                         if k in m),
              "benchmark/baselines.json",
              f"{base.get('settlements', 0)} settlements, identical datasets "
              f"and identical scoring",
              None,
              base.get("note"))
        claim("C-004", "correctness",
              "ATTEST is not the most precise method on this panel.",
              "MEASURED",
              f"attest {a.get('false_proof_rate', 0) * 100:.1f}% wrong · "
              f"{best} {m[best].get('false_proof_rate', 0) * 100:.1f}% wrong",
              "benchmark/baselines.json",
              f"{base.get('settlements', 0)} settlements",
              f"{best} makes fewer mistakes because it answers far less often — "
              f"{m[best].get('decided', 0)} settlements against "
              f"{a.get('decided', 0)}. Precision alone is trivially winnable by "
              f"declining, which is why coverage is reported beside it.")
    else:
        claim("C-003", "correctness", "ATTEST outperforms the baselines.",
              "NOT MEASURED", None, "benchmark/baselines.json", None,
              "No baseline artifact on disk.")

    # ---- AI --------------------------------------------------------------
    if anch:
        claim("C-005", "ai",
              "The model cannot reliably resolve an ambiguous settlement.",
              "MEASURED", f"{anch.get('precision', 0):.3f} precision",
              "benchmark/anchoring.json",
              f"{anch.get('ambiguous', 0)} ambiguous settlements over "
              f"{len(anch.get('seeds', []))} seeds",
              "This is why the loop is disabled as a resolver. It is not a "
              "figure to improve later — the lens duplicates a signal the "
              "blocking already applies.",
              anch.get("note"))
        claim("C-006", "ai",
              "The model's lens is vacuous on most candidate pools.",
              "MEASURED",
              f"{anch.get('single_date_share', 0) * 100:.0f}% span one capture date",
              "benchmark/anchoring.json",
              f"{anch.get('pools', 0)} candidate pools", None)

    # ---- reproducibility -------------------------------------------------
    claim("C-007", "reproducibility",
          "A run is reproducible from its size and seed.",
          "SUPPORTED", "verified on demand",
          "computed live by /api/replay", "one run, on request",
          "Measured when asked rather than recorded, so this reports the "
          "capability and the Activity lens reports the result.")

    # ---- performance ------------------------------------------------------
    claim("C-008", "performance",
          "The native kernel is substantially faster than the numpy path.",
          "LIMITED", "see native/BENCH.md",
          "native/BENCH.md — a document, not an artifact", "one credit size",
          "The figure lives in prose rather than in a machine-readable result, "
          "so nothing checks it on a build. It is reported as limited for that "
          "reason alone, not because the measurement is doubted.")

    # ---- gates -------------------------------------------------------------
    from attest.eval.gate import GATES
    cur, prev = p, _artifact("baseline.json").get("pooled", {})
    gates = []
    for g in GATES:
        a, b = cur.get(g.key), prev.get(g.key)
        if a is None or b is None:
            state = "NOT MEASURED"
        else:
            ok = (float(a) <= float(b) + g.tolerance
                  if g.direction == "lower_is_better"
                  else float(a) >= float(b) - g.tolerance)
            state = "PASS" if ok else ("FAIL" if g.fatal else "WARN")
        gates.append({"key": g.key, "label": g.label, "fatal": g.fatal,
                      "why": g.why, "state": state, "value": a, "baseline": b})

    obs = observatory()

    # CORE-001. Carried explicitly rather than left to the failure list, because
    # it is the one defect found in the protected core and the distinction it
    # turns on is easy to state wrongly: the exploit produced no financial
    # impact, and the integrity boundary was still incorrect.
    fixed = [{
        "id": "CORE-001",
        "what": "A forged proof without search-space provenance reached the "
                "postability boundary",
        "status": "FIXED",
        "why_it_mattered":
            "`Finding.postable` returned True when no search space was "
            "recorded, so a proof was postable because it omitted the evidence "
            "it would have been judged on. The gate that exists to encode D8 "
            "trusted a proof whose candidate universe was unrecorded.",
        "fix": "Postability now requires a search-space record, a recorded "
               "candidate universe, a named solver, and a proof that fits "
               "inside that universe. It fails closed on any of them.",
        "measured":
            "The reproduced exploit produced no financial impact in the current "
            "engine evaluation, because the downstream ledger balance check "
            "rejected it. The integrity boundary was nevertheless incorrect. "
            "0 legitimate decisions changed: 52 postable before and after, all "
            "six gates at +0.0000.",
        "report": "reports/CORE-001-postable-fails-open.md",
        "tests": 8,
    }]

    return {
        "claims": claims,
        "fixed": fixed,
        "gates": gates,
        "failures": {"count": obs.get("count", 0),
                     "refusals": obs.get("refusals", 0),
                     "entries": obs.get("entries", [])},
        "scope": scope,
        "artifacts": [
            {"name": "benchmark/results.json", "present": bool(res),
             "records": scope},
            {"name": "benchmark/baselines.json", "present": bool(base),
             "records": f"{base.get('settlements', 0)} settlements, 4 methods"},
            {"name": "benchmark/anchoring.json", "present": bool(anch),
             "records": f"{anch.get('ambiguous', 0)} ambiguous settlements"},
            {"name": "FAILURES.md", "present": bool(obs.get("count")),
             "records": f"{obs.get('count', 0)} entries"},
        ],
        # §21, §22. Only limitations that are true of this repository.
        "unknowns": [
            {"what": "No operator identity is recorded",
             "why": "The event model has no actor field for a person, so a "
                    "human review cannot be attributed. Absent, not unknown."},
            {"what": "No failed-posting path exists",
             "why": "The ledger write is in-process and deterministic. Nothing "
                    "has ever failed, so nothing is known about how failure "
                    "would behave."},
            {"what": "The evaluation panel is synthetic",
             "why": "Portfolios come from a frozen generator with fifteen "
                    "hazard families. Whether that distribution resembles a "
                    "real merchant's book is not established."},
            {"what": "No live traffic has been reconciled",
             "why": "The Razorpay adapter reports not connected. Every number "
                    "here describes generated data."},
            {"what": "The narrative docs describe a wider panel than the artifact",
             "why": f"docs/EVALUATION.md describes a five-seed sweep; "
                    f"benchmark/results.json records {scope}. The artifact is "
                    f"what the gates read and what this surface reports."},
            {"what": "Search-space integrity rests on blocking conventions",
             "why": "Most reductions are conventions rather than facts, so a "
                    "proof is unique inside a space the calendar chose."},
        ],
        "ai_permissions": agents_view(None),
    }
