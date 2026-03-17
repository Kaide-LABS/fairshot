import json
import logging
from typing import Any
from agents import Agent, function_tool
from src.models import SchemaReport, ATSField, FieldType
from src.utils.llm_providers import get_openai_model

logger = logging.getLogger(__name__)

_schema_cache = {}

def _read_schema_file(path: str) -> str:
    """Reads and parses a JSON schema file. Returns a JSON string of the schema."""
    try:
        if path in _schema_cache:
            return json.dumps(_schema_cache[path])
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            _schema_cache[path] = data
            return json.dumps(data)
    except Exception as e:
        logger.error(f"Failed to read schema file at {path}: {e}")
        return json.dumps({"error": str(e)})

def _list_endpoints(path: str) -> list[str]:
    """Enumerates all available endpoints or tables from the schema file at the given path."""
    try:
        if path not in _schema_cache:
            with open(path, 'r', encoding='utf-8') as f:
                _schema_cache[path] = json.load(f)
        schema = _schema_cache[path]
        
        endpoints = []
        if "entities" in schema:
            for entity_name, entity_data in schema["entities"].items():
                if "endpoint" in entity_data and entity_data["endpoint"]:
                    endpoints.append(entity_data["endpoint"])
                elif "table_name" in entity_data and entity_data["table_name"]:
                    endpoints.append(entity_data["table_name"])
                else:
                    endpoints.append(entity_name)
        return endpoints
    except Exception as e:
        logger.error(f"Failed to list endpoints: {e}")
        return []

def _inspect_field(path: str, field_path: str) -> str:
    """
    Gets detailed info on a single field from the schema.
    path: the file path to the schema.
    field_path: dot-notation path, e.g., 'entities.WD_Candidate_Profile.fields.cand_nm_first'
    """
    try:
        if path not in _schema_cache:
            with open(path, 'r', encoding='utf-8') as f:
                _schema_cache[path] = json.load(f)
        schema = _schema_cache[path]
        
        parts = field_path.split('.')
        current = schema
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return "{}"
        return json.dumps(current)
    except Exception as e:
        return "{}"

def create_schema_explorer() -> Agent:
    read_schema_file = function_tool(_read_schema_file)
    list_endpoints = function_tool(_list_endpoints)
    inspect_field = function_tool(_inspect_field)
    
    return Agent(
        name="Schema Explorer",
        instructions='''You are an expert integration engineer and forward deployed engineer. Your task is to autonomously explore a mock ATS schema, discovering all fields, data types, relationships, nesting structures, and naming conventions.
        
You must use the provided tools to:
1. Load the schema file (`read_schema_file`).
2. Enumerate all top-level endpoints/entities (`list_endpoints`).
3. Discover ALL fields across all entities recursively with types and sample values.
4. Identify relationships between entities (foreign keys, nested refs).
5. Flag naming conventions and anomalies (e.g., `_v3_Final` suffixes, mixed date formats, legacy fields).
6. Generate a complete and structured SchemaReport.

Ensure you process ALL entities and ALL fields in the schema to provide a comprehensively mapped SchemaReport output.

For Oracle (relational), infer relationships from naming conventions and explicit FK references.
''',
        tools=[read_schema_file, list_endpoints, inspect_field],
        output_type=SchemaReport,
        model="gpt-5.4",
    )
