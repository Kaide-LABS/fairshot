from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum

class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"

class ValidationIssue(BaseModel):
    """A single issue found during validation."""
    severity: Severity
    field: Optional[str] = None
    message: str
    suggestion: Optional[str] = None

class ValidationResult(BaseModel):
    """Output from Gemini cross-validation."""
    is_valid: bool
    issues: list[ValidationIssue] = Field(default_factory=list)
    gemini_summary: str = Field(description="Gemini's overall assessment")
    approved_transforms: int
    flagged_transforms: int
    iteration: int = Field(default=1, description="Which validation pass this is (max 2)")

class TransformOperation(BaseModel):
    """A single deterministic transform operation."""
    fairshot_field: str = Field(description="Target field in Fairshot API (dot-notation for nested)")
    ats_source_path: str = Field(description="Source field path in ATS record (dot-notation)")
    transform_type: str = Field(description="One of the predefined transform types")
    params: dict = Field(
        default_factory=dict,
        description="Transform-specific parameters (e.g., date_format, enum_map, delimiter)"
    )
    is_array_item: bool = Field(
        default=False,
        description="True if this transform applies inside an array (e.g., education[], experience[])"
    )
    array_source_path: str = Field(
        default="",
        description="If is_array_item, the path to the source array (e.g., 'education_history')"
    )
    array_target_path: str = Field(
        default="",
        description="If is_array_item, the path to the target array (e.g., 'education')"
    )
    nullable: bool = Field(default=True, description="Whether to skip if source value is None")


class TransformSpec(BaseModel):
    """Complete transform specification output by the Code Generator agent.
    This is the structured intermediate representation between the LLM
    and the Jinja2 template engine."""
    ats_name: str
    transforms: list[TransformOperation]
    custom_code_blocks: list[str] = Field(
        default_factory=list,
        description="Any custom Python snippets the agent deems necessary (escape hatch)"
    )
    notes: str = Field(default="", description="Agent notes about edge cases or assumptions")