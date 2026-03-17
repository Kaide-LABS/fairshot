from pydantic import BaseModel, Field
from typing import Optional, Any
from enum import Enum
from datetime import datetime

class PipelineStage(str, Enum):
    IDLE = "idle"
    SCHEMA_EXPLORATION = "schema_exploration"
    SEMANTIC_MAPPING = "semantic_mapping"
    CODE_GENERATION = "code_generation"
    VALIDATION = "validation"
    DATA_FLOW = "data_flow"
    DRIFT_DETECTION = "drift_detection"
    COMPLETED = "completed"
    ERROR = "error"

class LogEntry(BaseModel):
    """A single log entry from the pipeline."""
    timestamp: datetime
    stage: PipelineStage
    message: str
    detail: Optional[str] = None

class PipelineState(BaseModel):
    """Tracks the current state of the full integration pipeline."""
    current_stage: PipelineStage = PipelineStage.IDLE
    progress_percent: float = Field(default=0.0, ge=0.0, le=100.0)
    logs: list[LogEntry] = Field(default_factory=list)
    schema_report: Optional[Any] = None
    mapping_document: Optional[Any] = None
    generated_middleware: Optional[str] = None
    validation_result: Optional[Any] = None
    drift_detected: bool = False
    drift_changes: list[str] = Field(default_factory=list)
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None