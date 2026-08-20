# Baselines

Three reference matchers plus the engine, on identical data: `seed=20260821`, `n=250`, pools pinned at `rung=2` for every baseline (`attest.blocking.candidates`) so differences in the table come from the algorithm, not from one method being handed a better candidate set. The engine's own pool is per-settlement mixed-rung (whatever rung its cascade escalated to), so its `blocking_recall` is not pool-comparable to the baseline rows below -- its accuracy and WRONG numbers are.

| matcher              | exact-set | precision | recall |    WRONG    | wall clock |
|----------------------|-----------|-----------|--------|--------------|------------|
| exact_only           |      0.0% |     0.000 |  0.000 |   0 ( 0.0%) |    0.00s |
| fuzzy                |      2.8% |     0.368 |  0.003 |  12 ( 4.8%) |    0.02s |
| greedy               |      4.0% |     0.556 |  0.004 |   8 ( 3.2%) |    0.02s |
| attest-engine        |     20.0% |     0.983 |  0.076 |   1 ( 0.4%) |   10.36s |

Secondary (not `exact_only` -- reasons over amount, kept apart from the identifier-only floor per contract):

| matcher              | exact-set | precision | recall |    WRONG    | wall clock |
|----------------------|-----------|-----------|--------|--------------|------------|
| exact_amount_unique  |      4.0% |     1.000 |  0.004 |   0 ( 0.0%) |    0.02s |

blocking recall (ceiling, rung=2, baselines only): 1.000

## Analysis

`exact_only` declines all 250 settlements: `Order.payment_id` and `Settlement.utr` are disjoint ID spaces with no connecting field, so an identifier-only join has nothing to join on. 0% is the structural floor, not a bug -- see the docstring for the schema evidence. The non-degenerate `exact_amount_unique` sibling, reported separately, reaches 4.0% exact-set with 0 wrong.

`fuzzy` reaches 2.8% exact-set match with 12 wrong (4.8%). `greedy` reaches 4.0% with 8 wrong (3.2%). The engine reaches 20.0% exact-set match with 1 wrong (0.4%).

No baseline beats the engine on exact-set match; the best, `greedy`, reaches 4.0% against the engine's 20.0%. But `fuzzy` posts 12 wrong (4.8%) against the engine's 1 (0.4%) -- WRONG is the column that matters, and on it every baseline here is worse than the engine even though none out-scores it on exact-set.

`greedy`'s strongest family is `clean` (11.6%), where the engine still leads (43.0%); `greedy` scores 0% on every other family in the table -- the baselines never resolve a genuinely multi-order bundle, only the single-order cases that happen to also be `clean`.
