"""Writes the synthetic ESPN responses as JSON for the end-to-end stack's stand-in server.

    python -m tests.export_espn_fixtures

The builders in tests/espn_fixtures.py are the source of truth; web/e2e/mock_espn.py (a plain
standard-library server) and the browser tests read these files. A unit test fails if the
committed files drift from the builders.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tests import espn_fixtures as fx

OUT = Path(__file__).parent / "fixtures" / "espn_league"


def documents() -> dict[str, Any]:
    return {
        f"league_{fx.PUBLIC_LEAGUE}": fx.league_doc(fx.PUBLIC_LEAGUE),
        f"league_{fx.PRIVATE_LEAGUE}": fx.league_doc(fx.PRIVATE_LEAGUE),
        f"league_{fx.CATEGORY_LEAGUE}": fx.category_league_doc(),
        "matchup": fx.matchup_doc(),
        "transactions": fx.transactions_doc(),
        "fan": fx.fan_doc(),
        # The made-up cookies the stand-in accepts (and one pair it refuses): not real credentials.
        "cookies": {
            "good_s2": fx.GOOD_S2,
            "good_swid": fx.GOOD_SWID,
            "revoked_s2": fx.REVOKED_S2,
            "public_league": fx.PUBLIC_LEAGUE,
            "private_league": fx.PRIVATE_LEAGUE,
            "category_league": fx.CATEGORY_LEAGUE,
        },
    }


def render(doc: Any) -> str:
    return json.dumps(doc, indent=2) + "\n"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, doc in documents().items():
        (OUT / f"{name}.json").write_text(render(doc), encoding="utf-8", newline="\n")
        print("wrote", OUT / f"{name}.json")


if __name__ == "__main__":
    main()
