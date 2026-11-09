"""Read-side assembly for the Matchup, Lineup, Player and Accuracy screens (API side).

Reads only PostgreSQL (ADR-016): rosters and scores from the last sync, projections from the
worker, final stats from nflverse. Never calls a platform or recomputes a projection.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    League,
    LeagueMembership,
    Matchup,
    Player,
    PlayerWeekStats,
    Projection,
    ProjectionGrade,
    RosterEntry,
    Team,
)
from app.errors import ApiError, NotFound
from app.model import metrics
from app.model.distribution import load_calibration
from app.model.lineup import LineupPlayer, optimal_lineup
from app.model.projection import MODEL_VERSION
from app.model.scoring import check_rules, score, scoring_key
from app.model.winprob import SimPlayer, simulate
from app.nfl_teams import espn_headshot_url, espn_logo_url
from app.schemas import (
    AccuracyOut,
    AccuracyWeek,
    Factor,
    GameLine,
    LineupOut,
    MatchupOut,
    PlayerLine,
    PlayerProjectionOut,
    ProjectionOut,
    SwapOut,
    TeamSide,
    WinOutlook,
)
from app.services.projections import GameInfo, has_kicked_off, week_games


@dataclass
class WeekData:
    league: League
    week: int
    key: str
    players: dict[int, Player]
    projections: dict[int, Projection]
    games: dict[str, GameInfo]
    actuals: dict[int, float]  # player_id -> final points (games that are final)
    final_teams: set[str]
    now: datetime


def headshot(p: Player) -> str | None:
    if p.position == "DEF" and p.nfl_team:
        return espn_logo_url(p.nfl_team)
    return espn_headshot_url(p.espn_id) if p.espn_id else None


async def load_week(db: AsyncSession, league: League, week: int, player_ids: set[int]) -> WeekData:
    key = league.scoring_key or scoring_key(league.scoring_rules)
    players = {p.id: p for p in await db.scalars(select(Player).where(Player.id.in_(player_ids)))}
    projections = {
        pr.player_id: pr
        for pr in await db.scalars(
            select(Projection).where(
                Projection.player_id.in_(player_ids),
                Projection.season == league.season,
                Projection.week == week,
                Projection.scoring_key == key,
                Projection.model_version == MODEL_VERSION,
            )
        )
    }
    games = await week_games(db, league.season, week)
    final_teams = await _final_teams(db, league.season, week)

    gsis = {p.gsis_id: p.id for p in players.values() if p.gsis_id}
    rows = (
        await db.scalars(
            select(PlayerWeekStats).where(
                PlayerWeekStats.season == league.season,
                PlayerWeekStats.week == week,
                PlayerWeekStats.gsis_id.in_(list(gsis)),
            )
        )
    ).all()
    actuals: dict[int, float] = {}
    if rows:
        frame = pd.DataFrame([{**r.stats, "position": r.position} for r in rows])
        for r, pts in zip(rows, score(frame, league.scoring_rules), strict=True):
            actuals[gsis[r.gsis_id]] = float(pts)
    for pid, p in players.items():  # final game, no stat row: scored 0
        if p.nfl_team in final_teams and pid not in actuals:
            actuals[pid] = 0.0
    return WeekData(league, week, key, players, projections, games, actuals, final_teams,
                    datetime.now(UTC))  # fmt: skip


async def _final_teams(db: AsyncSession, season: int, week: int) -> set[str]:
    from app.db.models import NflGame

    games = await db.scalars(
        select(NflGame).where(
            NflGame.season == season, NflGame.week == week, NflGame.home_score.is_not(None)
        )
    )
    return {t for g in games for t in (g.home, g.away)}


def player_line(w: WeekData, player_id: int, slot: str) -> PlayerLine:
    p = w.players[player_id]
    game = w.games.get(p.nfl_team or "")
    if game is None:
        status, opp = "bye", None
    elif p.nfl_team in w.final_teams:
        status, opp = "final", None
    elif has_kicked_off(game, w.now):
        status, opp = "in_progress", None
    else:
        status, opp = "upcoming", None
    if game is not None:
        opp = ("vs " if game.home else "@") + game.opponent
    proj = w.projections.get(player_id)
    return PlayerLine(
        player_id=p.id,
        name=p.name,
        position=p.position,
        nfl_team=p.nfl_team,
        headshot_url=headshot(p),
        slot=slot,
        injury_status=p.injury_status,
        opponent=opp,
        kickoff_at=game.kickoff_at if game else None,
        game_status=status,
        projection=ProjectionOut.model_validate(proj) if proj else None,
        actual_points=w.actuals.get(player_id) if status == "final" else None,
    )


def sim_player(line: PlayerLine, floor: float) -> SimPlayer:
    if line.actual_points is not None:
        a = line.actual_points
        return SimPlayer(a, a, a, a)
    if line.projection is None:
        return SimPlayer(0, 0, 0, 0)
    pr = line.projection
    return SimPlayer(pr.p10, pr.p50, pr.p90, min(floor, pr.p10))


def _floors() -> dict[str, float]:
    return {pos: fit.floor for pos, fit in load_calibration(MODEL_VERSION).positions.items()}


def projected_total(lines: list[PlayerLine]) -> float:
    return round(
        sum(
            ln.actual_points
            if ln.actual_points is not None
            else (ln.projection.points if ln.projection else 0.0)
            for ln in lines
        ),
        2,
    )


async def _roster(db: AsyncSession, team_id: int, week: int) -> list[RosterEntry]:
    return list(
        await db.scalars(
            select(RosterEntry).where(RosterEntry.team_id == team_id, RosterEntry.week == week)
        )
    )


def _slot_order(league: League, entries: list[RosterEntry]) -> list[RosterEntry]:
    order = {s: i for i, s in enumerate(dict.fromkeys(league.roster_slots))}
    return sorted(entries, key=lambda e: (order.get(e.slot, 99), e.id))


def _resolve_week(league: League, week: int | None) -> int:
    week = week or league.current_week
    if week is None:
        raise ApiError(409, "not_synced", "This league hasn't finished its first sync yet")
    if not 1 <= week <= 18:
        raise ApiError(422, "invalid", "week must be between 1 and 18")
    return week


def _my_team_id(m: LeagueMembership) -> int:
    if m.my_team_id is None:
        raise ApiError(409, "team_not_chosen", "Choose your team in this league first")
    return m.my_team_id


async def _side(
    db: AsyncSession, w: WeekData, team: Team, entries: list[RosterEntry], score: float | None
) -> TeamSide:
    starters = [player_line(w, e.player_id, e.slot) for e in entries if e.is_starter]
    return TeamSide(
        team_id=team.id,
        name=team.name,
        owner_name=team.owner_name,
        avatar_url=team.avatar_url,
        record=f"{team.wins}-{team.losses}" + (f"-{team.ties}" if team.ties else ""),
        score=score,
        projected_total=projected_total(starters),
        starters=starters,
    )


def outlook(mine: list[PlayerLine], theirs: list[PlayerLine]) -> WinOutlook:
    floors = _floors()
    r = simulate(
        [sim_player(ln, floors.get(ln.position or "", 0.0)) for ln in mine],
        [sim_player(ln, floors.get(ln.position or "", 0.0)) for ln in theirs],
    )
    return WinOutlook(
        win_probability=r.win_prob,
        my_median=r.my_median,
        opponent_median=r.opp_median,
        my_range=(r.my_p10, r.my_p90),
        opponent_range=(r.opp_p10, r.opp_p90),
    )


# --------------------------------------------------------------------------- screens
async def matchup_view(
    db: AsyncSession, league: League, m: LeagueMembership, week: int | None
) -> MatchupOut:
    week = _resolve_week(league, week)
    my_id = _my_team_id(m)
    row = await db.scalar(
        select(Matchup).where(
            Matchup.league_id == league.id,
            Matchup.week == week,
            (Matchup.home_team_id == my_id) | (Matchup.away_team_id == my_id),
        )
    )
    opp_id = None
    my_score = opp_score = None
    if row is not None:
        mine_home = row.home_team_id == my_id
        opp_id = row.away_team_id if mine_home else row.home_team_id
        my_score = row.home_score if mine_home else row.away_score
        opp_score = row.away_score if mine_home else row.home_score

    my_entries = await _roster(db, my_id, week)
    opp_entries = await _roster(db, opp_id, week) if opp_id else []
    ids = {e.player_id for e in my_entries + opp_entries}
    w = await load_week(db, league, week, ids)

    my_team = await db.get(Team, my_id)
    assert my_team is not None
    me = await _side(db, w, my_team, _slot_order(league, my_entries), my_score)
    opponent = None
    if opp_id:
        opp_team = await db.get(Team, opp_id)
        assert opp_team is not None
        opponent = await _side(db, w, opp_team, _slot_order(league, opp_entries), opp_score)
    return MatchupOut(
        league_id=league.id,
        week=week,
        as_of=league.last_synced_at,
        model_version=MODEL_VERSION,
        me=me,
        opponent=opponent,
        outlook=outlook(me.starters, opponent.starters) if opponent else None,
        unsupported_rules=sorted(check_rules(league.scoring_rules).unsupported),
    )


async def lineup_view(
    db: AsyncSession, league: League, m: LeagueMembership, week: int | None
) -> LineupOut:
    week = _resolve_week(league, week)
    my_id = _my_team_id(m)
    entries = _slot_order(league, await _roster(db, my_id, week))
    w = await load_week(db, league, week, {e.player_id for e in entries})
    lines = {e.player_id: player_line(w, e.player_id, e.slot) for e in entries}

    def pts(ln: PlayerLine) -> float:
        if ln.actual_points is not None:
            return ln.actual_points
        return ln.projection.points if ln.projection else 0.0

    roster = [
        LineupPlayer(
            player_id=e.player_id,
            position=w.players[e.player_id].position or "",
            points=pts(lines[e.player_id]),
            current_slot=e.slot,
            locked=lines[e.player_id].game_status in ("in_progress", "final"),
        )
        for e in entries
    ]
    result = optimal_lineup(league.roster_slots, roster)

    # Win chance now vs with the optimal lineup, against this week's opponent.
    opp_lines: list[PlayerLine] = []
    row = await db.scalar(
        select(Matchup).where(
            Matchup.league_id == league.id,
            Matchup.week == week,
            (Matchup.home_team_id == my_id) | (Matchup.away_team_id == my_id),
        )
    )
    if row is not None:
        opp_id = row.away_team_id if row.home_team_id == my_id else row.home_team_id
        if opp_id:
            opp_entries = [e for e in await _roster(db, opp_id, week) if e.is_starter]
            ow = await load_week(db, league, week, {e.player_id for e in opp_entries})
            opp_lines = [player_line(ow, e.player_id, e.slot) for e in opp_entries]

    starters = [lines[e.player_id] for e in entries if e.is_starter]
    optimal_lines = [lines[pid] for _, pid in result.slots if pid is not None]
    win_now = win_best = None
    if opp_lines:
        win_now = outlook(starters, opp_lines).win_probability
        win_best = outlook(optimal_lines, opp_lines).win_probability

    return LineupOut(
        league_id=league.id,
        week=week,
        as_of=league.last_synced_at,
        model_version=MODEL_VERSION,
        starters=starters,
        bench=[lines[e.player_id] for e in entries if not e.is_starter],
        optimal=result.slots,
        swaps=[
            SwapOut(
                slot=s.slot,
                player_in=lines[s.player_in],
                player_out=lines[s.player_out] if s.player_out is not None else None,
                gain=s.gain,
            )
            for s in result.swaps
        ],
        current_points=result.current_points,
        optimal_points=result.optimal_points,
        win_probability_current=win_now,
        win_probability_optimal=win_best,
    )


async def player_projection_view(
    db: AsyncSession, league: League, player_id: int, week: int | None
) -> PlayerProjectionOut:
    week = _resolve_week(league, week)
    player = await db.get(Player, player_id)
    if player is None:
        raise NotFound("Player not found", code="player_not_found")
    w = await load_week(db, league, week, {player_id})
    entry = await db.scalar(
        select(RosterEntry.slot)
        .join(Team, Team.id == RosterEntry.team_id)
        .where(Team.league_id == league.id, RosterEntry.week == week,
               RosterEntry.player_id == player_id)
    )  # fmt: skip
    line = player_line(w, player_id, entry or "FA")
    proj = w.projections.get(player_id)

    recent: list[GameLine] = []
    if player.gsis_id:
        rows = (
            await db.scalars(
                select(PlayerWeekStats)
                .where(
                    PlayerWeekStats.gsis_id == player.gsis_id,
                    PlayerWeekStats.season == league.season,
                    PlayerWeekStats.week < week,
                )
                .order_by(PlayerWeekStats.week.desc())
                .limit(4)
            )
        ).all()
        if rows:
            frame = pd.DataFrame([{**r.stats, "position": r.position} for r in rows])
            recent = [
                GameLine(week=r.week, opponent=r.opponent, points=float(p))
                for r, p in zip(rows, score(frame, league.scoring_rules), strict=True)
            ]
    return PlayerProjectionOut(
        player=line,
        factors=[Factor(**f) for f in (proj.factors if proj else [])],
        recent_games=recent,
        unsupported_rules=sorted(check_rules(league.scoring_rules).unsupported),
    )


async def accuracy_view(db: AsyncSession, league: League) -> AccuracyOut:
    """Genuine (pre-kickoff), graded projections for players rostered in this league."""
    key = league.scoring_key or scoring_key(league.scoring_rules)
    rostered = (
        select(RosterEntry.player_id)
        .join(Team, Team.id == RosterEntry.team_id)
        .where(Team.league_id == league.id)
    )
    rows = (
        await db.execute(
            select(Projection, ProjectionGrade, Player.position)
            .join(ProjectionGrade, ProjectionGrade.projection_id == Projection.id)
            .join(Player, Player.id == Projection.player_id)
            .where(
                Projection.scoring_key == key,
                Projection.season == league.season,
                Projection.model_version == MODEL_VERSION,
                Projection.player_id.in_(rostered),
                ProjectionGrade.genuine.is_(True),
            )
        )
    ).all()
    if not rows:
        return AccuracyOut(league_id=league.id, model_version=MODEL_VERSION, n=0, mae=None,
                           bias=None, coverage_80=None, by_position={}, weeks=[])  # fmt: skip
    df = pd.DataFrame(
        [
            {"position": pos, "season": pr.season, "week": pr.week, "proj": pr.points,
             "actual": g.actual_points, "p10": pr.p10, "p90": pr.p90}
            for pr, g, pos in rows
        ]
    )  # fmt: skip
    overall = metrics.grade(df)
    by_pos: dict[str, dict[str, Any]] = metrics.grade_by_position(df)
    weeks = []
    for wk, g in df.groupby("week"):
        graded = metrics.grade(g)
        weeks.append(
            AccuracyWeek(
                week=int(str(wk)),
                n=len(g),
                mae=round(graded["mae"], 2),
                coverage_80=round(graded["coverage_80"], 3),
            )
        )
    return AccuracyOut(
        league_id=league.id,
        model_version=MODEL_VERSION,
        n=overall["n"],
        mae=round(overall["mae"], 2),
        bias=round(overall["bias"], 2),
        coverage_80=round(overall["coverage_80"], 3),
        by_position={
            pos: {
                "n": float(v["n"]),
                "mae": round(v["mae"], 2),
                "coverage_80": round(v["coverage_80"], 3),
            }
            for pos, v in by_pos.items()
        },
        weeks=weeks,
    )
