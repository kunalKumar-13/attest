# Phase 1 product gate

Reviewed against the four transitions and the §30 five-second question. No
lenses were built. Four things were redesigned because the review demanded it;
everything else is recorded rather than acted on.

The honest headline: **the review failed §27 on first inspection.** Shown side
by side, the four views would have read as four dashboard pages — not because
the content was generic but because the *composition* was identical in all
four. The autopsy warned about title → paragraph → list; I had avoided that and
built SUBJECT HEADER → SECTION → SECTION → SECTION instead. The same failure,
one level up. That is now fixed.

---

## A · What is excellent

**The flow.** After redesign, the single strongest thing in the product. A bar
collapsing from full width to a sliver at Verification says *where the money
stopped* before a single figure is read.

    SOURCE        ████████████████████████████  ₹53,02,701.96
    MATCHING      ████████████████████████████  ₹53,02,701.96
    VERIFICATION  ███                           ₹4,99,574.15   ₹48,03,127 held · 198
    POLICY        ▏                             ₹353.73        ₹4,99,220 held · 51
    ACTION        ▏                             ₹353.73

**The section headings.** Zero generic SaaS words in rendered copy, verified by
scanning every string the app renders. "Where the money stopped", "What unlocks
the most", "Needs a person", "Why it is unresolved", "The money trail" — the
product's voice is already distinctive.

**The money trail** on settlement × journal, and **the candidate bars**, which
show the one thing that distinguishes four explanations: 27 shared + 4.

**The continuity architecture.** Six invariants held by browser tests including
the stale-async case. This is settled and should not be reopened.

## B · What still feels generic

**Portfolio × journal is sparse.** Three metrics, one entry row, three groups,
and a great deal of nothing. It is the weakest of the four and reads as a
report rather than an instrument.

**`.c-metrics` is a KPI row wearing better type.** It is the one component that
could appear in any fintech product unchanged. It survives for now because it
is honest and dense, but it is the first thing to redesign in Phase 2.

## C · What still feels like a route

Nothing, in the navigation sense — subject and lens are genuinely independent
and nothing resets. But **every view is a single vertical column**, so movement
through the workspace is still *scrolling* rather than *moving*. §17 asked for
master/detail, drawers and split views and got none. This is the largest
remaining gap and it is deliberately unaddressed here, because it changes every
lens and belongs at the start of Phase 2 rather than the end of Phase 1.

## D · What was redesigned in this gate

1. **The spine became a flow.** It was five equal cards with ✓/✕ — a stepper
   wearing a financial diagram's clothes. A reader had to compare five numbers
   themselves to notice ₹53.03L → ₹4.99L → ₹353. Now the bar width is
   proportional to what *continues*, and the narrowing is the message.
2. **Card discipline.** 19 rounded boxes on portfolio × control → 3. A row is a
   line in a ledger and gets a hairline; only actions, the primary interactive
   object, keep a surface. The surface now means something because it is not
   applied to everything.
3. **The header binds the amount to the identity.** `setl_000089 AMBIGUOUS` and
   `₹1,00,036.83` were separated by 950px of nothing and read as two objects.
   The amount now sits against the identity behind a hairline rule.
4. **The lens strip stopped being browser tabs.** Underline and active-weight →
   uppercase legends with a filled active key.
5. **Two title-and-a-sentence sections became one decision block.** "What would
   resolve it" and "What ATTEST will do" are two halves of one answer.

## E · What should be deleted

- **`Panel`** — declared in the component layer and used by nothing. A
  component with no caller is a guess about the future.
- **The `jump` transition.** Both axes changing at once happens only via the
  URL, and it renders as an unremarkable fade. It is a third code path earning
  nothing.
- **`opts.detail` on the flow** — no caller passes it.

## F · What should become contextual

- **The withheld groups on portfolio × journal** should expand in place rather
  than link away. The reason is the subject; the settlements are its detail.
- **The attention queue's `+ 181 more`** is a dead end. It should reveal.
- **The candidate explanations** should let you pin one and see which orders
  differ, without leaving Control.

## G · What should become a reusable component

Extracted from what the two lenses actually needed twice or more:

| Component | Status |
|---|---|
| `SubjectHeader` `LensStrip` `StateSpine` | built, stateful, contract holds |
| `Metric` `MetricRow` `Row` `Section` `Disclosure` `DataTable` | built |
| `Status` `Amount` `EmptyState` `LoadingState` `ErrorState` | built |
| **`Decision`** | built inline in Control this gate — extract it |
| **`Group`** | `.c-group` is re-implemented in both lenses — extract it |
| **`Trail`** | lives in the journal lens; Evidence will want it |
| **`Timeline`** | not built; Activity and Investigate will both need it |
| **`Drawer`** | not built; required for §F and for §17 |

`Panel` should be deleted rather than kept.

## H · Final visual direction

**Financial instrument, not dashboard.** Concretely, four rules that now have
evidence behind them rather than taste:

1. **Proportion over enumeration.** Where a quantity can be shown as a
   proportion of another, show it. The flow beat five cards; the trail beats a
   table; the candidate bars beat a list of four amounts.
2. **A surface is a claim of interactivity.** Cards for things you act on.
   Hairlines for things you read. Nothing else gets a border.
3. **Each lens owns its grammar; the shell owns the frame.** Verified:
   `flow | actions | rows+groups` · `metrics | rows | groups` ·
   `flow | metrics | candidates | decision` · `trail | table`. Four different
   shapes under one header.
4. **Explanation is earned by asking.** Every essay lives behind a disclosure
   that opens closed on every visit.

---

## §30 · The five-second test

Looking at portfolio × control for five seconds:

| Question | Answered by | Verdict |
|---|---|---|
| Where is the money? | the flow's first bar, ₹53,02,701.96 | yes |
| Where did it stop? | the bar collapsing at Verification | yes |
| Why? | "198 settlements have no unique kernel-checked explanation" | yes |
| What can ATTEST prove? | ₹4,99,574.15 continues past Verification | yes |
| What can I do? | three ranked actions, ₹47,96,811 for one step | yes |

Looking at settlement × control for five seconds: where it stopped, what is
agreed (27 orders, ₹97,759.84), what turns on the answer (₹7,292.03), why four
explanations survive, and the decision with its reason.

**The answer is yes. Phase 2 may begin.**

## Measured after this gate

    visible prose        43%  ->  24%    (16% excluding decision-block fields)
    rounded boxes      19/0/5/0  ->  3/0/0/0
    distinct silhouettes    1  ->  4
    generic SaaS words in rendered copy   0
    WCAG AA failures        0
    page overflow           0   360px to 1512px
    tests                  81   six gates holding

## The one thing Phase 2 must fix first

§17. Everything is a vertical column. The subject persists, but the *workspace*
is not spatial — there is no master/detail, no drawer, no split. Build that
before Evidence, or five more lenses will be five more columns.
