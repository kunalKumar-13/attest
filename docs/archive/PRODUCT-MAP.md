# ATTEST

**A financial reconciliation control system.**

It matches bank credits to the orders that composed them, and it refuses to
invent certainty when the records cannot supply it.

```
₹53,02,701.96   processed          250 settlements, 2,368 orders
₹48,03,127.81   stopped at verification                198 settlements
₹47,96,811.78   blocked by one missing piece of evidence   197 settlements
₹353.73         posted to the ledger                        1 settlement
```

---

## The eight questions, and where each is answered

| | | |
|---|---|---|
| **CASE** | What money are we talking about? | the rail — amount, verdict, identity, agreed against disputed |
| **SPINE** | Where did it stop? | `SOURCE → MATCHING → VERIFICATION → POLICY → ACTION`, drawn as the proportion that survives each stage |
| **EVIDENCE** | Can the explanation be proved? | the search space: 2,368 orders in the book, 73 that could belong to this credit, 4 explanations that survive — and which cuts were conventions rather than facts |
| **INVESTIGATE** | What evidence can distinguish the explanations? | the hypothesis trail: what the model proposed, what the solver did to it, and why nothing separated them |
| **POLICY** | Is automation economically justified? | expected loss against the cost of a human review, as an inequality — never a confidence score |
| **JOURNAL** | What entered the books? | the double entry, or its deliberate absence: `DEBIT ₹0.00 · CREDIT ₹0.00 · LEDGER UNCHANGED` |
| **ACTIVITY** | What actually happened? | the run and its events, each carrying the reason it occurred |
| **TRUST** | What can ATTEST itself prove? | what it has demonstrated, what broke, what was fixed, what produced this result — and the eleven things it does not claim |

---

## The rule

```
MODEL     proposes.
SOLVER    tests.
ENGINE    decides.
POLICY    permits.
LEDGER    records.
```

The model may propose anything. It may not decide anything.

A proposal becomes a proof only by surviving a deterministic solver, and a proof
becomes a posting only when policy can price the remaining risk below the cost
of checking it by hand.

When no unique explanation survives, the engine abstains. Abstention is a
result, not a failure to produce one.

---

## The four verdicts

| | |
|---|---|
| `PROVEN` | exactly one explanation satisfies the amount, and an independent kernel re-derived it |
| `AMBIGUOUS` | several explanations satisfy it exactly, and arithmetic cannot choose between them |
| `CONTRADICTED` | no combination reaches the credit; something is missing from the records |
| `INSUFFICIENT` | the evidence available does not reach a decision |

Only `PROVEN` is eligible to post, and being eligible is not the same as being
permitted — policy decides that separately, and the ledger moves only after both.

---

## What ATTEST does not claim

Its own Trust surface states this before anything else:

```
LIVE RAZORPAY VALIDATION
NOT VERIFIED
```

No live account has been contacted. Every number above describes generated data.
Eleven such boundaries are listed in the product rather than omitted from it,
alongside 24 recorded failures with what broke and what changed.
