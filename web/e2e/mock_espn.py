"""A stand-in for ESPN's fantasy API, serving the synthetic responses in
api/tests/fixtures/espn_league (made-up league, no real people or cookies). End-to-end tests point
the worker at it, so they never touch the live service.

It behaves like ESPN where it matters: a public league answers anyone; a private one answers only
the right two cookies (401 otherwise, as ESPN does); a fan profile exists only for a signed-in
cookie pair (404 otherwise); a revoked cookie is refused everywhere.

Run: FIXTURES_DIR=api/tests/fixtures/espn_league PORT=4020 python web/e2e/mock_espn.py
Plain standard library on purpose: it runs in a stock python image with nothing installed.
"""

import json
import os
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

FIXTURES = Path(os.environ.get("FIXTURES_DIR", "/fixtures"))
PORT = int(os.environ.get("PORT", "4020"))


def load(name: str) -> object:
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


COOKIES = load("cookies")


def has_cookie(headers: object) -> bool:
    cookie = headers.get("Cookie", "")  # type: ignore[attr-defined]
    return (
        f"espn_s2={COOKIES['good_s2']}" in cookie and f"SWID={COOKIES['good_swid']}" in cookie
    )


def league(path: str, query: dict[str, list[str]], headers: object) -> tuple[int, object]:
    m = re.fullmatch(r"/apis/v3/games/ffl/seasons/\d+/segments/0/leagues/(\d+)", path)
    if not m:
        return 404, {}
    league_id = m.group(1)
    views = query.get("view", [])
    week = (query.get("scoringPeriodId") or ["9"])[0]
    if league_id == COOKIES["private_league"]:
        if not has_cookie(headers):
            return 401, {"details": [{"code": "AUTH_LEAGUE_NOT_VISIBLE"}]}
    elif league_id == COOKIES["category_league"]:
        return 200, load(f"league_{league_id}")
    elif league_id != COOKIES["public_league"]:
        return 404, {"messages": ["Not found"]}
    if "mTransactions2" in views:
        doc = load("transactions")
        doc["transactions"] = [  # type: ignore[index]
            t for t in doc["transactions"] if str(t["scoringPeriodId"]) == week  # type: ignore[index]
        ]
        return 200, doc
    if "mMatchupScore" in views:
        return 200, load("matchup")
    return 200, load(f"league_{league_id}")


def fan(headers: object) -> tuple[int, object]:
    if not has_cookie(headers):
        return 404, {}
    return 200, load("fan")


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802 (name fixed by the base class)
        parts = urlsplit(self.path)
        query = parse_qs(parts.query)
        if parts.path.startswith("/apis/v2/fans/"):
            status, doc = fan(self.headers)
        elif parts.path == "/health":
            status, doc = 200, {"ok": True}
        else:
            status, doc = league(parts.path, query, self.headers)
        body = json.dumps(doc).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args: object) -> None:  # quiet
        pass


if __name__ == "__main__":
    print(f"mock ESPN on :{PORT}, fixtures in {FIXTURES}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
