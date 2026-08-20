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
    layer: str = ""

    @property
    def postable(self) -> bool:
        """Only a unique, kernel-checked explanation may post automatically."""
        return self.verdict is Verdict.PROVEN


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
