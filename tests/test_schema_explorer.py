import os
import pytest
import json
from agents import Runner
from src.agents.schema_explorer import create_schema_explorer, _read_schema_file, _list_endpoints, _inspect_field
from src.models import SchemaReport

def test_read_schema_file():
    # Test reading the mock workday schema
    schema_str = _read_schema_file("src/mock_data/workday_schema.json")
    assert isinstance(schema_str, str)
    schema = json.loads(schema_str)
    assert "ats_name" in schema
    assert schema["ats_name"] == "Workday Enterprise HCM"

def test_list_endpoints():
    endpoints = _list_endpoints("src/mock_data/workday_schema.json")
    assert isinstance(endpoints, list)
    assert "/ccx/api/v1/recruiting/candidates" in endpoints
    assert "/ccx/api/v1/recruiting/requisitions" in endpoints

def test_inspect_field():
    field_info_str = _inspect_field("src/mock_data/workday_schema.json", "entities.WD_Candidate_Profile.fields.cand_nm_first")
    assert isinstance(field_info_str, str)
    field_info = json.loads(field_info_str)
    assert field_info.get("type") == "string"

@pytest.mark.asyncio
async def test_schema_explorer_agent():
    # Only run the agent if OPENAI_API_KEY is provided, to avoid failing CI without keys
    if not os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY") == "sk-your-openai-key-here":
        pytest.skip("Skipping agent test because OPENAI_API_KEY is not set.")

    agent = create_schema_explorer()
    result = await Runner.run(agent, input="Analyze the schema at src/mock_data/workday_schema.json")
    
    assert result.final_output is not None
    assert isinstance(result.final_output, SchemaReport)
    
    report = result.final_output
    assert report.ats_name == "Workday Enterprise HCM"
    assert len(report.endpoints) > 0
    assert len(report.fields) >= 50
    assert report.total_field_count >= 50
    
    # Check if anomalies/conventions were detected
    assert len(report.custom_conventions) > 0
    convention_text = " ".join(report.custom_conventions).lower()
    assert "_v3_final" in convention_text or "legacy" in convention_text or "do_not_use" in convention_text
