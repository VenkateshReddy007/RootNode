"""
RootNode - Step 6 Test Suite: Migration Time Estimator
=======================================================
Covers: per-app estimation, complexity multipliers, data bonus,
        wave timing, project timeline, calendar dates, and full fixture.
"""

import os
import sys
from datetime import date

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.models.application import ApplicationRecord
from backend.scoring.risk_engine import score_risk
from backend.scoring.strategy_engine import assign_all_strategies
from backend.scoring.time_estimator import (
    estimate_app_time,
    estimate_wave_time,
    DEFAULT_TIME_MAP,
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
    app = ApplicationRecord(
        app_id=app_id, name=name, dependencies=deps or [],
        criticality=criticality, data_size=data_size,
        business_priority=priority, complexity=complexity,
    )
    return app


def _scored_app(**kwargs):
    """Create an app with risk scored and strategy assigned."""
    app = _make_app(**kwargs)
    from backend.scoring.strategy_engine import assign_strategy
    assign_strategy(app)
    return app


# ===========================================================================
# Per-App Base Estimates
# ===========================================================================

class TestBaseEstimates:
    """Verify risk-level-to-days mapping."""

    def test_low_risk_range(self):
        app = _scored_app(criticality="low", complexity="moderate")
        est = estimate_app_time(app, apply_complexity=False, apply_data_bonus=False)
        assert est.min_days == 1.0
        assert est.max_days == 2.0
        assert est.expected_days == 1.5

    def test_medium_risk_range(self):
        app = _scored_app(criticality="high", data_size=200)
        est = estimate_app_time(app, apply_complexity=False, apply_data_bonus=False)
        assert est.min_days == 2.0
        assert est.max_days == 3.0
        assert est.expected_days == 2.5

    def test_high_risk_range(self):
        app = _scored_app(criticality="critical", data_size=200, complexity="complex")
        est = estimate_app_time(app, apply_complexity=False, apply_data_bonus=False)
        assert est.min_days == 4.0
        assert est.max_days == 5.0
        assert est.expected_days == 4.5


# ===========================================================================
# Complexity Multiplier
# ===========================================================================

class TestComplexityMultiplier:
    """Verify complexity adjustments."""

    def test_simple_reduces_time(self):
        app = _scored_app(criticality="low", complexity="simple")
        est = estimate_app_time(app, apply_data_bonus=False)
        # Low base: 1-2, simple multiplier: 0.8
        assert est.min_days == pytest.approx(0.8, abs=0.01)
        assert est.max_days == pytest.approx(1.6, abs=0.01)

    def test_moderate_no_change(self):
        app = _scored_app(criticality="low", complexity="moderate")
        est = estimate_app_time(app, apply_data_bonus=False)
        assert est.min_days == pytest.approx(1.0, abs=0.01)
        assert est.max_days == pytest.approx(2.0, abs=0.01)

    def test_complex_increases_time(self):
        app = _scored_app(criticality="low", complexity="complex")
        est = estimate_app_time(app, apply_data_bonus=False)
        assert est.min_days == pytest.approx(1.2, abs=0.01)
        assert est.max_days == pytest.approx(2.4, abs=0.01)

    def test_very_complex_big_increase(self):
        app = _scored_app(criticality="low", complexity="very_complex")
        est = estimate_app_time(app, apply_data_bonus=False)
        assert est.min_days == pytest.approx(1.5, abs=0.01)
        assert est.max_days == pytest.approx(3.0, abs=0.01)

    def test_complexity_disabled(self):
        app = _scored_app(criticality="low", complexity="very_complex")
        est = estimate_app_time(app, apply_complexity=False, apply_data_bonus=False)
        assert est.min_days == 1.0
        assert est.max_days == 2.0


# ===========================================================================
# Data Size Bonus
# ===========================================================================

class TestDataSizeBonus:
    """Verify extra time for large data volumes."""

    def test_small_data_no_bonus(self):
        app = _scored_app(data_size=100.0, complexity="moderate")
        est_no = estimate_app_time(app, apply_complexity=False, apply_data_bonus=False)
        est_yes = estimate_app_time(app, apply_complexity=False, apply_data_bonus=True)
        assert est_no.min_days == est_yes.min_days

    def test_large_data_adds_time(self):
        app = _scored_app(data_size=1000.0, complexity="moderate")
        est_no = estimate_app_time(app, apply_complexity=False, apply_data_bonus=False)
        est_yes = estimate_app_time(app, apply_complexity=False, apply_data_bonus=True)
        assert est_yes.min_days > est_no.min_days
        assert est_yes.max_days > est_no.max_days


# ===========================================================================
# Serialization
# ===========================================================================

class TestSerialization:
    """Verify to_dict output."""

    def test_app_estimate_to_dict(self):
        app = _scored_app(criticality="low")
        est = estimate_app_time(app)
        d = est.to_dict()
        assert "app_id" in d
        assert "min_days" in d
        assert "max_days" in d
        assert "expected_days" in d
        assert "risk_level" in d
        assert "migration_strategy" in d


# ===========================================================================
# Wave Timing
# ===========================================================================

class TestWaveTiming:
    """Wave-level time estimation."""

    def test_parallel_wave_uses_max(self):
        """Wave duration = max of app durations (parallel)."""
        apps = [
            _scored_app(app_id="FAST", name="Fast", criticality="low", complexity="simple"),
            _scored_app(app_id="SLOW", name="Slow", criticality="low", complexity="very_complex"),
        ]
        G = build_dependency_graph(apps)
        waves = topological_sort_waves(G)
        timeline = estimate_wave_time(waves, apps)

        fast_est = next(e for e in timeline.wave_estimates[0].app_estimates if e.app_id == "FAST")
        slow_est = next(e for e in timeline.wave_estimates[0].app_estimates if e.app_id == "SLOW")

        # Wave duration should match the slower app
        assert timeline.wave_estimates[0].expected_days == slow_est.expected_days
        assert timeline.wave_estimates[0].expected_days > fast_est.expected_days

    def test_sequential_waves_sum(self):
        """Total duration = sum of wave durations."""
        apps = [
            _scored_app(app_id="A", name="A", criticality="low", complexity="moderate"),
            _scored_app(app_id="B", name="B", criticality="low", complexity="moderate", deps=["A"]),
        ]
        G = build_dependency_graph(apps)
        waves = topological_sort_waves(G)
        timeline = estimate_wave_time(waves, apps)

        assert timeline.total_waves == 2
        sum_expected = sum(w.expected_days for w in timeline.wave_estimates)
        assert timeline.total_expected_days == pytest.approx(sum_expected, abs=0.01)

    def test_wave_start_end_days(self):
        apps = [
            _scored_app(app_id="A", name="A", complexity="moderate"),
            _scored_app(app_id="B", name="B", complexity="moderate", deps=["A"]),
            _scored_app(app_id="C", name="C", complexity="moderate", deps=["B"]),
        ]
        G = build_dependency_graph(apps)
        waves = topological_sort_waves(G)
        timeline = estimate_wave_time(waves, apps)

        # Wave 0 starts at 0
        assert timeline.wave_estimates[0].start_day == 0.0
        # Wave 1 starts where wave 0 ends
        assert timeline.wave_estimates[1].start_day == pytest.approx(
            timeline.wave_estimates[0].end_day, abs=0.01
        )


# ===========================================================================
# Calendar Dates
# ===========================================================================

class TestCalendarDates:
    """Verify start/end date calculation."""

    def test_start_date_set(self):
        apps = [_scored_app(app_id="A", name="A")]
        G = build_dependency_graph(apps)
        waves = topological_sort_waves(G)
        start = date(2026, 7, 1)
        timeline = estimate_wave_time(waves, apps, start_date=start)
        assert timeline.start_date == start
        assert timeline.end_date is not None
        assert timeline.end_date > start

    def test_no_start_date(self):
        apps = [_scored_app(app_id="A", name="A")]
        G = build_dependency_graph(apps)
        waves = topological_sort_waves(G)
        timeline = estimate_wave_time(waves, apps)
        assert timeline.start_date is None
        assert timeline.end_date is None


# ===========================================================================
# Project Timeline Serialization
# ===========================================================================

class TestProjectTimeline:
    """Verify ProjectTimeline.to_dict()."""

    def test_timeline_to_dict(self):
        apps = [
            _scored_app(app_id="A", name="A"),
            _scored_app(app_id="B", name="B", deps=["A"]),
        ]
        G = build_dependency_graph(apps)
        waves = topological_sort_waves(G)
        timeline = estimate_wave_time(waves, apps, start_date=date(2026, 7, 1))
        d = timeline.to_dict()
        assert "total_waves" in d
        assert "total_expected_days" in d
        assert "waves" in d
        assert "start_date" in d
        assert "end_date" in d

    def test_empty_timeline(self):
        from backend.graph.wave_analyzer import WaveAnalysisResult
        empty = WaveAnalysisResult()
        timeline = estimate_wave_time(empty, [])
        assert timeline.total_waves == 0
        assert timeline.total_expected_days == 0.0


# ===========================================================================
# Full Fixture Integration
# ===========================================================================

class TestFullFixture:
    """End-to-end with 15-app fixture."""

    def test_full_pipeline_timeline(self):
        parsed = parse_input(CSV_PATH)
        scored, _ = assign_all_strategies(parsed.applications)
        G = build_dependency_graph(scored)
        waves = topological_sort_waves(G)
        timeline = estimate_wave_time(waves, scored, start_date=date(2026, 7, 1))

        assert timeline.total_apps == 15
        assert timeline.total_waves > 1
        assert timeline.total_expected_days > 0
        assert timeline.end_date > date(2026, 7, 1)

        # Each wave should have non-zero duration
        for w in timeline.wave_estimates:
            assert w.expected_days > 0
            assert w.app_count > 0

    def test_waves_dont_overlap(self):
        parsed = parse_input(CSV_PATH)
        scored, _ = assign_all_strategies(parsed.applications)
        G = build_dependency_graph(scored)
        waves = topological_sort_waves(G)
        timeline = estimate_wave_time(waves, scored)

        for i in range(1, len(timeline.wave_estimates)):
            prev = timeline.wave_estimates[i - 1]
            curr = timeline.wave_estimates[i]
            assert curr.start_day == pytest.approx(prev.end_day, abs=0.01)

    def test_custom_time_map(self):
        parsed = parse_input(CSV_PATH)
        scored, _ = assign_all_strategies(parsed.applications)
        G = build_dependency_graph(scored)
        waves = topological_sort_waves(G)

        fast_map = {"Low": (1, 1), "Medium": (1, 2), "High": (2, 3)}
        timeline = estimate_wave_time(waves, scored, time_map=fast_map)
        assert timeline.total_expected_days > 0


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
