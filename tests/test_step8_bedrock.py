"""
RootNode - Step 8 Test Suite: Bedrock Claude Client
=====================================================
Covers: boto3 client initialization, payload extraction,
        JSON parsing (including markdown wrappers), and error handling.
"""

import json
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.genai.prompt_builder import PromptPayload
from backend.genai.bedrock_client import invoke_claude, AWS_REGION


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_bedrock_response(text_content: str):
    """Mocks the nested dictionary structure returned by boto3 invoke_model."""
    body = json.dumps({
        "type": "message",
        "role": "assistant",
        "content": [{"type": "text", "text": text_content}],
    }).encode("utf-8")
    
    mock_body = MagicMock()
    mock_body.read.return_value = body
    
    return {"body": mock_body}


# ===========================================================================
# Invocation & Payload Handling
# ===========================================================================

@patch("boto3.client")
class TestBedrockInvocation:
    """Core invocation handling."""

    def test_raw_string_prompt(self, mock_boto):
        mock_client = MagicMock()
        mock_boto.return_value = mock_client
        mock_client.invoke_model.return_value = _mock_bedrock_response('{"status": "ok"}')

        # Requires clearing the module-level client cache for isolated test
        import backend.genai.bedrock_client
        backend.genai.bedrock_client._bedrock_client = None

        result = invoke_claude("Analyze this architecture.")
        
        assert result == {"status": "ok"}
        
        # Verify call params
        mock_client.invoke_model.assert_called_once()
        call_kwargs = mock_client.invoke_model.call_args[1]
        assert call_kwargs["modelId"].startswith("anthropic.claude")
        
        # Verify string was wrapped in Messages format
        body = json.loads(call_kwargs["body"])
        assert body["messages"][0]["content"] == "Analyze this architecture."

    def test_prompt_payload_object(self, mock_boto):
        mock_client = MagicMock()
        mock_boto.return_value = mock_client
        mock_client.invoke_model.return_value = _mock_bedrock_response('{"plan": "good"}')

        import backend.genai.bedrock_client
        backend.genai.bedrock_client._bedrock_client = None

        payload = PromptPayload("You are an AI.", "Here is the data.")
        result = invoke_claude(payload)
        
        assert result == {"plan": "good"}
        
        call_kwargs = mock_client.invoke_model.call_args[1]
        body = json.loads(call_kwargs["body"])
        assert body["system"] == "You are an AI."
        assert body["messages"][0]["content"] == "Here is the data."


# ===========================================================================
# JSON Parsing & Markdown Stripping
# ===========================================================================

@patch("boto3.client")
class TestJSONParsing:
    """Verifies that the LLM response is safely parsed to dict."""

    def test_clean_json(self, mock_boto):
        mock_client = MagicMock()
        mock_boto.return_value = mock_client
        mock_client.invoke_model.return_value = _mock_bedrock_response(
            '{\n  "executive_summary": "Test"\n}'
        )

        import backend.genai.bedrock_client
        backend.genai.bedrock_client._bedrock_client = None

        res = invoke_claude("test prompt")
        assert res["executive_summary"] == "Test"

    def test_markdown_wrapped_json(self, mock_boto):
        """Claude often wraps JSON in ```json blocks."""
        mock_client = MagicMock()
        mock_boto.return_value = mock_client
        
        markdown_text = "```json\n{\"foo\": \"bar\"}\n```"
        mock_client.invoke_model.return_value = _mock_bedrock_response(markdown_text)

        import backend.genai.bedrock_client
        backend.genai.bedrock_client._bedrock_client = None

        res = invoke_claude("test prompt")
        assert res["foo"] == "bar"

    def test_malformed_json_raises(self, mock_boto):
        mock_client = MagicMock()
        mock_boto.return_value = mock_client
        
        bad_json = 'This is just text, not JSON.'
        mock_client.invoke_model.return_value = _mock_bedrock_response(bad_json)

        import backend.genai.bedrock_client
        backend.genai.bedrock_client._bedrock_client = None

        with pytest.raises(ValueError, match="not valid JSON"):
            invoke_claude("test prompt")


# ===========================================================================
# Error Handling
# ===========================================================================

@patch("boto3.client")
class TestErrorHandling:
    """Verifies bedrock API failures are surfaced correctly."""
    
    def test_bedrock_exception(self, mock_boto):
        mock_client = MagicMock()
        mock_boto.return_value = mock_client
        
        # Simulate AWS SDK throwing an exception (e.g., throttling or auth)
        mock_client.invoke_model.side_effect = Exception("ThrottlingException")

        import backend.genai.bedrock_client
        backend.genai.bedrock_client._bedrock_client = None

        with pytest.raises(RuntimeError, match="AWS Bedrock error"):
            invoke_claude("test prompt")


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
