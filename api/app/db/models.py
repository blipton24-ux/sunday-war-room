"""SQLAlchemy models for P1 (docs/Specs/Data-Model.md).

Schema changes only through Alembic migrations (ADR-015).

The first four tables are the ones Better Auth reads and writes from the web app
(ADR-035). Their shape must match what `npm run auth:schema` (web/) prints for our field
mapping in web/src/lib/server/auth-schema.ts; Better Auth checks this at startup.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Identity,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

TZ = DateTime(timezone=True)


# --------------------------------------------------------------------------- accounts (Better Auth)
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    email: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    email_verified: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    image: Mapped[str | None] = mapped_column(Text)
    # Ours, not Better Auth's: room for a paid tier later (ADR-011).
    plan: Mapped[str] = mapped_column(String(20), default="free", server_default="free")
    created_at: Mapped[datetime] = mapped_column(TZ, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        TZ, nullable=False, server_default=func.now(), onupdate=func.now()
    )


class AuthSession(Base):
    """A signed-in browser session (the cookie holds `token`). Written by Better Auth."""

    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    expires_at: Mapped[datetime] = mapped_column(TZ, nullable=False)
    token: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(TZ, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TZ, nullable=False)
    ip_address: Mapped[str | None] = mapped_column(Text)
    user_agent: Mapped[str | None] = mapped_column(Text)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )


class AuthAccount(Base):
    """A sign-in method linked to a user (e.g. Google). Written by Better Auth."""

    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    account_id: Mapped[str] = mapped_column(Text, nullable=False)
    provider_id: Mapped[str] = mapped_column(Text, nullable=False)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    access_token: Mapped[str | None] = mapped_column(Text)
    refresh_token: Mapped[str | None] = mapped_column(Text)
    id_token: Mapped[str | None] = mapped_column(Text)
    access_token_expires_at: Mapped[datetime | None] = mapped_column(TZ)
    refresh_token_expires_at: Mapped[datetime | None] = mapped_column(TZ)
    scope: Mapped[str | None] = mapped_column(Text)
    password: Mapped[str | None] = mapped_column(Text)  # unused: no passwords (ADR-017)
    created_at: Mapped[datetime] = mapped_column(TZ, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TZ, nullable=False)


class Verification(Base):
    """One-time values such as magic-link tokens. Written by Better Auth."""

    __tablename__ = "verifications"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    identifier: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(TZ, nullable=False)
    created_at: Mapped[datetime] = mapped_column(TZ, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TZ, nullable=False, server_default=func.now())


# --------------------------------------------------------------------------- platform connections
class PlatformAccount(Base):
    __tablename__ = "platform_accounts"
    __table_args__ = (UniqueConstraint("user_id", "platform"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    platform: Mapped[str] = mapped_column(String(20))  # sleeper / espn / yahoo
    external_user_id: Mapped[str] = mapped_column(String(64))
    display_name: Mapped[str | None] = mapped_column(String(255))
    # ESPN cookies / Yahoo tokens, encrypted by app/crypto.py (ADR-052). Never returned by the
    # API, logged, or passed as a job argument; Sleeper needs none.
    credentials_encrypted: Mapped[str | None] = mapped_column(Text)
    # ok / pending (just saved, not yet checked) / needs_reconnect (the platform refused them).
    status: Mapped[str] = mapped_column(String(20), server_default="ok", default="ok")
    credentials_checked_at: Mapped[datetime | None] = mapped_column(TZ)
    created_at: Mapped[datetime] = mapped_column(TZ, server_default=func.now())


class LeagueMembership(Base):
    """Which leagues a user follows and which team is theirs. **The tenant boundary.**"""

    __tablename__ = "league_memberships"
    __table_args__ = (UniqueConstraint("user_id", "league_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    league_id: Mapped[int] = mapped_column(ForeignKey("leagues.id", ondelete="CASCADE"), index=True)
    my_team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id", ondelete="SET NULL"))
    # The account whose credentials this follower reads a private league with (ADR-051): each
    # user's own cookies only, never a league-mate's. NULL for public leagues and Sleeper.
    platform_account_id: Mapped[int | None] = mapped_column(
        ForeignKey("platform_accounts.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(TZ, server_default=func.now())

    league: Mapped[League] = relationship(lazy="raise")


# --------------------------------------------------------------------------- leagues (shared)
class League(Base):
    """One row per real platform league, shared by every user who follows it."""

    __tablename__ = "leagues"
    __table_args__ = (UniqueConstraint("platform", "external_id", "season"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    platform: Mapped[str] = mapped_column(String(20))
    external_id: Mapped[str] = mapped_column(String(64))
    season: Mapped[int] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String(255))
    avatar_url: Mapped[str | None] = mapped_column(Text)
    scoring_rules: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    # Hash of scoring_rules (app/model/scoring.py): leagues sharing it share projections.
    scoring_key: Mapped[str | None] = mapped_column(String(64), index=True)
    roster_slots: Mapped[list[str]] = mapped_column(JSONB, default=list)
    current_week: Mapped[int | None] = mapped_column(Integer)
    last_synced_at: Mapped[datetime | None] = mapped_column(TZ)
    # app.adapters.base.WaiverRules / SeasonRules as JSON (ADR-046); {} until the first P2 sync.
    waiver_rules: Mapped[dict[str, Any]] = mapped_column(
        JSONB, default=dict, server_default=text("'{}'::jsonb")
    )
    season_rules: Mapped[dict[str, Any]] = mapped_column(
        JSONB, default=dict, server_default=text("'{}'::jsonb")
    )


class Team(Base):
    __tablename__ = "teams"
    __table_args__ = (UniqueConstraint("league_id", "external_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    league_id: Mapped[int] = mapped_column(ForeignKey("leagues.id", ondelete="CASCADE"), index=True)
    external_id: Mapped[str] = mapped_column(String(64))  # Sleeper roster_id
    owner_external_id: Mapped[str | None] = mapped_column(String(64))  # Sleeper user_id
    name: Mapped[str] = mapped_column(String(255))
    owner_name: Mapped[str | None] = mapped_column(String(255))
    avatar_url: Mapped[str | None] = mapped_column(Text)
    wins: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    losses: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    ties: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    waiver_position: Mapped[int | None] = mapped_column(Integer)
    waiver_budget_used: Mapped[int | None] = mapped_column(Integer)


class RosterEntry(Base):
    """Weekly roster snapshot: one row per player per team per week."""

    __tablename__ = "roster_entries"
    __table_args__ = (UniqueConstraint("team_id", "week", "player_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"), index=True)
    week: Mapped[int] = mapped_column(Integer)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), index=True)
    slot: Mapped[str] = mapped_column(String(16))  # QB/RB/WR/TE/FLEX/SUPER_FLEX/K/DEF/BN/IR/TAXI
    is_starter: Mapped[bool] = mapped_column(Boolean, default=False)


class Matchup(Base):
    __tablename__ = "matchups"
    __table_args__ = (UniqueConstraint("league_id", "week", "home_team_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    league_id: Mapped[int] = mapped_column(ForeignKey("leagues.id", ondelete="CASCADE"), index=True)
    week: Mapped[int] = mapped_column(Integer)
    home_team_id: Mapped[int] = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"))
    away_team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"))
    home_score: Mapped[float | None] = mapped_column(Float)
    away_score: Mapped[float | None] = mapped_column(Float)
    # P2 live game day: fantasy points so far per player (our player id as text -> points),
    # scored by the platform with the league's rules (ADR-044).
    home_player_points: Mapped[dict[str, float]] = mapped_column(
        JSONB, default=dict, server_default=text("'{}'::jsonb")
    )
    away_player_points: Mapped[dict[str, float]] = mapped_column(
        JSONB, default=dict, server_default=text("'{}'::jsonb")
    )
    updated_at: Mapped[datetime | None] = mapped_column(TZ)


class LeagueTransaction(Base):
    """Adds, drops, waiver claims and trades, as the platform reports them (P2: waiver status)."""

    __tablename__ = "league_transactions"
    __table_args__ = (
        UniqueConstraint("league_id", "external_id"),
        Index("ix_league_transactions_league_created", "league_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    league_id: Mapped[int] = mapped_column(ForeignKey("leagues.id", ondelete="CASCADE"))
    external_id: Mapped[str] = mapped_column(String(64))
    kind: Mapped[str] = mapped_column(String(16))  # waiver / free_agent / trade / commissioner
    status: Mapped[str] = mapped_column(String(16))  # complete / failed / pending
    week: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(TZ)
    # platform player id -> platform team id
    adds: Mapped[dict[str, str]] = mapped_column(JSONB, default=dict)
    drops: Mapped[dict[str, str]] = mapped_column(JSONB, default=dict)
    waiver_bid: Mapped[int | None] = mapped_column(Integer)


# --------------------------------------------------------------------------- NFL data (shared)
class Player(Base):
    """One NFL player, with the crosswalk of every platform's id for them."""

    __tablename__ = "players"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    gsis_id: Mapped[str | None] = mapped_column(String(32), unique=True)
    sleeper_id: Mapped[str | None] = mapped_column(String(32), unique=True)
    espn_id: Mapped[str | None] = mapped_column(String(32), index=True)
    yahoo_id: Mapped[str | None] = mapped_column(String(32), index=True)
    name: Mapped[str] = mapped_column(String(255))
    position: Mapped[str | None] = mapped_column(String(8), index=True)
    nfl_team: Mapped[str | None] = mapped_column(String(8))
    status: Mapped[str | None] = mapped_column(String(32))
    injury_status: Mapped[str | None] = mapped_column(String(32))
    depth_chart_order: Mapped[int | None] = mapped_column(Integer)
    updated_at: Mapped[datetime] = mapped_column(TZ, server_default=func.now(), onupdate=func.now())


class NflGame(Base):
    __tablename__ = "nfl_games"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    game_id: Mapped[str] = mapped_column(String(32), unique=True)  # nflverse game_id
    season: Mapped[int] = mapped_column(Integer)
    week: Mapped[int] = mapped_column(Integer)
    game_type: Mapped[str] = mapped_column(String(8), default="REG")
    home: Mapped[str] = mapped_column(String(8))
    away: Mapped[str] = mapped_column(String(8))
    kickoff_at: Mapped[datetime | None] = mapped_column(TZ)
    home_score: Mapped[int | None] = mapped_column(Integer)
    away_score: Mapped[int | None] = mapped_column(Integer)
    # Betting lines from nflverse (model 1.1.0): the home team's spread (positive: home
    # favoured by that many points) and the total. Pre-game; refreshed by the daily ingest.
    spread_line: Mapped[float | None] = mapped_column(Float)
    total_line: Mapped[float | None] = mapped_column(Float)

    __table_args__ = (Index("ix_nfl_games_season_week", "season", "week"),)


class LiveGame(Base):
    """Game state from ESPN's public scoreboard during game windows (P2, ADR-044)."""

    __tablename__ = "live_games"
    __table_args__ = (UniqueConstraint("season", "week", "home"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    espn_id: Mapped[str] = mapped_column(String(32))
    season: Mapped[int] = mapped_column(Integer)
    week: Mapped[int] = mapped_column(Integer)
    home: Mapped[str] = mapped_column(String(8))
    away: Mapped[str] = mapped_column(String(8))
    kickoff_at: Mapped[datetime] = mapped_column(TZ)
    state: Mapped[str] = mapped_column(String(16))  # upcoming/in_progress/halftime/final/postponed
    period: Mapped[int] = mapped_column(Integer, default=0)
    clock_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    detail: Mapped[str] = mapped_column(String(64))
    home_score: Mapped[int | None] = mapped_column(Integer)
    away_score: Mapped[int | None] = mapped_column(Integer)
    possession: Mapped[str | None] = mapped_column(String(8))
    remaining_fraction: Mapped[float] = mapped_column(Float)
    updated_at: Mapped[datetime] = mapped_column(TZ)


class PlayerWeekStats(Base):
    """One row per player per game-week, bulk-loaded from nflverse (ADR-030).

    Raw stat columns only: fantasy points are always computed with each league's own rules.
    """

    __tablename__ = "player_week_stats"
    __table_args__ = (Index("ix_pws_season_week", "season", "week"),)

    gsis_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    season: Mapped[int] = mapped_column(Integer, primary_key=True)
    week: Mapped[int] = mapped_column(Integer, primary_key=True)
    season_type: Mapped[str] = mapped_column(String(8))
    position: Mapped[str | None] = mapped_column(String(8))
    team: Mapped[str | None] = mapped_column(String(8))
    opponent: Mapped[str | None] = mapped_column(String(8))
    # Every numeric stat column from nflverse, keyed by its nflverse name. JSONB so a new
    # upstream column doesn't need a migration; the source module's contract lists the columns
    # the model depends on and fails loudly if one disappears.
    stats: Mapped[dict[str, float]] = mapped_column(JSONB)
    offense_snap_pct: Mapped[float | None] = mapped_column(Float)


class InjuryReport(Base):
    """Weekly game-status injury report per player, from nflverse (P4).

    Kept so models can be tested on real injury history; `report_status` is the final game
    designation (Out, Doubtful, Questionable) or null for a player listed without one, and
    `roster_status` is "RES" while he is on a reserve list (injured reserve shows here, not on
    the report).
    """

    __tablename__ = "injury_reports"

    gsis_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    season: Mapped[int] = mapped_column(Integer, primary_key=True)
    week: Mapped[int] = mapped_column(Integer, primary_key=True)
    report_status: Mapped[str | None] = mapped_column(String(16))
    roster_status: Mapped[str | None] = mapped_column(String(8))  # "RES": on a reserve list
    practice_status: Mapped[str | None] = mapped_column(Text)
    injury: Mapped[str | None] = mapped_column(Text)


class PlayerStatusSnapshot(Base):
    """What the app knew about a player's injury and depth-chart status when it projected him.

    Written when a compute sees a change (not every run). nflverse has weekly injury history but
    Sleeper's live status and depth chart have none, so this is how a later model version can be
    tested on them (backlog M-11).
    """

    __tablename__ = "player_status_snapshots"

    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), primary_key=True)
    season: Mapped[int] = mapped_column(Integer, primary_key=True)
    week: Mapped[int] = mapped_column(Integer, primary_key=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    injury_status: Mapped[str | None] = mapped_column(String(32))
    depth_chart_order: Mapped[int | None] = mapped_column(Integer)


# --------------------------------------------------------------------------- projections
class Projection(Base):
    __tablename__ = "projections"
    __table_args__ = (
        UniqueConstraint("player_id", "season", "week", "scoring_key", "model_version"),
        Index("ix_proj_lookup", "season", "week", "scoring_key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), index=True)
    season: Mapped[int] = mapped_column(Integer)
    week: Mapped[int] = mapped_column(Integer)
    scoring_key: Mapped[str] = mapped_column(String(64))  # hash of the scoring rules
    points: Mapped[float] = mapped_column(Float)
    p10: Mapped[float] = mapped_column(Float)
    p50: Mapped[float] = mapped_column(Float)
    p90: Mapped[float] = mapped_column(Float)
    factors: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    model_version: Mapped[str] = mapped_column(String(32))
    computed_at: Mapped[datetime] = mapped_column(TZ, server_default=func.now())
    frozen: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")


class RestOfSeasonProjection(Base):
    """A player's projected points over the rest of the fantasy season (P2, ADR-047/048).

    Shared by every league with the same scoring and season shape (`scoring_key`,
    `horizon_key`). Recomputed on each sync; not frozen or graded (the backtest measures it).
    """

    __tablename__ = "ros_projections"
    __table_args__ = (
        UniqueConstraint(
            "player_id",
            "season",
            "from_week",
            "scoring_key",
            "horizon_key",
            "model_version",
            name="uq_ros_projections_key",  # the generated name is over Postgres' 63 chars
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), index=True)
    season: Mapped[int] = mapped_column(Integer)
    from_week: Mapped[int] = mapped_column(Integer)
    scoring_key: Mapped[str] = mapped_column(String(64))
    # Last fantasy week and playoff start, e.g. "17:15": leagues with the same season shape.
    horizon_key: Mapped[str] = mapped_column(String(16))
    points: Mapped[float] = mapped_column(Float)  # weighted total
    games: Mapped[int] = mapped_column(Integer)
    weekly: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    model_version: Mapped[str] = mapped_column(String(32))
    computed_at: Mapped[datetime] = mapped_column(TZ, server_default=func.now())


class ProjectionGrade(Base):
    __tablename__ = "projection_grades"

    projection_id: Mapped[int] = mapped_column(
        ForeignKey("projections.id", ondelete="CASCADE"), primary_key=True
    )
    actual_points: Mapped[float] = mapped_column(Float)
    genuine: Mapped[bool] = mapped_column(Boolean)  # computed_at < kickoff_at
    graded_at: Mapped[datetime] = mapped_column(TZ, server_default=func.now())


# --------------------------------------------------------------------------- operations
class SyncRun(Base):
    """One background job run: shown as "updated N min ago", and kept for debugging."""

    __tablename__ = "sync_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kind: Mapped[str] = mapped_column(String(32))  # sync_league / ingest_nflverse / ...
    job_id: Mapped[str | None] = mapped_column(String(64), index=True)
    league_id: Mapped[int | None] = mapped_column(
        ForeignKey("leagues.id", ondelete="CASCADE"), index=True
    )
    requested_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    status: Mapped[str] = mapped_column(String(16))  # queued/running/done/failed
    started_at: Mapped[datetime | None] = mapped_column(TZ)
    finished_at: Mapped[datetime | None] = mapped_column(TZ)
    error: Mapped[str | None] = mapped_column(Text)
    # Small JSON result for jobs whose output the UI needs (e.g. leagues found on connect).
    result: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(TZ, server_default=func.now())
