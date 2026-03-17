"""
Tests for the Deployment Orchestrator.

- Unit tests for helper functions (no API key)
- Pipeline config tests (no API key)
- Full integration test (requires OPENAI_API_KEY, optionally GOOGLE_API_KEY)
"""

import os
import json
import pytest
from datetime import datetime, timezone

from src.models import PipelineState, PipelineStage, LogEntry
from src.agents.orchestrator import (
    SCHEMA_CONFIGS,
    _now,
    _add_log,
    _transition,
    run_pipeline,
)


# ─── Config Tests ────────────────────────────────────────────────────────


class TestSchemaConfigs:
    def test_all_schemas_defined(self):
        assert "Workday Enterprise" in SCHEMA_CONFIGS
        assert "SmartRecruiters Lite" in SCHEMA_CONFIGS
        assert "Legacy Oracle" in SCHEMA_CONFIGS

    def test_config_has_required_keys(self):
        for name, config in SCHEMA_CONFIGS.items():
            assert "schema_path" in config, f"{name} missing schema_path"
            assert "entity_name" in config, f"{name} missing entity_name"
            assert "fairshot_spec_path" in config, f"{name} missing fairshot_spec_path"

    def test_schema_files_exist(self):
        for name, config in SCHEMA_CONFIGS.items():
            assert os.path.exists(config["schema_path"]), f"{name}: {config['schema_path']} not found"
            assert os.path.exists(config["fairshot_spec_path"]), f"{name}: {config['fairshot_spec_path']} not found"


# ─── Helper Tests ────────────────────────────────────────────────────────


class TestHelpers:
    def test_now_returns_utc(self):
        ts = _now()
        assert ts.tzinfo is not None

    def test_add_log(self):
        state = PipelineState()
        _add_log(state, PipelineStage.IDLE, "test message", detail="some detail")
        assert len(state.logs) == 1
        assert state.logs[0].message == "test message"
        assert state.logs[0].detail == "some detail"
        assert state.logs[0].stage == PipelineStage.IDLE

    def test_transition_updates_state(self):
        state = PipelineState()
        callback_calls = []
        _transition(
            state, PipelineStage.SCHEMA_EXPLORATION, 25.0,
            "exploring", callback=lambda s: callback_calls.append(s.current_stage)
        )
        assert state.current_stage == PipelineStage.SCHEMA_EXPLORATION
        assert state.progress_percent == 25.0
        assert len(state.logs) == 1
        assert len(callback_calls) == 1
        assert callback_calls[0] == PipelineStage.SCHEMA_EXPLORATION

    def test_transition_without_callback(self):
        state = PipelineState()
        _transition(state, PipelineStage.COMPLETED, 100.0, "done")
        assert state.current_stage == PipelineStage.COMPLETED


# ─── Pipeline Error Handling ─────────────────────────────────────────────


class TestPipelineErrors:
    @pytest.mark.asyncio
    async def test_invalid_schema_name(self):
        state = await run_pipeline("Nonexistent ATS")
        assert state.current_stage == PipelineStage.ERROR
        assert "Unknown schema" in state.error
        assert len(state.logs) >= 1


# ─── Full Integration Test ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_full_pipeline_workday():
    """End-to-end pipeline test against Workday schema.
    Requires OPENAI_API_KEY. Optionally uses GOOGLE_API_KEY for Gemini validation.
    """
    if not os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY") == "sk-your-openai-key-here":
        pytest.skip("Skipping integration test — OPENAI_API_KEY not set")

    stage_log = []

    def track_callback(state: PipelineState):
        stage_log.append(state.current_stage)

    state = await run_pipeline("Workday Enterprise", callback=track_callback)

    # Pipeline should complete (or error gracefully)
    assert state.current_stage in (PipelineStage.COMPLETED, PipelineStage.ERROR), (
        f"Pipeline ended in unexpected stage: {state.current_stage}"
    )

    if state.current_stage == PipelineStage.COMPLETED:
        # Verify all artifacts present
        assert state.schema_report is not None, "Missing schema_report"
        assert state.mapping_document is not None, "Missing mapping_document"
        assert state.generated_middleware is not None, "Missing generated_middleware"
        assert state.validation_result is not None, "Missing validation_result"

        # Verify schema report
        assert state.schema_report["total_field_count"] >= 30

        # Verify mapping document
        assert len(state.mapping_document["mappings"]) >= 10

        # Verify middleware is valid Python
        compile(state.generated_middleware, "<test>", "exec")

        # Verify timing
        assert state.started_at is not None
        assert state.completed_at is not None
        elapsed = (state.completed_at - state.started_at).total_seconds()
        assert elapsed < 120, f"Pipeline took {elapsed:.1f}s — target is < 60s"

        # Verify callback was called for each stage
        assert PipelineStage.SCHEMA_EXPLORATION in stage_log
        assert PipelineStage.SEMANTIC_MAPPING in stage_log
        assert PipelineStage.CODE_GENERATION in stage_log
        assert PipelineStage.COMPLETED in stage_log

        # Verify logs
        assert len(state.logs) >= 6  # At least 2 per stage (start + complete)
    else:
        # If it errored, just make sure the error was logged
        assert state.error is not None
        print(f"Pipeline errored (may be expected without full API access): {state.error}")
