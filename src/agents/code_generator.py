"""
Code Generator Agent — Phase 4

Takes a MappingDocument from the Semantic Mapper, produces a TransformSpec
(JSON), renders it into Python middleware via Jinja2, and cross-validates
with Gemini 2.5 Pro.
"""

import json
import logging
import os
from typing import Any

from agents import Agent, function_tool
from jinja2 import Environment, FileSystemLoader

from src.models import (
    MappingDocument,
    TransformSpec,
    TransformOperation,
    ValidationResult,
    ValidationIssue,
    Severity,
)
from src.utils.llm_providers import get_gemini_client, get_gemini_model

logger = logging.getLogger(__name__)

# ─── Jinja2 Setup ────────────────────────────────────────────────────────

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "..", "templates")


def _render_middleware(transform_spec: TransformSpec) -> str:
    """Render a TransformSpec into a Python middleware module using Jinja2.

    This is a deterministic, non-LLM operation. The template is static;
    only the data (TransformSpec) varies.
    """
    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template("middleware.py.j2")
    return template.render(
        ats_name=transform_spec.ats_name,
        transforms=transform_spec.transforms,
        custom_code_blocks=transform_spec.custom_code_blocks,
    )


# ─── Tool 1: Render Middleware ───────────────────────────────────────────


def _render_middleware_from_spec(transform_spec_json: str) -> str:
    """Take a TransformSpec as JSON, render it into Python middleware code
    via the Jinja2 template, and return the generated Python source.

    Args:
        transform_spec_json: A TransformSpec serialized as JSON string.
    """
    try:
        spec = TransformSpec.model_validate_json(transform_spec_json)
        code = _render_middleware(spec)
        return code
    except Exception as e:
        logger.error(f"Failed to render middleware: {e}")
        return f"Error rendering middleware: {e}"


# ─── Tool 2: Test Transform ─────────────────────────────────────────────


def _run_test_transform(middleware_code: str, sample_input_json: str) -> str:
    """Execute the generated middleware code against a sample input record
    and return the transformed output. Uses exec() in a sandboxed namespace.

    Args:
        middleware_code: The generated Python middleware source code.
        sample_input_json: A sample ATS record as a JSON string.
    """
    try:
        sample_input = json.loads(sample_input_json)

        # Execute middleware in isolated namespace
        namespace: dict[str, Any] = {}
        exec(middleware_code, namespace)

        transform_fn = namespace.get("transform")
        if not transform_fn:
            return json.dumps({"error": "No 'transform' function found in generated code"})

        result = transform_fn(sample_input)
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        return json.dumps({"error": str(e), "error_type": type(e).__name__})


# ─── Tool 3: Gemini Cross-Validation ────────────────────────────────────


def _validate_with_gemini(
    middleware_code: str,
    mapping_document_json: str,
    sample_input_json: str,
    transform_output_json: str,
) -> str:
    """Send the generated middleware + mapping context to Gemini 2.5 Pro
    for independent cross-validation. Returns a ValidationResult as JSON.

    Args:
        middleware_code: The generated Python middleware source code.
        mapping_document_json: The MappingDocument as JSON (for reference).
        sample_input_json: The sample ATS input record as JSON.
        transform_output_json: The output produced by running the middleware.
    """
    try:
        client = get_gemini_client()
        model = get_gemini_model()

        prompt = f"""You are a senior code reviewer specializing in data integration middleware.

Review the following auto-generated Python middleware that transforms ATS records into Fairshot API payloads.

## Generated Middleware Code
```python
{middleware_code}
```

## Field Mapping Reference
```json
{mapping_document_json}
```

## Sample Input (ATS Record)
```json
{sample_input_json}
```

## Transform Output
```json
{transform_output_json}
```

## Review Checklist
1. **Correctness**: Does each transform match the mapping specification?
2. **Edge cases**: How does the code handle null values, empty strings, missing fields?
3. **Date handling**: Are date conversions correct (MM/DD/YYYY → ISO, epoch → ISO)?
4. **Enum mapping**: Are enum translations accurate?
5. **Data loss**: Are any fields silently dropped or incorrectly mapped?
6. **Type safety**: Could any transform cause a runtime TypeError?

## Output Format
Respond with ONLY a JSON object (no markdown, no explanation outside JSON):
{{
    "is_valid": true/false,
    "issues": [
        {{
            "severity": "error" | "warning" | "info",
            "field": "field_name or null",
            "message": "description of issue",
            "suggestion": "how to fix or null"
        }}
    ],
    "summary": "One-paragraph overall assessment"
}}
"""

        response = client.models.generate_content(
            model=model,
            contents=prompt,
        )

        # Parse Gemini's response into ValidationResult
        response_text = response.text.strip()
        # Strip markdown code fences if present
        if response_text.startswith("```"):
            response_text = response_text.split("\n", 1)[1]
            if response_text.endswith("```"):
                response_text = response_text[:-3].strip()

        parsed = json.loads(response_text)

        result = ValidationResult(
            is_valid=parsed.get("is_valid", False),
            issues=[
                ValidationIssue(
                    severity=Severity(issue.get("severity", "warning")),
                    field=issue.get("field"),
                    message=issue.get("message", ""),
                    suggestion=issue.get("suggestion"),
                )
                for issue in parsed.get("issues", [])
            ],
            gemini_summary=parsed.get("summary", "No summary provided"),
            approved_transforms=sum(
                1 for i in parsed.get("issues", []) if i.get("severity") == "info"
            ),
            flagged_transforms=sum(
                1 for i in parsed.get("issues", [])
                if i.get("severity") in ("error", "warning")
            ),
        )
        return result.model_dump_json(indent=2)

    except Exception as e:
        logger.error(f"Gemini validation failed: {e}")
        fallback = ValidationResult(
            is_valid=False,
            issues=[
                ValidationIssue(
                    severity=Severity.ERROR,
                    message=f"Gemini validation call failed: {e}",
                )
            ],
            gemini_summary=f"Validation failed due to error: {e}",
            approved_transforms=0,
            flagged_transforms=1,
        )
        return fallback.model_dump_json(indent=2)


# ─── Tool 4: Load Sample Record ─────────────────────────────────────────


def _load_sample_record(schema_file_path: str, entity_name: str) -> str:
    """Load the first sample record from a mock schema file for testing.

    Args:
        schema_file_path: Path to the ATS schema JSON file.
        entity_name: The entity key (e.g., 'WD_Candidate_Profile').
    """
    try:
        with open(schema_file_path, "r", encoding="utf-8") as f:
            schema = json.load(f)
        entity = schema.get("entities", {}).get(entity_name, {})
        samples = entity.get("sample_records", [])
        if not samples:
            return json.dumps({"error": f"No sample records for '{entity_name}'"})
        return json.dumps(samples[0], indent=2, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


# ─── Agent Factory ───────────────────────────────────────────────────────

CODE_GENERATOR_INSTRUCTIONS = """\
You are an expert code generator specializing in data transformation middleware. \
Your task is to produce a TransformSpec (JSON) that will be rendered into Python \
middleware via a Jinja2 template.

## IMPORTANT: You do NOT write Python code directly.
Instead, you produce a structured TransformSpec JSON that describes each \
transform operation. A deterministic template renders the final Python.

## Your Process

1. You will receive a MappingDocument (JSON) containing field mappings from an \
   ATS schema to the Fairshot API, along with file paths.

2. For each FieldMapping in the MappingDocument, create a TransformOperation:
   - Set `fairshot_field` to the Fairshot target field path
   - Set `ats_source_path` to the ATS source field path
   - Set `transform_type` to one of the predefined types (see below)
   - Set `params` with any transform-specific parameters
   - For array fields (education, experience), set `is_array_item=true` and \
     populate `array_source_path` and `array_target_path`

3. After building the TransformSpec, call `render_middleware_from_spec` to get \
   the generated Python code.

4. Call `load_sample_record` to get a test input record.

5. Call `run_test_transform` with the generated code and sample record to verify \
   the transform works.

6. Call `validate_with_gemini` with the generated code, mapping document, sample \
   input, and transform output for cross-validation.

7. If Gemini flags ERROR-severity issues, revise your TransformSpec and repeat \
   steps 3-6 (max 2 revision rounds).

## Predefined Transform Types

| Type | Params | Behavior |
|------|--------|----------|
| `direct_copy` | (none) | Pass value through unchanged |
| `lowercase_enum` | `enum_map` (optional dict) | Lowercase value or use explicit map |
| `date_mmddyyyy_to_iso` | (none) | MM/DD/YYYY → YYYY-MM-DD |
| `epoch_to_iso` | (none) | Unix epoch → YYYY-MM-DD |
| `nested_extract` | (none) | Value is already at the dot-path — just copy |
| `semicolon_to_list` | (none) | "a;b;c" → ["a","b","c"] |
| `json_string_to_list` | (none) | '["a"]' → ["a"] |
| `phone_to_e164` | (none) | Strip non-numeric except leading + |
| `numeric_enum` | `enum_map` (dict) | Map int codes to strings |
| `custom` | `code` (str) | Raw Python (escape hatch — use sparingly) |

## Array Field Handling

For array fields like education and experience:
- Set `is_array_item = true`
- Set `array_source_path` to the ATS array field (e.g., `education_history`)
- Set `array_target_path` to the Fairshot array (e.g., `education`)
- The `ats_source_path` should be the sub-field name within each array item \
  (e.g., `edu_institution_nm`)
- The `fairshot_field` should include the array prefix \
  (e.g., `education.institution`)

## TransformSpec JSON Format

```json
{
    "ats_name": "Workday Enterprise HCM",
    "transforms": [
        {
            "fairshot_field": "first_name",
            "ats_source_path": "cand_nm_first",
            "transform_type": "direct_copy",
            "params": {},
            "is_array_item": false,
            "array_source_path": "",
            "array_target_path": "",
            "nullable": true
        },
        {
            "fairshot_field": "education.institution",
            "ats_source_path": "edu_institution_nm",
            "transform_type": "direct_copy",
            "params": {},
            "is_array_item": true,
            "array_source_path": "education_history",
            "array_target_path": "education",
            "nullable": true
        }
    ],
    "custom_code_blocks": [],
    "notes": ""
}
```

## Output
Your final output must be a TransformSpec JSON object. After validation, output \
the final (possibly revised) TransformSpec.
"""


def create_code_generator() -> Agent:
    """Create and return the Code Generator agent."""
    render_middleware = function_tool(_render_middleware_from_spec)
    run_test = function_tool(_run_test_transform)
    validate_gemini = function_tool(_validate_with_gemini)
    load_sample = function_tool(_load_sample_record)

    return Agent(
        name="Code Generator",
        instructions=CODE_GENERATOR_INSTRUCTIONS,
        tools=[render_middleware, run_test, validate_gemini, load_sample],
        output_type=TransformSpec,
        model="gpt-5.3-codex",
    )