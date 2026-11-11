"""Matching a platform's player ids to our players (ADR-053).

Every platform spells a player differently. Sleeper's player list is the master list, so a
Sleeper id is stored on every player; ESPN ids arrive from Sleeper's own `espn_id` and nflverse's
crosswalk (services/ingest.py). What neither covers is matched here, in this order:

1. the platform's own id (`sleeper_id`, `espn_id`, `yahoo_id`);
2. a team defense, from ESPN's negative D/ST ids (adapters/espn_teams.py);
3. a unique name + position + team match, which writes the platform id back so it is a direct
   hit next time. Never a guess: two candidates means unmatched.
"""

from __future__ import annotations

import re
from collections.abc import Mapping

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute

from app.adapters.base import Platform, PlayerHint
from app.adapters.espn_teams import defense_team
from app.db.models import Player
from app.logging import get_logger
from app.nfl_teams import canonical_team, defense_key

log = get_logger("player_ids")

_SUFFIX = re.compile(r"\b(jr|sr|ii|iii|iv|v)\b")
_NOT_ALNUM = re.compile(r"[^a-z0-9 ]")


def normalize_name(name: str) -> str:
    """'Odell Beckham Jr.' and 'Odell Beckham' compare equal; case and punctuation don't matter."""
    text = _NOT_ALNUM.sub("", name.lower().replace(".", "").replace("'", "").replace("-", " "))
    return " ".join(_SUFFIX.sub("", text).split())


def platform_player_id(player: Player, platform: str) -> str | None:
    """A player's id on `platform` (None when we haven't linked one)."""
    if platform == "sleeper":
        return player.sleeper_id
    if platform == "espn":
        return player.espn_id
    if platform == "yahoo":
        return player.yahoo_id
    raise ValueError(f"unknown platform {platform!r}")


def _id_column(platform: str) -> InstrumentedAttribute[str | None]:
    return {"sleeper": Player.sleeper_id, "espn": Player.espn_id, "yahoo": Player.yahoo_id}[
        platform
    ]


async def resolve_player_ids(
    db: AsyncSession,
    platform: Platform,
    external_ids: set[str],
    hints: Mapping[str, PlayerHint] | None = None,
) -> dict[str, int]:
    """platform player id -> our players.id. Unmatched ids are left out (and logged)."""
    if not external_ids:
        return {}
    out: dict[str, int] = {}

    column = _id_column(platform)
    rows = await db.execute(
        select(column, Player.id).where(column.in_(external_ids)).order_by(Player.id)
    )
    for ext, pid in rows:
        if ext is not None:
            out.setdefault(ext, pid)  # espn_id isn't unique: the lowest player id wins, always

    if platform == "espn":
        defenses = {ext: team for ext in external_ids if (team := defense_team(ext))}
        if defenses:
            keys = {defense_key(team): ext for ext, team in defenses.items()}
            drows = await db.execute(
                select(Player.gsis_id, Player.id).where(Player.gsis_id.in_(keys))
            )
            for gsis, pid in drows:
                if gsis is not None:
                    out.setdefault(keys[gsis], pid)

    missing = external_ids - out.keys()
    if missing and hints:
        out.update(await _match_by_hint(db, platform, {m: hints[m] for m in missing if m in hints}))

    still = sorted(external_ids - out.keys())
    if still:
        log.warning("unmapped_players", platform=platform, count=len(still), sample=still[:10])
    return out


async def _match_by_hint(
    db: AsyncSession, platform: Platform, hints: Mapping[str, PlayerHint]
) -> dict[str, int]:
    """Unique name + position + team matches; writes the platform id back on the player."""
    found: dict[str, int] = {}
    if not hints:
        return found
    column = _id_column(platform)
    for ext, hint in hints.items():
        stmt = select(Player).where(Player.position == hint.position)
        team = canonical_team(hint.team)
        if team:
            stmt = stmt.where(Player.nfl_team == team)
        wanted = normalize_name(hint.name)
        candidates = [p for p in await db.scalars(stmt) if normalize_name(p.name) == wanted]
        if len(candidates) != 1:
            continue  # none or ambiguous: never guess
        player = candidates[0]
        if platform_player_id(player, platform) in (None, ext):
            setattr(player, column.key, ext)
        found[ext] = player.id
    if found:
        await db.flush()
    return found
