"""
Tests for the Code Generator agent.

- Template rendering tests (no API key required)
- Transform helper tests (no API key required)
- Gemini validation test (requires GOOGLE_API_KEY, skipped otherwise)
- Agent integration test (requires OPENAI_API_KEY + GOOGLE_API_KEY, skipped otherwise)
"""

import os
import json
import pytest
from src.models import (
    TransformSpec,
    TransformOperation,
    ValidationResult,
    MappingDocument,
    FieldMapping,
    Confidence,
)
from src.agents.code_generator import (
    _render_middleware,
    _render_middleware_from_spec,
    _run_test_transform,
    _load_sample_record,
    create_code_generator,
)


# ─── Template Rendering Tests ────────────────────────────────────────────


class TestRenderMiddleware:
    def _make_simple_spec(self) -> TransformSpec:
        return TransformSpec(
            ats_name="Test ATS",
            transforms=[
                TransformOperation(
                    fairshot_field="first_name",
                    ats_source_path="cand_nm_first",
                    transform_type="direct_copy",
                ),
                TransformOperation(
                    fairshot_field="email",
                    ats_source_path="cand_email",
                    transform_type="direct_copy",
                ),
            ],
        )

    def test_renders_valid_python(self):
        spec = self._make_simple_spec()
        code = _render_middleware(spec)
        assert "def transform(record: dict) -> dict:" in code
        assert "Test ATS" in code
        # Should compile without syntax errors
        compile(code, "<test>", "exec")

    def test_renders_date_transform(self):
        spec = TransformSpec(
            ats_name="Test",
            transforms=[
                TransformOperation(
                    fairshot_field="graduation_date",
                    ats_source_path="edu_grad_dt",
                    transform_type="date_mmddyyyy_to_iso",
                ),
            ],
        )
        code = _render_middleware(spec)
        assert "_date_mmddyyyy_to_iso" in code
        compile(code, "<test>", "exec")

    def test_renders_epoch_transform(self):
        spec = TransformSpec(
            ats_name="Test",
            transforms=[
                TransformOperation(
                    fairshot_field="start_date",
                    ats_source_path="exp_start_dt",
                    transform_type="epoch_to_iso",
                ),
            ],
        )
        code = _render_middleware(spec)
        assert "_epoch_to_iso" in code
        compile(code, "<test>", "exec")

    def test_renders_array_transforms(self):
        spec = TransformSpec(
            ats_name="Test",
            transforms=[
                TransformOperation(
                    fairshot_field="education.institution",
                    ats_source_path="edu_institution_nm",
                    transform_type="direct_copy",
                    is_array_item=True,
                    array_source_path="education_history",
                    array_target_path="education",
                ),
            ],
        )
        code = _render_middleware(spec)
        assert "education_history" in code
        assert "education" in code
        compile(code, "<test>", "exec")

    def test_renders_from_json(self):
        spec = TransformSpec(
            ats_name="Test",
            transforms=[
                TransformOperation(
                    fairshot_field="first_name",
                    ats_source_path="fname",
                    transform_type="direct_copy",
                ),
            ],
        )
        code = _render_middleware_from_spec(spec.model_dump_json())
        assert "def transform" in code


# ─── Transform Execution Tests ───────────────────────────────────────────


class TestRunTestTransform:
    def test_simple_direct_copy(self):
        code = '''
def transform(record):
    return {"first_name": record.get("fname")}
'''
        result = _run_test_transform(code, '{"fname": "Jane"}')
        parsed = json.loads(result)
        assert parsed["first_name"] == "Jane"

    def test_handles_bad_code(self):
        result = _run_test_transform("def broken(:", '{}')
        parsed = json.loads(result)
        assert "error" in parsed

    def test_handles_missing_transform_fn(self):
        result = _run_test_transform("x = 1", '{}')
        parsed = json.loads(result)
        assert "error" in parsed


# ─── Sample Record Loading ───────────────────────────────────────────────


class TestLoadSampleRecord:
    def test_loads_workday_sample(self):
        result = _load_sample_record(
            "src/mock_data/workday_schema.json", "WD_Candidate_Profile"
        )
        record = json.loads(result)
        assert record["cand_nm_first"] == "Jane"
        assert record["cand_email_primary_v3_Final"] == "jane.doe@email.com"

    def test_handles_missing_entity(self):
        result = _load_sample_record(
            "src/mock_data/workday_schema.json", "Nonexistent"
        )
        parsed = json.loads(result)
        assert "error" in parsed


# ─── End-to-End Render + Execute ─────────────────────────────────────────


class TestEndToEndTransform:
    """Renders a realistic TransformSpec and executes it against Workday sample data."""

    def test_workday_candidate_transform(self):
        spec = TransformSpec(
            ats_name="Workday Enterprise HCM",
            transforms=[
                TransformOperation(
                    fairshot_field="first_name",
                    ats_source_path="cand_nm_first",
                    transform_type="direct_copy",
                ),
                TransformOperation(
                    fairshot_field="last_name",
                    ats_source_path="cand_nm_last",
                    transform_type="direct_copy",
                ),
                TransformOperation(
                    fairshot_field="email",
                    ats_source_path="cand_email_primary_v3_Final",
                    transform_type="direct_copy",
                ),
                TransformOperation(
                    fairshot_field="location.city",
                    ats_source_path="address_block.addr_city_nm",
                    transform_type="nested_extract",
                ),
                TransformOperation(
                    fairshot_field="education.institution",
                    ats_source_path="edu_institution_nm",
                    transform_type="direct_copy",
                    is_array_item=True,
                    array_source_path="education_history",
                    array_target_path="education",
                ),
                TransformOperation(
                    fairshot_field="education.graduation_date",
                    ats_source_path="edu_graduation_dt",
                    transform_type="date_mmddyyyy_to_iso",
                    is_array_item=True,
                    array_source_path="education_history",
                    array_target_path="education",
                ),
            ],
        )

        # Render
        code = _render_middleware(spec)
        compile(code, "<test>", "exec")

        # Load sample and execute
        sample_json = _load_sample_record(
            "src/mock_data/workday_schema.json", "WD_Candidate_Profile"
        )
        result_json = _run_test_transform(code, sample_json)
        result = json.loads(result_json)

        # Assertions
        assert result.get("first_name") == "Jane"
        assert result.get("last_name") == "Doe"
        assert result.get("email") == "jane.doe@email.com"
        assert result.get("location", {}).get("city") == "San Francisco"
        assert len(result.get("education", [])) >= 1
        assert result["education"][0]["institution"] == "Stanford University"
        assert result["education"][0]["graduation_date"] == "2020-06-15"


# ─── Agent Integration Test ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_code_generator_agent():
    """Full agent integration test. Requires OPENAI_API_KEY."""
    if not os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY") == "sk-your-openai-key-here":
        pytest.skip("Skipping agent test — OPENAI_API_KEY not set")

    from agents import Runner

    # Build a minimal MappingDocument for the agent
    mapping_doc = MappingDocument(
        ats_name="Workday Enterprise HCM",
        mappings=[
            FieldMapping(
                ats_field="cand_nm_first",
                fairshot_field="first_name",
                transform_function="direct_copy",
                confidence=Confidence.HIGH,
                confidence_score=0.95,
                reasoning="cand_nm_first = candidate name first",
            ),
            FieldMapping(
                ats_field="cand_nm_last",
                fairshot_field="last_name",
                transform_function="direct_copy",
                confidence=Confidence.HIGH,
                confidence_score=0.95,
                reasoning="cand_nm_last = candidate name last",
            ),
            FieldMapping(
                ats_field="cand_email_primary_v3_Final",
                fairshot_field="email",
                transform_function="direct_copy",
                confidence=Confidence.HIGH,
                confidence_score=0.92,
                reasoning="Primary email field",
            ),
            FieldMapping(
                ats_field="address_block.addr_city_nm",
                fairshot_field="location.city",
                transform_function="nested_extract",
                confidence=Confidence.HIGH,
                confidence_score=0.93,
                reasoning="Nested address city field",
            ),
            FieldMapping(
                ats_field="source_channel_cd",
                fairshot_field="source_channel",
                transform_function="lowercase_enum",
                confidence=Confidence.MEDIUM,
                confidence_score=0.85,
                reasoning="ATS uses UPPERCASE enum codes",
            ),
        ],
        unmapped_ats_fields=["Custom_Diversity_Flag_DO_NOT_USE", "notes_txt_DEPRECATED"],
        unmapped_fairshot_fields=["candidate_id", "metadata"],
        overall_confidence=0.92,
        mapping_coverage=0.85,
    )

    generator = create_code_generator()
    gen_input = (
        f"Generate a TransformSpec for the following mapping.\n\n"
        f"Mapping Document (JSON):\n{mapping_doc.model_dump_json(indent=2)}\n\n"
        f"Schema file: src/mock_data/workday_schema.json\n"
        f"Primary entity: WD_Candidate_Profile\n"
        f"Fairshot spec: src/mock_data/fairshot_api_spec.json"
    )
    result = await Runner.run(generator, input=gen_input)
    transform_spec = result.final_output

    assert isinstance(transform_spec, TransformSpec)
    assert len(transform_spec.transforms) >= 4
    assert transform_spec.ats_name == "Workday Enterprise HCM"

    # Verify the spec can be rendered into valid Python
    code = _render_middleware(transform_spec)
    compile(code, "<test>", "exec")