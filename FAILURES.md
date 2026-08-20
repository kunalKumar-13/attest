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

---

## D5 — 2026-08-21

**Spent an hour optimising a search that was never running.**

`bundle_large` sat at 0.0% across 34 settlements — 13.6% of the portfolio — and
the diagnosis seemed obvious: depth-first search cannot find a 27-element subset
among 185 candidates, because the suffix-sum bound only rejects a branch once the
remainder has become arithmetically impossible, which is far too late.

So the counting DP's reachability array was wired into the enumerator as a prune:
a branch whose residual is unreachable *at all* is cut immediately. Sound, cheap,
and it can only over-approximate, so it never prunes a live branch.

Result: **no change. 0.0% before, 0.0% after.**

Measured instead of theorising:

```
hazard              n   out-of-envelope   median credit
bundle_large       34        34   100%    Rs 77,051
everything else   216         3     1%    Rs ~15,000
                                          envelope cap: Rs 30,000
```

Every one of them exceeds `MAX_TARGET_PAISE` and raises `OutOfEnvelope` before a
single subset is examined. The search was never the problem. The search never
ran.

**14.8% of the portfolio is currently unreachable in Python**, and the cap exists
because the numpy DP allocates and copies an array the width of the credit —
`O(n·target)` bytes of memory traffic per order, which at Rs 77,051 is 7.7M cells
copied 185 times.

The prune stays: it is correct, it costs nothing, and it will matter once the
envelope opens. But it fixed nothing today.

**Consequence: the Rust port stops being a benchmark and becomes the unlock.**
Not "the same thing, faster" — the difference between attempting 85% of the
portfolio and attempting all of it. The kernel is two bitsets rather than a byte
array, which is what makes the wider envelope affordable:

    A = sums reachable at least one way
    B = sums reachable at least two ways

    A' = A | (A << w)
    B' = B | (B << w) | (A & (A << w))

`A & (A << w)` is exactly "reachable both with and without this order" — a second
distinct explanation. Three bitwise operations per 64-bit word gives the same
0/1/2 saturating count the verdict needs, at one thirty-second of the memory
traffic. PROVEN / AMBIGUOUS / CONTRADICTED falls out of two bit arrays.

**Lesson, repeated from D2 and apparently not learned: measure the failure before
fixing it.** Two of the five days so far have opened with a confident wrong
diagnosis, and both times the data answered in one query.

---

## Adversary sweep — 2026-08-21

Everything below is generated by subclassing `Generator` (`_bundle`, `_collide`,
`build`) in a scratch file outside the repo and calling the real, unedited
`attest.pipeline.run`. `attest/**` was not touched. `ATTEST_PROP` was left unset
throughout — propagation is a pipeline flag, not a generator lever, and D4 already
covers it. Numbers are at HEAD `3805e17` (D6, envelope open, Rust kernel), each
config run across five seeds (20260821, 314159, 271828, 555001, 999983) so a
one-seed coincidence doesn't get written up as a mechanism.

**The "precision reaches 1.000" headline is one seed, not a property.** Reran the
*untouched* default generator, five seeds, no adversarial change at all:

```
seed        20260821  314159  271828  555001  999983
WRONG/250          0       0       1       2       2
```

5/1250 = 0.4%. D6 fixed the specific D5 mechanism — `bundle_large` starving on
`OutOfEnvelope` before the solver ever ran — and seed 20260821 happens to land on
zero because of it. The D3 false-proof mechanism (true explanation pruned, a
different subset matches uniquely) was never touched by D6 and still fires at
roughly the D3 rate on the other four seeds. "Precision reaches 1.000" is true of
one seed's run; it is not true of the config.

**Forcing every order to UPI (zero MDR, `net == gross`) roughly triples the
false-proof rate, and it reproduces.** Subclassed `_order` to ignore the method
weights and always emit `Method.UPI`; nothing else about the generator changed.

```
config              WRONG/250 across the 5 seeds        total
all-upi-zero-fee         0    1    8    4    1          14/1250 = 1.12%
baseline (above)         0    0    1    2    2           5/1250 = 0.40%
```

Four of five seeds nonzero; one seed alone hit 8/250 = 3.2%, the same order of
magnitude as the D4 propagation-on regression. **Mechanism:** `net_paise` is the
identity function under UPI, so every order's contribution to a subset sum is its
raw gross paise, drawn from one flat integer distribution instead of four
fee-adjusted ones. `model.py` says outright that method-mixed fee rates are what
stop "two bundles of identical gross" from settling to the same net — forcing a
single method deletes that fingerprint on purpose. With no fee-rate
differentiation left, unrelated orders collide on the same subset-sum far more
often, and the solver correctly reports the accidental collision as PROVEN,
because among the inputs it was given, it is the only explanation. The WRONG
cases concentrate in hazards that already carry a residual the credit doesn't
equal exactly — `refund_offset`, `split_order`, `chargeback_reversal`,
`timing_gap` — because those targets have more tolerance slack for a coincidental
subset to land inside.

**Shrinking `CLEAN` bundles to 1–2 orders, and separately upweighting
`AMBIGUOUS_SUBSET` with a wider collision width, both produce a smaller but
consistent elevation over baseline:**

```
config                    WRONG across 5 seeds            total            baseline-scale
tiny-clean (n=300)         1  1  4  1  1                  8/1500 = 0.53%   5/5 seeds nonzero
dense-ambiguous (n=250,
  mix 0.02->0.15, k 2-4->2-8)  0  4  1  3  1               9/1250 = 0.72%   4/5 seeds nonzero
```

Neither is as sharp as the UPI result, but `tiny-clean` never hit zero across five
seeds — baseline hit zero twice out of five at the same n. Same direction as the
UPI finding: shrink the bundle or thicken the collision set, and the number of
distinct explanations that land inside `tolerance_paise` goes up, which is
exactly the axis PROVEN depends on being singular.

**Weekend-boundary capture clustering (Fri/Sat/Sun/Mon, the exact seam the D3
calendar inversion collapses) is a weaker signal than expected and I am not
willing to call it a finding.**

```
weekend-boundary-cluster (n=300)   1  5  0  1  2      9/1500 = 0.60%
```

Elevated over the 0.40% baseline, four of five seeds nonzero, and one seed did hit
5/300 — but checking the layer each WRONG resolved at, only 2 of the 9 came from
a widened rung (`r1`/`r2`); the other 7 were already wrong at the tightest window,
same as baseline's own WRONGs. I went in expecting escalation-driven mismatches
(the literal D3 mechanism) and the rung breakdown doesn't support that story at
this sample size. Recording the numbers because they're real, but the mechanism
claim would be invented, not measured — needs more seeds than I had budget for
before it's worth asserting *why*.

**Two clean negative results, both of which matter because they run against the
intuition that "more adversarial pressure" should mean more false proofs:**

```
cluster-15days / cluster-6days (compress 90-day spread to 6-15 distinct dates)
                                     0  0  0  0  0   (15d, n=250)
                                     1  0  0  0  0   (6d,  n=300)
combined-attack (10-day cluster + dense-ambiguous mix/k + tiny-clean, stacked)
                                     0  0  0  0  0   (n=300)
```

Tight capture clustering inflates pools (one `cluster-6days` run hit a 494-order
bucket and took 6s against a <1s baseline) but the extra candidates mostly make
things *more* AMBIGUOUS, not falsely certain — declined rate went from ~80% at
baseline to 90–96%. Stacking every lever that individually raised WRONG
(clustering + dense collisions + tiny bundles, combined-attack) drove declined to
84–90% and WRONG to exactly zero across all five seeds, the single most
consistent negative result in this sweep. Working hypothesis: there's a regime
boundary. A *moderate* increase in collision density gives the solver just enough
extra candidates to manufacture one coincidental unique match. Pushing density
higher gives it two or more, and `solve()`'s own saturating-count logic — which
is the mechanism the D3 diagnosis already described as "under-constrained, not
under-searched" — correctly downgrades PROVEN to AMBIGUOUS once a second
explanation exists. The unsafe zone is not "more adversarial," it's "adversarial
enough to break uniqueness, not enough to break it twice."

---

## D7 — 2026-08-21

**Published "precision 1.000" for six days. It was one seed.**

The engine reported zero false proofs on seed 20260821, and that number went into
the README, the PRD, the UI status bar and every summary written since D6. An
adversarial sweep re-ran the *untouched* generator across five seeds:

```
seed        20260821  314159  271828  555001  999983
WRONG/250          0       0       1       2       2
```

Reproduced independently before changing anything — the agent's numbers and mine
agree exactly. Pooled across 1,250 settlements: **5 false proofs, precision
0.981, exact-set 18.5%.** Not 1.000, and not 20.8%.

**The mechanism is not interesting. The process failure is.** D3 already recorded
that blocking errors manufacture false proofs rather than merely costing recall,
so a seed whose portfolio lands more true explanations outside the lag ladder
will produce more of them. That was known. What was not done was checking whether
the headline survived a second draw.

**This is exactly the failure the project exists to prevent, committed by the
project.** ATTEST's entire argument is that a plausible answer is not a proven
one, and that verification — not generation — is the scarce thing. A number
measured once and repeated confidently is a plausible answer. Six days of
documentation asserted a property of the engine on evidence that only supported a
property of one portfolio.

**Fix.** `attest/eval/sweep.py` runs a fixed five-seed panel and reports the
POOLED figure — pairs counted, not per-seed precisions averaged, because a mean
weights a small run identically to a large one and flatters whichever was small.
The worst seed is printed beside the aggregate. Every claim in README.md and
PRD.md now carries its panel, and single-seed numbers are labelled as such.

The panel is fixed. Adding a seed because the numbers came out badly would be the
same mistake in a different costume.

**Credit where it is due:** this was found by the adversarial worker whose entire
brief was to prove the system wrong, and whose instructions said the seed sweep
alone was worth more than everything else on its list. It was.
