# Three product directions — ATTEST 10

Phase 10.1. Three mental models, not three stylesheets. Each answers the
autopsy's finding — *the shell occupies 38% of the viewport and half of what is
visible* — in a structurally different way.

All three use identical data. None invents backend capability. Each would be
prototyped across four lenses: **Control, Evidence, Investigate, Policy.**

---

# A — FINANCIAL TERMINAL

### Mental model

> **The case is a column. The instrument is the room.**

The case stops being a band across the top and becomes a persistent **left
rail** — identity, amount, verdict, stage, and the spine, stacked vertically and
never redrawn. The instrument gets the entire remaining rectangle, full height.

Chrome goes from **343px vertical** to **0px vertical** and ~300px horizontal.
On a 1440×900 screen the instrument gains 343px of height and loses 300px of
width — and height is what every lens was starving for.

### The primary screen

```
┌────────────────┬──────────────────────────────────────────────────────┐
│ setl_000089    │  WHAT THE EXPLANATIONS AGREE ON                      │
│ AMBIGUOUS      │                                                      │
│                │      A  ████████████████████▓▓▓▓   27 + 4   ₹2,312   │
│ ₹1,00,036.83   │      B  ████████████████████▓▓▓▓   27 + 4   ₹2,331   │
│ bank credit    │      C  ████████████████████▓▓▓▓   27 + 4   ₹2,323   │
│                │      D  ████████████████████▓▓▓▓▓  27 + 5   ₹2,276   │
│ ── SPINE ──    │                                                      │
│ SOURCE   ████  │  ₹97,759.84  settled whichever explanation is right  │
│ MATCHING ████  │  ₹7,292.03   turns on which one is, across 12 orders │
│ VERIFY   ▌     │                                                      │
│ POLICY   ▏     │  ─────────────────────────────────────────────────   │
│ ACTION   ▏     │  WHAT WAS CONSIDERED       2,368 → 73                │
│                │                                                      │
│ ── NOW ──      │  2,368  ████████████████████████  in the book        │
│ 4 explanations │ −2,295  ██                        calendar CONVENTION│
│ AGREED         │     73  ▌                         reach the solver   │
│ ₹97,759.84     │                                                      │
│ DISPUTED       │                                                      │
│ ₹7,292.03      │                                                      │
│                │                                                      │
│ ── NEXT ──     │                                                      │
│ Supply order-  │                                                      │
│ level ref      │                                                      │
│ ₹47,96,811     │                                                      │
├────────────────┤                                                      │
│ ⌘K             │                                                      │
└────────────────┴──────────────────────────────────────────────────────┘
```

The rail carries the seven answers a case must give — what, how much, where it
stopped, what is proven, what is uncertain, what would resolve it, what is safe
to do — and it never re-renders. **The lens strip disappears as a horizontal
band**; lenses become a compact instrument selector at the rail's foot, or ⌘K.

### How the four lenses differ

| lens | instrument filling the room |
|---|---|
| Control | the flow at full width — the spine enlarged into the working surface, each stage expanding into the cases held there |
| Evidence | the compression band above the explanation comparison, full-width bars |
| Investigate | a four-beat experiment: QUESTION / HYPOTHESIS ◇ / TEST ○ / RESULT ● laid horizontally |
| Policy | a single boundary line across the full width, with the two costs at its ends |

### Case persistence

Structural. The rail is never re-rendered on a lens change — only the room
swaps. Continuity stops being a promise seven files keep and becomes a property
of the layout.

### The spine

Moves into the rail as a vertical flow, and becomes **selectable**: clicking
VERIFICATION makes the 198 settlements held there the working set. The spine
becomes the primary filter — the financial map, not a legend.

### Command palette

The rail's foot. Operator console: ids, lenses, verdicts, `>75000 unexplained`.

### Spatial interaction

The rail/room split is resizable and remembered. Context opens as a third
column, sliding the room rather than covering it. Nothing else moves.

### Risk

The rail is a fixed 300px tax on every screen. If it drifts toward a summary
sidebar it becomes the same problem rotated 90°.

---

# B — INVESTIGATION WORKSTATION

### Mental model

> **The case is a line. The screen is a bench.**

The case compresses to a **single 40px line** — id, verdict, amount, stage —
and everything else is workbench. Two panes: what you are examining, and what
you are testing against it. The lens is not a page you visit; it is which
instrument is loaded on the bench.

Chrome drops from 343px to ~86px. The instrument gains 257px of height and loses
nothing horizontally.

### The primary screen

```
 setl_000089  AMBIGUOUS   ₹1,00,036.83   stops at VERIFICATION   4 explanations
────────────────────────────────────────────────────────────────────────────────
 SPINE ▏████ SOURCE ████ MATCHING ▌VERIFY ▏POLICY ▏ACTION        ₹7,292.03 in play
────────────────────────────────────────────────────────────────────────────────
                                       │
  THE QUESTION                         │   ◇ MODEL          proposed
  Why are these four                   │     capture-batch, 3 orders
  explanations indistinguishable?      │     2026-05-06
                                       │
  2,368 ──────────────────── in book   │   ○ SOLVER         tested
 −2,295 ██ calendar · CONVENTION       │     uniqueness
     73 ▌ reach the solver             │     ── NON-DISCRIMINATIVE
                                       │     4 of 4 explanations contain it
  A  ███████████▓▓▓  27+4  ₹2,312.65   │
  B  ███████████▓▓▓  27+4  ₹2,331.03   │   ● ENGINE         decided
  C  ███████████▓▓▓  27+4  ₹2,323.98   │     ABSTAINED
  D  ███████████▓▓▓▓ 27+5  ₹2,276.80   │     verdict unchanged
                                       │
  ₹97,759.84 agreed  ₹7,292.03 disputed│   ── TEST ANOTHER SIGNAL ──
                                       │   capture date ·  UTR suffix
                                       │   refund relation ·  fee pattern
                                       │   (only those the engine can run)
```

The left pane is the **specimen**; the right is the **experiment**. Lens
switching changes what is loaded on each side, and the specimen frequently
stays put — moving Evidence → Investigate keeps the explanations on the left
and swaps the right.

### How the four lenses differ

| lens | left pane (specimen) | right pane (instrument) |
|---|---|---|
| Control | the flow, stage by stage | what unlocks the most, ranked by value ÷ effort |
| Evidence | the compression band and explanations | the relationships in force, and what is missing |
| Investigate | the explanations still standing | the ◇ → ○ → ● experiment log |
| Policy | the proof gates, each satisfied or not | the boundary and its two costs |

### Case persistence

The 40px line is the whole case object and never re-renders. Because the left
pane often persists across a lens change, continuity is felt in the *content*,
not only in the header.

### The spine

Becomes a **horizontal 24px meter** directly under the case line — dense, always
present, still proportional. It loses the detail sentences (which move into
Control, where they are the instrument) and keeps the collapse.

### Command palette

⌘K loads a specimen onto the bench. It is how you change case, not how you
navigate.

### Spatial interaction

The bench divider is draggable — the one drag that earns itself, because
Evidence wants a wide left and Investigate wants a wide right. Context opens
*inside* the pane that owns it, not over the workspace.

### Risk

Two panes at 1440px is ~700px each, which is tight for the explanation
comparison. Below 1024px it must collapse to one pane and the metaphor weakens.

---

# C — OPERATIONS CONTROL ROOM

### Mental model

> **The primary object is the work, not the case.**

The other two ask "what about this settlement?". This one asks **"what should I
do first, and why?"** — and the case is what you open to answer that.

The screen is a **work queue** ranked by value ÷ operator effort, with the spine
as its filter. A case opens as an inspectable object *within* the queue, not as
a destination. The seven lenses become facets of the opened case.

This is the only direction where a portfolio of 250 settlements is the subject
rather than a list you leave.

### The primary screen

```
 ATTEST      ₹53,02,701.96 processed        250 settlements · 2,368 orders
────────────────────────────────────────────────────────────────────────────────
 SOURCE ████████ MATCHING ████████ VERIFY ██▌ POLICY ▏ ACTION ▏
 ₹53.03L         ₹53.03L           ₹4.99L    ₹353    ₹353
                                   ▲ 198 held here — click to work this stage
────────────────────────────────────────────────────────────────────────────────
 WHAT TO DO FIRST                                        value ÷ effort

 ┌ SYSTEMIC ────────────────────────────────────────────────────────────────┐
 │ Supply an order-level reference on the settlement report                  │
 │ ₹47,96,811.78          197 cases        1 step          ₹47.96L per step  │
 │ ─────────────────────────────────────────────────────────────────────────│
 │ setl_000089  ₹1,00,036.83  4 explanations  27 agreed  12 disputed   ▸     │
 │ setl_000247  ₹95,988.73    …                                        ▸     │
 └───────────────────────────────────────────────────────────────────────────┘

 ┌ FREE RE-RUN ─────────────────────────────────────────────────────────────┐
 │ Widen the settlement window and re-run                                    │
 │ ₹4,99,574.15            52 cases        1 step          ₹9,607 per step   │
 └───────────────────────────────────────────────────────────────────────────┘

 ┌ PER ITEM ────────────────────────────────────────────────────────────────┐
 │ Look for a fee correction around the value date                           │
 │ ₹6,316.03                1 case         1 step          ₹6,316 per step   │
 └───────────────────────────────────────────────────────────────────────────┘
```

Opening `setl_000089` expands it **in place** — the case unfolds within its
group, with its own seven-instrument selector, and the queue stays visible above
and below. You never lose your place in the work.

### How the four lenses differ

| lens | inside an opened case |
|---|---|
| Control | the case's own flow, and where it sits in the group |
| Evidence | compression and explanations, inline |
| Investigate | the experiment log, inline |
| Policy | the boundary, and what the same policy did to the other 196 cases in this group |

Policy is the standout here: it is the only direction where the boundary is
shown **across the group**, which is how a policy is actually evaluated.

### Case persistence

The case never becomes the whole screen, so it cannot be lost. Continuity is
guaranteed by the case being a *disclosure inside a list* rather than a route.

### The spine

Becomes the **queue's filter and the product's headline** — full width, at the
top, with each stage clickable to scope the work below it. This is the direction
that takes Design Principle #1 most literally: the spine *is* the financial map,
and it drives the working set.

### Command palette

An operator console that acts on the queue: `ambiguous`, `>75000 unexplained`,
`policy review` — filters as much as it navigates.

### Spatial interaction

Groups collapse and pin. An opened case can be **pinned** so it stays expanded
while you scroll the queue — the one direction where pinning has a real job.

### Risk

Two genuine dangers. It could drift toward a task-management UI, which was
explicitly rejected. And a single settlement examined deeply — the five-second
test case — is one level down rather than the front door, so `setl_000089` is
harder to reach cold.

---

## What I would delete, in all three

| delete | why | measured cost today |
|---|---|---|
| the horizontal lens strip as a band | it is 46px of identical pixels on every view; the instrument selector belongs to the case object | 46px × 7 |
| the repeated header band | the case should be an object, not a redraw | 90px × 7 |
| the spine's detail sentences on non-Control lenses | they are the instrument on Control and chrome everywhere else | ~80px × 6 |
| Trust as a seven-screen document | 6.8 screens, 32 actions below the fold; it must become a provenance surface | 3,090px scroll |
| the top bar's Run/theme controls in the primary position | the first touchable thing on every screen is app chrome | top=8 |

## What I would preserve, in all three

The engine and everything under it — untouched. And in the UI: the spine's
proportional collapse; the amount at 34px as the financial subject; the
context-origin motion and focus return; subject × lens × context with URL
addressability; the stale-fetch guard; ◇ MODEL → ○ SOLVER → ● ENGINE;
`UNPRICED` rather than a fabricated zero; Trust leading with failures; every
WCAG and reduced-motion guarantee; all 94 contracts.

---

## How the three will be measured

Not by DOM similarity — that metric was right for 9.2, where the primitives
differed, and it saturated in 9.3 when it could not tell a causal chain from a
test ledger. **Phase 10.2 measures task performance.**

Each prototype, same data, same tasks, timed by instrumented interaction:

| measure | how |
|---|---|
| 5-second comprehension | above-fold content only; can *what is this* be answered |
| 10-second comprehension | can *where is the money* be answered |
| time to locate ambiguous money | first paint → the ₹7,292.03 figure visible |
| time to understand *why* | first paint → compression band and explanation count visible |
| time to find the next action | first paint → `₹47,96,811` and its label visible |
| clicks to inspect evidence | from cold open |
| clicks to reach policy | from cold open |
| case continuity | strings shared between consecutive lenses — **target: under 25%**, against today's 41–97% |
| chrome share of viewport | pixels before the instrument — **target: under 15%**, against today's 38% |
| answer in the hierarchy | is the lens's own conclusion in the top three by visual weight — today it is not, on six of seven |
| scroll to complete a lens | screens — **target: under 1.5**, against today's 6.8 worst |
| trustworthiness | can *what is not verified* be reached in one action |

The last three are the autopsy's findings turned into acceptance criteria. A
direction that does not beat 38% chrome, 41% redundancy and an absent answer
hierarchy has not addressed the problem, however it looks.
