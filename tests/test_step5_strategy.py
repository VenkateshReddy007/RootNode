"""
RootNode - Step 5 Test Suite: Migration Strategy Assignment
=============================================================
Covers: core mapping, custom maps, rationale generation,
        batch assignment, summary output, and full fixture integration.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.models.application import ApplicationRecord
from backend.scoring.risk_engine import score_risk
from backend.scoring.strategy_engine import (
    assign_strategy,
    assign_all_strategies,
    get_strategy_summary,
    STRATEGY_REHOST,
    STRATEGY_REPLATFORM,
    STRATEGY_REFACTOR,
)
from backend.parsers.csv_parser import parse_input


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
# Core Mapping: Risk Level → Strategy
# ===========================================================================

class TestCoreMapping:
    """Verify the fundamental risk-to-strategy mapping."""

    def test_low_risk_rehost(self):
        app = _make_app(criticality="low", data_size=5, complexity="simple")
        rec = assign_strategy(app)
        assert rec.migration_strategy == STRATEGY_REHOST
        assert rec.risk_level == "Low"

    def test_medium_risk_replatform(self):
        # 2 factors → raw 4 → Medium
        app = _make_app(criticality="high", data_size=200)
        rec = assign_strategy(app)
        assert rec.migration_strategy == STRATEGY_REPLATFORM
        assert rec.risk_level == "Medium"

    def test_high_risk_refactor(self):
        # 3+ factors → raw 6+ → High
        app = _make_app(criticality="critical", data_size=200, complexity="complex")
        rec = assign_strategy(app)
        assert rec.migration_strategy == STRATEGY_REFACTOR
        assert rec.risk_level == "High"

    def test_updates_app_record(self):
        app = _make_app(criticality="low")
        assign_strategy(app)
        assert app.migration_strategy == STRATEGY_REHOST
        assert app.risk_score is not None


# ===========================================================================
# Custom Strategy Map
# ===========================================================================

class TestCustomMapping:
    """Verify custom strategy map override."""

    def test_custom_map(self):
        custom = {"Low": "Retain", "Medium": "Repurchase", "High": "Retire"}
        app = _make_app(criticality="low")
        rec = assign_strategy(app, strategy_map=custom)
        assert rec.migration_strategy == "Retain"

    def test_custom_map_high(self):
        custom = {"Low": "Retain", "Medium": "Repurchase", "High": "Retire"}
        app = _make_app(criticality="critical", data_size=500, complexity="very_complex")
        rec = assign_strategy(app, strategy_map=custom)
        assert rec.migration_strategy == "Retire"


# ===========================================================================
# Pre-computed Breakdown
# ===========================================================================

class TestPrecomputedBreakdown:
    """Verify using a pre-computed RiskBreakdown."""

    def test_uses_existing_breakdown(self):
        app = _make_app(criticality="critical", data_size=500, complexity="complex")
        breakdown = score_risk(app)
        rec = assign_strategy(app, breakdown=breakdown)
        assert rec.risk_level == breakdown.risk_level
        assert rec.risk_score == breakdown.normalized_score


# ===========================================================================
# Rationale
# ===========================================================================

class TestRationale:
    """Verify rationale generation."""

    def test_rehost_rationale(self):
        app = _make_app(criticality="low")
        rec = assign_strategy(app)
        assert "lift-and-shift" in rec.rationale

    def test_replatform_rationale(self):
        app = _make_app(criticality="high", complexity="complex")
        rec = assign_strategy(app)
        assert "managed services" in rec.rationale

    def test_refactor_rationale(self):
        app = _make_app(criticality="critical", data_size=500, complexity="complex")
        rec = assign_strategy(app)
        assert "re-architect" in rec.rationale

    def test_rationale_includes_factors(self):
        app = _make_app(criticality="critical", data_size=500, complexity="complex")
        rec = assign_strategy(app)
        assert "Risk factors:" in rec.rationale


# ===========================================================================
# Serialization
# ===========================================================================

class TestSerialization:
    """Verify to_dict output."""

    def test_to_dict_fields(self):
        app = _make_app(criticality="high")
        rec = assign_strategy(app)
        d = rec.to_dict()
        assert "app_id" in d
        assert "risk_level" in d
        assert "risk_score" in d
        assert "migration_strategy" in d
        assert "rationale" in d

    def test_to_dict_values(self):
        app = _make_app(app_id="X1", criticality="low")
        rec = assign_strategy(app)
        d = rec.to_dict()
        assert d["app_id"] == "X1"
        assert d["migration_strategy"] == STRATEGY_REHOST


# ===========================================================================
# Batch Assignment
# ===========================================================================

class TestBatchAssignment:
    """Test assign_all_strategies()."""

    def test_assigns_all(self):
        apps = [
            _make_app("A", "Low Risk", criticality="low"),
            _make_app("B", "High Risk", criticality="critical",
                       data_size=500, complexity="complex"),
        ]
        scored, recs = assign_all_strategies(apps)
        assert len(recs) == 2
        assert scored[0].migration_strategy is not None
        assert scored[1].migration_strategy is not None

    def test_strategies_match_risk(self):
        apps = [
            _make_app("LO", "Low", criticality="low"),
            _make_app("HI", "High", criticality="critical",
                       data_size=500, complexity="very_complex"),
        ]
        _, recs = assign_all_strategies(apps)
        lo = next(r for r in recs if r.app_id == "LO")
        hi = next(r for r in recs if r.app_id == "HI")
        assert lo.migration_strategy == STRATEGY_REHOST
        assert hi.migration_strategy == STRATEGY_REFACTOR

    def test_empty_list(self):
        scored, recs = assign_all_strategies([])
        assert len(scored) == 0
        assert len(recs) == 0


# ===========================================================================
# Strategy Summary
# ===========================================================================

class TestStrategySummary:
    """Test get_strategy_summary()."""

    def test_summary_structure(self):
        apps = [
            _make_app("A", "A", criticality="low"),
            _make_app("B", "B", criticality="high", complexity="complex"),
            _make_app("C", "C", criticality="critical",
                       data_size=500, complexity="very_complex"),
        ]
        _, recs = assign_all_strategies(apps)
        summary = get_strategy_summary(recs)
        assert summary["total_apps"] == 3
        assert "distribution" in summary
        assert "by_strategy" in summary

    def test_distribution_counts(self):
        apps = [
            _make_app("A", "A", criticality="low"),
            _make_app("B", "B", criticality="low"),
            _make_app("C", "C", criticality="critical",
                       data_size=500, complexity="very_complex"),
        ]
        _, recs = assign_all_strategies(apps)
        summary = get_strategy_summary(recs)
        assert summary["distribution"].get(STRATEGY_REHOST, 0) == 2
        assert summary["distribution"].get(STRATEGY_REFACTOR, 0) == 1


# ===========================================================================
# Full Fixture Integration
# ===========================================================================

class TestFullFixture:
    """End-to-end with 15-app fixture."""

    def test_full_pipeline(self):
        parsed = parse_input(CSV_PATH)
        scored, recs = assign_all_strategies(parsed.applications)

        assert len(recs) == 15
        # Every app should have a strategy
        for app in scored:
            assert app.migration_strategy in [
                STRATEGY_REHOST, STRATEGY_REPLATFORM, STRATEGY_REFACTOR
            ]
            assert app.risk_score is not None

    def test_known_app_strategies(self):
        parsed = parse_input(CSV_PATH)
        _, recs = assign_all_strategies(parsed.applications)

        auth = next(r for r in recs if r.app_id == "APP001")
        # critical + 120GB + complex = High → Refactor
        assert auth.migration_strategy == STRATEGY_REFACTOR

        email = next(r for r in recs if r.app_id == "APP005")
        # medium + 10GB + simple = Low → Rehost
        assert email.migration_strategy == STRATEGY_REHOST

    def test_summary_has_all_strategies(self):
        parsed = parse_input(CSV_PATH)
        _, recs = assign_all_strategies(parsed.applications)
        summary = get_strategy_summary(recs)
        # With 15 diverse apps we expect multiple strategies
        assert len(summary["distribution"]) >= 2


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
