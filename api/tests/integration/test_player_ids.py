"""Matching platform ids to our players: direct ids, ESPN defenses, name fallback (P3 step 3)."""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.base import PlayerHint
from app.db.models import Player
from app.services.player_ids import platform_player_id, resolve_player_ids

pytestmark = pytest.mark.integration


async def add(db: AsyncSession, **kw: object) -> Player:
    p = Player(**kw)
    db.add(p)
    await db.commit()
    return p


async def test_sleeper_ids_match_directly(db: AsyncSession) -> None:
    a = await add(db, name="A", sleeper_id="111")
    got = await resolve_player_ids(db, "sleeper", {"111", "999"})
    assert got == {"111": a.id}  # 999 is unknown and simply left out


async def test_espn_ids_match_on_espn_id_and_ties_go_to_the_lowest_player(
    db: AsyncSession,
) -> None:
    first = await add(db, name="One", sleeper_id="1", espn_id="4000")
    await add(db, name="Dup", sleeper_id="2", espn_id="4000")  # espn_id isn't unique
    got = await resolve_player_ids(db, "espn", {"4000"})
    assert got == {"4000": first.id}


async def test_espn_team_defenses_resolve_through_their_team_key(db: AsyncSession) -> None:
    was = await add(
        db, name="Commanders D/ST", position="DEF", sleeper_id="WAS", gsis_id="TEAM_WAS"
    )
    la = await add(db, name="Rams D/ST", position="DEF", sleeper_id="LAR", gsis_id="TEAM_LA")
    got = await resolve_player_ids(db, "espn", {"-16028", "-16014", "-16099"})
    assert got == {"-16028": was.id, "-16014": la.id}  # -16099 isn't a team


async def test_a_unique_name_position_team_match_links_and_remembers_the_id(
    db: AsyncSession,
) -> None:
    rookie = await add(
        db, name="Cj Daniels", position="WR", nfl_team="LA", sleeper_id="900", espn_id=None
    )
    hints = {"5000": PlayerHint("CJ Daniels", "WR", "LAR")}
    assert await resolve_player_ids(db, "espn", {"5000"}, hints) == {"5000": rookie.id}
    await db.commit()
    linked = await db.scalar(select(Player.espn_id).where(Player.id == rookie.id))
    assert linked == "5000"  # next time it is a direct hit
    assert await resolve_player_ids(db, "espn", {"5000"}) == {"5000": rookie.id}


async def test_two_candidates_means_unmatched_never_a_guess(db: AsyncSession) -> None:
    await add(db, name="Mike Williams", position="WR", nfl_team="LAC", sleeper_id="1")
    await add(db, name="Mike Williams", position="WR", nfl_team="LAC", sleeper_id="2")
    hints = {"7": PlayerHint("Mike Williams", "WR", "LAC")}
    assert await resolve_player_ids(db, "espn", {"7"}, hints) == {}


async def test_the_name_match_never_overwrites_a_different_espn_id(db: AsyncSession) -> None:
    p = await add(db, name="Pat Smith", position="RB", nfl_team="DEN", sleeper_id="3", espn_id="1")
    hints = {"2": PlayerHint("Pat Smith", "RB", "DEN")}
    got = await resolve_player_ids(db, "espn", {"2"}, hints)
    assert got == {"2": p.id}  # still resolves for this sync
    await db.commit()
    assert await db.scalar(select(Player.espn_id).where(Player.id == p.id)) == "1"


def test_platform_player_id_reads_the_right_column() -> None:
    p = Player(name="X", sleeper_id="s", espn_id="e", yahoo_id="y")
    assert [platform_player_id(p, k) for k in ("sleeper", "espn", "yahoo")] == ["s", "e", "y"]
    with pytest.raises(ValueError, match="unknown platform"):
        platform_player_id(p, "nope")
