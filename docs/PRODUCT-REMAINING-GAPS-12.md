# Phase 12 — Remaining Product Gaps

> *"What still prevents this from feeling like a real product?"*

Answered from the measured stranger test in `PRODUCT-STRANGER-TEST-12.md`, not
from reading the source. Categories are the ones the phase named. **Two gaps
found. Neither is a missing feature.**

---

## G-1 · Language — raw paise reaches the operator (category A/C)

The engine narrates in the unit it computes in, at six sites.

What an operator sees on `setl_000109`, the contradicted case, directly beneath
the headline:

```
No combination explains this credit          ₹447.05 unresolved
no subset of any window satisfies the amount constraint.
4 orders explain 586898 paise of 631603
```

The room formats the residual correctly (`₹447.05`) and then, one line later,
asks the reader to divide two six-digit integers by a hundred to recover ₹5,868.98
and ₹6,316.03 — numbers it is already displaying elsewhere on the same screen.

This is not a style preference. Two modules already state the rule:

- `exceptions.py` docstring: *"Six orders explain all but ₹680.74; look for a
  refund in that amount on or before the value date" is a work item.*
- `policy._rs()` docstring: *"the reasons are read by a person deciding whether
  to trust a posting; '11613 paise' makes them do the arithmetic, and money that
  has to be converted before it can be judged is money that will be misjudged."*

So this is drift from a decided contract, and the formatter to fix it already
exists.

**Sites (6):** `exceptions.py` — orders-totalling, explanations-differ-over,
partial-explains, pool-reaches-only; `graph.py:141`; `searchspace.py:150`.

**Explicitly not a defect:** `±31 paise` tolerance. A tolerance of ±31 paise is
sub-rupee, and ₹0.31 would be the less honest rendering. Kept.

**Fix:** route those six through the existing `_rs()`. No new abstraction.

---

## G-2 · Hierarchy and trust — Activity leads with a count that overstates (category C/G)

Portfolio Activity's headline:

```
Nothing is unrevised
60
events delivered
```

Two distinct problems in one figure.

**It is the only room of seven that does not lead with a conclusion.** Measured
first-glance figures: Control `₹47,96,811.78`, Evidence `₹53,02,701.96`, Policy
`₹53,02,348.23`, Journal `₹353.73`, Trust `NOT VERIFIED` — every one an answer.
Activity's is `60`, an inventory count, which is precisely the failure the phase
named ("24 events" without the conclusion). The conclusion *is* present at
`Nothing is unrevised`, but it is set smaller than the number beneath it.

**And 60 is not what happened.** The same payload records:

```
accepted 17    duplicate 17    replay_mismatch 17    bad_signature 17
```

43 of those 60 events were **refused** — as duplicates, as replays, as bad
signatures. Calling all sixty "delivered" describes attempts as though they were
acceptances. In a room whose entire subject is *what actually happened*, and in
a product whose thesis is that refusing is a first-class result, this is the one
place where a rejection is quietly counted as a success.

Fixing the number fixes the hierarchy: `17 of 60` `events accepted` is both a
conclusion and the truth, and it makes the webhook fail-closed behaviour —
already built, already tested — visible where it belongs.

**Fix:** change the figure and its label. Two lines in `lens-activity.js`.

---

## Categories with nothing to report

| | |
|---|---|
| **B · Interaction** | Blocker → population → case → all seven instruments measured at 0/1/2/+1 clicks, 1.3 s. Context survives lens changes, Back and reload via `from=`. Nothing to fix. |
| **D · Operational workflow** | The full loop — where is the money → what blocks it → why → can it be proven → what would resolve it → can we act → what happened → can I trust it — is walkable across existing instruments with no new screen. Mapped in Part 14. |
| **E · Missing capability** | The one true missing capability is stated *in the product*: ₹47,96,811.78 across 197 settlements waits on a field the settlement report does not contain. ATTEST says so and offers no button. That is the correct end state, not a gap. |
| **F · Data realism** | Synthetic, and the product says so five ways in Trust, including reporting a discrepancy against its own documentation. Honest rather than realistic is the right trade here. |
| **G · Trust** | `NOT VERIFIED` is the first thing in Trust; 11 boundaries, 24 recorded failures, 3 disabled features are all stated. Only G-2 touches this category. |
| **H · Performance** | 3.55 s cold start to interactive; every lens switch under 0.7 s. |
| **I · Onboarding** | No tour needed — 7/7 stranger questions answered with zero clicks. An onboarding overlay would be a step backwards. |
| **J · Demoability** | The three-blocker cold open *is* the demo. `RAZORPAY-DEMO.md` and the golden dataset are frozen. |

---

## What is deliberately not being fixed

Recorded so a later reader does not mistake these for oversights.

**Developer terms in Trust** (`/api/replay`, `benchmark/results.json`,
`docs/EVALUATION.md`). Trust's subject is provenance. Naming the file that
produced a number is what an audit console owes its reader; replacing those with
friendly prose would make the room less trustworthy, not more.

**"Leverage."** Flagged by the SaaS-filler pattern, kept. It is used in its
financial sense — value unlocked per unit of work — and the product explains the
ranking it drives in the next line.

**No eighth lens, no dashboard, no chatbot, no onboarding.** The stranger test
gave no evidence that any of these is needed, and Part 15 says not to manufacture
problems.

---

## Conclusion

All eight success sentences from the phase brief are **true** against measured
behaviour. The architecture, the information model, the interaction model and the
click economy all pass.

What remains is two places where the product speaks less honestly than it
behaves: it makes a person do arithmetic it has already done (G-1), and it counts
43 refusals as deliveries (G-2). Both are small, both are text, and both are
fixed by making the product say what it already knows.

After those, the product is ready for final visual polish and demo preparation.

---

## Implemented

Both gaps were fixed as text and formatting. No engine change, no new endpoint,
no new lens, no new screen. The six safety gates moved **+0.0000** on every
metric, which is the evidence that nothing about the engine's behaviour changed.

### G-1 — closed

`rupees()` moved out of `policy._rs` into a new leaf module `attest/money.py`,
the mirror of `adapters/money.py`: one reads an amount *in* from a source and may
refuse, the other writes one *out* to a person and never fails. It imports
nothing, so `policy`, `exceptions`, `searchspace` and `graph` can all reach it
without gaining a dependency on each other. `policy._rs` remains as a local
alias; its callers are untouched.

It is **not** in `model.py`, which was the first choice and is where the
integer arithmetic lives. The pre-commit guard refused the commit:

```
✖ BLOCKED — protected files in this commit:  attest/model.py
```

`model` is solver core, frozen by the boundary freeze, and the escape hatch
(`ATTEST_CORE=1`) exists for a human edit defended in review — not for
relocating a formatter. The guard was right and the module moved instead.

Seven call sites now route through it — `exceptions.py` ×4, `graph.py` ×2,
`searchspace.py` ×1. **Grep found six. The seventh was found by the contract**:

```
setl_000089: 13 further orders totalling 3154675 paise
```

— the collapsed-remainder edge in the evidence graph, which no search for
`"paise of"` would ever have matched.

Before and after, on the case Phase 12 asks a stranger to read:

```
-  4 orders explain 586898 paise of 631603
+  4 orders explain ₹5,868.98 of ₹6,316.03

-  net exceeds the credit of 11613 paise
+  net exceeds the credit of ₹116.13

-  net 440325 paise, captured 2026-05-06
+  net ₹4,403.25, captured 2026-05-06
```

The `±31 paise` tolerance is unchanged, and a contract now pins it that way so a
later sweep does not "fix" it into ₹0.31.

Five contracts in `tests/test_operator_units.py`, all confirmed red first.

### G-2 — closed, and the first fix was wrong

The obvious repair was `17 of 60` / `events accepted`. It was implemented, went
green, and was then discarded — on a freshly started server it renders **`0 of
0`**, because webhook deliveries accumulate at runtime and a cold run has none.
A headline figure that degenerates to zero is not a conclusion either.

Two things were true at once and only one belongs in the headline. The room's
question is *what happened* — whether the history is complete and the verdicts
still stand. So the figure now answers the fact directly above it:

```
-  Nothing is unrevised          -  60      -  EVENTS DELIVERED
+  Nothing is unrevised          +  250 of 250  +  VERDICTS CURRENT
```

The accept/refuse breakdown was **already** rendered in the room body — the
`Deliveries since` section lists every delivery with its status and asides the
counts per kind. It was never missing; it was being contradicted by the headline
above it. Removing the false headline leaves the honest record in place.

Two contracts. `test_no_room_leads_with_a_bare_entity_count` now covers all
seven rooms, not just the one that failed. `test_activity_does_not_count_refused
_events_as_delivered` seeds deliveries first (a fresh run has none, so the
assertion would otherwise be vacuous) and then pins the UI to the actual
`delivery_counts` payload — every non-zero outcome named in the room, and no
refusal folded into the headline. Both were mutation-tested: reverting the
figure to `deliveries.length` fails both.

### Measured after

| | before | after |
|---|---|---|
| paise leaking into operator text, 21 screens | 7 sites | **0** |
| rooms leading with a conclusion | 6 / 7 | **7 / 7** |
| tests | 259 | **266** |
| browser contracts | 102 | **104** |
| safety gates | 6 / 6 | **6 / 6, all +0.0000** |
| horizontal overflow at 360/393/430/768/1024/1512 | none | **none** |

The product is ready for final visual polish and demo preparation.

### Two contracts that had to be rewritten before they were worth keeping

Recorded because both were green while being wrong, and both would have
misled a later reader.

**`17 of 60` was hard-coded.** It passed, then failed in the full suite reporting
`19 of 60` — the delivery log accumulates across tests. A contract pinned to a
value that depends on execution order tests the order, not the product. Rewritten
to derive from the payload.

**"the refused count is absent from the headline" collided by coincidence.** The
figure reads `250 of 250`; once enough events had been delivered the refused
total also reached 250, and the assertion tripped on a substring match with no
defect behind it. A proxy that fails on a coincidence will one day pass on a real
defect. Replaced with an exact derivation — the figure must equal
`{total - unrevised} of {total}`, computed from the same payload the room renders.

Both final forms were mutation-tested: reverting the figure to `deliveries.length`
fails them.
