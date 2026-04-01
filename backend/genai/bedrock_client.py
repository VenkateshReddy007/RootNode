"""
RootNode - Bedrock Claude Client (Step 8)
===========================================
Executes the prompt against AWS Bedrock using Claude 4.6 Sonnet
in the ap-south-2 (Hyderabad) region.

Optimized for AWS Lambda:
  • Lazy boto3 client initialization (cold start optimization)
  • Robust error handling & JSON parsing
  • Designed to use default IAM execution role/credentials
"""

import json
import logging
import os
from typing import Any, Dict, Optional, Union

from backend.genai.prompt_builder import PromptPayload

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

AWS_REGION = os.environ.get("AWS_REGION", "ap-south-2")
# Sonnet 4.6 ID format in Bedrock (using standard naming convention)
DEFAULT_MODEL_ID = os.environ.get(
    "BEDROCK_MODEL_ID", 
    "anthropic.claude-sonnet-4-6-20250630-v2:0" # Approximate Bedrock ARN format for future models
)

# Global client cache for Lambda warm starts
_bedrock_client = None

def _get_client():
    """Lazy initialize the boto3 client to save on Lambda cold starts."""
    global _bedrock_client
    if _bedrock_client is None:
        import boto3
        _bedrock_client = boto3.client("bedrock-runtime", region_name=AWS_REGION)
    return _bedrock_client


# ===========================================================================
# Core Invocation
# ===========================================================================

def invoke_claude(
    prompt_input: Union[str, PromptPayload],
    *,
    model_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Call Bedrock Claude and return the structured JSON roadmap.
    
    Parameters
    ----------
    prompt_input : str | PromptPayload
        The prompt to send. If a string is provided, it is wrapped in 
        a standard user message format. If a PromptPayload (from Step 7) 
        is provided, it uses the exact formatted system/user separation.
    model_id : str, optional
        Override the default model ID.
        
    Returns
    -------
    dict
        Parsed JSON response from the model.
        
    Raises
    ------
    ValueError
        If the model fails to return valid JSON.
    RuntimeError
        If the Bedrock API call fails.
    """
    client = _get_client()
    target_model_id = model_id or DEFAULT_MODEL_ID
    
    # 1. Prepare Request Body
    if isinstance(prompt_input, PromptPayload):
        body = prompt_input.to_bedrock_messages()
    else:
        # Fallback for raw string prompts
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 4096,
            "temperature": 0.3,
            "messages": [
                {
                    "role": "user",
                    "content": prompt_input
                }
            ]
        }
        
    # 2. Invoke Model
    try:
        logger.info(f"Invoking Bedrock model: {target_model_id} in {AWS_REGION}")
        response = client.invoke_model(
            modelId=target_model_id,
            body=json.dumps(body),
            accept="application/json",
            contentType="application/json"
        )
    except Exception as e:
        logger.error(f"Bedrock invocation failed: {e}")
        raise RuntimeError(f"AWS Bedrock error: {e}") from e

    # 3. Process Response
    try:
        response_body = json.loads(response["body"].read())
        
        # Extract the text content from Claude's response format
        # Bedrock Anthropic Messages API format: response_body['content'][0]['text']
        raw_text = response_body.get("content", [])[0].get("text", "")
        
    except (json.JSONDecodeError, KeyError, IndexError) as e:
        logger.error(f"Failed to parse Bedrock response envelope: {e}")
        raise RuntimeError("Invalid response format from Bedrock API.") from e

    # 4. Extract and Parse Inner JSON
    # Claude sometimes wraps JSON in markdown blocks (```json ... ```)
    cleaned_text = raw_text.strip()
    if cleaned_text.startswith("```json"):
        cleaned_text = cleaned_text[7:]
    if cleaned_text.endswith("```"):
        cleaned_text = cleaned_text[:-3]
        
    cleaned_text = cleaned_text.strip()
    
    try:
        return json.loads(cleaned_text)
    except json.JSONDecodeError as e:
        logger.error(f"Model failed to return valid JSON. Raw output: {raw_text[:200]}...")
        raise ValueError(f"AI response is not valid JSON: {e}") from e

