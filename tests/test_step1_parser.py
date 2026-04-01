"""
RootNode - Step 1 Test Suite: CSV / JSON Input Parser
======================================================
Covers: CSV parsing, JSON parsing, validation, edge cases,
        column aliases, dependency integrity, and error handling.
"""

import json
import os
import sys
import pytest

# Ensure project root is on the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.parsers.csv_parser import parse_input
from backend.models.application import ApplicationRecord, Criticality, Complexity


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "..", "backend", "fixtures")
CSV_PATH = os.path.join(FIXTURES_DIR, "sample_apps.csv")
JSON_PATH = os.path.join(FIXTURES_DIR, "sample_apps.json")

MINIMAL_CSV = """app_id,name,dependencies,criticality,data_size,business_priority,complexity
APP001,Auth Service,,critical,50.0,1,simple
APP002,Payment,APP001,high,30.0,2,moderate
"""

MINIMAL_JSON = json.dumps([
    {
        "app_id": "APP001",
        "name": "Auth Service",
        "dependencies": [],
        "criticality": "critical",
        "data_size": 50.0,
        "business_priority": 1,
        "complexity": "simple",
    },
    {
        "app_id": "APP002",
        "name": "Payment",
        "dependencies": ["APP001"],
        "criticality": "high",
        "data_size": 30.0,
        "business_priority": 2,
        "complexity": "moderate",
    },
])


# ===========================================================================
# CSV Tests
# ===========================================================================

class TestCSVParsing:
    """Tests for CSV input path."""

    def test_parse_csv_string(self):
        result = parse_input(MINIMAL_CSV)
        assert result.source_format == "csv"
        assert result.valid_count == 2
        assert result.success

    def test_parse_csv_file(self):
        result = parse_input(CSV_PATH)
        assert result.source_format == "csv"
        assert result.valid_count == 15
        assert result.total_raw_records == 15

    def test_csv_app_ids_correct(self):
        result = parse_input(MINIMAL_CSV)
        assert result.app_ids == ["APP001", "APP002"]

    def test_csv_dependencies_parsed(self):
        result = parse_input(MINIMAL_CSV)
        auth = result.get_app("APP001")
        payment = result.get_app("APP002")
        assert auth.dependencies == []
        assert payment.dependencies == ["APP001"]

    def test_csv_comma_separated_dependencies(self):
        csv_data = """app_id,name,dependencies,criticality,data_size,business_priority,complexity
APP001,Service A,,medium,10,3,simple
APP002,Service B,"APP001,APP003",high,20,2,moderate
APP003,Service C,,low,5,4,simple
"""
        result = parse_input(csv_data)
        svc_b = result.get_app("APP002")
        assert "APP001" in svc_b.dependencies
        assert "APP003" in svc_b.dependencies

    def test_csv_column_aliases(self):
        csv_data = """application_id,application_name,depends_on,criticality,size_gb,priority,migration_complexity
APP001,Auth,,critical,50.0,1,simple
"""
        result = parse_input(csv_data)
        assert result.valid_count == 1
        app = result.applications[0]
        assert app.app_id == "APP001"
        assert app.name == "Auth"
        assert app.data_size == 50.0


# ===========================================================================
# JSON Tests
# ===========================================================================

class TestJSONParsing:
    """Tests for JSON input path."""

    def test_parse_json_string(self):
        result = parse_input(MINIMAL_JSON)
        assert result.source_format == "json"
        assert result.valid_count == 2

    def test_parse_json_file(self):
        result = parse_input(JSON_PATH)
        assert result.source_format == "json"
        assert result.valid_count == 15

    def test_json_wrapper_unwrap(self):
        wrapped = json.dumps({"applications": [
            {"app_id": "X1", "name": "Test", "criticality": "low",
             "data_size": 1, "business_priority": 5, "complexity": "simple"}
        ]})
        result = parse_input(wrapped)
        assert result.valid_count == 1
        assert result.applications[0].app_id == "X1"

    def test_json_single_object(self):
        single = json.dumps({
            "app_id": "SOLO", "name": "Solo App", "criticality": "medium",
            "data_size": 10, "business_priority": 3, "complexity": "simple"
        })
        result = parse_input(single)
        assert result.valid_count == 1

    def test_parse_python_list_directly(self):
        data = [
            {"app_id": "A1", "name": "Alpha", "criticality": "low",
             "data_size": 5, "business_priority": 4, "complexity": "simple"},
        ]
        result = parse_input(data)
        assert result.valid_count == 1
        assert result.source_format == "json"


# ===========================================================================
# Validation Tests
# ===========================================================================

class TestValidation:
    """Tests for Pydantic validation and integrity checks."""

    def test_missing_required_field(self):
        bad_json = json.dumps([{"name": "No ID", "criticality": "low",
                                "data_size": 1, "business_priority": 5,
                                "complexity": "simple"}])
        result = parse_input(bad_json)
        assert result.error_count > 0
        assert result.valid_count == 0

    def test_invalid_criticality(self):
        bad_json = json.dumps([{"app_id": "X", "name": "Bad",
                                "criticality": "ultra", "data_size": 1,
                                "business_priority": 3, "complexity": "simple"}])
        result = parse_input(bad_json)
        assert result.error_count > 0

    def test_invalid_priority_range(self):
        bad_json = json.dumps([{"app_id": "X", "name": "Bad",
                                "criticality": "low", "data_size": 1,
                                "business_priority": 99, "complexity": "simple"}])
        result = parse_input(bad_json)
        assert result.error_count > 0

    def test_negative_data_size(self):
        bad_json = json.dumps([{"app_id": "X", "name": "Bad",
                                "criticality": "low", "data_size": -10,
                                "business_priority": 3, "complexity": "simple"}])
        result = parse_input(bad_json)
        assert result.error_count > 0

    def test_duplicate_app_id_flagged(self):
        dupes = json.dumps([
            {"app_id": "DUP", "name": "First", "criticality": "low",
             "data_size": 1, "business_priority": 5, "complexity": "simple"},
            {"app_id": "DUP", "name": "Second", "criticality": "low",
             "data_size": 1, "business_priority": 5, "complexity": "simple"},
        ])
        result = parse_input(dupes)
        assert any("Duplicate" in e for e in result.errors)

    def test_dangling_dependency_flagged(self):
        data = json.dumps([
            {"app_id": "A", "name": "App A", "dependencies": ["GHOST"],
             "criticality": "low", "data_size": 1, "business_priority": 5,
             "complexity": "simple"},
        ])
        result = parse_input(data)
        assert any("GHOST" in e for e in result.errors)

    def test_strict_mode_raises(self):
        bad_json = json.dumps([{"name": "No ID"}])
        with pytest.raises(ValueError):
            parse_input(bad_json, strict=True)


# ===========================================================================
# Edge Cases
# ===========================================================================

class TestEdgeCases:
    """Edge cases and boundary conditions."""

    def test_empty_csv(self):
        result = parse_input("app_id,name\n")
        # Header only, no data rows
        assert result.valid_count == 0

    def test_invalid_format(self):
        result = parse_input("this is just plain text without commas")
        assert result.error_count > 0

    def test_invalid_json(self):
        result = parse_input('{"broken: json}', format_hint="json")
        assert result.error_count > 0

    def test_format_hint_override(self):
        result = parse_input(MINIMAL_JSON, format_hint="json")
        assert result.source_format == "json"
        assert result.valid_count == 2

    def test_whitespace_handling(self):
        csv_data = """app_id, name , dependencies, criticality , data_size, business_priority, complexity
  APP001 , Auth Service ,, critical , 50.0 , 1 , simple
"""
        result = parse_input(csv_data)
        assert result.valid_count == 1
        app = result.applications[0]
        assert app.app_id == "APP001"
        assert app.criticality == "critical"


# ===========================================================================
# Model Tests
# ===========================================================================

class TestApplicationRecord:
    """Direct model tests."""

    def test_defaults(self):
        app = ApplicationRecord(app_id="T1", name="Test")
        assert app.criticality == "medium"
        assert app.complexity == "moderate"
        assert app.data_size == 0.0
        assert app.business_priority == 3
        assert app.risk_score is None
        assert app.migration_strategy is None

    def test_dependency_string_parsing(self):
        app = ApplicationRecord(
            app_id="T1", name="Test",
            dependencies="APP001, APP002, APP003"
        )
        assert app.dependencies == ["APP001", "APP002", "APP003"]

    def test_enum_values_normalized(self):
        app = ApplicationRecord(
            app_id="T1", name="Test",
            criticality="  HIGH  ", complexity=" Simple "
        )
        assert app.criticality == "high"
        assert app.complexity == "simple"


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
