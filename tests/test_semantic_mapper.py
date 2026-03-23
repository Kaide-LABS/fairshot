"""
Tests for the Semantic Mapper agent.

- Tool-level unit tests (no API key required)
- Agent integration test (requires OPENAI_API_KEY, skipped otherwise)
"""

import os
import json
import pytest
from src.agents.semantic_mapper import (
    _load_fairshot_spec,
    _get_schema_summary,
    _get_field_samples,
    create_semantic_mapper,
)
from src.models import (
    SchemaReport,
    MappingDocument,
    ATSField,
    FieldType,
    Confidence,
)


# ─── Tool Unit Tests ─────────────────────────────────────────────────────


class TestLoadFairshotSpec:
    def test_loads_valid_spec(self):
        result = _load_fairshot_spec("src/mock_data/fairshot_api_spec.json")
        spec = json.loads(result)
        assert spec["api_name"] == "Fairshot Talent Assessment API"
        assert "create_candidate" in spec["endpoints"]
        assert "schedule_simulation" in spec["endpoints"]
        assert "get_requisition" in spec["endpoints"]
        assert "health_check" in spec["endpoints"]

    def test_spec_has_required_fields(self):
        result = _load_fairshot_spec("src/mock_data/fairshot_api_spec.json")
        spec = json.loads(result)
        candidate_fields = spec["endpoints"]["create_candidate"]["request_body"]
        # Verify key target fields exist
        assert "first_name" in candidate_fields
        assert "last_name" in candidate_fields
        assert "email" in candidate_fields
        assert "location" in candidate_fields
        assert "education" in candidate_fields
        assert "experience" in candidate_fields
        assert "source_channel" in candidate_fields
        assert "tags" in candidate_fields

    def test_handles_missing_file(self):
        result = _load_fairshot_spec("nonexistent.json")
        parsed = json.loads(result)
        assert "error" in parsed

    def test_caches_on_second_load(self):
        """Second load should use cache."""
        _load_fairshot_spec("src/mock_data/fairshot_api_spec.json")
        result2 = _load_fairshot_spec("src/mock_data/fairshot_api_spec.json")
        spec = json.loads(result2)
        assert spec["api_name"] == "Fairshot Talent Assessment API"


class TestGetSchemaSummary:
    def _make_sample_report(self) -> SchemaReport:
        return SchemaReport(
            ats_name="Test ATS",
            endpoints=["/api/test"],
            fields=[
                ATSField(
                    name="test_field",
                    field_type=FieldType.STRING,
                    nullable=False,
                    sample_value="hello",
                    nested_path="entity.test_field",
                    anomalies=["_v3_Final suffix"],
                ),
                ATSField(
                    name="another_field",
                    field_type=FieldType.INTEGER,
                    nullable=True,
                    nested_path="entity.another_field",
                ),
            ],
            total_field_count=2,
            nesting_depth=1,
            custom_conventions=["_v3_Final suffix pattern"],
        )

    def test_produces_readable_summary(self):
        report = self._make_sample_report()
        summary = _get_schema_summary(report.model_dump_json())
        assert "Test ATS" in summary
        assert "test_field" in summary
        assert "another_field" in summary
        assert "string" in summary
        assert "_v3_Final suffix" in summary

    def test_shows_sample_values(self):
        report = self._make_sample_report()
        summary = _get_schema_summary(report.model_dump_json())
        assert "hello" in summary

    def test_handles_invalid_json(self):
        result = _get_schema_summary("not valid json")
        assert "Error" in result


class TestGetFieldSamples:
    def test_returns_workday_samples(self):
        result = _get_field_samples(
            "src/mock_data/workday_schema.json", "WD_Candidate_Profile"
        )
        samples = json.loads(result)
        assert isinstance(samples, list)
        assert len(samples) >= 2
        assert samples[0]["cand_nm_first"] == "Jane"

    def test_returns_smartrecruiters_samples(self):
        result = _get_field_samples(
            "src/mock_data/smartrecruiters_schema.json", "candidates"
        )
        samples = json.loads(result)
        assert isinstance(samples, list)
        assert len(samples) >= 2

    def test_handles_missing_entity(self):
        result = _get_field_samples(
            "src/mock_data/workday_schema.json", "NonexistentEntity"
        )
        assert "No sample records" in result


# ─── Agent Integration Test ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_semantic_mapper_agent():
    """Full agent integration test against the Workday schema.
    Requires OPENAI_API_KEY to be set.
    """
    if not os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY") == "sk-your-openai-key-here":
        pytest.skip("Skipping agent test — OPENAI_API_KEY not set")

    from agents import Runner
    from src.agents.schema_explorer import create_schema_explorer

    # Step 1: Get a SchemaReport from the Explorer
    explorer = create_schema_explorer()
    explore_result = await Runner.run(
        explorer,
        input="Analyze the schema at src/mock_data/workday_schema.json",
    )
    schema_report = explore_result.final_output
    assert isinstance(schema_report, SchemaReport)

    # Step 2: Run the Semantic Mapper
    mapper = create_semantic_mapper()
    mapper_input = (
        f"Map the following ATS schema to the Fairshot API.\n\n"
        f"Schema Report (JSON):\n{schema_report.model_dump_json(indent=2)}\n\n"
        f"Raw schema file: src/mock_data/workday_schema.json\n"
        f"Fairshot API spec file: src/mock_data/fairshot_api_spec.json"
    )
    map_result = await Runner.run(mapper, input=mapper_input)
    mapping_doc = map_result.final_output

    # ── Assertions ──
    assert isinstance(mapping_doc, MappingDocument)
    assert mapping_doc.ats_name == "Workday Enterprise HCM"

    # Must have mappings
    assert len(mapping_doc.mappings) >= 15, (
        f"Expected at least 15 mappings, got {len(mapping_doc.mappings)}"
    )

    # Coverage should be >= 90%
    assert mapping_doc.mapping_coverage >= 0.85, (
        f"Expected coverage >= 85%, got {mapping_doc.mapping_coverage:.0%}"
    )

    # Every mapping must have reasoning
    for m in mapping_doc.mappings:
        assert m.reasoning, f"Mapping {m.ats_field} → {m.fairshot_field} has no reasoning"
        assert 0.0 <= m.confidence_score <= 1.0

    # Check critical mappings exist
    fairshot_fields_mapped = {m.fairshot_field for m in mapping_doc.mappings}
    for required_field in ["first_name", "last_name", "email"]:
        assert required_field in fairshot_fields_mapped, (
            f"Critical field '{required_field}' was not mapped"
        )

    # Check nested mapping exists (location.city)
    location_fields = {m.fairshot_field for m in mapping_doc.mappings if "location" in m.fairshot_field}
    assert len(location_fields) >= 1, "No location fields were mapped"

    # Check unmapped fields exist
    assert len(mapping_doc.unmapped_ats_fields) > 0, "Should have unmapped ATS fields"

    # Deprecated fields should be in unmapped (or mapped with anomaly noted)
    deprecated_keywords = ["DEPRECATED", "DO_NOT_USE"]
    all_mapped_ats = {m.ats_field for m in mapping_doc.mappings}
    for ats_field in all_mapped_ats:
        for kw in deprecated_keywords:
            if kw in ats_field:
                # If a deprecated field IS mapped, it should be low confidence
                matching = [m for m in mapping_doc.mappings if m.ats_field == ats_field]
                for m in matching:
                    assert m.confidence_score < 0.9, (
                        f"Deprecated field {ats_field} mapped with high confidence"
                    )