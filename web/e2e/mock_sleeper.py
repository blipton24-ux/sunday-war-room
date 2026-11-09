"""A stand-in for Sleeper's public API, serving the recorded (anonymized) responses in
api/tests/fixtures/sleeper. End-to-end tests point the worker at it, so they never depend
on the live service and always see the same league.

Run: FIXTURES_DIR=api/tests/fixtures/sleeper PORT=4010 python web/e2e/mock_sleeper.py
Plain standard library on purpose: it runs in a stock python image with nothing installed.
"""

import json
import os
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

FIXTURES = Path(os.environ.get("FIXTURES_DIR", "/fixtures"))
PORT = int(os.environ.get("PORT", "4010"))

LEAGUE_ID = "1100000000000000001"
ME = "900000000000000001"  # fixtureuser: owns "Team 1"
EMPTY_USER = "900000000000000099"  # a real account with no leagues this season


def load(name: str) -> object:
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


def route(path: str) -> object | None:
    """The JSON body for a Sleeper path, or None (sent as JSON null, like Sleeper does)."""
    if path == "/v1/state/nfl":
        return load("state")
    if m := re.fullmatch(r"/v1/user/([^/]+)", path):
        name = m.group(1)
        if name == "fixtureuser":
            return load("user")
        if name == "emptyuser":
            return {"user_id": EMPTY_USER, "username": "emptyuser",
                    "display_name": "EmptyUser", "avatar": None}  # fmt: skip
        return None  # Sleeper answers 200 + null for unknown usernames
    if m := re.fullmatch(r"/v1/user/(\d+)/leagues/nfl/(\d+)", path):
        return load("user_leagues") if m.group(1) == ME else []
    if m := re.fullmatch(r"/v1/league/(\d+)(?:/(rosters|users|matchups/(\d+)))?", path):
        if m.group(1) != LEAGUE_ID:
            return None
        part = m.group(2)
        if part is None:
            return load("league")
        if part == "rosters":
            return load("rosters")
        if part == "users":
            return load("league_users")
        return load("matchups_9" if m.group(3) == "9" else "matchups_8")
    if path == "/v1/players/nfl":
        return load("players")
    return None


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802 (name fixed by the base class)
        body = json.dumps(route(self.path.split("?")[0])).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args: object) -> None:  # quiet
        pass


if __name__ == "__main__":
    print(f"mock Sleeper on :{PORT}, fixtures in {FIXTURES}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
