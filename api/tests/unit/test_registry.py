"""The adapter registry (P3 step 2): platform lookup, per-user factories, shared NFL source."""

from __future__ import annotations

from typing import Any

import pytest

from app.adapters.registry import (
    UnsupportedPlatform,
    adapter_for,
    nfl_source,
    sleeper_discovery,
)


class Fake:
    """Stands in for an adapter; the registry only hands objects back."""

    def __init__(self, name: str) -> None:
        self.name = name


def test_shared_adapter_is_returned_by_platform() -> None:
    sleeper = Fake("sleeper")
    ctx: dict[str, Any] = {"adapters": {"sleeper": sleeper}}
    got: object = adapter_for(ctx, "sleeper")
    assert got is sleeper


def test_unregistered_platform_is_a_clear_non_retryable_error() -> None:
    ctx: dict[str, Any] = {"adapters": {"sleeper": Fake("sleeper")}}
    with pytest.raises(UnsupportedPlatform, match="espn"):
        adapter_for(ctx, "espn")
    assert issubclass(UnsupportedPlatform, LookupError)


def test_factory_builds_a_per_user_adapter_from_credentials() -> None:
    seen: list[object] = []

    def factory(credentials: object) -> Fake:
        seen.append(credentials)
        return Fake(f"espn:{credentials}")

    ctx: dict[str, Any] = {"adapters": {}, "adapter_factories": {"espn": factory}}
    first = adapter_for(ctx, "espn", "user-1-cookies")
    second = adapter_for(ctx, "espn", "user-2-cookies")
    assert (first.name, second.name) == ("espn:user-1-cookies", "espn:user-2-cookies")  # type: ignore[attr-defined]
    assert seen == ["user-1-cookies", "user-2-cookies"]


def test_factory_wins_over_a_shared_adapter_for_the_same_platform() -> None:
    ctx: dict[str, Any] = {
        "adapters": {"espn": Fake("shared")},
        "adapter_factories": {"espn": lambda creds: Fake("built")},
    }
    assert adapter_for(ctx, "espn", None).name == "built"  # type: ignore[attr-defined]


def test_nfl_source_and_discovery_come_from_sleeper() -> None:
    sleeper = Fake("sleeper")
    ctx: dict[str, Any] = {"adapters": {"sleeper": sleeper}}
    source: object = nfl_source(ctx)
    finder: object = sleeper_discovery(ctx)
    assert source is sleeper
    assert finder is sleeper
