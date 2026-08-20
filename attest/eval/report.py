"""The engine's output artifact.

A terminal table can report that 51 of 250 settlements were proven. It cannot
show what a proof *is*, and that is the only thing about ATTEST worth showing.
So the engine emits a listing, the way a compiler does: one self-contained file,
no assets, no network, openable from `file://`.

Three views, and the middle one sets the bar for the other two:

* **Summary** -- three counts, not a percentage bar. A percentage of a verdict
  is a category error: PROVEN is not 20% of the way to anything.
* **Proof** -- every intermediate value of one settlement's arithmetic, in the
  unit the model actually uses. The reader recomputes it and agrees or does not.
  Nothing on the page asks to be believed.
* **Exception** -- the competing explanations for an AMBIGUOUS settlement with
  the fields that separate them, and the `unsat_core` verbatim for a
  CONTRADICTED one.

**On the visual treatment of a decline.** 198 of 250 verdicts here are
AMBIGUOUS, so the exception view is the main view and not a footnote. It is
rendered in the same ink, the same weight and the same tone as a proof, and the
page carries no red, no icons and no apology. That is not decoration policy, it
is the argument: an engine that declines to guess is behaving correctly, and a
page that draws a decline as a failure has inverted its own thesis. For the same
reason verdict is never encoded in hue -- a warm/cool split across three
categories reads as good/bad no matter what the legend says, so the verdict is
carried by the word, which cannot be misread.
"""

from __future__ import annotations

import html
import sys
from pathlib import Path

from attest.blocking import LAG_LADDER, PoolIndex
from attest.eval.harness import Report
from attest.model import FEE_BPS, GST_BPS, Order, Settlement, fee_paise, tax_paise
from attest.subsetsum import MAX_ENUM, MAX_POOL, MAX_TARGET_PAISE
from attest.verdict import Finding, Proof, Verdict, check

#: Subset sums tracked before the bracket search gives up. A contradiction panel
#: that cannot afford the search says so rather than omitting the row.
REACH_CAP = 1 << 16

_LETTERS = "ABCDEFGH"


# --------------------------------------------------------------------------
# Money, formatted without ever leaving integers
# --------------------------------------------------------------------------


def _group_indian(n: int) -> str:
    """Digit grouping as an Indian finance team reads it: 53,02,701 not 5,302,701."""
    s = str(n)
    if len(s) <= 3:
        return s
    head, tail = s[:-3], s[-3:]
    parts = []
    while len(head) > 2:
        parts.insert(0, head[-2:])
        head = head[:-2]
    if head:
        parts.insert(0, head)
    return ",".join(parts) + "," + tail


def _rupees(paise: int) -> str:
    """Paise as rupees, by integer division. No float ever touches an amount."""
    sign = "-" if paise < 0 else ""
    p = abs(paise)
    return f"{sign}{_group_indian(p // 100)}.{p % 100:02d}"


def _signed_rupees(paise: int) -> str:
    return ("+" if paise > 0 else "") + _rupees(paise)


def _paise(n: int) -> str:
    """Signed integer paise. Only differences are signed; see `_paise_abs`."""
    if not n:
        return "0"
    return ("+" if n > 0 else "\u2212") + _group_indian(abs(n))


def _paise_abs(n: int) -> str:
    return _group_indian(n)


def _esc(s: object) -> str:
    return html.escape(str(s), quote=True)


def _pct(x: float) -> str:
    return f"{x * 100:.1f}%"


# --------------------------------------------------------------------------
# Derived facts about a finding. Nothing here consults ground truth: the page
# may only say what the engine could have said.
# --------------------------------------------------------------------------


def _members(proof: Proof, by_id: dict[str, Order]) -> list[Order]:
    return [by_id[oid] for oid in proof.order_ids]


def _common_orders(finding: Finding) -> frozenset[str]:
    if not finding.proofs:
        return frozenset()
    common = set(finding.proofs[0].order_ids)
    for p in finding.proofs[1:]:
        common &= set(p.order_ids)
    return frozenset(common)


def _pairwise_disjoint(finding: Finding) -> bool:
    seen: set[str] = set()
    for p in finding.proofs:
        ids = set(p.order_ids)
        if ids & seen:
            return False
        seen |= ids
    return True


def _nearest_reachable(nets: list[int], target: int) -> tuple[int | None, int | None]:
    """Achievable subset sums bracketing `target`.

    "No subset satisfies the amount constraint" is an assertion until the reader
    can see the hole. The two sums either side of the credit show the gap is real
    and how wide it is, which is a fact about the pool rather than about the
    solver that searched it.
    """
    ceiling = target + max(nets, default=0)
    reachable = {0}
    for net in nets:
        if net <= 0 or net > ceiling:
            continue
        grown = {r + net for r in reachable if r + net <= ceiling}
        reachable |= grown
        if len(reachable) > REACH_CAP:
            return None, None
    below = max((r for r in reachable if 0 < r <= target), default=None)
    above = min((r for r in reachable if r > target), default=None)
    return below, above


def _claimed(findings: list[Finding]) -> dict[str, str]:
    """order_id -> settlement_id, for orders cited by an accepted proof."""
    out: dict[str, str] = {}
    for f in findings:
        if f.postable:
            for oid in f.proofs[0].order_ids:
                out[oid] = f.settlement_id
    return out


# --------------------------------------------------------------------------
# Which settlements go on screen. Chosen by rule rather than pinned by id, so
# the featured panels stay honest if the data or the solver moves.
# --------------------------------------------------------------------------


def _clearest_proven(findings: list[Finding], by_id: dict[str, Order]) -> Finding | None:
    """The proof that exercises the most fee rates in the fewest rows.

    Distinct payment methods first because that is the claim under test -- two
    bundles of equal gross settle for different nets -- and a proof spanning all
    four rates demonstrates it where a single-method one cannot. Row count second
    because the panel exists to be recomputed by hand.
    """
    best: Finding | None = None
    best_key: tuple[int, int, str] | None = None
    for f in findings:
        if f.verdict is not Verdict.PROVEN or not f.proofs:
            continue
        p = f.proofs[0]
        methods = {by_id[oid].method for oid in p.order_ids}
        key = (-len(methods), len(p.order_ids), f.settlement_id)
        if best_key is None or key < best_key:
            best, best_key = f, key
    return best


def _sharpest_exception(findings: list[Finding]) -> Finding | None:
    """The ambiguity that is hardest to argue away.

    Exhaustive first: "there are exactly two explanations" is a stronger
    statement than "here are two of the ones we found". Disjoint next, because
    explanations sharing no order at all cannot be reconciled by preferring the
    overlap. Fewest explanations last -- two mutually exclusive stories is the
    whole point stated in the smallest number of rows.
    """
    best: Finding | None = None
    best_key: tuple[int, int, int, int, str] | None = None
    for f in findings:
        if f.verdict is not Verdict.AMBIGUOUS or len(f.proofs) < 2:
            continue
        key = (
            0 if f.exhaustive else 1,
            0 if _pairwise_disjoint(f) else 1,
            len(f.proofs),
            sum(len(p.order_ids) for p in f.proofs),
            f.settlement_id,
        )
        if best_key is None or key < best_key:
            best, best_key = f, key
    return best


def _first_contradiction(findings: list[Finding]) -> Finding | None:
    return next((f for f in findings if f.verdict is Verdict.CONTRADICTED), None)


# --------------------------------------------------------------------------
# Style. One accent, three inks, hairline rules, and a dark set chosen for the
# dark surface rather than flipped into it.
# --------------------------------------------------------------------------

CSS = """
:root{
  color-scheme: light dark;
  --bg:#fcfcfb; --panel:#ffffff; --ink:#0b0b0b; --ink-2:#52514e; --ink-3:#6b6961;
  --rule:#e4e2dc; --rule-2:#cfccc3; --accent:#1c5cab; --mark:#f4f2ec;
}
@media (prefers-color-scheme: dark){
  :root{
    --bg:#141413; --panel:#1a1a19; --ink:#ffffff; --ink-2:#c3c2b7; --ink-3:#8f8d83;
    --rule:#2e2e2b; --rule-2:#403f3b; --accent:#86b6ef; --mark:#232321;
  }
}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{
  margin:0 auto; padding:40px 24px 96px; max-width:1180px; background:var(--bg);
  color:var(--ink); font:15px/1.55 ui-sans-serif,-apple-system,"Segoe UI",Roboto,sans-serif;
}
.mono,td.n,th.n,pre,code{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  font-variant-numeric:tabular-nums}
a{color:var(--accent);text-decoration:none;border-bottom:1px solid transparent}
a:hover{border-bottom-color:var(--accent)}
h1{font-size:19px;font-weight:600;letter-spacing:.01em;margin:0}
h2{font-size:13px;font-weight:600;letter-spacing:.09em;text-transform:uppercase;
  color:var(--ink-2);margin:56px 0 14px;padding-bottom:8px;border-bottom:1px solid var(--rule-2)}
h3{font-size:14px;font-weight:600;margin:26px 0 8px}
p{margin:0 0 10px;max-width:78ch}
.sub{color:var(--ink-2)}
.dim{color:var(--ink-3)}
.tiny{font-size:12px}
header.doc{border-bottom:2px solid var(--ink);padding-bottom:14px;margin-bottom:8px}
header.doc .meta{margin-top:6px;font-size:12.5px;color:var(--ink-2)}
nav{font-size:12.5px;margin:14px 0 0;color:var(--ink-3)}
nav a{margin-right:18px}

/* Summary ---------------------------------------------------------------- */
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));
  gap:1px;background:var(--rule-2);border:1px solid var(--rule-2);margin:18px 0 8px}
.tile{background:var(--panel);padding:16px 18px}
.tile .k{font-size:11.5px;letter-spacing:.09em;text-transform:uppercase;color:var(--ink-2)}
.tile .v{font-size:30px;font-weight:600;letter-spacing:-.01em;margin-top:4px}
.tile .v small{font-size:14px;font-weight:400;color:var(--ink-2);letter-spacing:0}
.tile .d{margin-top:6px;font-size:12px;color:var(--ink-3);max-width:34ch}

/* Panels ----------------------------------------------------------------- */
.panel{background:var(--panel);border:1px solid var(--rule-2);padding:20px 22px;margin:16px 0}
.panel > .head{display:flex;flex-wrap:wrap;gap:8px 16px;align-items:baseline;
  padding-bottom:12px;margin-bottom:14px;border-bottom:1px solid var(--rule)}
.verdict{font-size:12px;font-weight:600;letter-spacing:.14em;text-transform:uppercase}
.sid{font-size:15px;font-weight:600}
.head .fact{font-size:12px;color:var(--ink-3);font-family:ui-monospace,Menlo,monospace}
.lede{color:var(--ink-2);font-size:14px}

/* Tables ----------------------------------------------------------------- */
.scroll{overflow-x:auto;margin:12px 0}
table{border-collapse:collapse;width:100%;font-size:13px}
th{text-align:left;font-weight:600;font-size:11px;letter-spacing:.07em;
  text-transform:uppercase;color:var(--ink-3);padding:0 10px 6px 0;
  border-bottom:1px solid var(--rule-2);white-space:nowrap}
td{padding:5px 10px 5px 0;border-bottom:1px solid var(--rule);white-space:nowrap}
th.n,td.n{text-align:right;padding-right:0}
th:last-child,td:last-child{padding-right:0}
tr.total td{border-top:1px solid var(--rule-2);border-bottom:none;font-weight:600;
  padding-top:8px}
tbody tr:last-child td{border-bottom:none}

/* The ledger: the part a reader recomputes ------------------------------- */
.ledger{margin:18px 0 6px;border-top:1px solid var(--rule-2)}
.ledger table{font-size:13.5px}
.ledger td{border-bottom:none;padding:3px 0}
.ledger td.lbl{width:100%;color:var(--ink-2);white-space:normal}
.ledger td.n{padding-left:24px}
.ledger tr.rule td{border-top:1px solid var(--rule-2);height:1px;padding:0}
.ledger tr.key td{font-weight:600;color:var(--ink)}
.rules{background:var(--mark);border:1px solid var(--rule);padding:12px 14px;
  font-size:12.5px;color:var(--ink-2);margin:12px 0}
.rules code{color:var(--ink);font-size:12.5px}
.rules ul{margin:8px 0 0;padding-left:18px}
.holds{margin-top:12px;font-size:13px}
.holds b{font-weight:600}
pre.core{background:var(--mark);border:1px solid var(--rule-2);padding:12px 14px;
  margin:10px 0;font-size:13px;white-space:pre-wrap;word-break:break-word;color:var(--ink)}

/* Competing explanations ------------------------------------------------- */
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(248px,1fr));gap:12px;
  margin:14px 0}
.card{border:1px solid var(--rule-2);padding:12px 14px;min-width:0}
.card .ch{display:flex;justify-content:space-between;align-items:baseline;
  padding-bottom:8px;margin-bottom:8px;border-bottom:1px solid var(--rule)}
.card .ch .lt{font-size:12px;font-weight:600;letter-spacing:.12em}
.card .ch .sz{font-size:11.5px;color:var(--ink-3)}
.card table{font-size:12px}
.card td{padding:3px 6px 3px 0}
.card .foot{margin-top:8px;font-size:11.5px;color:var(--ink-3);white-space:normal}
.shared td{color:var(--ink-3)}
.sep{border-top:1px solid var(--rule-2);margin-top:16px;padding-top:14px}
.sep h3{margin-top:0}
.sep ul{margin:8px 0 0;padding-left:18px;font-size:13.5px;color:var(--ink-2)}
.sep li{margin-bottom:5px;max-width:80ch}
.sep li b{color:var(--ink);font-weight:600}

/* Listing ---------------------------------------------------------------- */
details.row{border-bottom:1px solid var(--rule)}
details.row > summary{cursor:pointer;list-style:none;padding:7px 0;display:grid;
  grid-template-columns:126px 122px 132px 178px 1fr;gap:12px;align-items:baseline;
  font-size:13px}
details.row > summary::-webkit-details-marker{display:none}
details.row > summary:hover{background:var(--mark)}
details.row[open] > summary{font-weight:600}
summary .amt{text-align:right}
details.row > summary .verdict{letter-spacing:.06em;font-size:11px;color:var(--ink-2)}
summary .lay{color:var(--ink-3);font-size:12px;overflow:hidden;text-overflow:ellipsis}
details.row .panel{border-left:2px solid var(--rule-2);border-right:none;
  border-top:none;border-bottom:none;margin:4px 0 18px;padding:8px 0 8px 18px;
  background:transparent}
.legend{display:grid;grid-template-columns:126px 122px 132px 178px 1fr;gap:12px;
  font-size:11px;letter-spacing:.07em;text-transform:uppercase;color:var(--ink-3);
  padding-bottom:6px;border-bottom:1px solid var(--rule-2)}
.legend .amt{text-align:right}
footer{margin-top:64px;padding-top:16px;border-top:1px solid var(--rule);
  font-size:12px;color:var(--ink-3)}
@media (max-width:760px){
  details.row > summary,.legend{grid-template-columns:1fr 1fr;gap:4px 12px}
  summary .amt{text-align:left}
}
"""


# --------------------------------------------------------------------------
# Fragments
# --------------------------------------------------------------------------


def _order_rows(members: list[Order]) -> tuple[str, int, int, int, int]:
    """Per-order arithmetic, recomputed here from `attest.model` rather than read
    off the proof: a panel that copies the prover's own totals proves nothing."""
    rows: list[str] = []
    t_gross = t_fee = t_tax = t_net = 0
    for o in sorted(members, key=lambda x: -x.gross_paise):
        f = fee_paise(o.gross_paise, o.method)
        t = tax_paise(f)
        n = o.gross_paise - f - t
        t_gross += o.gross_paise
        t_fee += f
        t_tax += t
        t_net += n
        rows.append(
            f"<tr><td class='mono'>{_esc(o.order_id)}</td>"
            f"<td class='mono dim'>{o.captured_on.isoformat()}</td>"
            f"<td>{o.method.value}</td>"
            f"<td class='n mono'>{_rupees(o.gross_paise)}</td>"
            f"<td class='n mono dim'>{FEE_BPS[o.method]}</td>"
            f"<td class='n mono'>{_rupees(f)}</td>"
            f"<td class='n mono'>{_rupees(t)}</td>"
            f"<td class='n mono'>{_rupees(n)}</td></tr>"
        )
    return "".join(rows), t_gross, t_fee, t_tax, t_net


def _fee_rules() -> str:
    rates = " &middot; ".join(f"{m.value} {bps} bps" for m, bps in FEE_BPS.items())
    return (
        "<div class='rules'><b>To check this by hand</b>, per order:"
        "<ul>"
        f"<li><code>fee = round_half_up(gross &times; bps &divide; 10,000)</code> &nbsp; {rates}</li>"
        f"<li><code>GST = round_half_up(fee &times; {GST_BPS:,} &divide; 10,000)</code> "
        "&nbsp; 18% of the fee, never of the gross</li>"
        "<li><code>net = gross &minus; fee &minus; GST</code></li>"
        "</ul>"
        "<div style='margin-top:8px'>round_half_up sends a tie away from zero, which is what a "
        "gateway does and what neither <code>round</code> (ties to even) nor <code>int</code> "
        "(truncates) does. Every figure below is an exact integer number of paise; the rupee "
        "column is that integer divided by 100, not a decimal that was rounded to fit.</div></div>"
    )


def _ledger(net_sum: int, proof: Proof, settlement: Settlement, n_orders: int) -> str:
    expected = net_sum + proof.adjustment_paise
    residual = settlement.net_paise - expected
    tol = proof.tolerance_paise
    holds = abs(residual) <= tol
    adj_note = (
        "no linked refund or chargeback record, so the engine may not invent one"
        if proof.adjustment_paise == 0
        else "evidenced by a linked record"
    )
    body = (
        f"<tr><td class='lbl'>&Sigma; net of the {n_orders} orders above</td>"
        f"<td class='n mono'>{_rupees(net_sum)}</td>"
        f"<td class='n mono dim'>{_paise_abs(net_sum)} p</td></tr>"
        f"<tr><td class='lbl'>adjustment &mdash; {adj_note}</td>"
        f"<td class='n mono'>{_rupees(proof.adjustment_paise)}</td>"
        f"<td class='n mono dim'>{_paise(proof.adjustment_paise)} p</td></tr>"
    )
    body += "<tr class='rule'><td colspan='3'></td></tr>"
    body += (
        f"<tr class='key'><td class='lbl'>expected credit</td>"
        f"<td class='n mono'>{_rupees(expected)}</td>"
        f"<td class='n mono dim'>{_paise_abs(expected)} p</td></tr>"
        f"<tr class='key'><td class='lbl'>credit the gateway says it paid "
        f"&mdash; {_esc(settlement.settlement_id)}, {settlement.settled_on.isoformat()}</td>"
        f"<td class='n mono'>{_rupees(settlement.net_paise)}</td>"
        f"<td class='n mono dim'>{_paise_abs(settlement.net_paise)} p</td></tr>"
        "<tr class='rule'><td colspan='3'></td></tr>"
        f"<tr class='key'><td class='lbl'>residual = credit &minus; expected</td>"
        f"<td class='n mono'>{_signed_rupees(residual)}</td>"
        f"<td class='n mono dim'>{_paise(residual)} p</td></tr>"
        f"<tr><td class='lbl'>tolerance = 1 paisa &times; {n_orders} orders "
        "&mdash; fee and GST each round independently, so one order can drift one paisa</td>"
        f"<td class='n mono'>{_rupees(tol)}</td>"
        f"<td class='n mono dim'>{_group_indian(tol)} p</td></tr>"
    )
    verdict_line = (
        f"|residual| &le; tolerance &nbsp;&mdash;&nbsp; "
        f"{_group_indian(abs(residual))} &le; {_group_indian(tol)} paise"
        if holds
        else f"|residual| &gt; tolerance &nbsp;&mdash;&nbsp; "
        f"{_group_indian(abs(residual))} &gt; {_group_indian(tol)} paise"
    )
    return (
        f"<div class='ledger'><table><tbody>{body}</tbody></table></div>"
        f"<div class='holds mono'><b>{verdict_line}</b></div>"
    )


def _proof_panel(finding: Finding, settlement: Settlement, by_id: dict[str, Order],
                 *, full: bool = True) -> str:
    p = finding.proofs[0]
    members = _members(p, by_id)
    rows, t_gross, t_fee, t_tax, t_net = _order_rows(members)
    accepted = check(p, settlement, by_id)
    head = (
        "<div class='head'><span class='verdict'>PROVEN</span>"
        f"<span class='sid mono'>{_esc(finding.settlement_id)}</span>"
        f"<span class='fact'>{len(p.order_ids)} orders &middot; "
        f"credit {_rupees(settlement.net_paise)} &middot; "
        f"resolved by {_esc(finding.layer)}</span></div>"
    )
    lede = (
        "<p class='lede'>Exactly one subset of the candidate pool satisfies the amount "
        "constraint. Every intermediate value is below; recompute them and the claim stands "
        "or falls on its own.</p>"
        if full
        else ""
    )
    table = (
        "<div class='scroll'><table><thead><tr>"
        "<th>order</th><th>captured</th><th>method</th><th class='n'>gross &#8377;</th>"
        "<th class='n'>bps</th><th class='n'>fee &#8377;</th><th class='n'>GST &#8377;</th>"
        "<th class='n'>net &#8377;</th></tr></thead>"
        f"<tbody>{rows}</tbody>"
        f"<tfoot><tr class='total'><td colspan='3'>totals</td>"
        f"<td class='n mono'>{_rupees(t_gross)}</td><td></td>"
        f"<td class='n mono'>{_rupees(t_fee)}</td>"
        f"<td class='n mono'>{_rupees(t_tax)}</td>"
        f"<td class='n mono'>{_rupees(t_net)}</td></tr></tfoot></table></div>"
    )
    kernel = (
        "<p class='tiny dim' style='margin-top:14px'>"
        f"attest.verdict.check() re-derived this proof from the order records and "
        f"{'accepted' if accepted else 'REJECTED'} it. The kernel recomputes rather than "
        "reads: a prover that fabricated a total could not survive it. "
        f"Constraints carried: {_esc(', '.join(sorted(p.constraints)))}.</p>"
    )
    return (
        f"<section class='panel' id='{_esc(finding.settlement_id)}'>{head}{lede}"
        f"{_fee_rules() if full else ''}{table}"
        f"{_ledger(t_net, p, settlement, len(members))}{kernel}</section>"
    )


def _explanation_card(letter: str, proof: Proof, settlement: Settlement,
                      by_id: dict[str, Order], common: frozenset[str]) -> str:
    members = sorted(_members(proof, by_id), key=lambda o: -o.gross_paise)
    rows = "".join(
        f"<tr class='{'shared' if o.order_id in common else 'uniq'}'>"
        f"<td class='mono'>{_esc(o.order_id)}</td>"
        f"<td class='dim'>{o.method.value}</td>"
        f"<td class='n mono'>{_rupees(o.net)}</td></tr>"
        for o in members
    )
    residual = settlement.net_paise - (sum(o.net for o in members) + proof.adjustment_paise)
    no_ref = sum(1 for o in members if not o.payment_id)
    dates = sorted({o.captured_on.isoformat() for o in members})
    foot = (
        f"&Sigma; gross {_rupees(sum(o.gross_paise for o in members))} &middot; "
        f"fee+GST {_rupees(sum(o.gross_paise for o in members) - sum(o.net for o in members))}"
        f"<br>residual {_paise(residual)} p against a bound of {proof.tolerance_paise} p"
        f"<br>captured {', '.join(dates)}"
        + (f"<br>{no_ref} of {len(members)} without a gateway reference" if no_ref else "")
    )
    return (
        f"<div class='card'><div class='ch'><span class='lt'>{letter}</span>"
        f"<span class='sz'>{len(members)} orders</span></div>"
        f"<table><tbody>{rows}</tbody>"
        f"<tfoot><tr class='total'><td colspan='2'>&Sigma; net</td>"
        f"<td class='n mono'>{_rupees(sum(o.net for o in members))}</td></tr></tfoot></table>"
        f"<div class='foot'>{foot}</div></div>"
    )


def _separators(finding: Finding, settlement: Settlement,
                by_id: dict[str, Order]) -> str:
    """What a human would have to look at to decide.

    Every line below is a comparison of fields that are actually on the records.
    The engine does not rank the explanations and this panel does not hint at one:
    it states the difference and stops.
    """
    proofs = finding.proofs
    sets = [set(p.order_ids) for p in proofs]
    common = _common_orders(finding)
    items: list[str] = []

    if finding.exhaustive:
        items.append(
            f"<b>These are all of them.</b> The enumerator ran to completion, so there "
            f"are exactly {len(proofs)} subsets of this pool that satisfy the amount "
            "constraint &mdash; not the first few it happened to find."
        )
    else:
        items.append(
            f"<b>There may be more.</b> Enumeration stopped at the cap of {MAX_ENUM}, so "
            f"{len(proofs)} is a lower bound on the number of explanations. Nothing below "
            "is a claim about explanations that were never enumerated."
        )

    if common:
        claim = (
            "belong to this settlement whichever explanation is correct, because they "
            "appear in every one of them"
            if finding.exhaustive
            else "appear in every <em>enumerated</em> explanation, which is a fact about "
            "the sample and not yet a deduction"
        )
        items.append(
            "<b>Already determined:</b> "
            + ", ".join(f"<code>{_esc(o)}</code>" for o in sorted(common))
            + f" &mdash; {claim}."
        )
    elif len(proofs) > 1 and _pairwise_disjoint(finding):
        items.append(
            "<b>No order is common to any two explanations.</b> They are mutually "
            "exclusive accounts of the same rupees, so there is nothing to split the "
            "difference on."
        )

    grosses = {sum(by_id[o].gross_paise for o in s) for s in sets}
    if len(grosses) > 1:
        spread = max(grosses) - min(grosses)
        items.append(
            f"<b>They disagree about fees by {_rupees(spread)}.</b> Every explanation "
            f"reaches the same net &mdash; {_rupees(settlement.net_paise)} &mdash; from a "
            "different gross, so a payout advice carrying the fee and GST breakdown would "
            "decide this without any search at all."
        )

    method_sets = [{by_id[o].method.value for o in s} for s in sets]
    if len({frozenset(m) for m in method_sets}) > 1:
        items.append(
            "<b>Different payment methods:</b> "
            + " vs ".join(
                f"{_LETTERS[i]} {'/'.join(sorted(m))}" for i, m in enumerate(method_sets)
            )
            + " &mdash; so the method mix on the payout separates them."
        )

    # A one-order swap is the sharpest case: two explanations that differ by a
    # single pair of orders with the same net cannot be told apart by arithmetic
    # at all, and saying exactly which pair is more useful than saying "ambiguous".
    for i in range(len(sets)):
        for j in range(i + 1, len(sets)):
            only_i, only_j = sets[i] - sets[j], sets[j] - sets[i]
            if len(only_i) == 1 and len(only_j) == 1:
                a, b = by_id[next(iter(only_i))], by_id[next(iter(only_j))]
                same_net = "the same net to the paisa" if a.net == b.net else "different nets"
                items.append(
                    f"<b>{_LETTERS[i]} and {_LETTERS[j]} differ by one order.</b> "
                    f"<code>{_esc(a.order_id)}</code> ({a.customer_name}, "
                    f"ref {_esc(a.payment_id or 'absent')}) against "
                    f"<code>{_esc(b.order_id)}</code> ({b.customer_name}, "
                    f"ref {_esc(b.payment_id or 'absent')}), with {same_net} "
                    f"&mdash; {_rupees(a.net)} and {_rupees(b.net)}. "
                    "Only a reference or a name can separate these two; no amount of "
                    "solver time can."
                )

    missing_ref = [o for s in sets for o in s if not by_id[o].payment_id]
    if missing_ref:
        items.append(
            f"<b>{len(set(missing_ref))} of the cited orders carry no gateway reference</b> "
            "("
            + ", ".join(f"<code>{_esc(o)}</code>" for o in sorted(set(missing_ref)))
            + "), which is why they reached an amount-based search in the first place."
        )

    dates = {by_id[o].captured_on for s in sets for o in s}
    if len(dates) > 1:
        items.append(
            "<b>Capture dates in play:</b> "
            + ", ".join(d.isoformat() for d in sorted(dates))
            + f" &mdash; the settlement is dated {settlement.settled_on.isoformat()}, so a "
            "cut-off time on the payout would narrow the pool."
        )

    return (
        "<div class='sep'><h3>What separates them</h3><ul>"
        + "".join(f"<li>{x}</li>" for x in items)
        + "</ul></div>"
    )


def _ambiguous_panel(finding: Finding, settlement: Settlement,
                     by_id: dict[str, Order], *, full: bool = True) -> str:
    head = (
        "<div class='head'><span class='verdict'>AMBIGUOUS</span>"
        f"<span class='sid mono'>{_esc(finding.settlement_id)}</span>"
        f"<span class='fact'>{len(finding.proofs)} explanations"
        f"{'' if finding.exhaustive else ' so far'} &middot; "
        f"credit {_rupees(settlement.net_paise)} &middot; "
        f"{_esc(finding.layer)}</span></div>"
    )

    if not finding.proofs:
        # OutOfEnvelope: the instance was declined before any search ran. The
        # honest rendering says that, rather than implying explanations were
        # weighed and found equal.
        core = "\n".join(finding.unsat_core) or "(none recorded)"
        return (
            f"<section class='panel' id='{_esc(finding.settlement_id)}'>{head}"
            "<p class='lede'>Not attempted. The instance is larger than the Python "
            "reference implementation will decide, so the engine declined rather than "
            "approximate. No explanation was enumerated and none is claimed.</p>"
            f"<pre class='core'>{_esc(core)}</pre>"
            f"<p class='tiny dim'>Envelope: target &le; {_group_indian(MAX_TARGET_PAISE)} paise "
            f"({_rupees(MAX_TARGET_PAISE)}), pool &le; {MAX_POOL} orders. The counting DP is "
            "O(pool &times; target) over a dense array, so both bounds are memory-bandwidth "
            "limits of the reference, not properties of the settlement.</p></section>"
        )

    common = _common_orders(finding)
    cards = "".join(
        _explanation_card(_LETTERS[i], p, settlement, by_id, common)
        for i, p in enumerate(finding.proofs)
    )
    lede = (
        f"<p class='lede'>{len(finding.proofs)} distinct subsets of the candidate pool reach "
        f"this credit within tolerance. Arithmetic cannot choose between them, so the engine "
        "reports every one and posts none. This is the intended behaviour, not a failure to "
        "resolve: the alternative is picking one and moving money on it.</p>"
        if full
        else ""
    )
    return (
        f"<section class='panel' id='{_esc(finding.settlement_id)}'>{head}{lede}"
        f"<div class='cards'>{cards}</div>"
        f"{_separators(finding, settlement, by_id)}</section>"
    )


def _contradicted_panel(finding: Finding, settlement: Settlement,
                        by_id: dict[str, Order], orders: list[Order],
                        claimed: dict[str, str], *, full: bool = True) -> str:
    head = (
        "<div class='head'><span class='verdict'>CONTRADICTED</span>"
        f"<span class='sid mono'>{_esc(finding.settlement_id)}</span>"
        f"<span class='fact'>credit {_rupees(settlement.net_paise)} &middot; "
        f"{_esc(finding.layer)}</span></div>"
    )
    core = "\n".join(finding.unsat_core) or "(none recorded)"
    lede = (
        "<p class='lede'>No subset of the candidate pool reaches this credit at any window "
        "the engine is willing to open. Rather than widen a constraint until something fits, "
        "the engine reports which constraints cannot hold together and stops. The core below "
        "is the solver's, verbatim.</p>"
        if full
        else ""
    )

    index = PoolIndex(orders)
    widest = len(LAG_LADDER) - 1
    isolated = index.pool(settlement, widest)
    taken = [o for o in isolated if claimed.get(o.order_id) not in (None, finding.settlement_id)]
    survivors = [o for o in isolated if o.order_id not in claimed]
    below, above = _nearest_reachable([o.net for o in survivors], settlement.net_paise)

    rung_rows = "".join(
        f"<tr><td class='mono'>T+{lag} business days</td>"
        f"<td class='mono dim'>{', '.join(sorted(d.isoformat() for d in _dates(settlement, r)))}</td>"
        f"<td class='n mono'>{len(index.pool(settlement, r))}</td></tr>"
        for r, lag in enumerate(LAG_LADDER)
    )

    gap_rows = []
    tol_note = f"the widest bound any subset of this pool could claim is {len(survivors)} paise"
    if below is not None:
        gap_rows.append(("nearest reachable sum below the credit", below,
                         below - settlement.net_paise))
    if above is not None:
        gap_rows.append(("nearest reachable sum above the credit", above,
                         above - settlement.net_paise))
    gap = "".join(
        f"<tr><td class='lbl'>{lbl}</td><td class='n mono'>{_rupees(v)}</td>"
        f"<td class='n mono dim'>{_paise(d)} p</td></tr>"
        for lbl, v, d in gap_rows
    )
    gap_block = (
        "<h3>Where the amount axis has its hole</h3>"
        "<div class='ledger'><table><tbody>"
        f"<tr class='key'><td class='lbl'>credit to explain</td>"
        f"<td class='n mono'>{_rupees(settlement.net_paise)}</td>"
        f"<td class='n mono dim'>{_paise_abs(settlement.net_paise)} p</td></tr>"
        f"{gap}</tbody></table></div>"
        f"<p class='tiny dim' style='margin-top:8px'>Every achievable subset sum of the "
        f"{len(survivors)} remaining orders was enumerated; {tol_note}, and the nearest sums "
        "either side miss by more than that. The gap is a property of the amounts, not of how "
        "long the solver ran.</p>"
        if gap_rows
        else ""
    )

    return (
        f"<section class='panel' id='{_esc(finding.settlement_id)}'>{head}{lede}"
        "<h3>unsat core</h3>"
        f"<pre class='core'>{_esc(core)}</pre>"
        "<h3>What the engine had to work with</h3>"
        "<div class='scroll'><table><thead><tr><th>window tried</th><th>capture dates</th>"
        "<th class='n'>orders in window</th></tr></thead>"
        f"<tbody>{rung_rows}</tbody></table></div>"
        "<div class='ledger'><table><tbody>"
        f"<tr><td class='lbl'>orders captured on an eligible date, widest window</td>"
        f"<td class='n mono'>{len(isolated)}</td><td></td></tr>"
        f"<tr><td class='lbl'>&minus; already cited by another settlement's accepted proof"
        "</td>"
        f"<td class='n mono'>{len(taken)}</td><td></td></tr>"
        "<tr class='rule'><td colspan='3'></td></tr>"
        f"<tr class='key'><td class='lbl'>candidates actually available here</td>"
        f"<td class='n mono'>{len(survivors)}</td><td></td></tr>"
        "</tbody></table></div>"
        "<p class='tiny dim'>An order belongs to exactly one settlement, so proving an easier "
        "settlement removes its orders from this pool. That is sound deduction and it is also "
        "why this contradiction is stated against what remained, not against the whole file.</p>"
        f"{gap_block}"
        f"{_survivor_table(survivors) if full else ''}</section>"
    )


def _dates(settlement: Settlement, rung: int) -> set:
    from attest.blocking import _capture_dates_for

    days: set = set()
    for lag in LAG_LADDER[: rung + 1]:
        days |= _capture_dates_for(settlement.settled_on, lag)
    return days


def _survivor_table(survivors: list[Order]) -> str:
    if not survivors:
        return ""
    rows = "".join(
        f"<tr><td class='mono'>{_esc(o.order_id)}</td>"
        f"<td class='mono dim'>{o.captured_on.isoformat()}</td>"
        f"<td>{o.method.value}</td>"
        f"<td class='n mono'>{_rupees(o.gross_paise)}</td>"
        f"<td class='n mono'>{_rupees(o.net)}</td></tr>"
        for o in sorted(survivors, key=lambda x: -x.net)
    )
    return (
        "<h3>The candidates, so you can try</h3>"
        "<div class='scroll'><table><thead><tr><th>order</th><th>captured</th><th>method</th>"
        "<th class='n'>gross &#8377;</th><th class='n'>net &#8377;</th></tr></thead>"
        f"<tbody>{rows}</tbody></table></div>"
    )


def _panel(finding: Finding, settlement: Settlement, by_id: dict[str, Order],
           orders: list[Order], claimed: dict[str, str], *, full: bool) -> str:
    if finding.verdict is Verdict.PROVEN:
        return _proof_panel(finding, settlement, by_id, full=full)
    if finding.verdict is Verdict.AMBIGUOUS:
        return _ambiguous_panel(finding, settlement, by_id, full=full)
    return _contradicted_panel(finding, settlement, by_id, orders, claimed, full=full)


# --------------------------------------------------------------------------
# Views
# --------------------------------------------------------------------------


def _summary(findings: list[Finding], settlements: list[Settlement]) -> str:
    counts = {v: 0 for v in Verdict}
    for f in findings:
        counts[f.verdict] += 1
    rupees = sum(s.net_paise for s in settlements)

    definitions = {
        Verdict.PROVEN: "Exactly one assignment satisfies every constraint. "
                        "Re-derived by the kernel and safe to post.",
        Verdict.AMBIGUOUS: "Two or more assignments satisfy every constraint. "
                           "The engine reports them all and posts none.",
        Verdict.CONTRADICTED: "No assignment satisfies every constraint. "
                              "The engine reports which ones conflict.",
    }
    tiles = "".join(
        f"<div class='tile'><div class='k'>{v.value}</div>"
        f"<div class='v mono'>{counts[v]:,}<small> of {len(settlements):,}</small></div>"
        f"<div class='d'>{definitions[v]}</div></div>"
        for v in (Verdict.PROVEN, Verdict.AMBIGUOUS, Verdict.CONTRADICTED)
    )
    return (
        "<h2 id='summary'>Summary</h2>"
        "<div class='tiles'>"
        f"<div class='tile'><div class='k'>settlements</div>"
        f"<div class='v mono'>{len(settlements):,}</div>"
        "<div class='d'>Every payout in the file, each decided independently.</div></div>"
        f"<div class='tile'><div class='k'>rupees processed</div>"
        f"<div class='v mono'>{_rupees(rupees)}</div>"
        f"<div class='d'>{_group_indian(rupees)} paise, as integers. "
        "No amount in this run has been through a float.</div></div>"
        "</div>"
        f"<div class='tiles'>{tiles}</div>"
        "<p class='tiny dim' style='margin-top:12px;max-width:80ch'>Three counts, not a "
        "ratio. A verdict is a decidable property of the constraint system rather than a "
        "score, so there is no threshold here to tune and none of the three is a fraction of "
        "another. The engine emits no confidence number anywhere: a proof that needs one is "
        "not a proof.</p>"
    )


def _measurement(report: Report) -> str:
    rows = [
        ("settlements", f"{report.n_settlements:,}", ""),
        ("exact set match", f"{report.exact_sets:,}", _pct(report.set_accuracy)),
        ("declined to a human", f"{report.declined:,}",
         _pct(report.declined / report.n_settlements)),
        ("WRONG &mdash; would have moved money", f"{report.wrong:,}",
         _pct(report.wrong / report.n_settlements)),
        ("pair precision", f"{report.precision:.3f}", ""),
        ("pair recall", f"{report.recall:.3f}", ""),
        ("blocking recall &mdash; the ceiling layer 0 imposes",
         f"{report.blocking_recall:.3f}", ""),
        ("rupees explained", _rupees(report.rupees_explained),
         _pct(report.rupees_explained / report.rupees_total)),
        ("wall clock", f"{report.seconds:.2f}s", ""),
    ]
    body = "".join(
        f"<tr><td class='lbl'>{lbl}</td><td class='n mono'>{v}</td>"
        f"<td class='n mono dim'>{pct}</td></tr>"
        for lbl, v, pct in rows
    )
    layers = "".join(
        f"<tr><td class='mono'>{_esc(k)}</td><td class='n mono'>{n:,}</td>"
        f"<td class='n mono dim'>{_pct(n / report.n_settlements)}</td></tr>"
        for k, n in sorted(report.by_layer.items(), key=lambda kv: -kv[1])
    )
    cases = "".join(
        f"<tr><td class='mono'>{_esc(k)}</td><td class='n mono'>{n:,}</td>"
        f"<td class='n mono'>{hit:,}</td><td class='n mono dim'>{_pct(hit / n)}</td></tr>"
        for k, (hit, n) in sorted(report.by_case.items(), key=lambda kv: kv[1][0] / kv[1][1])
    )
    return (
        "<h2 id='measured'>Measured against ground truth</h2>"
        "<p class='sub'>Everything above is what the engine can say on its own. This section "
        "is the benchmark talking: the generator derived these settlements <em>from</em> "
        "orders, so the true membership of every one is known by construction and the engine "
        "never sees it. A declined settlement is counted as declined, not as a miss.</p>"
        f"<div class='ledger' style='max-width:640px'><table><tbody>{body}</tbody></table></div>"
        "<h3>Resolved by</h3>"
        "<div class='scroll'><table style='max-width:640px'><thead><tr><th>layer</th>"
        "<th class='n'>settlements</th><th class='n'>share</th></tr></thead>"
        f"<tbody>{layers}</tbody></table></div>"
        "<h3>Exact set match by hazard family</h3>"
        "<p class='tiny dim'>Failure attributed to a named cause rather than to a "
        "percentage. The hazard mix was frozen before the matcher was written.</p>"
        "<div class='scroll'><table style='max-width:640px'><thead><tr><th>hazard</th>"
        "<th class='n'>n</th><th class='n'>exact</th><th class='n'>share</th></tr></thead>"
        f"<tbody>{cases}</tbody></table></div>"
    )


def _listing(findings: list[Finding], by_settlement: dict[str, Settlement],
             by_id: dict[str, Order], orders: list[Order],
             claimed: dict[str, str]) -> str:
    rows: list[str] = []
    for f in sorted(findings, key=lambda x: x.settlement_id):
        s = by_settlement[f.settlement_id]
        if f.verdict is Verdict.PROVEN:
            note = f"{len(f.proofs[0].order_ids)} orders"
        elif f.proofs:
            note = (f"{len(f.proofs)} explanations"
                    f"{'' if f.exhaustive else ', enumeration capped'}")
        elif f.verdict is Verdict.AMBIGUOUS:
            note = "not attempted &mdash; out of envelope"
        else:
            note = "no explanation"
        rows.append(
            "<details class='row'><summary>"
            f"<span class='mono'>{_esc(f.settlement_id)}</span>"
            f"<span class='verdict'>{f.verdict.value}</span>"
            f"<span class='amt mono'>{_rupees(s.net_paise)}</span>"
            f"<span class='mono dim'>{note}</span>"
            f"<span class='lay mono'>{_esc(f.layer)}</span>"
            "</summary>"
            f"{_panel(f, s, by_id, orders, claimed, full=False)}"
            "</details>"
        )
    return (
        "<h2 id='all'>Every settlement</h2>"
        "<p class='sub'>The whole listing, in file order. Open a row for its arithmetic. "
        "Nothing is hidden behind a threshold and nothing was dropped for being "
        "inconvenient.</p>"
        "<div class='legend'><span>settlement</span><span>verdict</span>"
        "<span class='amt'>credit &#8377;</span><span>explanations</span><span>layer</span>"
        "</div>"
        + "".join(rows)
    )


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------


def render(report: Report, findings: list[Finding], settlements: list[Settlement],
           orders: list[Order]) -> str:
    by_id = {o.order_id: o for o in orders}
    by_settlement = {s.settlement_id: s for s in settlements}
    claimed = _claimed(findings)

    proven = _clearest_proven(findings, by_id)
    ambiguous = _sharpest_exception(findings)
    contradicted = _first_contradiction(findings)

    parts = [_summary(findings, settlements)]

    parts.append(
        "<h2 id='proof'>Proof &mdash; one settlement, checked by hand</h2>"
        "<p class='sub'>A proof is the point of the engine, so it is shown in full rather "
        "than summarised. Fees are deterministic, which is what turns "
        "<span class='mono'>credit &asymp; &Sigma; gross &minus; unknown fees</span> into "
        "<span class='mono'>credit = &Sigma; net &plusmn; rounding</span> &mdash; an equality "
        "a person can check with a calculator.</p>"
    )
    parts.append(
        _proof_panel(proven, by_settlement[proven.settlement_id], by_id)
        if proven
        else "<p class='sub'>No settlement was proven in this run.</p>"
    )

    parts.append(
        "<h2 id='ambiguous'>Exception &mdash; more than one explanation</h2>"
        "<p class='sub'>The largest class of outcome in this run, and the reason the engine "
        "exists in this shape. Two or more subsets of the pool reach the credit exactly; the "
        "engine puts them side by side with the fields that tell them apart and leaves the "
        "decision where the evidence is.</p>"
    )
    parts.append(
        _ambiguous_panel(ambiguous, by_settlement[ambiguous.settlement_id], by_id)
        if ambiguous
        else "<p class='sub'>No settlement was ambiguous in this run.</p>"
    )

    parts.append(
        "<h2 id='contradicted'>Exception &mdash; no explanation</h2>"
        "<p class='sub'>The constraints cannot all hold. The engine reports the core of the "
        "conflict instead of relaxing a bound until an answer appears, because a bound "
        "relaxed to produce an answer is no longer a bound.</p>"
    )
    parts.append(
        _contradicted_panel(contradicted, by_settlement[contradicted.settlement_id],
                            by_id, orders, claimed)
        if contradicted
        else "<p class='sub'>No settlement was contradicted in this run.</p>"
    )

    parts.append(_listing(findings, by_settlement, by_id, orders, claimed))
    parts.append(_measurement(report))

    nav = (
        "<nav><a href='#summary'>summary</a><a href='#proof'>proof</a>"
        "<a href='#ambiguous'>ambiguous</a><a href='#contradicted'>contradicted</a>"
        "<a href='#all'>all settlements</a><a href='#measured'>measurement</a></nav>"
    )
    head = (
        "<header class='doc'><h1>ATTEST &mdash; settlement reconciliation, with proofs</h1>"
        f"<div class='meta mono'>{len(settlements):,} settlements &middot; "
        f"{len(orders):,} orders &middot; "
        f"{_rupees(sum(s.net_paise for s in settlements))} processed &middot; "
        f"{report.seconds:.2f}s</div>"
        "<div class='meta'>Emitted by the engine itself. Self-contained: no scripts, no "
        "network, no external assets.</div>"
        f"{nav}</header>"
    )
    footer = (
        "<footer>Generated by <span class='mono'>attest.eval.report</span>. Amounts are "
        "integer paise throughout; the rupee column is that integer divided by 100. "
        "The three verdicts are computed properties of the constraint system, not scores, "
        "and none of them is an error state.</footer>"
    )
    return (
        "<!doctype html>\n<html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>ATTEST &middot; settlement report</title>"
        f"<style>{CSS}</style></head><body>{head}"
        + "".join(parts)
        + f"{footer}</body></html>\n"
    )


def main(argv: list[str]) -> int:
    # Deliberately no --holdout: AGENTS.md reserves seed 900913 for a single
    # execution on D7, and a reporting tool is not a reason to spend it.
    from attest.__main__ import SEED_TRAIN
    from attest.eval.harness import Timer, evaluate
    from attest.generate.generator import build
    from attest.pipeline import run

    n = int(argv[1]) if len(argv) > 1 else 250
    out = Path(argv[2]) if len(argv) > 2 else Path.cwd() / "report.html"

    ds = build(n, seed=SEED_TRAIN)
    with Timer() as t:
        preds, pools, findings = run(ds.settlements, ds.orders)
    rep = evaluate(ds.settlements, ds.truth, preds, pools, t.elapsed)

    out.write_text(render(rep, findings, ds.settlements, ds.orders), encoding="utf-8")
    print(f"{out}  ({out.stat().st_size / 1024:,.0f} KB, n={n}, seed={SEED_TRAIN})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
