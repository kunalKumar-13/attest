"""Ask ATTEST — natural language to a deterministic query. §24, §25, §33, §34.

This is where the model is allowed to work, and the reason it is allowed is that
it never touches an answer. It translates a question into a **structured query**;
the query runs against the run's own records; the numbers come back from the
data. So the worst a bad translation can do is answer the wrong question, which a
reader can see. It cannot invent a figure, because no part of the path that
produces figures has a model in it.

    question  ->  intent (model or rules)  ->  Query  ->  executed on records
                                                              |
                                                          Answer + evidence

The same division as `hypothesis.py`, for the same reason. There it was: the
model proposes an anchor, the solver decides. Here it is: the model proposes a
query, the data decides.

**Every claim carries its evidence.** A statement with no settlement ids behind
it is not allowed to render, because "reconciliation fell 2.1 points" is a thing
a language model can produce whether or not it happened. Attaching the specific
rows makes the claim checkable, and unfalsifiable statements are precisely what
this project exists to refuse.

The parser here is deterministic. It handles the question shapes a finance team
actually asks, it runs with no key and no network, and it is what the tests use.
Swapping in a model means replacing `parse` alone — nothing downstream knows or
cares, and nothing downstream trusts it any more than it trusts this one.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from attest.verdict import Verdict

#: Recognised without a model. Ordered by specificity — the first match wins, so
#: narrower patterns must come first.
SUGGESTIONS = [
    "why is setl_000089 unresolved",
    "show high value ambiguous settlements",
    "which settlements are unsafe to auto-post",
    "show unexplained amounts above 1000",
    "what is settled but not proven",
    "which settlements would post at a review cost of 500",
    "show contradicted settlements",
]


@dataclass
class Query:
    """A question, reduced to something the records can answer."""

    kind: str = "list"
    verdicts: set[str] = field(default_factory=set)
    settlement_id: str | None = None
    min_amount_paise: int = 0
    min_unexplained_paise: int = 0
    reasons: set[str] = field(default_factory=set)
    postable: bool | None = None
    limit: int = 25
    review_paise: int | None = None
    raw: str = ""

    def to_json(self) -> dict[str, Any]:
        return {"kind": self.kind, "verdicts": sorted(self.verdicts),
                "settlement_id": self.settlement_id,
                "min_amount_paise": self.min_amount_paise,
                "min_unexplained_paise": self.min_unexplained_paise,
                "reasons": sorted(self.reasons), "postable": self.postable,
                "review_paise": self.review_paise, "limit": self.limit}


@dataclass
class Fact:
    """One claim, and the rows that make it checkable."""

    text: str
    settlement_ids: tuple[str, ...] = ()
    amount_paise: int | None = None


@dataclass
class Answer:
    headline: str
    query: Query
    facts: list[Fact] = field(default_factory=list)
    rows: list[str] = field(default_factory=list)
    understood: bool = True

    def to_json(self) -> dict[str, Any]:
        return {"headline": self.headline, "understood": self.understood,
                "query": self.query.to_json(), "rows": self.rows,
                "facts": [{"text": f.text, "settlement_ids": list(f.settlement_ids),
                           "amount_paise": f.amount_paise} for f in self.facts]}


_MONEY = re.compile(r"(?:rs\.?|₹)?\s*([\d,]+(?:\.\d+)?)\s*(k|lakh|l|cr|crore)?",
                    re.I)


def _amount(text: str) -> int | None:
    """Read a rupee figure and return paise. Indian units, because the questions
    are asked in them: '2 lakh' is not 2,00,000 paise."""
    m = _MONEY.search(text)
    if not m:
        return None
    n = float(m.group(1).replace(",", ""))
    unit = (m.group(2) or "").lower()
    mult = {"k": 1_000, "lakh": 1_00_000, "l": 1_00_000,
            "cr": 1_00_00_000, "crore": 1_00_00_000}.get(unit, 1)
    return int(n * mult * 100)


def parse(text: str) -> Query:
    """Reduce a question to a query. Deterministic; a model replaces only this."""
    t = text.lower().strip()
    q = Query(raw=text)

    sid = re.search(r"(setl_\d+)", t)
    if sid and ("why" in t or "explain" in t or "unresolved" in t):
        return Query(kind="explain", settlement_id=sid.group(1), raw=text)
    if sid:
        return Query(kind="explain", settlement_id=sid.group(1), raw=text)

    if "unsafe" in t or "not safe" in t or ("cannot" in t and "post" in t):
        q.kind, q.postable = "unsafe", False
        return q

    if "review cost" in t or "if review" in t:
        q.kind = "policy"
        q.review_paise = _amount(t) or 15_000
        return q

    if "settled" in t and ("not proven" in t or "dispute" in t):
        q.kind = "settled"
        return q

    if "changed" in t or "since yesterday" in t or "different" in t:
        q.kind = "changed"
        return q

    if "unexplained" in t or "shortfall" in t or "missing" in t:
        q.kind = "list"
        q.min_unexplained_paise = _amount(t) or 1
        return q

    for word, v in (("ambiguous", Verdict.AMBIGUOUS), ("contradicted", Verdict.CONTRADICTED),
                    ("proven", Verdict.PROVEN), ("insufficient", Verdict.INSUFFICIENT)):
        if word in t:
            q.verdicts.add(v.value)

    if "high value" in t or "large" in t or "biggest" in t or "above" in t:
        q.min_amount_paise = _amount(t) or 50_00_00  # ₹5,000 default
    if not q.verdicts and not q.min_amount_paise and not q.min_unexplained_paise:
        q.kind = "unknown"
    return q


def execute(q: Query, rows: list[dict[str, Any]], summary: dict[str, Any],
            detail_of=None) -> Answer:
    """Run the query against the run's own records. No model on this path."""
    rs = lambda p: f"₹{p / 100:,.2f}"

    if q.kind == "unknown":
        return Answer(
            "I did not understand that as a question about this run.", q,
            [Fact("Ask about a settlement by id, a verdict, an unexplained "
                  "amount, what is safe to auto-post, or what a different review "
                  "cost would change.")],
            understood=False)

    if q.kind == "explain":
        row = next((r for r in rows if r["id"] == q.settlement_id), None)
        if row is None:
            return Answer(f"{q.settlement_id} is not in this run.", q,
                          understood=False)
        d = detail_of(q.settlement_id) if detail_of else {}
        facts = [Fact(f"{row['id']} is {row['verdict']} at {rs(row['amount'])}.",
                      (row["id"],), row["amount"])]
        for r in (d.get("judgement") or {}).get("reasons", []):
            facts.append(Fact(r))
        ex = d.get("exception") or {}
        if ex.get("settled"):
            st = ex["settled"]
            facts.append(Fact(
                f"{len(st['order_ids'])} orders worth {rs(st['net_paise'])} appear "
                f"in every surviving explanation and are not in dispute; "
                f"{rs(st['disputed_paise'])} across {st['differing_orders']} orders is.",
                (row["id"],), st["net_paise"]))
        if ex.get("next_step"):
            facts.append(Fact(f"Next step — {ex['next_step']}", (row["id"],)))
        return Answer(f"Why {row['id']} is {row['verdict'].lower()}", q, facts,
                      [row["id"]])

    if q.kind == "unsafe":
        bad = [r for r in rows if r["verdict"] != "PROVEN"]
        total = sum(r["amount"] for r in bad)
        bad.sort(key=lambda r: -r["amount"])
        by = {}
        for r in bad:
            by[r["reason"]] = by.get(r["reason"], 0) + 1
        facts = [Fact(f"{len(bad)} of {len(rows)} settlements are not safe to "
                      f"auto-post, holding {rs(total)}.",
                      tuple(r["id"] for r in bad[:40]), total)]
        for reason, n in sorted(by.items(), key=lambda kv: -kv[1]):
            ids = tuple(r["id"] for r in bad if r["reason"] == reason)[:40]
            facts.append(Fact(f"{n} — {reason}", ids))
        return Answer("Settlements that may not post automatically", q, facts,
                      [r["id"] for r in bad[: q.limit]])

    if q.kind == "settled":
        s, dsp = summary.get("settled_paise", 0), summary.get("disputed_paise", 0)
        amb = [r for r in rows if r["verdict"] == "AMBIGUOUS"]
        share = s / (s + dsp) if (s + dsp) else 0
        return Answer("Settled but not proven", q, [
            Fact(f"{rs(s)} inside ambiguous settlements is agreed by every "
                 f"surviving explanation, against {rs(dsp)} genuinely in dispute "
                 f"— {share:.1%} of ambiguous value is not contested at all.",
                 tuple(r["id"] for r in amb[:40]), s),
            Fact(f"Across the whole run that is "
                 f"{(summary.get('money', {}).get('PROVEN', 0) + s) / max(summary.get('processed_paise', 1), 1):.1%} "
                 f"of processed value accounted for."),
        ], [r["id"] for r in sorted(amb, key=lambda r: -r["amount"])[: q.limit]])

    if q.kind == "policy":
        return Answer(
            f"What a review cost of {rs(q.review_paise or 0)} would change", q,
            [Fact("Open the policy simulator and move the review-cost slider to "
                  "this value; the whole portfolio is re-decided at that costing "
                  "and the frontier shows what it buys.")],
            [])

    if q.kind == "changed":
        return Answer("What changed between runs", q, [
            Fact("Run `python -m attest 250 --changed` to diff two runs. Every "
                 "transition is attributed to an input difference, and an order "
                 "is only named as a cause if an explanation actually cites it."),
        ], [])

    # generic list
    sel = [r for r in rows
           if (not q.verdicts or r["verdict"] in q.verdicts)
           and r["amount"] >= q.min_amount_paise
           and r.get("unexplained", 0) >= q.min_unexplained_paise]
    sel.sort(key=lambda r: -(r.get("unexplained") or r["amount"]))
    total = sum(r["amount"] for r in sel)
    unex = sum(r.get("unexplained", 0) for r in sel)
    facts = [Fact(f"{len(sel)} settlements match, holding {rs(total)}.",
                  tuple(r["id"] for r in sel[:40]), total)]
    if unex:
        facts.append(Fact(f"{rs(unex)} of that is unexplained — a stated "
                          f"shortfall, not a guess.",
                          tuple(r["id"] for r in sel[:40] if r.get("unexplained")),
                          unex))
    return Answer(q.raw.strip() or "Matching settlements", q, facts,
                  [r["id"] for r in sel[: q.limit]])
