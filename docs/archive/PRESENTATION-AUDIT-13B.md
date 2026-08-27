# Phase 13B — Presentation-Grade Audit

Measured on the running product before any change. §20's instruction is the
governing one: *if the audit concludes something is already correct, leave it
alone.* Most of this document is that conclusion.

---

## What the audit measured

| section | question | measured result |
|---|---|---|
| §9 | how many card surfaces? | **24 across 14 screens, 0 of them cards** — every one is a chip or badge under 165×22px. The Phase 13 button reset removed the containers; nothing survived that needs to feel physically separate |
| §3 | does the truth hierarchy survive grayscale? | **yes.** `◇ MODEL / ○ SOLVER / ● ENGINE` are shapes, capability labels are dashed rules, held money is 20px against 10px stage names. Rendered at `grayscale(1)` the landing and Investigate both remain fully legible |
| §12 | do repeated rows share column edges? | **7 of 8 groups aligned and tabular.** One ragged: the blocker labels, 3px |
| §8 | one object owns each room? | **yes**, with one exception — Policy paints its decision word twice |
| §16 | cold start | shell paints at **303ms**; the remaining 2.4s is `/api/run` reconciling 250 settlements, with an honest `reconciling…` rather than a skeleton |
| §13 | motion | rail 0px, room 0px, origin marked — measured in Phase 22, unchanged |
| §11 | absence as result | `UNPRICED`, `ENGINE ABSTAINED`, `NO ENTRY IS WRITTEN`, `LEDGER UNCHANGED`, `NOT VERIFIED` each lead their room at 34px with their own reasoning |
| §17 | the 4-hour operator's eight questions | 8 of 8 answerable; *what happens if I do nothing* is answered by `₹48,03,127.81 held · 198` — the money stays where it is |

---

## §2 — the visual signature already exists

Not something to create. Three devices already recur, and they are the same
idea wearing different clothes:

**The proportional bar.** The state spine's collapse, the search-space
compression, the agreed/disputed split per explanation, and the economic
boundary are all one horizontal track whose fill is the answer.

**The left rule.** Search-space reductions use it to separate convention from
deterministic. The investigation timeline uses it to hold `◇ ○ ●`. The lit spine
stage uses it for "this room is talking about this". Same 2px rule, three
meanings, one grammar.

**The monospace tabular figure.** Every amount, count and identifier, aligned on
the digit.

They are all manifestations of *narrowing*: a wide thing becoming a narrow thing,
with the reason for each cut stated beside it. Nothing needs to be added to make
ATTEST recognisable without its name — the spine plus a compression chain plus
`◇ ○ ●` is already unlike anything else.

---

## The five highest-leverage remaining improvements

### 1 · "WOULD UNBLOCK" wraps, and the blocker labels are 3px ragged

**Current problem.** The label column in the blocker register is 96px. Phase 13
promoted these labels from an undeclared 9px to the scale's 10px, and
`WOULD UNBLOCK` no longer fits — it wraps to two lines on all three rows,
pushing its value down and leaving the label column ragged (`lefts 680/683`,
`rights 776/779`).

**Proposed change.** Widen the column to fit the longest label at the real type
size.

**Why it matters.** This is the first list on the landing screen and the
answer to *what should I do first*. §19's whole claim is that the interface
should feel expensive because it is precise; a wrapped label in the hero list is
the opposite.

**Demo impact: high** — it is on screen at second zero.
**Risk: low** — one column width.

### 2 · Policy states its decision twice at hero weight

**Current problem.** `REVIEW` is painted at 34px as the room's conclusion and
again at 20px 136px below it, under `WHAT POLICY PERMITS`. The same word, twice,
within one viewport. §8: *if there are two competing heroes, remove hierarchy
from one.*

**Proposed change.** The block's unique content is the sentence *"the verdict is
AMBIGUOUS — policy reads it and does not change it"*, which is one of the
product's core claims and appears nowhere else. Lead with that and drop the
repeated decision word.

**Why it matters.** Policy is where the thesis lands — *policy prices risk, it
never overrules the proof.* Saying the decision twice buries the sentence that
actually makes that point.

**Demo impact: medium-high** — Policy is step 5 of the case story.
**Risk: low** — copy and hierarchy, no data change.

### 3 · The spine's interactivity has no resting state

**Current problem.** Phase 22 made every stage a way into the instrument that
owns it. The affordance is `cursor:pointer`, a hover background and a `title` —
all of which require the operator to already be hovering. Nothing at rest says
the model is touchable. §14 asks exactly this question.

**Proposed change.** Use the device the spine already owns. A lit stage carries a
solid left rule; a hoverable stage shows that same rule faintly. The affordance
and the state then share one language: *this row can become the lit one.*

**Why it matters.** It is the difference between an interaction existing and an
interaction being found, and it costs no new element, no icon and no chevron.

**Demo impact: medium** — a judge who discovers it sees the model is navigable.
**Risk: low** — one hover rule, no layout change.

### 4 · Cold start is 2.4s of real reconciliation *(not doing)*

`/api/run` recomputes `execute(n, seed)` on every call. The shell paints at
303ms and shows `reconciling…`, which is true rather than a skeleton.

Memoising by `(n, seed)` would make it instant — the function is deterministic
against a frozen generator. **It is not being done**, because `/api/run` is also
what the Run control invokes, so caching it would make re-running silently
return the previous run and freeze Activity's run id and timestamps. That is a
behaviour change to a real feature in exchange for a number, and §16 says leave
it if it is not safe.

### 5 · Trust and Investigate each carry a supporting figure at display size *(not doing)*

Portfolio Trust paints `24`, `3` and `11` at 34px beneath `NOT VERIFIED`;
Investigate paints `1` at 34px far below the fold. Flagged, then rejected: on
Trust the three read as one group of counts rather than a competing hero, and
they are the most important content in the room. Investigate's sits at y=576,
which does not compete on first glance. Changing either would be a change made
because the phase exists.

---

## Three things deliberately not changed

**The reconciliation engine, kernel, solver, search space and policy.**
Untouched. The six gates are reported at +0.0000 as the evidence.

**The context interaction and the motion system.** Measured at 0px of case
movement with the origin marked. §13 says every animation must answer what
stayed, what moved and what was opened; all three already do. Adding motion here
could only degrade it.

**Room rhythm (§11 of Phase 22).** The 18–43 word paragraph between each
conclusion and its instrument carries the *why*. Deferred a second time on the
same reasoning: removing it to save 60px trades explanation for tempo, and no
measurement in this phase says that trade is right.

---

## The final product composition

The ATTEST moment, and it needs no new page — it is the case story read top to
bottom, each room contributing one object:

```
RAIL          ₹1,00,036.83   AMBIGUOUS   setl_000089
              SOURCE ████  MATCHING ████  VERIFICATION ▮ ← stopped
              AGREED ₹97,759.84    DISPUTED ₹7,292.03

EVIDENCE      2,368 ████████████████  orders in the book
              −2,295  settlement calendar     CONVENTION
                  73  ▍                could belong to this credit
                   4                   surviving explanations

INVESTIGATE   ◇ MODEL    proposed   capture-batch
              ○ SOLVER   tested     NON DISCRIMINATIVE
              ● ENGINE   abstain    ABSTAINED
                                    VERDICT UNCHANGED

POLICY        UNPRICED · REVIEW
              the verdict is AMBIGUOUS — policy reads it and does not change it

JOURNAL       DEBIT ₹0.00  CREDIT ₹0.00  NET ₹0.00
              balanced by absence · LEDGER UNCHANGED

TRUST         LIVE RAZORPAY VALIDATION · NOT VERIFIED
```

Every line already exists. The composition is the product, read in order.

---

## The 60-second journey

```
0:00   ₹53,02,701.96 processed · money stopped at VERIFICATION · ₹48,03,127.81 held
0:05   ₹47,96,811.78 · systemic · 197 settlements · REQUIRES EXTERNAL EVIDENCE
0:12   one click — the six settlements that blocker holds
0:15   one click — a case, with the blocker carried in above it
0:22   EVIDENCE      2,368 → 73 → 4, and the cuts that are conventions
0:32   INVESTIGATE   the model proposed, the solver rejected it, the engine abstained
0:40   POLICY        unpriced, because nothing was proved
0:47   JOURNAL       no entry written, balanced by absence
0:53   TRUST         live Razorpay validation, not verified
0:58   back to the work, blocker intact
```

Nine clicks. Every step is a thing the product offers rather than a thing the
operator has to know.

---

# Implemented

Three changes. Two of the five audited items were deliberately left alone, and
the reasons are recorded above rather than quietly dropped. Six gates at
+0.0000.

## 1 · The blocker register reads as one ledger

`WOULD UNBLOCK` wrapped on all three rows, and the deeper cause was worse than
the wrap: **each blocker is its own grid**, so `minmax(150px, auto)` resolved
column two from that row's own amount. Three rows, three column widths, and the
labels never shared an edge — measured at `lefts 680/683`, `rights 776/779`.

A fixed 160px value column and a 112px label column. Three rows now share exact
edges, which is what makes a list read as a register rather than three
paragraphs that happen to be stacked.

## 2 · Policy states its decision once

`REVIEW` was painted at 34px as the conclusion and again at 20px a hundred
pixels below, under `WHAT POLICY PERMITS`. The block's unique content — *"the
verdict is AMBIGUOUS — policy reads it and does not change it"* — is one of the
product's core claims and appears nowhere else, so it now leads that block under
`POLICY AND THE VERDICT` with the repeated word gone.

## 3 · The spine says it is a way in before you touch it

The interaction shipped in Phase 22 with `cursor:pointer`, a hover tint and a
`title` — all of which require already hovering. A lit stage carries a solid left
rule; a stage that can be opened now carries the same rule at a quarter weight,
darkening on hover. The affordance and the state share one language, and the
spine needs no icon and no chevron to say it is navigable.

## Two contracts re-pointed, and one of them strengthened

Removing the duplicate decision broke two existing contracts. Neither guarantee
was lost.

`test_settlement_policy_states_the_decision_and_the_verdict_apart` read
`.p-head` for both facts. Both are still stated and still apart — the decision
above, the verdict and what policy does with it below — so it reads the room,
and now also asserts the decision is **not** in `.p-head`, pinning the fix.

`test_the_ui_decision_matches_the_engine` read `.p-head-d` and compared it to
`/api/decision`. That is a load-bearing guarantee: the UI represents the engine
and does not re-derive it. It now checks the engine's decision is stated in the
conclusion **and that no other decision word appears anywhere in the room** —
strictly stronger than reading a single element, which could not have caught a
contradicting decision elsewhere on the page.

### A check that was wrong twice before the product was

The strengthened form first failed with *"engine says AUTO-POST but the room
also shows REVIEW"*. The room shows `COST OF A REVIEW` — a label for what a
person's time is worth, not a decision. A substring match read a policy input as
the engine being contradicted. It matches whole lines now.

## Measured after

| | |
|---|---|
| card surfaces | **0** (24 chips, none over 165×22px) |
| ragged repeated-row columns | **0** |
| labels wrapping in the blocker register | **0** |
| decision words at hero weight per room | **1** |
| grayscale legibility | full — shapes and sizes carry the hierarchy |
| stranger test | **7 / 7** |
| horizontal overflow at six widths | none |
| type sizes off the declared scale | none |
| safety gates | **6 / 6, all +0.0000** |
