# UX autopsy — ATTEST at 54 commits


> **Historical.** The sixteen-screen UI this autopsy dissects was deleted on 2026-08-22 along with
> `app.js`, `widgets.js`, `board-widgets.js` and `index.html`. The file names
> below no longer resolve. This document is kept because it is the evidence
> that justified the removal — deleting it would leave the decision
> unexplained, and the reasoning is worth more than the code was.

Written before any redesign, per the directive's step 1. Everything below is
measured against the running application, not recalled. The scripts that
produced each number are named so the finding can be re-derived rather than
believed.

The engine is not the problem. This document is about the 3,396 lines of UI in
front of it, and it is deliberately unkind to work I did myself.

---

## A · What exists

**16 screens** across four modes, plus Financial State as a sub-screen of
Attention. **19 API routes.** **26 engine modules**, 9,756 lines. **69 tests**,
**22 failure entries**, six safety gates holding.

    CONTROL      Attention · Act · Overview
    INVESTIGATE  Settlements · Exceptions · What changed · AI trail · Ask
    VERIFY       Accuracy · Failures · Trust centre
    AUTOMATE     Policy · Journal · Agents · Sources · Live events

Cold start is healthy: 3.2s to first data, auto-runs, lands on Attention.

---

## B · Finding 1 — Six screens are one `GROUP BY`

This is the most serious structural problem and it is invisible in code review,
because each screen is individually reasonable.

| Surface | Reads | Shows | Grouped by |
|---|---|---|---|
| Attention | the 250 findings | 198 | verdict, ordered by money |
| Act | the 250 findings | 3 | exception reason, ordered by leverage |
| Exceptions | the 250 findings | 3 | exception reason, ordered by money |
| Overview | the 250 findings | 3 | the same again, as widgets |
| Journal | the 250 findings | 4 | postability |
| Settlements | the 250 findings | 250 | nothing — a flat list |

Six of sixteen surfaces are **one array of 250 findings with a different sort
key**. Act and Exceptions group by the *same* key and differ only in ordering.

They are not six screens. They are six **lenses on one queue**, and the product
charges the user a navigation act to change lens.

## C · Finding 2 — The subject is dropped in 4 of 6 transitions

Measured by opening `setl_000089` from Attention and then navigating, checking
at each step whether the screen still knows which settlement I am working on:

    KEPT   Attention — see it in the queue
    KEPT   Financial State — open it
    LOST   Settlements — the ledger does not select it
    LOST   Policy — would it auto-post? screen cannot say
    LOST   Journal — what entry would it write? screen cannot say
    KEPT   AI trail — by coincidence; it defaults to the largest ambiguous
    LOST   Trust centre — what rules decided it? screen cannot say

The cause is one line in `go()`:

    S.sub = null;

There is no concept of *the thing I am currently working on* that survives
navigation. Every screen is a fresh portfolio-wide question. The one apparent
success is an accident: AI trail defaults to the largest ambiguous settlement,
which happens to be the one I opened.

This is the difference between a product and a set of reports.

## D · Finding 3 — 43% of on-screen text is explanation

| Screen | chars | prose | prose % |
|---|---|---|---|
| automate/events | 690 | 627 | **91%** |
| verify/trust | 1,385 | 942 | **68%** |
| investigate/trail | 3,309 | 2,146 | **65%** |
| control/actions | 1,969 | 1,219 | **62%** |
| verify/accuracy | 1,329 | 737 | 55% |
| automate/journal | 1,653 | 872 | 53% |
| investigate/changed | 2,385 | 792 | 33% |
| automate/agents | 2,734 | 690 | 25% |
| investigate/exceptions | 1,033 | 208 | 20% |
| control/attention | 1,528 | 250 | 16% |
| automate/sources | 2,249 | 273 | 12% |
| **overall** | **20,264** | **8,756** | **43%** |

The prose is good and most of it is true and load-bearing. That is not the
defect. The defect is that it is **always on**, at full length, above the data,
every time — so the product reads as documentation with figures embedded rather
than an instrument with an explanation available.

An operator returning for the ninth time this week does not need to be told
again what a regression gate is. A sceptical engineer on first contact does.
The current UI cannot tell those two people apart and serves the first one the
second one's page.

## E · Finding 4 — Tokens without components

The atom layer is clean: **59 tokens**, **0 raw font sizes**, **0 raw radii**,
0 contrast failures. The molecule layer does not exist.

- **227 distinct CSS classes** for 16 screens — about 14 bespoke classes each.
- **11 different "header" classes**: `.act-h .att-hd .bd-h .ctl-hd .grp-hd
  .je-h .jref-h .pal-h .pk-h .state-hd .sync-h`
- **16 different classes** for the identical *flex row, baseline-aligned*
  molecule.
- **32 rule bodies** duplicated verbatim across selectors.
- 43 inline `style=` escapes in `app.js`; 20 of them bypass the tokens.

Every screen re-implemented "title + count + amount on one line" under a new
name. That is why adding a screen has been cheap and why the product does not
cohere: there is nothing shared above the level of a colour.

## F · Finding 5 — Every screen has the same silhouette

Across the 16 renderers:

    16x  empty state
    16x  spinner
    12x  explanatory paragraph
    11x  page-title block
     6x  metric strip
     4x  clickable row list

Eleven of sixteen open with an identical title block; twelve with a paragraph.
Three-quarters of the product is **title → paragraph → list**. The screens
differ in content and not in form, which is precisely why it reads as "a
collection of fintech SaaS screens" despite the content being unusual.

## G · Smaller findings

- **`drawState` is 307 lines** and `drawPolicy` 255 — the two richest screens
  are the two least componentised.
- **Ask ATTEST is a dead end.** Results link to settlements, but nothing links
  *into* Ask. A question surface nothing routes to is a page, not a command
  line.
- **What changed costs a second full pipeline run (~7s)** on open, with no
  indication that it is doing something expensive and repeatable.
- **The board (Overview) is orphaned.** Widgets, drag, resize, presets and
  keyboard reordering all work, and nothing in the product needs them: the
  same figures appear on Attention, which is the default screen.
- **Sources correctly reports nothing connected.** No faked integration. That
  is right and should survive any redesign.

---

## H · What is worth keeping

Not the shell. Specifically worth preserving:

1. **The four verbs.** CONTROL / INVESTIGATE / VERIFY / AUTOMATE is a good
   statement of purpose, even if it should stop being a navigation bar.
2. **Financial State's four questions** — what we know, why, what would resolve
   this, what ATTEST will do. The single best thing in the UI.
3. **Leverage ranking** in Act. The insight that 197 ambiguous settlements is
   one action survives any redesign.
4. **Screens that demonstrate rather than assert** — Live events sending real
   deliveries, Agents executing the real pipeline, Accuracy reading the same
   files CI reads, AI trail reading `benchmark/anchoring.json`.
5. **The query language and saved views.**
6. **The command palette** — currently a convenience; should become the spine.
7. **Every API route.** The data layer is right; only the arrangement is wrong.
8. **The copy itself** — as progressive disclosure rather than as page furniture.

## I · What the redesign has to fix

    1. six lenses masquerading as six screens
    2. the subject dies on navigation
    3. explanation is always-on instead of on-demand
    4. no component layer between tokens and screens
    5. every screen the same shape
