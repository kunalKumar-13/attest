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

import pytest

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


# -------------------------------------------------------------------- actions

def test_a_systemic_action_is_one_step_however_many_settlements() -> None:
    """The whole point of the ranking. 197 settlements ambiguous for the same
    missing field is one piece of work, and calling it 197 puts a one-line
    change below a week of individual investigations."""
    from attest import api
    from attest.actions import Kind, plan
    r = api.execute(250, 20260821)
    amounts = {s.settlement_id: s.net_paise for s in r.settlements}
    acts = plan(r.exceptions, amounts)
    assert acts
    for a in acts:
        if a.kind is Kind.PER_ITEM:
            assert a.steps == a.settlements
        else:
            assert a.steps == 1


def test_actions_rank_by_leverage_not_by_volume() -> None:
    from attest import api
    from attest.actions import plan
    r = api.execute(250, 20260821)
    amounts = {s.settlement_id: s.net_paise for s in r.settlements}
    acts = plan(r.exceptions, amounts)
    lev = [a.leverage_paise for a in acts]
    assert lev == sorted(lev, reverse=True)


def test_every_exception_reason_has_a_classification() -> None:
    """A reason with no entry silently defaults to per-item, which understates
    leverage for anything systemic. The taxonomy is frozen, so this can be
    exhaustive."""
    from attest.actions import KINDS
    from attest.exceptions import GUIDE, ReasonCode
    for code in ReasonCode:
        assert code in KINDS, f"{code.value} has no action classification"
        assert code in GUIDE, f"{code.value} has no next step"
        assert KINDS[code][1].strip(), f"{code.value} has no rationale"


# ------------------------------------------------------- subject × lens shell

def test_every_lens_declares_which_subjects_it_serves() -> None:
    """A lens missing from the matrix is invisible everywhere; a subject type
    missing from every lens is a subject you can select and then cannot look
    at."""
    from attest.api import LENS_LABELS, LENS_MATRIX
    assert set(LENS_MATRIX) == set(LENS_LABELS)
    served = {t for ts in LENS_MATRIX.values() for t in ts}
    for t in ("portfolio", "settlement", "action", "source"):
        assert t in served, f"{t} has no lens"
    for k, (label, question) in LENS_LABELS.items():
        assert label and question.endswith("?"), f"{k} must state its question"


def test_portfolio_and_settlement_share_a_lens_set() -> None:
    """The commonest transition in the product is clicking a settlement while a
    lens is open. If the two subject types disagree about which lenses exist,
    the strip changes shape underneath that click — and the one promise the
    transition makes is that it does not."""
    from attest.api import lenses_for
    p = [x["key"] for x in lenses_for("portfolio")]
    s = [x["key"] for x in lenses_for("settlement")]
    assert p == s, f"strip would reshape on subject change: {p} vs {s}"


def test_a_subject_record_has_the_same_shape_whatever_it_is() -> None:
    """One header renders all of them, so they must agree on their fields."""
    from attest import api
    r = api.execute(120, 7)
    ids = {"portfolio": "", "settlement": r.findings[0].settlement_id,
           "source": ""}
    for t, i in ids.items():
        d = api.subject_view(r, t, i)
        assert "error" not in d, d
        for key in ("type", "id", "label", "meta", "lenses"):
            assert key in d, f"{t} record is missing {key}"
        assert isinstance(d["meta"], list) and d["meta"]
        assert d["type"] == t


def test_the_spine_is_five_stages_for_every_subject() -> None:
    from attest import api
    r = api.execute(120, 7)
    for t, i in [("portfolio", ""), ("settlement", r.findings[0].settlement_id)]:
        d = api.spine_view(r, t, i)
        assert [x["key"] for x in d["stages"]] == \
            ["source", "matching", "verification", "policy", "action"]
        for x in d["stages"]:
            assert x["state"] in ("passed", "stopped", "not_reached")
            assert x["detail"].strip()


def test_a_stage_after_the_stopping_point_is_never_marked_passed() -> None:
    """The spine's whole claim is that it shows where value is standing. A stage
    downstream of a refusal that reports success is the claim being false."""
    from attest import api
    from attest.verdict import Verdict
    r = api.execute(250, 20260821)
    order = ["source", "matching", "verification", "policy", "action"]
    checked = 0
    for f in r.findings:
        if f.verdict is Verdict.PROVEN:
            continue
        d = api.spine_view(r, "settlement", f.settlement_id)
        stop = d["stopped_at"]
        if stop is None:
            continue
        checked += 1
        after = order[order.index(stop) + 1:]
        for x in d["stages"]:
            if x["key"] in after:
                assert x["state"] != "passed", \
                    f"{f.settlement_id}: {x['key']} passed after {stop} stopped"
    assert checked > 10, "not enough stopped settlements to make this meaningful"


def test_the_portfolio_spine_marks_a_stage_that_holds_value() -> None:
    from attest import api
    d = api.spine_view(api.execute(250, 20260821), "portfolio", "")
    for x in d["stages"]:
        if x.get("held"):
            assert x["state"] == "stopped", \
                f"{x['key']} holds {x['held']} settlements but reports {x['state']}"


# ----------------------------------------------------------- claim integrity

def test_every_registered_claim_reads_from_its_artifact() -> None:
    """§8.1. A claim marked MEASURED whose artifact is missing is a claim
    nothing checks, which is how a precision figure survived six days past the
    measurement that refuted it."""
    from attest.eval.claims import REGISTER, value
    for c in REGISTER:
        if c.status != "MEASURED":
            continue
        v = value(c)
        assert v is not None and v != {}, \
            f"{c.id} is MEASURED but {c.artifact}{list(c.path)} is absent"


def test_no_percentage_in_the_readme_is_unaccounted_for() -> None:
    """The check that makes the register load-bearing rather than decorative."""
    from attest.eval.claims import audit
    a = audit()
    bad = [f for f in a.findings if f.kind != "note"]
    assert not bad, "\n".join(f"{f.where}: {f.detail}" for f in bad)


def test_the_readme_blocks_match_the_artifacts() -> None:
    """Regenerating must be a no-op. If it is not, the prose has drifted."""
    import pathlib

    from attest.eval.claims import MARK_BASELINES, MARK_RESULTS, ROOT, \
        render_baselines, render_results
    s = (ROOT / "README.md").read_text()
    for (start, end), body, name in ((MARK_RESULTS, render_results(), "results"),
                                     (MARK_BASELINES, render_baselines(), "baselines")):
        assert start in s, f"the {name} block is not generated"
        i = s.index(start) + len(start)
        j = s.index(end, i)
        assert s[i:j] == f"\n{body}\n", \
            f"the {name} block has drifted from its artifact"


def test_the_canonical_panel_is_the_held_out_seeds() -> None:
    """§8.2. Three of the five seeds fit the risk model. Evaluating on all five
    would report the policy's memory as its accuracy — D14."""
    from attest.eval.benchmark import CALIBRATION_SEEDS, EVALUATION_SEEDS
    assert not set(CALIBRATION_SEEDS) & set(EVALUATION_SEEDS)
    assert len(EVALUATION_SEEDS) >= 2


def test_the_baseline_panel_uses_the_evaluation_seeds() -> None:
    """§31 of the Trust brief: same dataset, same scoring, or the comparison
    means nothing."""
    from attest.eval.baseline_panel import SEEDS
    from attest.eval.benchmark import EVALUATION_SEEDS
    assert tuple(SEEDS) == tuple(EVALUATION_SEEDS)


def test_no_deciding_path_computes_money_in_floating_point() -> None:
    """§8.9. A ratio that gets printed is not a decision; an amount that moves
    is. This walks only the functions that decide."""
    import ast
    import pathlib

    deciders = {
        "attest/verdict.py": {"check"},
        "attest/subsetsum.py": {"solve", "_reachable"},
        "attest/ledger.py": {"post"},
        "attest/model.py": {"fee_paise", "tax_paise", "net_paise",
                            "tolerance_paise", "_round_half_up"},
    }
    bad: list[str] = []
    for path, names in deciders.items():
        tree = ast.parse(pathlib.Path(path).read_text())
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef) or node.name not in names:
                continue
            for n in ast.walk(node):
                if isinstance(n, ast.Constant) and isinstance(n.value, float):
                    bad.append(f"{path}:{n.lineno} float literal in {node.name}")
                if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Div):
                    bad.append(f"{path}:{n.lineno} true division in {node.name}: "
                               f"{ast.unparse(n)[:50]}")
    assert not bad, "\n".join(bad)


def test_expected_loss_rounds_toward_checking_not_toward_posting() -> None:
    """The one float that touches money. Truncating down understates the loss
    and makes auto-posting more likely; it must round up."""
    import math

    from attest import api
    from attest.policy import Costs, decide
    from attest.verdict import Verdict

    r = api.execute(250, 20260821)
    st = {x.settlement_id: x for x in r.settlements}
    costs = Costs()
    checked = 0
    for f in r.findings:
        if f.verdict is not Verdict.PROVEN:
            continue
        s = st[f.settlement_id]
        j = decide(f, s, r.risk, costs)
        exact = j.p_error * costs.wrong_post(s.net_paise)
        assert j.expected_loss_paise == math.ceil(exact), \
            f"{f.settlement_id}: {j.expected_loss_paise} != ceil({exact})"
        checked += 1
    assert checked > 10


# ------------------------------------------------------- the AI boundary (§8.13)

def test_no_model_output_can_reach_a_posting_without_the_deterministic_chain() -> None:
    """§8.13, attempted as an attack rather than asserted as a property.

    Hand the ledger a finding whose PROVEN verdict came from a model rather than
    from the solver, and require it to refuse. The refusal must come from the
    structure — postable, kernel-checked, policy-cleared — and not from anything
    inspecting where the finding came from, because a real attacker would not
    label it."""
    from attest import api
    from attest.ledger import Refusal, post
    from attest.policy import Costs, Decision, Judgement
    from attest.verdict import Finding, Proof, Verdict

    r = api.execute(120, 7)
    s = r.settlements[0]
    orders = {o.order_id: o for o in r.orders}
    oid = next(iter(orders))

    # A forged proof: correct shape, plausible numbers, never near the solver.
    forged = Finding(s.settlement_id, Verdict.PROVEN,
                     (Proof(s.settlement_id, (oid,), 1, 0, 0, 0, 1, 0, 1),))
    permissive = Judgement(Decision.AUTO_POST, 0, 0.0, ("model says so",))

    # Before CORE-001 was fixed this was stopped by `Unbalanced` in the entry
    # arithmetic — defence in depth rather than the gate that exists for it.
    # The integrity boundary refuses it now, and the reason names the search
    # space rather than the sum.
    out = post(forged, s, permissive, orders)
    assert isinstance(out, Refusal), "a forged proof reached the ledger"
    assert "search space" in out.reason.lower(), \
        f"refused, but not by the integrity gate: {out.reason!r}"


def test_a_model_verdict_cannot_pass_the_agent_pipeline() -> None:
    """The same attempt through the permission pipeline rather than the ledger."""
    from attest.agents import Capability, Pipeline, Stage
    from attest.verdict import Finding, Proof, Verdict

    forged = Finding("s1", Verdict.PROVEN,
                     (Proof("s1", ("o1",), 1, 0, 0, 0, 1, 0, 1),))
    a = Pipeline().request("investigation", "post the entry", "s1",
                           Capability.POST_ENTRY, evidence="a model said so",
                           finding=forged)
    assert a.stopped_at is Stage.CAPABILITY
    assert not any(s.stage is Stage.ACTION and s.passed for s in a.steps)


def test_the_hypothesis_loop_cannot_return_a_proof_the_solver_did_not_make() -> None:
    """falsify() may only SELECT among proofs the solver produced over the full
    pool. A hypothesis naming orders outside them must be refuted, whatever it
    claims."""
    from attest.hypothesis import Hypothesis, falsify
    from attest import api
    from attest.verdict import Verdict

    r = api.execute(120, 7)
    st = {x.settlement_id: x for x in r.settlements}
    f = next(x for x in r.findings if x.verdict is Verdict.AMBIGUOUS)
    orders = {o.order_id: o for o in r.pools[f.settlement_id]}

    ghost = Hypothesis(order_ids=("ord_does_not_exist",), lens="attack",
                       reasoning="a model asserted this", admits_missing=())
    proof, refutation = falsify(ghost, st[f.settlement_id], orders, f.proofs)
    assert proof is None
    assert refutation is not None and refutation.constraint == "existence"


# ------------------------------------------------------------------ CORE-001
#
# A PROVEN finding may only become postable if the system can answer four
# questions about it: what search space was proved, which candidate universe
# was considered, which solver produced the proof, and whether the proof belongs
# to that universe. Each test below removes exactly one of those answers.
#
# The property used to return True when `space` was absent, so a finding was
# postable *because* it omitted the evidence it would have been judged on.


def _space(universe: int = 100, removed: int = 40, deterministic: bool = True,
           members=("o1", "o2", "o3", "o4", "o5")):
    from attest.searchspace import Reduction, SearchSpace
    sp = SearchSpace(universe=universe, members=frozenset(members))
    sp.reductions.append(Reduction("test reduction", removed, deterministic,
                                   "constructed for a test"))
    return sp


def _proven(space=None, layer="L3-dp/r0", orders=("o1",)):
    from attest.verdict import Finding, Proof, Verdict
    return Finding("s1", Verdict.PROVEN,
                   (Proof("s1", orders, 1000, 0, 0, 0, 1000, 0, len(orders)),),
                   space=space, layer=layer)


def test_core001_a_proof_without_search_space_provenance_cannot_post() -> None:
    """Test A. The original CORE-001 exploit: PROVEN, plausible arithmetic, no
    recorded search space."""
    f = _proven(space=None)
    assert f.space is None
    assert not f.postable


def test_core001_a_legitimate_proof_still_posts() -> None:
    """Test B. Failing closed is only correct if it does not close on the
    truth."""
    assert _proven(space=_space()).postable


def test_core001_a_fabricated_space_that_is_not_a_record_cannot_post() -> None:
    """Test C. The check must not be satisfiable by putting *something* in the
    field — a string, an id, a dict that looks like provenance."""
    for fake in ("space_0001", {"universe": 100, "candidates": 60}, 12345, object()):
        assert not _proven(space=fake).postable, f"{fake!r} was accepted"


def test_core001_a_space_recording_no_universe_cannot_post() -> None:
    """Test D, first half. A SearchSpace of the right type that recorded no
    universe and no reductions describes no search that happened."""
    from attest.searchspace import SearchSpace
    assert not _proven(space=SearchSpace(universe=0)).postable
    assert not _proven(space=SearchSpace(universe=100)).postable   # no reductions


def test_core001_a_proof_with_no_solver_provenance_cannot_post() -> None:
    """Test D, second half. `layer` names the solver that resolved it; empty
    names none."""
    assert not _proven(space=_space(), layer="").postable


def test_core001_a_proof_larger_than_its_candidate_universe_cannot_post() -> None:
    """Test E. Certificate integrity: alter the selected records so the proof
    cites orders the space never held."""
    sp = _space(universe=100, removed=95)          # members o1..o5
    too_many = tuple(f"o{i}" for i in range(9))
    assert sp.candidates == 5
    assert not _proven(space=sp, orders=too_many).postable
    assert _proven(space=sp, orders=("o1", "o2")).postable


# ------------------------------------------------------------------ CORE-002
#
# Condition 4 originally compared CARDINALITY. Two invented ids against five
# candidates satisfies `len(order_ids) <= candidates` while belonging to no
# search that ever happened, so the gate could be passed by counting rather
# than by membership.


def test_core002_cited_orders_must_belong_to_the_candidate_universe() -> None:
    """The membership attack. Every structural condition satisfied — a real
    SearchSpace, a universe, recorded reductions, a named solver, and a proof
    small enough — but the cited orders were never candidates."""
    sp = _space(members=("A", "B", "C", "D", "E"))
    assert sp.candidates >= 2
    forged = _proven(space=sp, orders=("X", "Y"))
    assert len(forged.proofs[0].order_ids) <= sp.candidates, \
        "the attack must satisfy the cardinality check to be meaningful"
    assert not forged.postable


def test_core002_a_single_foreign_order_is_enough_to_refuse() -> None:
    """Membership is not a majority vote."""
    sp = _space(members=("A", "B", "C"))
    assert _proven(space=sp, orders=("A", "B")).postable
    assert not _proven(space=sp, orders=("A", "X")).postable


def test_core002_a_space_recording_no_members_cannot_post() -> None:
    """A count without a membership set is not a record of a search."""
    sp = _space(members=())
    assert not _proven(space=sp, orders=("o1",)).postable


def test_core002_every_engine_proof_sits_inside_its_recorded_members() -> None:
    """Failing closed on membership is only safe if blocking records it. It is
    populated at the one construction site, from the pool itself."""
    from attest import api
    from attest.searchspace import SearchSpace
    from attest.verdict import Verdict

    r = api.execute(250, 20260821)
    proven = [f for f in r.findings if f.verdict is Verdict.PROVEN]
    assert proven
    for f in proven:
        assert isinstance(f.space, SearchSpace)
        assert f.space.members, f"{f.settlement_id}: space records no members"
        assert set(f.proofs[0].order_ids) <= f.space.members, \
            f"{f.settlement_id}: proof cites orders outside its own pool"


def test_core001_a_compromised_space_still_cannot_post() -> None:
    """The original D8 condition must survive the fix."""
    sp = _space()
    sp.note_known_loss(1)
    assert not _proven(space=sp).postable


def test_the_engine_still_attaches_a_search_space_to_every_proof() -> None:
    """The other half: failing closed is only safe if the engine actually
    records what it is being asked for."""
    from attest import api
    from attest.searchspace import SearchSpace
    from attest.verdict import Verdict

    r = api.execute(250, 20260821)
    proven = [f for f in r.findings if f.verdict is Verdict.PROVEN]
    assert proven
    for f in proven:
        assert isinstance(f.space, SearchSpace), \
            f"{f.settlement_id} is proven with no search-space record"
        assert f.space.reductions, "a space with no recorded reductions"


# ----------------------------------------------------- the Razorpay adapter

def _recon_row(**kw):
    base = {"entity_id": "pay_1", "settlement_id": "setl_1", "type": "payment",
            "credit": 1000, "debit": 0, "fee": 20, "tax": 4, "amount": 1024,
            "method": "upi", "order_id": "ord_1", "payment_id": "pay_1",
            "created_at": 1747000000, "settled_at": 1747200000,
            "settlement_utr": "UTR1"}
    base.update(kw)
    return base


def test_adapter001_the_same_recon_row_twice_does_not_inflate_a_settlement() -> None:
    """ADAPTER-001. Rows are aggregated into a settlement total, so a repeated
    row doubles it. Razorpay pagination with an overlapping `skip` window and a
    retried pull both produce exactly that, and the result is a settlement net
    no bank credit matches — a CONTRADICTED verdict caused by the reader."""
    from attest.adapters.razorpay import RazorpayAdapter
    a = RazorpayAdapter(key_id=None, key_secret=None)
    one = a.normalise([_recon_row()], [])
    two = a.normalise([_recon_row(), _recon_row()], [])
    assert two.settlements[0].net_paise == one.settlements[0].net_paise
    assert len(two.orders) == len(one.orders) == 1
    assert two.duplicates == 1
    assert any("same source identity" in w for w in two.warnings)


def test_adapter001_distinct_rows_are_not_deduplicated() -> None:
    """Failing closed on duplicates must not swallow genuine second payments."""
    from attest.adapters.razorpay import RazorpayAdapter
    a = RazorpayAdapter(key_id=None, key_secret=None)
    snap = a.normalise([_recon_row(entity_id="pay_1", payment_id="pay_1"),
                        _recon_row(entity_id="pay_2", payment_id="pay_2",
                                   order_id="ord_2")], [])
    assert len(snap.orders) == 2
    assert snap.settlements[0].net_paise == 2000
    # And a row that names itself twice, differently, is refused rather than
    # resolved by preferring one field — merging distinct records loses money.
    conflict = a.normalise([_recon_row(entity_id="pay_2")], [])
    assert not conflict.orders
    assert "names itself both" in conflict.rejected[0].reason


def test_adapter002_a_non_integer_amount_is_dropped_not_truncated() -> None:
    """ADAPTER-002. `int(10.5)` was 10 — money changed by the reader without
    anyone being told. docs/MONEY-MODEL.md says every amount is integer paise."""
    from attest.adapters.razorpay import RazorpayAdapter
    a = RazorpayAdapter(key_id=None, key_secret=None)
    snap = a.normalise([_recon_row(amount=10.5)], [])
    assert not snap.orders
    assert snap.rejected[0].index == 0
    assert "non-integral" in snap.rejected[0].reason
    # a float that IS a whole number is fine; the objection is to losing paise
    ok = a.normalise([_recon_row(amount=1024.0)], [])
    assert len(ok.orders) == 1 and ok.orders[0].gross_paise == 1024


def test_adapter003_a_malformed_row_is_counted_not_fatal() -> None:
    """ADAPTER-003. A non-dict row raised AttributeError out of normalisation.
    One bad row in a page should not lose the page."""
    from attest.adapters.razorpay import RazorpayAdapter
    a = RazorpayAdapter(key_id=None, key_secret=None)
    snap = a.normalise(["nonsense", None, _recon_row()], [])
    assert len(snap.orders) == 1
    # ADAPTER-003 was upgraded from a counter to explicit records: a count of
    # skipped rows cannot be acted on, an index and a reason can.
    assert [r.index for r in snap.rejected] == [0, 1]
    assert "not an object" in snap.rejected[0].reason


def test_the_adapter_refuses_to_fetch_without_credentials() -> None:
    """No demo mode inside the adapter: absent credentials produce no data."""
    import pytest as _pytest

    from attest.adapters.base import NotConnected
    from attest.adapters.razorpay import RazorpayAdapter
    with _pytest.raises(NotConnected):
        RazorpayAdapter(key_id=None, key_secret=None).fetch(2026, 5)


def test_the_adapter_never_reports_a_fixture_as_live() -> None:
    """§39. `live` is set by fetch and by nothing else."""
    from attest.adapters.razorpay import RazorpayAdapter
    snap = RazorpayAdapter(key_id=None, key_secret=None).normalise(
        [_recon_row()], [])
    assert snap.live is False


def test_every_test_named_in_the_failure_map_exists() -> None:
    """docs/FAILURE-REGRESSION-MAP.md may not name a test that does not exist.

    A map is only worth reading if its right-hand column is true. Left to prose,
    a renamed or deleted test rots the document silently and the entry keeps
    claiming coverage that is gone — which is exactly the drift D13 recorded,
    applied to tests instead of to numbers. So the map is parsed and checked.
    """
    import pathlib
    import re

    root = pathlib.Path(__file__).resolve().parent.parent
    doc = (root / "docs" / "FAILURE-REGRESSION-MAP.md").read_text()
    named = set(re.findall(r"`(test_[a-z0-9_]+)`", doc))
    assert named, "the map names no tests at all"

    defined: set[str] = set()
    for f in sorted((root / "tests").glob("test_*.py")):
        defined |= set(re.findall(r"^def (test_[a-z0-9_]+)", f.read_text(), re.M))

    missing = sorted(named - defined - {"test_every_test_named_in_the_failure_map_exists"})
    assert not missing, (
        f"the failure map names {len(missing)} test(s) that do not exist: "
        f"{missing}. Either the test was renamed and the map was not, or the "
        f"map claims a regression that was never written.")


def test_the_failure_map_covers_every_recorded_failure() -> None:
    """Every D-number in FAILURES.md must appear in the map.

    A failure recorded in the log and absent from the map is one whose
    regression status nobody has had to state.
    """
    import pathlib
    import re

    root = pathlib.Path(__file__).resolve().parent.parent
    logged = set(re.findall(r"^## (D\d+)", (root / "FAILURES.md").read_text(), re.M))
    mapped = set(re.findall(r"\b(D\d+)\b",
                            (root / "docs" / "FAILURE-REGRESSION-MAP.md").read_text()))
    missing = sorted(logged - mapped, key=lambda d: int(d[1:]))
    assert not missing, f"failures with no entry in the map: {missing}"
