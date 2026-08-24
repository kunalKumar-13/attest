# Phase 13 — Visual Audit

Measured before any code was changed. Every number here comes from the running
product at `localhost:8420`, extracted by walking painted text nodes and reading
computed styles — not from reading CSS.

Baseline: `run_0094`, dataset `synthetic_n250_s20260821`, Chromium, 1440×900
and 393×852.

---

## Baseline measurements (§19)

| | measured |
|---|---|
| domcontentloaded | 313 ms |
| largest contentful paint | **308 ms** |
| interactive (financial state painted) | 2 743 ms |
| painted text nodes, first viewport | 108 |
| elements competing for the eye (≥20px, or ≥15px bold) | 13 desktop · 7 mobile |
| type sizes in use | 9, 10, 11, 13, 15, 16, 20, 34 |
| declared type scale | 10, 11, 13, 15, 20, 34 |
| spacing values off the 4px scale | **151 of 324 (47%)** |
| radii in use | 4px, 8px, 999px |
| ₹ amounts rendered at ≤11px on the landing | **12 of 23** |
| median ₹ type size | **11px** |
| median non-₹ type size | 10px |

The last three lines are the finding the whole phase turns on.

---

## TEST A — blur everything except money, verdicts and stages (§19)

Landing, in visual order, with only ₹ amounts, verdict words and stage names
kept:

```
RAIL   34px  ₹53,02,701.96
       34px  ₹47,96,811.78
        9px  Source
       10px  ₹53,02,701.96
        9px  Matching
       10px  ₹53,02,701.96
        9px  Verification
       10px  ₹4,99,574.15
        9px  ₹48,03,127.81      ← the money that is stuck
        9px  Policy
       10px  ₹353.73
        9px  ₹4,99,220.42
        9px  Action
       10px  ₹353.73
ROOM   20px  ₹47,96,811.78
       20px  ₹4,99,574.15
       20px  ₹6,316.03          ← a ₹6,316 blocker
```

**The story survives the blur. The hierarchy does not.**

`₹48,03,127.81` — the money held at verification, the single most important
number in the product and the answer to "where did my money stop" — is painted
at **9px**, the same size as the word "Source" beside it, and one size below the
`₹353.73` that did post.

Meanwhile `₹6,316.03`, the smallest blocker in the list, is painted at **20px**.
A ₹6,316 problem is rendered **2.2× larger** than ₹48,03,127 of stuck money.

That is the inversion §6 names: *"₹ amounts must never visually look like
metadata."* Twelve of the twenty-three amounts on the landing are at 10px or
below, which is the tier the token system reserves for labels and system
annotations.

The same inversion hits the verdict. On a case rail, `AMBIGUOUS` renders at
**10px** — a word from the product's protected vocabulary (§7), set at
annotation size.

---

## TEST C — Evidence for three seconds (§19)

The Evidence room already carries the compression §11 asks for, and it is the
strongest composition in the product:

```
WHAT WAS CONSIDERED                                        2,368 → 73
  2,368  ████████████████████████  orders in the book
 −2,295         settlement calendar (rung 0)   CONVENTION
     −0         already claimed                CONVENTION
     −0         amount ceiling                 DETERMINISTIC
     73  ▍                          could belong to this credit
```

Then the four surviving explanations as agreed/in-question bars, A–D, with the
disputed amount per set. A reader gets *"the universe was narrowed by a
convention, and four explanations survive inside it"* without reading a
sentence.

Two gaps against §11. The compression chain **stops at 73** — the four surviving
explanations are a separate section below, so the sequence
`2,368 → 73 → 4` is never completed in one object. And the line the brief asks
for underneath — *the universe is an assumption; the proof is only as good as
the search space* — exists only behind a collapsed disclosure
(`> Why the boundary matters more than the selection`).

---

## What each section of the brief found

### §10 · The landing does not say where the money stopped

The brief asks the first viewport to state:

```
MONEY STOPPED AT
VERIFICATION
₹48,03,127.81 HELD
```

The product contains every part of that and states none of it. The stage bars
show the collapse proportionally — SOURCE and MATCHING run full width in green,
VERIFICATION is a stub, POLICY and ACTION are hairlines — which is genuinely
good proportional geometry. But the *sentence* is assembled by the reader from a
bar length plus two 9px fragments (`₹48,03,127.81` and `held · 198`).

No hero copy is needed. The fact is already computed. It needs to be **said at a
size a person reads**.

### §9 · The dock is a menu

```css
.c-lens-q { display: none }
.c-lenses button.on .c-lens-q { display: block }
```

Six of seven instruments show a bare label. Only the selected one reveals its
question — so the dock reads exactly as the brief's bad example:

```
CONTROL  ← question visible
JOURNAL
EVIDENCE
INVESTIGATE
POLICY
ACTIVITY
TRUST
```

And the order is wrong. `LENS_LABELS` in `api.py` puts **Journal second**, so the
dock does not read as the product loop. §1's sequence and §9's own listing both
run Control → Evidence → Investigate → Policy → **Journal** → Activity → Trust.
Journal belongs at position five: what entered the books comes after asking
whether posting was permitted.

The current questions are also softer than the operational ones §9 lists —
"What is happening?" against "Where did the money stop?".

### §5 · An undeclared type tier is carrying the product's most important facts

`9px` is not in the declared scale and is used **31 times** in the first
viewport. It is not decoration: it carries the stage names, the held amounts,
the capability labels and the blocker keys. The scale has six steps and the
product is using eight.

Spacing is 47% off the 4px scale. Much of that is legitimate — 1px, 2px and 3px
values are hairlines and optical nudges. The genuine drift is `5px`, `6px`,
`9px`, which appear 21–23 times each. (`20px` is `--sp-5` and legitimate; the
code scale runs 4/8/12/16/20/24/32/40 rather than the brief's 4…48.)

### §17 · The blockers are cards

The three highest-leverage work items are drawn as large rounded grey bordered
boxes stacked vertically. That is precisely `card-grid-everything`, and it makes
the most operationally important list in the product look like a marketing page.
A register of ranked work should read as rows in a ledger, not as three cards.

### §16 · Copy repeats itself verbatim

Policy, on one screen, says this twice with identical wording:

> Nothing was priced. The proof did not establish a unique explanation, so there
> is no error probability to multiply.

— once as the conclusion, once under **THE BOUNDARY**. On the proven case the
same duplication occurs with *"₹135.49 expected loss against ₹150.00 to check —
automating is cheaper"*, which appears as the conclusion, again below the
boundary bar, and a third time as the bar's own labels. The verdict word
(`REVIEW`, `AUTO-POST`) is painted twice at large size within 250px of itself.

### §14 · Mobile puts metadata above the conclusion

At 393px the first viewport reads:

```
₹53,02,701.96 · processed · Financial control · all settlements
settlements 250 · orders 2,368 · seed 20260821
Source … Matching … Verification …
```

`seed 20260821` is run provenance — Trust's subject — and it occupies premium
space above the conclusion, which does not appear until y=236. §14's priority is
conclusion, money, verdict, spine, next action. Metadata is not on the list.

### §13 · Policy's decision boundary is already right

The marker, the threshold line and the two labelled halves all exist:

```
automating is cheaper          ●        │        checking is cheaper
₹135.49 expected loss    ₹150.00 to check
```

And on an ambiguous case the bar is **absent** rather than drawn empty, with
`UNPRICED` in its place. That is the behaviour §13 asks for, already built. No
change needed beyond removing the duplicated sentence.

### §12 · Investigate's actor sequence is already right

`◇ MODEL proposed → ○ SOLVER tested → ● ENGINE abstained`, ending in
`NON DISCRIMINATIVE` and `Verdict unchanged`, with the model visually
subordinate. No change needed.

### §15 · Performance

LCP is **308 ms** — the structural shell already paints immediately. The 2.7 s
to interactive is the engine processing 250 settlements, and the shell renders
its frame first rather than blocking on it. Nothing to do, and nothing to fake.

---

## The changes, ranked by leverage

Ordered by how much of the product each one fixes per unit of risk.

| # | Change | Why it is the highest leverage available | Brief |
|---|---|---|---|
| **1** | **Money and verdicts move up the type scale in the State Spine** | One change to one component fixes the landing, all seven rooms, both viewports and TEST A at once — the spine is rendered by the shell on every lens, so the money hierarchy is fixed everywhere or nowhere. Nothing is added; existing facts are given the weight they already earned. | §3 §6 |
| **2** | **The landing states where the money stopped** | The most important sentence in the product is currently assembled by the reader from a bar and two 9px fragments. Saying it is the difference between a chart and an instrument. | §10 §2 |
| **3** | **Dock: every question visible, product-loop order** | Turns seven navigation items into seven instruments, and makes the dock itself teach the loop in §1. Two-line change plus a reorder. | §9 §1 |
| **4** | **Retire the 9px tier** | An undeclared tier carrying money is how the inversion happened in the first place. Closing it prevents the regression rather than repairing it. | §5 |
| **5** | **Blockers become a register, not cards** | The most operational list in the product currently looks the most like a SaaS dashboard. | §17 |
| **6** | **Delete verbatim copy repeats** | Three sentences are painted twice each within one viewport. Removing them raises the signal of what remains without adding anything. | §16 |
| **7** | **Complete the compression chain to 4** | `2,368 → 73 → 4` in one object makes the signature moment self-contained, and surfaces the assumption line from behind a disclosure. | §11 |
| **8** | **Mobile: conclusion above metadata** | Restores §14's stated priority; `seed` leaves the first viewport. | §14 |

Deliberately **not** doing: the Policy boundary visual (§13) and the Investigate
actor sequence (§12) are already what the brief describes. A global spacing sweep
is high churn against 47% of declared values for no measurable hierarchy gain —
the systematic offenders inside the components being touched will be corrected,
and the rest is reported here rather than chased.

Nothing in §18's preserve list is affected: every change is type scale, copy,
ordering or CSS structure. No engine call, no API shape, no lens, no new screen.

---

# Implemented

Phase A of §20 (landing / Control), plus the dock and the copy pass. Every
change is CSS, copy, ordering or a component's markup. No engine call, no API
shape, no lens, no new screen — and the six safety gates moved **+0.0000** on
every metric, which is the evidence for that claim rather than the assertion of
it.

## The defect underneath most of the others

The single highest-leverage finding was not in the audit's ranked list, because
it did not look like a design decision. It was measured while trying to work out
why the blockers rendered as cards:

```css
button { font: inherit; color: inherit }
```

Type and colour were reset. **Background and border were not.** Every control
that did not paint its own surface inherited Chromium's `buttonface` grey and a
2px outset border — measured at **111 of ~190 visible controls**, including all
seven instrument dock items and all three blocker rows.

The dock's own stylesheet had described the intended design for months:

> *the held instrument states its QUESTION and the others do not; selection is a
> seated indent against the rail edge rather than a filled chip. A menu names
> places. An instrument says what it asks.*

That design had never once rendered. Seven raw OS buttons in a column is a menu
no matter what the comment says. One reset line fixed §17's cards, §9's menu and
Trust's failure list simultaneously.

## Money now has roles (§3, §6)

| role | where | was | now |
|---|---|---|---|
| money that entered | rail amount | 34px | 34px |
| **money that stopped** | spine, held | **9px** | **20px**, in the stop colour |
| money that continues | spine, per stage | 10px | 13px mono |
| money in dispute | rail, agreed/disputed | 15px | 15px |
| one item of work | blocker row | 20px | 20px |

`₹48,03,127.81` held at verification was painted at 9px, one size below the
`₹353.73` that posted and 2.2× smaller than a ₹6,316 blocker. It now reads as
the second-loudest thing in the rail, which is what it is.

§10 asks the landing to say `MONEY STOPPED AT / VERIFICATION / ₹48,03,127.81
HELD`. It is **not** a new block — the spine row already said exactly that, at
annotation size. Adding a second block stating it would have been the
duplication this same phase removed from Policy.

## The spine got shorter while carrying more (§3)

Promoting the money made the rail overflow and pushed the next action off the
bottom — a regression measured at 44px on the landing where the baseline was 4px.
Three structural corrections, each of which removes something that was never
carrying information:

- **The stage value is stated where the money changes.** Four of five stages
  repeated the figure above them — source and matching both read
  ₹53,02,701.96, policy and action both read ₹353.73. The bar carries magnitude
  at every stage; the figure now marks each collapse.
- **A stage that held nothing no longer reserves a line to say so.**
- **The continuing amount sits on the stage's own line**, not beneath it.
- **Agreed and disputed are paired** rather than stacked — they are one fact in
  two halves.

| rail | baseline | after |
|---|---|---|
| landing overflow at 1440×900 | 4px | **0px** |
| case overflow at 1440×900 | 148px | **89px** |
| case at 1440×1080 | — | **0px, next action visible** |

## The dock became an instrument index (§9, §1)

`display:none` on the question is gone: every instrument states what it asks, and
the held one is distinguished by seating and weight rather than by being the only
one that says anything. The questions are the operator's — *"Where did the money
stop?"* rather than *"What is happening?"*.

The order was wrong and the reason was structural: `lenses_for()` iterated
`LENS_MATRIX`, a table about which subjects a lens can answer for, which carried
the dock's reading order by accident. Two tables, one ordered by meaning and the
other consulted for it. Order now comes from `LENS_LABELS`, and Journal moved
from second to fifth — *what entered the books* comes after *may we post at all*:

```
CONTROL       Where did the money stop?
EVIDENCE      Can the explanation be proved?
INVESTIGATE   What would separate them?
POLICY        What is safe to automate?
JOURNAL       What entered the books?
ACTIVITY      What actually happened?
TRUST         What can I believe?
```

The dock now teaches §1's loop by being read top to bottom.

## The 9px tier is closed (§5)

14 CSS rules, 50 painted elements, none of them decoration — it carried the
stage names, the held amounts and the capability labels. That undeclared tier is
how the money inversion happened in the first place. All 14 folded into
`--type-micro`; a contract now fails on any size outside {10, 11, 13, 15, 20, 34}.

Retiring it was checked for clipping at five widths against the pre-change
baseline: **177 real clips before, 177 after** — identical, and dominated by the
visually-hidden screen-reader live region, where oversized content is correct.

## Four sentences were being painted twice (§16)

A contract compares each room's conclusion against the rest of that room:

- **Policy** stated its boundary sentence as the conclusion, then again word for
  word under THE BOUNDARY — and on an unpriced case that section contained
  nothing else, so it was a heading over a repeat. §13 asks for no marker when
  nothing was priced; the honest form of that is no boundary section at all.
- **Journal** repeated the refusal reason as an `entry / reason` field two blocks
  below the conclusion that leads with it.
- **Activity** repeated its unrevised note, and its "Decided before evidence that
  names them" section was a heading, a `0 settlements` count and that repeat.

Removing the repeats left three headings over nothing, so a second contract now
fails on any titled block with an empty body.

## Two metrics that misled, recorded rather than dropped

**`scrollWidth > clientWidth` reported 247 clipped elements.** It counts any
element whose content spills, including `overflow:visible` containers where
nothing is actually cut off. Real clipping needs `overflow:hidden|clip` or an
ellipsis — and by that measure the count was 177 before and after, unchanged.

**The duplicate-sentence contract first reported five defects, two of which were
false.** One came from comparing against a *detached clone* of the room:
`innerText` on a detached node degrades to `textContent`, which includes
collapsed disclosure bodies no reader can see. The other came from counting a
justification repeated down the rows of a list — 250 settlements share one
reduction reason and each row is entitled to state it. Both were rewritten to
count occurrences in the live room and to compare only against the conclusion.

## Not done, and why

- **Policy's decision boundary (§13)** and **Investigate's actor sequence
  (§12)** already are what the brief describes — marker, threshold line, both
  labelled halves, no marker at all when unpriced; `◇ MODEL → ○ SOLVER → ●
  ENGINE` ending in `NON DISCRIMINATIVE` and `Verdict unchanged`. Nothing to add.
- **Performance (§15).** LCP is 308ms — the shell already paints before the
  engine finishes. Nothing to do and nothing to fake.
- **A global spacing sweep.** 47% of spacing values are off the declared scale,
  but most are 1–3px hairlines and optical nudges. The systematic offenders
  inside the components touched here were corrected; a full sweep is high churn
  for no measurable hierarchy gain.
- **The case rail still scrolls at 1440×900** (89px, down from 148px). It fits
  entirely at 1080px and above. Recorded rather than chased.

## The signature moment now completes (§11)

The Evidence compression was already the strongest composition in the product,
and it stopped one step short. The number of explanations that survived the
reductions lived in a separate section below, so the sequence a judge is meant
to read in three seconds was never finished where it was being told.

```
WHAT WAS CONSIDERED                                 2,368 → 73 → 4

  2,368  ████████████████████████  orders in the book
 −2,295  settlement calendar (rung 0)   CONVENTION
     −0  already claimed                CONVENTION
     −0  amount ceiling                 DETERMINISTIC
     73  ▍                          could belong to this credit
  ─────────────────────────────────────────────────────────────
      4                              surviving explanations, and
                                     arithmetic cannot choose

unique within the validated candidate space; the space itself rests on
settlement calendar (rung 0), already claimed, which is a convention
rather than a proof
```

The final row's track is deliberately empty. Four explanations are not a
proportion of two thousand orders, and drawing a sliver there would invite
exactly that reading.

The claim underneath is this case's own — not a slogan. It used to sit behind
the *Why the boundary matters more than the selection* disclosure. A proof is
only as good as the space it was proved in is the argument this composition
exists to make, so it is stated under the chain rather than folded away beneath
it. A contract checks the chain's final figure equals the number of explanations
actually drawn.

---

## Measured, before and after

| | before | after |
|---|---|---|
| median painted ₹ type size | 11px | **15px** |
| median non-₹ type size | 10px | 10px |
| ₹ amounts at annotation size (≤11px), landing | **12 of 23** | **4 of 19** |
| money held at verification | 9px | **20px** |
| controls with browser-default chrome | **111** | **0** |
| type sizes outside the declared scale | 9px ×50 | **none** |
| sections that are a heading over nothing | 3 | **0** |
| conclusions repeated verbatim in their own room | 4 | **0** |
| elements competing for the eye, landing | 13 | **9** — all money or conclusions |
| instruments stating their question | 1 of 7 | **7 of 7** |
| largest contentful paint | 308ms | **252ms** |
| landing rail overflow at 1440×900 | 4px | **0px** |
| horizontal overflow at six widths | none | **none** |

### TEST A, after

```
34px  ₹53,02,701.96      money that entered
34px  ₹47,96,811.78      the work that unlocks the most
20px  ₹48,03,127.81      money that stopped, at verification
20px  ₹4,99,220.42       money that stopped, at policy
20px  ₹6,316.03          one item of work
13px  ₹4,99,574.15       money that continues
10px  Verification       the stage
```

Blur everything but the amounts, the verdicts and the stages, and the hierarchy
now matches the story: what came in, what to do about it, what stopped, what
continues. Before, the first two lines were identical and everything explaining
where the money stopped sat at the bottom of the visual order.

---

## §21 — the finish line, walked

A Razorpay engineer opening ATTEST, measured end to end:

```
0 clicks   ₹53,02,701.96 processed · 250 settlements · 2,368 orders
           SOURCE       ████████████  ₹53,02,701.96
           MATCHING     ████████████
           VERIFICATION ▮             ₹4,99,574.15
           ₹48,03,127.81 held · 198
           POLICY       |             ₹353.73
           ₹4,99,220.42 held · 51
           ACTION       |

           1  ₹47,96,811.78  Systemic · 197 settlements
              blocked at verification
              REQUIRES EXTERNAL EVIDENCE

2 clicks   a settlement affected by that blocker, with the blocker
           carried into it

+1 each    EVIDENCE      No unique proof · ₹15,750.00 in dispute
           INVESTIGATE   Engine abstained · Verdict unchanged
           POLICY        Unpriced · REVIEW
           JOURNAL       No entry is written · not posted
           TRUST         (portfolio) Live Razorpay validation · NOT VERIFIED
```

**7 clicks, 8.2 seconds**, no ID typed, no search, no tour.

## What was not changed

Every item on §18's preserve list is untouched: the reconciliation engine, the
proof kernel, the search-space model, the solver hierarchy, the AI hypothesis
separation, the policy engine, integer paise arithmetic, journal semantics,
activity causality, Trust's limitations, the Razorpay boundaries, the
subject/lens/context model, blocker continuity, stale-fetch protection,
context-origin motion, keyboard access, the responsive guarantees, and every
pre-existing contract.

One contract was re-pointed rather than deleted.
`test_an_unproven_settlement_is_never_priced` read `.p-bound`, a box whose whole
content was the sentence the conclusion already leads with. Its guarantee did not
move — *"nothing was priced"* is still asserted, and the absence of a marker is
now **absolute** (`.p-bound` count is zero) rather than a marker-less box. That
is strictly stronger than what it replaced, which is the only acceptable form of
re-pointing a contract.

**275 tests · 112 browser contracts · six gates at +0.0000 · zero overflow at
360/393/430/768/1024/1512 · no type size outside the declared scale.**
