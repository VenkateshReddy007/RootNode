"""
RootNode - AWS Lambda Handler (Step 9)
========================================
Main entry point for the RootNode backend. Orchestrates the full
migration planning pipeline:
  1. Parse CSV/JSON input
  2. Build dependency DAG
  3. Generate migration waves
  4. Compute risk scores
  5. Assign migration strategies
  6. Estimate project timeline
  7. Generate and send prompt to Bedrock Claude
  8. Return structured payload to frontend

Optimized for AWS Lambda:
  • Proper status codes and CORS headers
  • Graceful error handling (400 vs 500)
  • Integrates seamlessly with API Gateway
"""

import json
import logging
import os
import traceback
from datetime import date
from typing import Any, Dict

from backend.parsers.csv_parser import parse_input
from backend.graph.dag_builder import build_dependency_graph, graph_to_dict
from backend.graph.wave_analyzer import topological_sort_waves
from backend.scoring.risk_engine import score_waves
from backend.scoring.strategy_engine import assign_all_strategies, get_strategy_summary
from backend.scoring.time_estimator import estimate_wave_time
from backend.genai.prompt_builder import build_roadmap_prompt
from backend.genai.bedrock_client import invoke_claude

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_response(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    """Format response for API Gateway proxy integration."""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",  # For React frontend
            "Access-Control-Allow-Credentials": True,
        },
        "body": json.dumps(body),
    }


def _extract_input_data(event: Dict[str, Any]) -> str:
    """Safely extract input payload string from API Gateway event."""
    if "body" in event:
        # API Gateway HTTP API or REST API
        body = event["body"]
        if event.get("isBase64Encoded", False):
            import base64
            return base64.b64decode(body).decode("utf-8")
        return body
    
    # Direct invocation (e.g. testing)
    if isinstance(event, dict) and "data" in event:
        return event["data"]
    
    if not event:
        return ""
        
    # Raw JSON/dict fallback
    if isinstance(event, (dict, list)):
        if not event:
            return ""
        return json.dumps(event)
        
    return str(event)


# ===========================================================================
# Lambda Handler
# ===========================================================================

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda entry point.
    
    Expected event payload:
    {
       "body": "<csv or json string>"
    }
    """
    try:
        logger.info("Lambda invocation started.")
        
        # ---- 0. Extract Input ----------------------------------------------
        raw_data = _extract_input_data(event)
        if not raw_data or not raw_data.strip():
            return _build_response(400, {"error": "Empty input data provided."})
            
        strict_mode = os.environ.get("STRICT_MODE", "false").lower() == "true"

        # ---- 1. Parse Input ------------------------------------------------
        logger.info("Step 1: Parsing input...")
        parse_result = parse_input(raw_data, strict=strict_mode)
        
        if not parse_result.success:
            return _build_response(400, {
                "error": "Validation failed during parsing.",
                "details": parse_result.errors
            })
            
        apps = parse_result.applications
        if not apps:
            return _build_response(400, {
                "error": "No valid applications found in input data.",
                "details": parse_result.errors
            })

        # ---- 2. Build Graph ------------------------------------------------
        logger.info("Step 2: Building dependency DAG...")
        try:
            G = build_dependency_graph(apps, strict=strict_mode)
        except ValueError as e:
            return _build_response(400, {"error": str(e)})

        # ---- 3. Generate Waves ---------------------------------------------
        logger.info("Step 3: Generating waves...")
        wave_result = topological_sort_waves(G)
        
        if not wave_result.is_valid:
            return _build_response(400, {
                "error": "Cycle detected. Cannot generate migration waves.",
                "stuck_apps": wave_result.unresolved_apps
            })

        # ---- 4. Compute Risk & Assign Strategy -----------------------------
        logger.info("Steps 4-5: Computing risk and strategies...")
        # assign_all_strategies internally calls score_risk for each app
        scored_apps, strategies = assign_all_strategies(apps)
        
        # Also map risk scores into the wave items for completeness
        wave_result, breakdown_map = score_waves(wave_result)

        # ---- 6. Estimate Timeline ------------------------------------------
        logger.info("Step 6: Estimating timeline...")
        timeline = estimate_wave_time(wave_result, scored_apps, start_date=date.today())

        # ---- 7. Bedrock Prompt ---------------------------------------------
        logger.info("Step 7: Executing Bedrock AI analysis...")
        
        # We allow skipping AI analysis to save cost during dev/test
        skip_ai = os.environ.get("SKIP_AI", "false").lower() == "true"
        ai_response = None
        
        if not skip_ai:
            prompt_payload = build_roadmap_prompt(
                apps=scored_apps,
                wave_result=wave_result,
                risk_breakdowns=list(breakdown_map.values()),
                strategy_recommendations=strategies,
                timeline=timeline,
            )
            try:
                ai_response = invoke_claude(prompt_payload)
            except Exception as e:
                logger.error(f"Bedrock invocation failed: {e}")
                # We do not fail the whole request, we return computed backend 
                # data along with a partial AI failure payload.
                ai_response = {"error": "AI analysis failed.", "details": str(e)}

        # ---- 8. Return Aggregated JSON -------------------------------------
        logger.info("Step 8: Constructing final response...")
        
        # Serialize the graph safely
        graph_data = graph_to_dict(G)
        
        response_data = {
            "metadata": {
                "total_apps": parse_result.valid_count,
                "total_waves": wave_result.total_waves,
                "is_dag": wave_result.is_valid,
            },
            "strategy_summary": get_strategy_summary(strategies),
            "timeline": timeline.to_dict(),
            "graph": graph_data,
            "ai_roadmap": ai_response,
        }

        return _build_response(200, response_data)

    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {e}")
        return _build_response(400, {"error": "Invalid JSON format in request.", "details": str(e)})
        
    except ValueError as e:
        logger.error(f"Validation or processing error: {e}")
        return _build_response(400, {"error": "Validation failed.", "details": str(e)})
        
    except Exception as e:
        logger.error(f"Unhandled exception: {traceback.format_exc()}")
        return _build_response(500, {
            "error": "Internal server error during backend orchestration.",
            "details": str(e)
        })
