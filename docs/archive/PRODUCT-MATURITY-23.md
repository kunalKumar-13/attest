# Phase 23 — Product Maturity Review

Evaluated against the running product. §20 forbids new synthetic UI metrics
unless they represent real behaviour, so this phase measured **task completion,
click path, back-expectation, semantic classification and typographic role** —
and nothing that produces a number without a person behind it.

---

## A. Product maturity scorecard

| dimension | score | the evidence |
|---|---|---|
| financial hierarchy | **9** | every ₹ category has one type size: ENTERED 34px, HELD 20px, VALUE BLOCKED 20px, AGREED/DISPUTED 15px, CONTINUES 13px. Median painted ₹ is 15px against 10px for everything else |
| proof communication | **9** | `2,368 → 73 → 4` in one object, each cut labelled CONVENTION or DETERMINISTIC, with the claim that the space is an assumption stated under it |
| AI / deterministic separation | **9** | `◇ MODEL → ○ SOLVER → ● ENGINE` on a connected spine, ending `ABSTAINED / Verdict unchanged`. Shapes, so it survives grayscale. **−1: the conclusion is painted twice** |
| policy communication | **9** | expected loss against review cost as a marker on a threshold, and **no bar at all** when unpriced |
| accounting communication | **9** | `DEBIT ₹0.00 / CREDIT ₹0.00 / NET ₹0.00` under a double rule, captioned *balanced by absence* |
| trust communication | **8** | `NOT VERIFIED` leads, eleven boundaries stated, file paths named as evidence. Case-level Trust is deliberately thin — correct, but it is the least instrument-like room |
| case continuity | **10** | 15-step journey with the case never visually lost; Back correct at 5 of 5 steps; the blocker survives seven instruments and a return |
| instrument distinction | **9** | measured structurally: Evidence is bars and reductions, Investigate is a sequential timeline with actor marks. They are not two versions of one page |
| visual identity | **9** | three devices recur — the proportional bar, the 2px left rule, the monospace tabular figure — and the whole hierarchy survives `grayscale(1)` |
| demo memorability | **8** | each of the five screens is strong alone; the chain between them is carried by the next-question line and the lit spine, which reward walking it rather than seeing it |

**Mean 8.9.** The two points are in the same place: the thesis is unforgettable
*per screen* and merely clear *across screens*.

---

## What the audit measured, and found already correct

**§4 · Density.** Every painted element classified across 14 rooms. Text-bearing
elements dominate; bars and rules are data. **Unclassified: 0 in 13 of 14
rooms**, and the 11 in portfolio Control are 6×6px verdict dots, which are
semantic marks. Decoration is effectively zero.

**§5 · Implementation leaks.** Scanned for internal identifiers, technical
labels, API wording and file paths. Everything found passes §5's own test —
`policy_661e43db9242` in *which policy decided this*, `attest/adapters/
razorpay.py` in Trust's not-verified claim, `n=250, seed=20260821` in the run
record, `D1`/`D10` indexing recorded failures. Each answers *why should I
believe this*, which §5 explicitly permits. `(rung 0)` beside a settlement
calendar reduction is the weakest case — the justification already says "the T+2
capture window" — but the rung is real when several appear at once. Left.

**§17 · Back.** Walked blocker → case → next question → spine stage → inspect,
then pressed Back five times. **Correct at every step.** No navigation produced
*I thought I'd go there*.

**§10 · Context.** Rail 0px, room 0px, origin marked — measured in Phase 22 and
unchanged.

**§11 · Absence as result.** `UNPRICED`, `ENGINE ABSTAINED`, `NO ENTRY IS
WRITTEN`, `LEDGER UNCHANGED`, `NOT VERIFIED`, `NO UNIQUE PROOF` each lead their
room at display size with their own reasoning. None reads as an empty state.

**§13 · Evidence vs Investigate.** Confirmed distinct: Evidence is structural
(bars, reductions, a compression that ends in a count), Investigate is causal
(a vertical spine of actor marks, each step a proposal and its rejection).

---

## B. The top five remaining changes

### 1 · Investigate states its conclusion twice

**Problem.** `Engine abstained` is painted at 20px as the room's conclusion and
again at 20px in the summary block below — same phrase, same size, same room.
This is exactly the defect fixed in Policy last phase, in the room next door.

**Evidence.** Measured: `'engine abstained' → ['20px/c-concl-f', '20px/i-abs-v']`.
It is the only duplicated phrase at emphasis anywhere in the product; the other
three candidates are legitimate (₹0.00 three times *is* the balanced-by-absence
point; ₹1,00,036.83 as both credit received and amount reconciled are two facts
that happen to be equal).

**Change.** The summary block's unique content is the count — *1 hypothesis
tested, 0 discriminative* — and what it means for the verdict. Lead with that
and drop the repeated headline.

**Risk: low.** Copy and hierarchy. **Benefit:** the room stops competing with
itself on the screen that carries the AI-separation thesis.

### 2 · Held money is the only ₹ category that is not tabular

**Problem.** Every financial category declares `tabular-nums` except `HELD` —
which carries ₹48,03,127.81, the answer to *where did my money stop*.

**Evidence.** Measured across 3 subjects × 7 lenses: ENTERED, CONTINUES, AGREED,
DISPUTED, VALUE BLOCKED and the run ladder are all `tabular-nums`; `.c-flow-h`
reports `font-variant-numeric: normal`.

**Change.** One declaration. **Risk: none** — the face is already monospace, so
nothing moves; this makes the declared role match the other eight categories.

**Benefit:** §7's actual ask is semantic consistency, and this is the single
inconsistency in it.

### 3 · The thesis is per-screen, not across-screen *(not doing — see §3 below)*

### 4 · Case-level Trust is six elements *(not doing)*

It renders a conclusion and a way through, which is correct — one settlement
cannot testify to its own engine. Making it look like more of an instrument
would mean inventing content, and Policy already carries this case's
provenance. Adding it here would be the duplication this phase is auditing for.

### 5 · The landing paints ₹47,96,811.78 twice *(not doing)*

At 34px as the room's conclusion and 20px as the top blocker's value. They are
the same fact by design — the headline *is* the top blocker — and the ranked
register needs its own value or the ordering stops being legible. Flagged,
inspected, kept.

---

## §3 · Is the product moment visually obvious?

**Verdict: A, within a screen. B, across screens.**

```
EVIDENCE      2,368 → 73 → 4 → NO UNIQUE PROOF        obvious
INVESTIGATE   ◇ MODEL → ○ SOLVER → ● ENGINE ABSTAIN   obvious
POLICY        UNPRICED · REVIEW                        obvious
JOURNAL       LEDGER UNCHANGED                         obvious
```

Each is unmistakable in three seconds. The **sequence** between them is carried
by two devices that already exist: the next-question line at the foot of each
room, and the spine lighting the segment each instrument is talking about. Both
reward walking the product.

§3 says to redesign the presentation of this sequence if it is B. **I am not
doing that**, and the reason is §18's own framing: the five screenshots must
tell the story *even if someone never runs the product*, and they do — because
each carries its own complete idea. A composite that shows all four at once
would be the new screen §3 forbids, and every lesser version of it is a
progress indicator, which is a workflow being forced. The chain is already
stated in the one place it belongs: the spine, on every screen.

---

## C. Five things that are excellent and must not be touched

1. **The case rail's persistence.** The case survived all 15 steps of the
   operator journey without once being lost. This is the product's strongest
   interaction and every change to it can only cost something.
2. **The context interaction.** 0px of case movement, origin marked, measured
   across five rooms. It is already the magnifying glass §10 describes.
3. **The search-space compression.** `2,368 → 73 → 4` with each cut labelled
   convention or deterministic, and the assumption stated beneath. This is the
   product's signature and it is finished.
4. **`◇ MODEL / ○ SOLVER / ● ENGINE`.** Shapes, not colours — the AI separation
   survives grayscale, which is the strongest form the argument can take.
5. **Absence as a result.** Six states that each read as a decision at display
   size. This is the thesis and the visual language was built for it.

---

## D. The 60-second journey

```
0:00  ₹53,02,701.96 processed · stopped at VERIFICATION · ₹48,03,127.81 held
0:06  ₹47,96,811.78 · SYSTEMIC · 197 settlements · REQUIRES EXTERNAL EVIDENCE
0:14  one click  — the settlements that blocker holds
0:18  one click  — a case, the blocker carried in above it
0:26  EVIDENCE      2,368 → 73 → 4, and which cuts are only conventions
0:36  INVESTIGATE   the model proposed, the solver rejected it, the engine abstained
0:44  POLICY        UNPRICED — nothing was proved, so nothing was priced
0:51  JOURNAL       no entry written · balanced by absence
0:56  TRUST         live Razorpay validation · NOT VERIFIED
1:00  back to the work, blocker intact
```

## E. The five screenshots

| | screen | the distinct idea it carries |
|---|---|---|
| 1 | **Landing** | money stopped somewhere specific, and the work is ranked by what it unlocks |
| 2 | **Evidence** · setl_000089 | the proof happened inside a universe that was narrowed by conventions |
| 3 | **Investigate** · setl_000089 | the AI proposed, the solver rejected it, the engine refused to guess |
| 4 | **Policy** · setl_000020 | automation is an economic argument, not a confidence score |
| 5 | **Trust** · portfolio | the system names what it has not verified |

Each carries an idea none of the others do. Nothing to replace.

---

## The decision

**Two changes, both small, both semantic.** Everything else this phase examined
came back correct, and §21 is explicit that saying so is the right answer when
it is true. The product does not need to be bigger.

---

# Implemented

Two changes. Both semantic, both small, and both found by measurement rather
than by looking for work.

## 1 · Investigate stopped competing with itself

`Engine abstained` was painted at 20px as the room's conclusion and again at
20px in the summary block below it — the same phrase, the same size, the same
room. This is the defect fixed in Policy last phase, standing untouched in the
room next door, because that contract was scoped to Policy.

The summary block's own content is the count and what it means: *1 hypothesis
tested, 0 discriminative → the verdict stands at AMBIGUOUS and no financial
action was taken.* That is what it says now. The rule that styled the removed
line went with it — a CSS rule with no element is a guess about the future.

One existing contract broke and its guarantee did not move.
`test_abstention_is_shown_as_restraint_and_changes_no_verdict` read `.i-abs`
for the word *abstained* — the very line that was the duplicate. Abstention is
still stated, at the head of the room, so the contract reads the room for that
and `.i-abs` for what the block actually owns: that nothing moved as a result.

**The new contract is general this time.** It checks every room on four subjects
for its own conclusion painted twice at emphasis, so the next room to acquire
this cannot do so quietly. It deliberately does **not** cover repeated figures:
`₹0.00` three times in Journal *is* the balanced-by-absence point, and a bank
credit that equals the amount reconciled is two facts that happen to agree.

## 2 · Held money declares tabular figures

Nine financial roles, eight of them declaring `tabular-nums` so digits hold
their column. The ninth was `HELD` — which carries ₹48,03,127.81, the answer to
*where did my money stop*.

The face was already monospace, so nothing moved on screen; what changed is that
the declared role now matches the other eight. A contract asserts every money
role in the rail declares it.

## What was examined and left alone

Recorded so a later reader does not mistake these for things nobody looked at.

- **`(rung 0)` beside a settlement-calendar reduction.** The weakest case for
  technical detail in the product — the justification beside it already says
  "the T+2 capture window". Kept because the rung is genuinely distinguishing
  when rungs 0, 1 and 2 all appear in one reduction list.
- **`₹47,96,811.78` painted twice on the landing**, at 34px as the conclusion
  and 20px as the top blocker's value. The same fact by design: the headline
  *is* the top blocker, and the ranked register needs its own value or the
  ordering stops being readable.
- **Case-level Trust's six elements.** Correct as a refusal. Giving it more
  would mean duplicating the provenance Policy already carries for that case.
- **The thesis being per-screen rather than across-screen.** §3 offers a
  redesign of the sequence; the five screenshots each carry a complete idea, and
  any composite of all four is either the new screen §3 forbids or a progress
  indicator, which is a workflow being forced.

## Final measured state

| | |
|---|---|
| tests | **290** |
| browser contracts | **128** |
| safety gates | **6 / 6, all +0.0000** |
| operator journey, 15 steps | 8 clicks · 4.5s · case never lost |
| Back correctness | **5 of 5** |
| unclassified elements (decoration) | **0** in 13 of 14 rooms |
| money roles with a consistent type size | **9 of 9** |
| conclusions painted twice at emphasis | **0** |
| stranger test | **7 / 7** |
| horizontal overflow at six widths | none |
| type sizes off the declared scale | none |
