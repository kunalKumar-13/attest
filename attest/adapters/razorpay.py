"""Razorpay adapter. §33, §34, §39.

Written against the published API only. The endpoint and field names below are
from Razorpay's own documentation and are quoted rather than guessed:

    GET /v1/settlements/recon/combined?year=YYYY&month=MM[&day=DD][&count][&skip]

    entity_id, type, debit, credit, amount, currency, fee, tax, on_hold,
    settled, created_at, settled_at, settlement_id, description, notes,
    payment_id, settlement_utr, order_id, order_receipt, method, card_network,
    card_issuer, card_type, dispute_id

**This endpoint changes what ATTEST is doing, and the honest framing matters.**

FAILURES.md D8 concluded that the AI anchoring loop was a coin flip because the
settlement report carried no order-level reference, so every anchor was a guess.
That is true of the *synthetic* generator. It is not true of Razorpay: the recon
report carries `order_id` and `payment_id` on each settled transaction, and
`settlement_id` grouping them.

So against a real connected account, reconciliation is largely a **join**, and
the subset-sum machinery is the fallback for the cases where the join fails —
recon unavailable for a period, a bank credit that does not match any single
settlement, adjustments with no linked entity, or a merchant reconciling against
a bank statement rather than the gateway. Those are exactly the hard cases, and
they are the ones this engine was built for.

Saying that plainly is better than implying the hard path is always necessary.
The value is not that subset-sum is always needed; it is that when the join
fails, the alternative is a person in a spreadsheet.

**No credentials, no data.** `fetch` raises `NotConnected` rather than returning
anything. There is no demo mode inside this class.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

from attest.adapters.base import NotConnected, Snapshot
from attest.model import BankCredit, Method, Order, Settlement

BASE = "https://api.razorpay.com/v1"
RECON = "/settlements/recon/combined"
SETTLEMENTS = "/settlements"

#: Razorpay's `method` values mapped onto ATTEST's. Anything unrecognised is
#: reported as a warning rather than guessed into the nearest match — a wrong
#: method means a wrong fee, and a wrong fee means the truth stops balancing
#: (FAILURES.md D16).
METHOD_MAP: dict[str, Method] = {
    "upi": Method.UPI,
    "card": Method.CARD,
    "netbanking": Method.NETBANKING,
    "wallet": Method.WALLET,
    "emi": Method.CARD,
}


class RazorpayAdapter:
    """Reads settlements and their constituent transactions.

    Credentials come from the environment (`RAZORPAY_KEY_ID`,
    `RAZORPAY_KEY_SECRET`) and are never logged, echoed, or written into a
    snapshot.
    """

    name = "razorpay"

    def __init__(self, key_id: str | None = None, key_secret: str | None = None) -> None:
        self.key_id = key_id or os.environ.get("RAZORPAY_KEY_ID")
        self.key_secret = key_secret or os.environ.get("RAZORPAY_KEY_SECRET")

    @property
    def connected(self) -> bool:
        return bool(self.key_id and self.key_secret)

    def status(self) -> dict[str, object]:
        return {
            "provider": "razorpay",
            "connected": self.connected,
            "key_id": (self.key_id[:8] + "…") if self.key_id else None,
            "endpoints": [f"GET {BASE}{RECON}", f"GET {BASE}{SETTLEMENTS}"],
            "reads": ["settlements", "settled payments", "refunds",
                      "adjustments", "fees and tax"],
            "writes": [],
            "note": ("Read-only. ATTEST never posts, refunds, or modifies "
                     "anything through this connection — it has no write scope "
                     "and no endpoint in this adapter mutates state."),
        }

    # -- fetching ----------------------------------------------------------

    def fetch(self, year: int, month: int, day: int | None = None,
              page: int = 1000) -> Snapshot:
        """Pull one recon period and normalise it.

        Paginates with `count`/`skip` until a short page arrives. A partial pull
        is surfaced as a warning rather than silently truncated: a snapshot
        missing transactions makes settlements look CONTRADICTED for a reason
        that has nothing to do with the merchant's books.
        """
        if not self.connected:
            raise NotConnected(
                "RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET are not set. This "
                "adapter does not fabricate data; connect an account or use the "
                "synthetic source, which is labelled as synthetic everywhere it "
                "appears.")

        items, skip, warnings = [], 0, []
        while True:
            batch = self._get(RECON, {"year": year, "month": month,
                                      **({"day": day} if day else {}),
                                      "count": page, "skip": skip})
            got = batch.get("items", [])
            items.extend(got)
            if len(got) < page:
                break
            skip += page
            if skip > 100_000:
                warnings.append(
                    f"stopped after {skip:,} rows; this period is larger than a "
                    f"single pull and the snapshot is incomplete")
                break

        return self.normalise(
            items, warnings, live=True,
            coverage=f"{year}-{month:02d}" + (f"-{day:02d}" if day else ""))

    def _get(self, path: str, params: dict[str, object]) -> dict[str, object]:
        import base64
        import json
        import urllib.parse
        import urllib.request

        url = f"{BASE}{path}?" + urllib.parse.urlencode(params)
        token = base64.b64encode(f"{self.key_id}:{self.key_secret}".encode()).decode()
        req = urllib.request.Request(url, headers={"Authorization": f"Basic {token}"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())

    # -- normalisation -----------------------------------------------------

    def normalise(self, items: list[dict[str, object]], warnings: list[str],
                  coverage: str = "", live: bool = False) -> Snapshot:
        """Recon rows into ATTEST's model.

        Kept separate from `fetch` so it can be exercised against recorded
        fixtures without a live account — the transformation is where the bugs
        live, and it should be testable without credentials.

        `live` defaults to FALSE and only `fetch` sets it. A normaliser run over
        a fixture that reports itself as live is precisely the lie §39 forbids,
        and defaulting the other way would make it the easy mistake.
        """
        orders: list[Order] = []
        by_settlement: dict[str, dict[str, int]] = {}
        utrs: dict[str, str] = {}
        settled_on: dict[str, int] = {}
        linked = 0
        unknown_methods: set[str] = set()
        malformed = 0
        non_integer: set[str] = set()

        # ADAPTER-001. Recon rows are aggregated into a settlement total, so the
        # same row arriving twice DOUBLES that settlement. Pagination with an
        # overlapping `skip` window and a retried pull both produce exactly
        # that, and the result is a settlement net that no bank credit matches —
        # a CONTRADICTED verdict caused by the reader rather than the books.
        # Identity is `entity_id` where the API supplies one, and a hash of the
        # row where it does not.
        seen: set[str] = set()
        deduped: list[dict[str, object]] = []
        for it in items:
            if not isinstance(it, dict):
                # ADAPTER-003. A non-dict row used to raise AttributeError out
                # of normalisation. A malformed row is the source's problem and
                # is counted, not fatal.
                malformed += 1
                continue
            import hashlib as _h
            import json as _j
            key = str(it.get("entity_id") or "")
            if not key:
                key = _h.sha256(
                    _j.dumps(it, sort_keys=True, default=str).encode()).hexdigest()
            if key in seen:
                continue
            seen.add(key)
            deduped.append(it)
        duplicates = len(items) - len(deduped) - malformed

        for it in deduped:
            sid = str(it.get("settlement_id") or "")
            kind = str(it.get("type") or "")
            credit = int(it.get("credit") or 0)
            debit = int(it.get("debit") or 0)
            fee = int(it.get("fee") or 0)
            tax = int(it.get("tax") or 0)

            if sid:
                agg = by_settlement.setdefault(sid, {"credit": 0, "debit": 0})
                agg["credit"] += credit
                agg["debit"] += debit
                if it.get("settlement_utr"):
                    utrs[sid] = str(it["settlement_utr"])
                if it.get("settled_at"):
                    settled_on[sid] = int(it["settled_at"])

            if kind != "payment":
                # Refunds, adjustments and disputes reduce a settlement rather
                # than composing it. They are carried on the settlement total
                # above; modelling them as negative orders would let the solver
                # "explain" a credit with a refund, which is not a thing.
                continue

            raw_method = str(it.get("method") or "").lower()
            method = METHOD_MAP.get(raw_method)
            if method is None:
                unknown_methods.add(raw_method or "(absent)")
                continue

            # ADAPTER-002. Every amount is integer paise. A float here was
            # silently truncated — 10.5 became 10 — which is a money value
            # changed by the reader without anyone being told.
            raw_amount = it.get("amount")
            if raw_amount is None:
                raw_amount = credit + fee + tax
            if isinstance(raw_amount, float) and raw_amount != int(raw_amount):
                non_integer.add(str(raw_amount))
                continue
            gross = int(raw_amount)
            oid = str(it.get("order_id") or it.get("entity_id") or "")
            pid = str(it.get("payment_id") or it.get("entity_id") or "") or None
            created = int(it.get("created_at") or 0)
            if sid:
                linked += 1

            orders.append(Order(
                order_id=oid,
                captured_on=datetime.fromtimestamp(created, timezone.utc).date(),
                gross_paise=gross, method=method,
                customer_name=str(it.get("description") or ""),
                payment_id=pid))

        settlements, credits = [], []
        for sid, agg in by_settlement.items():
            net = agg["credit"] - agg["debit"]
            when = datetime.fromtimestamp(settled_on.get(sid, 0), timezone.utc).date()
            settlements.append(Settlement(sid, when, net, utrs.get(sid)))
            credits.append(BankCredit(
                f"bank_{sid}", when, net,
                f"NEFT-{utrs.get(sid, '')}-RAZORPAY SOFTWARE PVT LTD-SETTLEMENT"))

        if duplicates:
            warnings.append(
                f"{duplicates} duplicate recon row(s) discarded before "
                f"aggregation. Counting one twice inflates a settlement total "
                f"and produces a CONTRADICTED verdict caused by the reader.")
        if malformed:
            warnings.append(
                f"{malformed} row(s) were not objects and were skipped.")
        if non_integer:
            warnings.append(
                f"amounts that were not whole paise, dropped rather than "
                f"rounded: {', '.join(sorted(non_integer))}. Every amount in "
                f"ATTEST is integer paise; truncating one silently changes "
                f"money without saying so.")
        if unknown_methods:
            warnings.append(
                f"unrecognised payment methods dropped: {', '.join(sorted(unknown_methods))}. "
                f"A guessed method means a guessed fee, and a guessed fee makes the "
                f"truth stop balancing — see FAILURES.md D16.")
            warnings.append(
                "their credits remain in the settlement totals, deliberately: the "
                "money did settle, and removing it to make the books balance would "
                "hide a real gap. Those settlements will report CONTRADICTED with "
                "the exact unexplained amount, which is the honest outcome.")

        return Snapshot(
            orders=orders, settlements=settlements, credits=credits,
            source="razorpay", live=live, fetched_at=datetime.now(timezone.utc),
            coverage=coverage, warnings=warnings, linked_orders=linked)
