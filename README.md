# ATTEST

**Settlement reconciliation as constrained optimization.**

An LLM proposes hypotheses. A deterministic solver falsifies them. Nothing posts
unless it is proven.

> A merchant's bank statement shows one credit: **₹47,382.19**. It is the net of
> some subset of the 400 orders they captured that week — minus per-transaction
> fees, minus GST on those fees, offset by a refund, shifted T+2 by the
> settlement calendar.
>
> **Which orders?**

Matching one credit to N orders is subset-sum: NP-complete. Fuzzy matchers reach
roughly 70% and never diagnose that the residue is a different problem class.
This is resolved by hand, in Excel, daily, at effectively every merchant in India.

---

## The engine does not emit a confidence score

`97%` is not interpretable. It does not say what would have to be true for the
answer to be wrong, it cannot be audited, and it invites a threshold — and a
threshold invites posting an entry nobody can defend.

Instead every settlement receives a **decidable property of the constraint
system**:

| | |
|---|---|
| 🟢 **PROVEN** | exactly one assignment satisfies every constraint |
| 🟡 **AMBIGUOUS** | two or more do — the engine reports them and stops |
| 🔴 **CONTRADICTED** | none does — the engine reports which constraints conflict |

These are **counted, not estimated**. The solver saturates its subset counter at
two, because the question is never *how many* explanations exist, only whether
the explanation is *unique*. Two bits per reachable sum decides the verdict.

### The trusted kernel

The prover is large: blocking, a counting DP over the amount axis, constraint
propagation, model-proposed hypotheses. The verifier is **28 lines**
(`attest/verdict.py::check`), depends on none of it, and recomputes every value
from source records rather than trusting a single field on the proof.

A proof is accepted only if the kernel accepts it.

> A bug anywhere in the prover can cost recall. It cannot post a wrong entry.

Same reason a proof assistant separates its kernel from its tactics.

---

## Measured

Ground truth is exact by construction: orders are generated first, and
settlements derived *from* them. Fifteen hazard families
(`attest/generate/taxonomy.py`) are frozen — written before the matcher, so the
benchmark cannot be tuned to flatter the engine.

```
5 seeds × 250 settlements · pooled

  exact set match             18.5%
  WRONG (moved money)             5      0.4%
  pair precision              0.981
  blocking recall (ceiling)   0.956
  wall clock                  0.70s per seed

  seed        20260821  314159  271828  555001  999983
  WRONG              0       0       1       2       2
```

**Every figure here is pooled across a fixed five-seed panel, and the worst seed
is reported alongside it.** This project spent six days claiming precision 1.000
on the strength of seed 20260821 alone; an adversarial sweep found four other
seeds producing 0, 1, 2 and 2 false proofs. A single seed is an anecdote. See
[FAILURES.md](FAILURES.md), D7 — it is the most useful entry in the file.

**A decline is a correct outcome.** The engine is built to refuse rather than
guess, so `declined` is a feature and `WRONG` is the only real failure.

### Against reference matchers, same data, same pools

```
matcher        exact    declined      WRONG       precision   (seed 20260821)
-----------------------------------------------------------
exact-only      4.0%       96.0%     0   0.0%       1.000
fuzzy           3.2%       92.4%    11   4.4%       0.421
greedy          4.4%        5.2%   226  90.4%       0.166
ATTEST         20.8%       79.2%     0   0.0%       1.000
```

Baselines are still single-seed and are being re-run across the panel; the
comparison holds directionally but the ATTEST row should be read as 18.5% / 0.981
pooled, not 20.8% / 1.000.

**Read the WRONG column.** `greedy` declines 5% of the time and is wrong 90% of
the time — 226 of 250 settlements posted against orders that did not produce
them. That is what a matcher with no way to abstain actually does. `fuzzy`, the
industry default, scores *below* doing nothing clever and buys it with 11 false
proofs.

Greedy fails structurally, not by tuning: taking the largest order that fits is a
local decision, and subset-sum has no greedy-choice property. One early take
consumes an order a correct explanation needed and there is no way back.

Full methodology in [eval/BASELINES.md](attest/eval/BASELINES.md).

### A feature that was measured and then disabled

Cross-settlement constraint propagation (`attest/evidence.py`) works — an order
belongs to exactly one settlement, so settlements are evidence about each other.
It is off by default:

```
                  exact     WRONG    precision      (seed 20260821)
off               20.8%      0.0%      1.000
on                24.0%      3.6%      0.829
```

Three points of exact-set match, bought by going from **zero** false proofs to
nine. One bad seed amplifies across the population, because propagation is only
as sound as what it propagates from. A change that raises exact-set match by
three points is not an improvement if it raises false proofs by the same amount.
See [FAILURES.md](FAILURES.md), D4.

---

## Run

```bash
python3.13 -m venv .venv && ./.venv/bin/pip install -e .

./.venv/bin/python -m attest.web        # local UI on :8420, opens a browser
./.venv/bin/python -m attest 250 --sweep   # the five-seed panel — report THIS
./.venv/bin/python -m attest 250        # a single seed
./.venv/bin/python -m attest 250 --html # emit report.html
ATTEST_PROP=1 ./.venv/bin/python -m attest 250   # reproduce the D4 ablation
```

The UI runs a generated portfolio or takes your own `orders.csv` and
`settlements.csv`. Stdlib only — no framework, no build step, and nothing leaves
the machine. It leads with rupees rather than row counts, because the question a
merchant has is never "what is your exact-set match rate", it is **how much of my
money is accounted for, and what happened to the rest.**

```
processed         ₹53,02,702.35
auto-reconciled    ₹4,99,574.15     proven — arithmetic you can check by hand
needs review      ₹47,96,812.17     more than one explanation fits; both shown
unexplained           ₹6,316.03     no subset satisfies the constraint
false proofs                   0
```

Optional: build the Rust kernel for the wider envelope and the 52× DP.

```bash
cd native && maturin develop --release
```

## Layout

```
attest/model.py        fee model, tolerance derivation, records
attest/verdict.py      PROVEN/AMBIGUOUS/CONTRADICTED + the 28-line kernel
attest/blocking.py     calendar-inverted candidate generation, escalating
attest/subsetsum.py    counting DP over the amount axis
attest/evidence.py     cross-settlement propagation (off by default)
attest/generate/       hazard taxonomy + generator — FROZEN
eval/                  harness, baselines, ablations
native/                Rust port of the DP hot path
```

## The kernel

The DP is three ALU ops per cell and re-reads an array the width of the credit
once per order. It is bandwidth-bound, not compute-bound, so the only
optimisation that matters is **making the array smaller**.

Two bits is the floor — the verdict only distinguishes none / one / more than
one. Rather than interleaving 2-bit lanes, which forces lane-masking on every
shift, the counter is split into two **bitplanes** of one bit per sum: `one[s]`
and `many[s]`, mutually exclusive, so together they encode 0/1/2 exactly and each
shifts with a plain bit-shift. The saturating add becomes six bitwise operations
over 64 sums at a time:

```
both  = (one | many) & (s_one | s_many)     // both sides non-zero ⇒ ≥ 2
many' = many | s_many | both
one'  = (one | s_one) & !both
```

```
credit        numpy      native    speedup
₹20,000      275.6 ms   17.11 ms     16.1×
₹80,000    1,342.8 ms   25.46 ms     52.7×

DP footprint at ₹200,000:  4.8 MB   (one byte per sum would be 19.5 MB)
```

The speedup widens with credit size, which is what a bandwidth-bound kernel
should do. **Verified byte-identical to the numpy reference over 1,777 instances
and 1.32 × 10¹¹ DP cells, across all fifteen hazard families** — `tobytes()`
compared, not `array_equal`, because `solve` sums a slice of this array and a
dtype difference would change the sum.

This is not a benchmark flourish. The Python reference could only afford a
₹30,000 envelope, which silently skipped **14.8% of the portfolio** — including
*every* large bundle — before a single subset was examined. The port is what made
those settlements reachable at all. Without the extension the engine falls back
to numpy and a narrower envelope, and still runs correctly.

## Documents

- **[PRD.md](PRD.md)** — the problem, the algorithm, the tolerance derivation, the plan
- **[FAILURES.md](FAILURES.md)** — what broke, daily. Four entries and counting
- **[AGENTS.md](AGENTS.md)** — the working agreement, enforced by `.githooks/pre-commit`
- **[native/BENCH.md](native/BENCH.md)** — parity methodology and benchmarks
