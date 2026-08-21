"""Local server: static UI plus the JSON API.

Stdlib only. No framework, no build step, no dependency the engine does not
already have — `python -m attest.web` and the product opens.

Everything is served from 127.0.0.1 and nothing leaves the machine, which is the
correct default for a tool that reads a merchant's books.
"""

from __future__ import annotations

import json
import mimetypes
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from attest import api

PORT = 8420
UI = Path(__file__).resolve().parent / "ui"


class Handler(BaseHTTPRequestHandler):
    # HTTP/1.1 keep-alive on a single-threaded server deadlocks: the browser
    # holds the connection open and every subsequent request queues behind it.
    # Threading is not an optimisation here, it is what makes the page load.
    protocol_version = "HTTP/1.1"

    def log_message(self, *a: object) -> None:
        pass

    def _reply(self, body: bytes, ctype: str, code: int = 200) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, payload: object, code: int = 200) -> None:
        self._reply(json.dumps(payload).encode(), "application/json", code)

    def do_POST(self) -> None:
        u = urlparse(self.path)
        q = parse_qs(u.query)
        if u.path == "/api/events/demo":
            self._json(api.demonstrate_events(api.get(q.get("run", [""])[0])))
            return
        if u.path != "/api/events":
            self._json({"error": "not found"}, 404)
            return
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        sig = self.headers.get("X-Razorpay-Signature", "")
        try:
            self._json(api.receive_event(
                api.get(q.get("run", [""])[0]), body, sig))
        except Exception as exc:  # a malformed body is the client's problem
            self._json({"error": str(exc)}, 400)

    def do_GET(self) -> None:
        u = urlparse(self.path)
        q = parse_qs(u.query)

        if u.path == "/api/run":
            n = max(10, min(5000, int(q.get("n", ["250"])[0])))
            self._json(api.summary(api.execute(n, 20260821)))

        elif u.path == "/api/rows":
            r = api.get(q.get("run", [""])[0])
            self._json(api.rows(r) if r else {"error": "unknown run"},
                       200 if r else 404)

        elif u.path == "/api/investigate":
            r = api.get(q.get("run", [""])[0])
            v = api.investigate_view(r, q.get("id", [""])[0]) if r else None
            self._json(v or {"error": "not found"}, 200 if v else 404)

        elif u.path == "/api/attention":
            r = api.get(q.get("run", [""])[0])
            self._json(api.attention(r) if r else {"error": "unknown run"},
                       200 if r else 404)

        elif u.path == "/api/subject":
            self._json(api.subject_view(api.get(q.get("run", [""])[0]),
                                        q.get("type", ["portfolio"])[0],
                                        q.get("id", [""])[0]))

        elif u.path == "/api/spine":
            self._json(api.spine_view(api.get(q.get("run", [""])[0]),
                                      q.get("type", ["portfolio"])[0],
                                      q.get("id", [""])[0],
                                      int(q.get("review", ["15000"])[0]),
                                      int(q.get("exposure", ["10000000"])[0])))

        elif u.path == "/api/sync":
            self._json(api.sync_view(api.get(q.get("run", [""])[0])))

        elif u.path == "/api/trail":
            r = api.get(q.get("run", [""])[0])
            self._json(api.trail_view(r, q.get("id", [""])[0]) if r
                       else {"error": "unknown run"}, 200 if r else 404)

        elif u.path == "/api/actions":
            r = api.get(q.get("run", [""])[0])
            self._json(api.actions_view(r) if r
                       else {"error": "unknown run"}, 200 if r else 404)

        elif u.path == "/api/journal":
            r = api.get(q.get("run", [""])[0])
            self._json(api.journal_view(
                r,
                int(q.get("review", ["15000"])[0]),
                int(q.get("exposure", ["10000000"])[0]),
            ) if r else {"error": "unknown run"}, 200 if r else 404)

        elif u.path == "/api/whatchanged":
            r = api.get(q.get("run", [""])[0])
            self._json(api.whatchanged_view(r) if r
                       else {"error": "unknown run"}, 200 if r else 404)

        elif u.path == "/api/agents":
            self._json(api.agents_view(api.get(q.get("run", [""])[0])))

        elif u.path == "/api/trust":
            self._json(api.trust_view(api.get(q.get("run", [""])[0])))

        elif u.path == "/api/observatory":
            self._json(api.observatory())

        elif u.path == "/api/events":
            self._json(api.event_feed())

        elif u.path == "/api/integrations":
            self._json(api.integrations(api.get(q.get("run", [""])[0])))

        elif u.path == "/api/ask":
            r = api.get(q.get("run", [""])[0])
            self._json(api.ask(r, q.get("q", [""])[0]) if r
                       else {"error": "unknown run"}, 200 if r else 404)

        elif u.path == "/api/policy":
            r = api.get(q.get("run", [""])[0])
            if r is None:
                self._json({"error": "unknown run"}, 404)
            else:
                self._json(api.policy_view(
                    r,
                    int(q.get("review", ["15000"])[0]),
                    int(q.get("exposure", ["10000000"])[0])))

        elif u.path == "/api/exceptions":
            r = api.get(q.get("run", [""])[0])
            self._json(api.exceptions_view(r) if r
                       else {"error": "unknown run"}, 200 if r else 404)

        elif u.path == "/api/settlement":
            r = api.get(q.get("run", [""])[0])
            d = api.detail(r, q.get("id", [""])[0]) if r else None
            self._json(d or {"error": "not found"}, 200 if d else 404)

        else:
            name = "index.html" if u.path in ("/", "") else u.path.lstrip("/")
            path = (UI / name).resolve()
            if UI not in path.parents or not path.is_file():
                self._reply(b"not found", "text/plain", 404)
                return
            ctype = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
            self._reply(path.read_bytes(), f"{ctype}; charset=utf-8")


def main() -> None:
    url = f"http://127.0.0.1:{PORT}/"
    print(f"ATTEST → {url}")
    webbrowser.open(url)
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
