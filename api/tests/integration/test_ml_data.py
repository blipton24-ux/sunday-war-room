"""load_model_data reads every table the feature table needs, in the shapes it expects."""

from datetime import UTC, date, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    DepthChartWeek,
    InjuryReport,
    NflGame,
    PlayerBackground,
    PlayerWeekStats,
)
from app.model.ml.data import load_model_data
from app.model.ml.features import TARGET_COLUMNS, build_features

pytestmark = pytest.mark.integration


async def test_load_model_data_feeds_the_feature_table(db: AsyncSession) -> None:
    kick = datetime(2025, 9, 14, 17, tzinfo=UTC)
    db.add_all(
        [
            NflGame(game_id="2025_02_KC_LA", season=2025, week=2, home="LA", away="KC",
                    kickoff_at=kick, home_score=24, away_score=17, spread_line=1.5,
                    total_line=47.5, roof="dome"),
            NflGame(game_id="2025_03_LA_SEA", season=2025, week=3, home="SEA", away="LA",
                    kickoff_at=datetime(2025, 9, 21, 17, tzinfo=UTC), spread_line=2.5,
                    total_line=45.0, roof="outdoors"),
            PlayerWeekStats(gsis_id="00-1", season=2025, week=2, season_type="REG",
                            position="WR", team="LA", opponent="KC", offense_snap_pct=0.9,
                            stats={"targets": 9.0, "receptions": 6.0, "receiving_yards": 83.0}),
            InjuryReport(gsis_id="00-1", season=2025, week=3, report_status="Questionable",
                         practice_status="Limited Participation in Practice", played=True),
            DepthChartWeek(gsis_id="00-1", season=2025, week=3, depth_tier=1),
            DepthChartWeek(gsis_id="00-1", season=2024, week=3, depth_tier=2),  # not loaded
            PlayerBackground(gsis_id="00-1", birth_date=date(2001, 5, 29), rookie_season=2023,
                             draft_round=5, draft_pick=177),
        ]
    )  # fmt: skip
    await db.commit()

    data = await load_model_data(db, [2025])
    assert len(data.stats) == 1 and data.stats.iloc[0]["targets"] == 9.0
    assert set(data.games["roof"]) == {"dome", "outdoors"}
    assert data.injuries.iloc[0]["practice_status"].startswith("Limited")
    assert bool(data.injuries.iloc[0]["played"])
    assert data.depth["season"].tolist() == [2025]
    assert data.background.iloc[0]["draft_pick"] == 177

    upcoming = data.stats.assign(week=3, opponent="SEA")[list(TARGET_COLUMNS)]
    row = build_features(data, upcoming).iloc[0]
    assert row["season_targets"] == 9.0 and row["season_snap_share"] == pytest.approx(0.9)
    assert row["report_status"] == 1.0 and row["depth_tier"] == 1.0
    assert row["spread"] == -2.5 and row["dome"] == 0.0 and row["rest_days"] == 7.0
    assert row["draft_pick"] == 177
