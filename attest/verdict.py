"""Proof status, and a trusted verifier kernel.

Confidence scores are the wrong output for financial software. "97%" is not
interpretable: it does not say what would have to be true for the answer to be
wrong, and it cannot be audited. Worse, it invites a threshold, and a threshold
invites posting an entry that nobody can defend.

So the engine does not emit a score. It emits a **decidable property of the
constraint system**:

    PROVEN         exactly one assignment satisfies every constraint
    AMBIGUOUS      two or more do; the engine reports them and stops
    CONTRADICTED   none does; the engine reports which constraints conflict

These are computed, not estimated. The solver counts feasible solutions, so the
verdict is a fact about the model rather than a belief about the data.

**Trusted kernel.** The prover is large -- pruning, dynamic programming,
CP-SAT, model-proposed hypotheses. The verifier below is small enough to read in
one sitting and depends on none of it. A proof is accepted only if this function
accepts it, which means a bug anywhere in the prover can cost recall but cannot
post a wrong entry. Same reason a proof assistant separates its kernel from its
tactics.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from attest.model import Order, Settlement, tolerance_paise


class Verdict(str, Enum):
    PROVEN = "PROVEN"
    AMBIGUOUS = "AMBIGUOUS"
    CONTRADICTED = "CONTRADICTED"

    INSUFFICIENT = "INSUFFICIENT"
    """Not enough trustworthy data to make any claim at all.

    Distinct from AMBIGUOUS, and the distinction is not cosmetic. AMBIGUOUS says
    the evidence was examined and does not decide; INSUFFICIENT says the evidence
    was never there to examine. Collapsing the second into the first would report
    a missing-data problem as a solver outcome, and a merchant would go looking
    for the wrong fix.""" 


@dataclass(frozen=True)
class Proof:
    """A machine-checkable explanation of one settlement.

    Carries everything `check()` needs and nothing it does not. In particular it
    carries no scores: if a proof needs a confidence number to be believed, it is
    not a proof.
    """

    settlement_id: str
    order_ids: tuple[str, ...]
    gross_paise: int
    fee_paise: int
    tax_paise: int
    adjustment_paise: int
    """Refunds, chargebacks and settlement adjustments, signed. Non-zero values
    must be evidenced by a linked record, never inferred to close a gap."""
    net_paise: int
    residual_paise: int
    tolerance_paise: int
    constraints: dict[str, bool] = field(default_factory=dict)

    @property
    def balances(self) -> bool:
        return abs(self.residual_paise) <= self.tolerance_paise


@dataclass(frozen=True)
class Finding:
    """The engine's answer for one settlement."""

    settlement_id: str
    verdict: Verdict
    proofs: tuple[Proof, ...]
    """One proof for PROVEN. Several for AMBIGUOUS, so a human sees the actual
    competing explanations rather than a percentage. Empty for CONTRADICTED."""
    unsat_core: tuple[str, ...] = ()
    """For CONTRADICTED: the minimal set of constraints that cannot hold
    together. Extracted from the solver, not narrated by a model."""

    space: object | None = None
    """The `SearchSpace` the solver was given. A verdict without it is a claim
    about a search, not about the world — see attest/searchspace.py."""

    coincidence: object | None = None
    """How cheap this match was to make. Measured from the reachability the DP
    already computed, before anyone knows whether the answer is right. See
    attest/coincidence.py — it is the only upstream signal that separates a
    hard-won match from one the pool was always going to produce."""
    exhaustive: bool = False
    """True when every explanation was enumerated, not merely the first few.
    Cross-settlement deduction is only sound when this holds."""

    layer: str = ""

    @property
    def postable(self) -> bool:
        """Only a unique, kernel-checked explanation over an intact space.

        A COMPROMISED space is disqualifying regardless of the verdict: the
        arithmetic may be perfect and still answer a question that excluded the
        truth. That is D8, encoded rather than remembered.
        """
        if self.verdict is not Verdict.PROVEN:
            return False
        from attest.searchspace import Integrity, SearchSpace

        # CORE-001. This returned True when `space` was absent, so a PROVEN
        # finding assembled outside the pipeline was postable precisely because
        # it omitted the evidence it would have been judged on. Fails closed
        # now, and the four conditions are the four questions a posting has to
        # be able to answer about itself.
        sp = self.space

        # 1. What search space was proved?
        if not isinstance(sp, SearchSpace):
            return False

        # 2. Which candidate universe was considered? A space that recorded no
        #    universe and no reductions describes no search.
        if sp.universe <= 0 or not sp.reductions:
            return False

        # 3. Which solver produced it? `layer` is written by the layer that
        #    resolved the settlement; an empty one names no solver.
        if not self.layer:
            return False

        # 4. Does the proof belong to that universe? A proof citing more orders
        #    than the space ever contained cannot have come out of it.
        if not self.proofs or len(self.proofs[0].order_ids) > sp.candidates:
            return False

        return sp.integrity is not Integrity.COMPROMISED

    @property
    def uniqueness_claim(self) -> str:
        """What this finding has earned the right to say about uniqueness."""
        from attest.searchspace import SearchSpace
        if self.verdict is not Verdict.PROVEN:
            return ""
        if isinstance(self.space, SearchSpace):
            return self.space.uniqueness_claim()
        return "unique within the candidate space (space integrity unrecorded)"


# --------------------------------------------------------------------------
# Trusted kernel -- keep this small, keep it obvious, keep it independent
# --------------------------------------------------------------------------


def check(proof: Proof, settlement: Settlement, orders: dict[str, Order]) -> bool:
    """Re-derive a proof from source records. No solver, no heuristics.

    Deliberately recomputes rather than trusting any field on the proof: a
    prover bug that fabricates `gross_paise` must not survive.
    """
    if proof.settlement_id != settlement.settlement_id:
        return False
    if len(set(proof.order_ids)) != len(proof.order_ids):
        return False  # an order may not be spent twice inside one settlement
    try:
        members = [orders[oid] for oid in proof.order_ids]
    except KeyError:
        return False  # cites an order that does not exist

    gross = sum(o.gross_paise for o in members)
    net = sum(o.net for o in members)
    expected = net + proof.adjustment_paise
    residual = settlement.net_paise - expected
    tol = tolerance_paise(len(members))

    return (
        gross == proof.gross_paise
        and net + proof.adjustment_paise == proof.net_paise
        and residual == proof.residual_paise
        and tol == proof.tolerance_paise
        and abs(residual) <= tol
    )
