# Judge strategy — and the P0 we found

Researched from [razorpay.com/buildathon](https://razorpay.com/buildathon/) and
corroborating sources. The full extraction is in `COMPETITION-INTELLIGENCE.md`;
this answers the ten questions and records what we changed because of them.

---

## The bar, verbatim

> **Track 04 — AI Finance Controller:** *"Throughput plus measured accuracy plus
> an honest exception list. One cherry-picked match proves nothing."*

Submission: a public repository, a **5-minute pitch video**, architecture
documentation. *"No resume screening. No aptitude test."* Closes **5 September
2026**.

Named evaluation dimensions: **AI Judgment** — *"whether AI tools, LLMs, or
agents were applied appropriately instead of forcing unnecessary tech stacks"* —
and **Failure Recovery** — *"how the applicant identified system failures at
runtime and engineered graceful fallbacks."*

---

## The ten questions

**1 · What is actually being judged?** Throughput, measured accuracy, an honest
exception list — and whether AI was used *appropriately* rather than forced.
Not model sophistication.

**2 · What makes a submission memorable?** A claim the judge can check. Most
demos assert; almost none hand over a number that could embarrass them.

**3 · What makes one credible?** Reproducibility, and naming what you did not
verify before being asked.

**4 · What gets penalised?** Forced AI. Cherry-picked results. The bar says so
in its own sentence.

**5 · What makes a judge stop watching?** A minute of preamble; a tour of
navigation; a number that cannot be traced.

**6 · What makes them watch all five minutes?** Something changing every 10–20
seconds, and a claim that escalates rather than repeats.

**7 · What makes them believe the builder?** Being told the weakness first. Our
strongest credibility asset is `exact_only` beating us on precision, published
in our own README.

**8 · What makes a technically impressive project lose?** It cannot be run. A
judge who cannot reproduce the demo discounts everything else — **which is
exactly the defect we found.**

**9 · What makes a simpler project win?** It is legible in thirty seconds and
survives one hard question.

**10 · What can ATTEST uniquely own?** *We measured our own AI, found it worse
than a coin flip, and removed it from the authority path.* Against **AI
Judgment**, that is stronger than any accuracy claim — and it cannot be
retrofitted in ten days by a competitor, because it requires having measured.

---

## The P0, and how it was resolved

### What was wrong

`attest/subsetsum.py`:

```python
MAX_TARGET_PAISE = 20_000_000 if _native_reachable is not None else 3_000_000
```

The optional Rust kernel widens the solver envelope from ₹30,000 to ₹2,00,000.
Building it needs a Rust toolchain, which the README correctly calls *optional*.

The canonical demo settlement was **`setl_000089`, ₹1,00,036.83** — above the
portable envelope. Measured on a clean extraction with `pip install -e .`:

```
                   default install         with the kernel
setl_000089        INSUFFICIENT, 0 proofs  AMBIGUOUS, 4 explanations
PROVEN                    51                      52
AMBIGUOUS                161                     197
CONTRADICTED               1                       1
INSUFFICIENT              37                       0
top blocker        ₹25,58,683.75 / 37      ₹47,96,811.78 / 197
cold start                18.2s                   ~2.5s
```

**A judge following our own README could not reproduce our demo.** Against a bar
whose sentence is *"one cherry-picked match proves nothing"*, being unable to
reproduce the one match is the worst available failure.

### What we considered

**Raise the portable envelope to match.** Measured: it reproduces the kernel's
verdicts **exactly** — PROVEN 52, AMBIGUOUS 197, CONTRADICTED 1 — at **46.6s**
against 18.2s for 250 settlements. Rejected on cost: a 47-second cold start
would break the demo and time out the browser contracts. The envelope is a
resource guard, not a correctness boundary, and it is doing its job.

**Ship a prebuilt binary.** Cross-platform wheels for a submission a judge may
open on any OS. Fragile, and `*.so` is deliberately untracked.

**Make Rust a hard dependency.** Would make `pip install -e .` fail for most
judges. Strictly worse.

### What we did

**Moved the canonical case to one decided identically on both paths.**

`setl_000225` — **₹27,208.12**, below the portable envelope, **AMBIGUOUS with
four surviving explanations whether or not the kernel is installed**. Verified
on the native path and on a real clean-room extraction with no Rust toolchain.

```
₹27,208.12   credit
4            explanations satisfy it exactly
₹25,330.46   agreed by every one of them, across 6 orders
₹5,603.30    turns on which is right, across 11 orders
```

**Zero engine change.** No verdict logic, no policy, no kernel, no gate touched.
We chose a different settlement to demonstrate, because 28 of them qualify.

**And made the difference self-explaining.** The bar now reads
`ATTEST · GENERATED · PORTABLE` or `· NATIVE KERNEL`, read from the module. A
reader comparing their screen against a recording is told which envelope
produced their figures.

**Pinned by `tests/test_reproducibility.py`** — six tests asserting the
canonical case is identical on both paths, that it sits inside the portable
envelope, that every settlement has a disposition on either path, and the exact
portfolio disposition under each. The case that *could not* reproduce is pinned
as still not reproducing, so nobody quietly widens the cap and calls it fixed.

### What this buys beyond correctness

The portable install has **four** dispositions rather than three, and the extra
one is `INSUFFICIENT` — *the solver refusing to attempt what the reference
cannot decide*. That is the product's own thesis applied to its own
infrastructure, and it only appears on the install a judge will actually
perform.

> *"Thirty-seven settlements are beyond what the portable engine can decide. It
> reports that rather than guessing. Install the optional kernel and those
> thirty-seven become ambiguous for the same reason as the other hundred and
> sixty-one — it decides more, it does not decide differently."*
