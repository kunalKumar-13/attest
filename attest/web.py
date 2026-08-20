"""A local front end for the engine.

Stdlib only -- no framework, no build step, no dependencies beyond what the
engine already needs. `python -m attest.web` and open the page.

It exists because a reconciliation engine that only speaks in terminal tables
cannot answer the question its user actually has, which is never "what is your
exact-set match rate". It is **"how much of my money is accounted for, and what
happened to the rest".** So the page leads with rupees and lets you open any
settlement to see the arithmetic that justifies it.
"""

from __future__ import annotations

import csv
import io
import webbrowser
from datetime import date
from email.parser import BytesParser
from email.policy import default as email_policy
from http.server import BaseHTTPRequestHandler, HTTPServer

from attest.eval.harness import Timer, evaluate
from attest.eval.report import render
from attest.generate.generator import build
from attest.model import BankCredit, Method, Order, Settlement, TrueMatch
from attest.pipeline import run

PORT = 8420

_LANDING = """<!doctype html><html lang=en><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>ATTEST</title><style>
:root{--bg:#fbfaf8;--panel:#fff;--ink:#16150f;--dim:#6d685c;--line:#e4e0d6;--accent:#1a4f8a}
@media (prefers-color-scheme:dark){:root{--bg:#12120f;--panel:#1a1a16;--ink:#eceae2;
--dim:#9a958a;--line:#2c2b25;--accent:#7cb0e8}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);display:flex;min-height:100vh;
align-items:center;justify-content:center;padding:32px;
font:15px/1.6 ui-sans-serif,-apple-system,"Segoe UI",Inter,sans-serif}
.card{max-width:620px;width:100%}
h1{font-size:34px;margin:0 0 6px;letter-spacing:-.02em}
.tag{color:var(--dim);margin:0 0 30px}
.q{background:var(--panel);border:1px solid var(--line);border-left:3px solid var(--accent);
border-radius:8px;padding:18px 20px;margin-bottom:30px}
.q b{font-family:ui-monospace,Menlo,monospace;font-variant-numeric:tabular-nums}
.q p{margin:0 0 8px}.q p:last-child{margin:0;color:var(--dim);font-size:14px}
form{background:var(--panel);border:1px solid var(--line);border-radius:10px;
padding:22px;margin-bottom:14px}
h2{font-size:12px;text-transform:uppercase;letter-spacing:.09em;color:var(--dim);
margin:0 0 14px;font-weight:600}
label{display:block;font-size:13px;color:var(--dim);margin:12px 0 5px}
input[type=file],input[type=number]{width:100%;padding:9px;border:1px solid var(--line);
border-radius:6px;background:var(--bg);color:var(--ink);font:inherit;font-size:14px}
button{margin-top:18px;width:100%;padding:12px;border:0;border-radius:7px;
background:var(--accent);color:#fff;font:inherit;font-weight:600;font-size:15px;cursor:pointer}
button.ghost{background:transparent;color:var(--accent);border:1px solid var(--line)}
.note{color:var(--dim);font-size:13px;margin-top:18px;line-height:1.65}
code{font-family:ui-monospace,Menlo,monospace;font-size:12.5px}
</style></head><body><div class=card>
<h1>ATTEST</h1>
<p class=tag>Settlement reconciliation as constrained optimization</p>

<div class=q>
<p>One bank credit of <b>&#8377;47,382.19</b> lands. It is the net of some subset
of the 400 orders you captured that week &mdash; minus fees, minus GST on those
fees, offset by a refund, two days late.</p>
<p><strong>Which orders?</strong></p>
<p>Every proven answer here is arithmetic you can check by hand. Everything else
is declined, with a reason.</p>
</div>

<form method=post action=/reconcile>
<h2>Try it</h2>
<label>Portfolio size (settlements)</label>
<input type=number name=n value=250 min=10 max=2000>
<button type=submit>Reconcile a generated portfolio</button>
</form>

<form method=post action=/reconcile enctype=multipart/form-data>
<h2>Or use your own books</h2>
<label>orders.csv &mdash; <code>order_id, captured_on, gross_paise, method,
customer_name, payment_id</code></label>
<input type=file name=orders accept=.csv>
<label>settlements.csv &mdash; <code>settlement_id, settled_on, net_paise, utr</code></label>
<input type=file name=settlements accept=.csv>
<button class=ghost type=submit>Reconcile my files</button>
</form>

<p class=note>Everything runs locally. Nothing is uploaded anywhere &mdash; this
page is served by <code>python -m attest.web</code> on your own machine.</p>
</div></body></html>"""


def _parse_orders(text: str) -> list[Order]:
    out = []
    for r in csv.DictReader(io.StringIO(text)):
        out.append(Order(
            r["order_id"], date.fromisoformat(r["captured_on"]),
            int(r["gross_paise"]), Method(r["method"]),
            r.get("customer_name", ""), r.get("payment_id") or None))
    return out


def _parse_settlements(text: str) -> list[Settlement]:
    return [Settlement(r["settlement_id"], date.fromisoformat(r["settled_on"]),
                       int(r["net_paise"]), r.get("utr") or None)
            for r in csv.DictReader(io.StringIO(text))]


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a: object) -> None:  # keep the console clean
        pass

    def _send(self, body: str, code: int = 200) -> None:
        raw = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:
        self._send(_LANDING if self.path == "/" else "<h1>404</h1>", 
                   200 if self.path == "/" else 404)

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length)
        ctype = self.headers.get("Content-Type", "")

        orders: list[Order] | None = None
        settlements: list[Settlement] | None = None
        n, seed = 250, 20260821

        if ctype.startswith("multipart/form-data"):
            msg = BytesParser(policy=email_policy).parsebytes(
                b"Content-Type: " + ctype.encode() + b"\r\n\r\n" + raw)
            files = {p.get_param("name", header="content-disposition"):
                     p.get_payload(decode=True) for p in msg.iter_parts()}
            if files.get("orders") and files.get("settlements"):
                orders = _parse_orders(files["orders"].decode())
                settlements = _parse_settlements(files["settlements"].decode())
        else:
            from urllib.parse import parse_qs
            n = int(parse_qs(raw.decode()).get("n", ["250"])[0])

        if orders is None or settlements is None:
            ds = build(n, seed=seed)
            orders, settlements, truth = ds.orders, ds.settlements, ds.truth
        else:
            # Real books carry no ground truth, so accuracy is unmeasurable and
            # the harness is fed empty truth. The verdicts are still real: the
            # kernel checks every proof against the records that were uploaded.
            truth = []

        with Timer() as t:
            preds, pools, findings = run(settlements, orders)
        rep = evaluate(settlements, truth or [
            TrueMatch(s.settlement_id, (), "unknown") for s in settlements
        ], preds, pools, t.elapsed)
        self._send(render(rep, findings, settlements, orders, seed))


def main() -> None:
    srv = HTTPServer(("127.0.0.1", PORT), Handler)
    url = f"http://127.0.0.1:{PORT}/"
    print(f"ATTEST → {url}")
    webbrowser.open(url)
    srv.serve_forever()


if __name__ == "__main__":
    main()
