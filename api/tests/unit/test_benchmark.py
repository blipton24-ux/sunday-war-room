"""ADR-066: Sleeper's past projections as a local benchmark. Synthetic responses only: real
ones are licensed data and never committed."""

from pathlib import Path

import pandas as pd
import pytest

from app.model import benchmark


def item(pid: str, half: float | None, full: float = 0.0, std: float = 0.0) -> dict:
    stats = {} if half is None else {"pts_half_ppr": half, "pts_ppr": full, "pts_std": std}
    return {"player_id": pid, "week": 5, "stats": stats, "company": "synthetic"}


def test_parse_keeps_players_with_a_projection() -> None:
    out = benchmark.parse([item("1", 10.5, 12.0, 9.0), item("2", None), item("3", 0.0)], 2024, 5)
    assert out["sleeper_id"].tolist() == ["1", "3"]  # "2" listed with no stats: no projection
    row = out.iloc[0]
    assert (row["half"], row["full"], row["standard"]) == (10.5, 12.0, 9.0)
    assert (row["season"], row["week"]) == (2024, 5)


def test_fetch_asks_once_per_week_and_position() -> None:
    calls: list[tuple[str, dict[str, str]]] = []

    def get(url: str, params: dict[str, str]) -> list[dict]:
        calls.append((url, params))
        return [item(f"{params['position[]']}1", 5.0)]

    out = benchmark.fetch_season(2023, weeks=[1, 2], get=get, pause=0)
    assert len(calls) == 8 and calls[0][0].endswith("/projections/nfl/2023/1")
    assert {c[1]["position[]"] for c in calls} == set(benchmark.POSITIONS)
    assert len(out) == 8 and set(out["week"]) == {1, 2}


def test_load_reads_only_cached_seasons(tmp_path: Path) -> None:
    assert benchmark.load([2024], tmp_path).empty
    benchmark.parse([item("7", 3.0)], 2024, 5).to_csv(tmp_path / "2024.csv", index=False)
    out = benchmark.load([2023, 2024], tmp_path)
    assert out["sleeper_id"].tolist() == ["7"]  # read back as text, not the number 7


def test_attach_maps_ids_and_picks_the_format() -> None:
    paired = pd.DataFrame({"gsis_id": ["g1", "g2"], "season": 2024, "week": 5})
    sleeper = benchmark.parse([item("1", 10.0, 12.0, 8.0), item("9", 4.0)], 2024, 5)
    out = benchmark.attach(paired, sleeper, {"1": "g1"}, "full")
    assert out["sleeper"].iloc[0] == 12.0
    assert pd.isna(out["sleeper"].iloc[1])  # no Sleeper projection for g2
    assert len(out) == 2


@pytest.mark.parametrize("fmt", ["half", "full", "standard"])
def test_every_format_has_a_points_key(fmt: str) -> None:
    assert fmt in benchmark.POINTS
