# Final UX direction

Phase 9.0. Written after measuring the running product — see
`docs/VISUAL-AUTOPSY.md` for the evidence this responds to. No UI code has been
changed at this point.

The seven questions, the three axes, and the engineering are frozen. What
follows is the visual and interaction language built around them.

---

## 1. Visual thesis

**A financial investigation workstation.** Something an operator sits in front
of for hours: dense when necessary, quiet when nothing needs attention,
unmistakable when money is blocked.

The measure of success is not that ATTEST looks impressive. It is that the
operator moves through four thoughts in order:

1. I understand exactly what happened to this money.
2. I understand why the system believes it.
3. I understand what it refuses to claim.
4. I know what I can safely do.

Three rules fall out of that, and each is a direct answer to an autopsy finding.

**Structure carries the argument; prose annotates it.** Six of fourteen views
are currently more than half prose. Where a sentence explains a relationship, a
relationship should be drawn and the sentence should become its caption.

**The money is the subject, not a field.** The amount is currently 13.5px beside
an ID at the same weight. It becomes the largest thing in the case.

**Each lens is a different instrument.** Right now you cannot tell which lens
you are in without reading the strip. Seven questions must not share one voice.

### What it must not look like

Stripe dashboard · generic fintech SaaS · admin panel · Notion · Linear clone ·
table-heavy ERP · AI chatbot · hackathon landing page.

The failure mode to watch for is *card soup with good typography*. A screen that
would survive having its labels swapped with another product's is a failed
screen.

---

## 2. Layout system

The workspace is a **canvas**, not a stack of pages. Three things persist across
every lens change and never re-render: the **subject header**, the **lens
strip**, and the **state spine**.

```
┌──────────────────────────────────────────────────────────────┐
│  SUBJECT HEADER          identity · state · amount           │
├──────────────────────────────────────────────────────────────┤
│  LENS STRIP              seven keys                          │
├────────────┬─────────────────────────────────────────────────┤
│            │                                                 │
│   SPINE    │   MASTER                          CONTEXT       │
│  (always)  │   the lens's own composition      (on demand)   │
│            │                                                 │
└────────────┴─────────────────────────────────────────────────┘
```

**The spine gets a permanent column.** It moves out of Control's corner and
becomes a persistent left rail on every lens, for every subject. It is the one
element that answers "where does money stop" before any reading happens, and it
should be answering that continuously rather than on two views out of fourteen.

**The context pane does not exist until something is inspected.** The empty pane
currently takes 54% of the workspace to hold nine words. When nothing is
selected, the master owns the full width; when an object is inspected, the
master yields. That is also what makes the transition mean something.

### The grid

A 4px base unit, and a spacing scale with actual steps:

```
4  8  12  16  24  32  48  64
```

Sixteen improvised values between 1px and 22px collapse into these eight. Nothing
outside the scale, and no value is chosen because it looked right at one
zoom level.

---

## 3. Typography

One family for prose and UI, one for numbers. The number face must have
**tabular figures** and must not be chosen for personality.

### The ramp

Nine sizes with two near-duplicate pairs become **six**, each with a job:

| step | size | weight | used for |
|---|---|---|---|
| `amount` | 34 | 500 | the financial subject, once per case |
| `subject` | 20 | 600 | identity, the lens's headline question |
| `figure` | 15 | 500 | numbers inside the composition |
| `body` | 13 | 400 | statements, row content |
| `label` | 11 | 600 | small-caps section labels, uppercase |
| `micro` | 10 | 400 | provenance, timestamps, secondary counts |

`13px` and `13.5px` merge into `body`. `8.5px` and `9px` merge into `micro` at
10px — the current 9px is below what an operator should read for hours.
Weight `500` currently appears six times in the entire product; it becomes the
numeric weight and earns its place.

### Financial numbers

Non-negotiable, because these are the product:

- `font-variant-numeric: tabular-nums` on every figure
- Indian digit grouping — `₹1,00,036.83`, not `₹100,036.83`
- decimals always present, never trimmed
- right-aligned wherever two numbers can be compared vertically
- the currency mark at a lighter weight than the digits, so the eye lands on
  magnitude first

A number that changes must not reflow the layout around it. Reserve the width.

---

## 4. Colour system

Colour is semantic. It never decorates, and **it is never the only carrier** —
every state has a symbol or a structural difference as well, because the browser
contracts already assert that policy decisions are readable without colour and
that must not regress.

| meaning | role | non-colour carrier |
|---|---|---|
| PROVEN | resolved | filled mark ● + label |
| AMBIGUOUS | withheld | split mark ◑ + label |
| CONTRADICTED | conflict | struck mark ⊘ + label |
| INSUFFICIENT | out of envelope | hollow mark ○ + label |
| UNREVISED | stale | dotted underline + label |
| AUTO-POST | permitted | solid rule under the row |
| REVIEW | held | dashed rule |
| ABSTAIN / BLOCK | refused | no rule, indented reason |

Actors keep their existing grammar exactly (§13): **MODEL ◇ · SOLVER ○ ·
ENGINE ●** — hollow, ringed, filled. The progression from hollow to filled *is*
the argument, and it survives greyscale, which is the point.

The surface palette is near-monochrome: two backgrounds, one hairline, three ink
weights. Money-blocked states are the only place saturated colour appears, so
that when something is wrong it is the only coloured thing on screen.

---

## 5. Surface system

**Default: no container.** A box must justify its existence. Rows are lines;
relationships are lines; evidence is structured space. The old UI's nineteen
rounded boxes went to three and must not regress.

Radii go from six values to **two**: `4px` for surfaces, `pill` for status
marks. 2, 3, 6, 9 and 12 all collapse.

A surface is permitted for exactly four things:

1. an **action** the operator can take
2. a **context** object under inspection
3. a **boundary** that is genuinely a boundary (the policy threshold)
4. a **refusal** that needs to stop the eye

Activity currently carries 12 and 9 surfaces. Its events become lines on a
causal spine, not cards.

**More than four meaningful surfaces on a screen is a failure**, and the
question to ask is: can these be rows, can this be a drawn relationship, can
whitespace do it?

---

## 6. Navigation

Three axes, addressable, unchanged: `#/settlement/setl_000089/journal?in=order:ord_000819`.

**The lens strip is not tabs.** Seven keys in a fixed order, rendered as a
vertical ladder of short labels against a hairline, each with a state mark
showing whether that lens has anything to say about the current subject. The
active key is indicated by weight and a solid indent — a physical key seated in
the lock — not by a filled pill.

Switching lens **transforms the workspace**: the spine and header hold still,
the master composition cross-fades and re-lays out beneath them. It must never
read as a route change.

**The command palette stays, as case navigation** — subjects, lenses, saved
views, actions, trust claims. Not application search, and never a chat box.

---

## 7. Motion

Three tiers, replacing the current two:

| tier | duration | for |
|---|---|---|
| micro | 100–160ms | hover, selection, focus |
| standard | 160–240ms | lens change, filter, disclosure |
| spatial | 240–360ms | context open and close |

Easing `cubic-bezier(.2,0,0,1)` for entrances; a gentle spring for the context
pane only, because it is the one motion that models a physical object.

**Context-origin motion is preserved exactly.** The pane emerges from the
clicked row's rectangle and returns toward it — the existing `--oy` mechanism
stays. It must communicate *this object opened*, never *a page transition
happened*.

Motion never runs to look good. If it is not showing hierarchy, causality,
continuity, state change, or a spatial relationship, it should not run.

`prefers-reduced-motion` collapses **durations**, never feedback. A reduced-motion
user must still see that the context opened and where it came from.

---

## 8. Density

**High information density, low cognitive density.** Many facts, few competing
signals.

Concretely: row height 28px, comfortable line length capped at 68 characters for
prose, and no more than **three** competing visual signals in any one region —
where a signal is a colour, a weight change, or a rule.

Density is not smallness. The current 9px body text is dense in the wrong way:
it fatigues without fitting more meaning on screen. Density comes from removing
chrome, not from shrinking type.

---

## 9. Data visualisation

Every visual answers a question that a number alone cannot.

**The state spine** — proportional flow, five stages, showing where value stops.
Never five cards, five pills, five equal boxes, or five checkmarks. The
collapse must be legible before any number is read.

**Search-space compression** (§15) — a signature. `2,368 orders → 2,295 excluded
by convention → 73 candidates` drawn as a collapsing band, not 2,368 nodes. It
must say *most of the world was removed before solving*, and that the removal is
itself an assumption.

**Ambiguity** (§16) — never a warning triangle. Draw the shared core and the
disputed remainder: `27 shared + 4 unique` against `27 shared + 5 unique`, so
what is agreed and what is disputed are visible without prose.

**The policy boundary** (§18) — a threshold on a line, drawn only where an error
probability actually exists. For AMBIGUOUS, show **UNPRICED** and say the proof
was never established. Never invent a zero.

**Causality** (§19) — cause → event → effect on a vertical spine using the
MODEL/SOLVER/ENGINE marks. Not a log table.

---

## 10. Context / drawer behaviour

The context pane is **the object being inspected**. Not a modal, not a sidebar,
not a page.

- It does not exist until something is inspected. No empty placeholder pane.
- It emerges from the row that owns it and returns toward it.
- It states the chain it hangs off, so its provenance is never ambiguous.
- It nests — explanation → order — without becoming a stack of modals.
- It is addressable in the URL and survives reload.
- A context the next lens cannot hold is **dropped visibly**, never silently.
- The subject stays visible underneath. Inspecting is not navigating.

---

## 11. Responsive behaviour

| width | composition |
|---|---|
| ≥1200px | spine rail + master + context beside it |
| 768–1199px | spine collapses to a compact bar; master + context stacked |
| <768px | master, with context as a full-width overlay sheet |

The three axes survive at every width. Desktop spatial complexity is never
reproduced on a phone — no drag, no resize handles. Horizontal overflow is zero
at every width from 360px up, which is currently true and untested; it becomes a
contract.

---

## 12. Accessibility

Nothing here regresses. Every item below is already true and stays true.

- keyboard movement through every interactive element, in document order
- **focus restoration**: closing a context returns focus to the row that opened it
- live regions announcing verdict and context changes
- `prefers-reduced-motion` honoured, feedback preserved
- ARIA labels on the spine, lens strip and context chrome
- `:focus-visible` everywhere and never suppressed — currently one rule, which
  becomes a rule per interactive family
- WCAG AA contrast at every size, including the 10px micro step
- **every spatial interaction has a non-pointer equivalent**

The autopsy found `:focus-visible` defined once and `prefers-reduced-motion`
honoured in two places. Both need to be systematic rather than spot-applied.

---

## 13. Empty states

Never "No data found." An empty state answers three questions: **what is empty,
why, and what can be done.**

```
NO UNREVISED SETTLEMENTS

All ingested events are reflected in current verdicts.
Last event 02:01:30 · 8 events this run
```

An empty state that is *good news* should read as good news. The Trust lens
declining to render on a settlement is already correct in content — "Trust is a
property of the system, not of one settlement" — and needs the structure to
match: it is an answer, not an absence.

---

## 14. Loading states

**Loading must never feel like navigation.**

- no full-screen spinner, ever
- skeletons only where geometry is known, matching the final layout's rhythm
- when a **context** is loading, the master stays fully visible and interactive
- when a **lens** is loading, the header and spine hold; only the master area
  resolves
- a request slower than 400ms shows a skeleton; faster than that shows nothing,
  because a flash of skeleton is worse than a beat of stillness

The stale-fetch guard already discards results for a subject that moved. The
visual layer must match: a subject that changed mid-flight never shows the old
subject's skeleton filling with new data.

---

## 15. Error states

An error states **what failed, what remains true, and what can be done.** The
middle one is the one most products omit, and for this product it is the most
important: a source being unavailable does not make the existing verdicts wrong.

```
RAZORPAY SOURCE UNAVAILABLE

Last verified ingestion   2026-08-22 02:31
Current verdicts          unchanged

                                          [ RETRY ]
```

Rules:

- never a raw exception, never a status code alone
- distinguish *the source failed* from *the engine failed* from *this view
  failed* — they have different consequences and different remedies
- an ingestion error must say whether anything was partially read, because a
  half-read pull is worse than a failed one
- a rejected record from the adapter is an error state with a row index and a
  reason, not a count

---

## What is preserved, explicitly

Redesigns destroy good things by accident. These are already right:

- the State Spine's proportional collapse
- context-origin motion via the clicked row's rectangle
- surface discipline — no return to card soup
- Evidence's candidate-universe bars
- Trust starting with bad news, and failures as first-class
- Policy showing UNPRICED rather than a fabricated zero
- `settlement/trust` declining to render, and saying why
- the four-state verdict vocabulary, unchanged
- MODEL ◇ → SOLVER ○ → ENGINE ● as an ordered argument

---

## Next: three compositions, then two deletions

Per §37, this direction gets built three ways against the same data — a
**financial terminal**, a **spatial investigation desk**, and a **minimal
evidence workspace** — then compared on first impression, density, spatial
continuity, case understanding, and distinctiveness.

Two get deleted. They do not get merged into a compromise.
