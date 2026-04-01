"""
RootNode - Migration Strategy Engine (Step 5)
===============================================
Assigns migration_strategy to each application based on its risk_level.

Strategy Mapping (per spec):
  • Low  risk  → Rehost    (lift-and-shift, minimal changes)
  • Medium risk → Replatform (partial optimization, managed services)
  • High risk  → Refactor   (re-architect for cloud-native)

Also supports the full 7R framework for downstream AI enrichment:
  Retain, Retire, Rehost, Relocate, Repurchase, Replatform, Refactor

Optimized for AWS Lambda:
  • Pure computation — no I/O
  • Stateless — safe for concurrent invocation
  • Integrates with score_risk() output
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from backend.models.application import ApplicationRecord
from backend.scoring.risk_engine import (
    RiskBreakdown,
    score_risk,
    score_all_apps,
)

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))


# ---------------------------------------------------------------------------
# Strategy Definitions
# ---------------------------------------------------------------------------

STRATEGY_REHOST = "Rehost"
STRATEGY_REPLATFORM = "Replatform"
STRATEGY_REFACTOR = "Refactor"

# Default mapping: risk_level → migration_strategy
DEFAULT_STRATEGY_MAP: Dict[str, str] = {
    "Low": STRATEGY_REHOST,
    "Medium": STRATEGY_REPLATFORM,
    "High": STRATEGY_REFACTOR,
}

# Full 7R taxonomy for reference / AI enrichment
VALID_STRATEGIES = [
    "Retain",
    "Retire",
    "Rehost",
    "Relocate",
    "Repurchase",
    "Replatform",
    "Refactor",
]


@dataclass(frozen=True)
class StrategyRecommendation:
    """Full strategy assignment output for a single application."""
    app_id: str
    risk_level: str
    risk_score: float
    migration_strategy: str
    rationale: str

    def to_dict(self) -> Dict:
        return {
            "app_id": self.app_id,
            "risk_level": self.risk_level,
            "risk_score": self.risk_score,
            "migration_strategy": self.migration_strategy,
            "rationale": self.rationale,
        }


# ---------------------------------------------------------------------------
# Rationale Generator
# ---------------------------------------------------------------------------

_RATIONALE_TEMPLATES: Dict[str, str] = {
    STRATEGY_REHOST: (
        "Low risk profile — suitable for lift-and-shift migration "
        "with minimal code changes. Move directly to cloud infrastructure."
    ),
    STRATEGY_REPLATFORM: (
        "Medium risk profile — recommended for partial optimization. "
        "Leverage managed services (e.g., RDS, ElastiCache) to reduce "
        "operational overhead while limiting refactoring scope."
    ),
    STRATEGY_REFACTOR: (
        "High risk profile — requires re-architecture for cloud-native. "
        "Decompose into microservices, adopt serverless patterns, and "
        "implement resilience patterns to mitigate migration risk."
    ),
}


def _build_rationale(strategy: str, breakdown: Optional[RiskBreakdown] = None) -> str:
    """Generate human-readable rationale for strategy assignment."""
    base = _RATIONALE_TEMPLATES.get(strategy, f"Assigned strategy: {strategy}.")
    if breakdown and breakdown.factors:
        factors_str = ", ".join(breakdown.factors)
        return f"{base} Risk factors: {factors_str}."
    return base


# ===========================================================================
# Core Assignment Function
# ===========================================================================

def assign_strategy(
    app: ApplicationRecord,
    *,
    strategy_map: Optional[Dict[str, str]] = None,
    breakdown: Optional[RiskBreakdown] = None,
) -> StrategyRecommendation:
    """
    Assign a migration strategy to an application based on its risk level.

    Parameters
    ----------
    app : ApplicationRecord
        Application with risk_score already computed (or will be computed).
    strategy_map : dict, optional
        Custom risk_level → strategy mapping. Defaults to:
        Low → Rehost, Medium → Replatform, High → Refactor.
    breakdown : RiskBreakdown, optional
        Pre-computed risk breakdown. If None, score_risk() is called.

    Returns
    -------
    StrategyRecommendation
        Strategy assignment with rationale.

    Example
    -------
    >>> app = ApplicationRecord(app_id="APP001", name="Auth",
    ...     criticality="critical", data_size=150, complexity="complex")
    >>> rec = assign_strategy(app)
    >>> print(rec.migration_strategy)
    'Refactor'
    """
    mapping = strategy_map or DEFAULT_STRATEGY_MAP

    # Score if not already scored
    if breakdown is None:
        breakdown = score_risk(app)
        app.risk_score = breakdown.normalized_score

    risk_level = breakdown.risk_level
    strategy = mapping.get(risk_level, STRATEGY_REPLATFORM)  # safe fallback
    rationale = _build_rationale(strategy, breakdown)

    # Update the application record
    app.migration_strategy = strategy

    recommendation = StrategyRecommendation(
        app_id=app.app_id,
        risk_level=risk_level,
        risk_score=breakdown.normalized_score,
        migration_strategy=strategy,
        rationale=rationale,
    )

    logger.debug(
        f"assign_strategy({app.app_id}): {risk_level} → {strategy}"
    )

    return recommendation


# ===========================================================================
# Batch Assignment
# ===========================================================================

def assign_all_strategies(
    apps: List[ApplicationRecord],
    *,
    strategy_map: Optional[Dict[str, str]] = None,
) -> Tuple[List[ApplicationRecord], List[StrategyRecommendation]]:
    """
    Score and assign strategies to all applications.

    Returns
    -------
    tuple[list[ApplicationRecord], list[StrategyRecommendation]]
        Updated apps and full recommendations.
    """
    scored_apps, breakdowns = score_all_apps(apps)
    recommendations: List[StrategyRecommendation] = []

    for app, breakdown in zip(scored_apps, breakdowns):
        rec = assign_strategy(app, strategy_map=strategy_map, breakdown=breakdown)
        recommendations.append(rec)

    # Summary logging
    counts: Dict[str, int] = {}
    for rec in recommendations:
        counts[rec.migration_strategy] = counts.get(rec.migration_strategy, 0) + 1

    logger.info(
        f"assign_all_strategies: {len(apps)} apps — "
        + ", ".join(f"{k}: {v}" for k, v in sorted(counts.items()))
    )

    return scored_apps, recommendations


def get_strategy_summary(recommendations: List[StrategyRecommendation]) -> Dict:
    """
    Generate a summary of strategy distribution.
    Useful for Lambda response and frontend dashboard.
    """
    summary: Dict[str, List[Dict]] = {s: [] for s in VALID_STRATEGIES}

    for rec in recommendations:
        if rec.migration_strategy in summary:
            summary[rec.migration_strategy].append(rec.to_dict())
        else:
            summary[rec.migration_strategy] = [rec.to_dict()]

    return {
        "total_apps": len(recommendations),
        "distribution": {
            strategy: len(apps)
            for strategy, apps in summary.items()
            if apps
        },
        "by_strategy": {
            strategy: apps
            for strategy, apps in summary.items()
            if apps
        },
    }
