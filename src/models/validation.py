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