# ATTEST — three-minute demo

Every screen, number and click below was walked against the running product.
Nothing is staged: no scripted animation, no fake typing, no seeded loading
state. The demo **is** the product, started from `./run-demo`.

Two settlements carry the story:

| | | why it is in the demo |
|---|---|---|
| `setl_000089` | ₹1,00,036.83 · **AMBIGUOUS** | four explanations survive — the restraint case |
| `setl_000109` | ₹6,316.03 · **CONTRADICTED** | nothing reaches the credit — the other failure mode |

Neither is reached by typing an ID.

---

## 0:00 — cold open, nothing clicked

> *"Fifty-three lakh entered this system. Three hundred and fifty-three rupees
> came out the other end."*

```
₹53,02,701.96   PROCESSED        250 settlements · 2,368 orders

SOURCE        ████████████████████   ₹53,02,701.96
MATCHING      ████████████████████
VERIFICATION  ▮                      ₹4,99,574.15
              ₹48,03,127.81 held · 198
POLICY        |                      ₹353.73
ACTION        |
```

Point at the bars, not the numbers. **The collapse is the product.** The money
that continues shrinks at a named stage, and the stage that ate it is the one
carrying ₹48,03,127.81 in the stop colour.

## 0:20 — the work, ranked

> *"It isn't 197 separate problems. It's one missing field, 197 times."*

```
1   ₹47,96,811.78    Systemic · 197 settlements
    BLOCKED AT      verification
    WHY             several disjoint sets of orders satisfy the amount exactly
    WOULD UNBLOCK   Supply an order-level reference on the settlement report
    REQUIRES EXTERNAL EVIDENCE
```

Ranked by **value unlocked, not by amount** — the list says so itself. And note
what the row does not have: a button. ATTEST cannot supply that field, so it
does not offer to.

## 0:45 — one settlement · 2 clicks

Click `000089` in *Needs a person*, then **Open ↗**.

> *"A hundred thousand rupees arrived. Ninety-seven thousand of it is settled no
> matter which explanation is right. Seven thousand turns on which one is."*

```
₹7,292.03   DISPUTED
₹97,759.84  AGREED
```

The rail keeps the case from here on: amount, verdict, where it stopped, what
to do next — through every instrument that follows.

## 1:05 — Evidence · 1 click

> *"Here is the universe the proof was established in."*

```
2,368  ████████████████████  orders in the book
−2,295 settlement calendar (rung 0)   CONVENTION
    −0 already claimed                CONVENTION
    −0 amount ceiling                 DETERMINISTIC
    73 ▍                          could belong to this credit
─────────────────────────────────────────────────────
     4                            surviving explanations,
                                  and arithmetic cannot choose
```

The line to land: **two of those three cuts are conventions, not facts.** A
proof can be arithmetically perfect inside a space that already excluded the
truth, and the room says which cuts could have done that.

## 1:30 — Investigate · 1 click

> *"Now watch what the model is allowed to do."*

```
◇ MODEL    proposed    capture-batch
           three orders captured together on 2026-05-06,
           the densest batch in the window

○ SOLVER   tested      uniqueness      NON DISCRIMINATIVE
           4 of 4 valid explanations contain this anchor;
           it does not distinguish between them

◇ MODEL    exhausted   round 2: no further hypothesis

● ENGINE   abstain     ABSTAINED
```

> *"The model proposed something reasonable. The solver tested it and found it
> present in all four explanations, so it separates nothing. The engine
> abstained — and the verdict is unchanged. The model's output was discarded,
> not averaged in."*

**ENGINE ABSTAINED · VERDICT UNCHANGED**

## 1:55 — Policy · 1 click

> *"This is where most systems would show you a confidence score."*

```
UNPRICED
REVIEW
Nothing was priced. The proof did not establish a unique explanation,
so there is no error probability to multiply.

WHAT HAD TO HOLD                                        0/5 passed
```

Then the contrast — `setl_000020`, the one settlement that posted:

```
AUTO-POST
₹135.49   EXPECTED LOSS · ₹150.00 TO CHECK

automating is cheaper          ●     │      checking is cheaper
```

> *"An inequality, not a score. And when there is nothing to price, there is no
> marker at all — the bar is absent rather than empty."*

## 2:20 — Journal · 1 click

```
No entry is written        ₹1,00,036.83 not posted

DEBIT   ₹0.00
CREDIT  ₹0.00
NET     ₹0.00
Balanced by absence — nothing was written, rather than an entry
that happens to net to zero.
```

> *"Nothing happened, and that is an accounting result."*

## 2:35 — the other failure mode · 2 clicks

Back to the work, then blocker 3 → its single case. No ID typed.

```
₹6,316.03   CONTRADICTED
No combination explains this credit        ₹447.05 unresolved
candidates 11 — none reach this credit
```

> *"Ambiguous means too many answers. Contradicted means none. They are not the
> same failure and ATTEST does not blur them."*

## 2:50 — Trust · 1 click

```
Live Razorpay validation
NOT VERIFIED
11 things not known

NOT VERIFIED   No live traffic has been reconciled
NOT VERIFIED   Bank statement ingestion is synthetic
NOT VERIFIED   The evaluation panel is synthetic
NOT VERIFIED   The narrative docs describe a wider panel than the artifact
...
24 recorded failures · 3 features built, measured, then disabled
```

> *"And this is the screen the system points at itself. Twenty-four recorded
> failures. Three features it built, measured, and switched off. One of these
> boundaries is ATTEST reporting a discrepancy against its own documentation."*

## 3:00 — close

> *"ATTEST doesn't automate certainty. It automates the work that can be proven
> — and it never pretends to know more than the evidence proves."*

---

## Measured click budget

| | clicks |
|---|---|
| understand the money and the collapse | **0** |
| understand the highest-leverage blocker | **0** |
| reach the canonical ambiguous case | **2** |
| each instrument from there | **1** |
| reach the contradicted case, no ID | **2** |
| blocker → Trust | **3** |

Cold start: shell painted at ~250 ms, financial state at ~2.6 s while the engine
reconciles 250 settlements. That wait is real work and is labelled `reconciling…`
— it is not a staged loader.
