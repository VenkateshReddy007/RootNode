"""
RootNode - Step 7 Test Suite: Bedrock Prompt Builder
======================================================
Covers: prompt payload generation, schema compliance, JSON validation,
        and Bedrock Messages API formatting.
"""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.models.application import ApplicationRecord
from backend.scoring.risk_engine import RiskBreakdown
from backend.scoring.strategy_engine import StrategyRecommendation
from backend.graph.wave_analyzer import WaveAnalysisResult, Wave, WaveItem
from backend.scoring.time_estimator import ProjectTimeline, WaveTimeEstimate, AppTimeEstimate
from backend.genai.prompt_builder import build_roadmap_prompt, OUTPUT_SCHEMA


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_dummy_data():
    app1 = ApplicationRecord(
        app_id="APP1", name="App 1", criticality="high",
        data_size=100.0, complexity="complex", business_priority=1,
        dependencies=[], risk_score=75.0, migration_strategy="Refactor"
    )
    app2 = ApplicationRecord(
        app_id="APP2", name="App 2", criticality="low",
        data_size=10.0, complexity="simple", business_priority=3,
        dependencies=["APP1"], risk_score=10.0, migration_strategy="Rehost"
    )

    wave1 = Wave(wave_number=0, items=[WaveItem(
        app_id="APP1", name="App 1", criticality="high",
        complexity="complex", data_size=100.0, business_priority=1,
        dependencies=[]
    )])
    wave2 = Wave(wave_number=1, items=[WaveItem(
        app_id="APP2", name="App 2", criticality="low",
        complexity="simple", data_size=10.0, business_priority=3,
        dependencies=["APP1"]
    )])
    waves = WaveAnalysisResult(waves=[wave1, wave2], total_waves=2, total_apps=2)

    risk1 = RiskBreakdown("APP1", 2, 2, 0, 2, 6, 75.0, "High")
    risk2 = RiskBreakdown("APP2", 0, 0, 0, 0, 0, 0.0, "Low")
    risks = [risk1, risk2]

    strat1 = StrategyRecommendation("APP1", "High", 75.0, "Refactor", "Test")
    strat2 = StrategyRecommendation("APP2", "Low", 0.0, "Rehost", "Test")
    strats = [strat1, strat2]

    return [app1, app2], waves, risks, strats


# ===========================================================================
# Prompt Generation Tests
# ===========================================================================

class TestPromptGeneration:
    """Core prompt building functionality."""

    def test_builds_valid_payload(self):
        apps, waves, risks, strats = _make_dummy_data()
        payload = build_roadmap_prompt(apps, waves, risks, strats)
        
        assert payload.system_prompt
        assert payload.user_prompt
        assert "APP1" in payload.user_prompt
        assert "APP2" in payload.user_prompt
        assert "Refactor" in payload.user_prompt

    def test_includes_output_schema(self):
        apps, waves, risks, strats = _make_dummy_data()
        payload = build_roadmap_prompt(apps, waves, risks, strats)
        
        # Verify JSON schema is embedded
        assert "executive_summary" in payload.user_prompt
        assert "wave_explanations" in payload.user_prompt

    def test_bedrock_format(self):
        apps, waves, risks, strats = _make_dummy_data()
        payload = build_roadmap_prompt(apps, waves, risks, strats)
        msg_format = payload.to_bedrock_messages()
        
        assert msg_format["anthropic_version"] == "bedrock-2023-05-31"
        assert msg_format["system"] == payload.system_prompt
        assert len(msg_format["messages"]) == 1
        assert msg_format["messages"][0]["role"] == "user"
        assert msg_format["messages"][0]["content"] == payload.user_prompt

    def test_with_timeline(self):
        apps, waves, risks, strats = _make_dummy_data()
        
        timeline = ProjectTimeline(
            total_waves=2,
            total_apps=2,
            total_expected_days=5.0,
            wave_estimates=[
                WaveTimeEstimate(wave_number=0, min_days=4.0, max_days=5.0, expected_days=4.5),
                WaveTimeEstimate(wave_number=1, min_days=1.0, max_days=2.0, expected_days=1.5),
            ]
        )
        
        payload = build_roadmap_prompt(apps, waves, risks, strats, timeline=timeline)
        assert "total_expected_days" in payload.user_prompt
        assert "5.0" in payload.user_prompt

    def test_additional_context(self):
        apps, waves, risks, strats = _make_dummy_data()
        ctx = "MUST COMPLY WITH HIPAA."
        payload = build_roadmap_prompt(apps, waves, risks, strats, additional_context=ctx)
        assert "MUST COMPLY WITH HIPAA." in payload.user_prompt


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
