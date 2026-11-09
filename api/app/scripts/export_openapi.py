"""Write the API's OpenAPI description to a file (no server, database or Redis needed).

    python -m app.scripts.export_openapi              # writes api/openapi.json
    python -m app.scripts.export_openapi --check      # exits 1 if the committed file is stale

`api/openapi.json` is committed. The web app's TypeScript client is generated from it
(`npm run generate:api` in web/), so a backend change shows up as a reviewable diff in
this file and, from it, in the generated client.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SPEC_PATH = Path(__file__).resolve().parents[2] / "openapi.json"


def render(spec: dict[str, Any]) -> str:
    """Stable text form: same input, same bytes, LF line endings on every OS."""
    return json.dumps(spec, indent=2, ensure_ascii=False) + "\n"


def current_spec() -> str:
    from app.main import app

    return render(app.openapi())


def read_committed() -> str:
    # Normalize line endings so a Windows checkout with CRLF still compares equal.
    return SPEC_PATH.read_text(encoding="utf-8").replace("\r\n", "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if openapi.json is stale")
    args = parser.parse_args()

    fresh = current_spec()
    if args.check:
        if not SPEC_PATH.exists() or read_committed() != fresh:
            print(
                "api/openapi.json is out of date. Run: python -m app.scripts.export_openapi",
                file=sys.stderr,
            )
            return 1
        print("api/openapi.json is up to date")
        return 0
    SPEC_PATH.write_bytes(fresh.encode("utf-8"))  # bytes: no CRLF translation on Windows
    print(f"wrote {SPEC_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
