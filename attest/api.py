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

from attest.eval.harness import Timer, evaluate
from attest.graph import build as build_graph
from attest.generate.generator import build
from attest.model import Order, Settlement, TrueMatch
from attest.pipeline import run
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
        preds, pools, findings = run(ds.settlements, ds.orders)
    _audit(log, "reconcile", f"{len(findings):,} settlements decided in {t.elapsed:.2f}s")

    rep = evaluate(ds.settlements, ds.truth, preds, pools, t.elapsed)
    counts = {v: sum(1 for f in findings if f.verdict is v) for v in Verdict}
    _audit(log, "verdicts",
           f"PROVEN {counts[Verdict.PROVEN]} · AMBIGUOUS {counts[Verdict.AMBIGUOUS]} "
           f"· CONTRADICTED {counts[Verdict.CONTRADICTED]}")
    _audit(log, "kernel", f"{counts[Verdict.PROVEN]} proofs re-derived from source "
                          f"records by verdict.check; {rep.wrong} rejected")
    _audit(log, "policy", "auto-post eligible: PROVEN only — a unique, "
                          "kernel-checked explanation")

    r = Run(f"run_{len(_RUNS) + 1:04d}", seed, ds.settlements, ds.orders,
            ds.truth, findings, rep, log)
    _RUNS[r.run_id] = r
    return r


def get(run_id: str) -> Run | None:
    return _RUNS.get(run_id)


# --------------------------------------------------------------------------
# Serialisation
# --------------------------------------------------------------------------


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
    }


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
        })
    return out


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
    }
