# Final submission check

Every row below was verified against a running instance or the artifact named,
not from memory. Anything not checked says so.

**Git revision** `87f2ce0` (this file is committed on top of it)
**Tag** none — to be applied at submission
**Date of check** 2026-08-27

---

## Execution paths

The recorded demo uses the **native kernel**. A clean checkout without a Rust
toolchain runs the **portable** solver, whose envelope is ₹30,000 instead of
₹2,00,000. The divergence is the envelope and nothing else.

| | native kernel | portable |
|---|---|---|
| solver envelope | ₹2,00,000 | ₹30,000 |
| 250 population | 250 settlements · 2,368 orders | identical |
| split | **52 / 197 / 1**, 0 insufficient | **51 / 161 / 1**, 37 insufficient |
| match rate | 20.8% | 20.4% |
| held at verification | ₹48,03,127.81 across 198 | ₹49,16,887.51 across 199 |
| top blocker | ₹47,96,811.78 · 197 | ₹25,58,683.75 · 37 |
| canonical case | setl_000225 · AMBIGUOUS · ₹27,208.12 | **identical** |
| narrowing | 2,368 → 164 → 4 | **identical** |
| AI benchmark | 27 of 63 · 42.9% | **identical** |
| benchmark panel | 500 = 2 seeds × 250 | **identical** |
| gates · adversarial · isolation · kernel | 6/6 · 34/34/0 · 21/21 · 28 lines | **identical** |

The 37 are settlements whose candidate space exceeds what the portable solver
will attempt. It reports INSUFFICIENT rather than searching a space it cannot
finish. That is the same refusal this product is about, applied to compute
instead of evidence — not a failure to reconcile them.

---

## Gate results

| | State | How checked |
|---|---|---|
| **NATIVE reproduction** | **PASS** | 20/20 rehearsal items VERIFIED against a live native instance |
| **PORTABLE reproduction** | **PASS** | clean clone of `87f2ce0`, fresh venv, no Rust — produced 51/161/1/37 as documented; `run-demo` named the path first |
| **Canonical cross-path identity** | **PASS** | `tests/test_execution_paths.py` — case is ₹27,208.12, an order of magnitude under even the portable cap |
| **README** | **PASS** | reproduce section at line 26, both paths tabled, native build in the path, all 66 markdown files' links resolve |
| **run-demo** | **PASS** | prints `ATTEST · GENERATED · <PATH>` and the envelope **before** any portfolio figure; portable branch explains INSUFFICIENT and gives the build command |
| **Video script** | **PASS** | every portfolio figure now labelled native; 843 spoken words; no figure spoken that is not on the front door |
| **Tests** | **346 passed**, 0 failed | full suite |
| **Contracts** | **168** browser contracts | `tests/test_shell_contract.py` |
| **Gates** | **6/6 PASS** | `/api/claims` |
| **Adversarial** | **34 attacks · 34 defended · 0 breached** | `benchmark/adversarial.json` |
| **Stranger** | **10/10** above the fold | harness |
| **Comprehension** | **10/10** | ten-question audit |
| **Track-04 questions** | **10/10** | ten-question probe |
| **Responsive** | **7 widths**, zero overflow, zero console errors | 360 → 1512 |
| **Contrast** | **0 under AA** on both surfaces | composited-alpha checker |
| **Clean checkout** | **PASS** | clone → venv → install → serve → verified |

---

## Claims discipline — re-verified

- No production-ready claim anywhere.
- No confidence score anywhere; the engine does not emit one.
- No live Razorpay claim. Live account validation reads NOT VERIFIED on the
  product's own Trust instrument.
- No "four times" claim (retired in an earlier phase; the real ratio was 3.818×).
- ₹6,316.03 is marked workspace-only and explicitly not speakable.
- 197 ambiguous and 198 held at verification are kept distinct in every
  document; the difference is the single contradicted case.
- Every percentage in the README matches a registered claim in
  `docs/CLAIMS.md`, enforced by `test_no_percentage_in_the_readme_is_unaccounted_for`.

---

## Known limitations, stated on the product itself

Live account validation not verified · bank statement simulated · pagination
not verified · the adapter is trusted (if it lies, the verdict is wrong and we
would not know) · the solver envelope caps at ₹2,00,000 native / ₹30,000
portable · the anchoring loop measures 42.9% and is therefore disabled as a
decider.

---

## Outstanding

**The five-minute pitch video.** Script, shot list and recording guide are
ready (`docs/DEMO-SCRIPT-35.md`, `docs/DEMO-SHOTLIST-35.md`,
`docs/VIDEO-README-35.md`). Build the native kernel first and confirm
`run-demo` prints `NATIVE KERNEL` before recording.
