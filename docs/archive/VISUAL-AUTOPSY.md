# Visual autopsy — the seven lenses, side by side

Phase 9.1. Every number below was measured against the running product on
2026-08-22 by walking all fourteen views (7 lenses × 2 subjects) at 1400×900 and
reading the computed styles, then looking at the screenshots as two contact
sheets. Nothing here is recalled.

> Not to be confused with `docs/UX-AUTOPSY.md`, which dissected the
> sixteen-screen UI that was deleted. This one is about the Case Desk.

## What was measured

| view | elements | surfaces | font sizes | colours | prose | words |
|---|---|---|---|---|---|---|
| portfolio/control | 151 | 5 | 5 | 7 | 48% | 241 |
| portfolio/journal | 58 | 2 | 5 | 3 | 28% | 108 |
| portfolio/evidence | 65 | 1 | 4 | 5 | **70%** | 198 |
| portfolio/investigate | 30 | 2 | 5 | 4 | **60%** | 60 |
| portfolio/policy | 107 | 3 | 5 | 7 | 45% | 98 |
| portfolio/activity | 168 | **12** | 5 | 8 | **56%** | 379 |
| portfolio/trust | 288 | 2 | 6 | 6 | **74%** | **1,121** |
| settlement/control | 99 | 1 | 6 | 4 | 20% | 151 |
| settlement/journal | 14 | 1 | 4 | 4 | — | 42 |
| settlement/evidence | 124 | 2 | 4 | 7 | **70%** | 255 |
| settlement/investigate | 76 | 5 | **7** | 7 | **71%** | 197 |
| settlement/policy | 89 | 2 | 6 | 4 | 38% | 195 |
| settlement/activity | 120 | **9** | 5 | 6 | 25% | 189 |
| settlement/trust | 3 | 0 | 2 | 2 | — | 16 |

*Prose = share of words in blocks longer than eight words. The measure
double-counts nested spans, so treat it as an index rather than a percentage;
the ranking is what matters, and the ranking is stable.*

---

# The systemic problems

Seven findings. Not thirty fixes — the individual issues are symptoms, and
several of them have one cause.

## 1. Seven questions, one appearance

**This is the finding that matters most.** Every lens is built from the same
three moves: a small-caps grey label, a left-aligned block of text, then rows.
Control, Journal, Policy, Activity and Trust are visually interchangeable at a
glance — and the contact sheet makes it obvious, because you cannot tell which
lens you are looking at without reading the strip.

The measurement agrees: `10.5px` and `13.5px` dominate the font histogram in
every one of the fourteen views, and the same `.c-disc` disclosure row is the
largest bordered element in six of them.

The product's whole claim is that these are seven *different questions*. The
interface answers them in one voice. Evidence does not look like evidence;
Trust does not look like trust; Activity does not look like causality.

## 2. Half the canvas is a placeholder

On five of seven portfolio lenses, the empty context pane occupies
**756 × 707 px — 54% of the workspace — to display eight to ten words** of
"Select an action to see a settlement to inspect it."

The master content is compressed into the remaining 46% while the larger half
of the screen holds a sentence. On a canvas that is supposed to feel continuous
and spatial, the dominant spatial fact is an apology for nothing being selected.

## 3. There are values, but there are no scales

| token | distinct values found | evidence of accident |
|---|---|---|
| font size | **9** — 8.5, 9, 10.5, 13, 13.5, 15, 19, 24, 30 | `13` and `13.5` both used heavily (87 and 410 nodes); `8.5` and `9` likewise |
| radius | **6** — 2, 3, 6, 9, 12, pill | no step relationship between any two |
| spacing | **16** — 1…22px | frequencies are flat (2px:28, 7px:20, 5px:18, 9px:17): no dominant step |
| weight | 4 — 400, 500, 600, 700 | **500 appears 6 times in the entire product** |
| motion | **2** — `--fast .12s`, `--med .22s` | no slow or spatial tier exists |

A pair like 13px and 13.5px is not a decision. Fifty-one CSS custom properties
are defined and the type ramp is still improvised at the call site.

## 4. Prose is carrying the argument

Six of fourteen views are more than half prose, and `portfolio/trust` is
**1,121 words** — an essay. `settlement/investigate`, both Evidence views and
`portfolio/investigate` are all around 70%.

The design thesis asks: *can I understand where money stopped without reading
paragraphs?* On those six views the honest answer is no. The writing is good,
which is exactly why it has been allowed to do work that structure should do.

## 5. The best idea in the product is a corner widget

The State Spine renders at roughly 215px wide in the top-left of Control, and
appears on two of fourteen views. It is the one element that answers "where does
money stop" **pre-verbally** — long, long, stub, nothing, nothing — and you can
read it before you read anything.

It is currently smaller than the empty context pane by a factor of twenty-three.

## 6. The amount is not the subject

`₹1,00,036.83` renders at 13.5px in the header — the same size as body text,
next to an ID at the same weight. The 24px and 30px sizes exist but account for
17 nodes across all fourteen views combined.

The money is the financial subject of the case and it currently reads as a
field in a record.

## 7. Motion is decoration-grade, not spatial

Eleven of twenty-one transition declarations are `:hover` background changes.
The context-origin animation is real — `ctx-in`/`ctx-out` keyed off a
`--oy` captured from the clicked row's rectangle — but it is the only spatial
motion in the system, and it runs on the same `.22s` token as a hover tint.
There is no slow or spatial tier to distinguish "this object opened" from "this
row is warm."

`prefers-reduced-motion` is honoured in two places and `:focus-visible` has a
single rule.

---

## What is already right, and must not be lost

Naming these because a redesign is as likely to destroy them as to improve them.

- **The State Spine's proportional collapse.** It is the thesis, rendered.
- **The context-origin motion.** Objects emerge from the row that owns them.
- **Surface discipline.** One to five surfaces on most views — the old UI's
  nineteen-boxes problem has not regressed. Activity (12 and 9) is the exception.
- **Evidence's candidate-universe bars**, which are the closest thing in the
  product to a proof sheet.
- **Trust starting with bad news** — "The uncomfortable numbers first / 24
  recorded failures".
- **Policy refusing to price the unpriceable**, showing UNPRICED rather than
  inventing a zero.
- **`settlement/trust` declining to render** and saying why.

## The one-line diagnosis

The Case Desk has the right information architecture, honest content, and no
card soup — and it renders all of it as **one continuous document at one
typographic pitch**, with the most important element small, the most spatial
element empty, and the argument carried by sentences.
