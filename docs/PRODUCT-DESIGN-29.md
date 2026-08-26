# ATTEST — product design system

Written before any code, as §18 requires. What follows is the system, not a
wish list: every token, grammar and interaction below is stated precisely
enough to implement or to reject.

---

## What the reference actually teaches

Studied `modiqo.ai` and `modiqo.ai/blog/the-playoffs` directly. Stripped of
brand, five principles are portable — and each has to earn its place against a
financial instrument, not a marketing page.

| principle | what ATTEST takes | what it does not |
|---|---|---|
| **numbered sequence as scaffolding** (01–08 as visual anchors, not decoration) | number the seven instruments and the sections inside a room, so position carries meaning | not numbering for ornament; a number that does not encode order is noise |
| **statement against micro-label** — a massive claim paired with a tiny uppercase tag | this is already ATTEST's conclusion pattern; formalise it as *the* recurring device | not making everything large |
| **proof-through-demonstration** — a claim followed immediately by evidence you can check | our strongest existing habit: `4.8% false-proof` sits beside `exact_only 0%` | not claims followed by testimonials |
| **monospace reserved for the technical** | money, ids, hashes, counts — never prose | not monospace as texture |
| **asymmetry and progressive disclosure** | let a ₹48L figure break the column; reward inspection with inline expansion | not hidden primary information |

**What we reject from the reference.** Inverse sequencing — leading with the
call-to-action before explaining the thing. A financial instrument must say what
it is and how much money it holds before it says anything else. Marketing pages
can afford intrigue; a reconciliation system cannot.

---

## 1 · Visual thesis

> **Money enters. Evidence constrains. Proof decides. When the evidence runs
> out, the instrument stops — and says where.**

Every visual decision serves one of three jobs:

1. **Make the collapse legible** — money shrinking as it passes through stages
   is the product, and it should be readable before any word is.
2. **Make authority legible** — `◇ proposes · ○ tests · ● decides` must be
   visible as a *shape language*, so the AI boundary survives grayscale, blur
   and a 3-second glance.
3. **Make refusal legible** — `UNPRICED`, `NOT VERIFIED`, `LEDGER UNCHANGED`
   must read as decisions, never as empty states.

Anything that serves none of these is decoration and does not ship.

---

## 2 · Typography

Six sizes, semantically named. Two faces: a grotesque for prose, a monospace for
every figure and identifier.

```
--type-display   34px   the primary financial fact — once per screen
--type-statement 20px   a conclusion, an identity, an instrument's answer
--type-data      15px   figures inside a composition; agreed/disputed
--type-body      13px   statements, row content, explanation
--type-label     11px   small-caps section labels
--type-micro     10px   provenance, timestamps, counts, annotations
```

**The pairing rule.** A display or statement figure is always preceded or
followed by a `--type-micro` uppercase label at `.13em` tracking. Never a figure
alone; never a label alone. That pair is ATTEST's sentence.

```
₹48,03,127.81        display, mono, tabular
HELD AT VERIFICATION micro, caps, tracked
```

**Money roles, fixed.** Nine categories, one size each — already implemented and
measured. Entered 34, held 20, value-blocked 20, agreed/disputed 15, continues
13. **This does not change.** It survives blur today and re-deriving it would be
churn.

**Never** monospace for prose. **Never** a seventh size.

---

## 3 · Spacing

Eight steps on a 4px base — `4 8 12 16 20 24 32 40`. Already in place at 47%
adherence, with the drift concentrated in 1–3px optical nudges that are
legitimate.

**New rule — the breathing set.** Three objects get double the surrounding
space: the display figure, the actor sequence, and any refusal statement. Space
is how a financial instrument signals importance without shouting.

---

## 4 · Colour

Contrast through weight, not saturation. The palette is near-white ground,
near-black ink, muted graphite secondary, hairline rules, and exactly four
semantic accents already in use: proven, ambiguous, contradicted, accent.

**The constraint that matters:** no state may be carried by colour alone. Today
verdicts are words, actors are shapes, the collapse is bar length, held money is
size. Verified at `grayscale(1)` and at `blur(2.2px)`. **A redesign that breaks
this is a regression regardless of how it looks.**

Forbidden: gradients, glassmorphism, AI-purple, glow, shadow as decoration,
rounded cards, coloured status pills.

---

## 5 · Instrument grammar

Seven instruments, numbered, each with a name, a question, and a live state:

```
01  CONTROL       Where did the money stop?          VERIFICATION
02  EVIDENCE      Can the explanation be proved?     NO UNIQUE PROOF
03  INVESTIGATE   What would separate them?          ENGINE ABSTAINED
04  POLICY        What is safe to automate?          UNPRICED
05  JOURNAL       What entered the books?            NOT WRITTEN
06  ACTIVITY      What actually happened?            10 EVENTS
07  TRUST         What can I believe?                NOT VERIFIED
```

The **number encodes the product loop** — it is the order the operator moves
through, and reading the dock top to bottom teaches the system. The **third
line is new**: each instrument reports its own current state, so the dock
becomes a summary of the case rather than a menu.

Selection: a rule on the leading edge and a surface. Never a pill, never a
filled chip, never a tab.

---

## 6 · The signature objects

**The collapse.** Not a chart. A sequence of figures that physically shrink,
each with its stage label and a proportional rule. The reader should see the
money disappear before reading a stage name.

**The reduction.** `2,368 → 164 → 4` as a descending sequence where each cut
names itself and its authority — CONVENTION or DETERMINISTIC. Hovering a
reduction expands what it removed *inline*, never as a tooltip.

**The actor sequence.** `◇ MODEL → ○ SOLVER → ● ENGINE`, appearing in order, and
ending in a statement of what did not change. Shape plus fill, so it survives
grayscale. **This is the motif that should recur across the product.**

**The threshold.** Expected loss against review cost as a marker on a rule. When
unpriced, **the rule is absent** — not empty, not zero. Absence is the statement.

---

## 7 · Interaction

Three motion tiers, already defined: micro `.13s`, standard `.2s`, spatial
`.3s`. Every animation must answer *what stayed, what moved, what opened*.

| interaction | what it must communicate |
|---|---|
| open a blocker | the affected population belongs to *that* row |
| open a case | the blocker travels with it — the reason you came stays on screen |
| change instrument | the case does not move; only the room does |
| open context | it grew out of the row you clicked; the case moved 0px |
| click a spine stage | the instrument that owns that stage |

**Forbidden:** numbers that animate on load, decorative motion, confetti,
anything that moves without a state change behind it.

---

## 8 · Composition

**Desktop 1440.** Rail 296px, room the remainder. Within a room: statement →
instrument → annotation → evidence. Asymmetry earns its place where a display
figure may occupy 40% of the width with its explanation set well away from it —
but the rail and dock stay regular, because a financial instrument's frame
should not move.

**Mobile 360.** Rail becomes a financial strip capped at 25vh; dock becomes
seven single lines at 138px total; room takes the rest. Money, stopped stage,
verdict and next action must survive the first viewport. Zero horizontal
overflow at 360/390/430/768/1024/1440/1512 — currently true and non-negotiable.

---

## 9 · Accessibility and performance

Keyboard reach for all seven instruments, `role=tab`, visible focus rings, an
`aria-live` region for state changes, Escape closing context, Back correct at
every step. LCP ~250ms to a painted shell; the engine's real reconciliation
time is labelled `reconciling…` and never faked.

**Any redesign that costs a contract here is rejected.**

---

## 10 · What this phase will and will not do

**The honest scope statement.** §17 asks for twelve prototyped screens. The
system above is complete and implementable, but the product already scores 10/10
on the stranger test, zero overflow at seven widths, and survives blur and
grayscale — the information architecture is not the weakness.

The weaknesses this design system actually addresses are **three**:

| # | gap | change |
|---|---|---|
| **1** | the dock is a list of names and questions; it does not report state | add the third line — each instrument's current answer |
| **2** | the collapse is a bar list in the rail, not a designed object | make it the landing's central instrument, figures shrinking |
| **3** | sections inside a room have no ordinal rhythm | number them, so a room reads as a sequence rather than a stack |

Everything else in §§1–17 either **already exists** — the actor motif, the
reduction chain, the threshold instrument with its absent rule, Trust as a lab
report, the Razorpay boundary, the money hierarchy — or is **decoration this
system rejects**.

Building the three above is a presentation-layer change touching no financial
semantics. Building a twelve-screen speculative rebuild ten days before a
deadline, on a product that measures 10/10 with judges' questions, would be the
kind of change §XIII of the previous phase warned about: made because it is
cool, not because it raises the probability of winning.

**Recommendation: implement 1–3, measure against the current baseline, and keep
everything that already passes.**
