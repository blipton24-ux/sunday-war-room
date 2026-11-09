"""Response/request shapes: these become the OpenAPI schema and the generated TS client."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class Schema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class MembershipOut(Schema):
    league_id: int
    league_name: str
    platform: str
    season: int
    my_team_id: int | None
    last_synced_at: datetime | None


class MeOut(Schema):
    id: int
    email: str | None
    name: str | None
    image: str | None
    plan: str
    sleeper_username: str | None
    memberships: list[MembershipOut]


class JobAccepted(Schema):
    job_id: str
    status: str


class JobOut(Schema):
    job_id: str
    kind: str
    status: str  # queued / running / done / failed
    league_id: int | None
    error: str | None
    result: dict[str, Any] | None
    created_at: datetime
    finished_at: datetime | None


class SleeperConnectIn(BaseModel):
    username: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_.\-]+$")


class FollowLeagueIn(BaseModel):
    platform: Literal["sleeper"]
    external_id: str = Field(pattern=r"^\d{1,32}$")


class LeagueOut(Schema):
    id: int
    platform: str
    external_id: str
    season: int
    name: str
    avatar_url: str | None
    current_week: int | None
    my_team_id: int | None
    last_synced_at: datetime | None
    sync_status: str | None  # status of the newest sync run


class FollowLeagueOut(Schema):
    league: LeagueOut
    job_id: str


class SetMyTeamIn(BaseModel):
    my_team_id: int


class TeamOut(Schema):
    id: int
    name: str
    owner_name: str | None
    avatar_url: str | None
    wins: int
    losses: int
    ties: int
