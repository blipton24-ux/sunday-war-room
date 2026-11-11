"""League sync: adapter output -> PostgreSQL. Called only from worker jobs, never a request.

All writes are idempotent upserts, so a retried or repeated sync converges on the same rows.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.base import (
    LeagueAdapter,
    LeagueData,
    LeagueRef,
    MatchupData,
    PlayerData,
    RosterSpot,
    TransactionData,
)
from app.db.models import League, LeagueTransaction, Matchup, Player, RosterEntry, Team
from app.logging import get_logger
from app.model.scoring import scoring_key
from app.services.player_ids import resolve_player_ids

log = get_logger("sync")
BATCH = 1000


def _chunks(rows: Sequence[dict[str, Any]], n: int = BATCH) -> Iterable[Sequence[dict[str, Any]]]:
    for i in range(0, len(rows), n):
        yield rows[i : i + n]


# --------------------------------------------------------------------------- players
async def upsert_platform_players(
    db: AsyncSession, platform: str, players: Sequence[PlayerData]
) -> int:
    """Insert/update the master player list, keyed by Sleeper's id (ADR-053).

    Sleeper's list is the master for every platform; ESPN and Yahoo ids are matched against it
    (services/player_ids.py). nflverse ids (gsis_id) are NOT taken from the platform: the
    nflverse crosswalk owns them, which avoids two sources fighting over a unique column.
    """
    assert platform == "sleeper", "only Sleeper's list is the master player list"
    rows = [
        {
            "sleeper_id": p.external_id,
            "name": p.name,
            "position": p.position,
            "nfl_team": p.nfl_team,
            "status": p.status,
            "injury_status": p.injury_status,
            "depth_chart_order": p.depth_chart_order,
            "espn_id": p.espn_id,
            "yahoo_id": p.yahoo_id,
        }
        for p in players
    ]
    for chunk in _chunks(rows):
        stmt = insert(Player).values(list(chunk))
        ex = stmt.excluded
        await db.execute(
            stmt.on_conflict_do_update(
                index_elements=[Player.sleeper_id],
                set_={
                    "name": ex.name,
                    "position": ex.position,
                    "nfl_team": ex.nfl_team,
                    "status": ex.status,
                    "injury_status": ex.injury_status,
                    "depth_chart_order": ex.depth_chart_order,
                    "espn_id": ex.espn_id,
                    "yahoo_id": ex.yahoo_id,
                    "updated_at": datetime.now(UTC),
                },
            )
        )
    await db.commit()
    return len(rows)


# --------------------------------------------------------------------------- league
async def upsert_league(db: AsyncSession, data: LeagueData, current_week: int | None) -> League:
    stmt = insert(League).values(
        platform=data.ref.platform,
        external_id=data.ref.external_id,
        season=data.ref.season,
        name=data.ref.name,
        avatar_url=data.avatar_url,
        scoring_rules=data.scoring_rules,
        scoring_key=scoring_key(data.scoring_rules),
        roster_slots=data.roster_slots,
        current_week=current_week,
        waiver_rules=asdict(data.waivers),
        season_rules=asdict(data.season_rules),
    )
    ex = stmt.excluded
    upsert = stmt.on_conflict_do_update(
        index_elements=[League.platform, League.external_id, League.season],
        set_={
            "name": ex.name,
            "avatar_url": ex.avatar_url,
            "scoring_rules": ex.scoring_rules,
            "scoring_key": ex.scoring_key,
            "roster_slots": ex.roster_slots,
            "current_week": ex.current_week,
            "waiver_rules": ex.waiver_rules,
            "season_rules": ex.season_rules,
        },
    ).returning(League.id)
    league_id = (await db.execute(upsert)).scalar_one()
    league = await db.get(League, league_id, populate_existing=True)
    assert league is not None
    return league


async def _replace_roster_week(
    db: AsyncSession,
    team_id: int,
    week: int,
    spots: Sequence[RosterSpot],
    player_ids: dict[str, int],
) -> list[str]:
    """Replace one team's snapshot for one week. Returns platform ids we couldn't map."""
    await db.execute(
        delete(RosterEntry).where(RosterEntry.team_id == team_id, RosterEntry.week == week)
    )
    missing = [s.player_external_id for s in spots if s.player_external_id not in player_ids]
    rows = [
        {
            "team_id": team_id,
            "week": week,
            "player_id": player_ids[s.player_external_id],
            "slot": s.slot,
            "is_starter": s.is_starter,
        }
        for s in spots
        if s.player_external_id in player_ids
    ]
    if rows:
        await db.execute(insert(RosterEntry).values(rows))
    return missing


async def _upsert_matchups(
    db: AsyncSession,
    league_id: int,
    week: int,
    rows: Sequence[MatchupData],
    team_ids: dict[str, int],
    player_ids: dict[str, int] | None = None,
) -> None:
    """Upsert one week's pairings, scores and (P2) fantasy points so far per player."""
    ids = player_ids or {}

    def points(r: MatchupData | None) -> dict[str, float]:
        if r is None:
            return {}
        return {str(ids[pid]): pts for pid, pts in r.player_points.items() if pid in ids}

    by_key: dict[str | None, list[MatchupData]] = defaultdict(list)
    for r in rows:
        by_key[r.matchup_key].append(r)

    pairs: list[tuple[MatchupData, MatchupData | None]] = []
    for key, group in by_key.items():
        group.sort(key=lambda r: int(r.team_external_id) if r.team_external_id.isdigit() else 0)
        if key is None:  # bye weeks / median formats: no opponent
            pairs.extend((g, None) for g in group)
        else:
            pairs.append((group[0], group[1] if len(group) > 1 else None))

    for home, away in pairs:
        stmt = insert(Matchup).values(
            league_id=league_id,
            week=week,
            home_team_id=team_ids[home.team_external_id],
            away_team_id=team_ids[away.team_external_id] if away else None,
            home_score=home.points,
            away_score=away.points if away else None,
            home_player_points=points(home),
            away_player_points=points(away),
            updated_at=datetime.now(UTC),
        )
        ex = stmt.excluded
        await db.execute(
            stmt.on_conflict_do_update(
                index_elements=[Matchup.league_id, Matchup.week, Matchup.home_team_id],
                set_={
                    k: getattr(ex, k)
                    for k in ("away_team_id", "home_score", "away_score", "home_player_points",
                              "away_player_points", "updated_at")
                },
            )
        )  # fmt: skip


async def sync_league(
    db: AsyncSession,
    adapter: LeagueAdapter,
    external_id: str,
    *,
    current_week: int,
    history_weeks: Iterable[int] = (),
) -> League:
    """Pull one league's settings, teams, rosters and matchups into the database.

    `current_week`: rosters come from the live roster endpoint (reflects today's moves).
    `history_weeks`: past weeks, rebuilt from that week's matchup lineups and final scores.
    """
    data = await adapter.fetch_league(external_id)
    league = await upsert_league(db, data, current_week)
    teams = await adapter.fetch_teams(data)

    for t in teams:
        stmt = insert(Team).values(
            league_id=league.id,
            external_id=t.external_id,
            owner_external_id=t.owner_external_id,
            name=t.name,
            owner_name=t.owner_name,
            avatar_url=t.avatar_url,
            wins=t.wins,
            losses=t.losses,
            ties=t.ties,
            waiver_position=t.waiver_position,
            waiver_budget_used=t.waiver_budget_used,
        )
        ex = stmt.excluded
        await db.execute(
            stmt.on_conflict_do_update(
                index_elements=[Team.league_id, Team.external_id],
                set_={
                    k: getattr(ex, k)
                    for k in ("owner_external_id", "name", "owner_name", "avatar_url")
                }
                | {k: getattr(ex, k) for k in ("wins", "losses", "ties")}
                | {k: getattr(ex, k) for k in ("waiver_position", "waiver_budget_used")},
            )
        )
    team_rows = await db.execute(
        select(Team.external_id, Team.id).where(Team.league_id == league.id)
    )
    team_ids = {ext: tid for ext, tid in team_rows}

    weeks = sorted(set(history_weeks) | {current_week})
    matchups_by_week = {w: await adapter.fetch_matchups(data, w) for w in weeks}

    spots = [s for t in teams for s in t.roster] + [
        s for rows in matchups_by_week.values() for r in rows for s in r.roster
    ]
    all_ids = {s.player_external_id for s in spots}
    hints = {s.player_external_id: s.hint for s in spots if s.hint is not None}
    player_ids = await resolve_player_ids(db, data.ref.platform, all_ids, hints)

    unmapped: set[str] = set()
    for t in teams:
        unmapped |= set(
            await _replace_roster_week(
                db, team_ids[t.external_id], current_week, t.roster, player_ids
            )
        )
    for w, rows in matchups_by_week.items():
        if w != current_week:
            for r in rows:
                unmapped |= set(
                    await _replace_roster_week(
                        db, team_ids[r.team_external_id], w, r.roster, player_ids
                    )
                )
        await _upsert_matchups(db, league.id, w, rows, team_ids, player_ids)

    # Waiver status needs recent drops; claim windows are a few days, so this and last week.
    tx_weeks = sorted({w for w in (current_week - 1, current_week) if w >= 1})
    transactions = [t for w in tx_weeks for t in await adapter.fetch_transactions(data, w)]
    await upsert_transactions(db, league.id, transactions)

    league.last_synced_at = datetime.now(UTC)
    await db.commit()
    log.info(
        "league_synced",
        league_id=league.id,
        external_id=external_id,
        teams=len(teams),
        weeks=weeks,
        unmapped_players=sorted(unmapped)[:20],
    )
    return league


async def upsert_transactions(
    db: AsyncSession, league_id: int, transactions: Sequence[TransactionData]
) -> None:
    # One row per transaction id: a platform may report the same move in two weekly reads, and
    # Postgres refuses to update one row twice in a single statement. The later read wins.
    unique = {t.external_id: t for t in transactions}
    rows = [
        {
            "league_id": league_id,
            "external_id": t.external_id,
            "kind": t.kind,
            "status": t.status,
            "week": t.week,
            "created_at": t.created_at,
            "adds": t.adds,
            "drops": t.drops,
            "waiver_bid": t.waiver_bid,
        }
        for t in unique.values()
    ]
    for chunk in _chunks(rows):
        stmt = insert(LeagueTransaction).values(list(chunk))
        await db.execute(
            stmt.on_conflict_do_update(
                index_elements=[LeagueTransaction.league_id, LeagueTransaction.external_id],
                set_={"status": stmt.excluded.status, "waiver_bid": stmt.excluded.waiver_bid},
            )
        )


async def players_are_stale(db: AsyncSession, max_age_hours: float = 24) -> bool:
    """True when the player table is empty or hasn't been refreshed recently."""
    newest: datetime | None = await db.scalar(select(func.max(Player.updated_at)))
    if newest is None:
        return True
    return (datetime.now(UTC) - newest).total_seconds() > max_age_hours * 3600


async def refresh_live_matchups(
    db: AsyncSession, adapter: LeagueAdapter, league: League, week: int
) -> int:
    """Live game day (P2): re-read only this week's scores and per-player points."""
    data = LeagueData(
        ref=LeagueRef(league.platform, league.external_id, league.season, league.name),  # type: ignore[arg-type]
        avatar_url=league.avatar_url,
        scoring_rules=league.scoring_rules,
        roster_slots=league.roster_slots,
        status="in_season",
    )
    rows = await adapter.fetch_matchups(data, week)
    team_rows = await db.execute(
        select(Team.external_id, Team.id).where(Team.league_id == league.id)
    )
    team_ids = {ext: tid for ext, tid in team_rows}
    rows = [r for r in rows if r.team_external_id in team_ids]
    player_ids = await resolve_player_ids(
        db, data.ref.platform, {pid for r in rows for pid in r.player_points}
    )
    await _upsert_matchups(db, league.id, week, rows, team_ids, player_ids)
    await db.commit()
    return len(rows)
