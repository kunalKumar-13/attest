"""Phase 12 · G-1. Money an operator reads is money in rupees.

exceptions.py's own docstring promises "Six orders explain all but ₹680.74".
policy._rs() argues the case: money that has to be converted before it can be
judged is money that will be misjudged. These pin that promise to the strings
the product actually paints.

A tolerance of ±31 paise is deliberately exempt: sub-rupee is the honest unit
for a tolerance, and ₹0.31 would read worse.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from attest.exceptions import classify
from attest.generate.generator import build as build_dataset
from attest.graph import build as build_graph
from attest.pipeline import run
from attest.searchspace import amount_ceiling

SEED, N = 20260821, 250

# an integer of 4+ digits immediately before the word "paise"
BARE_PAISE = re.compile(r"\b\d{4,}\s+paise\b")
# ...or a bare 4+ digit integer where money is being narrated
BARE_INT_MONEY = re.compile(
    r"\b(?:explain|explains|totalling|worth|reaches only|credit of|of)\s+\d{4,}\b")


def _offending(text: str) -> list[str]:
    return BARE_PAISE.findall(text) + BARE_INT_MONEY.findall(text)


@pytest.fixture(scope="module")
def demo():
    ds = build_dataset(N, seed=SEED)
    _, pools, findings = run(ds.settlements, ds.orders)
    sett = {s.settlement_id: s for s in ds.settlements}
    orders = {o.order_id: o for o in ds.orders}
    excs = {}
    for i, f in enumerate(findings):
        e = classify(f, sett[f.settlement_id], list(pools.get(f.settlement_id, ())), i)
        if e is not None:
            excs[f.settlement_id] = e
    return {"findings": {f.settlement_id: f for f in findings}, "sett": sett,
            "orders": orders, "excs": excs}


def test_exception_evidence_never_narrates_bare_paise(demo):
    """Every string a person reads in an exception is rupee-formatted."""
    bad: list[tuple[str, str]] = []
    for sid, exc in demo["excs"].items():
        for line in (*exc.established, exc.next_step, exc.missing):
            if _offending(line):
                bad.append((sid, line))
    assert not bad, "bare paise reached operator text:\n" + "\n".join(
        f"  {sid}: {line}" for sid, line in bad[:8])


def test_contradicted_case_states_both_amounts_in_rupees(demo):
    """setl_000109 is the case a stranger is asked to read in Phase 12 Part 9.

    It must not say "4 orders explain 586898 paise of 631603".
    """
    exc = demo["excs"].get("setl_000109")
    assert exc is not None, "setl_000109 is expected to be an exception"
    joined = " ".join(exc.established)
    assert not _offending(joined), f"bare paise in contradicted evidence: {joined}"
    assert "₹" in joined, f"no rupee amount in contradicted evidence: {joined}"


def test_search_space_reduction_reasons_are_rupee_formatted():
    r = amount_ceiling(removed=3, credit_paise=11613)
    assert not _offending(r.justification), r.justification
    assert "₹116.13" in r.justification, r.justification


def test_graph_edge_labels_are_rupee_formatted(demo):
    """The evidence graph labels every order edge with its net."""
    bad = []
    for sid in ("setl_000089", "setl_000109", "setl_000020"):
        f = demo["findings"].get(sid)
        if f is None:
            continue
        g = build_graph(f, demo["sett"][sid], demo["orders"])
        for e in g.edges:
            if _offending(e.why or ""):
                bad.append((sid, e.why))
    assert not bad, "bare paise on graph edges:\n" + "\n".join(
        f"  {s}: {l}" for s, l in bad[:8])


def test_tolerance_stays_in_paise(demo):
    """The exemption is deliberate — pin it so nobody "fixes" it later."""
    seen = [line for exc in demo["excs"].values() for line in exc.established
            if "tolerance" in line or "±" in line]
    assert any(re.search(r"±\d+ paise", s) for s in seen), \
        f"tolerance should still be expressed in paise, saw: {seen[:4]}"
