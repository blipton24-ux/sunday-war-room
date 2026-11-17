"""Fetch Sleeper's past weekly projections into the local benchmark cache (ADR-066).

    python -m app.scripts.fetch_sleeper_benchmark                 # 2022-2025, skips cached seasons
    python -m app.scripts.fetch_sleeper_benchmark --seasons 2025 --refresh

About 72 requests per season, a second apart. The cache (`api/benchmarks/sleeper/`) is
git-ignored: the numbers are Rotowire's, licensed to Sleeper, and never committed.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from app.model.benchmark import DEFAULT_CACHE, fetch_season


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seasons", type=int, nargs="+", default=[2022, 2023, 2024, 2025])
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--refresh", action="store_true", help="fetch cached seasons again")
    args = parser.parse_args()
    args.cache.mkdir(parents=True, exist_ok=True)
    for season in args.seasons:
        target = args.cache / f"{season}.csv"
        if target.exists() and not args.refresh:
            print(f"{season}: cached")
            continue
        frame = fetch_season(season)
        frame.to_csv(target, index=False)
        print(f"{season}: {len(frame):,} projections")


if __name__ == "__main__":
    main()
