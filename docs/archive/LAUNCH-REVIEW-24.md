# Phase 24 — Launch Readiness Review

Twelve states captured at four widths — 1440, 1024, 768, 390 — and walked as a
product, not as a test suite. **No code was changed.** §15 caps this phase at
five changes; the review found **two** worth making, two worth deferring, and
everything else already correct.

---

## §1 · The walkthrough

**Zero horizontal overflow at any of the 48 screens.** The hierarchy holds at
every width: the rail's amount and the room's conclusion figure are the two
largest things on desktop, and on a phone the room's figure takes the 34px slot
while the rail's identity steps down to 20px — the correct priority for a small
screen, since the conclusion outranks the label.

Answering §1's eight questions on the canonical screens:

| | eye hits first | second | conclusion | where the money is |
|---|---|---|---|---|
| **Landing** | ₹53,02,701.96 | ₹47,96,811.78 | *one change unlocks 197 settlements* | rail spine: ₹48,03,127.81 held at verification |
| **Evidence** | ₹1,00,036.83 | ₹7,292.03 | *no unique proof* | the dispute, at 34px |
| **Investigate** | ₹1,00,036.83 | *Verdict unchanged* | *engine abstained* | the case amount, in the rail |
| **Policy (proven)** | ₹353.73 | ₹135.49 | *AUTO-POST* | expected loss against review cost |
| **Trust** | ₹53,02,701.96 | NOT VERIFIED | *live Razorpay validation not verified* | the portfolio, in the rail |
| **Contradicted** | ₹6,316.03 | ₹447.05 | *no combination explains this credit* | the unresolved residual |

*Does this look like a financial system or a web app?* — a financial system. The
evidence is not opinion: there is no card, no shadow, no gradient, no icon set,
no illustration; every surface is a hairline, an indent or a proportional bar;
every amount is monospace and tabular; and the vocabulary scan below returns
nothing from the SaaS lexicon.

---

## §2 · The five canonical screens

All five exist and each carries one complete idea.

| | screen | the one idea |
|---|---|---|
| 01 | Landing | money stopped at a named stage, and the work is ranked by what it unlocks |
| 02 | Evidence | `2,368 → 73 → 4` — the proof happened inside a universe narrowed by conventions |
| 03 | Investigate | `◇ MODEL → ○ SOLVER → ● ENGINE` — the model participates, the engine decides |
| 04 | Policy | expected loss against review cost — automation is governed, not guessed |
| 05 | Trust | `NOT VERIFIED`, then eleven boundaries — an adversarial inspection surface |

§3's rule holds: they are five instruments from one system, sharing the rail,
the spine, the type scale and the actor language, and differing only in what
each asks. **Nothing is combined into a composite, a timeline or a hero.**

---

## §4 · The visual signature — confirmed, not invented

The three elements are already there and they are the right three:

1. **The state spine** — `SOURCE → MATCHING → VERIFICATION → POLICY → ACTION`,
   on every screen, with the collapse drawn proportionally.
2. **The three-actor language** — `◇ MODEL / ○ SOLVER / ● ENGINE`, measured as
   shape plus fill (`border-radius: 2px` against `999px`, hollow against
   filled), so it survives grayscale.
3. **The proportional money collapse** — full-width green at source, a stub at
   verification, a hairline at action.

No logo work is needed. The system is the identity.

---

## §5 · Typography, including the edge cases

Nine financial roles, each with one type size: ENTERED 34px, HELD 20px, VALUE
BLOCKED 20px, AGREED/DISPUTED 15px, CONTINUES 13px, run ladder 13px. All
monospace, all tabular.

Edge cases, all present in the live UI and all correctly set:

| case | example on screen |
|---|---|
| negative | `−₹1.20` |
| zero | `₹0.00` (three times in Journal — the balanced-by-absence point) |
| percentage | `53% span one capture date` |
| date | `value date 2026-05-25` |
| long identifier | `policy_661e43db9242` |

One latent inconsistency, not currently visible: the JavaScript formatter emits
`−` (U+2212 MINUS SIGN) and the Python formatter emits `-` (ASCII hyphen). No
Python-produced amount is negative in any current state — expected loss, residuals
and disputed amounts are all non-negative — so the two never appear side by side.
**Deferred**, not fixed, because fixing an invisible difference is churn.

---

## §6 · Colour

Rendered at `grayscale(1)`, the whole hierarchy survives.

- **Verdicts** carry text: `PROVEN`, `AMBIGUOUS`, `CONTRADICTED`. The word is
  the state; the colour is an accent on it.
- **Actors** carry shape and fill, measured: diamond, hollow circle, filled
  circle.
- **The spine collapse** is bar length.
- **Held money** is 20px against 10px stage names.

No colour is load-bearing anywhere. Nothing to add.

---

## §7 · Interactions

| interaction | result |
|---|---|
| click blocker → population → case | 2 clicks, blocker carried in |
| change lens | rail 0px, room replaced |
| open context | rail 0px, room 0px, origin marked |
| **Escape** | closes the context, **case unchanged** |
| **Back** ×5 | correct at every step |
| spine stage | lens change, case unchanged |
| **Ctrl+K** | palette opens |

Every one answers *the thing I was looking at changed*, not *the page changed*.

---

## §8 · Absence states

`UNPRICED`, `ENGINE ABSTAINED`, `LEDGER UNCHANGED`, `NO ENTRY IS WRITTEN`,
`NOT VERIFIED`, `NO UNIQUE PROOF`, `NO FEASIBLE SOLUTION` — each leads its room
at display size with its own reasoning beside it. None reads as an empty state.
Journal's `DEBIT ₹0.00 / CREDIT ₹0.00 / NET ₹0.00` under a double rule,
captioned *balanced by absence — nothing was written, rather than an entry that
happens to net to zero*, is the strongest of them.

---

## §9 · Language

Scanned all rendered text across 4 subjects × 7 lenses for: *ai-powered,
ai-driven, smart, intelligent, seamless, effortless, next-generation, platform,
solution, dashboard, insights, confidence, probably, likely, coming soon, beta,
experimental.*

**Zero hits.**

---

## §10 · The rubber-duck run

Each question is answered by the screen it lands on, and the transition to the
next is offered by the product rather than known by the operator:

```
What is ATTEST?              ₹53,02,701.96 processed · Financial control
Why can't this money move?   several disjoint sets of orders satisfy the amount
Why can't it be proved?      2,368 → 73 → 4 · no unique proof
What did the model try?      capture-batch → NON DISCRIMINATIVE → abstained
Why not auto-posted?         UNPRICED · nothing was proved, so nothing was priced
What happened to the books?  no entry is written · balanced by absence
What actually happened?      the run, its phases, and each event's because
What can I trust?            live Razorpay validation · NOT VERIFIED
```

No transition needs explaining.

---

## §11 · Demo mode

There is none. No demo-only route the product calls, no demo-only data, no fake
loading, no fake AI, no fake progress. The `reconciling…` state during cold
start is true — the engine is reconciling 250 settlements.

One note for completeness: `/api/events/demo` exists in the served API and
**nothing in the product calls it** — only browser contracts do. It is not fake:
it constructs four webhook bodies, signs three, and hands every one to the same
`Ingest.handle` the real endpoint uses, so the verdicts come from the code under
test. It is a test fixture living on the production surface, not a demo path.
**Keep** — three contracts depend on it and no viewer can reach it.

---

## §13 · README audit

The README does **not** open with AI marketing. It opens:

> **Settlement reconciliation as constrained optimization.**
> An LLM proposes hypotheses. A deterministic solver falsifies them. Nothing
> posts unless it is proven.

That is the thesis in three lines, and *"the engine does not emit a confidence
score"* follows immediately. **The banned opening is not present.**

What §13 asks for and the README does not do is **lead with the money**. The
first 20 seconds are currently a problem framing — subset-sum, NP-complete, an
illustrative ₹47,382.19 — rather than the live state of the running system. This
is the one genuine gap, and it is listed as a change below rather than made.

---

## §14 · Judge test — the six questions

Answerable at cold open in under 60 seconds; question 4 needs three clicks.

| | question | answered by |
|---|---|---|
| 1 | What does this product do? | `Financial control · all settlements · ₹53,02,701.96 processed` |
| 2 | Where did the money stop? | `VERIFICATION · ₹48,03,127.81 held · 198` |
| 3 | Why did it stop? | `several disjoint sets of orders satisfy the amount exactly` |
| 4 | What does the AI do? | `Model proposed → Solver tested → Engine abstained` |
| 5 | Why didn't it auto-post? | `UNPRICED · REVIEW` |
| 6 | What does it refuse to claim? | `REQUIRES EXTERNAL EVIDENCE`, then Trust's eleven boundaries |

**6 / 6.**

---

## §15 · The decision

### CHANGE — two

#### 1 · On a phone, the instrument dock is larger than the room it serves

**Problem.** The dock is laid out as `repeat(4, 1fr)` below 768px. That grid was
chosen when an instrument was a single label. Phase 13 made every instrument
state its question — correct, and it is what turned the dock into an index — but
each item became two lines, so seven items across four columns is two rows of
~130px.

**Evidence.** Measured at four phone widths:

```
 360x780   rail 195px   room 216px   dock 263px      dock 34% / room 28%
 390x844   rail 211px   room 264px   dock 263px      dock 31% / room 31%
 430x932   rail 233px   room 330px   dock 263px      dock 28% / room 35%
```

At 360 the dock is **larger than the room**, and the room is holding 2,323px of
content in a 216px window. Phase 23 §9's rule — *the dock must never compete
with the financial case* — is violated on the smallest screen, and only there.

**Change.** Restore the dock to a compact form below 768px: the question hidden
on the unheld instruments (which is what the desktop dock did before it had room
for both), or a horizontal strip. Desktop is untouched.

**Impact.** Roughly doubles the room on a phone. **Risk: low** — one media query,
no desktop change, no new element.

#### 2 · Control on an ambiguous case is the only room with no financial headline

**Problem.** Of 28 room-states measured, exactly one has no figure at display
size: Control on an ambiguous settlement. It is also the room a case *opens
into* — the first screen after clicking a case. Its conclusion reads
*"4 explanations satisfy it exactly"* with the supporting line *"4 subsets
satisfy every constraint"*, which is the same sentence twice in different words.

**Evidence.** From the walkthrough table: every other state shows two items at
34px (the rail's amount and the room's figure); `amb-control` shows the rail's
34px and then nothing above 20px. The contradicted case, by contrast, leads
correctly with `₹447.05 unresolved`.

**Change.** Give it the figure it already computes — the money that turns on
which explanation is right, `₹7,292.03`, matching the contradicted case's
`₹447.05 unresolved` — and replace the paraphrasing support line with what the
figure does not say.

**Consideration worth your call:** Evidence on the same case also leads with
₹7,292.03. Different rooms, so not the same-room duplication a contract already
forbids, but the two would share a headline number with different framings
(*turns on which is right* against *in dispute*). The alternative is the agreed
amount, ₹97,759.84 — *settled whichever is right* — which is arguably more
Control's answer and is not used as a headline anywhere else.

**Impact.** The first screen of every ambiguous case — 197 of 250 — gains a
financial headline. **Risk: low** — one conclusion object, data already present.

### DEFER — two

- **The minus sign.** JS emits `−`, Python emits `-`. No Python-produced amount
  is currently negative, so they never appear together. Fixing an invisible
  difference is churn; recorded so it is not rediscovered as a mystery.
- **`/api/events/demo`.** A route the product never calls, exercising the real
  ingest path for three contracts. Renaming or gating it is churn against
  passing tests for no user-visible gain.

### CHANGE — one, on the README, if you want it

**Problem.** §13 asks the first 20 seconds to lead with the running system's
money. The README leads with the problem class instead.

**Change.** Open with the thesis line, then the three live numbers, then
`MODEL → SOLVER → ENGINE → POLICY → LEDGER`, then the existing subset-sum
framing below the fold.

**Risk: low**, but it is a voice decision on the repository's front door, and
the current opening is genuinely good — it states the AI/proof separation in
three lines. **Listed, not assumed.**

### KEEP — everything else

Every item on §16's frozen list, plus what this review measured and found
correct: zero banned vocabulary, zero overflow across 48 screens, grayscale
survival, Escape and Back and the palette, all seven absence states, the five
canonical screens, and the visual signature.

### DELETE — nothing

---

## §17 · If ATTEST disappeared tomorrow

What a Razorpay engineer would remember is the sequence they cannot get from
another reconciliation demo:

> The model proposed something. The solver tested it and reported
> `NON DISCRIMINATIVE`. The engine abstained. The policy refused to price what
> had not been proved. The ledger did not move. And the system told me, on its
> own Trust screen, that its live Razorpay validation is **NOT VERIFIED**.

That is the memorable thing, and it is already what the product does.

**Awaiting approval before implementing changes 1 and 2.**
