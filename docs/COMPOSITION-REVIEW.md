# Composition review — A, B, C

Phase 9.2. Three complete compositions were built against identical data, all
seven lenses, both subjects. This records what was measured, what was judged,
which one was chosen, and what was deleted.

**Identical data is structural, not a promise.** All three read through one
`attest/ui/exp/data.js`. A composition receives a plain object and decides only
how it looks. Nothing about the engine, the metrics, the endpoints or the
verdicts differs between them — the only way they could diverge is if a
composition fetched for itself, which none does.

| | A | B | C |
|---|---|---|---|
| | Financial terminal | Spatial investigation desk | Minimal evidence workspace |
| contact sheet | ![A](img/composition-a.png) | ![B](img/composition-b.png) | ![C](img/composition-c.png) |

---

## Measured results

Three things were measured rather than judged, because they are the three most
likely to be argued about.

### Lens differentiation — the core experiment

Every view's DOM was reduced to a **structural signature**: for each visible
element, its tag, display, height band, width band, whether it has a border or
fill, and its font size. Two lenses that look alike produce the same
distribution. The number below is the mean cosine similarity over all 21 lens
pairs on `setl_000089`. **Lower is better.**

| | mean similarity | most-similar pair | second | third |
|---|---|---|---|---|
| **A** | **0.427** | control/policy 0.874 | control/investigate 0.814 | control/journal 0.795 |
| B | 0.664 | journal/policy 0.947 | journal/trust 0.919 | policy/trust 0.892 |
| C | 0.670 | journal/policy 0.926 | control/journal 0.833 | policy/trust 0.813 |

A is measurably more differentiated, and the reason is structural rather than
stylistic. **B and C each use one repeated primitive across all seven lenses** —
`Doc` + `Line` in B, `Sheet` + `Item` in C. They are more beautiful than the
current product and they reproduce its central failure: seven questions answered
in one voice. A uses a genuinely different instrument per lens — proportional
bars, a compression band, column-aligned tables with different column counts, a
boundary meter.

*Limitation, stated because it decides the outcome:* this measures structural
shape distribution, not perceived difference. It cannot see that C's serif claim
sentence makes its lenses feel distinct even where their structure repeats. And
A's own `control/policy` pair at 0.874 is a real weakness that A does not
escape by winning.

### Context integrity

Open `setl_000089` → explanation → inspect → close.

| | opens | subject held during | closes on Escape | subject held after |
|---|---|---|---|---|
| A | ✅ | `setl_000089` | ✅ | `setl_000089` |
| B | ✅ | `setl_000089` | ✅ | `setl_000089` |
| C | ✅ | `setl_000089` | ✅ | `setl_000089` |

All three pass. A failed this at first — its Evidence lens had no context
handler at all, so explanations were not inspectable and the test could not run.
Found by the test, not by looking.

### Responsive — horizontal overflow

| px overflow | 360 | 768 | 1024 | 1512 |
|---|---|---|---|---|
| A | 0 | 0 | 0 | 0 |
| B | 0 | 0 | 0 | 0 |
| C | 0 | 0 | 0 | 0 |

All three failed initially — A by 21px at 768, B by 328px and C by 366px at 360.
All three had the *same* root cause, and it was not the inner rules: `#app` is a
grid, grid items default to `min-width:auto`, so one non-wrapping child set the
whole row's width no matter how carefully the header wrapped. `#app>*{min-width:0}`
fixed all three.

---

## The five-second test

Given `setl_000089 · ₹1,00,036.83 · AMBIGUOUS`, what is readable above the fold
at 1400×900 without scrolling and without prose?

**A** — identity, amount, and the complete spine *with its reasons*: "73 orders
could belong to this credit", "4 explanations satisfy the amount exactly",
"verification did not pass, so nothing was priced". Where it stopped, why it
stopped, and what follows, before reaching the checks.
✅ ✅ ✅ ✅ ✅ — all five answered above the fold.

**B** — identity, amount, then **all seven lens questions** consume the fold
before any data. The strip is self-teaching, and it costs the thing the test
measures. Only the first spine stage is visible.
✅ ✅ ⚠️ ⚠️ ❌ — where and roughly why; proven, disputed and actionable need scrolling.

**C** — identity, the largest amount of the three, the spine as values
(`₹1.00L → ₹1.00L → — → — → —`), then a serif sentence: *"This settlement is
AMBIGUOUS."* The starkest numeric collapse and the clearest single statement,
with the least supporting detail.
✅ ✅ ✅ ⚠️ ❌ — the *why* is a number, not a reason; what can be done is below the fold.

## The three-second test — portfolio

Largest blocked amount, the stage it stopped at, dominant reason.

**A** ✅ Green, green, then a **red** verification bar at ₹5.00L, then hairlines
at ₹354. "STOPS AT VERIFICATION" in red, then immediately
`SYSTEMIC · ₹47,96,811.78 · 1 step · 197 cases`. All three in one screen.

**B** ⚠️ The rail shows the collapse, but blocks of similar height make it a read
rather than a glance, and the questions delay the data.

**C** ✅ States it in words — *"Value stops at verification."* — over a numeric
collapse of `₹53.03L → ₹53.03L → ₹5.00L → ₹354 → ₹354`. Arguably the clearest
single sentence in the experiment. Loses on the third question: the dominant
reason is present but does not compete for attention.

## The lens recognition test

With the strip hidden, can Evidence, Policy, Trust and Activity be told apart?

- **A** — yes for all four. Evidence is a compression band over a five-column
  explanation table; Policy is a three-band boundary meter; Trust is a
  status-led claim register; Activity is an actor-marked event table.
- **B** — Evidence yes (funnel plus split bars), Activity yes (marked causal
  chain). **Policy and Trust are not reliably distinguishable from Journal** —
  0.947 and 0.919 similarity. All three are documents made of lines.
- **C** — Evidence yes (stepped rules with "— an assumption"), Policy yes when
  UNPRICED renders. **Journal and Policy at 0.926** — the same sheet with
  different words.

---

## Scores

1–5, higher is better except #14.

| | A | B | C |
|---|---|---|---|
| 1. immediate comprehension | **5** | 3 | 4 |
| 2. financial hierarchy | 4 | 4 | **5** |
| 3. lens differentiation | **5** | 2 | 2 |
| 4. evidence clarity | 4 | **5** | 4 |
| 5. spatial continuity | 3 | **5** | 3 |
| 6. visual distinctiveness | 4 | **5** | **5** |
| 7. information density | **5** | 3 | 2 |
| 8. cognitive density *(low is good; scored as "kept low")* | 4 | 3 | **5** |
| 9. trustworthiness | 4 | 3 | **5** |
| 10. demo impact | 4 | **5** | 4 |
| 11. responsiveness | **5** | **5** | **5** |
| 12. accessibility | 4 | 4 | 4 |
| 13. motion quality | 3 | **5** | 3 |
| 14. similarity to generic SaaS *(lower is better)* | **2** | **2** | **1** |
| **total** *(with #14 inverted)* | **58** | 54 | 55 |

Accessibility scores identically because all three inherit the same shell:
keyboard traversal, focus restoration, live region, `prefers-reduced-motion`,
`:focus-visible`. None earned a point the others did not.

---

## Chosen: A — Financial terminal

### Why A won

**It is the only one that passes the experiment's own question.** The task was
to test three answers to "how should a reconciliation system feel", and the
autopsy had already named the systemic failure: seven questions, one appearance.
B and C are better-looking versions of exactly that failure — one primitive
repeated seven times. A is measurably differentiated at 0.427 against 0.66 and
0.67, and that difference is visible in the contact sheets, not just the metric.

**It answers all five questions above the fold**, which no other composition
does, on a screen an operator would actually sit in front of.

**Its density serves the thesis.** High information density with low cognitive
density was the stated goal. A puts more true facts on screen than B or C while
using fewer competing signals — hairlines, one accent for money that stopped,
tabular figures throughout.

**It looks like an instrument.** Not a dashboard, not a document viewer, not a
SaaS product. The thing it most resembles is a reconciliation terminal, which is
what it is.

### Why B lost

The spatial metaphor is genuinely the best of the three — the persistent case
tab, the tapering rail, context that lifts off the surface, and the strongest
motion. Its explanation bars (grey shared, red unique) are the single clearest
rendering of ambiguity produced in this experiment.

It lost on two things. **Putting the seven questions in the lens strip is
self-teaching and expensive** — they consume the fold on every view, and the
five-second test is decided above the fold. And **the paper-on-bench chrome
costs real estate**: surfaces, padding and elevation push the data down and
narrow it, in a product whose autopsy finding was that content was already too
compressed.

### Why C lost

C produced the two best individual moments in the whole experiment: the serif
claim line — *"unique within the validated candidate space; the space itself
rests on settlement calendar (rung 0), already claimed, which is a convention
rather than a proof"* — and the stepped compression annotated "— an assumption",
which states ATTEST's central thesis more clearly than anything currently
shipping.

It lost because **restraint at that level is not free**. Density is the lowest of
the three, the collapse must be read rather than seen, and its lenses are
structurally the least differentiated. For a product whose failure mode is
*prose carrying the argument*, a composition that answers with a better sentence
is solving the wrong half.

### The cost of choosing, stated plainly

Choosing means losing things. B's explanation bars are better than A's numeric
columns. C's assumption-annotated compression is better than A's band. These
were not merged in, because §37 says the three do not get averaged into a
compromise, and a compromise would have carried B's chrome cost and C's density
cost along with their strengths.

### What A must fix on its own terms

Recorded now so it is not lost with the deletion:

1. **`control`/`policy` at 0.874 similarity.** A's own weakest pair. Policy's
   boundary meter and Control's spine are both horizontal proportional bars, and
   at a glance they read alike.
2. **The header is a strip, not an identity.** The amount is correctly the
   largest thing on screen, but identity, state and amount are three items in a
   row rather than one composed object.
3. **Motion is the weakest of the three** — scored 3 against B's 5. The
   context-origin animation works, but A does not otherwise use the spatial tier.
4. **Trust on a settlement drops the spine** — the only view in any composition
   where a non-negotiable does not hold.

---

## Deleted

`attest/ui/exp/comp-b.js`, `b.html`, `comp-c.js`, `c.html` — removed, not kept
behind a flag and not preserved as "future components". Both are recoverable
from git history if the decision ever needs re-examining, which is where a
rejected implementation belongs.

The contact sheets above are kept, because a decision whose evidence has been
deleted is indistinguishable from a preference.
