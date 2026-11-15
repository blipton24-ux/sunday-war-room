"""The ESPN adapter against synthetic ESPN responses (P3 steps 5-6, ADR-051/053)."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from typing import Any

import httpx
import pandas as pd
import pytest
import respx

from app.adapters.base import (
    AdapterError,
    AdapterSchemaError,
    AuthRequired,
    CredentialsInvalid,
    LeagueAdapter,
    NotFoundOnPlatform,
    UnsupportedLeague,
)
from app.adapters.espn import (
    EspnAdapter,
    EspnCredentials,
    EspnHttp,
    make_credentials,
    normalize_swid,
    parse_league_link,
)
from app.model.scoring import check_rules, score
from tests import espn_fixtures as fx

CREDS = EspnCredentials(fx.GOOD_S2, fx.GOOD_SWID)
REVOKED = EspnCredentials(fx.REVOKED_S2, fx.GOOD_SWID)


@pytest.fixture
def router() -> Iterator[respx.MockRouter]:
    with fx.mock_espn() as r:
        yield r


@pytest.fixture
async def http() -> AsyncIterator[EspnHttp]:
    h = EspnHttp(retries=0)
    yield h
    await h.aclose()


def adapter(http: EspnHttp, creds: EspnCredentials | None = None) -> EspnAdapter:
    return EspnAdapter(http, fx.SEASON, creds)


async def league(a: EspnAdapter, league_id: str = fx.PUBLIC_LEAGUE) -> Any:
    return await a.fetch_league(league_id)


def test_the_adapter_satisfies_the_league_interface(http: EspnHttp) -> None:
    a: LeagueAdapter = adapter(http)  # mypy checks the Protocol here
    assert a.platform == "espn"


# --------------------------------------------------------------------------- access (ADR-051)
async def test_a_public_league_answers_without_cookies(router: Any, http: EspnHttp) -> None:
    public, name, teams = await adapter(http).probe(fx.PUBLIC_LEAGUE)
    assert (public, name) == (True, "ESPN Fixture League")
    assert teams[0] == ("1", "Team 1")
    assert teams[3] == ("4", "Gridiron Gang")  # no `name`: location + nickname


async def test_a_private_league_needs_cookies(router: Any, http: EspnHttp) -> None:
    with pytest.raises(AuthRequired):
        await adapter(http).probe(fx.PRIVATE_LEAGUE)
    _, name, _ = await adapter(http, CREDS).probe(fx.PRIVATE_LEAGUE)
    assert name == "ESPN Private League"


async def test_cookies_that_stopped_working_are_reported_as_such(
    router: Any, http: EspnHttp
) -> None:
    with pytest.raises(CredentialsInvalid):
        await adapter(http, REVOKED).fetch_league(fx.PRIVATE_LEAGUE)


async def test_an_unknown_league_is_not_found(router: Any, http: EspnHttp) -> None:
    with pytest.raises(NotFoundOnPlatform):
        await adapter(http).probe("1")


async def test_cookies_ride_on_each_request_and_never_on_the_shared_client(
    router: Any, http: EspnHttp
) -> None:
    await adapter(http, CREDS).fetch_league(fx.PRIVATE_LEAGUE)
    sent = router.calls.last.request
    assert f"espn_s2={fx.GOOD_S2}" in sent.headers["cookie"]
    assert f"SWID={fx.GOOD_SWID}" in sent.headers["cookie"]
    assert "cookie" not in {k.lower() for k in http._client.headers}  # another user's call is clean
    await adapter(http).probe(fx.PUBLIC_LEAGUE)
    assert "cookie" not in router.calls.last.request.headers


def test_credentials_never_print_their_secrets() -> None:
    assert fx.GOOD_S2 not in repr(CREDS) and fx.GOOD_SWID not in repr(CREDS)
    assert fx.GOOD_S2 not in str(CREDS)
    assert EspnCredentials.from_json(CREDS.to_json()) == CREDS


# --------------------------------------------------------------------------- the league
async def test_league_settings_map_to_ours(router: Any, http: EspnHttp) -> None:
    data = await league(adapter(http))
    assert (data.ref.platform, data.ref.external_id, data.ref.season) == ("espn", "424242", 2026)
    assert (data.ref.name, data.ref.total_teams, data.status) == (
        "ESPN Fixture League",
        4,
        "in_season",
    )
    # lineup slots in our order; the linebacker slot is left out (IDP isn't projected yet)
    assert data.roster_slots == [
        "QB", "RB", "RB", "WR", "WR", "TE", "FLEX", "K", "DEF", "BN", "BN", "BN", "BN", "BN", "BN",
        "IR",
    ]  # fmt: skip


async def test_waivers_and_season_rules(router: Any, http: EspnHttp) -> None:
    data = await league(adapter(http))
    w, s = data.waivers, data.season_rules
    assert (w.kind, w.budget, w.min_bid, w.clear_days, w.weekly_day) == ("faab", 100, 1, 2, 2)
    assert w.raw["waiverHours"] == 48
    assert (s.start_week, s.playoff_week_start, s.playoff_teams) == (1, 15, 6)
    assert s.playoff_round == "two_week_rounds"


async def test_scoring_rules_become_espn_keys_with_overrides_and_open_ladders(
    router: Any, http: EspnHttp
) -> None:
    rules = (await league(adapter(http))).scoring_rules
    assert rules["espn:PY"] == 0.04 and rules["espn:REC"] == 1 and rules["espn:REC@TE"] == 1.5
    assert "espn:FG50+" in rules and "espn:FG50" not in rules  # no 60+ band: 50 covers longer
    assert rules["espn:def_tds"] == 6  # INTTD and FRTD share a value: scored once
    assert check_rules(rules).unsupported == {}  # everything this league scores is scored


async def test_the_leagues_own_rules_score_a_game(router: Any, http: EspnHttp) -> None:
    rules = (await league(adapter(http))).scoring_rules
    qb = {"passing_yards": 300, "passing_tds": 2, "passing_interceptions": 1, "position": "QB"}
    te = {"receptions": 4, "receiving_yards": 50, "receiving_tds": 1, "position": "TE"}
    wr = {**te, "position": "WR"}
    got = score(pd.DataFrame([qb, te, wr]), rules).tolist()
    assert got == [12 + 8 - 2, 6 + 5 + 6, 4 + 5 + 6]  # TE reception 1.5, WR reception 1.0


async def test_a_category_league_is_refused_with_a_plain_reason(
    router: Any, http: EspnHttp
) -> None:
    with pytest.raises(UnsupportedLeague, match="head-to-head points"):
        await league(adapter(http), fx.CATEGORY_LEAGUE)


# --------------------------------------------------------------------------- teams
async def test_teams_with_owners_records_and_waiver_state(router: Any, http: EspnHttp) -> None:
    a = adapter(http)
    teams = await a.fetch_teams(await league(a))
    assert [t.external_id for t in teams] == ["1", "2", "3", "4"]
    t1, t4 = teams[0], teams[3]
    assert (t1.name, t1.owner_name, t1.owner_external_id) == ("Team 1", "owner1", fx.OWNER_GUIDS[0])
    assert (t1.wins, t1.losses, t1.waiver_position, t1.waiver_budget_used) == (5, 3, 1, 0)
    assert t4.name == "Gridiron Gang" and t4.waiver_budget_used == 30


async def test_one_league_read_serves_both_league_and_teams(router: Any, http: EspnHttp) -> None:
    a = adapter(http)
    await a.fetch_teams(await league(a))
    assert router.calls.call_count == 1


async def test_rosters_map_slots_and_carry_name_hints(router: Any, http: EspnHttp) -> None:
    a = adapter(http)
    roster = {s.player_external_id: s for s in (await a.fetch_teams(await league(a)))[0].roster}
    assert roster[str(fx.QB1)].slot == "QB" and roster[str(fx.QB1)].is_starter
    assert roster[str(fx.RB2)].slot == "BN" and not roster[str(fx.RB2)].is_starter
    assert roster[str(fx.DEF_KC)].slot == "DEF"
    assert roster[str(fx.UNKNOWN_ROOKIE)].slot == "FLEX"
    assert roster[str(fx.IDP_PLAYER)].slot == "BN"  # IDP slot: not a starter we project
    hint = roster[str(fx.UNKNOWN_ROOKIE)].hint
    assert (hint.name, hint.position, hint.team) == ("Rookie Rusher Jr.", "RB", "LA")  # type: ignore[union-attr]


# --------------------------------------------------------------------------- matchups
async def test_matchups_pair_teams_and_carry_player_points(router: Any, http: EspnHttp) -> None:
    a = adapter(http)
    rows = await a.fetch_matchups(await league(a), 9)
    by_team = {r.team_external_id: r for r in rows}
    assert set(by_team) == {"1", "2", "3"}  # period 9 only; the playoff round is another period
    assert by_team["1"].matchup_key == by_team["2"].matchup_key is not None
    assert by_team["3"].matchup_key is None  # bye
    assert by_team["1"].points == 100.2
    assert by_team["1"].player_points[str(fx.QB1)] == 21.5
    assert {s.slot for s in by_team["1"].roster} >= {"QB", "RB", "WR", "TE", "BN"}


async def test_a_two_week_round_reports_only_the_weeks_own_points(
    router: Any, http: EspnHttp
) -> None:
    a = adapter(http)
    data = await league(a)
    week15 = {r.team_external_id: r.points for r in await a.fetch_matchups(data, 15)}
    week16 = {r.team_external_id: r.points for r in await a.fetch_matchups(data, 16)}
    assert week15 == {"1": 90.0, "4": 80.0}
    assert week16 == {"1": 31.0, "4": 55.5}  # not the 121.0 / 135.5 round totals


async def test_a_week_with_no_matchup_period_fails_loudly(router: Any, http: EspnHttp) -> None:
    a = adapter(http)
    with pytest.raises(AdapterSchemaError, match="no matchup period"):
        await a.fetch_matchups(await league(a), 30)


async def test_the_matchup_request_asks_for_the_scoring_period(router: Any, http: EspnHttp) -> None:
    a = adapter(http)
    await a.fetch_matchups(await league(a), 9)
    params = router.calls.last.request.url.params
    assert params["scoringPeriodId"] == "9" and "mBoxscore" in params.get_list("view")


# --------------------------------------------------------------------------- transactions
async def test_transactions_become_claims_and_skip_lineup_changes(
    router: Any, http: EspnHttp
) -> None:
    a = adapter(http)
    txs = {t.external_id: t for t in await a.fetch_transactions(await league(a), 9)}
    assert set(txs) == {"tx-fa", "tx-waiver", "tx-failed", "tx-trade"}  # not "tx-lineup"
    fa = txs["tx-fa"]
    assert (fa.kind, fa.status, fa.adds, fa.drops) == (
        "free_agent",
        "complete",
        {"111": "2"},
        {"222": "2"},
    )
    assert (txs["tx-waiver"].kind, txs["tx-waiver"].waiver_bid) == ("waiver", 12)
    assert txs["tx-failed"].status == "failed"
    assert txs["tx-trade"].kind == "trade" and txs["tx-trade"].waiver_bid is None


# --------------------------------------------------------------------------- finding leagues
async def test_the_fan_profile_lists_this_seasons_football_leagues_with_my_team(
    router: Any, http: EspnHttp
) -> None:
    found = await adapter(http, CREDS).find_leagues()
    assert [(ref.external_id, ref.name, team) for ref, team in found] == [
        ("424242", "ESPN Fixture League", "3"),
        ("777777", "ESPN Private League", "2"),
    ]  # no basketball, no last season, no empty preference
    assert router.calls.last.request.url.path.endswith(fx.GOOD_SWID)


async def test_finding_leagues_needs_real_cookies(router: Any, http: EspnHttp) -> None:
    with pytest.raises(AuthRequired):
        await adapter(http).find_leagues()
    with pytest.raises(CredentialsInvalid):  # ESPN answers 404 for a profile that isn't signed in
        await adapter(http, REVOKED).find_leagues()


# --------------------------------------------------------------------------- resilience
async def test_a_rate_limit_is_retried_after_the_wait_it_asks_for(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sleeps: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    monkeypatch.setattr("app.adapters.espn.asyncio.sleep", fake_sleep)
    url = f"{fx.BASE}/seasons/2026/segments/0/leagues/{fx.PUBLIC_LEAGUE}"
    with respx.mock() as r:
        r.get(url__regex=url).mock(
            side_effect=[
                httpx.Response(429, headers={"Retry-After": "7"}),
                httpx.Response(200, json=fx.league_doc()),
            ]
        )
        h = EspnHttp(retries=2)
        _, name, _ = await EspnAdapter(h, 2026).probe(fx.PUBLIC_LEAGUE)
        await h.aclose()
    assert name == "ESPN Fixture League" and sleeps == [7.0]


async def test_it_gives_up_after_its_retries_with_an_error_that_hides_the_cookies() -> None:
    with respx.mock() as r:
        r.get(url__regex=fx.BASE).mock(return_value=httpx.Response(503))
        h = EspnHttp(retries=1)
        with pytest.raises(AdapterError, match="HTTP 503") as err:
            await EspnAdapter(h, 2026, CREDS).probe(fx.PUBLIC_LEAGUE)
        await h.aclose()
    assert fx.GOOD_S2 not in str(err.value)


async def test_a_network_failure_is_an_adapter_error() -> None:
    with respx.mock() as r:
        r.get(url__regex=fx.BASE).mock(side_effect=httpx.ConnectError("boom"))
        h = EspnHttp(retries=0)
        with pytest.raises(AdapterError, match="unreachable"):
            await EspnAdapter(h, 2026).probe(fx.PUBLIC_LEAGUE)
        await h.aclose()


async def test_a_changed_response_shape_fails_loudly(http: EspnHttp) -> None:
    with respx.mock() as r:  # a league whose settings lost their scoring block
        r.get(url__regex=fx.BASE).mock(
            return_value=httpx.Response(200, json={"id": 1, "settings": {"name": "x"}})
        )
        with pytest.raises(AdapterSchemaError, match="league response changed shape"):
            await adapter(http).probe("1")


async def test_an_html_page_with_a_200_is_a_schema_error_not_a_crash(http: EspnHttp) -> None:
    with respx.mock() as r:
        r.get(url__regex=fx.BASE).mock(return_value=httpx.Response(200, text="<html>"))
        with pytest.raises(AdapterSchemaError, match="not JSON"):
            await adapter(http).probe("1")


# --------------------------------------------------------------------------- pasted input
@pytest.mark.parametrize(
    "raw",
    [
        "{11111111-2222-3333-4444-555555555555}",
        "11111111-2222-3333-4444-555555555555",
        "  {11111111-2222-3333-4444-555555555555} ",
        '"{11111111-2222-3333-4444-555555555555}"',
        "{11111111-2222-3333-4444-555555555555".lower() + "}",
    ],
)
def test_swid_is_accepted_with_or_without_braces(raw: str) -> None:
    assert normalize_swid(raw) == "{11111111-2222-3333-4444-555555555555}"


@pytest.mark.parametrize("raw", ["", "abc", "{1234}", "not-a-guid-at-all-not-a-guid-at-all-12"])
def test_a_bad_swid_is_rejected(raw: str) -> None:
    with pytest.raises(ValueError, match="SWID"):
        normalize_swid(raw)


def test_make_credentials_tidies_and_validates() -> None:
    creds = make_credentials(f' "{fx.GOOD_S2}" ', fx.GOOD_SWID.strip("{}"))
    assert creds == CREDS
    with pytest.raises(ValueError, match="espn_s2"):
        make_credentials("short", fx.GOOD_SWID)
    with pytest.raises(ValueError, match="espn_s2"):
        make_credentials("has a space " + "x" * 30, fx.GOOD_SWID)
    with pytest.raises(ValueError, match="espn_s2"):
        make_credentials(
            f"{fx.GOOD_S2}; SWID={fx.GOOD_SWID}", fx.GOOD_SWID
        )  # pasted a whole cookie line


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("424242", ("424242", None, None)),
        (" 424242 ", ("424242", None, None)),
        (
            "https://fantasy.espn.com/football/team?leagueId=424242&seasonId=2026&teamId=3",
            ("424242", 2026, "3"),
        ),
        ("https://fantasy.espn.com/football/league?leagueId=424242", ("424242", None, None)),
    ],
)
def test_a_league_link_or_bare_id_is_understood(
    text: str, expected: tuple[str, int | None, str | None]
) -> None:
    link = parse_league_link(text)
    assert (link.league_id, link.season, link.team_id) == expected


def test_a_link_without_a_league_id_is_explained() -> None:
    with pytest.raises(ValueError, match="leagueId"):
        parse_league_link("https://fantasy.espn.com/football/")
