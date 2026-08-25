# ATTEST — submission package

Everything below was verified against the commit being submitted. Nothing is
remembered.

---

## 1 · README review — what was found and fixed

The README's UI section described a **superseded product**. Found by reading it
against the running build, not by assumption:

| stale | actual |
|---|---|
| `SUBJECT × LENS` | `SUBJECT × LENS × CONTEXT` — context is a first-class, addressable part of the state model |
| all seven lens questions in pre-Phase-22 wording | the operator-voice set the product ships |
| *Financial State*, *Live events*, *Agents*, *Accuracy*, *AI trail*, *Act* | screens that no longer exist under those names |
| `processed ₹53,02,702.35`, `needs review ₹47,96,812.17` | the product renders `₹53,02,701.96` and `₹47,96,811.78` |

The money block was **not** inside a generated marker, so it had drifted by hand
and an evaluator running the demo would have seen different figures from the
front page. Replaced with an accurate description of the rail, the spine and the
blocker register. `./run-demo` is now the first line of **Run**.

Checked and found clean: every relative link and file path across 54 tracked
markdown files resolves; no occurrence of *production-ready*, *live Razorpay
reconciliation*, *real/production traffic*, *battle-tested* or *enterprise-grade*
except one deliberate negation — `RAZORPAY-INTEGRATION.md`: *"It is not
production-ready."*

## 2 · Demo rehearsal — what it corrected

Walked end to end in a browser. Every beat lands on real painted text at
**6 clicks / 7.7 s** of machine time. Two corrections came out of rehearsing
rather than writing:

**`back to the work` is not on screen after entering a case from the landing's
case list.** That is correct — the banner exists only when a case was entered
*through a blocker* — but the script had assumed it. It now says *press Back
three times*, with a note explaining why no button is drawn.

**`setl_000004` must not be substituted for `setl_000089`.** It is the first
example under blocker 1, and it reports **₹15,750.00 disputed against a
₹13,907.11 credit**. That is arithmetically correct — orders differing *between*
explanations overlap, so the disputed figure is a union, not a share — but on
stage it reads as an error. `setl_000089` divides cleanly: ₹97,759.84 agreed
plus ₹7,292.03 disputed against ₹1,00,036.83.

## 3 · Talk track

`docs/DEMO-SCRIPT-26.md` — three minutes, nine beats, every number read off the
screen. `docs/DEMO-60S-26.md` — the sixty-second cut, five clicks, four beats.

The moment both build to:

```
◇ MODEL    proposed     capture-batch
○ SOLVER   tested       NON DISCRIMINATIVE
● ENGINE   abstain      ABSTAINED

VERDICT UNCHANGED · NO FINANCIAL ACTION
```

## 4 · Screenshot and recording plan

Five stills, each carrying one idea no other carries. All at 1440×900, device
scale 2, taken from the running product.

| | screen | route | the idea |
|---|---|---|---|
| 1 | Landing | `/` | money stopped at a named stage; work ranked by what it unlocks |
| 2 | Evidence | `#/settlement/setl_000089/evidence` | `2,368 → 73 → 4`, and which cuts were only conventions |
| 3 | Investigate | `#/settlement/setl_000089/investigate` | model proposes, solver rejects, engine abstains |
| 4 | Policy | `#/settlement/setl_000020/policy` | an inequality, not a confidence score |
| 5 | Trust | `#/portfolio/trust` | what the system refuses to claim |

**Recording:** one continuous screen capture of the three-minute script, no cuts
and no post-production. The cold start shows `reconciling…` for ~2.6 s while the
engine reconciles 250 settlements — leave it in. It is real work, and cutting it
would be the one staged thing in the submission.

Do not record at a phone width. The dock and rail are correct there, but the
narrative reads left-to-right on a desktop.

## 5 · Submission checklist

- [x] README describes the product that ships
- [x] every internal doc link resolves
- [x] no overclaiming language
- [x] demo runs from one command on a clean checkout
- [x] three-minute and sixty-second scripts, both rehearsed
- [x] five canonical screenshots identified
- [x] limitations stated in the product, not only in the docs
- [x] clean-room verification passed

---

## Clean-room verification

| | |
|---|---|
| **submitted revision** | tag **`attest-submission`** — a commit cannot contain its own hash, so the tag is the identifier. `git rev-parse --short attest-submission` resolves it. |
| **tests** | **297 passed** (full stack: Playwright, server running, `ortools`) |
| **browser contracts** | **133**, counted by `ci/verify.sh` from the source |
| **safety gates** | **6 / 6 PASS**. `money wrongly auto-posted` and `false proof rate` at **+0.0000** in both environments |
| **adversarial** | **34 attacks · 34 defended · 0 breached · 0 harness errors**, re-run in the clean room |
| **clean checkout** | `python3.13 -m venv` → `pip install -e .` → import, gates, adversarial, demo — all pass |
| **demo startup** | `./run-demo` → `http://localhost:8420`, verified from the clean checkout |

A clean room without `ortools` and without the optional Rust kernel runs the
numpy path, and the three **coverage** gates read slightly lower there
(`proof precision` 0.9506, `safe resolution` 0.0160, `exact set recovery`
0.1540). `docs/REPRODUCE.md` states this — *"the engine runs without it, and the
numbers differ"* — and the gate reports it as an allowed trade. The two
**safety** gates are identical to four decimal places in both environments,
which is the property that matters.

### Known limitations, stated plainly

1. **No live Razorpay account has ever been contacted.** The adapter performs a
   real authenticated request and has never been called with real credentials.
   The product says so on the Trust lens, first, unprompted.
2. **The dataset is generated** — seed 20260821, 250 settlements, 2,368 orders.
   Ground truth is what makes a false-proof rate knowable, and it is a population
   ATTEST created. It is not production traffic.
3. **The bank statement is simulated.** Every credit matches its settlement by
   construction, so the adapter cannot exercise the one case the engine exists
   for — a credit corresponding to no single settlement.
4. **Coverage is 16%**, not 90%. Most settlements are correctly refused rather
   than resolved.
5. **`docs/EVALUATION.md` describes a five-seed panel**; pooled claims come from
   the two held-out evaluation seeds, the other three being calibration. The
   product flags this itself as one of its eleven NOT VERIFIED boundaries. Left
   as-is because the Trust claim that reports it lives in frozen code, and a
   self-reported discrepancy is worth more than a quietly corrected one.
6. **The rail's held amount is clipped at 360px** by its 25vh cap. It scrolls.

### Files that constitute the submission artifact

```
README.md                     the front door
run-demo                      one command
docs/PRODUCT-THESIS-26.md     what enters, what it computes, what it refuses
docs/DEMO-SCRIPT-26.md        three minutes, rehearsed
docs/DEMO-60S-26.md           sixty seconds, rehearsed
docs/SUBMISSION-26.md         this file
docs/ARCHITECTURE.md          the pipeline and its boundaries
docs/EVALUATION.md            method, panel, and what the numbers mean
docs/DECISIONS.md             what was chosen and what it cost
docs/RAZORPAY-INTEGRATION.md  IMPLEMENTED / SIMULATED / NOT VERIFIED
FAILURES.md                   24 recorded failures, with what changed
attest/                       the engine, the kernel, the adapters, the UI
tests/                        297 tests, 133 of them browser contracts
ci/verify.sh                  ten stages, counts its own contracts
benchmark/                    the artifacts every claim is read from
```
