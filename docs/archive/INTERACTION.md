# Interaction — the finished product

Phase 9.4. The composition and the engineering are frozen; this is what was
measured, what was fixed, and two things that were not.

## The golden journey

Portfolio → Control → a settlement as context → promoted to subject → Evidence →
an explanation → Investigate → Policy → Activity → Trust → back.

Walked end to end and measured at each step. **No page ever reloads and the case
never moves.** What changes at each transition, measured rather than intended:

| transition | changed | held |
|---|---|---|
| open context | context, url, master width, focus | subject, lens, spine, scroll |
| promote to subject | subject, context, url, master | lens, spine |
| lens change | lens, url | subject, spine, header, scroll |
| lens change (unholdable context) | lens, url, context | subject, spine, header |
| back | context only | subject, lens, spine |
| reload | nothing | everything |

Nothing animates that logically remains unchanged. The header is patched rather
than re-rendered and measures **89.5px before and after** a lens change.

## Performance

Median of five, at 1400×900:

| | ms |
|---|---|
| context open | **4** |
| context close | **7** |
| lens switch | **9** |
| subject change | **8** |
| cold reload | 2,887 |

Every interaction is under 10ms. The cold reload is the run itself — the engine
reconciles 250 settlements before the first paint — and is the only number here
worth attacking, which is a backend question and therefore out of scope.

## The final interaction contract

All eight clauses verified against the running product:

```
PASS  SUBJECT persists across a lens change
PASS  CONTEXT is dropped visibly where a lens cannot hold it
PASS  SPINE persists
PASS  URL reflects context
PASS  Back closes the context before it navigates
PASS  Reload restores subject and lens
PASS  FOCUS returns to the row that opened the context
PASS  SCROLL persists across open
```

ESC, the close button and Back converge on byte-identical state:
`context null · #/portfolio/control · master 1400px`.

## What was fixed

**The mobile spine was 416px of a 780px viewport** — 53% of a phone screen spent
on the header of every lens. The cause was not the mobile rules: the base rail
block written in 9.3 had been lost to a later line-insert, so the spine had been
rendering with the *desktop* stacked treatment and positioning correctly only by
accident of implicit grid rows. Restored, plus a rail treatment that collapses
each stage to a single line of label, bar and figure. **416px → 174px**, and the
stage where money stopped keeps its sentence, because that is the answer.

**There was no command palette.** It lived in the sixteen-screen UI and went with
it, which left the keyboard journey requiring a tab through a queue of 250 to
reach a settlement. `attest/ui/palette.js` navigates the three axes and nothing
else — subjects, lenses, and the settlements this run actually flagged, published
from data Control already fetches rather than by adding an endpoint. Subsequence
matching, so `setl_0000` finds the queue and `evid` finds Evidence. It is not
search and it is not a chat box.

**Closing the palette dropped focus to `<body>`** when nothing had been focused
before. It now lands on the active lens, which is a real place to be.

**Trust stated one adapter boundary of six.** The frozen boundaries lived in
`docs/RAZORPAY-INTEGRATION.md`, and Trust is where a reader looks to find out
what the system will not say — a boundary recorded only in a markdown file is a
boundary nobody reads at the moment it matters. All six are now in the lens,
including **"Live account validation is NOT VERIFIED"** stated in those words.

## The canonical dataset

Eleven states, produced by the run rather than by demo-only code:

| | state | where it appears |
|---|---|---|
| A | clean proven settlement | policy auto-post = 1 |
| B | ambiguous settlement | 186 cases, ₹47,50,945.53 |
| C | contradicted settlement | 1 case |
| D | search-space boundary | 3 of 5 reductions are conventions |
| E | bad model hypothesis | the capture-batch anchor, non-discriminative |
| F | solver rejection | `NON DISCRIMINATIVE` against uniqueness |
| G | policy auto-post | 1 |
| H | policy review | 249 |
| I | activity trail | 8 deliveries, 8 events |
| J | Trust limitation | 2 of 8 claims not MEASURED, 11 unknowns |
| K | Razorpay adapter evidence | 6 frozen boundaries in Trust |

No demo-only UI exists. The product renders these because the run contains them.

## Density, against Phase 9.1

| | 9.1 | now |
|---|---|---|
| elements across 14 views | ~1,700 | 1,727 |
| surfaces > 60×24 | 46 | 46 |
| bordered | — | 23 |
| tabular-figure nodes | not measured | 145 |

Information held steady; the noise did not grow. Two views moved and both are
honest:

`portfolio/trust` went from **1,121 words to 1,388**, because five adapter
boundaries were added to it. That is the lens the 9.1 autopsy called an essay,
and it got longer. It is defensible on the rule the autopsy actually set: prose
must answer *why*, *what does this mean*, *what is the limitation* — and must not
be responsible for *where is the money*, *what stage*, *how much*, *what action*.
Every word added answers the first kind. Trust is where an auditor reads.

## Copy

No banned term appears anywhere in the product across all fourteen views:
*overview, insights, smart, AI-powered, get started, manage, optimize, monitor,
analytics, dashboard, something went wrong, no data found.* The vocabulary is
ATTEST's: VERIFICATION, UNEXPLAINED, PROVEN, ABSTAINED, VALUE UNLOCKED, SEARCH
SPACE, UNREVISED, UNPRICED.

## Reduced motion

Under `prefers-reduced-motion: reduce`, animation duration collapses to `0s` and
the context still opens, renders and closes. No information depends on movement.

## Responsive

Zero horizontal overflow at 360, 393, 430, 768, 1024 and 1512. Context is a
full-width overlay below 768. The spine compresses and is never hidden — the
financial stage model is the last thing that should leave a small screen.

## Regression

**251 tests · 94 browser contracts · six gates at +0.0000.**

Four contracts were added, each for a guarantee that had been a defect: the
spine on all fourteen views, the master owning full width until something is
inspected, the palette reaching a settlement by keyboard alone, and focus never
returning to the document. No screenshot tests. Nothing locks a pixel.
