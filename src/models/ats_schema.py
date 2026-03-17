from pydantic import BaseModel, Field
from typing import Optional, Any
from enum import Enum

class FieldType(str, Enum):
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"
    OBJECT = "object"
    ARRAY = "array"
    UNKNOWN = "unknown"

class ATSField(BaseModel):
    """Represents a single field discovered in an ATS schema."""
    name: str = Field(description="Raw field name as it appears in the ATS")
    field_type: FieldType = Field(description="Detected data type")
    nullable: bool = Field(default=True, description="Whether the field can be null")
    sample_value: Optional[Any] = Field(default=None, description="Example value from mock data")
    nested_path: str = Field(description="Dot-notation path to this field (e.g., 'candidate.address.city')")
    description: Optional[str] = Field(default=None, description="Inferred description of what this field contains")
    anomalies: list[str] = Field(default_factory=list, description="Detected naming/format anomalies")

class EntityRelationship(BaseModel):
    """Represents a relationship between two entities in the ATS schema."""
    source_entity: str
    source_field: str
    target_entity: str
    target_field: str
    relationship_type: str = Field(description="e.g., 'foreign_key', 'nested_ref', 'lookup'")

class SchemaReport(BaseModel):
    """Complete report from the Schema Explorer agent."""
    ats_name: str = Field(description="Name of the ATS system (e.g., 'Workday Enterprise')")
    endpoints: list[str] = Field(description="Discovered API endpoints or table names")
    fields: list[ATSField] = Field(description="All discovered fields across all endpoints")
    relationships: list[EntityRelationship] = Field(default_factory=list)
    total_field_count: int
    nesting_depth: int = Field(description="Maximum nesting depth observed")
    custom_conventions: list[str] = Field(
        default_factory=list,
        description="Detected naming conventions (e.g., '_v3_Final suffix pattern')"
    )
    anomaly_summary: str = Field(default="", description="Human-readable summary of schema oddities")