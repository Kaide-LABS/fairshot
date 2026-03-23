"""
Semantic Mapper Agent — Phase 3

Takes a SchemaReport from the Schema Explorer + the Fairshot API spec,
and produces a MappingDocument with field-by-field mappings, confidence
scores, and reasoning.
"""

import json
import logging
from typing import Any

from agents import Agent, function_tool

from src.models import (
    SchemaReport,
    MappingDocument,
    FieldMapping,
    Confidence,
    ATSField,
)

logger = logging.getLogger(__name__)

# ─── Tool 1: Load Fairshot API Spec ──────────────────────────────────────

_fairshot_spec_cache: dict[str, dict] = {}


def _load_fairshot_spec(path: str) -> str:
    """Load and return the Fairshot API spec as a JSON string.

    Args:
        path: File path to the fairshot_api_spec.json file.
    """
    try:
        if path in _fairshot_spec_cache:
            return json.dumps(_fairshot_spec_cache[path], indent=2)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            _fairshot_spec_cache[path] = data
            return json.dumps(data, indent=2)
    except Exception as e:
        logger.error(f"Failed to load Fairshot spec at {path}: {e}")
        return json.dumps({"error": str(e)})


# ─── Tool 2: Schema Summary Helper ──────────────────────────────────────


def _get_schema_summary(schema_report_json: str) -> str:
    """Parse a SchemaReport JSON and return a concise summary of all fields
    with their types, paths, and any anomalies. This helps the agent
    quickly scan all available ATS fields.

    Args:
        schema_report_json: The SchemaReport serialized as a JSON string.
    """
    try:
        report = SchemaReport.model_validate_json(schema_report_json)
        lines = [
            f"ATS: {report.ats_name}",
            f"Endpoints: {', '.join(report.endpoints)}",
            f"Total fields: {report.total_field_count}",
            f"Nesting depth: {report.nesting_depth}",
            f"Conventions: {', '.join(report.custom_conventions)}",
            "",
            "=== ALL FIELDS ===",
        ]
        for field in report.fields:
            anomaly_str = f" [ANOMALIES: {', '.join(field.anomalies)}]" if field.anomalies else ""
            sample_str = f" (sample: {field.sample_value})" if field.sample_value is not None else ""
            lines.append(
                f"  {field.nested_path} | type={field.field_type.value} | "
                f"nullable={field.nullable}{sample_str}{anomaly_str}"
            )
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"Failed to parse SchemaReport: {e}")
        return f"Error parsing schema report: {e}"


# ─── Tool 3: Field Samples Lookup ───────────────────────────────────────


def _get_field_samples(schema_file_path: str, entity_name: str) -> str:
    """Return sample records for a specific entity from the raw schema file.
    Useful when the agent needs to inspect actual data values to resolve
    ambiguous mappings.

    Args:
        schema_file_path: Path to the original ATS schema JSON file.
        entity_name: The entity key (e.g., 'Candidate').
    """
    try:
        with open(schema_file_path, "r", encoding="utf-8") as f:
            schema = json.load(f)
        entity = schema.get("entities", {}).get(entity_name, {})
        samples = entity.get("sample_records", [])
        if not samples:
            return f"No sample records found for entity '{entity_name}'"
        return json.dumps(samples, indent=2, default=str)
    except Exception as e:
        return f"Error loading samples: {e}"


# ─── Agent Factory ───────────────────────────────────────────────────────

SEMANTIC_MAPPER_INSTRUCTIONS = """\
You are an expert data integration engineer specializing in enterprise ATS \
schema mapping. Your task is to produce a complete, deterministic field mapping \
between a source ATS schema and the Fairshot target API.

## Your Process

1. **Load the Fairshot API spec** using `load_fairshot_spec` to understand ALL \
   target fields across all endpoints (create_candidate, schedule_simulation, \
   get_requisition).

2. **Review the Schema Summary** using `get_schema_summary` to see all \
   discovered ATS fields with their types, paths, and anomalies.

3. **If needed**, use `get_field_samples` to inspect actual sample data values \
   for ambiguous fields.

4. **Produce a MappingDocument** with the following rules:

## Mapping Rules

For EACH Fairshot target field (from the `create_candidate` endpoint — this is \
the primary mapping target), find the best matching ATS source field:

- **Exact matches** are rare. Focus on semantic equivalence.
- **Expand abbreviations**: `nm` = name, `cd` = code, `dt` = date, `ts` = \
  timestamp, `txt` = text, `addr` = address, `loc` = location, `cand` = \
  candidate, `req` = requisition, `edu` = education, `exp` = experience, \
  `mgr` = manager.
- **Nested paths**: Map nested ATS fields to nested Fairshot fields. E.g., \
  `Candidate.Contact_Data.Location_Data.City` → `location.city`.
- **Array items**: Map array sub-fields individually. E.g., \
  `Resume_Data.Education_Data[].School_Name` → `education[].institution`.
- **Enum translation**: When ATS uses codes (e.g., `Careers_Page`) and \
  Fairshot uses lowercase (e.g., `careers_page`), note the transform needed.
- **Date format normalization**: When ATS uses `dateTime` or other formats \
  and Fairshot expects ISO 8601, note the transform needed.
- **Skip deprecated/legacy fields**: Fields with `_DEPRECATED`, `_DO_NOT_USE`, \
  or `_LEGACY` suffixes should NOT be mapped if a non-deprecated alternative \
  exists for the same data. If a `_LEGACY` field is the ONLY source for a \
  target field, map it but flag the anomaly.

## Confidence Scoring

- **HIGH (>0.9)**: Clear semantic match. E.g., `cand_nm_first` → `first_name`.
- **MEDIUM (0.7–0.9)**: Reasonable match requiring transformation. E.g., \
  `source_channel_cd` → `source_channel` (needs enum normalization).
- **LOW (<0.7)**: Uncertain match. E.g., `screening_score_v2` → `metadata` \
  (no direct Fairshot equivalent, stuffed into metadata).

## Transform Function Naming

Name each transform function descriptively:
- `direct_copy` — field value passes through unchanged
- `lowercase_enum` — convert ATS enum to Fairshot lowercase equivalent
- `date_mmddyyyy_to_iso` — convert MM/DD/YYYY to ISO 8601
- `epoch_to_iso` — convert Unix epoch seconds to ISO 8601 date
- `nested_extract` — extract value from a nested object path
- `semicolon_to_list` — split semicolon-delimited string into array
- `json_string_to_list` — parse a JSON array string into actual array
- `phone_to_e164` — normalize phone to E.164 format
- `custom_[description]` — any other transform

## Output Requirements

- Map ALL fields in the Fairshot `create_candidate` endpoint
- Also map `job_id` from `get_requisition` (for the simulation scheduling flow)
- List ALL unmapped ATS fields in `unmapped_ats_fields`
- List any unmapped Fairshot fields in `unmapped_fairshot_fields`
- Calculate `overall_confidence` as the mean of all `confidence_score` values
- Calculate `mapping_coverage` as: mapped_fairshot_fields / total_fairshot_fields

## CRITICAL
- You MUST use the provided tools. Do NOT guess the schema or spec contents.
- Every mapping MUST include a `reasoning` string explaining WHY this match \
  was chosen.
- DO NOT map the same ATS field to multiple Fairshot fields unless it genuinely \
  serves both (e.g., `Custom_Req_ID_v3_Final` → `job_id`).
"""


def create_semantic_mapper() -> Agent:
    """Create and return the Semantic Mapper agent."""
    load_fairshot_spec = function_tool(_load_fairshot_spec)
    get_schema_summary = function_tool(_get_schema_summary)
    get_field_samples = function_tool(_get_field_samples)

    return Agent(
        name="Semantic Mapper",
        instructions=SEMANTIC_MAPPER_INSTRUCTIONS,
        tools=[load_fairshot_spec, get_schema_summary, get_field_samples],
        output_type=MappingDocument,
        model="gpt-5.3-codex",
    )