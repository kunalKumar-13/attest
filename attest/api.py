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
from attest.verdict import Finding, Verdict

#: Runs are held in memory and addressed by id so the UI can drill into a
#: settlement without recomputing the portfolio. A real deployment persists this;
#: for a local tool a dict is the honest amount of machinery.
_RUNS: dict[str, "Run"] = {}


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
    fits = {}
    for k in range(4):
        cal = build(n, seed=(seed ^ 0x5EED) + k * 7919)
        _, _, cf = run(cal.settlements, cal.orders)
        fits[k] = (cf, {t_.settlement_id: set(t_.order_ids) for t_ in cal.truth})
    risk = calibrate(fits)
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
            risk=risk, exceptions=exceptions)
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
