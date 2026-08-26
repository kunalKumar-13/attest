# ATTEST — the fifteen questions

Every number here is read from an artifact in this repository. Where something
is not verified, it says so.

---

## 1 · Why does this problem matter?

A merchant's bank statement shows one credit. It is the net of some subset of
the orders they captured — after per-method fees, GST on those fees, refunds,
and a T+2 settlement calendar. Deciding *which* orders is subset-sum, and it is
done by hand, in Excel, daily, at effectively every merchant in India.

Getting it wrong is not a reporting error. Candidate order sets discharge
receivables against **different customers**, so posting the wrong explanation
moves money against the wrong account and the books balance while being false.

## 2 · Why is AI dangerous here?

Because the failure is silent and confident. A language model asked *which
orders make up this credit* will answer. It will produce a plausible subset, and
the subset will balance, because balancing is easy — 73 candidate orders admit
many subsets that sum correctly.

Measured on this repository's benchmark, a greedy matcher decides **462 of 500**
settlements and is **wrong on 439** of them — a 95% false-proof rate. It is not
that the heuristic is bad. It is that *deciding more* and *being right* are
different objectives, and only one of them is easy to optimise.

## 3 · Why isn't an ordinary reconciliation engine enough?

Because the safe version is nearly useless. An exact-only matcher — accept a
settlement only when a single order matches the credit exactly — has a **0%**
false-proof rate and decides **22 of 500**. It declines 478.

```
                decided   wrong    false-proof rate
exact_only         22       0            0.0%
ATTEST             84       4            4.8%
greedy            462     439           95.0%
```

*(`benchmark/baselines.json`, 500 settlements, held-out seeds.)*

**ATTEST does not claim the best precision. `exact_only` beats it.** The claim
is different: **84 decided against `exact_only`'s 22**, at a false-proof rate
one twentieth of `greedy`'s — and, the part neither baseline has, it says which
of its answers it could not establish.

## 4 · Why does AI belong in the system at all?

Because when several explanations survive, the question stops being arithmetic
and becomes *what else do we know*. Orders captured in one batch, a shared
customer, a settlement window — those are hypotheses, and generating them is
what a model is good at.

The model proposes an **anchor**: *"these three orders were captured together on
2026-05-06, the densest batch in the window."* That is a real observation and it
is worth testing.

## 5 · What exactly is deterministic?

Everything that can change a financial outcome.

- The **search space** — which orders were even considered, and which reductions
  built that set, each labelled a convention or a deterministic fact.
- The **solver** — a counting DP over the amount axis that saturates at two,
  because the question is never how many explanations exist, only whether the
  explanation is unique.
- The **kernel** — 28 lines, sharing no code with the solver, re-deriving every
  proof from source records before it may be called PROVEN.
- The **policy** — an inequality over expected loss and the cost of a review.
- The **ledger** — a balanced double entry, or none.

Integer paise throughout. Zero `float()` and zero `round()` on any amount path;
`Decimal` appears only at the adapter's parse boundary.

## 6 · What happens when evidence is ambiguous?

```
₹1,00,036.83     4 explanations satisfy the amount exactly
₹97,759.84       agreed by every one of them
₹7,292.03        turns on which one is right, across 12 orders
```

The engine reports `AMBIGUOUS`, names what is settled regardless, and states the
evidence that would resolve it — an order-level reference on the settlement
report. It does not pick one.

## 7 · What happens when evidence contradicts?

```
₹6,316.03        CONTRADICTED
₹447.05          unresolved — no subset of any window reaches this credit
```

A different failure entirely: not too many answers, but none. ATTEST reports the
closest partial explanation and the exact residual, because *"look for a fee
correction of ₹447.05 around this value date"* is a work item and
`CONTRADICTED` alone is not.

## 8 · Why can the model not silently influence posting?

Structurally, in three places.

**It never returns a verdict.** The model returns an anchor. The solver tests
it and reports `NON DISCRIMINATIVE` — present in all four explanations — or
`NO FEASIBLE SOLUTION` — present in none. Either way it separated nothing, and
the engine's verdict is unchanged. The product says `ENGINE ABSTAINED · VERDICT
UNCHANGED` and calls the model's output *discarded*.

**Postability is a property of the finding, not a decision made elsewhere.**
`Finding.postable` requires a PROVEN verdict, kernel re-derivation, and a
recorded search space whose integrity is known. An absent space fails closed.

**Membership is checked.** A proof's order ids must be a subset of the search
space's recorded members. A proof cannot cite an order the search never saw.

No module below the API imports the model layer, and the ledger imports no
agent, model or hypothesis module at all.

## 9 · What did we test adversarially?

**34 attacks from source to ledger**, run in CI and re-run in a clean room:
inflated settlement totals, identity collisions, fabricated proofs, proofs
citing orders outside their space, tampered webhook replays, malformed amounts,
`float("nan")` and `float("inf")` as money.

**34 defended, 0 breached, 0 harness errors.** Every stage carries a control
attack that *should* succeed, because a harness that refuses everything defends
nothing.

## 10 · What did we discover that was wrong?

`FAILURES.md` records **24**, each with what was expected, what happened, and
what changed. Three features were built, measured, and then **disabled** because
the measurement did not support them (D4, D8, D12).

Two are worth naming:

**CORE-001** — `postable` returned `True` when the search space was absent. A
PROVEN finding assembled outside the pipeline was postable *precisely because*
it omitted the evidence it would have been judged on. It fails closed now.

**CORE-002** — the refusal reason said *"the search space is compromised"* for
all six conditions `postable` guards, including the five where the space was
fine. A refusal that names the wrong cause sends an operator to inspect the
wrong thing.

The adversarial harness itself was found scoring its own `AttributeError`s as
successful defences — 4 of 29 results. Fixed before the number was reported.

## 11 · What is genuinely connected to Razorpay?

`docs/RAZORPAY-INTEGRATION.md` carries a row per capability with the test that
exercises it. Summarised honestly:

| | |
|---|---|
| **IMPLEMENTED** | settlement and payment ingestion, webhook ingestion, HMAC-SHA256 signature verification (**fails closed** — an absent secret refuses ingestion), idempotency on both the webhook and the pull, duplicate and replay-mismatch detection, explicit malformed-record rejection, integer-paise conversion with the unit **declared**, credentials from the environment and never logged |
| **PARTIAL** | refunds reduce a settlement but are not evidence; fees are read but not retained per order; pagination's loop is written but **never run against a real response**; error handling has no retry or backoff |
| **SIMULATED** | the bank statement — `BankCredit` is constructed from each settlement, so every credit matches by construction |
| **NOT IMPLEMENTED** | incremental sync — no cursor, no watermark |

The adapter is **read-only by construction**: `writes: []`, GET endpoints only,
no code path in it mutates anything.

## 12 · What remains unverified?

**No live Razorpay account has ever been contacted.** `fetch` performs a real
authenticated request and has never been called with real credentials. Every
number in the product describes generated data — seed 20260821, 250 settlements,
2,368 orders — and the interface says `GENERATED` on every screen, read from the
adapter rather than asserted.

The product's own Trust lens leads with `LIVE RAZORPAY VALIDATION · NOT
VERIFIED` and lists **eleven** such boundaries, one of which is ATTEST reporting
a discrepancy against its own documentation.

## 13 · Why is this useful to a real finance team?

It answers *what should I do first* with money rather than counts. The work is
ranked by **what each item unlocks**: 197 ambiguous settlements are one action,
not 197, because they are ambiguous for the same missing field — ₹47,96,811.78
behind a single order-level reference.

And it says what it cannot do. Three blockers, three capability labels:
`REQUIRES EXTERNAL EVIDENCE`, `REQUIRES ENGINE CHANGE`, `REQUIRES HUMAN SEARCH`.
None of them offers a button, because none of them can be resolved by pressing
one.

## 14 · Why is this technically difficult?

Subset-sum is NP-complete, and the interesting instances are the dense ones —
73 candidate orders where many subsets balance. The solver counts solutions
rather than finding one, over a two-bitplane DP on the amount axis, with a
tolerance derived from the order count rather than guessed.

But the harder problem is epistemic. **Uniqueness inside a restricted space is
not uniqueness.** A proof can be arithmetically perfect and answer a question
that had already excluded the truth. That is why every reduction is recorded and
labelled convention or fact, why integrity travels with the finding, and why
`SEARCH_SPACE_UNCERTAIN` is a first-class blocker worth ₹4,99,574.15 on this
portfolio.

## 15 · Why is this architecture generalizable beyond reconciliation?

Because reconciliation is only the instance. The pattern is:

```
AI proposes.
Evidence constrains.
Deterministic systems verify.
Policy controls action.
The system abstains when justification runs out.
```

Anywhere a model's suggestion can trigger a consequential action — a payout, a
clinical flag, a compliance filing, a trade — the same five boundaries apply.
The model's value is generating candidates worth testing. Its danger is that its
output is indistinguishable, at the point of consumption, from a conclusion.

ATTEST's answer is to make the boundary structural rather than procedural: the
model cannot produce a verdict, the verdict cannot post without a recorded
search space, the policy cannot price what was not proved, and the ledger cannot
move without both.

> **Other systems optimise how much they automate.
> ATTEST optimises how much it can safely justify.**
