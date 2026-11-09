"""SQLAlchemy models for P1 (docs/Specs/Data-Model.md).

Schema changes only through Alembic migrations (ADR-015).

The first four tables follow the schema the Auth.js Postgres adapter (@auth/pg-adapter)
expects, including its camelCase column names, so Next.js and FastAPI share one `users` table.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

TZ = DateTime(timezone=True)


# --------------------------------------------------------------------------- accounts (Auth.js)
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str | None] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(String(255), unique=True)
    email_verified: Mapped[datetime | None] = mapped_column("emailVerified", TZ)
    image: Mapped[str | None] = mapped_column(Text)
    # Ours, not Auth.js's: room for a paid tier later (ADR-011).
    plan: Mapped[str] = mapped_column(String(20), default="free", server_default="free")
    created_at: Mapped[datetime] = mapped_column(TZ, server_default=func.now())


class AuthAccount(Base):
    """An OAuth link (e.g. Google) for a user. Written by Auth.js."""

    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        "userId", ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[str] = mapped_column(String(255), nullable=False)
    provider: Mapped[str] = mapped_column(String(255), nullable=False)
    provider_account_id: Mapped[str] = mapped_column(
        "providerAccountId", String(255), nullable=False
    )
    refresh_token: Mapped[str | None] = mapped_column(Text)
    access_token: Mapped[str | None] = mapped_column(Text)
    expires_at: Mapped[int | None] = mapped_column(BigInteger)
    id_token: Mapped[str | None] = mapped_column(Text)
    scope: Mapped[str | None] = mapped_column(Text)
    session_state: Mapped[str | None] = mapped_column(Text)
    token_type: Mapped[str | None] = mapped_column(Text)


class AuthSession(Base):
    """A signed-in browser session. Written by Auth.js."""

    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        "userId", ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    expires: Mapped[datetime] = mapped_column(TZ, nullable=False)
    session_token: Mapped[str] = mapped_column("sessionToken", String(255), nullable=False)


class VerificationToken(Base):
    """Magic-link tokens. The Auth.js pg adapter names this table in the singular."""

    __tablename__ = "verification_token"

    identifier: Mapped[str] = mapped_column(Text, primary_key=True)
    token: Mapped[str] = mapped_column(Text, primary_key=True)
    expires: Mapped[datetime] = mapped_column(TZ, nullable=False)


# --------------------------------------------------------------------------- platform connections
class PlatformAccount(Base):
    __tablename__ = "platform_accounts"
    __table_args__ = (UniqueConstraint("user_id", "platform"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    platform: Mapped[str] = mapped_column(String(20))  # sleeper / espn / yahoo
    external_user_id: Mapped[str] = mapped_column(String(64))
    display_name: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(TZ, server_default=func.now())


class LeagueMembership(Base):
    """Which leagues a user follows and which team is theirs. **The tenant boundary.**"""

    __tablename__ = "league_memberships"
    __table_args__ = (UniqueConstraint("user_id", "league_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    league_id: Mapped[int] = mapped_column(ForeignKey("leagues.id", ondelete="CASCADE"), index=True)
    my_team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id", ondelete="SET NULL"))
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
    roster_slots: Mapped[list[str]] = mapped_column(JSONB, default=list)
    current_week: Mapped[int | None] = mapped_column(Integer)
    last_synced_at: Mapped[datetime | None] = mapped_column(TZ)


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

    __table_args__ = (Index("ix_nfl_games_season_week", "season", "week"),)


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
    created_at: Mapped[datetime] = mapped_column(TZ, server_default=func.now())
