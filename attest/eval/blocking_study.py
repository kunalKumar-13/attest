"""Measurement of the lag ladder that `attest/blocking.py` hard-codes.

`LAG_LADDER = (2, 3, 4)` was chosen by argument. This file is the argument's
audit: it re-derives pool size and the blocking ceiling for every ladder worth
testing, so the constant can be defended with a number instead of a paragraph.

Three things this file is careful about, because each is easy to get silently
wrong and each would invalidate the whole sweep.

**The sweep must measure the frozen function.** `StudyIndex` subclasses
`attest.blocking.PoolIndex` and reuses `_capture_dates_for` verbatim rather than
reimplementing the calendar inversion -- that inversion is exactly what D3 got
wrong by hand. `anchor()` then asserts that at the default ladder, with the
amount filter on and consumption off, the parameterised pools are *identical*
(same orders, same order) to `attest.blocking.candidates`, and that the
parameterised engine reproduces `attest.pipeline.run` finding for finding.
Without those two assertions the sweep would be measuring a different function
and every row below would be fiction.

**Three different numbers are all called "blocking recall".** They are not
comparable and each row states which it is:

* `STATIC`  -- every settlement scored at the ladder's terminal rung, no
  consumption. Uniform-rung. This is the ceiling the ladder *offers*.
* `ORACLE`  -- same, but the true bundle is consumed after each settlement, in a
  stated order. Bundles are disjoint by construction, so this isolates what
  consumption does to pool size with recall held harmless.
* `LIVE`    -- the pools `pipeline.run` actually used, which is a *mixed-rung*
  set: whatever rung each settlement happened to succeed at. This is the ceiling
  the engine *realises*, and it is lower, because most settlements never
  escalate past rung 0.

**Consumption makes pools order-dependent.** Two orders are evaluated and both
reported: easiest-first (the engine's own order) and chronological.
"""

from __future__ import annotations

import os
import sys
import time
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import date, timedelta
from functools import lru_cache
from itertools import combinations
from pathlib import Path

from attest.__main__ import SEED_TRAIN
from attest.blocking import LAG_LADDER, PoolIndex, _capture_dates_for, candidates
from attest.eval.harness import Prediction, Report, Timer, evaluate
from attest.evidence import to_fixed_point
from attest.generate.generator import Dataset, build
from attest.layers import match_single_order
from attest.model import Order, Settlement, TrueMatch, tolerance_paise
from attest.pipeline import _proof
from attest.pipeline import run as pipeline_run
from attest.subsetsum import OutOfEnvelope, solve
from attest.verdict import Finding, Verdict, check

#: Lags the sweep enumerates. 1 is below the nominal T+2 cycle and 5-6 are the
#: old fixed-width window; both are included so the chosen ladder is bracketed
#: by settings that are known to be wrong in each direction.
SWEEP_LAGS: tuple[int, ...] = (1, 2, 3, 4, 5, 6)

#: `_capture_dates_for` runs the forward business-day map over a 13-day window
#: per call and the sweep calls it ~200k times. Cached here rather than in the
#: frozen module: same inputs, same outputs, no behaviour change.
_dates = lru_cache(maxsize=None)(_capture_dates_for)

#: `_capture_dates_for`'s own default. A lag of L business days spans up to
#: ceil(7L/5) + 2 calendar days once weekends fan in, so 12 covers lag 8 and no
#: more -- at lag 11 the function returns the empty set and a ladder rung
#: silently becomes a no-op. Measured in `span_cap()`; see BLOCKING.md.
DEFAULT_SPAN = 12


# --------------------------------------------------------------------------
# Parameterised blocking
# --------------------------------------------------------------------------


Rung = tuple[int, ...]


def _rungs(ladder: Sequence[int] | Sequence[Sequence[int]]) -> tuple[Rung, ...]:
    """Normalise a ladder to one lag-set per rung.

    `attest.blocking` spells a ladder as a flat tuple of ints, which forces
    exactly one new lag per rung. The sweep needs to ask a question that spelling
    cannot express -- *what if rung 0 already covered two lags?* -- so a rung may
    also be given as a tuple. `(2, 3, 4)` and `((2,), (3,), (4,))` are the same
    ladder; `((2, 4),)` is a single rung that no flat tuple can write.
    """
    out: list[Rung] = []
    for item in ladder:
        out.append((item,) if isinstance(item, int) else tuple(item))
    return tuple(out)


class StudyIndex(PoolIndex):
    """`PoolIndex` with the ladder, the amount filter and consumption exposed.

    Subclassing is the sanctioned way to vary a frozen module: the date
    arithmetic, the bucketing and the spent-set semantics are inherited
    unchanged, and only the knobs under study are overridden.
    """

    def __init__(self, orders: list[Order],
                 ladder: Sequence[int] | Sequence[Sequence[int]] = LAG_LADDER,
                 *, amount_filter: bool = True, consumption: bool = True,
                 span: int = DEFAULT_SPAN) -> None:
        super().__init__(orders)
        self.ladder = _rungs(ladder)
        self.amount_filter = amount_filter
        self.consumption = consumption
        self.span = span

    def consume(self, order_ids: tuple[str, ...] | list[str]) -> None:
        if self.consumption:
            super().consume(order_ids)

    def pool(self, s: Settlement, rung: int = 0) -> list[Order]:
        days: set[date] = set()
        for step in self.ladder[: rung + 1]:
            for lag in step:
                days |= _dates(s.settled_on, lag, self.span)
        out: list[Order] = []
        for d in days:
            for o in self._by_day.get(d, ()):
                if o.order_id in self._spent:
                    continue
                # Without the filter an order larger than the whole credit still
                # enters the pool; `subsetsum.solve` discards it again, so the
                # cost is pool size and the MAX_POOL envelope, not wrong answers.
                if self.amount_filter and not 0 < o.net <= s.net_paise:
                    continue
                out.append(o)
        return out


def study_candidates(settlements: list[Settlement], orders: list[Order],
                     ladder: Sequence[int] | Sequence[Sequence[int]] = LAG_LADDER,
                     rung: int = 0,
                     *, amount_filter: bool = True,
                     span: int = DEFAULT_SPAN) -> dict[str, list[Order]]:
    idx = StudyIndex(orders, ladder, amount_filter=amount_filter, consumption=False,
                     span=span)
    return {s.settlement_id: idx.pool(s, rung) for s in settlements}


# --------------------------------------------------------------------------
# Parameterised engine -- a copy of `pipeline.run` with the ladder lifted out
# --------------------------------------------------------------------------


def study_run(settlements: list[Settlement], orders: list[Order],
              ladder: Sequence[int] | Sequence[Sequence[int]] = LAG_LADDER,
              *, amount_filter: bool = True,
              consumption: bool = True, span: int = DEFAULT_SPAN) -> tuple[
                  list[Prediction], dict[str, list[Order]], list[Finding]]:
    """`pipeline.run` with `LAG_LADDER` replaced by `ladder`.

    Duplicated rather than monkeypatched: patching a frozen module's constant at
    runtime is a write in disguise, and it would leave every other importer of
    `attest.pipeline` observing the mutated value. `anchor()` pins this copy to
    the original at the default settings.
    """
    index = StudyIndex(orders, ladder, amount_filter=amount_filter,
                       consumption=consumption, span=span)
    by_id = {o.order_id: o for o in orders}
    order_of_work = sorted(settlements, key=lambda s: len(index.pool(s, 0)))

    findings: list[Finding] = []
    preds: list[Prediction] = []
    pools_used: dict[str, list[Order]] = {}

    for s in order_of_work:
        finding: Finding | None = None

        for rung in range(len(index.ladder)):
            pool = index.pool(s, rung)
            pools_used[s.settlement_id] = pool

            single = match_single_order(s, pool)
            if single is not None:
                members = [by_id[single[0]]]
                p = _proof(s, members)
                if check(p, s, by_id):
                    finding = Finding(s.settlement_id, Verdict.PROVEN, (p,),
                                      exhaustive=True, layer=f"L2-single/r{rung}")
                    break

            try:
                verdict, sols, exhaustive = solve(pool, s.net_paise)
            except OutOfEnvelope as exc:
                finding = Finding(s.settlement_id, Verdict.AMBIGUOUS, (),
                                  unsat_core=(f"out-of-envelope: {exc}",),
                                  layer=f"L3-skipped/r{rung}")
                break

            if verdict is Verdict.CONTRADICTED:
                continue

            proofs = tuple(
                p for p in (_proof(s, [by_id[o] for o in sol.order_ids]) for sol in sols)
                if check(p, s, by_id)
            )
            if not proofs:
                continue
            finding = Finding(
                s.settlement_id,
                Verdict.PROVEN if len(proofs) == 1 else Verdict.AMBIGUOUS,
                proofs, exhaustive=exhaustive, layer=f"L3-dp/r{rung}",
            )
            break

        if finding is None:
            finding = Finding(
                s.settlement_id, Verdict.CONTRADICTED, (),
                unsat_core=("no subset of any window satisfies the amount constraint",),
                layer="L3-dp/exhausted",
            )

        findings.append(finding)
        if finding.postable:
            index.consume(finding.proofs[0].order_ids)

    # L4 mirrors `pipeline.run` at HEAD, including its default: off. It matters
    # to a blocking study because propagation promotes AMBIGUOUS to PROVEN by
    # elimination, so an explanation that survives only because the true one was
    # pruned can be promoted into a posted entry -- blocking loss and false
    # proofs are coupled through this layer, not just through the solver.
    if os.environ.get("ATTEST_PROP"):
        to_fixed_point(findings)

    preds = [
        Prediction(
            f.settlement_id,
            list(f.proofs[0].order_ids) if f.postable else None,
            f.layer,
            reason="" if f.postable else f.verdict.value,
        )
        for f in findings
    ]
    return preds, pools_used, findings


# --------------------------------------------------------------------------
# Anchor
# --------------------------------------------------------------------------


def span_cap(probe: date = date(2026, 6, 15)) -> int:
    """Largest lag `_capture_dates_for` can still answer at its default span.

    A rung whose lag exceeds this returns no capture dates at all, so widening
    `LAG_LADDER` past it is a silent no-op rather than a wider window. Computed
    rather than asserted, because the bound moves if the default span does.
    """
    lag = 1
    while _dates(probe, lag, DEFAULT_SPAN) == _dates(probe, lag, 60):
        lag += 1
    return lag - 1


def anchor(ds: Dataset) -> None:
    """Assert the parameterised copies reproduce the frozen originals exactly.

    Identity of the *sequence*, not the set: `pool` iterates a set of dates, so a
    reordering would still be a behaviour change for `match_single_order`, which
    takes `fits[0]`.
    """
    for rung in range(len(LAG_LADDER)):
        want = candidates(ds.settlements, ds.orders, rung)
        got = study_candidates(ds.settlements, ds.orders, LAG_LADDER, rung)
        assert want.keys() == got.keys(), f"pool keys differ at rung {rung}"
        for sid, ref in want.items():
            assert [o.order_id for o in ref] == [o.order_id for o in got[sid]], (
                f"pool differs at rung {rung} for {sid}"
            )

    w_preds, w_pools, w_find = pipeline_run(ds.settlements, ds.orders)
    g_preds, g_pools, g_find = study_run(ds.settlements, ds.orders, LAG_LADDER)
    assert [(p.settlement_id, p.order_ids, p.layer) for p in w_preds] == \
           [(p.settlement_id, p.order_ids, p.layer) for p in g_preds], "predictions differ"
    assert [(f.settlement_id, f.verdict, f.layer) for f in w_find] == \
           [(f.settlement_id, f.verdict, f.layer) for f in g_find], "findings differ"
    assert {k: [o.order_id for o in v] for k, v in w_pools.items()} == \
           {k: [o.order_id for o in v] for k, v in g_pools.items()}, "pools_used differ"


# --------------------------------------------------------------------------
# Metrics
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Row:
    ladder: tuple[Rung, ...]
    mode: str
    """STATIC | ORACLE-easiest | ORACLE-chrono | LIVE."""
    amount_filter: bool
    p50: int
    p90: int
    pmax: int
    recall: float
    lost_pairs: int
    total_pairs: int
    by_case: dict[str, tuple[int, int]] = field(default_factory=dict)
    """case -> (reachable pairs, total pairs)."""
    hurt: tuple[str, ...] = ()
    """Families that lose at least one true pair at this setting."""


def _percentile(sorted_vals: list[int], q: float) -> int:
    if not sorted_vals:
        return 0
    i = min(len(sorted_vals) - 1, int(q * (len(sorted_vals) - 1) + 0.5))
    return sorted_vals[i]


def score(pools: dict[str, list[Order]], truth: list[TrueMatch],
          ladder: Sequence[int] | Sequence[Sequence[int]], mode: str,
          amount_filter: bool) -> Row:
    sizes = sorted(len(v) for v in pools.values())
    by_case: dict[str, list[int]] = {}
    reachable = total = 0
    for t in truth:
        ids = {o.order_id for o in pools.get(t.settlement_id, ())}
        hit = sum(1 for oid in t.order_ids if oid in ids)
        reachable += hit
        total += len(t.order_ids)
        slot = by_case.setdefault(t.case, [0, 0])
        slot[0] += hit
        slot[1] += len(t.order_ids)
    cases = {k: (v[0], v[1]) for k, v in by_case.items()}
    return Row(
        ladder=_rungs(ladder), mode=mode, amount_filter=amount_filter,
        p50=_percentile(sizes, 0.50), p90=_percentile(sizes, 0.90),
        pmax=sizes[-1] if sizes else 0,
        recall=reachable / total if total else 0.0,
        lost_pairs=total - reachable, total_pairs=total, by_case=cases,
        hurt=tuple(sorted(k for k, (h, n) in cases.items() if h < n)),
    )


def oracle_pools(ds: Dataset, ladder: Sequence[int] | Sequence[Sequence[int]], *,
                 amount_filter: bool, order: str) -> dict[str, list[Order]]:
    """Pools under perfect consumption, in a stated evaluation order.

    The true bundles are pairwise disjoint by construction, so consuming them
    can never remove an order another settlement needs. That makes this the
    upper bound on what consumption buys in pool size with the ceiling held
    fixed -- the live engine consumes *proven* sets instead, which can be wrong,
    and that difference is what the LIVE rows carry.
    """
    idx = StudyIndex(ds.orders, ladder, amount_filter=amount_filter, consumption=True)
    rung = len(idx.ladder) - 1
    truth_by_id = {t.settlement_id: t for t in ds.truth}
    if order == "easiest":
        # The engine's own order: cheapest tightest-rung pool first, so the
        # settlements most likely to be decidable free their orders earliest.
        seq = sorted(ds.settlements, key=lambda s: (len(idx.pool(s, 0)), s.settlement_id))
    else:
        seq = sorted(ds.settlements, key=lambda s: (s.settled_on, s.settlement_id))

    out: dict[str, list[Order]] = {}
    for s in seq:
        out[s.settlement_id] = idx.pool(s, rung)
        t = truth_by_id.get(s.settlement_id)
        if t is not None:
            idx.consume(t.order_ids)
    return out


def ladders() -> list[tuple[int, ...]]:
    """Every non-empty subset of `SWEEP_LAGS`.

    Order within a ladder changes only *when* a rung is paid, never which orders
    the terminal rung offers, so the STATIC and ORACLE sweeps are over sets. The
    LIVE sweep, where order decides escalation cost, uses ascending ladders
    because a non-monotone ladder would make `PoolIndex.pool`'s stated
    "escalation is monotone" guarantee false.
    """
    out: list[tuple[int, ...]] = []
    for k in range(1, len(SWEEP_LAGS) + 1):
        out.extend(combinations(SWEEP_LAGS, k))
    return out


# --------------------------------------------------------------------------
# Chargeback probe
# --------------------------------------------------------------------------


def _business_lag(start: date, end: date) -> int:
    day, moved = start, 0
    while day < end:
        day += timedelta(days=1)
        if day.weekday() < 5:
            moved += 1
    return moved


@dataclass(frozen=True)
class Reversal:
    settlement_id: str
    lag: int
    """Business days from the reversing order's capture to the payout date."""
    reversal_net: int
    credit: int
    bundle_net: int


def reversals(ds: Dataset) -> list[Reversal]:
    """Locate each `chargeback_reversal` settlement's off-window order.

    Identified structurally, not by reading the generator's intent: the family's
    credit is `sum(bundle) - reversing_order.net`, so the reversal is the order
    outside the bundle whose net closes that gap exactly.
    """
    by_id = {o.order_id: o for o in ds.orders}
    bundled = {oid for t in ds.truth for oid in t.order_ids}
    settle_by_id = {s.settlement_id: s for s in ds.settlements}
    loose_by_net: dict[int, list[Order]] = {}
    for o in ds.orders:
        if o.order_id not in bundled:
            loose_by_net.setdefault(o.net, []).append(o)

    out: list[Reversal] = []
    for t in ds.truth:
        if t.case != "chargeback_reversal":
            continue
        s = settle_by_id[t.settlement_id]
        bundle_net = sum(by_id[oid].net for oid in t.order_ids)
        gap = bundle_net - s.net_paise
        hit = next((o for o in loose_by_net.get(gap, ())
                    if o.captured_on < s.settled_on), None)
        if hit is None:
            continue
        out.append(Reversal(t.settlement_id, _business_lag(hit.captured_on, s.settled_on),
                            hit.net, s.net_paise, bundle_net))
    return out


# --------------------------------------------------------------------------
# Report
# --------------------------------------------------------------------------


def _fmt_ladder(rungs: tuple[Rung, ...]) -> str:
    return " > ".join("+".join(str(x) for x in r) for r in rungs)


def _table(rows: Iterable[Row]) -> list[str]:
    out = ["| ladder | p50 | p90 | max | ceiling | lost pairs | families losing pairs |",
           "|---|---:|---:|---:|---:|---:|---|"]
    for r in rows:
        hurt = ", ".join(r.hurt) if r.hurt else "--"
        mark = " **" if r.ladder == _rungs(LAG_LADDER) else ""
        name = f"`{_fmt_ladder(r.ladder)}`{mark}"
        out.append(f"| {name} | {r.p50} | {r.p90} | {r.pmax} | {r.recall:.4f} "
                   f"| {r.lost_pairs} | {hurt} |")
    return out


@dataclass(frozen=True)
class LiveRow:
    ladder: tuple[Rung, ...]
    amount_filter: bool
    consumption: bool
    span: int
    rep: Report
    verdicts: dict[str, int]
    p50: int
    p90: int
    pmax: int
    seconds: float
    chargeback_exact: tuple[int, int]
    false_proofs: tuple[tuple[str, str, bool], ...] = ()
    """(settlement_id, hazard, true-bundle-was-inside-the-pool) for every posted
    entry that did not equal the truth. The third field is the whole point of
    this study: True means blocking was innocent and the engine had the right
    answer available; False means blocking pruned the truth and the engine then
    proved a substitute."""


def live(ds: Dataset, ladder: Sequence[int] | Sequence[Sequence[int]], *,
         amount_filter: bool = True,
         consumption: bool = True, span: int = DEFAULT_SPAN) -> LiveRow:
    import contextlib
    import io
    from collections import Counter

    # `pipeline.run`'s propagation line goes to stdout; the sweep prints its own
    # table and one line per configuration would drown it.
    with contextlib.redirect_stdout(io.StringIO()), Timer() as t:
        preds, pools, findings = study_run(ds.settlements, ds.orders, ladder,
                                           amount_filter=amount_filter,
                                           consumption=consumption, span=span)
    rep = evaluate(ds.settlements, ds.truth, preds, pools, t.elapsed)
    sizes = sorted(len(v) for v in pools.values())
    cb = rep.by_case.get("chargeback_reversal", (0, 0))

    truth_by_id = {t_.settlement_id: t_ for t_ in ds.truth}
    bad: list[tuple[str, str, bool]] = []
    for p in preds:
        if p.order_ids is None:
            continue
        t_ = truth_by_id[p.settlement_id]
        if set(p.order_ids) == set(t_.order_ids):
            continue
        ids = {o.order_id for o in pools.get(p.settlement_id, ())}
        bad.append((p.settlement_id, t_.case, all(o in ids for o in t_.order_ids)))

    return LiveRow(
        ladder=_rungs(ladder), amount_filter=amount_filter, consumption=consumption,
        span=span,
        rep=rep, verdicts=dict(Counter(f.verdict.value for f in findings)),
        p50=_percentile(sizes, 0.50), p90=_percentile(sizes, 0.90),
        pmax=sizes[-1] if sizes else 0, seconds=t.elapsed, chargeback_exact=cb,
        false_proofs=tuple(bad),
    )
