"""Synthetic ESPN league responses, shaped like ESPN's fantasy API, for tests (P3 step 5).

Everything here is made up: no real league, owner or cookie is recorded (the repo is public). The
shapes come from earlier work and are checked against the owner's real league in Verification Gaps
(P3 step 15). The mock mimics the three behaviours that matter: public leagues answer anyone,
private ones answer only the right cookies, and a revoked cookie is refused.
"""

from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from typing import Any

import httpx
import respx

BASE = "https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl"
FAN = "https://fan.api.espn.com/apis/v2/fans"
SEASON = 2026
PUBLIC_LEAGUE = "424242"
PRIVATE_LEAGUE = "777777"
CATEGORY_LEAGUE = "555555"

GOOD_S2 = "AEBgoodcookievalue" + "x" * 30
GOOD_SWID = "{11111111-2222-3333-4444-555555555555}"
REVOKED_S2 = "AEBrevokedcookie" + "y" * 30
OWNER_GUIDS = [
    "{11111111-2222-3333-4444-555555555555}",
    "{AAAAAAAA-BBBB-CCCC-DDDD-000000000002}",
    "{AAAAAAAA-BBBB-CCCC-DDDD-000000000003}",
    "{AAAAAAAA-BBBB-CCCC-DDDD-000000000004}",
]

# ESPN player ids used below (made-up names; ids are in the range ESPN uses)
QB1, RB1, RB2, WR1, WR2, TE1, K1 = 9000001, 9000002, 9000003, 9000004, 9000005, 9000006, 9000007
DEF_KC = -16012  # Kansas City D/ST: -(16000 + proTeamId 12)
UNKNOWN_ROOKIE = 9000099  # on a roster but not in our player list (name-fallback test)
IDP_PLAYER = 9000050


def _scoring_items() -> list[dict[str, Any]]:
    def item(stat: int, pts: float, over: dict[str, float] | None = None) -> dict[str, Any]:
        return {"statId": stat, "points": pts, "pointsOverrides": over or {}}

    return [
        item(3, 0.04),  # PY
        item(4, 4),  # PTD
        item(20, -2),  # INTT
        item(24, 0.1),  # RY
        item(25, 6),  # RTD
        item(53, 1, {"6": 1.5}),  # REC, tight-end premium
        item(42, 0.1),  # REY
        item(43, 6),  # RETD
        item(72, -2),  # FUML
        item(80, 3),  # FG0 (0-39)
        item(77, 4),  # FG40
        item(198, 5),  # FG50 (no FG60: open ended)
        item(86, 1),  # PAT
        item(99, 1),  # SK
        item(95, 2),  # INT
        item(89, 10),  # PA0
        item(90, 7),  # PA1
        item(91, 4),  # PA7
        item(92, 1),  # PA14
        item(123, -1),  # PA28
        item(124, -4),  # PA35
        item(103, 6),  # INTTD
        item(104, 6),  # FRTD
    ]


def _entry(
    player_id: int, slot: int, name: str, pos: int, team: int, pts: float | None = None
) -> dict[str, Any]:
    pool: dict[str, Any] = {
        "id": player_id,
        "player": {
            "id": player_id,
            "fullName": name,
            "defaultPositionId": pos,
            "proTeamId": team,
            "injuryStatus": "ACTIVE",
        },
    }
    if pts is not None:
        pool["appliedStatTotal"] = pts
    return {"playerId": player_id, "lineupSlotId": slot, "playerPoolEntry": pool}


def _team_roster(offset: int = 0) -> list[dict[str, Any]]:
    return [
        _entry(QB1 + offset * 100, 0, f"Quarterback {offset}", 1, 12),
        _entry(RB1 + offset * 100, 2, f"Runner {offset}", 2, 7),
        _entry(RB2 + offset * 100, 20, f"Backup Runner {offset}", 2, 7),
        _entry(WR1 + offset * 100, 4, f"Receiver {offset}", 3, 16),
        _entry(TE1 + offset * 100, 6, f"Tight End {offset}", 4, 17),
    ]


def league_doc(league_id: str = PUBLIC_LEAGUE, **settings_over: Any) -> dict[str, Any]:
    """mSettings + mTeam + mRoster."""
    teams = []
    for i in range(4):
        roster = _team_roster(i)
        if i == 0:
            roster += [
                _entry(DEF_KC, 16, "Chiefs D/ST", 16, 12),
                _entry(K1, 17, "Kicker", 5, 12),
                _entry(UNKNOWN_ROOKIE, 23, "Rookie Rusher Jr.", 2, 14),
                _entry(IDP_PLAYER, 10, "Linebacker", 10, 3),  # an IDP slot: treated as bench
            ]
        teams.append(
            {
                "id": i + 1,
                "name": f"Team {i + 1}" if i != 3 else None,  # one team has only location+nickname
                "location": "Gridiron" if i == 3 else None,
                "nickname": "Gang" if i == 3 else None,
                "abbrev": f"T{i + 1}",
                "primaryOwner": OWNER_GUIDS[i],
                "owners": [OWNER_GUIDS[i]],
                "logo": f"https://example.invalid/logo{i + 1}.png",
                "waiverRank": i + 1,
                "record": {"overall": {"wins": 5 - i, "losses": i + 3, "ties": 0}},
                "transactionCounter": {"acquisitionBudgetSpent": 10 * i},
                "roster": {"entries": roster},
            }
        )
    settings: dict[str, Any] = {
        "name": "Fixture League",
        "size": 4,
        "isPublic": league_id == PUBLIC_LEAGUE,
        "scoringSettings": {"scoringType": "H2H_POINTS", "scoringItems": _scoring_items()},
        "rosterSettings": {
            "lineupSlotCounts": {
                "0": 1,
                "2": 2,
                "4": 2,
                "6": 1,
                "23": 1,
                "16": 1,
                "17": 1,
                "20": 6,
                "21": 1,
                "8": 0,
                "10": 1,
                "12": 0,
                "18": 0,
                "19": 0,
            }
        },
        "scheduleSettings": {
            "matchupPeriodCount": 14,
            "matchupPeriods": {
                **{str(p): [p] for p in range(1, 15)},
                "15": [15, 16],
                "16": [17, 18],
            },
            "playoffTeamCount": 6,
            "playoffMatchupPeriodLength": 2,
        },
        "acquisitionSettings": {
            "acquisitionType": "FAAB",
            "isUsingAcquisitionBudget": True,
            "acquisitionBudget": 100,
            "minimumBid": 1,
            "waiverHours": 48,
            "waiverProcessDays": ["WED"],
        },
    }
    settings.update(settings_over)
    return {
        "id": int(league_id),
        "seasonId": SEASON,
        "scoringPeriodId": 9,
        "status": {"isActive": True, "currentMatchupPeriod": 9, "firstScoringPeriod": 1},
        "settings": settings,
        "teams": teams,
        "members": [
            {"id": g, "displayName": f"owner{i + 1}", "firstName": "Pat", "lastName": f"No{i + 1}"}
            for i, g in enumerate(OWNER_GUIDS)
        ],
    }


def _side(
    team_id: int, week_pts: dict[str, float], total: float, with_roster: bool
) -> dict[str, Any]:
    offset = team_id - 1
    side: dict[str, Any] = {
        "teamId": team_id,
        "totalPoints": total,
        "pointsByScoringPeriod": week_pts,
    }
    if with_roster:
        entries = [
            _entry(QB1 + offset * 100, 0, f"Quarterback {offset}", 1, 12, 21.5),
            _entry(RB1 + offset * 100, 2, f"Runner {offset}", 2, 7, 12.4),
            _entry(RB2 + offset * 100, 20, f"Backup Runner {offset}", 2, 7, 3.1),
            _entry(WR1 + offset * 100, 4, f"Receiver {offset}", 3, 16, 9.8),
            _entry(TE1 + offset * 100, 6, f"Tight End {offset}", 4, 17, 7.5),
        ]
        side["rosterForCurrentScoringPeriod"] = {"entries": entries}
    return side


def matchup_doc(week: int = 9) -> dict[str, Any]:
    """mSettings + mMatchupScore + mBoxscore for NFL week `week` (a scoring period)."""
    doc = league_doc()
    schedule = [
        {
            "id": 1, "matchupPeriodId": 9,
            "home": _side(1, {"9": 100.2}, 100.2, True),
            "away": _side(2, {"9": 88.0}, 88.0, True),
        },
        {  # team 3 has a bye in period 9: no opponent
            "id": 2, "matchupPeriodId": 9, "home": _side(3, {"9": 70.5}, 70.5, True),
        },
        {  # a two-week playoff round: periods 15 covers NFL weeks 15 and 16
            "id": 3, "matchupPeriodId": 15,
            "home": _side(1, {"15": 90.0, "16": 31.0}, 121.0, True),
            "away": _side(4, {"15": 80.0, "16": 55.5}, 135.5, True),
        },
    ]  # fmt: skip
    return {
        "id": int(PUBLIC_LEAGUE),
        "status": doc["status"],
        "settings": doc["settings"],
        "schedule": schedule,
    }


def transactions_doc() -> dict[str, Any]:
    ms = 1_730_000_000_000
    return {
        "transactions": [
            {
                "id": "tx-fa", "type": "FREEAGENT", "status": "EXECUTED", "scoringPeriodId": 9,
                "proposedDate": ms, "teamId": 2,
                "items": [
                    {"playerId": 111, "type": "ADD", "fromTeamId": 0, "toTeamId": 2},
                    {"playerId": 222, "type": "DROP", "fromTeamId": 2, "toTeamId": 0},
                ],
            },
            {
                "id": "tx-waiver", "type": "WAIVER", "status": "EXECUTED", "scoringPeriodId": 9,
                "proposedDate": ms + 1000, "bidAmount": 12, "teamId": 1,
                "items": [{"playerId": 333, "type": "ADD", "fromTeamId": 0, "toTeamId": 1}],
            },
            {
                "id": "tx-failed", "type": "WAIVER", "status": "FAILED_PLAYERALREADYDROPPED",
                "scoringPeriodId": 9, "proposedDate": ms + 2000, "bidAmount": 5, "teamId": 3,
                "items": [{"playerId": 444, "type": "ADD", "fromTeamId": 0, "toTeamId": 3}],
            },
            {
                "id": "tx-trade", "type": "TRADE_ACCEPT", "status": "EXECUTED",
                "scoringPeriodId": 9, "proposedDate": ms + 3000,
                "items": [
                    {"playerId": 555, "type": "ADD", "fromTeamId": 1, "toTeamId": 4},
                    {"playerId": 666, "type": "ADD", "fromTeamId": 4, "toTeamId": 1},
                ],
            },
            {  # a lineup change: not a claim
                "id": "tx-lineup", "type": "ROSTER", "status": "EXECUTED", "scoringPeriodId": 9,
                "proposedDate": ms + 4000, "teamId": 1,
                "items": [{"playerId": 777, "type": "LINEUP", "fromTeamId": 1, "toTeamId": 1}],
            },
        ]
    }  # fmt: skip


def fan_doc() -> dict[str, Any]:
    def pref(
        game: int, season: int, entry_id: int, groups: list[tuple[str, str]]
    ) -> dict[str, Any]:
        return {
            "metaData": {
                "entry": {
                    "gameId": game, "seasonId": season, "entryId": entry_id,
                    "groups": [{"groupId": int(g), "groupName": n} for g, n in groups],
                }
            }
        }  # fmt: skip

    return {
        "preferences": [
            pref(1, SEASON, 3, [(PUBLIC_LEAGUE, "Fixture League")]),
            pref(1, SEASON, 7, [(PRIVATE_LEAGUE, "Private Fixture League")]),
            pref(2, SEASON, 1, [("999", "A basketball league")]),
            pref(1, SEASON - 1, 2, [("888", "Last year's league")]),
            {"metaData": None},  # a preference with no entry (ESPN has several kinds)
        ]
    }


def category_league_doc() -> dict[str, Any]:
    doc = league_doc(CATEGORY_LEAGUE)
    doc["id"] = int(CATEGORY_LEAGUE)
    doc["settings"]["scoringSettings"]["scoringType"] = "H2H_CATEGORY"
    return doc


# --------------------------------------------------------------------------- the mock
def _has_cookie(request: httpx.Request, s2: str, swid: str) -> bool:
    cookie = request.headers.get("cookie", "")
    return f"espn_s2={s2}" in cookie and f"SWID={swid}" in cookie


def mock_espn(*, on_request: Callable[[httpx.Request], None] | None = None) -> respx.MockRouter:
    """A respx router serving the fixtures above. Use as `with mock_espn() as router:`."""
    router = respx.mock(assert_all_called=False)

    def league(request: httpx.Request) -> httpx.Response:
        if on_request:
            on_request(request)
        league_id = request.url.path.rsplit("/", 1)[-1]
        views = request.url.params.get_list("view")
        week = request.url.params.get("scoringPeriodId")
        if league_id == PRIVATE_LEAGUE:
            if not _has_cookie(request, GOOD_S2, GOOD_SWID):
                return httpx.Response(401, json={"details": [{"code": "AUTH_LEAGUE_NOT_VISIBLE"}]})
        elif league_id == CATEGORY_LEAGUE:
            return httpx.Response(200, json=category_league_doc())
        elif league_id != PUBLIC_LEAGUE:
            return httpx.Response(404, json={"messages": ["Not found"]})
        if "mTransactions2" in views:
            doc = transactions_doc()
            doc["transactions"] = [  # only this scoring period's moves, like a real weekly read
                t for t in doc["transactions"] if str(t["scoringPeriodId"]) == (week or "9")
            ]
            return httpx.Response(200, json=doc)
        if "mMatchupScore" in views:
            return httpx.Response(200, json=matchup_doc(int(week or 9)))
        return httpx.Response(200, json=deepcopy(league_doc(league_id)))

    def fan(request: httpx.Request) -> httpx.Response:
        if on_request:
            on_request(request)
        if not _has_cookie(request, GOOD_S2, GOOD_SWID):
            return httpx.Response(404, json={})  # signed out: ESPN answers 404 / anon
        return httpx.Response(200, json=fan_doc())

    router.get(url__regex=rf"{BASE}/seasons/\d+/segments/0/leagues/\d+").mock(side_effect=league)
    router.get(url__regex=rf"{FAN}/.*").mock(side_effect=fan)
    return router
