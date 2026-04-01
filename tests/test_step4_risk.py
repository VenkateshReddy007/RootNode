"""
RootNode - Step 4 Test Suite: Risk Scoring Engine
==================================================
Covers: individual factor scoring, tier classification, edge cases,
        batch scoring, wave scoring, and full fixture integration.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.models.application import ApplicationRecord
from backend.scoring.risk_engine import (
    score_risk,
    score_all_apps,
    score_waves,
    RiskBreakdown,
    MAX_RAW_SCORE,
)
from backend.parsers.csv_parser import parse_input
from backend.graph.dag_builder import build_dependency_graph
from backend.graph.wave_analyzer import topological_sort_waves


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "..", "backend", "fixtures")
CSV_PATH = os.path.join(FIXTURES_DIR, "sample_apps.csv")


def _make_app(app_id="T1", name="Test", deps=None, criticality="low",
              data_size=10.0, priority=3, complexity="simple"):
    return ApplicationRecord(
        app_id=app_id, name=name, dependencies=deps or [],
        criticality=criticality, data_size=data_size,
        business_priority=priority, complexity=complexity,
    )


# ===========================================================================
# Individual Factor Tests
# ===========================================================================

class TestCriticalityScoring:
    """Criticality factor: +2 for high/critical."""

    def test_critical_gets_points(self):
        app = _make_app(criticality="critical")
        result = score_risk(app)
        assert result.criticality_points == 2

    def test_high_gets_points(self):
        app = _make_app(criticality="high")
        result = score_risk(app)
        assert result.criticality_points == 2

    def test_medium_no_points(self):
        app = _make_app(criticality="medium")
        result = score_risk(app)
        assert result.criticality_points == 0

    def test_low_no_points(self):
        app = _make_app(criticality="low")
        result = score_risk(app)
        assert result.criticality_points == 0


class TestDataSizeScoring:
    """Data size factor: +2 for ≥ 100 GB."""

    def test_large_data_gets_points(self):
        app = _make_app(data_size=150.0)
        result = score_risk(app)
        assert result.data_size_points == 2

    def test_exact_threshold_gets_points(self):
        app = _make_app(data_size=100.0)
        result = score_risk(app)
        assert result.data_size_points == 2

    def test_small_data_no_points(self):
        app = _make_app(data_size=50.0)
        result = score_risk(app)
        assert result.data_size_points == 0

    def test_zero_data_no_points(self):
        app = _make_app(data_size=0.0)
        result = score_risk(app)
        assert result.data_size_points == 0


class TestDependencyScoring:
    """Dependency count factor: +2 for ≥ 3 deps."""

    def test_many_deps_gets_points(self):
        app = _make_app(deps=["A", "B", "C"])
        result = score_risk(app)
        assert result.dependency_points == 2

    def test_exact_threshold_gets_points(self):
        app = _make_app(deps=["A", "B", "C"])
        result = score_risk(app)
        assert result.dependency_points == 2

    def test_few_deps_no_points(self):
        app = _make_app(deps=["A", "B"])
        result = score_risk(app)
        assert result.dependency_points == 0

    def test_no_deps_no_points(self):
        app = _make_app(deps=[])
        result = score_risk(app)
        assert result.dependency_points == 0


class TestComplexityScoring:
    """Complexity factor: +2 for complex/very_complex."""

    def test_complex_gets_points(self):
        app = _make_app(complexity="complex")
        result = score_risk(app)
        assert result.complexity_points == 2

    def test_very_complex_gets_points(self):
        app = _make_app(complexity="very_complex")
        result = score_risk(app)
        assert result.complexity_points == 2

    def test_moderate_no_points(self):
        app = _make_app(complexity="moderate")
        result = score_risk(app)
        assert result.complexity_points == 0

    def test_simple_no_points(self):
        app = _make_app(complexity="simple")
        result = score_risk(app)
        assert result.complexity_points == 0


# ===========================================================================
# Composite Score & Risk Level
# ===========================================================================

class TestCompositeScore:
    """Test aggregate scoring and tier classification."""

    def test_all_factors_max_score(self):
        app = _make_app(
            criticality="critical", data_size=500,
            deps=["A", "B", "C", "D"], complexity="very_complex",
        )
        result = score_risk(app)
        assert result.raw_score == 8
        assert result.normalized_score == 100.0
        assert result.risk_level == "High"

    def test_no_factors_min_score(self):
        app = _make_app(
            criticality="low", data_size=5,
            deps=[], complexity="simple",
        )
        result = score_risk(app)
        assert result.raw_score == 0
        assert result.normalized_score == 0.0
        assert result.risk_level == "Low"

    def test_low_tier_boundary(self):
        # raw_score = 2 → Low
        app = _make_app(criticality="critical")  # +2, rest are 0
        result = score_risk(app)
        assert result.raw_score == 2
        assert result.risk_level == "Low"

    def test_medium_tier_lower_boundary(self):
        # raw_score = 3 → Medium
        app = _make_app(criticality="critical", complexity="complex")  # 2+2=4
        result = score_risk(app)
        assert result.raw_score == 4
        assert result.risk_level == "Medium"

    def test_medium_tier_upper_boundary(self):
        # raw_score = 5 → Medium (we need to engineer a 5, but factors are 0 or 2)
        # 2+2 = 4 → Medium, 2+2+2 = 6 → High
        # So max Medium is 4 with default points
        app = _make_app(
            criticality="high", data_size=200,
        )
        result = score_risk(app)
        assert result.raw_score == 4
        assert result.risk_level == "Medium"

    def test_high_tier_boundary(self):
        # raw_score = 6 → High
        app = _make_app(
            criticality="critical", data_size=200, complexity="complex",
        )
        result = score_risk(app)
        assert result.raw_score == 6
        assert result.risk_level == "High"

    def test_normalized_score_calculation(self):
        app = _make_app(criticality="high", complexity="complex")  # 4/8
        result = score_risk(app)
        assert result.normalized_score == 50.0


# ===========================================================================
# Risk Breakdown
# ===========================================================================

class TestRiskBreakdown:
    """Test breakdown metadata and serialization."""

    def test_factors_list(self):
        app = _make_app(
            criticality="critical", data_size=200,
            deps=["A", "B", "C"], complexity="complex",
        )
        result = score_risk(app)
        assert "high criticality" in result.factors
        assert "high complexity" in result.factors
        assert len(result.factors) == 4

    def test_no_factors_empty_list(self):
        app = _make_app()
        result = score_risk(app)
        assert result.factors == []

    def test_to_dict(self):
        app = _make_app(criticality="high")
        result = score_risk(app)
        d = result.to_dict()
        assert d["app_id"] == "T1"
        assert "raw_score" in d
        assert "normalized_score" in d
        assert "risk_level" in d
        assert "factors" in d


# ===========================================================================
# Batch Scoring
# ===========================================================================

class TestBatchScoring:
    """Test score_all_apps() batch function."""

    def test_scores_all_apps(self):
        apps = [
            _make_app("A", "App A", criticality="critical"),
            _make_app("B", "App B", criticality="low"),
        ]
        scored_apps, breakdowns = score_all_apps(apps)
        assert len(breakdowns) == 2
        assert scored_apps[0].risk_score is not None
        assert scored_apps[1].risk_score is not None

    def test_updates_risk_score_field(self):
        app = _make_app(criticality="critical", data_size=200, complexity="complex")
        scored, breakdowns = score_all_apps([app])
        assert scored[0].risk_score == 75.0  # 6/8 * 100

    def test_empty_list(self):
        scored, breakdowns = score_all_apps([])
        assert len(scored) == 0
        assert len(breakdowns) == 0


# ===========================================================================
# Wave Scoring
# ===========================================================================

class TestWaveScoring:
    """Test score_waves() integration with wave analysis."""

    def test_scores_wave_items(self):
        parsed = parse_input(CSV_PATH)
        G = build_dependency_graph(parsed.applications)
        waves = topological_sort_waves(G)
        scored_waves, breakdown_map = score_waves(waves)

        # All 15 apps should have breakdowns
        assert len(breakdown_map) == 15

        # All wave items should have risk_score set
        for wave in scored_waves.waves:
            for item in wave.items:
                assert item.risk_score is not None

    def test_breakdown_map_keyed_by_app_id(self):
        parsed = parse_input(CSV_PATH)
        G = build_dependency_graph(parsed.applications)
        waves = topological_sort_waves(G)
        _, breakdown_map = score_waves(waves)

        assert "APP001" in breakdown_map
        assert "APP002" in breakdown_map
        assert breakdown_map["APP001"].app_id == "APP001"


# ===========================================================================
# Full Fixture Integration
# ===========================================================================

class TestFullFixture:
    """End-to-end scoring with 15-app fixture."""

    def test_full_pipeline_scoring(self):
        parsed = parse_input(CSV_PATH)
        scored_apps, breakdowns = score_all_apps(parsed.applications)

        # Verify known apps
        auth = next(b for b in breakdowns if b.app_id == "APP001")
        # APP001: critical (+2), 120.5GB (+2), 0 deps (0), complex (+2) = 6 → High
        assert auth.criticality_points == 2
        assert auth.data_size_points == 2
        assert auth.complexity_points == 2
        assert auth.risk_level == "High"

        email = next(b for b in breakdowns if b.app_id == "APP005")
        # APP005: medium (0), 10GB (0), 1 dep (0), simple (0) = 0 → Low
        assert email.raw_score == 0
        assert email.risk_level == "Low"

    def test_api_gateway_scoring(self):
        parsed = parse_input(CSV_PATH)
        _, breakdowns = score_all_apps(parsed.applications)

        gw = next(b for b in breakdowns if b.app_id == "APP011")
        # APP011: critical (+2), 5GB (0), 3 deps (+2), complex (+2) = 6 → High
        assert gw.criticality_points == 2
        assert gw.data_size_points == 0
        assert gw.dependency_points == 2
        assert gw.complexity_points == 2
        assert gw.risk_level == "High"

    def test_distribution_sanity(self):
        parsed = parse_input(CSV_PATH)
        _, breakdowns = score_all_apps(parsed.applications)

        levels = [b.risk_level for b in breakdowns]
        # Should have a mix of risk levels
        assert "Low" in levels
        assert "High" in levels


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
