"""
RootNode - Step 9 Test Suite: Lambda Orchestration
===================================================
Covers: e2e API Gateway proxy event testing, error mapping,
        and AI skipping behavior.
"""

import json
import os
import sys
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.handler import lambda_handler


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

CSV_PAYLOAD = """app_id,name,dependencies,criticality,data_size,business_priority,complexity
APP001,Auth,,critical,100.0,1,complex
APP002,Payment,APP001,high,50.0,2,moderate
"""

INVALID_CSV = """app_id,name,dependencies,criticality,data_size,business_priority,complexity
APP001,Test,,super_critical,10.0,1,simple
"""

CYCLE_CSV = """app_id,name,dependencies
A,AppA,C
B,AppB,A
C,AppC,B
"""


def _make_event(body_str: str, b64=False) -> dict:
    if b64:
        import base64
        body_str = base64.b64encode(body_str.encode("utf-8")).decode("utf-8")
        
    return {
        "resource": "/plan",
        "path": "/plan",
        "httpMethod": "POST",
        "isBase64Encoded": b64,
        "body": body_str
    }


# ===========================================================================
# End-to-End Execution
# ===========================================================================

@patch("backend.handler.invoke_claude")
class TestOrchestrationPipeline:
    """Verifies lambda_handler invokes all steps and formats response."""

    def test_successful_e2e_run(self, mock_invoke):
        mock_invoke.return_value = {"executive_summary": "Test Roadmap"}
        
        event = _make_event(CSV_PAYLOAD)
        res = lambda_handler(event, None)
        
        assert res["statusCode"] == 200
        assert "application/json" in res["headers"]["Content-Type"]
        
        body = json.loads(res["body"])
        
        # Ensure core keys exist
        assert "metadata" in body
        assert "strategy_summary" in body
        assert "timeline" in body
        assert "graph" in body
        assert "ai_roadmap" in body
        
        # Spot check computations
        assert body["metadata"]["total_apps"] == 2
        assert body["metadata"]["total_waves"] == 2
        assert body["ai_roadmap"]["executive_summary"] == "Test Roadmap"
        
        mock_invoke.assert_called_once()

    def test_skip_ai_env_var(self, mock_invoke):
        os.environ["SKIP_AI"] = "true"
        try:
            event = _make_event(CSV_PAYLOAD)
            res = lambda_handler(event, None)
            
            assert res["statusCode"] == 200
            body = json.loads(res["body"])
            assert body["ai_roadmap"] is None
            
            mock_invoke.assert_not_called()
        finally:
            del os.environ["SKIP_AI"]

    def test_ai_graceful_failure(self, mock_invoke):
        mock_invoke.side_effect = Exception("Bedrock timeout")
        
        event = _make_event(CSV_PAYLOAD)
        res = lambda_handler(event, None)
        
        assert res["statusCode"] == 200
        body = json.loads(res["body"])
        assert "error" in body["ai_roadmap"]
        assert "Bedrock timeout" in body["ai_roadmap"]["details"]


# ===========================================================================
# Event Parsing & Errors
# ===========================================================================

class TestErrorHandling:
    """Verifies edge cases and malformed inputs."""

    def test_empty_event(self):
        res = lambda_handler({}, None)
        assert res["statusCode"] == 400
        body = json.loads(res["body"])
        assert "Empty input data" in body["error"]

    def test_base64_encoded_body(self):
        event = _make_event("app_id,name\nA,Test\n", b64=True)
        os.environ["SKIP_AI"] = "true"  # Don't invoke bedrock
        try:
            res = lambda_handler(event, None)
            assert res["statusCode"] == 200
        finally:
            del os.environ["SKIP_AI"]

    def test_parse_failure_400(self):
        os.environ["STRICT_MODE"] = "true"
        try:
            event = _make_event(INVALID_CSV)
            res = lambda_handler(event, None)
            
            assert res["statusCode"] == 400
            body = json.loads(res["body"])
            assert "Validation failed" in body["error"]
            assert len(body["details"]) > 0
        finally:
            del os.environ["STRICT_MODE"]

    def test_cycle_graph_validation_400(self):
        event = _make_event(CYCLE_CSV)
        res = lambda_handler(event, None)
        
        assert res["statusCode"] == 400
        body = json.loads(res["body"])
        assert "Cycle detected" in body["error"]

    def test_raw_dict_event(self):
        # E.g. direct lambda invoke rather than APIGW proxy
        event = {"data": "app_id,name\nA,Test\n"}
        os.environ["SKIP_AI"] = "true"
        try:
            res = lambda_handler(event, None)
            assert res["statusCode"] == 200
        finally:
            del os.environ["SKIP_AI"]


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
