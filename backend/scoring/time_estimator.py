"""
RootNode - Migration Time Estimator (Step 6)
==============================================
Estimates migration duration per application and per wave
based on risk level and complexity factors.

Time Estimates (per spec):
  • Low risk    → 1–2 days
  • Medium risk → 2–3 days
  • High risk   → 4–5 days

Wave duration = max(app durations) within wave (parallel execution).
Total project duration = sum(wave durations) (sequential waves).

Optimized for AWS Lambda:
  • Pure computation — no I/O
  • Integrates with wave analysis + risk scoring outputs
  • Produces Gantt-chart-ready timeline data
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple

from backend.models.application import ApplicationRecord
from backend.scoring.risk_engine import score_risk, RiskBreakdown
from backend.graph.wave_analyzer import WaveAnalysisResult

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Risk level → (min_days, max_days)
DEFAULT_TIME_MAP: Dict[str, Tuple[int, int]] = {
    "Low": (1, 2),
    "Medium": (2, 3),
    "High": (4, 5),
}

# Complexity multipliers for fine-grained estimation
COMPLEXITY_MULTIPLIERS: Dict[str, float] = {
    "simple": 0.8,
    "moderate": 1.0,
    "complex": 1.2,
    "very_complex": 1.5,
}

# Data size bonus: extra days per 500 GB
DATA_SIZE_BONUS_PER_GB = float(os.environ.get("EST_DATA_BONUS_PER_500GB", "0.5"))
DATA_SIZE_THRESHOLD = 500.0


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AppTimeEstimate:
    """Time estimate for a single application."""
    app_id: str
    name: str
    risk_level: str
    migration_strategy: str
    min_days: float
    max_days: float
    expected_days: float   # midpoint
    complexity: str
    data_size: float

    def to_dict(self) -> Dict:
        return {
            "app_id": self.app_id,
            "name": self.name,
            "risk_level": self.risk_level,
            "migration_strategy": self.migration_strategy,
            "min_days": round(self.min_days, 1),
            "max_days": round(self.max_days, 1),
            "expected_days": round(self.expected_days, 1),
        }


@dataclass
class WaveTimeEstimate:
    """Time estimate for a migration wave (parallel execution)."""
    wave_number: int
    app_estimates: List[AppTimeEstimate] = field(default_factory=list)
    min_days: float = 0.0       # max of app min_days (parallel)
    max_days: float = 0.0       # max of app max_days (parallel)
    expected_days: float = 0.0  # max of app expected_days (parallel)
    start_day: float = 0.0      # cumulative start offset
    end_day: float = 0.0        # start_day + expected_days

    @property
    def app_count(self) -> int:
        return len(self.app_estimates)

    def to_dict(self) -> Dict:
        return {
            "wave_number": self.wave_number,
            "app_count": self.app_count,
            "min_days": round(self.min_days, 1),
            "max_days": round(self.max_days, 1),
            "expected_days": round(self.expected_days, 1),
            "start_day": round(self.start_day, 1),
            "end_day": round(self.end_day, 1),
            "apps": [e.to_dict() for e in self.app_estimates],
        }


@dataclass
class ProjectTimeline:
    """Complete migration timeline for the project."""
    wave_estimates: List[WaveTimeEstimate] = field(default_factory=list)
    total_min_days: float = 0.0
    total_max_days: float = 0.0
    total_expected_days: float = 0.0
    total_apps: int = 0
    total_waves: int = 0
    start_date: Optional[date] = None
    end_date: Optional[date] = None

    def to_dict(self) -> Dict:
        d = {
            "total_waves": self.total_waves,
            "total_apps": self.total_apps,
            "total_min_days": round(self.total_min_days, 1),
            "total_max_days": round(self.total_max_days, 1),
            "total_expected_days": round(self.total_expected_days, 1),
            "waves": [w.to_dict() for w in self.wave_estimates],
        }
        if self.start_date:
            d["start_date"] = self.start_date.isoformat()
        if self.end_date:
            d["end_date"] = self.end_date.isoformat()
        return d


# ===========================================================================
# Core Estimator
# ===========================================================================

def estimate_app_time(
    app: ApplicationRecord,
    *,
    breakdown: Optional[RiskBreakdown] = None,
    time_map: Optional[Dict[str, Tuple[int, int]]] = None,
    apply_complexity: bool = True,
    apply_data_bonus: bool = True,
) -> AppTimeEstimate:
    """
    Estimate migration time for a single application.

    Parameters
    ----------
    app : ApplicationRecord
        Application with risk_score and migration_strategy set.
    breakdown : RiskBreakdown, optional
        Pre-computed breakdown. If None, score_risk() is called.
    time_map : dict, optional
        Custom risk_level → (min_days, max_days) mapping.
    apply_complexity : bool
        Apply complexity multiplier to base estimate.
    apply_data_bonus : bool
        Add extra time for large data volumes.

    Returns
    -------
    AppTimeEstimate
    """
    mapping = time_map or DEFAULT_TIME_MAP

    if breakdown is None:
        breakdown = score_risk(app)

    risk_level = breakdown.risk_level
    base_min, base_max = mapping.get(risk_level, (2, 3))

    min_days = float(base_min)
    max_days = float(base_max)

    # Apply complexity multiplier
    if apply_complexity:
        multiplier = COMPLEXITY_MULTIPLIERS.get(app.complexity, 1.0)
        min_days *= multiplier
        max_days *= multiplier

    # Add data size bonus
    if apply_data_bonus and app.data_size >= DATA_SIZE_THRESHOLD:
        bonus = (app.data_size / DATA_SIZE_THRESHOLD) * DATA_SIZE_BONUS_PER_GB
        min_days += bonus
        max_days += bonus

    expected_days = (min_days + max_days) / 2.0

    strategy = app.migration_strategy or "Unknown"

    return AppTimeEstimate(
        app_id=app.app_id,
        name=app.name,
        risk_level=risk_level,
        migration_strategy=strategy,
        min_days=min_days,
        max_days=max_days,
        expected_days=expected_days,
        complexity=app.complexity,
        data_size=app.data_size,
    )


# ===========================================================================
# Wave & Project Estimation
# ===========================================================================

def estimate_wave_time(
    wave_result: WaveAnalysisResult,
    apps: List[ApplicationRecord],
    *,
    time_map: Optional[Dict[str, Tuple[int, int]]] = None,
    start_date: Optional[date] = None,
) -> ProjectTimeline:
    """
    Estimate migration time for all waves and produce a project timeline.

    Wave duration = max(app durations) within wave (parallel).
    Total duration = sum(wave durations) (sequential waves).

    Parameters
    ----------
    wave_result : WaveAnalysisResult
        Output from topological_sort_waves().
    apps : list[ApplicationRecord]
        Scored applications with risk_score set.
    time_map : dict, optional
        Custom time mapping.
    start_date : date, optional
        Project start date for calendar-based timeline.

    Returns
    -------
    ProjectTimeline
    """
    # Build app lookup
    app_map: Dict[str, ApplicationRecord] = {a.app_id: a for a in apps}

    wave_estimates: List[WaveTimeEstimate] = []
    cumulative_days = 0.0

    for wave in wave_result.waves:
        app_estimates: List[AppTimeEstimate] = []

        for item in wave.items:
            app = app_map.get(item.app_id)
            if app is None:
                continue
            est = estimate_app_time(app, time_map=time_map)
            app_estimates.append(est)

        if not app_estimates:
            continue

        # Wave is parallel → duration = max of individual durations
        wave_min = max(e.min_days for e in app_estimates)
        wave_max = max(e.max_days for e in app_estimates)
        wave_expected = max(e.expected_days for e in app_estimates)

        wave_est = WaveTimeEstimate(
            wave_number=wave.wave_number,
            app_estimates=app_estimates,
            min_days=wave_min,
            max_days=wave_max,
            expected_days=wave_expected,
            start_day=cumulative_days,
            end_day=cumulative_days + wave_expected,
        )
        wave_estimates.append(wave_est)
        cumulative_days += wave_expected

    total_min = sum(w.min_days for w in wave_estimates)
    total_max = sum(w.max_days for w in wave_estimates)
    total_expected = sum(w.expected_days for w in wave_estimates)

    end_date = None
    if start_date:
        end_date = start_date + timedelta(days=int(total_expected) + 1)

    timeline = ProjectTimeline(
        wave_estimates=wave_estimates,
        total_min_days=total_min,
        total_max_days=total_max,
        total_expected_days=total_expected,
        total_apps=sum(w.app_count for w in wave_estimates),
        total_waves=len(wave_estimates),
        start_date=start_date,
        end_date=end_date,
    )

    logger.info(
        f"estimate_wave_time: {timeline.total_apps} apps, "
        f"{timeline.total_waves} waves, "
        f"{timeline.total_expected_days:.1f} expected days"
    )

    return timeline
