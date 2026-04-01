"""
RootNode - Bedrock Claude Prompt Builder (Step 7)
===================================================
Constructs a structured prompt for Claude 4.6 (via AWS Bedrock)
that includes all computed migration data and instructs the model
to generate a strategic migration roadmap in JSON format.

Prompt includes:
  • Application inventory with metadata
  • Wave assignments with dependency ordering
  • Risk scores and breakdowns
  • Assigned migration strategies with rationale
  • Time estimates per app and per wave

AI is asked to:
  1. Explain wave grouping logic
  2. Highlight critical risks and mitigation steps
  3. Justify strategy assignments
  4. Provide strategic insights and recommendations

Output format: Structured JSON for frontend consumption.

Optimized for AWS Lambda:
  • Pure string construction — no I/O
  • Token-efficient formatting (minimizes prompt cost)
  • Configurable system/user prompt separation for Bedrock Messages API
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from backend.models.application import ApplicationRecord
from backend.graph.wave_analyzer import WaveAnalysisResult
from backend.scoring.risk_engine import RiskBreakdown
from backend.scoring.strategy_engine import StrategyRecommendation
from backend.scoring.time_estimator import ProjectTimeline

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))


# ---------------------------------------------------------------------------
# Prompt Configuration
# ---------------------------------------------------------------------------

DEFAULT_MODEL_ID = "anthropic.claude-sonnet-4-20250514"
MAX_APPS_IN_PROMPT = int(os.environ.get("PROMPT_MAX_APPS", "50"))


# ---------------------------------------------------------------------------
# Prompt Output
# ---------------------------------------------------------------------------

@dataclass
class PromptPayload:
    """Complete prompt ready for Bedrock Claude Messages API."""
    system_prompt: str
    user_prompt: str
    model_id: str = DEFAULT_MODEL_ID
    max_tokens: int = 4096
    temperature: float = 0.3
    top_p: float = 0.9

    def to_bedrock_messages(self) -> Dict[str, Any]:
        """Format for Bedrock invoke_model (Messages API)."""
        return {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "system": self.system_prompt,
            "messages": [
                {
                    "role": "user",
                    "content": self.user_prompt,
                }
            ],
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "system_prompt": self.system_prompt,
            "user_prompt": self.user_prompt,
            "model_id": self.model_id,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }


# ---------------------------------------------------------------------------
# System Prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are RootNode AI, an expert cloud migration architect. You analyze application portfolios, dependency graphs, and risk assessments to produce strategic migration roadmaps.

Your responses MUST be valid JSON matching the exact schema specified in the user prompt. Do not include any text outside the JSON object.

Your expertise includes:
- AWS migration patterns (7R framework: Retain, Retire, Rehost, Relocate, Repurchase, Replatform, Refactor)
- Dependency-aware migration wave planning
- Risk mitigation strategies for enterprise workloads
- Cloud-native architecture patterns (microservices, serverless, containers)
- Data migration strategies for large-scale databases
- Compliance and security considerations during migration"""


# ---------------------------------------------------------------------------
# Data Serializers
# ---------------------------------------------------------------------------

def _serialize_apps(apps: List[ApplicationRecord]) -> List[Dict]:
    """Serialize apps to token-efficient dicts."""
    result = []
    for app in apps[:MAX_APPS_IN_PROMPT]:
        result.append({
            "app_id": app.app_id,
            "name": app.name,
            "criticality": app.criticality,
            "complexity": app.complexity,
            "data_size_gb": app.data_size,
            "business_priority": app.business_priority,
            "dependencies": app.dependencies,
            "risk_score": app.risk_score,
            "migration_strategy": app.migration_strategy,
        })
    return result


def _serialize_waves(wave_result: WaveAnalysisResult) -> List[Dict]:
    """Serialize wave assignments."""
    waves = []
    for wave in wave_result.waves:
        waves.append({
            "wave_number": wave.wave_number,
            "app_ids": wave.app_ids,
            "app_count": wave.app_count,
            "max_criticality": wave.max_criticality,
            "total_data_size_gb": round(wave.total_data_size, 1),
        })
    return waves


def _serialize_risks(breakdowns: List[RiskBreakdown]) -> List[Dict]:
    """Serialize risk breakdowns."""
    return [
        {
            "app_id": b.app_id,
            "risk_level": b.risk_level,
            "score": b.normalized_score,
            "factors": b.factors,
        }
        for b in breakdowns
    ]


def _serialize_strategies(recommendations: List[StrategyRecommendation]) -> List[Dict]:
    """Serialize strategy assignments."""
    return [
        {
            "app_id": r.app_id,
            "strategy": r.migration_strategy,
            "risk_level": r.risk_level,
        }
        for r in recommendations
    ]


def _serialize_timeline(timeline: Optional[ProjectTimeline]) -> Optional[Dict]:
    """Serialize project timeline."""
    if timeline is None:
        return None
    return {
        "total_waves": timeline.total_waves,
        "total_expected_days": round(timeline.total_expected_days, 1),
        "total_min_days": round(timeline.total_min_days, 1),
        "total_max_days": round(timeline.total_max_days, 1),
        "wave_durations": [
            {
                "wave": w.wave_number,
                "expected_days": round(w.expected_days, 1),
                "start_day": round(w.start_day, 1),
                "end_day": round(w.end_day, 1),
            }
            for w in timeline.wave_estimates
        ],
    }


# ---------------------------------------------------------------------------
# Output JSON Schema
# ---------------------------------------------------------------------------

OUTPUT_SCHEMA = {
    "executive_summary": "string — 2-3 sentence overview of the migration plan",
    "wave_explanations": [
        {
            "wave_number": "int",
            "title": "string — short wave title",
            "explanation": "string — why these apps are grouped together",
            "parallel_apps": ["app_id list"],
            "estimated_duration": "string — e.g. '3-4 days'",
            "key_considerations": ["string list"],
        }
    ],
    "risk_analysis": {
        "critical_risks": [
            {
                "app_id": "string",
                "risk_level": "string",
                "description": "string — why this app is risky",
                "mitigation_steps": ["string list — concrete actions"],
            }
        ],
        "overall_risk_assessment": "string — portfolio-level risk summary",
    },
    "strategy_justifications": [
        {
            "app_id": "string",
            "strategy": "string",
            "justification": "string — why this strategy was chosen",
            "cloud_services": ["string — specific AWS services to use"],
        }
    ],
    "strategic_insights": [
        {
            "insight": "string — actionable recommendation",
            "impact": "High/Medium/Low",
            "category": "string — e.g. 'Cost', 'Performance', 'Security'",
        }
    ],
    "migration_roadmap": {
        "recommended_start": "string — when to begin",
        "total_estimated_duration": "string — overall timeline",
        "critical_path": ["app_id list — longest dependency chain"],
        "quick_wins": ["app_id list — easy migrations to build momentum"],
    },
}


# ===========================================================================
# Core Prompt Builder
# ===========================================================================

def build_roadmap_prompt(
    apps: List[ApplicationRecord],
    wave_result: WaveAnalysisResult,
    risk_breakdowns: List[RiskBreakdown],
    strategy_recommendations: List[StrategyRecommendation],
    *,
    timeline: Optional[ProjectTimeline] = None,
    model_id: str = DEFAULT_MODEL_ID,
    max_tokens: int = 4096,
    temperature: float = 0.3,
    additional_context: Optional[str] = None,
) -> PromptPayload:
    """
    Build a structured prompt for Bedrock Claude to generate a migration roadmap.

    Parameters
    ----------
    apps : list[ApplicationRecord]
        Scored and strategy-assigned application records.
    wave_result : WaveAnalysisResult
        Wave assignments from topological sort.
    risk_breakdowns : list[RiskBreakdown]
        Per-app risk breakdowns.
    strategy_recommendations : list[StrategyRecommendation]
        Per-app strategy assignments.
    timeline : ProjectTimeline, optional
        Time estimates for waves and project.
    model_id : str
        Bedrock model identifier.
    max_tokens : int
        Maximum response tokens.
    temperature : float
        Sampling temperature (lower = more deterministic).
    additional_context : str, optional
        Extra context to include (e.g. compliance requirements).

    Returns
    -------
    PromptPayload
        Ready-to-send prompt with system/user separation.

    Example
    -------
    >>> payload = build_roadmap_prompt(apps, waves, risks, strategies)
    >>> bedrock_body = payload.to_bedrock_messages()
    """
    # ---- Build data sections -----------------------------------------------
    apps_data = _serialize_apps(apps)
    waves_data = _serialize_waves(wave_result)
    risks_data = _serialize_risks(risk_breakdowns)
    strategies_data = _serialize_strategies(strategy_recommendations)
    timeline_data = _serialize_timeline(timeline)

    # ---- Construct user prompt --------------------------------------------
    sections = []

    sections.append("# Cloud Migration Analysis Request\n")
    sections.append(
        "Analyze the following application portfolio and generate a strategic "
        "migration roadmap. All data has been pre-computed using dependency graph "
        "analysis (NetworkX DAG), topological wave sorting, and risk scoring.\n"
    )

    # Application Inventory
    sections.append("## Application Inventory\n")
    sections.append(f"```json\n{json.dumps(apps_data, indent=2)}\n```\n")

    # Wave Assignments
    sections.append("## Migration Waves (Topological Sort)\n")
    sections.append(
        "Apps within each wave can migrate in parallel. "
        "Waves must execute sequentially (Wave 0 before Wave 1, etc.).\n"
    )
    sections.append(f"```json\n{json.dumps(waves_data, indent=2)}\n```\n")

    # Risk Analysis
    sections.append("## Risk Scores\n")
    sections.append(
        "Scoring: criticality (high/critical=+2), data_size (≥100GB=+2), "
        "dependencies (≥3=+2), complexity (complex/very_complex=+2). "
        "Tiers: 0-2=Low, 3-5=Medium, 6-8=High.\n"
    )
    sections.append(f"```json\n{json.dumps(risks_data, indent=2)}\n```\n")

    # Strategy Assignments
    sections.append("## Assigned Strategies\n")
    sections.append(
        "Mapping: Low risk→Rehost, Medium risk→Replatform, High risk→Refactor.\n"
    )
    sections.append(f"```json\n{json.dumps(strategies_data, indent=2)}\n```\n")

    # Timeline (optional)
    if timeline_data:
        sections.append("## Time Estimates\n")
        sections.append(f"```json\n{json.dumps(timeline_data, indent=2)}\n```\n")

    # Additional Context
    if additional_context:
        sections.append("## Additional Context\n")
        sections.append(f"{additional_context}\n")

    # Instructions
    sections.append("## Instructions\n")
    sections.append(
        "Based on the data above, generate a comprehensive migration roadmap. "
        "Your response must:\n\n"
        "1. **Explain wave grouping**: Why are these apps grouped together? "
        "What dependency relationships drive the ordering?\n"
        "2. **Highlight risks**: Identify the most critical risks in this portfolio. "
        "Provide concrete mitigation steps for each.\n"
        "3. **Justify strategies**: For each app, explain why the assigned strategy "
        "(Rehost/Replatform/Refactor) is appropriate. Recommend specific AWS services.\n"
        "4. **Provide strategic insights**: Offer actionable recommendations for "
        "cost optimization, performance, security, and organizational readiness.\n\n"
    )

    # Output Format
    sections.append("## Required Output Format\n")
    sections.append(
        "Respond with ONLY a valid JSON object matching this schema:\n\n"
        f"```json\n{json.dumps(OUTPUT_SCHEMA, indent=2)}\n```\n"
    )

    user_prompt = "\n".join(sections)

    payload = PromptPayload(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        model_id=model_id,
        max_tokens=max_tokens,
        temperature=temperature,
    )

    logger.info(
        f"build_roadmap_prompt: {len(apps)} apps, {len(waves_data)} waves, "
        f"prompt length={len(user_prompt)} chars"
    )

    return payload
