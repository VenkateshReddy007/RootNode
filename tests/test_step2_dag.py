"""
RootNode - Step 2 Test Suite: Dependency DAG Builder
=====================================================
Covers: graph construction, edge direction, cycle detection,
        dangling deps, stats computation, utility functions,
        and JSON serialization.
"""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.models.application import ApplicationRecord
from backend.graph.dag_builder import (
    build_dependency_graph,
    get_ancestors,
    get_descendants,
    get_direct_dependencies,
    get_direct_dependents,
    graph_to_dict,
    subgraph_for_app,
)
from backend.parsers.csv_parser import parse_input


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "..", "backend", "fixtures")
CSV_PATH = os.path.join(FIXTURES_DIR, "sample_apps.csv")


def _make_app(app_id: str, name: str, deps: list = None) -> ApplicationRecord:
    """Quick factory for test ApplicationRecords."""
    return ApplicationRecord(
        app_id=app_id,
        name=name,
        dependencies=deps or [],
        criticality="medium",
        data_size=10.0,
        business_priority=3,
        complexity="simple",
    )


def _simple_chain():
    """A → B → C linear chain."""
    return [
        _make_app("A", "Service A"),
        _make_app("B", "Service B", ["A"]),
        _make_app("C", "Service C", ["B"]),
    ]


def _diamond():
    """
    Diamond dependency:
        A
       / \
      B   C
       \ /
        D
    """
    return [
        _make_app("A", "Root"),
        _make_app("B", "Left", ["A"]),
        _make_app("C", "Right", ["A"]),
        _make_app("D", "Join", ["B", "C"]),
    ]


# ===========================================================================
# Graph Construction
# ===========================================================================

class TestGraphConstruction:
    """Core graph building tests."""

    def test_basic_construction(self):
        apps = _simple_chain()
        G = build_dependency_graph(apps)
        assert G.number_of_nodes() == 3
        assert G.number_of_edges() == 2

    def test_edge_direction_dep_to_dependent(self):
        """Edge goes FROM dependency TO dependent."""
        apps = _simple_chain()
        G = build_dependency_graph(apps)
        # B depends on A → edge is A→B
        assert G.has_edge("A", "B")
        assert G.has_edge("B", "C")
        # NOT reversed
        assert not G.has_edge("B", "A")

    def test_diamond_graph(self):
        apps = _diamond()
        G = build_dependency_graph(apps)
        assert G.number_of_nodes() == 4
        assert G.number_of_edges() == 4
        assert G.has_edge("A", "B")
        assert G.has_edge("A", "C")
        assert G.has_edge("B", "D")
        assert G.has_edge("C", "D")

    def test_isolated_node(self):
        apps = [
            _make_app("A", "Root"),
            _make_app("B", "Isolated"),  # no deps, nothing depends on it
            _make_app("C", "Child", ["A"]),
        ]
        G = build_dependency_graph(apps)
        assert "B" in G.graph["stats"].isolated_nodes

    def test_no_apps(self):
        G = build_dependency_graph([])
        assert G.number_of_nodes() == 0
        assert G.graph["stats"].is_dag

    def test_single_app_no_deps(self):
        apps = [_make_app("SOLO", "Solo App")]
        G = build_dependency_graph(apps)
        assert G.number_of_nodes() == 1
        assert G.number_of_edges() == 0
        assert G.graph["stats"].is_dag

    def test_full_fixture(self):
        result = parse_input(CSV_PATH)
        G = build_dependency_graph(result.applications)
        assert G.number_of_nodes() == 15
        assert G.graph["stats"].is_dag


# ===========================================================================
# Node Metadata
# ===========================================================================

class TestNodeMetadata:
    """Verify node attributes are attached correctly."""

    def test_node_has_attributes(self):
        apps = [_make_app("A", "Auth Service")]
        G = build_dependency_graph(apps)
        data = G.nodes["A"]
        assert data["name"] == "Auth Service"
        assert data["criticality"] == "medium"
        assert data["data_size"] == 10.0

    def test_metadata_disabled(self):
        apps = [_make_app("A", "Auth")]
        G = build_dependency_graph(apps, include_metadata=False)
        data = G.nodes["A"]
        assert "name" not in data


# ===========================================================================
# DAG Validation
# ===========================================================================

class TestDAGValidation:
    """Cycle detection and DAG property tests."""

    def test_is_dag(self):
        apps = _simple_chain()
        G = build_dependency_graph(apps)
        assert G.graph["stats"].is_dag is True

    def test_cycle_detected(self):
        """Create a cycle: A→B→C→A."""
        apps = [
            _make_app("A", "Svc A", ["C"]),
            _make_app("B", "Svc B", ["A"]),
            _make_app("C", "Svc C", ["B"]),
        ]
        G = build_dependency_graph(apps)
        assert G.graph["stats"].is_dag is False
        assert len(G.graph["stats"].cycles) > 0

    def test_cycle_strict_raises(self):
        apps = [
            _make_app("A", "Svc A", ["C"]),
            _make_app("B", "Svc B", ["A"]),
            _make_app("C", "Svc C", ["B"]),
        ]
        with pytest.raises(ValueError, match="cycles"):
            build_dependency_graph(apps, strict=True)


# ===========================================================================
# Dangling Dependencies
# ===========================================================================

class TestDanglingDeps:
    """Tests for references to non-existent applications."""

    def test_dangling_dep_warning(self):
        apps = [_make_app("A", "App A", ["GHOST"])]
        G = build_dependency_graph(apps)
        assert len(G.graph["dangling_deps"]) > 0
        # Phantom node created
        assert "GHOST" in G.nodes

    def test_dangling_dep_strict_raises(self):
        apps = [_make_app("A", "App A", ["GHOST"])]
        with pytest.raises(ValueError, match="Dangling"):
            build_dependency_graph(apps, strict=True)

    def test_phantom_node_marked(self):
        apps = [_make_app("A", "App A", ["GHOST"])]
        G = build_dependency_graph(apps)
        assert G.nodes["GHOST"].get("phantom") is True


# ===========================================================================
# Graph Statistics
# ===========================================================================

class TestGraphStats:
    """Verify computed statistics."""

    def test_root_nodes(self):
        apps = _simple_chain()
        G = build_dependency_graph(apps)
        assert G.graph["stats"].root_nodes == ["A"]

    def test_leaf_nodes(self):
        apps = _simple_chain()
        G = build_dependency_graph(apps)
        assert G.graph["stats"].leaf_nodes == ["C"]

    def test_diamond_roots_and_leaves(self):
        apps = _diamond()
        G = build_dependency_graph(apps)
        assert G.graph["stats"].root_nodes == ["A"]
        assert G.graph["stats"].leaf_nodes == ["D"]

    def test_max_depth_chain(self):
        apps = _simple_chain()
        G = build_dependency_graph(apps)
        assert G.graph["stats"].max_depth == 2  # A→B→C = path length 2

    def test_max_depth_diamond(self):
        apps = _diamond()
        G = build_dependency_graph(apps)
        assert G.graph["stats"].max_depth == 2  # A→B→D or A→C→D

    def test_density(self):
        apps = _diamond()
        G = build_dependency_graph(apps)
        # 4 edges / (4 * 3) = 0.3333
        assert 0.3 < G.graph["stats"].density < 0.4

    def test_full_fixture_roots(self):
        """Root nodes should be apps with no dependencies."""
        result = parse_input(CSV_PATH)
        G = build_dependency_graph(result.applications)
        stats = G.graph["stats"]
        # APP001 (Auth), APP010 (CRM), APP012 (CDN) have no deps
        for root in ["APP001", "APP010", "APP012"]:
            assert root in stats.root_nodes


# ===========================================================================
# Utility Functions
# ===========================================================================

class TestUtilities:
    """Tests for graph query utilities."""

    def test_get_ancestors(self):
        apps = _simple_chain()
        G = build_dependency_graph(apps)
        assert get_ancestors(G, "C") == {"A", "B"}

    def test_get_descendants(self):
        apps = _simple_chain()
        G = build_dependency_graph(apps)
        assert get_descendants(G, "A") == {"B", "C"}

    def test_direct_dependencies(self):
        apps = _diamond()
        G = build_dependency_graph(apps)
        assert sorted(get_direct_dependencies(G, "D")) == ["B", "C"]

    def test_direct_dependents(self):
        apps = _diamond()
        G = build_dependency_graph(apps)
        assert sorted(get_direct_dependents(G, "A")) == ["B", "C"]

    def test_subgraph(self):
        apps = _diamond()
        G = build_dependency_graph(apps)
        sub = subgraph_for_app(G, "B")
        # B's ancestors (A) + B's descendants (D) + B itself
        # D also pulls in C (since C→D), but subgraph_for_app only
        # looks at B's ancestors/descendants
        assert "A" in sub.nodes
        assert "B" in sub.nodes
        assert "D" in sub.nodes

    def test_ancestors_of_root_is_empty(self):
        apps = _simple_chain()
        G = build_dependency_graph(apps)
        assert get_ancestors(G, "A") == set()

    def test_descendants_of_leaf_is_empty(self):
        apps = _simple_chain()
        G = build_dependency_graph(apps)
        assert get_descendants(G, "C") == set()


# ===========================================================================
# Serialization
# ===========================================================================

class TestSerialization:
    """Tests for graph_to_dict output."""

    def test_to_dict_structure(self):
        apps = _simple_chain()
        G = build_dependency_graph(apps)
        d = graph_to_dict(G)
        assert "nodes" in d
        assert "edges" in d
        assert "stats" in d

    def test_to_dict_nodes(self):
        apps = _simple_chain()
        G = build_dependency_graph(apps)
        d = graph_to_dict(G)
        app_ids = {n["app_id"] for n in d["nodes"]}
        assert app_ids == {"A", "B", "C"}

    def test_to_dict_edges(self):
        apps = _simple_chain()
        G = build_dependency_graph(apps)
        d = graph_to_dict(G)
        edges = d["edges"]
        assert {"source": "A", "target": "B"} in edges
        assert {"source": "B", "target": "C"} in edges

    def test_to_dict_json_serializable(self):
        apps = _diamond()
        G = build_dependency_graph(apps)
        d = graph_to_dict(G)
        # Must not raise
        serialized = json.dumps(d)
        assert len(serialized) > 0

    def test_to_dict_stats(self):
        apps = _diamond()
        G = build_dependency_graph(apps)
        d = graph_to_dict(G)
        assert d["stats"]["total_nodes"] == 4
        assert d["stats"]["is_dag"] is True


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
