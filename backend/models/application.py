"""
RootNode - Application Data Models
===================================
Pydantic models for validated, type-safe application records.
Optimized for AWS Lambda cold-start performance.
"""

from __future__ import annotations

import enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class Criticality(str, enum.Enum):
    """Business criticality tier of an application."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Complexity(str, enum.Enum):
    """Technical migration complexity."""
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    VERY_COMPLEX = "very_complex"


# ---------------------------------------------------------------------------
# Core Record
# ---------------------------------------------------------------------------

class ApplicationRecord(BaseModel):
    """
    Validated representation of a single application in the migration portfolio.

    Consistent variable naming per project spec:
        app_id, dependencies, risk_score, migration_strategy
    """

    app_id: str = Field(
        ...,
        min_length=1,
        description="Unique identifier for the application.",
    )
    name: str = Field(
        ...,
        min_length=1,
        description="Human-readable application name.",
    )
    dependencies: List[str] = Field(
        default_factory=list,
        description="List of app_ids this application depends on.",
    )
    criticality: Criticality = Field(
        default=Criticality.MEDIUM,
        description="Business criticality tier.",
    )
    data_size: float = Field(
        default=0.0,
        ge=0,
        description="Data footprint in GB.",
    )
    business_priority: int = Field(
        default=3,
        ge=1,
        le=5,
        description="Business priority (1 = highest, 5 = lowest).",
    )
    complexity: Complexity = Field(
        default=Complexity.MODERATE,
        description="Technical migration complexity.",
    )

    # Computed downstream — initialized to defaults here
    risk_score: Optional[float] = Field(
        default=None,
        ge=0,
        le=100,
        description="Computed risk score (0-100). Populated by risk engine.",
    )
    migration_strategy: Optional[str] = Field(
        default=None,
        description="Migration strategy (e.g. rehost, replatform, refactor). Populated by AI engine.",
    )

    # ----- Validators -------------------------------------------------------

    @field_validator("dependencies", mode="before")
    @classmethod
    def parse_dependencies(cls, v):
        """Accept comma/semicolon-separated strings or lists."""
        if isinstance(v, str):
            # Normalize semicolons to commas, then split
            normalized = v.replace(";", ",")
            return [dep.strip() for dep in normalized.split(",") if dep.strip()]
        if v is None:
            return []
        return v

    @field_validator("criticality", mode="before")
    @classmethod
    def normalize_criticality(cls, v):
        if isinstance(v, str):
            return v.strip().lower()
        return v

    @field_validator("complexity", mode="before")
    @classmethod
    def normalize_complexity(cls, v):
        if isinstance(v, str):
            return v.strip().lower()
        return v

    @field_validator("data_size", mode="before")
    @classmethod
    def coerce_data_size(cls, v):
        if isinstance(v, str):
            return float(v.strip()) if v.strip() else 0.0
        return v

    @field_validator("business_priority", mode="before")
    @classmethod
    def coerce_priority(cls, v):
        if isinstance(v, str):
            return int(v.strip()) if v.strip() else 3
        return v

    model_config = {
        "str_strip_whitespace": True,
        "use_enum_values": True,
    }


# ---------------------------------------------------------------------------
# Parse Result Wrapper
# ---------------------------------------------------------------------------

class ParseResult(BaseModel):
    """Encapsulates the full output of a parse_input() call."""

    applications: List[ApplicationRecord] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    source_format: str = Field(default="unknown")
    total_raw_records: int = Field(default=0)
    valid_count: int = Field(default=0)
    error_count: int = Field(default=0)

    @property
    def success(self) -> bool:
        return self.error_count == 0

    @property
    def app_ids(self) -> List[str]:
        return [app.app_id for app in self.applications]

    def get_app(self, app_id: str) -> Optional[ApplicationRecord]:
        """Retrieve a single application by its app_id."""
        for app in self.applications:
            if app.app_id == app_id:
                return app
        return None
