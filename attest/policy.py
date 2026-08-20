"""The action policy. §7, §27, §35.

A verdict is a statement about evidence. Posting is a statement about money. The
second does not follow from the first, and this module is the gap between them.

**No threshold is chosen.** `confidence > 0.95` is the shape of the mistake: the
number is picked, then defended. Here the rule is an inequality with units on
both sides —

    P(error) × cost(a wrong posting)  <  cost(a human review)

— so the threshold is whatever that inequality implies. Change the review cost
and the threshold moves on its own, which is the correct behaviour: a merchant
whose analysts are expensive should automate more, and the policy should say so
without anyone retuning it.

**P(error) is measured, never asserted.** It is the observed false-proof rate of
this engine, conditioned on things a caller can see before the answer is known:
the verdict, whether the search space was validated or heuristic, and which
layer resolved it. `calibrate()` derives those rates against ground truth.

**An uncalibrated policy posts nothing.** Not a degraded estimate, not a prior —
nothing. A policy that guesses its own error rate is a confidence score wearing a
lab coat, and this engine exists because of what those cost.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from attest.model import Settlement
from attest.searchspace import Integrity, SearchSpace
from attest.verdict import Finding, Verdict


class Decision(str, Enum):
    AUTO_POST = "AUTO_POST"
    REVIEW = "REVIEW"
    BLOCK = "BLOCK"
    """Not "expensive to check" but "must not be actioned at all" — a
    compromised search space, or an engine that has not measured itself."""


@dataclass(frozen=True)
class Costs:
    """The economics. Every figure is an assumption and is labelled as one.

    Defaults are placeholders a merchant is expected to replace. They are stated
    rather than buried so that a reader can disagree with the number instead of
    with the engine.
    """

    review_paise: int = 15_000
    """₹150 — an analyst's time to open a settlement, read the evidence and
    decide. Assumption."""

    wrong_post_fixed_paise: int = 250_000
    """₹2,500 — the fixed cost of a wrong posting regardless of size:
    investigation, correction, the journal reversal, the trust. Assumption."""

    wrong_post_rate_bps: int = 3_000
    """30% of the misposted amount, as the expected recoverable loss once the
    error is found. Assumption, and the one most worth arguing about."""

    max_exposure_paise: int = 10_000_000
    """₹1,00,000. A hard ceiling: above this a human looks regardless of how
    good the arithmetic is, because expected-value reasoning is the wrong tool
    for a tail a merchant cannot absorb."""

    def wrong_post(self, amount_paise: int) -> int:
        return self.wrong_post_fixed_paise + amount_paise * self.wrong_post_rate_bps // 10_000


@dataclass
class RiskModel:
    """Measured false-proof rates, conditioned on what is visible up front.

    Keys are `(verdict, integrity)`. Not the layer, deliberately: layer strata
    are thin enough that a single settlement moves the rate several points, and
    a rate estimated from four observations is a number pretending to be a
    measurement.
    """

    rates: dict[tuple[str, str], tuple[int, int]] = field(default_factory=dict)
    """(wrong, total) per stratum."""

    calibrated_on: int = 0

    #: Below this many observations a stratum has not been measured, only
    #: glimpsed. Fail closed rather than post on a rate derived from a handful.
    MIN_OBSERVATIONS = 30

    def key(self, f: Finding) -> tuple[str, str]:
        space = f.space if isinstance(f.space, SearchSpace) else None
        return (f.verdict.value, space.integrity.value if space else "unrecorded")

    def p_error(self, f: Finding) -> float | None:
        """Upper confidence bound on this stratum's error rate, or None.

        The point estimate is the wrong number and the engine measured why.
        Calibrating on three seeds gave 1 wrong in 152, a rate of 0.013; on
        held-out seeds the policy's realised loss came in **five times** its
        prediction, because the training portfolios happened to be kind. That is
        the D7 lesson arriving in a second place: a rate measured once is an
        anecdote about one draw.

        So the policy prices risk at the **95% Wilson upper bound** rather than
        the observed rate. For 1/152 that is roughly 0.035 instead of 0.013 —
        about three times more cautious, and the direction of the error now
        favours the merchant. Being wrong about your own error rate is
        acceptable in exactly one direction.

        None means the stratum is unmeasured, and the caller must block.
        """
        wrong, total = self.rates.get(self.key(f), (0, 0))
        if total < self.MIN_OBSERVATIONS:
            return None
        return _wilson_upper(wrong, total)

    def observe(self, f: Finding, was_wrong: bool) -> None:
        w, t = self.rates.get(self.key(f), (0, 0))
        self.rates[self.key(f)] = (w + int(was_wrong), t + 1)
        self.calibrated_on += 1


#: 1.96 — the 95% one-sided normal deviate. Named rather than inlined because
#: choosing a confidence level is a policy decision, not a constant.
Z95 = 1.959963985


def _wilson_upper(wrong: int, total: int, z: float = Z95) -> float:
    """Upper end of the Wilson score interval for a proportion.

    Wilson rather than the normal approximation because the rates here are small
    and the counts are modest, which is exactly where the normal interval
    misbehaves — it can even reach below zero for a stratum with no observed
    errors, which would price that stratum as risk-free.
    """
    if total <= 0:
        return 1.0
    p = wrong / total
    d = 1 + z * z / total
    centre = p + z * z / (2 * total)
    margin = z * ((p * (1 - p) / total + z * z / (4 * total * total)) ** 0.5)
    return min((centre + margin) / d, 1.0)


@dataclass(frozen=True)
class Judgement:
    decision: Decision
    expected_loss_paise: int | None
    p_error: float | None
    reasons: tuple[str, ...]

    def explain(self) -> str:
        return "\n".join(self.reasons)


def decide(f: Finding, s: Settlement, risk: RiskModel,
           costs: Costs = Costs()) -> Judgement:
    """Whether this settlement may post itself, and the arithmetic that says so."""
    why: list[str] = []

    if f.verdict is not Verdict.PROVEN:
        return Judgement(Decision.REVIEW, None, None,
                         (f"verdict is {f.verdict.value}; only a unique, "
                          f"kernel-checked explanation is eligible to post",))

    space = f.space if isinstance(f.space, SearchSpace) else None
    if space and space.integrity is Integrity.COMPROMISED:
        return Judgement(Decision.BLOCK, None, None,
                         ("the search space is known to have excluded a valid "
                          "candidate; the arithmetic answers a question that "
                          "did not contain the truth",))

    p = risk.p_error(f)
    if p is None:
        return Judgement(
            Decision.BLOCK, None, None,
            ("this engine has not measured its own error rate for this class of "
             "result, so expected loss cannot be computed; an unmeasured policy "
             "posts nothing",))
    obs_w, obs_t = risk.rates.get(risk.key(f), (0, 0))
    why.append(f"observed {obs_w} false proof(s) in {obs_t} {risk.key(f)[0]} "
               f"results over a {risk.key(f)[1]} search space; priced at the 95% "
               f"upper bound {p:.4f}, not the point estimate {obs_w / obs_t:.4f}")

    exposure = costs.wrong_post(s.net_paise)
    loss = int(p * exposure)
    why.append(f"a wrong posting of {s.net_paise} paise costs "
               f"{exposure} paise, so expected loss is {loss} paise")
    why.append(f"a human review costs {costs.review_paise} paise")

    if s.net_paise > costs.max_exposure_paise:
        why.append(f"amount exceeds the {costs.max_exposure_paise} paise exposure "
                   f"ceiling; expected value is the wrong instrument for a tail "
                   f"this size")
        return Judgement(Decision.REVIEW, loss, p, tuple(why))

    if space and space.integrity is Integrity.HEURISTIC:
        why.append(f"uniqueness is local: {space.uniqueness_claim()}")

    if loss < costs.review_paise:
        why.append(f"expected loss {loss} < review cost {costs.review_paise} — "
                   f"automating is cheaper than checking")
        return Judgement(Decision.AUTO_POST, loss, p, tuple(why))

    why.append(f"expected loss {loss} >= review cost {costs.review_paise} — "
               f"checking is cheaper than being wrong")
    return Judgement(Decision.REVIEW, loss, p, tuple(why))


# --------------------------------------------------------------------------
# Calibration and simulation
# --------------------------------------------------------------------------


def calibrate(findings_by_seed: dict[int, tuple[list[Finding], dict[str, set[str]]]]
              ) -> RiskModel:
    """Derive the error rates from runs whose ground truth is known.

    Fitting on the same portfolio the policy then judges would be leakage; the
    caller is expected to pass held-out seeds. That is a real requirement, not a
    formality — a policy calibrated on its own test set is a policy that has
    measured nothing.
    """
    risk = RiskModel()
    for _seed, (findings, truth) in findings_by_seed.items():
        for f in findings:
            if f.verdict is not Verdict.PROVEN or not f.proofs:
                continue
            risk.observe(f, set(f.proofs[0].order_ids) != truth.get(f.settlement_id, set()))
    return risk


@dataclass
class Simulation:
    auto_post: int
    review: int
    block: int
    posted_paise: int
    protected_paise: int
    """Money the policy refused to post automatically. The number a merchant
    should actually be shown: it is what the engine's caution is worth."""
    expected_loss_paise: int
    realised_wrong_paise: int
    """What auto-posting actually cost against ground truth, priced with the SAME
    cost function as the prediction. Comparing a modelled loss against a raw
    misposted amount would make any policy look catastrophically miscalibrated
    for a reason that is purely an accounting mismatch."""

    wrong_posts: int = 0

    @property
    def calibration(self) -> str:
        """How far the modelled loss was from the realised one.

        Reported on every simulation because a policy that cannot say how wrong
        its own estimate was is not a policy, it is a preference.
        """
        if not self.expected_loss_paise:
            return "no auto-posts"
        r = self.realised_wrong_paise / self.expected_loss_paise
        verdict = ("within tolerance" if 0.5 <= r <= 2.0
                   else "UNDER-estimates loss" if r > 2.0 else "over-estimates loss")
        return f"realised / predicted = {r:.2f}x — {verdict}"

    def render(self, costs: Costs) -> str:
        total = max(self.auto_post + self.review + self.block, 1)
        return "\n".join([
            f"  review cost      ₹{costs.review_paise / 100:>12,.0f}",
            f"  max exposure     ₹{costs.max_exposure_paise / 100:>12,.0f}",
            "  " + "-" * 44,
            f"  auto-post        {self.auto_post:>6}  {self.auto_post / total:>6.1%}",
            f"  review           {self.review:>6}  {self.review / total:>6.1%}",
            f"  block            {self.block:>6}  {self.block / total:>6.1%}",
            "  " + "-" * 44,
            f"  posted           ₹{self.posted_paise / 100:>12,.0f}",
            f"  protected        ₹{self.protected_paise / 100:>12,.0f}",
            f"  expected loss    ₹{self.expected_loss_paise / 100:>12,.0f}",
            f"  realised loss    ₹{self.realised_wrong_paise / 100:>12,.0f}"
            f"   ({self.wrong_posts} wrong post"
            f"{'' if self.wrong_posts == 1 else 's'})",
            f"  calibration      {self.calibration}",
        ])


def simulate(findings: list[Finding], settlements: dict[str, Settlement],
             truth: dict[str, set[str]], risk: RiskModel,
             costs: Costs = Costs()) -> Simulation:
    """Run the policy over a portfolio and report predicted against realised."""
    auto = rev = blk = posted = protected = eloss = wrong_amt = n_wrong = 0
    for f in findings:
        s = settlements[f.settlement_id]
        j = decide(f, s, risk, costs)
        if j.decision is Decision.AUTO_POST:
            auto += 1
            posted += s.net_paise
            eloss += j.expected_loss_paise or 0
            if f.proofs and set(f.proofs[0].order_ids) != truth.get(f.settlement_id, set()):
                wrong_amt += costs.wrong_post(s.net_paise)
                n_wrong += 1
        else:
            (rev, blk)[j.decision is Decision.BLOCK]
            if j.decision is Decision.BLOCK:
                blk += 1
            else:
                rev += 1
            protected += s.net_paise
    return Simulation(auto, rev, blk, posted, protected, eloss, wrong_amt, n_wrong)
