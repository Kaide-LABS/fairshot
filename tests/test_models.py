import pytest
from pydantic import ValidationError
from datetime import datetime
from src.models import (
    FieldType, ATSField, EntityRelationship, SchemaReport,
    Confidence, FieldMapping, MappingDocument,
    Severity, ValidationIssue, ValidationResult,
    PipelineStage, LogEntry, PipelineState
)

def test_ats_field_creation():
    field = ATSField(
        name="cand_nm_first",
        field_type=FieldType.STRING,
        nested_path="candidate.first_name"
    )
    assert field.name == "cand_nm_first"
    assert field.nested_path == "candidate.first_name"
    
    with pytest.raises(ValidationError):
        ATSField(name="missing_path", field_type=FieldType.STRING)

def test_schema_report_creation():
    field = ATSField(name="test", field_type=FieldType.STRING, nested_path="test")
    report = SchemaReport(
        ats_name="Test ATS",
        endpoints=["/api/test"],
        fields=[field],
        total_field_count=1,
        nesting_depth=1
    )
    assert report.total_field_count == 1
    
    with pytest.raises(ValidationError):
        SchemaReport(ats_name="Missing Count", endpoints=[], fields=[], nesting_depth=0)

def test_field_mapping_confidence_score():
    mapping = FieldMapping(
        ats_field="cand_nm_first",
        fairshot_field="first_name",
        transform_function="transform_first_name",
        confidence=Confidence.HIGH,
        confidence_score=0.95,
        reasoning="Exact match"
    )
    assert mapping.confidence_score == 0.95
    
    with pytest.raises(ValidationError):
        FieldMapping(
            ats_field="a", fairshot_field="b", transform_function="c",
            confidence=Confidence.HIGH, confidence_score=1.5, reasoning="d"
        )

def test_mapping_document_creation():
    doc = MappingDocument(
        ats_name="Test ATS",
        mappings=[],
        overall_confidence=0.0,
        mapping_coverage=0.0
    )
    assert doc.overall_confidence == 0.0

def test_validation_result_creation():
    issue = ValidationIssue(severity=Severity.ERROR, message="Test issue")
    result = ValidationResult(
        is_valid=False,
        issues=[issue],
        gemini_summary="Failed",
        approved_transforms=0,
        flagged_transforms=1
    )
    assert not result.is_valid
    assert len(result.issues) == 1

def test_pipeline_state_defaults():
    state = PipelineState()
    assert state.current_stage == PipelineStage.IDLE
    assert state.progress_percent == 0.0

def test_log_entry_requires_timestamp():
    entry = LogEntry(timestamp=datetime.now(), stage=PipelineStage.IDLE, message="Test")
    assert entry.message == "Test"
    
    with pytest.raises(ValidationError):
        LogEntry(stage=PipelineStage.IDLE, message="Test")

def test_imports():
    # If the file imported everything properly at the top, this test just passes.
    assert True
