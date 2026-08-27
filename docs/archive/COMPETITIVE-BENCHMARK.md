# Competitive benchmark — what exists and what is missing

Track 04 asks for *throughput plus measured accuracy*. This records what is
measured today, against what §VIII asks for.

---

## What exists — `benchmark/baselines.json`, 500 settlements, held-out seeds

| approach | decided | wrong | false-proof rate | pair precision | coverage | seconds |
|---|---|---|---|---|---|---|
| `exact_only` | 22 | 0 | **0.0%** | 1.000 | 4.4% | 0.05 |
| `fuzzy` | 30 | 12 | 40.0% | 0.600 | 3.6% | 0.04 |
| **ATTEST** | **84** | **4** | **4.8%** | **0.959** | **16.0%** | 4.56 |
| `greedy` | 462 | 439 | 95.0% | 0.165 | 4.6% | 0.05 |

Read across the row, not down a column. `exact_only` is the most precise and
answers 4% of the book. `greedy` answers nearly everything and is wrong 95% of
the time. **ATTEST decides 84 against `exact_only`'s 22, at a false-proof rate
one twentieth of `greedy`'s.**

The safety/coverage frontier is the story. No single column wins it.

## What exists — the AI layer, `benchmark/anchoring.json`, five seeds

| | |
|---|---|
| ambiguous settlements seen | 1,020 |
| the loop had something to say on | 63 |
| correct | **27** |
| wrong | 36 |
| precision | **0.4286** |

Below a coin flip. D8 first measured this by hand at 0.521; the re-measurement
came back worse and the feature stayed disabled. **This measurement is the
reason the model has no authority** — which is the strongest possible answer to
the *AI Judgment* dimension.

## What §VIII asks for and we do not have

**A naive-LLM reconciliation baseline.** We benchmark `exact_only`, `fuzzy`,
`greedy` and ATTEST — deterministic alternatives — but not *"ask a model to pick
the orders"*. That is the baseline a judge will imagine, and it is the one every
competing submission effectively is.

We have the harness (`attest/eval/`), the ground truth, and the proposer
interface. A stub LLM-shaped proposer that returns a plausible subset and is
scored the same way would produce the missing row.

**Honest expectation:** it will land near `greedy` — plausible subsets that
balance are easy to produce and usually wrong. If it does not, that is a finding
worth publishing either way. **This is P1-2.**

**Cost and latency per approach.** We record seconds; we do not record token
cost, because nothing calls a paid model. Worth stating rather than measuring.

## What we should not claim

- Not *"most accurate"* — `exact_only` is, and our README says so.
- Not *"four times the coverage"* — it is **3.8×** on decided (84/22) and 3.6×
  on the coverage figure. Restated to the counts.
- Not a per-case probability. Policy prices expected loss; it does not score
  confidence, and the word appears nowhere in the product.
