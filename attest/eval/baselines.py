"""Published-baseline comparison matchers.

PRD.md S6 promises that every ATTEST claim is comparative, not self-reported:
"we matched 94%" means nothing without a number for what the tools everyone
already has would have matched on the same data. These matchers are that
number -- the conventional approaches PRD.md S4 ("L4 -- why greedy is wrong")
argues against, implemented straight rather than as a strawman.

Interface (contracts/baselines.md):

    def fuzzy(settlements: list[Settlement], orders: list[Order]) -> list[Prediction]: ...

A bare list, not a (preds, pools) pair. Pools are the caller's job: every
matcher below calls `attest.blocking.candidates(settlements, orders, rung=2)`
itself to decide its matches, and `main` separately computes that same
rung-2 pool set once and hands it to `evaluate` for every matcher's report.
Rung 2 is pinned rather than left at the engine's default (rung 0) so every
matcher sees an identical, fixed candidate set -- differences in the table
come from the algorithm, not from one method being handed a wider or
narrower pool than another. This makes `blocking_recall` identical across
the `exact_only` / `fuzzy` / `greedy` rows and directly comparable.

`attest.pipeline.run`'s own row uses its own returned pools instead: that
pool set is per-settlement at whichever rung the cascade escalated to, so it
is a *mixed*-rung set and not pool-comparable to the pinned-rung-2 baselines.
Its accuracy numbers are still comparable; its blocking_recall is not.

Four matchers:

(a) `exact_only` -- join on gateway identifier alone, no arithmetic.
    `Order.payment_id` and `Settlement.utr` are different ID spaces (a gateway
    payment reference vs. a bank UTR) with no field connecting them; the UTR is
    only recoverable from `BankCredit.narration`, which no matcher here reads,
    per the interface above. So this matcher declines every settlement by
    construction. 0% is the finding, not a bug in the join -- see its
    docstring. This is the contract's floor and the only row that may be
    called "exact_only".

(b) `exact_amount_unique` -- SECONDARY, not `exact_only`. Non-degenerate
    exact-amount floor (settlement net equals exactly one pool order's net, at
    zero tolerance), reported separately so the exact-only row is not
    conflated with an amount-based sibling.

(c) `fuzzy` -- single order within 1% (relative) of the settlement net,
    first hit wins over the pool in blocking order. Deliberately not
    best-fit: that sloppiness is what "fuzzy matching" means in the tools this
    project is measured against.

(d) `greedy` -- the same 1% fit, scored and taken highest-first across ALL
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

#: Every baseline matcher is measured on the same fixed candidate set so
#: differences in the table come from the algorithm, not the pool.
BASELINE_RUNG = 2

Matcher = Callable[[list[Settlement], list[Order]], list[Prediction]]


def exact_only(settlements: list[Settlement], orders: list[Order]) -> list[Prediction]:
    """Join on gateway identifier alone -- no arithmetic, no fallback.

    Inspecting the schema first (as instructed): `Order` carries `payment_id`,
    a gateway payment reference like `pay_000123`. `Settlement` carries only
    `utr`, a bank UTR; `BankCredit.narration` carries that same UTR as free
    text. There is no field on either `Order` or `Settlement` that overlaps --
    `payment_id` and `utr` are drawn from disjoint ID spaces by construction
    (`attest.generate.generator.Generator._order` / `.build`). A matcher that
    joins only on identifier therefore has no key to join on, and declines
    every settlement. That is the structural result, reported plainly rather
    than papered over with an invented join. 0% is the floor.
    """
    return [
        Prediction(
            s.settlement_id, None, "exact-id",
            reason="no shared identifier: Order.payment_id and Settlement.utr are disjoint ID spaces",
        )
        for s in settlements
    ]


def exact_amount_unique(settlements: list[Settlement], orders: list[Order]) -> list[Prediction]:
    """SECONDARY -- not `exact_only`. Non-degenerate exact-amount floor:
    settlement net equals exactly one pool order's net, at zero tolerance.
    Declines on zero or 2+ hits.

    Stricter than `attest.layers.match_single_order`, which allows one order's
    rounding error (`tolerance_paise(1)`): this is zero tolerance, by the task
    definition of "exact-amount-unique". Reported apart from `exact_only`
    because it reasons over amount, and the contract reserves `exact_only` for
    unambiguous identifier evidence alone.
    """
    pools = candidates(settlements, orders, rung=BASELINE_RUNG)
    preds: list[Prediction] = []
    for s in settlements:
        fits = [o for o in pools[s.settlement_id] if o.net == s.net_paise]
        if len(fits) == 1:
            preds.append(Prediction(s.settlement_id, [fits[0].order_id], "exact-amount-unique"))
        else:
            reason = "no exact-net order in pool" if not fits else f"{len(fits)} orders tie on exact net"
            preds.append(Prediction(s.settlement_id, None, "exact-amount-unique", reason=reason))
    return preds


def _fits_1pct(o: Order, s: Settlement) -> bool:
    """|o.net - s.net_paise| <= 1% of s.net_paise, cross-multiplied so the test
    stays in integer paise rather than dividing into a float."""
    return abs(o.net - s.net_paise) * 100 <= s.net_paise


def fuzzy(settlements: list[Settlement], orders: list[Order]) -> list[Prediction]:
    """Amount within 1% (relative) of the settlement net; date is already
    constrained by blocking. First hit wins: the pool is scanned in exactly the
    order `candidates` returns it and the first order that fits is taken -- no
    sorting for the best fit. That sloppiness is the point of the baseline.
    """
    pools = candidates(settlements, orders, rung=BASELINE_RUNG)
    preds: list[Prediction] = []
    for s in settlements:
        hit = next((o for o in pools[s.settlement_id] if _fits_1pct(o, s)), None)
        if hit is not None:
            preds.append(Prediction(s.settlement_id, [hit.order_id], "fuzzy-1pct"))
        else:
            preds.append(Prediction(s.settlement_id, None, "fuzzy-1pct", reason="no order within 1%"))
    return preds


def greedy(settlements: list[Settlement], orders: list[Order]) -> list[Prediction]:
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
    pools = candidates(settlements, orders, rung=BASELINE_RUNG)

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
    return preds


def _fmt_row(name: str, rep: Report) -> str:
    return (
        f"| {name:<20s} | {rep.set_accuracy:>9.1%} | {rep.precision:>9.3f} | "
        f"{rep.recall:>6.3f} | {rep.wrong:>3d} ({rep.wrong/rep.n_settlements:>5.1%}) | "
        f"{rep.seconds:>7.2f}s |"
    )


def _worst_hazard_gap(baseline: Report, engine: Report) -> tuple[str, float, float] | None:
    """Hazard family with the largest (baseline hit-rate - engine hit-rate),
    restricted to families both reports scored, used to name where a
    baseline's advantage over the engine (if any) actually concentrates."""
    best: tuple[str, float, float] | None = None
    for case, (bhit, bn) in baseline.by_case.items():
        if case not in engine.by_case:
            continue
        ehit, en = engine.by_case[case]
        gap = bhit / bn - ehit / en
        if best is None or gap > best[1] - best[2]:
            best = (case, bhit / bn, ehit / en)
    return best


def _write_report(
    path: str,
    n: int,
    seed: int,
    exact_rep: Report,
    secondary_rep: Report,
    fuzzy_rep: Report,
    greedy_rep: Report,
    engine_rep: Report,
) -> None:
    baselines = {"exact_only": exact_rep, "fuzzy": fuzzy_rep, "greedy": greedy_rep}
    best_name = max(baselines, key=lambda k: baselines[k].set_accuracy)
    best = baselines[best_name]

    lines = [
        "# Baselines",
        "",
        f"Three reference matchers plus the engine, on identical data: `seed={seed}`, "
        f"`n={n}`, pools pinned at `rung={BASELINE_RUNG}` for every baseline "
        "(`attest.blocking.candidates`) so differences in the table come from the "
        "algorithm, not from one method being handed a better candidate set. The "
        "engine's own pool is per-settlement mixed-rung (whatever rung its cascade "
        "escalated to), so its `blocking_recall` is not pool-comparable to the "
        "baseline rows below -- its accuracy and WRONG numbers are.",
        "",
        "| matcher              | exact-set |  precision | recall | WRONG        | wall clock |",
        "|----------------------|----------:|-----------:|-------:|:-------------|-----------:|",
        _fmt_row("exact_only", exact_rep),
        _fmt_row("fuzzy", fuzzy_rep),
        _fmt_row("greedy", greedy_rep),
        _fmt_row("attest-engine", engine_rep),
        "",
        "Secondary (not `exact_only` -- reasons over amount, kept apart from the "
        "identifier-only floor per contract):",
        "",
        "| matcher                | exact-set |  precision | recall | WRONG        | wall clock |",
        "|------------------------|----------:|-----------:|-------:|:-------------|-----------:|",
        _fmt_row("exact_amount_unique", secondary_rep),
        "",
        f"blocking recall (ceiling, rung={BASELINE_RUNG}, baselines only): "
        f"{exact_rep.blocking_recall:.3f}",
        "",
        "## Analysis",
        "",
    ]

    para = [
        f"`exact_only` declines all {exact_rep.n_settlements} settlements: "
        "`Order.payment_id` and `Settlement.utr` are disjoint ID spaces with no "
        "connecting field, so an identifier-only join has nothing to join on. 0% "
        "is the structural floor, not a bug -- see the docstring for the schema "
        "evidence. The non-degenerate `exact_amount_unique` sibling, reported "
        f"separately, reaches {secondary_rep.set_accuracy:.1%} exact-set with "
        f"{secondary_rep.wrong} wrong.",
        "",
        f"`fuzzy` reaches {fuzzy_rep.set_accuracy:.1%} exact-set match with "
        f"{fuzzy_rep.wrong} wrong ({fuzzy_rep.wrong/fuzzy_rep.n_settlements:.1%}). "
        f"`greedy` reaches {greedy_rep.set_accuracy:.1%} with "
        f"{greedy_rep.wrong} wrong ({greedy_rep.wrong/greedy_rep.n_settlements:.1%}). "
        f"The engine reaches {engine_rep.set_accuracy:.1%} exact-set match with "
        f"{engine_rep.wrong} wrong ({engine_rep.wrong/engine_rep.n_settlements:.1%}).",
        "",
    ]

    if best.set_accuracy > engine_rep.set_accuracy:
        para.append(
            f"**`{best_name}` beats the engine on exact-set match** "
            f"({best.set_accuracy:.1%} vs {engine_rep.set_accuracy:.1%}) -- but at "
            f"{best.wrong} wrong ({best.wrong/best.n_settlements:.1%}) against the "
            f"engine's {engine_rep.wrong} ({engine_rep.wrong/engine_rep.n_settlements:.1%}). "
            "WRONG moves money on a false premise; declined routes to a human. A "
            "matcher that trades WRONG for exact-set is not an improvement, it is a "
            "worse system that scores better on the wrong column."
        )
    else:
        para.append(
            f"No baseline beats the engine on exact-set match; the best, "
            f"`{best_name}`, reaches {best.set_accuracy:.1%} against the engine's "
            f"{engine_rep.set_accuracy:.1%}."
        )
    gap = _worst_hazard_gap(best, engine_rep)
    if gap is not None and gap[1] > gap[2]:
        case, bhit, ehit = gap
        para.append(
            f" The largest per-family gap in `{best_name}`'s favour is `{case}` "
            f"({bhit:.1%} vs the engine's {ehit:.1%})."
        )
    elif gap is not None:
        case, bhit, ehit = gap
        para.append(
            f" Even on `{best_name}`'s best-relative family, `{case}`, the engine "
            f"still leads ({ehit:.1%} vs {bhit:.1%})."
        )

    lines.append("".join(para))
    lines.append("")

    with open(path, "w") as f:
        f.write("\n".join(lines))


def main(argv: list[str]) -> int:
    n = int(argv[1]) if len(argv) > 1 else 250
    ds = build(n, seed=SEED_TRAIN)

    # Pinned rung=2 pools, computed once and shared across every baseline's
    # `evaluate` call so `blocking_recall` is identical for all of them.
    pools = candidates(ds.settlements, ds.orders, rung=BASELINE_RUNG)

    matchers: list[tuple[str, Matcher]] = [
        ("exact_only", exact_only),
        ("exact_amount_unique (secondary)", exact_amount_unique),
        ("fuzzy", fuzzy),
        ("greedy", greedy),
    ]

    reports: dict[str, Report] = {}
    for name, fn in matchers:
        with Timer() as t:
            preds = fn(ds.settlements, ds.orders)
        reports[name] = evaluate(ds.settlements, ds.truth, preds, pools, t.elapsed)

    with Timer() as t:
        preds3, pools3, _findings = pipeline_run(ds.settlements, ds.orders)
    reports["attest-pipeline"] = evaluate(ds.settlements, ds.truth, preds3, pools3, t.elapsed)

    for name, rep in reports.items():
        print(rep.render(f"ATTEST baselines · {name} · n={n} · seed {SEED_TRAIN}"))

    _write_report(
        "attest/eval/BASELINES.md",
        n,
        SEED_TRAIN,
        reports["exact_only"],
        reports["exact_amount_unique (secondary)"],
        reports["fuzzy"],
        reports["greedy"],
        reports["attest-pipeline"],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
