"""The engine. Layers run cheapest-first; each removes work from the next.

Layer 3 (meet-in-the-middle subset-sum) and beyond land on D2+. Until then this
is the honest floor: what pure determinism achieves before any search or any
model is involved. Every later claim is measured as a delta against it.
"""

from __future__ import annotations

from attest.blocking import candidates
from attest.eval.harness import Prediction
from attest.layers import match_single_order
from attest.model import Order, Settlement


def run(
    settlements: list[Settlement], orders: list[Order]
) -> tuple[list[Prediction], dict[str, list[Order]]]:
    pools = candidates(settlements, orders)
    preds: list[Prediction] = []

    for s in settlements:
        pool = pools[s.settlement_id]

        single = match_single_order(s, pool)
        if single is not None:
            preds.append(Prediction(s.settlement_id, single, "L2-single"))
            continue

        preds.append(Prediction(
            s.settlement_id, None, "declined",
            reason=f"no deterministic explanation; {len(pool)} candidates in window",
        ))

    return preds, pools
