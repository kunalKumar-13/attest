# Decisions

An ADR log of decisions already made, each with what it cost. Reconstructed from
`FAILURES.md` and the commit history, not from memory.

---

### ADR-1 · Track 04, because ground truth is constructible
**Status** accepted

Fraud detection means inventing the patterns and then detecting them; precision
measures the author's imagination. Reconciliation lets orders be generated first
and settlements derived from them, so the mapping is known exactly.

**Consequence** every accuracy figure is defensible. No other candidate allowed
that claim.

---

### ADR-2 · Meet-in-the-middle, abandoned
**Status** superseded by ADR-3 · D2

MITM is viable to roughly n=45. Measured pools: p50 = 899. 2^449 per side.

**Consequence** the estimate had been invented rather than measured, and was
wrong by twenty-fold. Measure before optimising.

---

### ADR-3 · Counting DP over the amount axis
**Status** accepted

O(n·target) rather than O(2^(n/2)). The saturating counter also makes
PROVEN/AMBIGUOUS/CONTRADICTED a computed property rather than a threshold.

**Consequence** the bug forced a better architecture than the plan had.

---

### ADR-4 · Verdicts are counted, never scored
**Status** accepted

`97%` is not interpretable, cannot be audited, and invites a threshold. Solution
count is a fact about the model.

**Consequence** no confidence number anywhere in the product.

---

### ADR-5 · Cross-settlement propagation, built and disabled
**Status** rejected · D4

+3.2pp exact for +3.2pp WRONG. One false proof consumed orders it did not own and
manufactured eight more across four rounds.

**Consequence** a change that raises exact-set match by three points is not an
improvement if it raises false proofs by the same amount.

---

### ADR-6 · Rust is load-bearing, not a benchmark
**Status** accepted · D5

The ₹30,000 Python envelope silently skipped 14.8% of the portfolio — every large
bundle — before a single subset was examined.

**Consequence** the port is the difference between attempting 85% of the
portfolio and all of it. Opening the envelope also removed the last false proof.

---

### ADR-7 · Every claim is pooled across a fixed seed panel
**Status** accepted · D7

Precision 1.000 survived six days past the measurement that refuted it. Five
seeds give 0, 0, 1, 2, 2.

**Consequence** a number with two homes will disagree with itself.
`benchmark/results.json` is the only origin.

---

### ADR-8 · An anchor may select, never create uniqueness
**Status** accepted · D8

Anchoring *before* the search resolved 92 abstentions and got 32 wrong.
Uniqueness inside a restricted space is not uniqueness.

**Consequence** the corrected version is sound and *worse* — 0.521, a coin flip —
which is the useful result: there is no signal to select on, because the generator
emits no order-level reference.

---

### ADR-9 · Risk is priced at the Wilson upper bound
**Status** accepted · D9

The point estimate 1/152 under-priced realised loss by 5.6× on held-out data.

**Consequence** auto-post fell 15.2% → 7.6%. Being wrong about your own error
rate is acceptable in exactly one direction.

---

### ADR-10 · Hungarian rejected for global selection
**Status** accepted · ADR-11 supersedes the packing

Hungarian solves one-to-one matching and cannot express "candidate A conflicts
with candidate B because both claim order #17". That is set packing.

---

### ADR-11 · CP-SAT packing rejected, unsat cores shipped
**Status** accepted · D12

+0.64pp exact for +0.32pp WRONG, a straight regression at n=1200, and the gain
not even consistent in sign.

**Consequence** the valuable output was the measurement that said not to ship it,
plus a by-product nobody set out to build.

---

### ADR-12 · Rules are beliefs, and versioned
**Status** accepted · D16

Constants let the engine check its assumptions against themselves. A ₹2 flat fee
takes the share of true bundles that balance from 85% to 0%.

**Consequence** "coverage collapsed" and "your fee schedule is wrong" are the
same observation, and only one is actionable.

---

### ADR-13 · Against a real gateway, reconciliation is largely a join
**Status** accepted · D17

Razorpay's recon report carries `order_id`, `payment_id` and `settlement_id` on
the same row — the evidence D8 concluded was missing.

**Consequence** the honest framing is that the solver is the fallback for where
the join fails: recon unavailable, bank-statement reconciliation, adjustments with
no linked entity. Those are the hard cases and the reason the engine exists.

---

### ADR-14 · No agent holds a write capability
**Status** accepted · D19

Defined and granted to none, enforced at construction. An absence is silent; a
refusal is auditable.

---

### ADR-15 · Gates fail on safety, never on accuracy
**Status** accepted · D20

Verified by re-enabling ADR-5: exact recovery improves two points while the build
fails.

**Consequence** a symmetric gate would have argued for shipping ADR-5, ADR-8 and
ADR-11.
