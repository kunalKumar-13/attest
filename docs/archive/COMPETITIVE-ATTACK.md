# Attacking ATTEST

Written to eliminate the submission, not defend it. Each objection is rated for
**danger** (how likely it is to cost us selection) and marked **VALID** where it
is genuinely true.

---

## The two that could actually kill us

### 1 · "Your demo case doesn't exist on a clean install." — **VALID · CRITICAL**

Measured today, not hypothesised. On a default install — `python3.13 -m venv
.venv && pip install -e . && ./run-demo`, exactly what the README documents —
the canonical settlement is **`INSUFFICIENT` with zero proofs**:

```
                   default install        with the Rust kernel
setl_000089        INSUFFICIENT, 0        AMBIGUOUS, 4 explanations
top blocker        ₹25,58,683.75 / 37     ₹47,96,811.78 / 197
blocker count      4                      3
```

The Rust kernel widens the solver envelope, so 37 settlements the numpy path
declares out-of-envelope are actually solved. Building it needs `cd native &&
maturin develop --release` and a Rust toolchain — which the README lists as
*optional*.

**So a judge who follows our own instructions cannot reproduce our demo.** The
video would say ₹47,96,811.78 across 197 settlements; their screen would say
₹25,58,683.75 across 37, and the four-explanation case at the heart of the pitch
would not be ambiguous at all.

Against a track whose bar is *"one cherry-picked match proves nothing"*, being
unable to reproduce our one match is the worst available failure. **P0.**

### 2 · "This is one cherry-picked match." — **VALID as presented · CRITICAL**

The bar says it in those words. Our three-minute script, sixty-second script and
five canonical screenshots all revolve around `setl_000089`. The population
evidence exists — 250 settlements fully accounted for, a 500-settlement
benchmark against two baselines — but the demo leads with the anecdote and
reaches the population late or never.

We have the throughput and the exception list. We are presenting them second.
**P0, and cheap to fix: reorder the story, not the product.**

---

## Serious, answerable

| # | objection | valid? | danger | where the answer is |
|---|---|---|---|---|
| 3 | "Just subset-sum with a UI." | partly | high | Search-space integrity — a proof is bound to the universe it was found in. **In the code and Evidence; weak in the README.** |
| 4 | "Why AI at all? It barely does anything." | fair | high | We measured it: 27/63 correct. It proposes; it never decides. **The measurement is now on screen (F2).** |
| 5 | "The data is synthetic." | true | medium | Ground truth is what makes a false-proof rate knowable. Product says `GENERATED` on every screen. |
| 6 | "This isn't actually Razorpay." | true | high | Adapter boundary is real and tested; live validation is `NOT VERIFIED` and stated first. **Turn into a strength, see §Razorpay.** |
| 7 | "Exact matching already solves this." | no | medium | 22 of 500 decided, 478 declined. Published in our own README. |
| 8 | "The AI benchmark is weak — 42.9% is bad." | inverts | medium | That is the point. The measurement *caused* the architecture. |
| 9 | "It doesn't resolve the hard cases." | true | high | It resolves 84 and **names** the rest with what would unblock them. Refusing is the product. |
| 10 | "Seven lenses is over-engineered." | fair | medium | Each answers one question; the dock states them. But a judge sees seven tabs in 5 minutes. **Demo must never tour them.** |
| 11 | "Too complicated for 30 seconds." | fair | high | Landing answers 6 of 10 stranger questions at zero clicks. Measured 10/10 overall. |
| 12 | "An engineering exercise, not a product." | fair | high | The blocker register is operator work, ranked by value unlocked. |
| 13 | "No real operator value." | no | medium | *"Supply an order-level reference"* is a schema change, not 197 tickets. |
| 14 | "Another team could build this with an LLM wrapper." | no | medium | The wrapper is what we measured and rejected. That is the submission. |
| 15 | "Not novel — reconciliation is old." | partly | medium | The novelty is the authority boundary, not the matching. |
| 16 | "The proof system is unnecessary." | no | low | CORE-001/002 are the counter-evidence: without it, a forged PROVEN posts. |
| 17 | "Demo needs too much explanation." | risk | high | Mitigated only by the story order. |
| 18 | "UI is impressive, product isn't." | risk | medium | Blur test shows money and collapse survive; no cards, no charts. |
| 19 | "Doesn't demonstrate enough AI." | fair | high | Against **AI Judgment** this inverts — but only if we say so explicitly. |
| 20 | "Throughput is small — 250 settlements." | fair | medium | 500 in the benchmark panel across seeds. **Lead with the panel.** |
| 21 | "Where is the runtime failure recovery?" | **gap** | high | We have fail-closed design and 24 recorded failures, but the demo never shows a **runtime** failure handled. **See P1-1.** |
| 22 | "No audit trail shown." | **gap** | medium | Activity is the audit trail and the demo skips it. |

---

## What the attack changes

Three things, in order of danger:

1. **The demo must reproduce on a clean install.** Non-negotiable.
2. **The story must lead with the population, then drill into the case.** The
   bar demands throughput + accuracy + exception list; we have all three and
   present the anecdote first.
3. **"Failure Recovery" and "audit trail" are named evaluation dimensions we
   currently do not demonstrate live.** We have the material — webhook
   rejection, adapter rejection, the event trail — and show none of it.
