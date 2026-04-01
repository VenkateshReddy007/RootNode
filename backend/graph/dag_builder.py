"""
RootNode - Dependency DAG Builder (Step 2)
===========================================
Constructs a validated Directed Acyclic Graph from parsed application records.

Edge semantics:  dependency ──► dependent
    (APP001) ──► (APP002)  means APP002 depends on APP001,
    i.e. APP001 must migrate first.

This direction is critical — topological sort gives migration order directly.

Optimized for AWS Lambda:
  • Single-pass graph construction
  • Minimal memory footprint (node attrs stored by reference)
  • Cycle detection via NetworkX DFS (O(V+E))
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

import networkx as nx

from backend.models.application import ApplicationRecord

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))


# ---------------------------------------------------------------------------
# Graph Metadata
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class GraphStats:
    """Summary statistics for a dependency graph."""
    total_nodes: int
    total_edges: int
    is_dag: bool
    root_nodes: List[str]          # nodes with no incoming edges (migrate first)
    leaf_nodes: List[str]          # nodes with no outgoing edges (nothing depends on them)
    max_depth: int                 # longest path in the DAG
    density: float                 # edge density
    isolated_nodes: List[str]      # nodes with no edges at all
    cycles: List[List[str]] = field(default_factory=list)  # populated only if graph has cycles


# ---------------------------------------------------------------------------
# Core Builder
# ---------------------------------------------------------------------------

def build_dependency_graph(
    apps: List[ApplicationRecord],
    *,
    strict: bool = False,
    include_metadata: bool = True,
) -> nx.DiGraph:
    """
    Build a directed dependency graph from application records.

    Parameters
    ----------
    apps : list[ApplicationRecord]
        Validated application records from parse_input().
    strict : bool
        If True, raise on cycles or dangling dependencies instead of
        logging warnings.
    include_metadata : bool
        If True, attach full application attributes as node data.

    Returns
    -------
    nx.DiGraph
        Directed graph where edge (A → B) means B depends on A.
        Node attributes include all ApplicationRecord fields.
        Graph-level attribute 'stats' contains a GraphStats summary.

    Raises
    ------
    ValueError
        In strict mode: if the graph contains cycles or dangling deps.

    Example
    -------
    >>> from backend.parsers import parse_input
    >>> result = parse_input("path/to/apps.csv")
    >>> G = build_dependency_graph(result.applications)
    >>> print(G.graph['stats'].total_nodes)
    15
    """
    G = nx.DiGraph()
    app_index: Dict[str, ApplicationRecord] = {}
    dangling: List[str] = []

    # ---- 1. Register all nodes --------------------------------------------
    for app in apps:
        app_index[app.app_id] = app

        node_attrs = {}
        if include_metadata:
            node_attrs = {
                "name": app.name,
                "criticality": app.criticality,
                "data_size": app.data_size,
                "business_priority": app.business_priority,
                "complexity": app.complexity,
                "risk_score": app.risk_score,
                "migration_strategy": app.migration_strategy,
                "dependencies": app.dependencies,
            }

        G.add_node(app.app_id, **node_attrs)

    # ---- 2. Add edges: dependency ──► dependent ---------------------------
    all_ids: Set[str] = set(app_index.keys())

    for app in apps:
        for dep_id in app.dependencies:
            if dep_id not in all_ids:
                msg = (
                    f"Dangling dependency: '{app.app_id}' depends on "
                    f"'{dep_id}' which is not in the graph."
                )
                dangling.append(msg)
                logger.warning(msg)

                if strict:
                    raise ValueError(msg)

                # Add a phantom node so the graph remains queryable
                G.add_node(dep_id, phantom=True, name=f"[UNKNOWN] {dep_id}")
            
            # Edge direction: dep_id ──► app.app_id
            # "dep must be done before app"
            G.add_edge(dep_id, app.app_id)

    # ---- 3. Cycle detection -----------------------------------------------
    cycles: List[List[str]] = []
    is_dag = nx.is_directed_acyclic_graph(G)

    if not is_dag:
        try:
            cycle = nx.find_cycle(G, orientation="original")
            cycle_path = [edge[0] for edge in cycle] + [cycle[-1][1]]
            cycles.append(cycle_path)
            logger.error(f"Cycle detected in dependency graph: {cycle_path}")
        except nx.NetworkXNoCycle:
            pass  # shouldn't happen if is_dag is False, but be safe

        if strict:
            raise ValueError(
                f"Dependency graph contains cycles: {cycles}. "
                "A DAG is required for migration wave planning."
            )

    # ---- 4. Compute graph statistics --------------------------------------
    root_nodes = [n for n in G.nodes() if G.in_degree(n) == 0]
    leaf_nodes = [n for n in G.nodes() if G.out_degree(n) == 0]
    isolated = list(nx.isolates(G))

    max_depth = 0
    if is_dag and G.number_of_nodes() > 0:
        max_depth = nx.dag_longest_path_length(G)

    density = nx.density(G) if G.number_of_nodes() > 1 else 0.0

    stats = GraphStats(
        total_nodes=G.number_of_nodes(),
        total_edges=G.number_of_edges(),
        is_dag=is_dag,
        root_nodes=sorted(root_nodes),
        leaf_nodes=sorted(leaf_nodes),
        max_depth=max_depth,
        density=round(density, 4),
        isolated_nodes=sorted(isolated),
        cycles=cycles,
    )

    G.graph["stats"] = stats
    G.graph["dangling_deps"] = dangling

    logger.info(
        f"build_dependency_graph complete: "
        f"{stats.total_nodes} nodes, {stats.total_edges} edges, "
        f"is_dag={stats.is_dag}, max_depth={stats.max_depth}, "
        f"roots={stats.root_nodes}"
    )

    return G


# ---------------------------------------------------------------------------
# Utility Functions
# ---------------------------------------------------------------------------

def get_ancestors(G: nx.DiGraph, app_id: str) -> Set[str]:
    """Get all transitive dependencies of an application (must migrate before it)."""
    return nx.ancestors(G, app_id)


def get_descendants(G: nx.DiGraph, app_id: str) -> Set[str]:
    """Get all applications that transitively depend on this one."""
    return nx.descendants(G, app_id)


def get_direct_dependencies(G: nx.DiGraph, app_id: str) -> List[str]:
    """Get immediate dependencies (predecessors in the graph)."""
    return list(G.predecessors(app_id))


def get_direct_dependents(G: nx.DiGraph, app_id: str) -> List[str]:
    """Get applications that directly depend on this one (successors)."""
    return list(G.successors(app_id))


def subgraph_for_app(G: nx.DiGraph, app_id: str) -> nx.DiGraph:
    """Extract the full dependency tree rooted at an application."""
    ancestors = nx.ancestors(G, app_id)
    descendants = nx.descendants(G, app_id)
    relevant = ancestors | descendants | {app_id}
    return G.subgraph(relevant).copy()


def graph_to_dict(G: nx.DiGraph) -> Dict:
    """
    Serialize graph to a JSON-safe dictionary.
    Useful for Lambda response payloads and frontend consumption.
    """
    nodes = []
    for node_id, attrs in G.nodes(data=True):
        node_data = {"app_id": node_id, **attrs}
        # Remove non-serializable items
        node_data.pop("risk_score", None) if node_data.get("risk_score") is None else None
        node_data.pop("migration_strategy", None) if node_data.get("migration_strategy") is None else None
        nodes.append(node_data)

    edges = [
        {"source": u, "target": v}
        for u, v in G.edges()
    ]

    stats = G.graph.get("stats")
    stats_dict = {}
    if stats:
        stats_dict = {
            "total_nodes": stats.total_nodes,
            "total_edges": stats.total_edges,
            "is_dag": stats.is_dag,
            "root_nodes": stats.root_nodes,
            "leaf_nodes": stats.leaf_nodes,
            "max_depth": stats.max_depth,
            "density": stats.density,
            "isolated_nodes": stats.isolated_nodes,
        }

    return {
        "nodes": nodes,
        "edges": edges,
        "stats": stats_dict,
    }
