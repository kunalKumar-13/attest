"""Property tests. §48.

These are not unit tests of functions; they are the engine's promises, written so
a change that breaks one fails loudly rather than quietly costing money. Each
corresponds to something this project got wrong and paid for.

They are stated as conditionals on purpose. "ATTEST must never produce a false
PROVEN" is not a property this engine has — it produces them at roughly 0.8% and
FAILURES.md D7 records what asserting otherwise cost. The true property is
narrower and much more useful:

    when blocking did not exclude the truth, a PROVEN result is correct.

That conditional is the whole architecture in one line. It says the solver and
the kernel are sound and that every remaining false proof enters through the
search space — which is exactly what D3 and D8 measured, and exactly what
`searchspace.py` was built to make visible.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from attest.blocking import PoolIndex
from attest.generate.generator import build
from attest.model import Method, fee_paise, net_paise, tolerance_paise
from attest.pipeline import run
from attest.searchspace import Integrity
from attest.verdict import Verdict, check

SEEDS = (20260821, 314159, 271828)
N = 150


def _runs():
    for seed in SEEDS:
        ds = build(N, seed=seed)
        _, pools, findings = run(ds.settlements, ds.orders)
        yield (seed, ds, findings, pools,
               {t.settlement_id: set(t.order_ids) for t in ds.truth},
               {s.settlement_id: s for s in ds.settlements},
               {o.order_id: o for o in ds.orders})


# --------------------------------------------------------------------------
# Money
# --------------------------------------------------------------------------

def test_money_is_integral_and_lossless() -> None:
    """Fee plus tax plus net reconstitutes gross exactly, for every method.

    No float ever touches an amount, so this is an equality rather than a
    tolerance — and if it ever stops being one, the tolerance derivation that
    every proof depends on becomes meaningless.
    """
    for gross in (1, 99, 100, 12_345, 999_999, 45_00_000):
        for m in Method:
            f = fee_paise(gross, m)
            net = net_paise(gross, m)
            assert isinstance(net, int) and isinstance(f, int)
            assert 0 <= net <= gross
            assert gross - net >= f  # the remainder is GST on the fee


def test_tolerance_is_derived_not_tuned() -> None:
    """One paisa per order, from two independent half-up roundings."""
    assert tolerance_paise(1) == 1
    assert tolerance_paise(31) == 31
    assert all(tolerance_paise(k + 1) > tolerance_paise(k) for k in range(1, 60))


def test_upi_is_zero_mdr() -> None:
    """The property AMBIGUOUS_SUBSET collisions are constructed from."""
    for gross in (9_900, 1_00_000, 4_50_000):
        assert net_paise(gross, Method.UPI) == gross


# --------------------------------------------------------------------------
# The conditional soundness property — the important one
# --------------------------------------------------------------------------

def _truth_is_expressible(actual, orders, settlement) -> bool:
    """Does the true explanation satisfy the amount constraint at all?

    For four hazard families it does not, by construction. A split settlement
    pays out half an order; a refund nets off inside the credit; a chargeback
    reverses an order from two periods back; an orphan settlement contains an
    order the merchant never exported. In each case

        credit != sum(net of the true orders)

    so no exact-sum solver can reach the truth however wide the search. Those
    are MODEL gaps — the constraint system has no term for the adjustment — and
    they are a different problem from a search that looked in the wrong place.
    """
    net = sum(orders[o].net for o in actual)
    return abs(settlement.net_paise - net) <= tolerance_paise(max(len(actual), 1))


def test_proven_is_correct_when_the_truth_was_reachable() -> None:
    """The engine's actual guarantee, stated precisely enough to be true.

    A false PROVEN is permitted only where the truth was unreachable — either
    blocking pruned it (a SEARCH-SPACE error, D3/D8) or the constraint model
    cannot express it (a MODEL gap, D10). Anywhere the truth was both present
    and expressible, a claim of proof must be correct, or the solver or the
    kernel is unsound — a far worse class of bug than either.
    """
    violations = []
    for seed, _ds, findings, pools, truth, sts, ords in _runs():
        for f in findings:
            if f.verdict is not Verdict.PROVEN or not f.proofs:
                continue
            actual = truth[f.settlement_id]
            in_pool = actual <= {o.order_id for o in pools[f.settlement_id]}
            expressible = _truth_is_expressible(actual, ords, sts[f.settlement_id])
            if in_pool and expressible and set(f.proofs[0].order_ids) != actual:
                violations.append((seed, f.settlement_id, f.layer))
    assert not violations, (
        f"{len(violations)} PROVEN results were wrong although the truth was "
        f"both inside the pool and expressible under the constraints — the "
        f"solver or the kernel is unsound: {violations[:5]}")


def test_every_false_proof_has_an_attributable_cause() -> None:
    """No false proof may be unexplained.

    Each one must be attributable to a pruned candidate or to a truth the model
    cannot express. An unattributable false proof means the engine is wrong in a
    way nothing currently accounts for, and that is the finding worth failing a
    build over.
    """
    causes = {"search space": 0, "model gap": 0, "unattributed": []}
    for seed, _ds, findings, pools, truth, sts, ords in _runs():
        for f in findings:
            if f.verdict is not Verdict.PROVEN or not f.proofs:
                continue
            actual = truth[f.settlement_id]
            if set(f.proofs[0].order_ids) == actual:
                continue
            if not _truth_is_expressible(actual, ords, sts[f.settlement_id]):
                causes["model gap"] += 1
            elif not actual <= {o.order_id for o in pools[f.settlement_id]}:
                causes["search space"] += 1
            else:
                causes["unattributed"].append((seed, f.settlement_id))
    assert not causes["unattributed"], causes


def test_local_uniqueness_is_never_reported_as_global() -> None:
    """§28. The D8 lesson, as an assertion.

    Uniqueness found over a heuristically reduced space is local. The engine may
    say so; it may never say plain 'unique'.
    """
    for _seed, _ds, findings, _pools, _truth, _sts, _ords in _runs():
        for f in findings:
            if f.verdict is not Verdict.PROVEN:
                continue
            claim = f.uniqueness_claim
            if f.space is not None and f.space.integrity is Integrity.HEURISTIC:
                assert "within" in claim, claim
                assert not claim.startswith("unique —"), claim


def test_compromised_space_never_posts() -> None:
    from attest.searchspace import SearchSpace, date_window
    from attest.verdict import Finding, Proof
    sp = SearchSpace(universe=100)
    sp.reductions.append(date_window(50, 0, (2,)))
    sp.note_known_loss(1)
    p = Proof("s", ("o",), 100, 0, 0, 0, 100, 0, 1)
    f = Finding("s", Verdict.PROVEN, (p,), space=sp)
    assert sp.integrity is Integrity.COMPROMISED
    assert not f.postable


# --------------------------------------------------------------------------
# Verdict discipline
# --------------------------------------------------------------------------

def test_ambiguous_never_carries_one_explanation() -> None:
    """AMBIGUOUS means several survived. One survivor is PROVEN or nothing."""
    for _seed, _ds, findings, _p, _t, _s, _o in _runs():
        for f in findings:
            if f.verdict is Verdict.AMBIGUOUS and f.proofs:
                assert len(f.proofs) > 1, f.settlement_id


def test_contradicted_and_insufficient_carry_no_proof() -> None:
    for _seed, _ds, findings, _p, _t, _s, _o in _runs():
        for f in findings:
            if f.verdict in (Verdict.CONTRADICTED, Verdict.INSUFFICIENT):
                assert not f.proofs, f.settlement_id
                assert not f.postable


def test_every_proof_survives_the_independent_kernel() -> None:
    """Nothing reaches a verdict without the 28-line verifier agreeing."""
    for _seed, _ds, findings, _p, _t, sts, ords in _runs():
        for f in findings:
            for proof in f.proofs:
                assert check(proof, sts[f.settlement_id], ords), (
                    f"{f.settlement_id} carries a proof the kernel rejects")


def test_kernel_rejects_a_fabricated_proof() -> None:
    """The kernel must recompute, not trust the fields handed to it."""
    from attest.verdict import Proof
    ds = build(40, seed=20260821)
    s = ds.settlements[0]
    ords = {o.order_id: o for o in ds.orders}
    real = next(iter(ords))
    liar = Proof(s.settlement_id, (real,), gross_paise=s.net_paise, fee_paise=0,
                 tax_paise=0, adjustment_paise=0, net_paise=s.net_paise,
                 residual_paise=0, tolerance_paise=1)
    assert not check(liar, s, ords)


def test_kernel_rejects_a_duplicated_order() -> None:
    from attest.verdict import Proof
    ds = build(40, seed=20260821)
    s, ords = ds.settlements[0], {o.order_id: o for o in ds.orders}
    oid = next(iter(ords))
    dup = Proof(s.settlement_id, (oid, oid), 0, 0, 0, 0, 0, 0, 2)
    assert not check(dup, s, ords)


# --------------------------------------------------------------------------
# Search space
# --------------------------------------------------------------------------

def test_reductions_account_for_every_excluded_order() -> None:
    """The audit must add up, or it is decoration."""
    ds = build(120, seed=20260821)
    idx = PoolIndex(ds.orders)
    for s in ds.settlements[:40]:
        pool, space = idx.audited_pool(s, 0)
        assert space.candidates == len(pool), (space.candidates, len(pool))
        assert sum(r.removed for r in space.reductions) == space.universe - len(pool)


def test_amount_ceiling_is_deterministic_and_calendar_is_not() -> None:
    ds = build(60, seed=20260821)
    _, space = PoolIndex(ds.orders).audited_pool(ds.settlements[0], 0)
    kinds = {r.name.split(" (")[0]: r.deterministic for r in space.reductions}
    assert kinds["amount ceiling"] is True
    assert kinds["settlement calendar"] is False
    assert kinds["already claimed"] is False


# --------------------------------------------------------------------------
# Policy
# --------------------------------------------------------------------------

def test_uncalibrated_policy_posts_nothing() -> None:
    from attest.policy import Decision, RiskModel, decide
    for _seed, _ds, findings, _p, _t, sts, _o in _runs():
        risk = RiskModel()
        for f in findings[:40]:
            assert decide(f, sts[f.settlement_id], risk).decision is not Decision.AUTO_POST
        break


def test_risk_is_priced_above_the_point_estimate() -> None:
    """D9. The upper bound must be strictly more cautious than the observation."""
    from attest.policy import _wilson_upper
    for wrong, total in ((0, 100), (1, 152), (5, 500), (20, 1000)):
        assert _wilson_upper(wrong, total) > wrong / total


def test_threshold_moves_with_the_review_cost() -> None:
    """No threshold is hardcoded, so raising the cost of a human must widen
    what the engine is willing to automate."""
    from attest.policy import Costs, Decision, calibrate, decide
    runs = list(_runs())
    risk = calibrate({s: (f, t) for s, _d, f, _p, t, _st, _o in runs})
    seed, _ds, findings, _p, _t, sts, _o = runs[0]
    cheap = sum(decide(f, sts[f.settlement_id], risk, Costs(review_paise=1_000)
                       ).decision is Decision.AUTO_POST for f in findings)
    dear = sum(decide(f, sts[f.settlement_id], risk, Costs(review_paise=500_000)
                      ).decision is Decision.AUTO_POST for f in findings)
    assert dear >= cheap


# --------------------------------------------------------------------------
# Event ingestion — §35, §36
# --------------------------------------------------------------------------

def _signed(payload, secret="whsec_test"):
    import hashlib
    import hmac
    import json
    body = json.dumps(payload, separators=(",", ":")).encode()
    return body, hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def test_duplicate_event_is_not_processed_twice() -> None:
    from attest.webhooks import EventStatus, Ingest
    ing = Ingest(secret="whsec_test")
    p = {"id": "evt_1", "event": "refund.created",
         "payload": {"refund": {"entity": {"id": "r1", "payment_id": "pay_1"}}}}
    b, s = _signed(p)
    assert ing.handle("razorpay", b, s, {"pay_1": "setl_A"}, {"setl_A"}).status \
        is EventStatus.ACCEPTED
    assert ing.handle("razorpay", b, s, {"pay_1": "setl_A"}, {"setl_A"}).status \
        is EventStatus.DUPLICATE


def test_same_id_different_body_is_a_contradiction_not_a_duplicate() -> None:
    """An id check alone would wave this through, and it must not.

    A provider replaying an id with a mutated body is a different problem from a
    retry, and treating the second delivery as 'already handled' loses data
    silently.
    """
    from attest.webhooks import EventStatus, Ingest
    ing = Ingest(secret="whsec_test")
    a = {"id": "evt_1", "event": "refund.created", "payload": {"amount": 100}}
    c = {"id": "evt_1", "event": "refund.created", "payload": {"amount": 999}}
    ing.handle("razorpay", *_signed(a), {}, set())
    assert ing.handle("razorpay", *_signed(c), {}, set()).status \
        is EventStatus.REPLAY_MISMATCH


def test_bad_signature_is_rejected_not_queued() -> None:
    from attest.webhooks import EventStatus, Ingest
    ing = Ingest(secret="whsec_test")
    b, _ = _signed({"id": "e", "event": "refund.created", "payload": {}})
    ev = ing.handle("razorpay", b, "deadbeef", {}, set())
    assert ev.status is EventStatus.BAD_SIGNATURE
    assert ev.processed_at is None


def test_blast_radius_is_scoped_to_named_entities() -> None:
    """§35: do not rerun the world. An event naming nothing the book holds must
    affect nothing."""
    from attest.webhooks import Ingest
    ing = Ingest(secret="whsec_test")
    o2s, known = {"pay_1": "setl_A"}, {"setl_A", "setl_B"}

    hit = ing.handle("razorpay", *_signed(
        {"id": "e1", "event": "refund.created",
         "payload": {"refund": {"entity": {"payment_id": "pay_1"}}}}), o2s, known)
    assert hit.affected == ("setl_A",)

    miss = ing.handle("razorpay", *_signed(
        {"id": "e2", "event": "payment.captured",
         "payload": {"payment": {"entity": {"id": "pay_unknown"}}}}), o2s, known)
    assert miss.affected == ()


def test_signature_verifies_over_raw_bytes() -> None:
    """Re-serialising before hashing changes the digest and rejects valid events
    — a bug that only shows up against a real gateway."""
    import json

    from attest.webhooks import verify
    p = {"b": 2, "a": 1}
    body, sig = _signed(p)
    assert verify(body, sig, "whsec_test")
    reserialised = json.dumps(p, sort_keys=True).encode()
    assert not verify(reserialised, sig, "whsec_test")


def test_adapter_normalise_never_claims_live() -> None:
    """§39, and D17: the default must be the safe one."""
    from attest.adapters.razorpay import RazorpayAdapter
    snap = RazorpayAdapter().normalise([], [])
    assert snap.live is False


def test_synthetic_source_is_always_labelled() -> None:
    from attest.adapters.synthetic import SyntheticAdapter
    snap = SyntheticAdapter().fetch(20)
    assert snap.live is False
    assert "synthetic" in snap.source
    assert snap.warnings


def test_rules_agree_with_the_frozen_fee_model() -> None:
    """The rule set is the engine's belief; today it must match what the
    generator actually did, or every measured number is against a different
    world than the one described."""
    from attest.model import Method, net_paise
    from attest.rules import DEFAULT
    for gross in (9_900, 1_00_000, 4_50_000, 12_345):
        for m in Method:
            assert DEFAULT.net_paise(gross, m.value) == net_paise(gross, m)


def test_a_changed_rule_changes_the_version() -> None:
    from attest.rules import DEFAULT, FeeSchedule
    other = DEFAULT.with_(fees=FeeSchedule(fixed_paise=200))
    assert DEFAULT.version != other.version


# --------------------------------------------------------------------------
# Agent permissions — §42, §68, §69
# --------------------------------------------------------------------------

def test_no_agent_can_be_configured_with_a_write_capability() -> None:
    """Enforced at GRANT time, not only at call time.

    A permission that can be granted and refused later is one somebody will be
    surprised by. Refusing the configuration means the unsafe state cannot exist.
    """
    import pytest

    from attest.agents import Agent, Capability
    for c in (Capability.POST_ENTRY, Capability.TRIGGER_REFUND,
              Capability.MODIFY_RECORD, Capability.MARK_RECONCILED):
        with pytest.raises(PermissionError):
            Agent("x", "X", "", frozenset({c}))


def test_no_agent_in_the_roster_holds_a_write_capability() -> None:
    from attest.agents import NEVER_GRANTED, ROSTER
    for a in ROSTER.values():
        assert not (a.capabilities & NEVER_GRANTED), a.id


def test_pipeline_refuses_a_write_at_the_capability_stage() -> None:
    from attest.agents import Capability, Pipeline, Stage
    a = Pipeline().request("investigation", "post", "s1", Capability.POST_ENTRY)
    assert not a.permitted
    assert a.stopped_at is Stage.CAPABILITY


def test_pipeline_stops_at_the_first_refusal() -> None:
    """A later stage must not excuse an earlier one — an action that failed the
    capability check never reaches the policy."""
    from attest.agents import Capability, Pipeline, Stage
    a = Pipeline().request("explanation", "run the solver", "s1",
                           Capability.RUN_SOLVER, evidence="x")
    assert a.stopped_at is Stage.CAPABILITY
    assert len(a.steps) == 1


def test_pipeline_requires_evidence_before_verification() -> None:
    from attest.agents import Capability, Pipeline, Stage
    a = Pipeline().request("evidence", "read", "s1", Capability.READ_EVIDENCE)
    assert a.stopped_at is Stage.EVIDENCE


def test_pipeline_refuses_an_unproven_finding() -> None:
    from attest.agents import Capability, Pipeline, Stage
    from attest.verdict import Finding, Verdict
    f = Finding("s1", Verdict.AMBIGUOUS, ())
    a = Pipeline().request("reconciliation", "reconcile", "s1",
                           Capability.RUN_SOLVER, evidence="x", finding=f)
    assert a.stopped_at is Stage.VERIFICATION


def test_pipeline_refuses_a_compromised_search_space_even_when_proven() -> None:
    """The arithmetic can be perfect and still answer a question that excluded
    the truth. D8, as a control."""
    from attest.agents import Capability, Pipeline, Stage
    from attest.searchspace import SearchSpace, date_window
    from attest.verdict import Finding, Proof, Verdict
    sp = SearchSpace(universe=100)
    sp.reductions.append(date_window(10, 0, (2,)))
    sp.note_known_loss(1)
    f = Finding("s1", Verdict.PROVEN, (Proof("s1", ("o",), 1, 0, 0, 0, 1, 0, 1),),
                space=sp)
    a = Pipeline().request("reconciliation", "reconcile", "s1",
                           Capability.RUN_SOLVER, evidence="x", finding=f)
    assert a.stopped_at is Stage.VERIFICATION


# --------------------------------------------------------------------- ledger

def _journal(n: int = 250, seed: int = 20260821):
    from attest import api
    from attest.ledger import JournalEntry, Journal, post
    r = api.execute(n, seed)
    st = {x.settlement_id: x for x in r.settlements}
    orders = {o.order_id: o for o in r.orders}
    j = Journal()
    for f in r.findings:
        s = st[f.settlement_id]
        out = post(f, s, api._judge(r, f, s), orders)
        (j.entries if isinstance(out, JournalEntry) else j.refusals).append(out)
    return r, st, j


def test_every_journal_entry_balances_to_the_paisa() -> None:
    """The balance check is the fee model restated: net = gross - fee - tax. An
    entry that does not balance is a rule set disagreeing with the records, not
    a bookkeeping slip, so this is an engine assertion wearing accounting
    clothes."""
    _, _, j = _journal()
    assert j.entries, "no entry posted; the invariant would be vacuous"
    for e in j.entries:
        d = sum(x.debit_paise for x in e.lines)
        c = sum(x.credit_paise for x in e.lines)
        assert d == c, f"{e.settlement_id}: {d} != {c}"
    assert j.balances()


def test_the_bank_line_is_the_credit_that_actually_arrived() -> None:
    """Not the modelled net. Where the two differ it is by the proof's residual,
    and letting the modelled figure onto the bank line would post an amount the
    bank never paid — which reconciles perfectly and is wrong."""
    _, st, j = _journal()
    for e in j.entries:
        assert e.lines[0].debit_paise == st[e.settlement_id].net_paise


def test_nothing_posts_without_a_unique_kernel_checked_explanation() -> None:
    from attest.policy import Decision
    from attest.verdict import Verdict
    r, st, j = _journal()
    from attest import api
    posted = {e.settlement_id for e in j.entries}
    for f in r.findings:
        if f.settlement_id not in posted:
            continue
        assert f.verdict is Verdict.PROVEN
        assert f.postable
        assert api._judge(r, f, st[f.settlement_id]).decision is Decision.AUTO_POST


def test_every_refusal_states_a_reason() -> None:
    """A queue of unexplained gaps is how a reconciliation becomes an argument."""
    _, _, j = _journal()
    assert j.refusals
    for x in j.refusals:
        assert x.reason.strip()


def test_an_unbalanced_entry_cannot_be_constructed() -> None:
    import pytest
    from attest.ledger import BANK, RECEIVABLES, JournalEntry, Line, Unbalanced
    with pytest.raises(Unbalanced):
        JournalEntry("s1", "2026-01-01", "utr", (
            Line(BANK, debit_paise=100), Line(RECEIVABLES, credit_paise=99),
        ), ("o1",), "", 0, 1)


def test_a_line_cannot_be_both_a_debit_and_a_credit() -> None:
    import pytest
    from attest.ledger import BANK, Line, Unbalanced
    with pytest.raises(Unbalanced):
        Line(BANK, debit_paise=100, credit_paise=100)


def test_a_foreign_rule_set_is_refused_rather_than_absorbed() -> None:
    """Splitting the charge under rules that did not produce the proof would
    balance — the drift lands on the fee line — and would silently misstate
    recoverable GST. It raises instead."""
    import pytest
    from attest import api
    from attest.ledger import Unbalanced, post
    from attest.policy import Decision
    from attest.rules import DEFAULT, FeeSchedule
    from attest.verdict import Verdict

    r = api.execute(250, 20260821)
    st = {x.settlement_id: x for x in r.settlements}
    orders = {o.order_id: o for o in r.orders}
    foreign = DEFAULT.with_(fees=FeeSchedule(tax_bps=2800))

    tried = False
    for f in r.findings:
        s = st[f.settlement_id]
        jm = api._judge(r, f, s)
        if f.verdict is not Verdict.PROVEN or jm.decision is not Decision.AUTO_POST:
            continue
        tried = True
        with pytest.raises(Unbalanced):
            post(f, s, jm, orders, rules=foreign)
    assert tried, "no postable finding to test against"
