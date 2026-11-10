"""Screen endpoints: matchup, lineup, player, accuracy, waivers, trades (docs/Specs/API.md)."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query

from app.auth.deps import DB, CurrentUser, Membership, get_membership, require_league
from app.db.models import League
from app.errors import error_responses
from app.schemas import (
    AccuracyOut,
    LineupOut,
    MatchupOut,
    PlayerProjectionOut,
    TradeEvaluateIn,
    TradeEvaluationOut,
    TradeRostersOut,
    TradeSuggestionsOut,
    WaiversOut,
)
from app.services import trades, views, waivers

router = APIRouter(prefix="/api/v1", tags=["views"], responses=error_responses())
LeagueDep = Annotated[League, Depends(require_league)]
Week = Annotated[int | None, Query(ge=1, le=18, description="Defaults to the current week")]


@router.get("/leagues/{league_id}/matchup", response_model=MatchupOut)
async def get_matchup(
    league: LeagueDep, membership: Membership, db: DB, week: Week = None
) -> MatchupOut:
    """Head-to-head: both lineups with projections and ranges, win probability, scores."""
    return await views.matchup_view(db, league, membership, week)


@router.get("/leagues/{league_id}/lineup", response_model=LineupOut)
async def get_lineup(
    league: LeagueDep, membership: Membership, db: DB, week: Week = None
) -> LineupOut:
    """My lineup: current vs optimal, swap suggestions, win chance before/after."""
    return await views.lineup_view(db, league, membership, week)


@router.get("/leagues/{league_id}/accuracy", response_model=AccuracyOut)
async def get_accuracy(league: LeagueDep, db: DB) -> AccuracyOut:
    """How frozen, pre-kickoff projections compared with actual results in past weeks."""
    return await views.accuracy_view(db, league)


@router.get("/players/{player_id}/projection", response_model=PlayerProjectionOut)
async def get_player_projection(
    player_id: int,
    user: CurrentUser,
    db: DB,
    league_id: Annotated[int, Query(description="Scores with this league's rules")],
    week: Week = None,
) -> PlayerProjectionOut:
    """One player's projection with every factor, range, and recent games."""
    membership = await get_membership(db, user, league_id)
    league = await db.get(League, membership.league_id)
    assert league is not None
    return await views.player_projection_view(db, league, player_id, week)


@router.get("/leagues/{league_id}/waivers", response_model=WaiversOut)
async def get_waivers(
    league: LeagueDep,
    membership: Membership,
    db: DB,
    horizon: Annotated[
        Literal["ros", "week"], Query(description="Rest of season (default) or this week")
    ] = "ros",
) -> WaiversOut:
    """Free agents ranked by points they'd add to my best lineup, with a suggested drop,
    waiver status and (FAAB leagues) a bid guide (ADR-047)."""
    return await waivers.waivers_view(db, league, membership, horizon)


@router.get("/leagues/{league_id}/trades/rosters", response_model=TradeRostersOut)
async def get_trade_rosters(league: LeagueDep, membership: Membership, db: DB) -> TradeRostersOut:
    """Every team's roster with rest-of-season points per week, to build a trade from."""
    return await trades.trade_rosters_view(db, league, membership)


@router.post("/leagues/{league_id}/trades/evaluate", response_model=TradeEvaluationOut)
async def evaluate_trade(
    body: TradeEvaluateIn, league: LeagueDep, membership: Membership, db: DB
) -> TradeEvaluationOut:
    """Lineup impact of a trade between any two teams in the league (ADR-048)."""
    return await trades.evaluate_trade_view(db, league, body)


@router.get("/leagues/{league_id}/trades/suggestions", response_model=TradeSuggestionsOut)
async def get_trade_suggestions(
    league: LeagueDep,
    membership: Membership,
    db: DB,
    max_loss: Annotated[
        float,
        Query(
            ge=0,
            le=trades.MAX_LOSS_CAP,
            description="Most the other team may lose, in points per week",
        ),
    ] = 1.0,
) -> TradeSuggestionsOut:
    """Trades that help my lineup most while the other team loses at most `max_loss`."""
    return await trades.trade_suggestions_view(db, league, membership, max_loss)
