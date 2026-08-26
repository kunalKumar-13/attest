# Internship signal — three stories

Not a list of everything built. The three that answer *"can this person be
trusted with money-touching code?"* — each in the shape an interviewer wants.

---

## 1 · Cardinality was not membership

**Problem.** A `PROVEN` finding may only post if the orders it cites actually
belong to the search space it was proved in.

**Attack.** An adversarial case constructed a finding citing two orders that
were never in the candidate pool.

**Discovery.** The guard compared **counts**, not sets. A forged proof citing
two invented orders against a five-candidate space passed, because 2 ≤ 5.

**Design change.** `set(proof.order_ids) <= space.members` — membership, with
the members recorded on the space. An unrecorded membership set is now no record
of a search, and fails closed.

**Regression.** In the adversarial suite as a permanent attack; the invariant is
one of four numbered conditions in `verdict.postable`.

**Why it matters.** A label is not authority. The proof has to be structurally
connected to the search that produced it, or "PROVEN" is a string.

---

## 2 · The system was postable *because* it omitted its evidence

**Problem.** `postable` gates whether a proof may reach the ledger.

**Attack.** A `PROVEN` finding assembled outside the pipeline, with no search
space attached.

**Discovery.** It returned `True`. The check read *"if a space is present and
compromised, refuse"* — so **a finding with no space at all passed**. It was
postable precisely because it omitted the evidence it would have been judged on.

**Design change.** Fails closed: absent space, empty universe, no reductions or
no solver layer each refuse. And the refusal had to be fixed too — it reported
*"the search space is compromised"* for all six conditions, sending an operator
to inspect a space that was fine.

**Regression.** Both the gate and the reason are contract-tested; a refusal that
names the wrong cause fails.

**Why it matters.** Fail-open defaults in a money path are invisible until they
are expensive. The absence of evidence read as the absence of a problem.

---

## 3 · We measured our own AI and took its authority away

**Problem.** When several explanations survive, can a model choose?

**Attack.** We let it. Then we measured it against ground truth across five
seeds — and made the measurement re-runnable rather than leaving it in a
markdown table.

**Discovery.** The loop resolved 63 cases and got **27 right — 0.4286**. Below a
coin flip. The cause is structural, not fixable by a better model: the
settlement report carries no order-level reference, so every anchor is a guess.
*A language model would change which guess gets made, not that it is one.*

**Design change.** The loop still runs and its verdict is **discarded** —
`changed_nothing: true`. The model proposes; the deterministic solver tests
whether the proposal discriminates; the engine keeps the verdict it had.

**Regression.** The displayed figure is read from `benchmark/anchoring.json` at
call time, and a test refuses any bare superseded number.

**Why it matters.** The interesting engineering decision was not building the AI
feature. It was measuring it, finding it worse than chance, and removing it from
the authority path while keeping it where it genuinely helps — investigation.

---

## The line these three make

> *"I attacked my own system three times and it failed twice. Both failures were
> in the boundary between a label and the authority that label implies."*
