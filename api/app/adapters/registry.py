"""Which adapter serves which platform (ADR-006, ADR-053).

The worker keeps its long-lived adapters in `ctx["adapters"]`, keyed by platform name. Anything
that needs a platform's adapter asks here instead of reaching into that dict, so adding a platform
means registering one more adapter, not editing every job.

Per-user adapters (ESPN needs the follower's cookies) are built by a factory stored as
`ctx["adapter_factories"][platform]`; the factory shares one HTTP client across all users.
"""

from __future__ import annotations

from typing import Any

from app.adapters.base import (
    DiscoveryAdapter,
    LeagueAdapter,
    NflSource,
    Platform,
)

Ctx = dict[str, Any]


class UnsupportedPlatform(LookupError):
    """No adapter is registered for this platform (not retryable)."""


def adapter_for(ctx: Ctx, platform: Platform, credentials: Any | None = None) -> LeagueAdapter:
    """The adapter that reads leagues of `platform`.

    `credentials` is only used by platforms that need them (ESPN's cookies); public platforms
    ignore it.
    """
    factory = ctx.get("adapter_factories", {}).get(platform)
    if factory is not None:
        adapter: LeagueAdapter = factory(credentials)
        return adapter
    shared = ctx.get("adapters", {}).get(platform)
    if shared is None:
        raise UnsupportedPlatform(f"no adapter registered for platform {platform!r}")
    adapter = shared
    return adapter


def nfl_source(ctx: Ctx) -> NflSource:
    """Where the master player list and the current NFL week come from (Sleeper)."""
    source: NflSource = ctx["adapters"]["sleeper"]
    return source


def sleeper_discovery(ctx: Ctx) -> DiscoveryAdapter:
    """Sleeper's find-by-username lookup."""
    finder: DiscoveryAdapter = ctx["adapters"]["sleeper"]
    return finder
