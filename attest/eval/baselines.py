"""Published-baseline comparison matchers.

PRD.md S6 promises that every ATTEST claim is comparative, not self-reported:
"we matched 94%" means nothing without a number for what the tools everyone
already has would have matched on the same data. These three matchers are that
number -- the conventional approaches PRD.md S4 ("L4 -- why greedy is wrong")
argues against, implemented straight rather than as a strawman.

All three share `attest.pipeline.run`'s calling convention --

    (settlements: list[Settlement], orders: list[Order])
        -> (predictions: list[Prediction], pools: dict[str, list[Order]])

-- but return only the two-tuple: these are baselines being measured, not the
engine, so they have no findings to report. Every matcher below calls
`attest.blocking.candidates` verbatim for its pools rather than reimplementing
blocking, because `evaluate` derives `blocking_recall` from the pools a matcher
returns, and rows are only comparable if that ceiling is identical across all of
them.

(a) `exact_identifier` -- join on gateway identifier alone, no arithmetic.
    `Order.payment_id` and `Settlement.utr` are different ID spaces (a gateway
    payment reference vs. a bank UTR) with no field connecting them; the UTR is
    only recoverable from `BankCredit.narration`, which no matcher here reads,
    per the interface above. So this matcher declines every settlement by
    construction. 0% is the finding, not a bug in the join -- see its docstring.
    `exact_amount_unique` is the non-degenerate sibling that gives the
    exact-only row a real floor to report.

(b) `fuzzy` -- single order within 1% (relative) of the settlement net,
    first hit wins over the pool in blocking order. Deliberately not
    best-fit: that sloppiness is what "fuzzy matching" means in the tools this
    project is measured against.

(c) `greedy` -- the same 1% fit, scored and taken highest-first across ALL
    settlements at once, consuming orders globally. Scorer and tie-break are
    documented on the function; an undocumented scorer makes the comparison
    unreproducible.
"""

from __future__ import annotations

import sys
from collections.abc import Callable

from attest.__main__ import SEED_TRAIN
from attest.blocking import candidates
from attest.eval.harness import Prediction, Report, Timer, evaluate
from attest.generate.generator import build
from attest.model import Order, Settlement
from attest.pipeline import run as pipeline_run

Matcher = Callable[[list[Settlement], list[Order]], tuple[list[Prediction], dict[str, list[Order]]]]


def exact_identifier(
    settlements: list[Settlement], orders: list[Order]
) -> tuple[list[Prediction], dict[str, list[Order]]]:
    """Join on gateway identifier alone -- no arithmetic, no fallback.

    Inspecting the schema first (as instructed): `Order` carries `payment_id`,
    a gateway payment reference like `pay_000123`. `Settlement` carries only
    `utr`, a bank UTR; `BankCredit.narration` carries that same UTR as free
    text. There is no field on either `Order` or `Settlement` that overlaps --
    `payment_id` and `utr` are drawn from disjoint ID spaces by construction
    (`attest.generate.generator.Generator._order` / `.build`). A matcher that
    joins only on identifier therefore has no key to join on, and declines
    every settlement. That is the structural result, reported plainly rather
    than papered over with an invented join.
    """
    pools = candidates(settlements, orders)
    preds = [
        Prediction(
            s.settlement_id, None, "exact-id",
            reason="no shared identifier: Order.payment_id and Settlement.utr are disjoint ID spaces",
        )
        for s in settlements
    ]
    return preds, pools


def exact_amount_unique(
    settlements: list[Settlement], orders: list[Order]
) -> tuple[list[Prediction], dict[str, list[Order]]]:
    """Non-degenerate exact-only floor: settlement net equals exactly one pool
    order's net, at zero tolerance. Declines on zero or 2+ hits.

    Stricter than `attest.layers.match_single_order`, which allows one order's
    rounding error (`tolerance_paise(1)`): this is zero tolerance, by the task
    definition of "exact-amount-unique", so the exact-only row in the
    comparison table has a real number instead of the 0% `exact_identifier`
    reports for a different, structural reason.
    """
    pools = candidates(settlements, orders)
    preds: list[Prediction] = []
    for s in settlements:
        fits = [o for o in pools[s.settlement_id] if o.net == s.net_paise]
        if len(fits) == 1:
            preds.append(Prediction(s.settlement_id, [fits[0].order_id], "exact-amount-unique"))
        else:
            reason = "no exact-net order in pool" if not fits else f"{len(fits)} orders tie on exact net"
            preds.append(Prediction(s.settlement_id, None, "exact-amount-unique", reason=reason))
    return preds, pools


def _fits_1pct(o: Order, s: Settlement) -> bool:
    """|o.net - s.net_paise| <= 1% of s.net_paise, cross-multiplied so the test
    stays in integer paise rather than dividing into a float."""
    return abs(o.net - s.net_paise) * 100 <= s.net_paise


def fuzzy(
    settlements: list[Settlement], orders: list[Order]
) -> tuple[list[Prediction], dict[str, list[Order]]]:
    """Amount within 1% (relative) of the settlement net; date is already
    constrained by blocking. First hit wins: the pool is scanned in exactly the
    order `candidates` returns it and the first order that fits is taken -- no
    sorting for the best fit. That sloppiness is the point of the baseline.
    """
    pools = candidates(settlements, orders)
    preds: list[Prediction] = []
    for s in settlements:
        hit = next((o for o in pools[s.settlement_id] if _fits_1pct(o, s)), None)
        if hit is not None:
            preds.append(Prediction(s.settlement_id, [hit.order_id], "fuzzy-1pct"))
        else:
            preds.append(Prediction(s.settlement_id, None, "fuzzy-1pct", reason="no order within 1%"))
    return preds, pools


def greedy(
    settlements: list[Settlement], orders: list[Order]
) -> tuple[list[Prediction], dict[str, list[Order]]]:
    """The approach PRD.md S4 argues against, implemented to measure the cost
    of being wrong rather than merely to describe it.

    Scorer: every (settlement, candidate-order) pair that passes the same 1%
    relative fit as `fuzzy` is scored

        score = 1 - |o.net - s.net_paise| / s.net_paise

    i.e. 1.0 for an exact match, falling linearly to 0.0 at the 1% edge. ALL
    pairs, across every settlement, are sorted descending by score. Ties (score
    equal, which a whole-rupee bundle makes common) break deterministically by
    `(settlement_id, order_id)` ascending, so a run at a fixed seed is
    reproducible byte for byte. The sorted list is then walked once: a pair is
    taken only if neither its settlement nor its order has been claimed yet,
    and both are then consumed globally.

    That global consumption is the failure mode being measured: one
    confident-looking pair can starve a later, equally valid settlement of the
    order it needed, and both are then wrong or declined. It is the same
    failure `attest.pipeline.run` avoids by deferring to CP-SAT set packing
    (L4b) instead of taking greedily.
    """
    pools = candidates(settlements, orders)

    pairs: list[tuple[float, str, str]] = []
    for s in settlements:
        for o in pools[s.settlement_id]:
            if _fits_1pct(o, s):
                score = 1.0 - abs(o.net - s.net_paise) / s.net_paise
                pairs.append((score, s.settlement_id, o.order_id))
    pairs.sort(key=lambda p: (-p[0], p[1], p[2]))

    claimed_settlements: set[str] = set()
    claimed_orders: set[str] = set()
    assignment: dict[str, str] = {}
    for _, sid, oid in pairs:
        if sid in claimed_settlements or oid in claimed_orders:
            continue
        assignment[sid] = oid
        claimed_settlements.add(sid)
        claimed_orders.add(oid)

    preds = []
    for s in settlements:
        oid = assignment.get(s.settlement_id)
        if oid is not None:
            preds.append(Prediction(s.settlement_id, [oid], "greedy-1pct"))
        else:
            preds.append(
                Prediction(s.settlement_id, None, "greedy-1pct", reason="no unclaimed order within 1%")
            )
    return preds, pools


def main(argv: list[str]) -> int:
    n = int(argv[1]) if len(argv) > 1 else 1200
    ds = build(n, seed=SEED_TRAIN)

    matchers: list[tuple[str, Matcher]] = [
        ("exact-id", exact_identifier),
        ("exact-amount-unique", exact_amount_unique),
        ("fuzzy-1pct", fuzzy),
        ("greedy-1pct", greedy),
    ]

    reports: list[tuple[str, Report]] = []
    for name, fn in matchers:
        with Timer() as t:
            preds, pools = fn(ds.settlements, ds.orders)
        reports.append((name, evaluate(ds.settlements, ds.truth, preds, pools, t.elapsed)))

    with Timer() as t:
        preds3, pools3, _findings = pipeline_run(ds.settlements, ds.orders)
    reports.append(("attest-pipeline", evaluate(ds.settlements, ds.truth, preds3, pools3, t.elapsed)))

    for name, rep in reports:
        print(rep.render(f"ATTEST baselines · {name} · n={n} · seed {SEED_TRAIN}"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
