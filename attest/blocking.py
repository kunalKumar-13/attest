"""Layer 0 -- candidate generation.

Comparing every order against every settlement is 11k x 1.2k pairs, and the
subset search downstream is exponential in the *candidate* count, so pruning is
not an optimisation here: it is what makes the problem decidable at all.

Blocking also imposes a hard ceiling on final recall. An order pruned here can
never be matched by any later layer, however clever. `blocking_recall` in the
harness measures that ceiling explicitly, because a matcher reporting 94% under
a blocker that already threw away 5% of true pairs is really reporting 89%.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import timedelta

from attest.model import Order, Settlement

#: How far back a settlement may reach for its orders. T+2 nominal, stretched by
#: weekends and bank holidays to T+4; 6 covers both with a day of slack.
#: Deliberately *not* wide enough for CHARGEBACK_REVERSAL, which reaches 14-30
#: days back. Widening it to catch those inflates every candidate pool by ~5x for
#: a 3% family -- the harness reports what that choice costs instead of hiding it.
LOOKBACK_DAYS = 6


def candidates(
    settlements: list[Settlement], orders: list[Order]
) -> dict[str, list[Order]]:
    """Map each settlement to the orders it could plausibly contain.

    Bucketing by date makes this O(n + m*w) rather than O(n*m): each settlement
    touches only the `w` day-buckets inside its lookback window.
    """
    by_day: dict[object, list[Order]] = defaultdict(list)
    for o in orders:
        by_day[o.captured_on].append(o)

    out: dict[str, list[Order]] = {}
    for s in settlements:
        pool: list[Order] = []
        for back in range(LOOKBACK_DAYS + 1):
            pool.extend(by_day.get(s.settled_on - timedelta(days=back), ()))
        # An order can never contribute more than the whole credit.
        out[s.settlement_id] = [o for o in pool if o.net <= s.net_paise]
    return out
