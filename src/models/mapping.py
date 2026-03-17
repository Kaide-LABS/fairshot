from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum

class Confidence(str, Enum):
    HIGH = "high"      # > 0.9
    MEDIUM = "medium"  # 0.7 - 0.9
    LOW = "low"        # < 0.7

class FieldMapping(BaseModel):
    """A single field mapping from ATS to Fairshot."""
    ats_field: str = Field(description="Source field path in ATS schema")
    fairshot_field: str = Field(description="Target field in Fairshot API")
    transform_function: str = Field(description="Name of the Python transform function to apply")
    confidence: Confidence
    confidence_score: float = Field(ge=0.0, le=1.0)
    reasoning: str = Field(description="Why this mapping was chosen")
    alternatives: list[str] = Field(
        default_factory=list,
        description="Alternative ATS fields that could also map here"
    )

class MappingDocument(BaseModel):
    """Complete mapping output from the Semantic Mapper agent."""
    ats_name: str
    fairshot_api_version: str = "v1"
    mappings: list[FieldMapping]
    unmapped_ats_fields: list[str] = Field(
        default_factory=list,
        description="ATS fields with no Fairshot equivalent"
    )
    unmapped_fairshot_fields: list[str] = Field(
        default_factory=list,
        description="Fairshot fields with no ATS source"
    )
    warnings: list[str] = Field(default_factory=list)
    overall_confidence: float = Field(description="Average confidence across all mappings")
    mapping_coverage: float = Field(description="Percentage of Fairshot fields successfully mapped")