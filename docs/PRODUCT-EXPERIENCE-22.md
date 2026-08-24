# Phase 22 — Product Experience

Measured on the running product. No source read to answer §1; every number below
comes from driving the interface.

---

## A. Current journey map (§1)

The fifteen steps, walked from cold open at 1440×900:

| step | clicks | sec | rail amount | verdict | room scroll |
|---|---|---|---|---|---|
| 1. open ATTEST | 0 | 0.0 | ₹53,02,701.96 | — | 594px |
| 2. where money stopped | 0 | 0.0 | ₹53,02,701.96 | — | — |
| 3. highest-value blocker | 0 | 0.0 | ₹53,02,701.96 | — | — |
| 4a. blocker → affected population | 1 | 0.6 | ₹53,02,701.96 | — | 1184px |
| 4b. open the settlement | 2 | 1.2 | ₹13,907.11 | AMBIGUOUS | 0 |
| 5. why ambiguous | 2 | 1.2 | ₹13,907.11 | AMBIGUOUS | 0 |
| 6. Evidence | 3 | 1.8 | ₹13,907.11 | AMBIGUOUS | 398px |
| 7–8. Investigate, AI rejected | 4 | 2.3 | ₹13,907.11 | AMBIGUOUS | 290px |
| 9–10. Policy | 5 | 2.9 | ₹13,907.11 | AMBIGUOUS | 245px |
| 11–12. Journal | 6 | 3.4 | ₹13,907.11 | AMBIGUOUS | 23px |
| 13–14. Trust | 7 | 4.0 | ₹13,907.11 | AMBIGUOUS | 0 |
| 15. back to the work | 8 | 4.5 | **fails** | | |

**8 clicks · 4.5 seconds · 5 lens changes · 2 subject changes · 1 context
change · the case is never visually lost** — the rail carried the amount and the
verdict on every one of the fifteen steps.

> *Could an operator explain this case to another person without opening the
> source code?* **Yes for steps 1–14.** Every screen states its conclusion in
> words, and the numbers needed to retell the case — ₹13,907.11, AMBIGUOUS, four
> explanations, ₹15,750.00 in dispute, UNPRICED, no entry written, NOT VERIFIED —
> are all painted. Step 15 is where it breaks.

### The one failure

**"Back to the work" does not go back to the work.**

```
blocker context was   #/portfolio/control?in=action%3AMULTIPLE_VALID_ASSIGNMENTS
from the case         #/settlement/setl_000004/trust?from=MULTIPLE_VALID_ASSIGNMENTS
back to the work  →   #/portfolio/trust
                      returns to the blocker:  False
                      affected population still listed:  0
```

Two things are dropped. The **blocker context** — so the operator lands on the
portfolio with nothing selected and the affected population gone. And the
**lens** is inherited from wherever the case was left, so a return from Trust
arrives at portfolio Trust, a page with no work on it at all. The button is
labelled with the one thing it does not do.

This is the close of the loop the entire product is built around, and it is the
only measured break in the journey.

---

## B. The seven signature moments (§5)

Audited by opening each room and asking what a judge could point at.

| instrument | the object | state |
|---|---|---|
| **CONTROL** | the ranked blocker register — value, scope, blocked-at, what would unblock, capability | ✅ present. The collapse §5 names lives in the **rail**, which is on all seven screens, so it is not distinctive to Control; the register is |
| **EVIDENCE** | `2,368 → 73 → 4` with the reductions labelled CONVENTION / DETERMINISTIC | ✅ built in Phase 13 |
| **INVESTIGATE** | `◇ MODEL proposed → ○ SOLVER NON DISCRIMINATIVE → ● ENGINE abstain`, ending `Verdict unchanged` | ✅ present |
| **POLICY** | the boundary: marker, threshold, two labelled halves — and **no bar at all** when unpriced | ✅ present |
| **JOURNAL** | `DEBIT ₹0.00 / CREDIT ₹0.00 / NET ₹0.00` under an accounting double rule, captioned *"Balanced by absence"* | ✅ present |
| **ACTIVITY** | the causal chain — each event carrying its own `because` | ✅ at case level; portfolio shows the run's money ladder instead, which is the right answer at that scale |
| **TRUST** | `Live Razorpay validation / NOT VERIFIED`, then eleven boundaries | ✅ present |

Seven of seven already have a moment. **Nothing to build here** — which is the
point of auditing before coding.

---

## C. Portfolio → case → context (§3, §4)

### The context interaction is already what §4 asks for

Measured across five rooms, opening an inspectable row:

```
                rail moved   room moved   row moved   context   origin marked
evidence            0px          0px         0px       open        yes
investigate         0px          0px         0px       open        yes
control             0px          0px        20px       open        yes
activity            0px          0px         0px       open        yes
trust               0px          0px         0px       open        yes
```

The case does not move, the instrument does not change, the originating row
stays marked. Control's row shifts 20px because the blocker register reflows
when the context column takes width — the only movement anywhere, and it is the
room adapting rather than the case.

**No change needed.** This is the strongest interaction in the product and it
already behaves as specified.

### The scale change is already visual

Portfolio and case rails differ in more than text: the case gains a **verdict
chip**, an **id**, a **value date and UTR**, an **explanation count**, and its
spine rows switch from *held* amounts to *stopped here* / *not reached*. A
reader can tell portfolio from case without reading a word.

---

## D. Proof-chain interaction proposal (§10)

Measured: **the spine is five inert `<div>`s.** No `data-lens`, no
`data-context`, no handler. It is the one part of the product that states the
whole model and cannot be touched.

§10 asks for two things, and they are separable.

**D1 — the spine navigates.** Each stage is owned by exactly one instrument, and
that mapping already exists in the product's own vocabulary:

```
SOURCE        →  Evidence      what came in, and from where
MATCHING      →  Evidence      the candidate universe
VERIFICATION  →  Evidence      (proven / contradicted)
              →  Investigate   (ambiguous — the question is what would separate them)
POLICY        →  Policy        what was permitted
ACTION        →  Journal       what entered the books
```

This adds no new state: a stage click is a lens change, already addressable,
already in the URL, already reversible with Back. The verdict decides where
VERIFICATION goes, which makes the routing derived rather than authored.

**D2 — each room illuminates its own segment.** The spine is rendered by the
shell on every lens, so the room can mark which stages it is talking about
without drawing a second spine. Evidence lights MATCHING→VERIFICATION,
Investigate lights VERIFICATION, Policy lights VERIFICATION→POLICY, Journal
lights POLICY→ACTION, Activity and Trust light the whole chain.

Together these make the spine the product's table of contents *and* its
"you are here" — which is what §10 means by *let the spine become interactive
context* rather than duplicating it.

---

## E. The five highest-leverage changes, ranked

| # | change | product impact | risk | demo value |
|---|---|---|---|---|
| **1** | **Return to the work actually returns to the work** — restore the blocker context and land on Control | **high** — it is the only broken step in the fifteen | **low** — one handler, state already in the URL | **high** — closes §6's loop on stage |
| **2** | **The spine navigates and illuminates** (D1 + D2) | **high** — makes the model touchable on all seven screens | **medium** — new interaction on a shared component | **high** — §10 calls it the most distinctive interaction available |
| **3** | **A next instrument, derived from state** (§7) | **medium-high** — turns the loop from something you must know into something the product offers | **low-medium** — must come from verdict/decision, never a script | **very high** — it *is* the case-story path in §6 |
| 4 | Rhythm: the 18–43 word paragraph between every conclusion and its instrument (§11) | medium | medium — the paragraph carries real explanation; moving it risks losing the why | medium |
| 5 | Control's room owning a collapse of its own | low | medium | low |

**Implementing 1, 2 and 3.**

Together they are one idea rather than three: *the case knows where it came
from, where it is, and where it goes next.* One is the way back, two is the map,
three is the way forward.

---

## F. What will explicitly not change

- **The reconciliation engine, the kernel, the search space, the solver
  hierarchy, the policy engine, integer paise.** Untouched, and the six gates
  will be reported at +0.0000 as the evidence rather than the claim.
- **The context interaction.** Measured at 0px of case movement with the origin
  marked. It is already what §4 specifies; touching it can only make it worse.
- **The seven signature moments.** All present. §15 is explicit that the goal is
  not more features, and the audit's most useful finding is that this section
  needed no work.
- **Room rhythm (§11).** Ranked fourth and deferred. The paragraph between the
  conclusion and the instrument does carry the *why*; removing it to save 60px
  trades explanation for tempo, and this phase has no measurement saying that
  trade is right.
- **No new lens, no dashboard, no chat, no settings, no tour, no onboarding, no
  feature called Story.** §6 is explicit that the existing product should tell
  the case, not a new mode.
- **The blocker model (§8).** Already value-first, already ordered by leverage,
  already labelled with what ATTEST cannot do. The ordering is the feature and it
  is intact.
- **"Nothing happened" states (§9).** Audited: `UNPRICED`, `ABSTAINED`,
  `LEDGER UNCHANGED`, `NOT VERIFIED` and `Balanced by absence` all read as
  decisions rather than empty states, each at 34px with its own reasoning. This
  is the thesis and it was built for. Nothing to redesign.

---

# Implemented

Three changes, and they are one idea: **the case knows where it came from,
where it is, and where it goes next.** No new lens, no new screen, no engine
call, no API shape change. The six gates are reported at +0.0000 as evidence
rather than assertion.

## 1 · Returning to the work returns to the work

The button carried one instruction — become the portfolio — and inherited
everything else from wherever the case had been left.

```
was   #/portfolio/trust                     lens inherited, blocker dropped
now   #/portfolio/control?in=action%3AMULTIPLE_VALID_ASSIGNMENTS
```

The fix generalised the click model rather than special-casing the button. An
element carrying `data-subject` may now also carry `data-lens` and
`data-context`, and then it means **all of them at once** — one navigation, one
history entry. Doing it as three separate moves would leave two useless states
in the Back button.

Measured after: 3 blockers on screen, 6 affected cases still listed, the exact
URL the operator left from.

## 2 · The spine became the proof chain (§10)

It was five inert `<div>`s — the one object that states the whole model and
could not be touched. It now works in both directions.

**Into the instruments.** Each stage is owned by exactly one instrument, and a
stage click is a lens change: already addressable, already in the URL, already
reversible with Back.

```
SOURCE, MATCHING  →  Evidence
VERIFICATION      →  Evidence      when a proof exists to read
                  →  Investigate   when several explanations survive
POLICY            →  Policy
ACTION            →  Journal
```

The one branch is real. `VERIFICATION` reads its own painted value — the same
string the rail already shows — so the routing is derived from the case rather
than authored. With four explanations surviving, the question is *what would
separate them*, and that is the question Investigate exists to ask.

**Out to the room.** Each instrument marks the segment it is talking about on
the spine the shell already draws, rather than drawing a second one:

```
Evidence      MATCHING → VERIFICATION
Investigate   VERIFICATION
Policy        VERIFICATION → POLICY
Journal       POLICY → ACTION
```

The mark is a rule down the left edge — the same device the search-space
reductions use for deterministic-versus-convention — not a fill, because a
filled row in a column of five reads as a selected menu item.

## 3 · The next question, derived from the case (§7)

One line at the foot of the room. Not a banner, not a call to action, and the
operator can ignore it — the dock still works.

The loop is the product's structure; the place **state** decides is Evidence:

| on Evidence, the case is | the next question is | because |
|---|---|---|
| AMBIGUOUS | Investigate | several explanations survive; what would separate them |
| PROVEN | Policy | there is nothing to separate |
| CONTRADICTED | Policy | there is no explanation to separate |

The question text is read from the instrument's own record — the same string
the dock shows — so the two cannot drift apart.

**On Trust it is absent.** There is no destination after *what can I believe*,
and inventing one would make the product feel like it is steering.

### The room that had nothing in it

Trust on a settlement rendered two lines and stopped. Its refusal is correct —
one settlement cannot testify to its own engine — but it named a destination
(*"open Trust on the portfolio"*) and gave no way to reach it, so the last beat
of the case story was a near-blank screen ending in an instruction.

The sentence is the affordance now, carrying subject and lens together. It is
marked `.up` in the DOM because it is a different thing from the derived next
instrument: a handoff to another **subject**, not the next question about this
one. Two contracts were scoped to that distinction rather than relaxed.

## The case story, walked using only what the product offers

Not a script — at each step the only thing clicked was the next question the
product itself proposed:

```
0 clicks   CONTROL       One change unlocks 197 settlements · ₹47,96,811.78
2 clicks   CASE          ₹13,907.11 · AMBIGUOUS · setl_000004
3 clicks   EVIDENCE      No unique proof · ₹15,750.00
4 clicks   INVESTIGATE   Engine abstained · Verdict unchanged
5 clicks   POLICY        Unpriced · REVIEW
6 clicks   JOURNAL       No entry is written · ₹13,907.11
7 clicks   ACTIVITY      Ledger unchanged · 10 events
8 clicks   TRUST         (loop ends — no further question offered)
9 clicks   back to the work, blocker context intact
```

**9 clicks, 6.3 seconds**, and it is §6's path exactly. The product tells the
case; nothing was added called Story.

---

## §14 · The stranger test, after

Cold open, zero clicks, five seconds:

| | question | answered by |
|---|---|---|
| 1 | What is ATTEST doing? | `Financial control · all settlements` |
| 2 | How much money is involved? | `₹53,02,701.96 processed` |
| 3 | Where did the money stop? | `VERIFICATION · ₹48,03,127.81 held · 198` |
| 4 | Why? | `several disjoint sets of orders satisfy the amount exactly` |
| 5 | What can the operator do? | `Supply an order-level reference on the settlement report` |
| 6 | What did ATTEST refuse to do? | `REQUIRES EXTERNAL EVIDENCE` |
| 7 | Why didn't the AI decide? | 3 clicks: `Model proposed → Solver tested → Engine abstained · Verdict unchanged` |

**7 / 7.**

### A check that was wrong before the product was

Question 7 first scored ❌, and the product was right. The check hard-coded
`setl_000089`'s solver outcome — `NON DISCRIMINATIVE`, an anchor present in all
four explanations. The case actually reached through the blocker is
`setl_000004`, where the same model hypothesis is rejected as `NO FEASIBLE
SOLUTION`: the anchor appears in **none** of the explanations, so it and the
arithmetic disagree.

Both are real solver verdicts and both answer the question. A test pinned to one
case's vocabulary was measuring the fixture, not the product. It now checks the
structure — the three actors, a rejection of either kind, and the abstention.

---

## Final state

| | |
|---|---|
| tests | **285** |
| browser contracts | **123** |
| safety gates | **6 / 6, all +0.0000** |
| horizontal overflow at 360/393/430/768/1024/1512 | **none** |
| type sizes outside the declared scale | **none** |
| operator journey, 15 steps | 8 clicks · 4.5s · case never lost |
| case story, following only what the product offers | 9 clicks · 6.3s |
| stranger test | **7 / 7** |

Nothing on §18's preserve list was touched, and the engine reports identical
numbers to four decimal places.
