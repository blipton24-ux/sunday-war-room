"""Projection ranges (Projection Model step 6; method approved in ADR-031 #2).

From walk-forward backtest residuals, per position:
* scale(proj) = a + b * proj   (bigger projections miss by more, so the spread grows with them)
* z = (actual - proj) / scale  standardized residual; keep its empirical 10/50/90% quantiles
* floor = the 1st percentile of actual scores (not "clip at 0": DEF and QBs can go negative)

range_q = max(floor, proj + z_q * scale(proj)). All numbers are FIT, never hand-set, and
stored with the model version that produced them.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd

QUANTILES = (0.10, 0.50, 0.90)
MIN_SCALE = 1.0


@dataclass(frozen=True)
class PositionFit:
    a: float
    b: float
    z10: float
    z50: float
    z90: float
    floor: float
    n: int

    def scale(self, proj: float) -> float:
        return max(MIN_SCALE, self.a + self.b * proj)


@dataclass(frozen=True)
class Calibration:
    model_version: str
    fitted_on: str  # e.g. "2023-2025 walk-forward, half-PPR"
    positions: dict[str, PositionFit]

    def to_json(self) -> str:
        return json.dumps(
            {
                "model_version": self.model_version,
                "fitted_on": self.fitted_on,
                "positions": {k: asdict(v) for k, v in sorted(self.positions.items())},
            },
            indent=2,
        )

    @classmethod
    def from_json(cls, text: str) -> Calibration:
        raw = json.loads(text)
        return cls(
            raw["model_version"],
            raw["fitted_on"],
            {k: PositionFit(**v) for k, v in raw["positions"].items()},
        )


CALIBRATION_FILE = Path(__file__).with_name("calibration.json")


def load_calibration(expected_version: str) -> Calibration:
    """The committed calibration. Fails loudly if it was fit for a different model version."""
    cal = Calibration.from_json(CALIBRATION_FILE.read_text(encoding="utf-8"))
    if cal.model_version != expected_version:
        raise RuntimeError(
            f"calibration.json is for model {cal.model_version}, code is {expected_version}: "
            "re-run the backtest (python -m app.scripts.backtest --write-calibration)"
        )
    return cal


def fit_position(proj: np.ndarray, actual: np.ndarray) -> PositionFit:
    resid = actual - proj
    # Least squares of |residual| on projection: E|r| = a + b * proj.
    design = np.column_stack([np.ones_like(proj), proj])
    (a, b), *_ = np.linalg.lstsq(design, np.abs(resid), rcond=None)
    a, b = max(float(a), MIN_SCALE), max(float(b), 0.0)
    scale = np.maximum(MIN_SCALE, a + b * proj)
    z10, z50, z90 = np.quantile(resid / scale, QUANTILES)
    return PositionFit(
        a=round(a, 4),
        b=round(b, 4),
        z10=round(float(z10), 4),
        z50=round(float(z50), 4),
        z90=round(float(z90), 4),
        floor=round(float(np.quantile(actual, 0.01)), 2),
        n=len(proj),
    )


def fit_calibration(frame: pd.DataFrame, model_version: str, fitted_on: str) -> Calibration:
    """`frame`: columns position, proj, actual (one row per backtested player-week)."""
    fits = {
        str(pos): fit_position(g["proj"].to_numpy(float), g["actual"].to_numpy(float))
        for pos, g in frame.groupby("position")
        if len(g) >= 50
    }
    return Calibration(model_version, fitted_on, fits)


def apply_range(proj: float, position: str, cal: Calibration) -> tuple[float, float, float]:
    fit = cal.positions.get(position)
    if fit is None:  # e.g. kickers in a backtest without enough rows: honest wide range
        return (round(max(0.0, proj * 0.4), 2), round(proj, 2), round(proj * 1.6 + 2, 2))
    if proj == 0.0:  # out / bye: nothing to spread
        return (0.0, 0.0, 0.0)
    s = fit.scale(proj)
    p10, p50, p90 = (max(fit.floor, proj + z * s) for z in (fit.z10, fit.z50, fit.z90))
    return (round(p10, 2), round(p50, 2), round(p90, 2))


def sample(
    p10: np.ndarray,
    p50: np.ndarray,
    p90: np.ndarray,
    floor: np.ndarray,
    draws: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """Draws for many players at once: a split normal through (p10, p50, p90), floored.

    Returns shape (draws, players). Below the median the spread is (p50-p10)/1.2816, above it
    (p90-p50)/1.2816, so skewed ranges (boom-or-bust) are reproduced.
    """
    z = rng.standard_normal((draws, len(p50)))
    lo = (p50 - p10) / 1.2816
    hi = (p90 - p50) / 1.2816
    x = p50 + np.where(z < 0, z * lo, z * hi)
    out: np.ndarray = np.maximum(x, floor)
    return out
