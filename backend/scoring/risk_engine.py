"""
RootNode - Risk Scoring Engine (Step 4)
========================================
Computes a composite risk_score for each application based on
criticality, data size, dependency count, and complexity.

Scoring Rules (per spec):
  • High/Critical criticality  → +2
  • High data size (≥100 GB)   → +2
  • Dependencies ≥ 3           → +2
  • Complex/Very Complex       → +2
  Max raw score = 8

Risk Tiers:
  • 0–2  → Low
  • 3–5  → Medium
  • 6–8  → High

The raw score is also normalized to 0–100 for the risk_score field
on ApplicationRecord (used by the AI roadmap and frontend heatmap).

Optimized for AWS Lambda:
  • Pure computation — no I/O
  • Stateless — safe for concurrent invocation
  • Configurable thresholds via environment variables
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from backend.models.application import ApplicationRecord
from backend.graph.wave_analyzer import WaveAnalysisResult, Wave, WaveItem

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))


# ---------------------------------------------------------------------------
# Configuration (overridable via env vars for Lambda)
# ---------------------------------------------------------------------------

DATA_SIZE_THRESHOLD = float(os.environ.get("RISK_DATA_SIZE_THRESHOLD", "100.0"))
DEPENDENCY_COUNT_THRESHOLD = int(os.environ.get("RISK_DEP_COUNT_THRESHOLD", "3"))

# Points per factor
POINTS_CRITICALITY = int(os.environ.get("RISK_PTS_CRITICALITY", "2"))
POINTS_DATA_SIZE = int(os.environ.get("RISK_PTS_DATA_SIZE", "2"))
POINTS_DEPENDENCIES = int(os.environ.get("RISK_PTS_DEPENDENCIES", "2"))
POINTS_COMPLEXITY = int(os.environ.get("RISK_PTS_COMPLEXITY", "2"))

MAX_RAW_SCORE = POINTS_CRITICALITY + POINTS_DATA_SIZE + POINTS_DEPENDENCIES + POINTS_COMPLEXITY


# ---------------------------------------------------------------------------
# Risk Breakdown
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RiskBreakdown:
    """Detailed breakdown of how risk_score was computed."""
    app_id: str
    criticality_points: int
    data_size_points: int
    dependency_points: int
    complexity_points: int
    raw_score: int
    normalized_score: float  # 0–100
    risk_level: str          # Low / Medium / High

    @property
    def factors(self) -> List[str]:
        """Human-readable list of contributing risk factors."""
        f = []
        if self.criticality_points > 0:
            f.append("high criticality")
        if self.data_size_points > 0:
            f.append(f"large data size (≥{DATA_SIZE_THRESHOLD} GB)")
        if self.dependency_points > 0:
            f.append(f"many dependencies (≥{DEPENDENCY_COUNT_THRESHOLD})")
        if self.complexity_points > 0:
            f.append("high complexity")
        return f

    def to_dict(self) -> Dict:
        return {
            "app_id": self.app_id,
            "raw_score": self.raw_score,
            "normalized_score": self.normalized_score,
            "risk_level": self.risk_level,
            "criticality_points": self.criticality_points,
            "data_size_points": self.data_size_points,
            "dependency_points": self.dependency_points,
            "complexity_points": self.complexity_points,
            "factors": self.factors,
        }


# ===========================================================================
# Core Scoring Function
# ===========================================================================

def score_risk(app: ApplicationRecord) -> RiskBreakdown:
    """
    Compute risk score for a single application.

    Parameters
    ----------
    app : ApplicationRecord
        Validated application record.

    Returns
    -------
    RiskBreakdown
        Full breakdown with raw score, normalized score (0–100),
        and risk level (Low / Medium / High).

    Example
    -------
    >>> from backend.models.application import ApplicationRecord
    >>> app = ApplicationRecord(
    ...     app_id="APP001", name="Auth", criticality="critical",
    ...     data_size=150, business_priority=1, complexity="complex",
    ...     dependencies=["X", "Y", "Z"]
    ... )
    >>> result = score_risk(app)
    >>> print(result.risk_level)
    'High'
    """
    # ---- 1. Criticality ---------------------------------------------------
    criticality_pts = 0
    if app.criticality in ("high", "critical"):
        criticality_pts = POINTS_CRITICALITY

    # ---- 2. Data Size -----------------------------------------------------
    data_size_pts = 0
    if app.data_size >= DATA_SIZE_THRESHOLD:
        data_size_pts = POINTS_DATA_SIZE

    # ---- 3. Dependency Count ----------------------------------------------
    dependency_pts = 0
    if len(app.dependencies) >= DEPENDENCY_COUNT_THRESHOLD:
        dependency_pts = POINTS_DEPENDENCIES

    # ---- 4. Complexity ----------------------------------------------------
    complexity_pts = 0
    if app.complexity in ("complex", "very_complex"):
        complexity_pts = POINTS_COMPLEXITY

    # ---- 5. Aggregate -----------------------------------------------------
    raw_score = (
        criticality_pts
        + data_size_pts
        + dependency_pts
        + complexity_pts
    )

    # Normalize to 0–100
    normalized = round((raw_score / MAX_RAW_SCORE) * 100, 1) if MAX_RAW_SCORE > 0 else 0.0

    # Risk tier
    risk_level = _raw_to_level(raw_score)

    breakdown = RiskBreakdown(
        app_id=app.app_id,
        criticality_points=criticality_pts,
        data_size_points=data_size_pts,
        dependency_points=dependency_pts,
        complexity_points=complexity_pts,
        raw_score=raw_score,
        normalized_score=normalized,
        risk_level=risk_level,
    )

    logger.debug(
        f"score_risk({app.app_id}): {raw_score}/{MAX_RAW_SCORE} → "
        f"{risk_level} [{', '.join(breakdown.factors) or 'no factors'}]"
    )

    return breakdown


# ---------------------------------------------------------------------------
# Tier Classification
# ---------------------------------------------------------------------------

def _raw_to_level(raw_score: int) -> str:
    """Map raw score to risk tier."""
    if raw_score <= 2:
        return "Low"
    elif raw_score <= 5:
        return "Medium"
    else:
        return "High"


# ===========================================================================
# Batch Scoring
# ===========================================================================

def score_all_apps(
    apps: List[ApplicationRecord],
) -> Tuple[List[ApplicationRecord], List[RiskBreakdown]]:
    """
    Score all applications and update their risk_score fields in-place.

    Returns
    -------
    tuple[list[ApplicationRecord], list[RiskBreakdown]]
        Updated apps and full breakdowns.
    """
    breakdowns: List[RiskBreakdown] = []

    for app in apps:
        breakdown = score_risk(app)
        app.risk_score = breakdown.normalized_score
        breakdowns.append(breakdown)

    logger.info(
        f"score_all_apps: scored {len(apps)} apps — "
        f"High: {sum(1 for b in breakdowns if b.risk_level == 'High')}, "
        f"Medium: {sum(1 for b in breakdowns if b.risk_level == 'Medium')}, "
        f"Low: {sum(1 for b in breakdowns if b.risk_level == 'Low')}"
    )

    return apps, breakdowns


def score_waves(
    wave_result: WaveAnalysisResult,
) -> Tuple[WaveAnalysisResult, Dict[str, RiskBreakdown]]:
    """
    Apply risk scoring to all apps within a WaveAnalysisResult.
    Updates WaveItem.risk_score in-place.

    Returns
    -------
    tuple[WaveAnalysisResult, dict[str, RiskBreakdown]]
        Updated wave result and breakdown map keyed by app_id.
    """
    breakdown_map: Dict[str, RiskBreakdown] = {}

    for wave in wave_result.waves:
        for item in wave.items:
            # Build a temporary ApplicationRecord for scoring
            temp_app = ApplicationRecord(
                app_id=item.app_id,
                name=item.name,
                criticality=item.criticality,
                complexity=item.complexity,
                data_size=item.data_size,
                business_priority=item.business_priority,
                dependencies=item.dependencies,
            )
            breakdown = score_risk(temp_app)
            item.risk_score = breakdown.normalized_score
            breakdown_map[item.app_id] = breakdown

    logger.info(
        f"score_waves: scored {len(breakdown_map)} apps across "
        f"{wave_result.total_waves} waves"
    )

    return wave_result, breakdown_map
