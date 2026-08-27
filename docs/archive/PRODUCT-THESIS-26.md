# ATTEST — the thesis

**ATTEST is a financial reconciliation system that uses constrained proof to
determine what can be safely explained, what cannot, and what action is
justified — while refusing to invent certainty.**

One sentence for four readers:

- **A finance operator** — it tells you where your money stopped, which single
  piece of missing evidence is holding the most of it, and what you can safely
  post without a person looking.
- **A technical evaluator** — matching a bank credit to the orders that composed
  it is subset-sum. ATTEST counts solutions instead of scoring them, and reports
  uniqueness rather than confidence.
- **A Razorpay engineer** — money is integer paise from the adapter's parse
  boundary to the ledger. A proof cannot post without a recorded search space
  and cannot cite an order outside it. Both are structural.
- **A non-technical judge** — it is a system that does the reconciliation it can
  prove, and says so plainly when it cannot.

---

## What enters

A settlement report and an order book. In the demo they come from a frozen
generator; in production they would come from the Razorpay adapter, which
declares its amount unit (`Unit.PAISE`), derives each record's identity from
declared fields, and **rejects** a malformed row with its index and reason
rather than guessing at it.

Every amount is parsed exactly or refused. `parse_amount` reads `1050` and
`"1050.00"` as 1050 paise and raises on `10.5` — a reader that rounds is a
reader that changes money.

## What ATTEST computes

For each bank credit, the set of orders whose net — after per-method fees, GST
on those fees, refunds and the T+2 calendar — sums to the credit exactly, within
a tolerance of one paisa per order.

That question has three interesting answers and ATTEST reports which one it got:

| | |
|---|---|
| `PROVEN` | exactly one order set satisfies every constraint |
| `AMBIGUOUS` | several disjoint sets satisfy it equally |
| `CONTRADICTED` | none reaches the credit; a record is missing |

The solver saturates its counter at two, because the question is never *how
many* explanations exist — only whether the explanation is **unique**.

## What the AI does

Proposes. Nothing else.

When several explanations survive, a model suggests an anchor that might
separate them — *"these three orders were captured together on the densest day
in the window"*. That proposal is a **hypothesis**, and it is handed to the
deterministic solver to test.

## What the deterministic systems do

The solver tests the hypothesis against the constraints and returns a verdict on
it: `NON DISCRIMINATIVE` when the anchor appears in every surviving explanation,
`NO FEASIBLE SOLUTION` when it appears in none. Either way it has not
distinguished anything.

The engine then **abstains**, and the settlement's verdict is unchanged. The
model's output is discarded, not overruled and not averaged in.

A separate 28-line kernel, sharing no code with the solver, re-derives every
proof from source records before it can be called PROVEN.

## What comes out

A verdict, the search space it was established in, the reductions that built
that space — each labelled a **convention** or a **deterministic fact** — and,
where the engine stopped, the specific evidence that would resolve it.

## What can be posted

Only what survives both boundaries.

**Proof:** a unique explanation, re-derived by the independent kernel, over a
search space whose integrity is recorded. An absent space fails closed.

**Economics:** expected loss below the cost of a human review, and below the
exposure ceiling. Policy reads the verdict; it never changes it, and it will not
price a settlement the proof did not establish — the honest output there is
`UNPRICED`, not a fabricated probability.

The ledger writes only after both. On the demo portfolio that is **₹353.73 of
₹53,02,701.96** — one settlement of 250.

## What ATTEST refuses to claim

Its own Trust surface states this before anything else:

```
LIVE RAZORPAY VALIDATION
NOT VERIFIED
```

No live account has been contacted. The bank statement is constructed from each
settlement, so every credit matches by construction. The evaluation panel is
synthetic. Eleven such boundaries are listed **in the product**, alongside 24
recorded failures with what broke and what changed, and three features that were
built, measured, and then disabled.

---

## The rule the whole system exists to enforce

```
MODEL     proposes.
SOLVER    tests.
ENGINE    decides.
POLICY    permits.
LEDGER    records.
```

ATTEST does not automate certainty. It automates the work that can be proven,
and it says so when the work cannot.
