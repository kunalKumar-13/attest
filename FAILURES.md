# Failure log

Kept daily, from hour one. Razorpay's form asks *"what broke, and how you got
out"* and says it is the answer they read first. Reconstructing that from memory
on day 7 produces "we had some bugs"; this file produces commits.

---

## D1 — 2026-08-21

**`dataclass(slots=True)` exploded on import.**
macOS ships Python 3.9 as `python3`; `slots=` landed in 3.10. Wasted a cycle
assuming the interpreter on PATH was the one I meant. Fixed by pinning a 3.13
venv in-tree. Lesson generalises: the environment is a dependency and belongs in
the repo, not in my head.

**Layer 2 had nothing to do on first run.**
The generator's `CLEAN` family produced bundles of size 2–6, so the single-order
exact matcher could never fire — a whole layer was dead code and the baseline
would have been 0% for a reason that had nothing to do with the algorithm.
Fixed by allowing size-1 bundles, which is also correct domain-wise: instant and
on-demand settlements really are one order. **The generator was wrong before the
matcher was.** Argument for writing the harness first, not after.

**Open question carried into D2.**
`blocking_recall` came out at 0.999, higher than expected. `CHARGEBACK_REVERSAL`
was supposed to punish the 6-day lookback window, but the reversing order is
deliberately *not* in the truth set, so it never counts against blocking recall —
it instead makes the credit unmatchable by any subset of the pool. That is a
legitimate hazard, but it is not the hazard I thought I was building. Decide on
D2 whether to add a family that genuinely strands true pairs outside the window,
so the ceiling metric is actually exercised rather than trivially satisfied.

---

## D2 — 2026-08-21

**Meet-in-the-middle was the wrong algorithm and the data said so immediately.**
The plan, written into the PRD on D1, was MITM subset-sum: split the candidate
pool, enumerate 2^(n/2) partial sums per side, binary-search the tolerance
interval. Viable to roughly n=45.

Measured the actual pools before writing a line of it:

```
candidate pool   p50 = 899   p90 = 1023   max = 1097
true bundle      p50 = 6     p90 = 27     max = 40
```

2^449 per side. Not slow — impossible. The estimate of "n under 40 after
blocking" was invented rather than measured, and it was wrong by a factor of
twenty.

**Fix: counting DP over the amount axis instead of the subset axis.** Amounts are
integers, so reachable sums are a dense array and each order is one shifted add:
O(n·target) instead of O(2^(n/2)). Linear in the pool.

The replacement is strictly better than what it replaced, for a reason that has
nothing to do with speed: saturating the counter at two decides
CONTRADICTED / PROVEN / AMBIGUOUS directly, so the verdict became a computed
property of the constraint system instead of a threshold on a confidence score.
The bug forced a better architecture.

**What it cost:** ~4.3e9 cell updates per settlement at p50, which numpy cannot
carry. The Python reference now declares an explicit envelope
(`OutOfEnvelope`) rather than degrading to a guess. The Rust port moved from
"nice benchmark" to load-bearing — measured justification, not a flourish.

**Carried to D3:** blocking is far too loose. A 6-day sweep collects ~900 orders
where the true bundle is 6. Tightening the window using the settlement calendar
should cut the pool by an order of magnitude and is worth more than any solver
optimisation.

---

## D3 — 2026-08-21

**Inverted the settlement calendar by hand and silently deleted 2/7 of the data.**
Wrote `business_days_before` as the mirror of `business_days_after`. Pools fell
from p50 899 to 132 — and the blocking ceiling fell from 0.999 to **0.695**.

The loss was 30.5%, which is the weekend fraction almost exactly. The forward map
is many-to-one: an order captured on Saturday and one captured the following
Monday settle on the same business day. A hand-written inverse returns one date
and drops the weekend.

Fixed by inverting the *actual function* — run `business_days_after` forward over
a window and keep every date that lands on the target — rather than
reimplementing the arithmetic backwards. Ceiling back to 0.999 at rung 2, pool
p50 185 at rung 0. **Lesson: never hand-write the inverse of a many-to-one map.**

**A wrong match got past the kernel.** 1 of 250, precision 0.983. The kernel did
its job — the arithmetic genuinely balances. The true explanation had been pruned
by blocking, and a *different* subset then matched uniquely, so the engine proved
something that was internally consistent and factually wrong. Confirms the
ceiling metric is not academic: blocking errors do not merely cost recall, they
manufacture false proofs.

**The real finding: the problem is under-constrained, not under-searched.**
198 of 250 settlements came back AMBIGUOUS. Not a solver weakness — with a
185-order pool and paise-level tolerance, genuinely many distinct subsets satisfy
the amount constraint exactly. Arithmetic alone cannot decide, and the engine
correctly refuses to.

So the path forward is **more evidence, not more search**: reference-ID anchoring,
bundle-size priors, cross-settlement uniqueness. D4 is measured by driving the
AMBIGUOUS rate down while WRONG stays at zero — which is the whole thesis, arrived
at from the data rather than asserted up front.

---

## D4 — 2026-08-21

**Built cross-settlement constraint propagation. Measured it. Shipped it off.**

The D3 diagnosis was that the problem is under-constrained rather than
under-searched: 198/250 AMBIGUOUS, because with a 185-order pool many distinct
subsets satisfy the amount constraint exactly. The free extra constraint is that
an order belongs to exactly one settlement, which makes settlements evidence
about each other. Orders appearing in *every* surviving explanation are
determined even when the full set is not, so they can be struck from every other
pool — which kills candidates elsewhere, sometimes leaving a unique survivor.

It works. It also nearly quadrupled the false-proof rate.

```
                     exact      WRONG    precision
propagation off      20.0%       0.4%       0.983
propagation on       23.2%       3.6%       0.807
```

Eight more correct answers, eight more wrong ones.

**Mechanism.** Propagation is only as sound as its seeds, and one seed was
already wrong: D3 logged a settlement whose true explanation had been pruned by
blocking, so a *different* subset matched uniquely and was proven. That false
proof consumed orders it did not own. Those orders were struck from other
settlements' candidate lists, killing their *true* explanations and leaving wrong
survivors — which were then promoted to PROVEN, and consumed more orders. A
single blocking error amplified into nine false proofs across four rounds.

**First fix, insufficient.** The enumerator caps at `MAX_ENUM`, so "present in
every explanation" was a claim about a *sample*. Made the cap detectable (ask for
`MAX_ENUM + 1`; coming back short proves the search ran out of explanations
rather than budget) and refused to deduce from non-exhaustive findings. Correct
and worth keeping — it is a real unsoundness — but it moved WRONG from 8 to 9.
The bug was never the sampling. It was the seeds.

**Decision: default off.** A sound version needs to treat a
propagation-induced CONTRADICTED as a refutation of the seed that caused it and
backtrack, which is a real solver feature and not a D5 afternoon. Until then the
feature exists, is measured, and is disabled.

Worth stating plainly, because it is the whole thesis applied to our own work: a
change that raises exact-set match by three points is *not* an improvement if it
raises false proofs by the same amount. The engine's job is to refuse to guess.
A feature that makes it guess more confidently is a regression no matter what the
headline number does.
