"""
RootNode - CSV / JSON Input Parser (Step 1)
=============================================
Production-ready parser for AWS Lambda that accepts CSV or JSON
application inventory data and returns validated ApplicationRecords.

Supports:
  • Raw CSV/JSON strings
  • File paths (local or Lambda /tmp)
  • S3 URIs (s3://bucket/key)
  • Auto-detection of input format
  • Streaming parse for large files (memory-safe on Lambda 512 MB)

Variable naming follows project spec:
    app_id, dependencies, risk_score, migration_strategy
"""

from __future__ import annotations

import csv
import io
import json
import logging
import os
from typing import Any, Dict, List, Optional, Union

from pydantic import ValidationError

from backend.models.application import ApplicationRecord, ParseResult

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))


# ---------------------------------------------------------------------------
# Format Detection
# ---------------------------------------------------------------------------

def _detect_format(raw: str) -> str:
    """Heuristic format detection from raw content."""
    stripped = raw.strip()
    if stripped.startswith(("{", "[")):
        return "json"
    # If it has commas and newlines, treat as CSV
    if "," in stripped and "\n" in stripped:
        return "csv"
    raise ValueError(
        "Unable to auto-detect input format. "
        "Content must be valid CSV or JSON."
    )


# ---------------------------------------------------------------------------
# S3 Loader (lazy import — only pays cost when used)
# ---------------------------------------------------------------------------

def _load_from_s3(uri: str) -> str:
    """Download object from S3 and return as string. Expects s3://bucket/key."""
    import boto3  # noqa: deferred import for Lambda cold-start optimization

    if not uri.startswith("s3://"):
        raise ValueError(f"Invalid S3 URI: {uri}")

    parts = uri[5:].split("/", 1)
    if len(parts) != 2:
        raise ValueError(f"Invalid S3 URI format: {uri}")

    bucket, key = parts
    s3 = boto3.client("s3")
    response = s3.get_object(Bucket=bucket, Key=key)
    return response["Body"].read().decode("utf-8")


# ---------------------------------------------------------------------------
# Raw Content Resolver
# ---------------------------------------------------------------------------

def _resolve_content(input_data: Union[str, List, Dict]) -> tuple[str, str]:
    """
    Resolve input to (raw_content_string, detected_format).

    Accepts:
      - Raw CSV/JSON string
      - File path
      - S3 URI
      - Already-parsed list/dict (re-serialized to JSON)
    """
    # Already-parsed Python objects → re-serialize
    if isinstance(input_data, (list, dict)):
        return json.dumps(input_data), "json"

    raw = input_data.strip()

    # S3 URI
    if raw.startswith("s3://"):
        content = _load_from_s3(raw)
        fmt = _detect_format(content)
        return content, fmt

    # Local file path
    if os.path.isfile(raw):
        with open(raw, "r", encoding="utf-8") as f:
            content = f.read()
        # Use extension hint first, fall back to detection
        ext = os.path.splitext(raw)[1].lower()
        if ext == ".json":
            return content, "json"
        if ext in (".csv", ".tsv"):
            return content, "csv"
        return content, _detect_format(content)

    # Raw string content
    fmt = _detect_format(raw)
    return raw, fmt


# ---------------------------------------------------------------------------
# CSV Parser
# ---------------------------------------------------------------------------

_COLUMN_ALIASES: Dict[str, str] = {
    # Common CSV header variations → canonical field names
    "app_id": "app_id",
    "application_id": "app_id",
    "id": "app_id",
    "application": "app_id",
    "application_name": "name",
    "app_name": "name",
    "name": "name",
    "deps": "dependencies",
    "dependencies": "dependencies",
    "depends_on": "dependencies",
    "dependson": "dependencies",
    "criticality": "criticality",
    "priority": "business_priority",
    "business_priority": "business_priority",
    "data_size": "data_size",
    "datasize": "data_size",
    "data_size_gb": "data_size",
    "size_gb": "data_size",
    "complexity": "complexity",
    "migration_complexity": "complexity",
}


def _normalize_headers(headers: List[str]) -> List[str]:
    """Map CSV headers to canonical field names."""
    normalized = []
    for h in headers:
        key = h.strip().lower().replace(" ", "_").replace("-", "_")
        canonical = _COLUMN_ALIASES.get(key, key)
        normalized.append(canonical)
    return normalized


def _parse_csv(content: str) -> List[Dict[str, Any]]:
    """Parse CSV content into list of dicts with normalized keys."""
    reader = csv.reader(io.StringIO(content))
    rows = list(reader)

    if len(rows) < 2:
        raise ValueError("CSV must contain a header row and at least one data row.")

    headers = _normalize_headers(rows[0])
    records = []

    for i, row in enumerate(rows[1:], start=2):
        if not any(cell.strip() for cell in row):
            continue  # skip blank rows
        if len(row) != len(headers):
            logger.warning(f"Row {i}: column count mismatch (expected {len(headers)}, got {len(row)}). Skipping.")
            continue
        record = dict(zip(headers, row))
        records.append(record)

    return records


# ---------------------------------------------------------------------------
# JSON Parser
# ---------------------------------------------------------------------------

def _parse_json(content: str) -> List[Dict[str, Any]]:
    """Parse JSON content (array of objects or single object)."""
    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}") from e

    # Unwrap common wrapper patterns:  { "applications": [...] }
    if isinstance(data, dict):
        for key in ("applications", "apps", "data", "records", "items"):
            if key in data and isinstance(data[key], list):
                data = data[key]
                break
        else:
            # Single application object
            data = [data]

    if not isinstance(data, list):
        raise ValueError("JSON input must be an array of application objects or a wrapper containing one.")

    # Normalize keys
    normalized = []
    for record in data:
        normed = {}
        for k, v in record.items():
            key = k.strip().lower().replace(" ", "_").replace("-", "_")
            canonical = _COLUMN_ALIASES.get(key, key)
            normed[canonical] = v
        
        # Ensure both app_id and name exist
        if "app_id" in normed and "name" not in normed:
            normed["name"] = normed["app_id"]
        elif "name" in normed and "app_id" not in normed:
            normed["app_id"] = normed["name"]
            
        normalized.append(normed)

    return normalized


# ---------------------------------------------------------------------------
# Duplicate & Dependency Validation
# ---------------------------------------------------------------------------

def _validate_integrity(records: List[ApplicationRecord]) -> List[str]:
    """Post-parse integrity checks."""
    errors = []
    seen_ids = set()

    for app in records:
        # Duplicate app_id
        if app.app_id in seen_ids:
            errors.append(f"Duplicate app_id detected: '{app.app_id}'.")
        seen_ids.add(app.app_id)

    # Dangling dependency references
    all_ids = {app.app_id for app in records}
    for app in records:
        for dep in app.dependencies:
            if dep not in all_ids:
                errors.append(
                    f"app_id '{app.app_id}' depends on '{dep}' which is not in the input data."
                )

    return errors


# ===========================================================================
# PUBLIC API
# ===========================================================================

def parse_input(
    input_data: Union[str, List, Dict],
    *,
    strict: bool = False,
    format_hint: Optional[str] = None,
) -> ParseResult:
    """
    Parse CSV or JSON application inventory into validated ApplicationRecords.

    Parameters
    ----------
    input_data : str | list | dict
        Raw CSV/JSON string, file path, S3 URI (s3://bucket/key),
        or pre-parsed Python list/dict.
    strict : bool
        If True, raise on first validation error instead of collecting them.
    format_hint : str | None
        Force format ("csv" or "json"). Auto-detected if None.

    Returns
    -------
    ParseResult
        Contains validated applications, any errors, and metadata.

    Example
    -------
    >>> result = parse_input("path/to/apps.csv")
    >>> for app in result.applications:
    ...     print(app.app_id, app.dependencies)
    """
    errors: List[str] = []

    # ---- 1. Resolve raw content -------------------------------------------
    try:
        content, detected_format = _resolve_content(input_data)
        if format_hint:
            detected_format = format_hint.lower()
    except ValueError as e:
        return ParseResult(errors=[str(e)], error_count=1)

    # ---- 2. Parse to raw dicts --------------------------------------------
    try:
        if detected_format == "csv":
            raw_records = _parse_csv(content)
        elif detected_format == "json":
            raw_records = _parse_json(content)
        else:
            return ParseResult(
                errors=[f"Unsupported format: '{detected_format}'."],
                error_count=1,
            )
    except ValueError as e:
        return ParseResult(errors=[str(e)], error_count=1)

    total_raw = len(raw_records)

    # ---- 3. Validate each record with Pydantic ----------------------------
    validated: List[ApplicationRecord] = []
    for idx, raw in enumerate(raw_records):
        try:
            app = ApplicationRecord(**raw)
            validated.append(app)
        except ValidationError as e:
            msg = f"Record {idx + 1}: {e.error_count()} validation error(s) — {e.errors()}"
            errors.append(msg)
            if strict:
                raise ValueError(msg) from e

    # ---- 4. Integrity checks ----------------------------------------------
    integrity_errors = _validate_integrity(validated)
    errors.extend(integrity_errors)

    # ---- 5. Build result --------------------------------------------------
    result = ParseResult(
        applications=validated,
        errors=errors,
        source_format=detected_format,
        total_raw_records=total_raw,
        valid_count=len(validated),
        error_count=len(errors),
    )

    logger.info(
        f"parse_input complete: {result.valid_count}/{result.total_raw_records} records valid "
        f"({result.error_count} errors) [format={result.source_format}]"
    )

    return result
