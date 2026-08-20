"""The engine.

Order of work is itself an optimisation. Settlements are attempted
easiest-first -- smallest candidate pool -- because every settlement proven
removes its orders from every remaining pool. Proving the easy ones first is
constraint propagation: the hard cases are attempted against a materially
smaller search space than they would have faced in isolation, and some become
decidable only because of it.

Escalation runs the other way. A settlement is tried against the tightest date
window first; the window widens only when the verdict comes back CONTRADICTED,
which is precisely the signal that the true explanation was pruned rather than
absent. Cost is paid where the difficulty is, and the rung that succeeded is
recorded on the finding so escalation shows up in the audit trail.
"""

from __future__ import annotations

from attest.blocking import LAG_LADDER, PoolIndex
from attest.eval.harness import Prediction
from attest.evidence import to_fixed_point
from attest.layers import match_single_order
from attest.model import Order, Settlement, tolerance_paise
from attest.subsetsum import OutOfEnvelope, solve
from attest.verdict import Finding, Proof, Verdict, check


def _proof(s: Settlement, members: list[Order]) -> Proof:
    gross = sum(o.gross_paise for o in members)
    net = sum(o.net for o in members)
    return Proof(
        settlement_id=s.settlement_id,
        order_ids=tuple(o.order_id for o in members),
        gross_paise=gross,
        fee_paise=gross - net,
        tax_paise=0,
        adjustment_paise=0,
        net_paise=net,
        residual_paise=s.net_paise - net,
        tolerance_paise=tolerance_paise(len(members)),
        constraints={"amount": True, "window": True, "uniqueness": True},
    )


def run(settlements: list[Settlement], orders: list[Order]) -> tuple[
    list[Prediction], dict[str, list[Order]], list[Finding]
]:
    index = PoolIndex(orders)
    by_id = {o.order_id: o for o in orders}

    # Easiest-first. Cheap proxy for difficulty, computed once against the
    # tightest window: a settlement with few candidates is both fast to decide
    # and likely to free orders that shrink everyone else's pool.
    order_of_work = sorted(settlements, key=lambda s: len(index.pool(s, 0)))

    findings: list[Finding] = []
    preds: list[Prediction] = []
    pools_used: dict[str, list[Order]] = {}

    for s in order_of_work:
        finding: Finding | None = None

        for rung in range(len(LAG_LADDER)):
            pool = index.pool(s, rung)
            pools_used[s.settlement_id] = pool

            single = match_single_order(s, pool)
            if single is not None:
                members = [by_id[single[0]]]
                p = _proof(s, members)
                if check(p, s, by_id):
                    finding = Finding(s.settlement_id, Verdict.PROVEN, (p,),
                                      layer=f"L2-single/r{rung}")
                    break

            try:
                verdict, sols = solve(pool, s.net_paise)
            except OutOfEnvelope as exc:
                finding = Finding(s.settlement_id, Verdict.AMBIGUOUS, (),
                                  unsat_core=(f"out-of-envelope: {exc}",),
                                  layer=f"L3-skipped/r{rung}")
                break

            if verdict is Verdict.CONTRADICTED:
                continue  # pruned, not absent -- widen and retry

            proofs = tuple(
                p for p in (_proof(s, [by_id[o] for o in sol.order_ids]) for sol in sols)
                if check(p, s, by_id)
            )
            if not proofs:
                continue
            finding = Finding(
                s.settlement_id,
                Verdict.PROVEN if len(proofs) == 1 else Verdict.AMBIGUOUS,
                proofs, layer=f"L3-dp/r{rung}",
            )
            break

        if finding is None:
            finding = Finding(
                s.settlement_id, Verdict.CONTRADICTED, (),
                unsat_core=("no subset of any window satisfies the amount constraint",),
                layer="L3-dp/exhausted",
            )

        findings.append(finding)
        if finding.postable:
            index.consume(finding.proofs[0].order_ids)

        preds.append(Prediction(
            s.settlement_id,
            list(finding.proofs[0].order_ids) if finding.postable else None,
            finding.layer,
            reason="" if finding.postable else finding.verdict.value,
        ))

    # L4 -- settlements are evidence about each other. Deducing across the whole
    # population resolves cases no single-settlement search can decide.
    rounds = to_fixed_point(findings)
    promoted = sum(r.promoted for r in rounds)
    if promoted:
        print(f"  propagation: {len(rounds)} rounds, "
              f"{sum(r.killed for r in rounds)} candidates eliminated, "
              f"{promoted} settlements promoted to PROVEN")

    preds = [
        Prediction(
            f.settlement_id,
            list(f.proofs[0].order_ids) if f.postable else None,
            f.layer,
            reason="" if f.postable else f.verdict.value,
        )
        for f in findings
    ]
    return preds, pools_used, findings
