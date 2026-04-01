"""
RootNode - Step 3 Test Suite: Migration Wave Analyzer
======================================================
Covers: wave grouping, ordering, cycle handling, sort strategies,
        metadata computation, and full fixture integration.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.models.application import ApplicationRecord
from backend.graph.dag_builder import build_dependency_graph
from backend.graph.wave_analyzer import topological_sort_waves, WaveAnalysisResult
from backend.parsers.csv_parser import parse_input


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "..", "backend", "fixtures")
CSV_PATH = os.path.join(FIXTURES_DIR, "sample_apps.csv")


def _make_app(app_id, name, deps=None, criticality="medium",
              data_size=10.0, priority=3, complexity="simple"):
    return ApplicationRecord(
        app_id=app_id, name=name, dependencies=deps or [],
        criticality=criticality, data_size=data_size,
        business_priority=priority, complexity=complexity,
    )


def _chain():
    """A → B → C → D linear chain = 4 waves."""
    return [
        _make_app("A", "Svc A"),
        _make_app("B", "Svc B", ["A"]),
        _make_app("C", "Svc C", ["B"]),
        _make_app("D", "Svc D", ["C"]),
    ]


def _diamond():
    """
       A
      / \\
     B   C
      \\ /
       D
    2 waves: [A] then [B,C] then [D] = 3 waves
    """
    return [
        _make_app("A", "Root"),
        _make_app("B", "Left", ["A"]),
        _make_app("C", "Right", ["A"]),
        _make_app("D", "Join", ["B", "C"]),
    ]


def _parallel():
    """Three independent apps = 1 wave."""
    return [
        _make_app("X", "X App"),
        _make_app("Y", "Y App"),
        _make_app("Z", "Z App"),
    ]


# ===========================================================================
# Wave Grouping
# ===========================================================================

class TestWaveGrouping:
    """Core wave assignment tests."""

    def test_linear_chain_produces_sequential_waves(self):
        apps = _chain()
        G = build_dependency_graph(apps)
        result = topological_sort_waves(G)
        assert result.total_waves == 4
        assert result.waves[0].app_ids == ["A"]
        assert result.waves[1].app_ids == ["B"]
        assert result.waves[2].app_ids == ["C"]
        assert result.waves[3].app_ids == ["D"]

    def test_diamond_produces_three_waves(self):
        apps = _diamond()
        G = build_dependency_graph(apps)
        result = topological_sort_waves(G)
        assert result.total_waves == 3
        assert result.waves[0].app_ids == ["A"]
        assert sorted(result.waves[1].app_ids) == ["B", "C"]
        assert result.waves[2].app_ids == ["D"]

    def test_parallel_apps_single_wave(self):
        apps = _parallel()
        G = build_dependency_graph(apps)
        result = topological_sort_waves(G)
        assert result.total_waves == 1
        assert result.waves[0].app_count == 3

    def test_empty_graph(self):
        G = build_dependency_graph([])
        result = topological_sort_waves(G)
        assert result.total_waves == 0
        assert result.total_apps == 0
        assert result.is_valid

    def test_single_node(self):
        apps = [_make_app("SOLO", "Solo")]
        G = build_dependency_graph(apps)
        result = topological_sort_waves(G)
        assert result.total_waves == 1
        assert result.waves[0].app_ids == ["SOLO"]

    def test_wave_numbers_sequential(self):
        apps = _chain()
        G = build_dependency_graph(apps)
        result = topological_sort_waves(G)
        for i, wave in enumerate(result.waves):
            assert wave.wave_number == i

    def test_all_apps_assigned(self):
        apps = _diamond()
        G = build_dependency_graph(apps)
        result = topological_sort_waves(G)
        all_assigned = []
        for wave in result.waves:
            all_assigned.extend(wave.app_ids)
        assert sorted(all_assigned) == ["A", "B", "C", "D"]
        assert result.total_apps == 4


# ===========================================================================
# Dependency Order Correctness
# ===========================================================================

class TestDependencyOrder:
    """Verify that dependencies always appear in earlier waves."""

    def test_dep_before_dependent_chain(self):
        apps = _chain()
        G = build_dependency_graph(apps)
        result = topological_sort_waves(G)
        mapping = result.app_to_wave
        assert mapping["A"] < mapping["B"]
        assert mapping["B"] < mapping["C"]
        assert mapping["C"] < mapping["D"]

    def test_dep_before_dependent_diamond(self):
        apps = _diamond()
        G = build_dependency_graph(apps)
        result = topological_sort_waves(G)
        mapping = result.app_to_wave
        assert mapping["A"] < mapping["B"]
        assert mapping["A"] < mapping["C"]
        assert mapping["B"] < mapping["D"]
        assert mapping["C"] < mapping["D"]

    def test_complex_graph_ordering(self):
        """Multi-root, multi-level graph."""
        apps = [
            _make_app("R1", "Root 1"),
            _make_app("R2", "Root 2"),
            _make_app("M1", "Mid 1", ["R1"]),
            _make_app("M2", "Mid 2", ["R1", "R2"]),
            _make_app("L1", "Leaf 1", ["M1", "M2"]),
        ]
        G = build_dependency_graph(apps)
        result = topological_sort_waves(G)
        mapping = result.app_to_wave
        # Both roots in wave 0
        assert mapping["R1"] == 0
        assert mapping["R2"] == 0
        # Mid nodes in wave 1
        assert mapping["M1"] == 1
        assert mapping["M2"] == 1
        # Leaf in wave 2
        assert mapping["L1"] == 2


# ===========================================================================
# Cycle Handling
# ===========================================================================

class TestCycleHandling:
    """Verify graceful degradation when cycles exist."""

    def test_cycle_marks_invalid(self):
        apps = [
            _make_app("A", "A", ["C"]),
            _make_app("B", "B", ["A"]),
            _make_app("C", "C", ["B"]),
        ]
        G = build_dependency_graph(apps)
        result = topological_sort_waves(G)
        assert result.is_valid is False
        assert len(result.unresolved_apps) == 3

    def test_partial_cycle(self):
        """Some nodes resolvable, some in a cycle."""
        apps = [
            _make_app("OK1", "OK 1"),
            _make_app("OK2", "OK 2", ["OK1"]),
            _make_app("CYC_A", "Cyc A", ["CYC_B"]),
            _make_app("CYC_B", "Cyc B", ["CYC_A"]),
        ]
        G = build_dependency_graph(apps)
        result = topological_sort_waves(G)
        assert result.is_valid is False
        # OK1 and OK2 should still be in waves
        assigned = []
        for wave in result.waves:
            assigned.extend(wave.app_ids)
        assert "OK1" in assigned
        assert "OK2" in assigned
        # Cyclic nodes are unresolved
        assert "CYC_A" in result.unresolved_apps
        assert "CYC_B" in result.unresolved_apps


# ===========================================================================
# Sorting Within Waves
# ===========================================================================

class TestWaveSorting:
    """Verify intra-wave sorting strategies."""

    def test_sort_by_business_priority(self):
        apps = [
            _make_app("LOW", "Low Pri", priority=5),
            _make_app("HIGH", "High Pri", priority=1),
            _make_app("MED", "Medium Pri", priority=3),
        ]
        G = build_dependency_graph(apps)
        result = topological_sort_waves(G, sort_within_wave="business_priority")
        ids = result.waves[0].app_ids
        assert ids == ["HIGH", "MED", "LOW"]

    def test_sort_by_criticality(self):
        apps = [
            _make_app("L", "Low", criticality="low"),
            _make_app("C", "Crit", criticality="critical"),
            _make_app("H", "High", criticality="high"),
        ]
        G = build_dependency_graph(apps)
        result = topological_sort_waves(G, sort_within_wave="criticality")
        ids = result.waves[0].app_ids
        assert ids == ["C", "H", "L"]

    def test_sort_by_data_size(self):
        apps = [
            _make_app("SM", "Small", data_size=10),
            _make_app("LG", "Large", data_size=500),
            _make_app("MD", "Medium", data_size=100),
        ]
        G = build_dependency_graph(apps)
        result = topological_sort_waves(G, sort_within_wave="data_size")
        ids = result.waves[0].app_ids
        assert ids == ["LG", "MD", "SM"]

    def test_sort_by_app_id(self):
        apps = [
            _make_app("C", "C App"),
            _make_app("A", "A App"),
            _make_app("B", "B App"),
        ]
        G = build_dependency_graph(apps)
        result = topological_sort_waves(G, sort_within_wave="app_id")
        ids = result.waves[0].app_ids
        assert ids == ["A", "B", "C"]


# ===========================================================================
# Wave Metadata
# ===========================================================================

class TestWaveMetadata:
    """Verify computed wave properties."""

    def test_total_data_size(self):
        apps = [
            _make_app("A", "A", data_size=100.5),
            _make_app("B", "B", data_size=200.0),
        ]
        G = build_dependency_graph(apps)
        result = topological_sort_waves(G)
        assert result.waves[0].total_data_size == 300.5

    def test_max_criticality(self):
        apps = [
            _make_app("L", "Low", criticality="low"),
            _make_app("C", "Crit", criticality="critical"),
        ]
        G = build_dependency_graph(apps)
        result = topological_sort_waves(G)
        assert result.waves[0].max_criticality == "critical"

    def test_app_to_wave_mapping(self):
        apps = _chain()
        G = build_dependency_graph(apps)
        result = topological_sort_waves(G)
        mapping = result.app_to_wave
        assert mapping == {"A": 0, "B": 1, "C": 2, "D": 3}

    def test_get_wave(self):
        apps = _chain()
        G = build_dependency_graph(apps)
        result = topological_sort_waves(G)
        wave1 = result.get_wave(1)
        assert wave1 is not None
        assert wave1.app_ids == ["B"]
        assert result.get_wave(99) is None


# ===========================================================================
# Serialization
# ===========================================================================

class TestSerialization:
    """Verify JSON-safe dict output."""

    def test_to_dict_structure(self):
        apps = _diamond()
        G = build_dependency_graph(apps)
        result = topological_sort_waves(G)
        d = result.to_dict()
        assert "total_waves" in d
        assert "total_apps" in d
        assert "waves" in d
        assert len(d["waves"]) == 3

    def test_wave_dict_fields(self):
        apps = _diamond()
        G = build_dependency_graph(apps)
        result = topological_sort_waves(G)
        d = result.to_dict()
        wave0 = d["waves"][0]
        assert "wave_number" in wave0
        assert "app_count" in wave0
        assert "total_data_size" in wave0
        assert "max_criticality" in wave0
        assert "items" in wave0

    def test_item_dict_fields(self):
        apps = [_make_app("A", "Auth", criticality="critical")]
        G = build_dependency_graph(apps)
        result = topological_sort_waves(G)
        d = result.to_dict()
        item = d["waves"][0]["items"][0]
        assert item["app_id"] == "A"
        assert item["criticality"] == "critical"


# ===========================================================================
# Full Fixture Integration
# ===========================================================================

class TestFullFixture:
    """End-to-end test with the 15-app sample data."""

    def test_full_pipeline(self):
        parsed = parse_input(CSV_PATH)
        G = build_dependency_graph(parsed.applications)
        result = topological_sort_waves(G)

        assert result.is_valid
        assert result.total_apps == 15
        assert result.total_waves > 1

        # Wave 0 must contain root nodes (no deps)
        wave0_ids = set(result.waves[0].app_ids)
        assert "APP001" in wave0_ids  # Auth Service
        assert "APP010" in wave0_ids  # Legacy CRM
        assert "APP012" in wave0_ids  # CDN

        # Every app assigned exactly once
        all_ids = []
        for wave in result.waves:
            all_ids.extend(wave.app_ids)
        assert len(all_ids) == 15
        assert len(set(all_ids)) == 15

    def test_dependencies_respect_wave_order(self):
        parsed = parse_input(CSV_PATH)
        G = build_dependency_graph(parsed.applications)
        result = topological_sort_waves(G)
        mapping = result.app_to_wave

        # APP002 depends on APP001 → APP002 in later wave
        assert mapping["APP001"] < mapping["APP002"]
        # APP011 depends on APP001, APP002, APP003
        assert mapping["APP001"] < mapping["APP011"]
        assert mapping["APP002"] < mapping["APP011"]
        assert mapping["APP003"] < mapping["APP011"]

    def test_original_graph_not_mutated(self):
        parsed = parse_input(CSV_PATH)
        G = build_dependency_graph(parsed.applications)
        original_nodes = G.number_of_nodes()
        original_edges = G.number_of_edges()

        topological_sort_waves(G)

        assert G.number_of_nodes() == original_nodes
        assert G.number_of_edges() == original_edges


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
