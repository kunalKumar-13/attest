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

---

## D8 — 2026-08-21

**Built the AI investigation loop. Measured it twice. Shipped it disabled.**

197 of 250 settlements abstain because several disjoint subsets satisfy the
amount constraint exactly. Arithmetic has said everything it can; the tie needs
evidence of a different kind — narration, counterparty, capture batch — which is
exactly what a model is good at reading and exactly what it must not be allowed
to conclude from. So: the model proposes an anchor, the solver decides.

**First version was architecturally wrong, and the mechanism is worth stating.**
It subtracted the anchor from the target and solved the remainder over what was
left. That resolved 92 abstentions across five seeds and got **32 of them wrong** —
precision 0.652.

    uniqueness inside a restricted space is not uniqueness.

Restricting the search to subsets containing the anchor changes which problem is
being solved. When the true explanation does not contain the anchor, the
restricted problem can have exactly one solution — a wrong one — and it arrives
wearing every mark of a proof: it balances, it clears the bound, the kernel
accepts it. It *is* internally consistent. It is simply not true. The kernel
cannot catch this, because the kernel checks arithmetic and the arithmetic is
correct; what is wrong is the question that was asked.

**Corrected: an anchor may only select among explanations arithmetic already
found valid over the FULL pool.** It can recognise uniqueness, never create it.
Re-measured:

```
                       resolved   correct   WRONG   precision
anchor completes             92        60      32       0.652
anchor selects only          73        38      35       0.521
```

Sound, and *worse*. That result is the useful one.

**The real finding: there is no signal here to select on.** The stub proposer
anchors on the densest same-day capture cluster, which has no causal link to any
particular settlement — it is a plausible-sounding guess. Selecting among four
candidate explanations with a guess lands near a coin flip, and 0.521 is a coin
flip. Swapping in a language model would change which guess gets made, not
whether it is a guess: the generator emits settlements carrying a UTR and nothing
that names an order, so the semantic evidence the loop is built to consume **does
not exist in this data**.

**Shipped disabled** (`ATTEST_ANCHOR=1` reproduces the measurement). Turning it on
would take the engine from 5 false proofs per 1,250 to roughly 40 while making
the demo look better, which is the trade this project exists to refuse.

What would make it work is not a better model. It is order-level references in
the settlement report — which real gateway settlement reports carry and this
generator does not. That is a data problem with a known shape, and naming it is
worth more than a resolution rate bought with guesses.

**Third time now** — D4 propagation, D6 envelope, D8 anchoring — that a feature
which raised the headline number was measured, found to raise false proofs, and
turned off. The pattern is not bad luck. Anything that resolves an abstention is
by construction taking a position the evidence did not support, and the only
defence is measuring against ground truth before believing it.

---

## D9 — 2026-08-21

**The policy under-priced its own risk by five times, and the point estimate was
the reason.**

The action policy computes `P(error) × cost(wrong post) < cost(review)`, so
everything rests on `P(error)`. Calibrated it against ground truth on three
seeds: **1 false proof in 152 PROVEN results, a rate of 0.0066.** Then ran it on
two held-out seeds and compared the predicted loss against what auto-posting
actually cost:

```
seed 555001    predicted ₹2,342    realised ₹13,211    5.64x
seed 999983    predicted ₹2,877    realised ₹13,906    4.83x
```

Five times under. Not a modelling subtlety — the policy would have been posting
money on a risk estimate that was wrong by most of an order of magnitude.

**Mechanism: a proportion measured once is an anecdote about one draw.** The
three calibration portfolios happened to be kind. This is D7 arriving in a second
place, and it arrived because the point estimate was used as though the sample
size did not matter. 1-in-152 and 7-in-1064 are the same ratio and emphatically
not the same evidence, and only one of them supports posting a merchant's money.

**Fix: price at the 95% Wilson upper bound, not the observed rate.** For 1/152
that is 0.0363 against a point estimate of 0.0066 — roughly five times more
cautious, which is almost exactly the size of the error. Wilson rather than the
normal approximation because these rates are small and the counts modest, which
is where the normal interval misbehaves; for a stratum with no observed errors it
can reach below zero and price the stratum as risk-free.

```
                predicted   realised   ratio
seed 555001       ₹2,273     ₹3,036    1.34x   within tolerance
seed 999983       ₹2,171         ₹0    0.00x   over-estimates
```

Auto-post rate fell from 15.2% to 7.6%. That is the cost and it is the right
trade: **being wrong about your own error rate is acceptable in exactly one
direction.**

**A second thing fell out of it.** The first predicted-vs-realised comparison
showed 12x, which sent me looking for a modelling flaw that was not there — I had
compared a modelled loss against a raw misposted amount. An accounting mismatch
in the instrument, not a defect in the thing being measured. Every comparison now
prices both sides with the same cost function, and `Simulation` reports the ratio
on every run so a miscalibrated policy announces itself instead of waiting to be
noticed.

The sweep this makes possible is the useful artefact:

```
review cost    auto-post   posted        protected      realised loss
     ₹50               0   ₹0            ₹1,02,04,412   ₹0
     ₹150             37   ₹99,571       ₹1,01,04,841   ₹3,036
     ₹500             82   ₹6,96,826     ₹95,07,586     ₹27,117
     ₹1,500           84   ₹8,04,849     ₹93,99,563     ₹27,117
```

That is the coverage/expected-loss frontier, measured rather than drawn. A
merchant picks a point on it by naming what an analyst's hour is worth.

---

## D10 — 2026-08-21

**A property test asserted the engine was sound and found out it is sound for a
narrower reason than stated.**

Wrote the invariant the architecture claims:

    when blocking did not exclude the truth, a PROVEN result is correct

One violation, seed 271828, `setl_000056`. A PROVEN result was wrong although
the true explanation was sitting in the candidate pool — which, if the property
were right, would mean the solver or the kernel is unsound. It is not.

The settlement is a `split_order`. Half of one order's proceeds went to a
different payout, so:

```
credit                    7,64,813 paise
sum of the true 6 orders  8,32,887 paise
difference                  68,074 paise
```

**The true explanation does not satisfy the amount constraint.** No exact-sum
solver can reach it however wide the search, because the constraint system has no
term for a split settlement. A different four-order subset happened to sum within
2 paise of the credit, and it is arithmetically perfect, uniquely so, and wrong.

**So false proofs have two sources, and conflating them hid one of them:**

```
search-space error   the truth was pruned before solving          D3, D8
model gap            the truth is not expressible at all          D10
```

The second is the worse of the two, because widening the search cannot fix it.
The engine will keep confidently explaining split settlements, refunds and
chargebacks with coincidental subsets until the constraint model carries an
adjustment term.

Attributed every false proof in the panel:

```
5 across 1,250 settlements
  model gap       3    chargeback_reversal x2, refund_offset x1
  search space    2    timing_gap, missing_ref
  unattributed    0
```

Zero unattributed is the number that matters. Every wrong answer this engine
produces is now explained by a named mechanism rather than absorbed into a rate.

`tests/test_invariants.py` states the property precisely — reachable means *in
the pool AND expressible* — and a second test fails the build if any false proof
becomes unattributable, because an unexplained wrong answer is a defect nothing
currently accounts for.

**The lesson is about the test, not the engine.** "ATTEST must never produce a
false PROVEN" is not a property this engine has; asserting it is what D7 cost.
The true property is conditional, and writing the condition down forced the
discovery of a failure class nobody had named.

---

## D11 — 2026-08-21

**D10 named a failure class that could not be searched away. There was a signal
for it sitting in an array the solver already builds.**

Model gaps — a split settlement, a refund netted inside the credit, a chargeback
reversing across periods — leave the true explanation unreachable by any exact
solver, because the credit does not equal the sum of its true orders. Some
*other* subset then lands within tolerance, uniquely, and it is arithmetically
perfect and factually wrong. Nothing downstream can catch it. The kernel checks
arithmetic and the arithmetic is correct.

Nothing downstream. Something **upstream** can.

The counting DP already computes which sums are reachable from the candidate
pool. So ask how densely populated the neighbourhood of the target is:

    a credit in a region where almost every value is reachable was CHEAP to
    hit, and a unique hit there is weak evidence

    a credit in a sparse region was EXPENSIVE to hit, and a unique hit there
    is strong evidence

One extra pass over an array that already exists, computed before anyone knows
whether the answer is right. Measured across the panel:

```
neighbourhood   proofs   correct   wrong   precision
sparse             189       189       0       1.000
moderate            43        38       5       0.884
dense                4         4       0       1.000
```

**Every false proof in the panel is in one bucket.** 189 proofs found in sparse
neighbourhoods, not one wrong.

Stratifying the risk model on it and re-running held out:

```
                        before    after
false proof rate         0.80%    0.80%   (unchanged — the engine still errs)
wrongly auto-posted     ₹1,786       ₹0   (the policy no longer acts on them)
financial error rate    1.7937%   0.0000%
safe resolution rate      7.4%     2.2%
```

The engine is exactly as wrong as it was. The difference is that it now knows
*which* of its proofs to distrust, and the money stops moving on them.

**The cost is real and is not hidden.** Automation fell from 7.4% to 2.2%,
because splitting one stratum into three leaves each with fewer observations and
several below the floor where a rate is a measurement rather than a glimpse.
Those fail closed. More calibration data recovers it; guessing the rate would
recover it faster and is exactly the thing this engine exists to refuse.

**A second finding fell out of the larger run.** Coverage is not a constant. At
250 settlements per seed it is 16.8%; at 600 over the same 90-day window it is
8.5%, because denser portfolios mean larger pools and more subsets landing
within tolerance. The engine is not worse on the bigger portfolio — the bigger
portfolio is a harder question, and the false-proof rate falls with it (0.80% to
0.08%) precisely because the engine refuses more of it. Any single coverage
figure quoted without its portfolio density is meaningless, and `results.json`
now carries that caveat next to the number.

---

## D12 — 2026-08-21

**Benchmarked CP-SAT set packing against the greedy cascade. Rejected the
packing, shipped the cores.**

`attest/partition.py` — 574 lines, written by an agent on the floor — formulates
L4b properly: one boolean per (settlement, candidate), at most one true per
settlement, each order claimed at most once, decomposed by connected component,
with a soundness gate that posts a settlement only when its candidate is *forced*
across every optimal packing.

The comparison it made is the right one, and worth stating because it is easy to
get wrong: the baseline is not "no packing". `PoolIndex.consume` already **is**
set packing — solved greedily and early, disjointness enforced by irrevocable
commitment in easiest-first order rather than by search. The question was never
whether to pack. It was greedy packing against global packing.

Reproduced independently, cell for cell, before acting on it:

```
seed        greedy exact  cpsat exact   greedy WRONG  cpsat WRONG
20260821              52           53              0            1
314159                56           57              0            1
271828                43           45              1            1
555001                37           34              2            4
999983                43           50              2            2
pooled (1,250)       231          239              5            9

exact-set   18.48% -> 19.12%   (+0.64 pp)
WRONG        0.40% ->  0.72%   (+0.32 pp)
precision   0.9807 -> 0.9714
```

**+0.64 pp of exact match for +0.32 pp of false proofs**, with precision moving
the wrong way and a straight regression at n=1200 (5.33% -> 2.42%). The gain is
not even consistent in sign: seed 555001 goes *backwards* by three, and four of
the eight extra false proofs land on that one seed. Shown only seed 999983
(+7 exact, WRONG unchanged) a reader would conclude the opposite of what the five
seeds say together — which is D7's lesson arriving for the fourth time.

Same trade as D4 propagation and D8 anchoring. Refused for the same reason.

**But the unsat cores are a different thing entirely, and they ship.** Set
packing is trivially feasible — select nothing — so infeasibility has to be
*asked for*: one assumption literal per settlement meaning "this one must be
explained", then read `SufficientAssumptionsForInfeasibility`. What comes back is
extracted by the solver's own conflict analysis, not reconstructed afterwards by
a heuristic:

```
setl_000109 AMBIGUOUS
  mutually unsatisfiable: setl_000109, setl_000155 cannot all be explained
    setl_000109: 4 candidate subset(s), truncated at MAX_ENUM
    setl_000155: 1 candidate subset(s), exhaustive
    contested orders: ord_001451, ord_001453, ord_001455
```

That is a named conflict over named resources. It turns "no valid assignment"
from a shrug into a work item, and it says something a single-settlement view
structurally cannot: *this settlement is unresolved because another one is
claiming its orders.*

**Verified it changes nothing it should not.** Verdicts are identical with cores
on and off; 80 findings gain an explanation and none gains an answer. It costs
2.17x wall clock, which is why it is off in the CLI and on in the API, where an
explanation is the product. `ortools` stays an optional import — a missing core
costs a reason, never a verdict.

**The measured shape of the whole exercise:** an agent wrote a rigorous
574-line implementation, benchmarked it honestly against the shipping engine,
and recommended against its own work. The valuable output was not the optimiser.
It was the measurement that said not to ship it, and the by-product nobody set
out to build.

---

## D13 — 2026-08-21

**Built the what-changed engine and used it to test a claim the engine makes
about itself.**

Reconciliation is a standing claim about a moving set of records — refunds land
late, chargebacks arrive weeks after capture, exports get re-pulled with rows
that were missing. So the daily question is not "what is the state" but "what
changed, and why".

Detecting a transition is bookkeeping. Attribution is the product, and it is
computed rather than narrated: an order is only named as a cause if it is
**load-bearing** — present in an explanation on the side it exists. An order that
arrived and is cited by nothing changed nothing, however suggestive the timing,
and asserting otherwise would be exactly the confident wrongness this engine
exists to refuse.

Simulated the real case by withholding 6% of orders from an earlier run:

```
21 settlements changed · 229 unchanged · 0 unattributed

resolved      12   ₹2,00,333
withdrawn      8   ₹1,59,514
recomposed     1     ₹5,001
```

**Then checked the transitions against ground truth, which is the part that
matters:**

```
RESOLVED     12 correct, 0 wrong    every new resolution landed on the truth
WITHDRAWN     5 withdrew a WRONG proof, 3 withdrew a correct one
RECOMPOSED    yesterday's proof was wrong (6 orders); today's is right (4)
```

Three findings fall out of that.

**More data makes the engine correct itself.** The single recomposition — the
alarming category, where the engine was certain twice and disagreed — resolved in
favour of the truth. Five of eight withdrawals removed a false proof.

**Withdrawal is not a regression, and labelling it as one would be wrong.**
PROVEN → AMBIGUOUS is usually the engine discovering that yesterday's uniqueness
was an artefact of a thinner pool. Yesterday's certainty was cheap because there
was less to be uncertain about. The diff labels these separately from real
regressions instead of lumping both under "worse", and the ground-truth check
says that call was right by 5 to 3.

**Every resolution was correct, 12 for 12.** When new evidence collapses an
ambiguity, the engine lands on the truth — which is the strongest available
argument that the 82% ambiguity rate is genuine under-determination rather than
weakness. The engine is not failing to decide. There is nothing there to decide
with, and the moment there is, it decides correctly.

Zero unattributed across all 21.
