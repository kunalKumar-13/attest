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
250 settlements · seed 20260821

  exact set match             20.0%
  declined to a human         79.6%
  WRONG (moved money)          0.4%     ← the number that matters
  pair precision              0.983
  blocking recall (ceiling)   0.956
  wall clock                  10.5s
```

**A decline is a correct outcome.** The engine is built to refuse rather than
guess, so `declined` is a feature and `WRONG` is the only real failure.

### A feature that was measured and then disabled

Cross-settlement constraint propagation (`attest/evidence.py`) works — an order
belongs to exactly one settlement, so settlements are evidence about each other.
It is off by default:

```
                  exact     WRONG    precision
off               20.0%      0.4%      0.983
on                23.2%      3.6%      0.807
```

Eight more correct answers, eight more wrong ones. One false proof seeds error
amplification across the population. A change that raises exact-set match by
three points is not an improvement if it raises false proofs by the same amount.
See [FAILURES.md](FAILURES.md), D4.

---

## Run

```bash
python3.13 -m venv .venv && ./.venv/bin/pip install -e .
./.venv/bin/python -m attest 250
ATTEST_PROP=1 ./.venv/bin/python -m attest 250    # reproduce the D4 ablation
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

## Documents

- **[PRD.md](PRD.md)** — the problem, the algorithm, the tolerance derivation, the plan
- **[FAILURES.md](FAILURES.md)** — what broke, daily. Four entries and counting
- **[AGENTS.md](AGENTS.md)** — the working agreement, enforced by `.githooks/pre-commit`

Built for the Razorpay AI Buildathon, Track 04 — AI Finance Controller.
