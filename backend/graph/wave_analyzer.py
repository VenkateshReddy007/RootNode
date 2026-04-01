"""
RootNode - Migration Wave Analyzer (Step 3)
=============================================
Performs layered topological sort (Kahn's algorithm) to group
applications into parallelizable migration waves.

Wave semantics:
  • Wave 0 = root nodes (zero in-degree) → migrate first
  • Wave N = nodes whose ALL dependencies are in waves 0..(N-1)
  • Apps within the same wave can migrate in parallel

This is the core scheduling primitive for the migration roadmap.

Optimized for AWS Lambda:
  • O(V + E) time complexity
  • Operates on a copy — original graph is never mutated
  • Rich wave metadata for downstream risk scoring + AI roadmap
"""

from __future__ import annotations

import logging
import os
from collections import deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

import networkx as nx

from backend.models.application import ApplicationRecord

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

@dataclass
class WaveItem:
    """A single application within a migration wave."""
    app_id: str
    name: str
    criticality: str
    complexity: str
    data_size: float
    business_priority: int
    dependencies: List[str]
    risk_score: Optional[float] = None
    migration_strategy: Optional[str] = None

    def to_dict(self) -> Dict:
        d = {
            "app_id": self.app_id,
            "name": self.name,
            "criticality": self.criticality,
            "complexity": self.complexity,
            "data_size": self.data_size,
            "business_priority": self.business_priority,
            "dependencies": self.dependencies,
        }
        if self.risk_score is not None:
            d["risk_score"] = self.risk_score
        if self.migration_strategy is not None:
            d["migration_strategy"] = self.migration_strategy
        return d


@dataclass
class Wave:
    """A single migration wave — a group of apps that can migrate in parallel."""
    wave_number: int
    items: List[WaveItem] = field(default_factory=list)

    @property
    def app_ids(self) -> List[str]:
        return [item.app_id for item in self.items]

    @property
    def total_data_size(self) -> float:
        return sum(item.data_size for item in self.items)

    @property
    def max_criticality(self) -> str:
        priority = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        if not self.items:
            return "low"
        return min(self.items, key=lambda i: priority.get(i.criticality, 99)).criticality

    @property
    def app_count(self) -> int:
        return len(self.items)

    def to_dict(self) -> Dict:
        return {
            "wave_number": self.wave_number,
            "app_count": self.app_count,
            "total_data_size": round(self.total_data_size, 2),
            "max_criticality": self.max_criticality,
            "items": [item.to_dict() for item in self.items],
        }


@dataclass
class WaveAnalysisResult:
    """Complete output of wave analysis."""
    waves: List[Wave] = field(default_factory=list)
    total_waves: int = 0
    total_apps: int = 0
    is_valid: bool = True
    unresolved_apps: List[str] = field(default_factory=list)  # apps stuck in cycles

    @property
    def app_to_wave(self) -> Dict[str, int]:
        """Map of app_id → wave number for quick lookup."""
        mapping = {}
        for wave in self.waves:
            for item in wave.items:
                mapping[item.app_id] = wave.wave_number
        return mapping

    def get_wave(self, wave_number: int) -> Optional[Wave]:
        """Retrieve a specific wave by number."""
        for wave in self.waves:
            if wave.wave_number == wave_number:
                return wave
        return None

    def to_dict(self) -> Dict:
        return {
            "total_waves": self.total_waves,
            "total_apps": self.total_apps,
            "is_valid": self.is_valid,
            "unresolved_apps": self.unresolved_apps,
            "waves": [wave.to_dict() for wave in self.waves],
        }


# ===========================================================================
# Core Algorithm
# ===========================================================================

def topological_sort_waves(
    graph: nx.DiGraph,
    *,
    sort_within_wave: str = "business_priority",
) -> WaveAnalysisResult:
    """
    Perform layered topological sort to produce migration waves.

    Uses Kahn's algorithm with level grouping:
      1. Find all nodes with zero in-degree → Wave 0
      2. Remove them from the graph
      3. Find new zero in-degree nodes → Wave 1
      4. Repeat until graph is empty

    Parameters
    ----------
    graph : nx.DiGraph
        Dependency graph from build_dependency_graph().
        Edge direction: dependency → dependent.
    sort_within_wave : str
        Attribute to sort apps within each wave. Options:
        'business_priority', 'criticality', 'data_size', 'app_id'.
        Default sorts by business_priority (1 = highest first).

    Returns
    -------
    WaveAnalysisResult
        Ordered list of waves with metadata.
        If graph has cycles, unresolved_apps lists the stuck nodes.

    Example
    -------
    >>> from backend.parsers import parse_input
    >>> from backend.graph import build_dependency_graph
    >>> result = parse_input("path/to/apps.csv")
    >>> G = build_dependency_graph(result.applications)
    >>> waves = topological_sort_waves(G)
    >>> for wave in waves.waves:
    ...     print(f"Wave {wave.wave_number}: {wave.app_ids}")
    """
    # Work on a copy — never mutate the original graph
    G = graph.copy()
    waves: List[Wave] = []
    wave_number = 0
    total_processed = 0

    while G.number_of_nodes() > 0:
        # Find all zero in-degree nodes (ready to migrate)
        zero_in = [n for n in G.nodes() if G.in_degree(n) == 0]

        if not zero_in:
            # Remaining nodes are in cycles — cannot be scheduled
            unresolved = list(G.nodes())
            logger.error(
                f"Wave analysis stalled at wave {wave_number}: "
                f"{len(unresolved)} nodes in cycles: {unresolved}"
            )
            return WaveAnalysisResult(
                waves=waves,
                total_waves=len(waves),
                total_apps=total_processed,
                is_valid=False,
                unresolved_apps=unresolved,
            )

        # Build wave items from node attributes
        wave_items: List[WaveItem] = []
        for node_id in zero_in:
            attrs = G.nodes[node_id]
            item = WaveItem(
                app_id=node_id,
                name=attrs.get("name", node_id),
                criticality=attrs.get("criticality", "medium"),
                complexity=attrs.get("complexity", "moderate"),
                data_size=attrs.get("data_size", 0.0),
                business_priority=attrs.get("business_priority", 3),
                dependencies=attrs.get("dependencies", []),
                risk_score=attrs.get("risk_score"),
                migration_strategy=attrs.get("migration_strategy"),
            )
            wave_items.append(item)

        # Sort within wave
        wave_items = _sort_wave_items(wave_items, sort_within_wave)

        wave = Wave(wave_number=wave_number, items=wave_items)
        waves.append(wave)
        total_processed += len(zero_in)

        logger.debug(
            f"Wave {wave_number}: {len(zero_in)} apps — {wave.app_ids}"
        )

        # Remove processed nodes and their edges
        G.remove_nodes_from(zero_in)
        wave_number += 1

    result = WaveAnalysisResult(
        waves=waves,
        total_waves=len(waves),
        total_apps=total_processed,
        is_valid=True,
        unresolved_apps=[],
    )

    logger.info(
        f"topological_sort_waves complete: "
        f"{result.total_apps} apps across {result.total_waves} waves"
    )

    return result


# ---------------------------------------------------------------------------
# Sorting Helpers
# ---------------------------------------------------------------------------

_CRITICALITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def _sort_wave_items(items: List[WaveItem], sort_by: str) -> List[WaveItem]:
    """Sort items within a wave for deterministic ordering."""
    if sort_by == "business_priority":
        return sorted(items, key=lambda i: (i.business_priority, i.app_id))
    elif sort_by == "criticality":
        return sorted(
            items,
            key=lambda i: (_CRITICALITY_ORDER.get(i.criticality, 99), i.app_id),
        )
    elif sort_by == "data_size":
        return sorted(items, key=lambda i: (-i.data_size, i.app_id))
    elif sort_by == "app_id":
        return sorted(items, key=lambda i: i.app_id)
    else:
        return sorted(items, key=lambda i: (i.business_priority, i.app_id))
