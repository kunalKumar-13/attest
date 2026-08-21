# The ATTEST visual language

Phase 9.3. Composition A — **financial terminal** — built into the product.
This records what changed, what was measured, and one thing the measurement
could not settle.

## 1. Tokens

Every value below resolves to a named variable. The old names are kept as
aliases so no rule had to be rewritten to obey the scale — the discipline is in
what they resolve to, not in a rename.

| | before | after |
|---|---|---|
| type sizes | **9** — 9, 10.5, 11.5, 13, 15, 19, 24, 30, 42 | **6** — display 34, title 20, data 15, body 13, label 11, micro 10 |
| spacing | **7** — 4, 6, 9, 13, 19, 27, 38 | **8** — 4, 8, 12, 16, 20, 24, 32, 40 |
| radii | **6** — 2, 3, 6, 9, 12, pill | **2** — 4 small, 8 large (+ pill for status marks) |
| motion | **2** — `.12s`, `.22s` | **3** — micro `.13s`, standard `.2s`, spatial `.3s` |

The accidental pairs are gone: `13`/`13.5` and `8.5`/`9` were not decisions,
they were the residue of choosing at the call site. `DATA` is a role rather than
a size — financial values must never render as body copy.

**Measured after:** `10 · 11 · 13 · 15 · 20 · 34`. The `16px` the audit still
reports belongs to `<html>`/`<head>`/`<title>`, which have no rendered box; it
is an artifact of the measurement, not a size in the interface.

## 2. The subject header

One composed identity, not four fields in a row.

```
setl_000089   AMBIGUOUS   stops at VERIFICATION        ₹1,00,036.83
value date 2026-05-08 · UTR 999926430521 · explanations 4      BANK CREDIT
```

The amount is now **34px/500 against 13px/400 body** — it was 13.5px beside an
identity at the same weight, which is the autopsy's finding that the financial
subject of the case read as a field in a record. The stage hangs off the
identity because it is a property *of* the case, not a neighbour of it, and it
is read from the spine the shell already fetched rather than drawn twice.

The header is patched, never re-rendered. Measured stable at 89.5px across a
lens change.

## 3. The state spine is structural

It is rendered **by the shell**, above every lens, for both subjects.

Before: it appeared on 2 of 14 views, because it was whichever lens chose to
call `StateSpine`. On Trust it vanished entirely — the one lens where a reader
is holding "where did the money stop" while reading about the system's failures.

**Measured after: present on all 14 views.** Making it a property of the shell
is what makes "no exceptions" true rather than a promise seven files have to
keep. Control was drawing a second one directly beneath it; that is gone.

## 4. No empty context pane

The pane was already hidden when nothing was selected — but its **grid column
stayed**, so the master rendered at 54% of the workspace and the other 46% was
reserved for a sentence.

**Measured after: master 100% with no context.** `has-pane` says a lens *can*
hold a context; `has-ctx` says one is open. The absence of a context is the
correct state, and it is also what gives the opening transition something to
mean.

That change had a consequence worth recording, because it took four attempts to
get right. Opening a context now narrows the master, which reflows it, and
`test_the_master_scroll_position_survives_open_and_close` began failing at 413,
then 393. The cause was not clamping:

- Chrome's **scroll anchoring** adjusts `scrollTop` when layout shifts, and that
  adjustment fires a scroll event indistinguishable from a real one.
- A naive tracker therefore records *the reflow* as the reader's intent, and
  then faithfully restores the wrong number.
- `renderContext` can run more than once per open, so re-reading `scrollTop`
  reads what the first pass already moved.

The fix is `overflow-anchor:none` on the master, a continuously-tracked
`MASTER_SCROLL`, and a `SETTLING` flag so the shell ignores the scroll events it
causes itself. §7 says the master is where the reader already was, so the
position is ours to decide rather than the browser's.

## 5. Seven instruments

| lens | primary instrument | secondary |
|---|---|---|
| Control | money flow — the spine, then leverage | action groups ranked by value unlocked |
| Journal | double-entry ledger | refusals with their stated reason |
| Evidence | cumulative search-space compression | surviving explanations, shared vs unique |
| Investigate | **test ledger** — claim left, outcome right | the signal that had nothing to say |
| Policy | decision boundary | priced strata, or UNPRICED |
| Activity | **causal chain** — cause linked to event | where it ended up |
| Trust | claim → measurement → limitation | failures first |

Two of those are new in this phase. Investigate and Activity were the product's
closest pair, and both rendered as a flat vertical list of actor-marked steps.
Now Activity is a chain — events linked downward by a connector carrying their
cause — and Investigate is a ledger of attempts in columns, because the question
it answers is *what was tried and did it work*.

## 6. The similarity report, and its limit

Mean cosine similarity over all 21 lens pairs, on structural signatures:

| | mean | control/policy | worst pair |
|---|---|---|---|
| product before 9.3 | 0.278 | 0.238 | investigate/activity 0.663 |
| composition A | 0.427 | **0.874** | control/policy 0.874 |
| **product after 9.3** | **0.315** | **0.295** | investigate/activity 0.725 |

**Control and Policy: 0.874 → 0.295.** That was the explicit target and it is
met. The 0.874 was A's own weakness, introduced when A drew both as horizontal
proportional bars; the product never had it.

The mean rose from 0.278 to 0.315, and that rise is honest: **the spine is now
on every view.** A deliberate constant across all seven lenses raises pairwise
similarity by construction. Removing it would improve the number and damage the
product.

**Where the metric failed.** Investigate and Activity went 0.721 → 0.718 → 0.725
across three genuine structural redesigns — a connector-based causal chain, an
indented effect, and a two-column test ledger. The metric did not move because
it bins elements by tag, display, height band, width band, border, fill and font
size, and two lenses built from the same `div`/`span` vocabulary at the same
sizes produce nearly the same distribution however differently they are
arranged. It discriminated well between A, B and C, which differed in their
*primitives*; it cannot resolve a chain from a ledger.

They are visibly different now — see the contact sheet. The number says
otherwise, and the number is wrong here. Recording that rather than continuing
to optimise against a metric that had stopped responding, or claiming a win the
measurement does not support.

## 7. Surfaces

| | before | after |
|---|---|---|
| surfaces > 60×24 | 229 | 230 |
| rounded | 151 | 151 |
| bordered | 34 | 35 |
| shadowed | 3 | 3 |

Unchanged, deliberately. The goal was never zero surfaces — it was that every
surface has a semantic reason, and the product had already been through that
reduction (nineteen boxes to three). What changed is that the six radii those
surfaces used are now two.

## 8. Responsive

| width | horizontal overflow | spine visible on all seven lenses |
|---|---|---|
| 360 | 0 | yes |
| 768 | 0 | yes |
| 1024 | 0 | yes |
| 1512 | 0 | yes |

The financial stage model is never hidden — it compresses.

## 9. Regression

**247 tests · 90 browser contracts · six gates at +0.0000.**

One contract was updated rather than fixed, and the distinction matters.
`test_a_result_is_discarded_when_the_subject_moved_during_the_request` asserted
Control was showing by looking for "Where it stopped" — a heading that moved out
of Control and into the shell's spine, where it no longer identifies anything.
The guarantee is unchanged and still asserted: the stale journal must not land,
and Control must be what is showing. Only the thing that identifies Control
changed, so the selector did.

No screenshot tests were added. Nothing here locks a pixel.
