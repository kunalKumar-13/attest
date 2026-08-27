# Product workflow audit — Phase 11

Written before any code, per 11T. Everything below was read from the engine and
measured against the running product on 2026-08-24.

---

## 1 · Current workflow

The engine's state vocabulary, verbatim — nothing here is invented and nothing
is missing from it:

```
Verdict     PROVEN · AMBIGUOUS · CONTRADICTED · INSUFFICIENT
Integrity   VALIDATED · HEURISTIC · COMPROMISED
Scope       GLOBAL · LOCAL
Decision    AUTO_POST · REVIEW · BLOCK
Stage       CAPABILITY · EVIDENCE · VERIFICATION · POLICY · ACTION
```

Exception reasons the engine actually emits:

```
MULTIPLE_VALID_ASSIGNMENTS   SEARCH_SPACE_UNCERTAIN   NO_VALID_ASSIGNMENT
UNKNOWN_ADJUSTMENT           NO_FEASIBLE_SOLUTION     PARTIAL_SETTLEMENT
REFUND_MISMATCH              MISSING_TRANSACTION      DUPLICATE_AMOUNT
CHARGEBACK                   DATA_QUALITY             INSUFFICIENT_EVIDENCE
```

The lifecycle in 11A maps cleanly onto this. **No lifecycle state is missing.**

## 2 · Existing capabilities

What the product can genuinely execute today:

| capability | how | real? |
|---|---|---|
| Run the book | `/api/run?n=` — full reconciliation, deterministic from seed | **yes** |
| Re-price the policy boundary | `review` / `exposure` query params, marked `simulated` when off the recorded costing | **yes** |
| Replay for determinism | `/api/replay` → `original`, `replay`, `differing`, `provenance_identical`, `reproduced` | **yes** |
| Ingest events | the real webhook path — 44 deliveries, 11 each accepted / duplicate / replay_mismatch / bad_signature | **yes** |
| Group work by root cause | `/api/actions` — reason, kind, cause, value, leverage, affected, steps, examples | **yes** |
| Rank by value ÷ effort | `leverage_paise` and `steps` already computed | **yes** |

**The blocker model already exists in the data.** `/api/actions` returns every
field 11B asks for. It does not need building — it needs promoting from a
section inside Control to the thing the product opens with.

## 3 · Missing capabilities

Three, stated plainly because 11P forbids pretending otherwise.

**None of the three unlock actions is executable by ATTEST.**

| blocker | value | what would unlock it | can ATTEST do it? |
|---|---|---|---|
| `MULTIPLE_VALID_ASSIGNMENTS` · systemic | ₹47,96,811.78 · 197 settlements | supply an order-level reference on the settlement report | **No — external.** The field does not exist in the source data. This is a change at Razorpay's end, not a button. |
| `SEARCH_SPACE_UNCERTAIN` · free re-run | ₹4,99,574.15 · 52 settlements | widen the window and re-run | **No — and it is subtler than it looks.** See below. |
| `UNKNOWN_ADJUSTMENT` · per item | ₹6,316.03 · 1 settlement | find a fee correction or manual adjustment | **No — a human searches a record.** |

The middle one deserves care, because the UI currently calls it a *free* re-run
and that reads like a button.

The pipeline **already escalates through every rung on every run** —
`for rung in range(len(LAG_LADDER))`, with `LAG_LADDER = (2, 3, 4)`. So
"widen the window" means widening *beyond* the ladder. `LAG_LADDER` is a module
constant in `attest/blocking.py`, which is **protected by the pre-commit hook**,
and `attest/eval/BLOCKING.md` records the study that chose it, concluding:
**"Keep `LAG_LADDER = (2, 3, 4)`. No change."** A parameterised ladder exists
only in the evaluation harness (`StudyIndex`), deliberately outside the product.

So the honest label is not "free re-run". It is: *the engine was deliberately
conservative here, widening is a decision about the engine's defaults, and that
decision has already been argued and rejected.*

Also absent, and already disclosed by Trust: **no operator identity**, so work
cannot be assigned or attributed; and **no persistence** — a blocker's state
does not survive a run, exactly as adapter rejections do not survive a pull.

## 4 · The blocker model

A blocker is the smallest missing fact preventing money from progressing.
Every field below exists today in `/api/actions`:

```
BLOCKED AT      verification              ← spine.stopped_at
WHY             several disjoint sets of orders satisfy the amount exactly
MISSING         an order-level reference on the settlement report
VALUE BLOCKED   ₹47,96,811.78             ← leverage_paise
UNEXPLAINED     ₹34,78,721.17             ← unexplained_paise
AFFECTED        197 settlements
EFFORT          1 step                    ← steps
SCOPE           SYSTEMIC                  ← kind
ACTION          REQUIRES EXTERNAL EVIDENCE  ← NEW, and the honest part
```

The last row is the only new field, and it is a label rather than a capability:
`REQUIRES EXTERNAL EVIDENCE` · `ENGINE DEFAULT, ALREADY ARGUED` ·
`REQUIRES A HUMAN SEARCH`. Nothing is promised that cannot be done.

## 5 · Operational entry experience

The entry point is not a new screen. `portfolio/control` already carries the
financial state and the three blockers; what it lacks is the blocker *shape*
above and the honest action label.

Measured at cold open today, without a single click:

```
value visible          ₹53,02,701.96 total     ✓
value blocked visible  ₹48,03,127.81 held      ✓
top action visible     ₹47,96,811.78 systemic  ✓
```

## 6–9 · The four journeys

**Happy path** — `setl_000020`, ₹353.73. PROVEN → expected loss ₹135.48 against
₹150.00 to check → AUTO-POST → entry written, balanced across four accounts,
₹361.57 each side. Every stage renders today.

**Ambiguous** — `setl_000089`, ₹1,00,036.83. 2,368 orders → 73 candidates → 4
explanations → ₹97,759.84 agreed, ₹7,292.03 disputed across 12 orders → model
proposes a capture-batch anchor → solver returns NON-DISCRIMINATIVE → engine
abstains, `verdict_changed: false` → UNPRICED → REVIEW → no entry. Renders today.

**Contradicted** — `setl_000109`, ₹6,316.03. Real, in the canonical dataset, and
richer than expected:

```
unsat core    no subset of any window satisfies the amount constraint
established   4 orders explain ₹5,868.98 of ₹6,316.03
missing       the closest explanation leaves a residual with no matching record
unexplained   ₹447.05
```

Everything 11I asks for exists. **This case is currently reachable only by
knowing its id** — it is one settlement inside a per-item group.

**Systemic resolution** — this is the journey that cannot complete. It can show
₹47,96,811.78 blocked across 197 settlements by one root cause, one action, one
step. It **cannot** perform the action or show the state changing afterwards,
because the action is a change to Razorpay's settlement report. Per 11J the
boundary is shown rather than faked.

## 10 · What must change in the UI

1. **Blockers get the blocker shape.** Control's action rows become blocker
   objects carrying blocked-at, why, missing evidence, value, affected, effort,
   scope and an honest action label.
2. **Every action gets a capability label.** `REQUIRES EXTERNAL EVIDENCE`,
   `REQUIRES A HUMAN SEARCH`, `ENGINE DEFAULT — ALREADY ARGUED`. No bare verbs.
3. **"Free re-run" is renamed.** It is not free and it is not available; calling
   it free is the one piece of language in the product that promises something
   the engine will not do.
4. **The one executable lever is surfaced.** Re-pricing the review cost is real
   and consequential — ₹150 gives 1 auto-post, ₹500 gives 40 — and it is
   currently three clicks inside Policy. It belongs where the operator decides
   what to work on.
5. **Working a blocker enters its population.** Selecting a blocker scopes the
   case list to its affected settlements, inside the existing rail + room model.
6. **The contradicted case becomes reachable** from its blocker rather than by id.

## 11 · What must not change

The rail, the seven instruments, subject × lens × context, context-origin
motion, URL addressability, 14/14 conclusions, 0% room redundancy, the
deterministic engine and every artefact under it, the Razorpay boundaries, the
251 tests, the 94 contracts, the six gates. No engine change is required by
anything above.

## 12 · Measurements — baseline

All ten product questions from 11Q are answerable from the UI today:

| question | clicks |
|---|---|
| what is ATTEST · where is money stuck · how much is blocked | **0** |
| why is it blocked · smallest thing to resolve · which work first | **0** |
| can it safely post · why trust the result | 1 |
| what the system actually did | 4 |
| what it cannot claim | 6 |

Room redundancy 0%, worst pair 9%, max scroll 1.37 screens, zero overflow at
360–1512. Journal-ambiguous 102% occupancy, Trust 3.97 screens.

**The product does not have an information problem. It has a framing problem**
— and one honesty problem, in the words "free re-run".

## 13 · Implementation plan — DELIVERED

Small, because the audit says most of this already exists.

| # | change | risk |
|---|---|---|
| 1 | Blocker shape in Control, from existing `/api/actions` fields | presentation only |
| 2 | Capability label per blocker, derived from `kind` | presentation only |
| 3 | Rename the re-run blocker and state the boundary | copy, load-bearing |
| 4 | Surface the review-cost lever at the point of decision | reuses the existing param |
| 5 | Selecting a blocker scopes the population; contradicted becomes reachable | uses `examples` + existing context |
| 6 | Contract that no action label promises an unavailable capability | new test |

Steps 1–3 together; 4–6 independently. No engine change, no new endpoint, no
new lens.


---

# Implemented

## The blocker, as an operator reads it

```
1   ₹47,96,811.78     Systemic · 197 settlements

    BLOCKED AT      verification
    WHY             several disjoint sets of orders satisfy the amount exactly
    WOULD UNBLOCK   Supply an order-level reference on the settlement report

    REQUIRES EXTERNAL EVIDENCE
```

Three blockers, three capability labels, none of them executable by ATTEST:
`REQUIRES EXTERNAL EVIDENCE` · `REQUIRES ENGINE CHANGE` · `REQUIRES HUMAN
SEARCH`. **`FREE RE-RUN` is gone**, and a contract fails if it returns.

## Blocker context

`from=<reason>` is a fourth piece of addressable state — not a fourth axis.
Subject, lens and context are what you are looking at; `from` is *why*. It
survives lens changes, context opens, Back and reload, because a pasted link
has to carry the reason as much as the destination.

Measured: blocker → case → evidence is **3 clicks**, and the blocker's value
and root cause stay on screen through all seven instruments.

## The one lever ATTEST holds

Every blocker needs something outside the engine. Re-pricing a review does not:

```
CURRENT     ₹150.00     1 post without a person    ₹353.73        0 wrong
IF IT WERE  ₹250.00    26 would post              ₹1,01,665.87    0 wrong
```

Stated at the point where work is chosen, with the recorded costing named and
untouched. The frontier and the slider stay in Policy.

## The contradicted case

`setl_000109` is reachable in **3 clicks with no id**, through the per-item
blocker's population. Implementing that exposed a real defect: Control reported
**"Every check passed"** over a CONTRADICTED settlement, because its conclusion
read the check list rather than the verdict — and a settlement can pass every
check it was given while having no explanation at all. It now reads:

```
No combination explains this credit
₹447.05  UNRESOLVED
no subset of any window satisfies the amount constraint.
4 orders explain 586898 paise of 631603 — the closest explanation leaves a
residual with no matching record
```

## Measurements — after

All ten product questions answerable; **eight at cold open** (was six).

| | before | after |
|---|---|---|
| can it safely post | 1 click | **0** |
| blocker → case → evidence | not possible | **3 clicks** |
| contradicted case | id only | **3 clicks** |
| room redundancy | 0% | **0%** (worst pair 9%) |
| overflow 360–1512 | 0 | **0** |
| tests / contracts / gates | 251 / 94 / 6 | **259 / 102 / 6** |

Eight contracts added, all behavioural: capability labels, the absent
`FREE RE-RUN`, blocker scoping, blocker retention across seven instruments and
a reload, contradicted discovery, contradicted not reported as passing, the
lever not editing recorded policy, and the blocker's value staying visible.

## What is still not possible, and stays that way

The systemic blocker cannot be resolved inside ATTEST. ₹47,96,811.78 across 197
settlements waits on a field that does not exist in the settlement report. The
product says so and offers no button, because the honest end state is
**waiting for external evidence**, not a fake success.
