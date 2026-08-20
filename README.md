# ATTEST

**Settlement reconciliation as constrained optimization.**
An LLM proposes hypotheses. A deterministic solver falsifies them. Nothing posts
unless it is proven.

> One bank credit of ₹47,382.19. Four hundred orders that week. **Which ones?**

Matching a credit to N orders is subset-sum — NP-complete. Fuzzy matchers reach
~70% and never diagnose that the residue is a different problem class.

## Status — D1 of 7

Deterministic floor only. No search, no model yet.

```
settlements              1,200
exact set match            4.8%
declined (to human)       95.2%
WRONG (moved money)        0.0%     precision 1.000 — it declines instead of guessing
blocking recall            0.999    ceiling; layer 0 discards nothing
wall clock                 0.34s
```

## Run

```bash
python3.13 -m venv .venv && ./.venv/bin/pip install -e .
./.venv/bin/python -m attest 1200
./.venv/bin/python -m attest 1200 --holdout   # run once, at the end
```

See [PRD.md](PRD.md) for the algorithm, the tolerance derivation, and the plan.
See [FAILURES.md](FAILURES.md) for what broke.
