# Product principles

Ten rules the product is built on. Each is enforced somewhere — by a contract,
by the data model, or by a decision that is written down.

### 1 · Money before metadata

A row leads with the amount it holds, not with a verb or a label. The blocker
list is ordered `value → scope → blocked at → why → what would unblock it`,
because value is what decides whether the work is worth the next ten minutes.

### 2 · Blockers before exceptions

An exception says *this settlement has a problem*. A blocker says *this is why
money is stuck, how much is affected, and what would move it*. 197 settlements
ambiguous for the same missing field are one piece of work, not 197.

### 3 · Value unlocked before row count

Work is ranked by what an answer would release, not by amount and not by
volume. A cause worth ₹47.96L that one change settles outranks fifty separate
questions worth ₹10k each.

### 4 · Evidence before action

Nothing is actionable until the search space, the candidates and the surviving
explanations have been stated. The Evidence lens is not a justification written
after the fact; it is what the decision was made from.

### 5 · Permission before execution

Proof, then policy, then action — three separate events, never merged.
Activity shows them separately on purpose: the engine proving something, the
policy permitting it, and the ledger changing are three different facts.

### 6 · Absence is a valid financial result

`NO ENTRY WRITTEN`, `LEDGER UNCHANGED`, `UNPRICED`, `ABSTAINED`. A verdict that
held and a ledger that did not move are results. Journal shows a ledger effect
of ₹0.00 **balanced by absence** rather than pretending a transaction exists.

### 7 · External capability must be explicit

Every blocker states what ATTEST can do about it, in words:
`REQUIRES EXTERNAL EVIDENCE` · `REQUIRES ENGINE CHANGE` · `REQUIRES HUMAN
SEARCH`. Enforced by
`test_no_action_label_claims_a_capability_attest_does_not_have`.

### 8 · AI may propose; deterministic systems decide

◇ MODEL proposes, ○ SOLVER tests, ● ENGINE decides. The model can investigate
and narrate. It cannot prove, price or post — and `POST_ENTRY` is held by no
agent, refused at configuration time rather than at the call site.

### 9 · Never fabricate a capability

A label that promises an operation the engine cannot perform is the product
lying about itself. `FREE RE-RUN` was exactly that: the pipeline already
escalates through every rung on each run, so widening the window means widening
beyond a ladder that lives in protected code and that the blocking study
explicitly decided to keep. It is now `REQUIRES ENGINE CHANGE`, and a contract
fails if the old wording returns.

### 10 · Every unresolved amount has a reason

₹48,03,127.81 is held at verification, and the product can say why for all of
it. A settlement that cannot be explained still carries what was established,
what is unresolved, and what record is missing — `setl_000109` establishes
₹5,868.98 of ₹6,316.03 and names the ₹447.05 that has no matching record.
