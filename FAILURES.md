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
