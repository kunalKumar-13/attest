# Evaluation

## Ground truth by construction

Orders are generated first; settlements are derived **from** them. The mapping is
known exactly rather than approximately, and that is the single reason any figure
here can be defended.

It is also why Track 04 was the only tenable choice. Fraud detection would have
meant inventing the patterns and then detecting them — precision measuring the
author's imagination. Reconciliation has no such circularity.

## Fifteen hazard families

Frozen in `attest/generate/taxonomy.py` **before the matcher existed**, so the
benchmark cannot be tuned to flatter the engine. Every ground-truth row is
labelled with the family that produced it, so a miss is attributed to a named
cause rather than absorbed into a rate.

The one that decides the product's shape is `AMBIGUOUS_SUBSET`: two disjoint
subsets whose nets sum to the same value within tolerance, built from zero-MDR
UPI orders so the collision is exact. Arithmetic cannot say which is correct. A
matcher returning a single answer there is not more accurate than one returning
two ranked answers — it is the same accuracy, dishonestly reported.

Four families are **structurally unreachable** by an exact solver, because the
credit does not equal the sum of the true orders: `SPLIT_ORDER`,
`REFUND_OFFSET`, `CHARGEBACK_REVERSAL`, `ORPHAN_SETTLEMENT`. Those are model
gaps, not search failures, and widening the search cannot fix them (D10).

## One number cannot describe this engine

```
18.5% exact set recovery  +  98.1% proof precision
  is NOT
"98.1% accurate reconciliation"
```

The first is how often the complete truth is recovered. The second is how often
the engine is right *when it claims to be sure*. Blending them sells the second
while doing the work of the first.

| metric | what it measures |
|---|---|
| exact set recovery | complete ground-truth set recovered |
| **false proof rate** | **a claim of proof that was wrong — the number that moves money** |
| proof precision | right when it claims to be sure |
| coverage | resolved at all |
| ambiguity rate | correctly refused. A feature |
| blocking recall | the **ceiling** L0 imposes; any recall is read against it |
| accounted for | proven, or agreed by every surviving explanation |
| financial error rate | share of auto-posted **value** posted wrongly |
| safe resolution rate | resolved without a human, and allowed to be |

## Read `accounted for`, not `exact set recovery`

16% complete recovery reads like an engine that fails five times out of six. That
reading is wrong.

When several explanations survive, the orders in **every** one of them belong to
that settlement whichever is right. So the engine states that part as settled and
names the exact remainder in dispute. **77.5% of ambiguous value turns out not to
be in dispute at all**, and 67.3% of all processed value is accounted for.

A real case: ₹1,00,036.83 with four surviving explanations. Twenty-seven orders
worth ₹97,759.84 appear in all four. Only ₹7,292.03 across twelve orders is
contested, and the next step is not "investigate" — it is *a reference on any one
of those twelve settles the rest*.

## The seed panel

A single seed is an anecdote. The engine reported precision 1.000 for six days on
the strength of seed 20260821 alone; four other seeds produce 0, 1, 2 and 2 false
proofs (D7).

Every claim is pooled across a fixed five-seed panel, and the worst seed is
reported beside the aggregate. Pooling counts **pairs**, not per-seed precisions:
a mean weights a 250-settlement run identically to a 1,200-settlement one and
flatters whichever was small.

Calibration and evaluation seeds are **disjoint**. Fitting the risk model on the
portfolios it then judges reports its memory as its accuracy.

## Coverage is not a constant

```
250 settlements/seed   coverage 16.8%   false proof rate 0.80%
600 settlements/seed   coverage  8.5%   false proof rate 0.08%
```

Denser portfolios mean larger pools and more subsets landing within tolerance.
The engine is not worse on the bigger portfolio — the bigger portfolio is a harder
question, and the false-proof rate falls with it because the engine refuses more.
Any coverage figure quoted without its portfolio density is meaningless.

## Baselines

Same data, same candidate pools, so differences come from the algorithm.

```
matcher        exact    declined      WRONG       precision
exact-only      4.0%       96.0%     0   0.0%       1.000
fuzzy           3.2%       92.4%    11   4.4%       0.421
greedy          4.4%        5.2%   226  90.4%       0.166
ATTEST         20.8%       79.2%     0   0.0%       1.000
```

**Read the WRONG column.** Greedy declines 5% of the time and is wrong 90% of the
time — 226 of 250 settlements posted against orders that did not produce them.
That is what a matcher with no way to abstain does. Fuzzy, the industry default,
scores *below* doing nothing clever and buys it with 11 false proofs.

## Every false proof is attributed

```
5 across 1,250 settlements
  model gap       3    the truth is not expressible under the constraints
  search space    2    the truth was pruned before solving
  unattributed    0
```

Zero unattributed is the number that matters. A property test fails the build if
any false proof becomes unattributable, because an unexplained wrong answer is a
defect nothing currently accounts for.

## The property the engine actually has

Not *"ATTEST never produces a false PROVEN"* — it produces them at roughly 0.8%,
and asserting otherwise is what D7 cost. The true property is conditional:

> when the truth was in the candidate pool **and expressible under the
> constraints**, a PROVEN result is correct

Writing the condition down is what surfaced the model-gap failure class nobody
had named.

## Gates

The build fails on safety, never on accuracy. Money wrongly auto-posted and the
false-proof rate carry no tolerance; coverage metrics are advisory and may fall.
A symmetric gate would have argued for shipping D4, D8 and D12 — all three of
which correctly traded coverage for safety.
