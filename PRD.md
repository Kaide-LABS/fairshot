# PRD: Virtual FDE — Enterprise Integration Concierge Demo

> **Version:** 1.0
> **Date:** 2026-03-17
> **Author:** Claude (Architect) → Gemini (Implementer)
> **Status:** Draft — Awaiting Review

---

## 1. Executive Summary

The **Virtual FDE (Forward Deployed Engineer)** is a multi-agent AI system that autonomously maps, translates, and integrates Fairshot's talent assessment platform into any enterprise ATS — eliminating weeks of manual data plumbing. In a live demo, the system ingests a messy Workday-like schema, semantically maps every field to Fairshot's clean API, generates production-style middleware code, cross-validates it with a second LLM, and runs a live data flow — all in under 60 seconds with zero manual configuration. This directly automates the role Palantir fills with human FDEs, turning a months-long professional services engagement into a push-button deployment.

**Target audience:** Mattia Martinelli (primary — technical gatekeeper, ex-Palantir FDE), Alberto Natale & Luca Ventriglia (secondary — strategy & capital efficiency).

---

## 2. Problem Statement

Enterprise ATS integration is the **#1 bottleneck** in scaling B2B SaaS talent platforms:

- **Typical onboarding takes weeks to months** — schema mapping, middleware development, testing, and deployment require dedicated professional services teams
- **Every enterprise client is different** — Workday uses deeply nested XML-like structures with custom fields (`Custom_Req_ID_v3_Final`), SmartRecruiters uses cryptic codes (`sr_cnd_ext_ref_001`), Oracle exports relational CSVs with foreign keys
- **Schema drift is constant** — enterprise ATS vendors push updates, clients add custom fields, and integrations silently break
- **The Palantir model doesn't scale** — Forward Deployed Engineers are expensive ($300K+/yr), scarce, and create human bottlenecks. Fairshot cannot embed an FDE at every enterprise client

**The Virtual FDE replaces the human FDE with an autonomous agent pipeline** that performs schema exploration, semantic mapping, code generation, and validation — with self-healing capabilities when schemas drift.

---

## 3. Product Vision & Demo Scope

### What the Demo IS

A **working multi-agent system** that:
1. Takes a mock ATS schema (simulating real enterprise messiness)
2. Autonomously explores and catalogs every field, type, and relationship
3. Semantically maps fields to Fairshot's target API spec using LLM reasoning
4. Generates Python middleware (transformation functions) with confidence scores
5. Cross-validates generated code with a second LLM (Gemini) for correctness
6. Runs a live data flow — transforming a mock candidate record end-to-end
7. Detects and auto-repairs schema drift mid-demo

### What the Demo is NOT

- **Not production-ready** — no auth, rate limiting, retry logic, or monitoring
- **Not connected to real ATS APIs** — uses local mock schemas
- **Not replacing Fairshot's core assessment engine** — focuses solely on the integration/onboarding layer
- **Not a general-purpose ETL tool** — purpose-built for ATS→Fairshot mapping

---

## 4. System Architecture

### 4.1 Tech Stack

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| Language | Python 3.11+ | Agent SDK support, rapid prototyping |
| Agent Framework | OpenAI Agents SDK (`openai-agents-python`) | Manager/Orchestrator pattern, structured outputs |
| Primary LLM | OpenAI GPT-4o | Schema analysis, semantic mapping, code generation |
| Validation LLM | Gemini 2.5 Pro (via LiteLLM) | Independent cross-validation of mappings and code |
| Frontend | Streamlit | Rapid dashboard with real-time streaming |
| Mock ATS | Local JSON/YAML files | Simulates messy enterprise schemas |
| Data Models | Pydantic v2 | Structured agent outputs, validation |

### 4.2 Multi-Agent Architecture

```
┌─────────────────────────────────────────┐
│       Deployment Orchestrator           │
│       (Supervisor / Manager Agent)      │
│       Model: GPT-4o                     │
├─────────────────────────────────────────┤
│  Orchestrates the full pipeline:        │
│  1. Triggers Schema Explorer            │
│  2. Feeds results to Semantic Mapper    │
│  3. Sends mapping to Code Generator     │
│  4. Runs validation loop                │
│  5. Monitors for schema drift           │
└──────┬──────────────┬──────────┬────────┘
       │              │          │
  ┌────▼────┐   ┌─────▼────┐  ┌─▼────────────┐
  │ Schema  │   │ Semantic │  │  Code Gen     │
  │Explorer │   │  Mapper  │  │ & Validator   │
  │(Worker) │   │ (Worker) │  │  (Worker)     │
  │ GPT-4o  │   │  GPT-4o  │  │ GPT-4o +     │
  │         │   │          │  │ Gemini verify │
  └─────────┘   └──────────┘  └──────────────┘
```

### 4.3 Agent Roles

#### Agent 1: Deployment Orchestrator (Supervisor)

- **Role:** Central manager agent. Ingests mock ATS schema path, delegates to workers sequentially, maintains pipeline state, and handles error recovery.
- **Pattern:** Modeled after `FinancialResearchManager` in the OpenAI Agents SDK — uses the **agents-as-tools** pattern where each worker agent is registered as a tool the orchestrator can call.
- **Model:** GPT-4o
- **Inputs:** Mock ATS schema file path, Fairshot API spec path
- **Outputs:** `PipelineState` with all artifacts (SchemaReport, MappingDocument, generated middleware, ValidationResult)
- **Responsibilities:**
  - Sequence the pipeline: explore → map → generate → validate
  - Pass structured outputs between agents
  - Detect failures and trigger retries
  - Manage the schema drift detection loop
  - Emit real-time status updates for the dashboard

#### Agent 2: Schema Explorer (Worker)

- **Role:** Autonomously crawls a mock ATS schema, discovering all fields, data types, relationships, nesting structures, and naming conventions.
- **Model:** GPT-4o
- **Tools:**
  - `read_schema_file(path: str) -> dict` — reads and parses a JSON/YAML/CSV schema file
  - `list_endpoints(schema: dict) -> list[str]` — enumerates all available endpoints/tables
  - `inspect_field(field_path: str) -> ATSField` — gets detailed info on a single field
- **Inputs:** File path to mock ATS schema
- **Outputs:** `SchemaReport` (Pydantic model)
- **Behavior:**
  1. Load the schema file
  2. Enumerate all top-level endpoints/entities
  3. For each endpoint, recursively discover all fields with types and sample values
  4. Identify relationships between entities (foreign keys, nested refs)
  5. Flag naming conventions and anomalies (e.g., `_v3_Final` suffixes, mixed date formats)
  6. Output a structured `SchemaReport`

#### Agent 3: Semantic Mapper (Worker)

- **Role:** Takes the SchemaReport + Fairshot's target API spec and produces a deterministic field-by-field mapping with confidence scores and reasoning.
- **Model:** GPT-4o
- **Tools:**
  - `load_fairshot_spec(path: str) -> dict` — reads the Fairshot API spec
  - `compute_similarity(ats_field: str, fairshot_field: str) -> float` — semantic similarity score
  - `lookup_field_context(field_name: str, schema: SchemaReport) -> str` — gets contextual info about a field
- **Inputs:** `SchemaReport`, Fairshot API spec path
- **Outputs:** `MappingDocument` (Pydantic model)
- **Behavior:**
  1. Load Fairshot API spec
  2. For each Fairshot target field, search the SchemaReport for the best matching ATS field
  3. Assign confidence scores: `high` (>0.9), `medium` (0.7–0.9), `low` (<0.7)
  4. For ambiguous mappings, provide reasoning and alternative candidates
  5. Flag unmappable fields (no reasonable ATS equivalent)
  6. Output a structured `MappingDocument`

#### Agent 4: Code Generator & Validator (Worker)

- **Role:** Takes the MappingDocument and generates working Python middleware. Then uses Gemini as a cross-validator to review the code for correctness, edge cases, and data loss risks.
- **Models:** GPT-4o (generation) + Gemini 2.5 Pro (validation)
- **Tools:**
  - `generate_transform_function(mapping: FieldMapping) -> str` — generates a Python transform function for a single field mapping
  - `assemble_middleware(functions: list[str]) -> str` — assembles individual transforms into a complete middleware module
  - `validate_with_gemini(code: str, mapping: MappingDocument) -> ValidationResult` — sends generated code + mapping context to Gemini for independent review
  - `run_test_transform(middleware: str, sample_input: dict) -> dict` — executes the generated middleware against a sample record
- **Inputs:** `MappingDocument`, sample ATS record
- **Outputs:** Generated `middleware.py` content + `ValidationResult`
- **Behavior:**
  1. For each field mapping, generate a Python transformation function
  2. Handle type conversions, date format normalization, nested field extraction
  3. Assemble into a complete middleware module with a `transform(record: dict) -> dict` entry point
  4. Send to Gemini for cross-validation — Gemini reviews for:
     - Correctness of field mappings
     - Edge cases (nulls, empty strings, unexpected types)
     - Data loss risks
     - Code quality
  5. If Gemini flags issues, revise and re-validate (max 2 iterations)
  6. Output final middleware + validation report

### 4.4 Dual-LLM Strategy

| Aspect | OpenAI GPT-4o | Gemini 2.5 Pro |
|--------|--------------|----------------|
| Role | Primary reasoning engine | Independent cross-validator |
| Used by | All 4 agents | Code Generator agent only |
| Tasks | Schema analysis, semantic mapping, code generation, orchestration | Code review, mapping verification, edge case detection |
| Integration | Native via OpenAI Agents SDK | Via LiteLLM provider adapter |

**Why dual-LLM matters for the pitch:**
- **Anti-fragility:** No single-model dependency — if one model hallucinates, the other catches it
- **Mirrors real engineering:** Two sets of eyes on every critical output (code review culture)
- **Speaks to Mattia:** This is how Palantir builds fault-tolerant systems — redundancy at every layer

---

## 5. Demo Flow (What the Audience Sees)

### Step 1 — Input (5 seconds)
User selects a mock ATS schema from a dropdown (Workday Enterprise, SmartRecruiters Lite, or Legacy Oracle). The dashboard displays the raw schema preview — visibly messy, deeply nested, with cryptic field names.

**Visual:** Schema file preview panel, "Start Integration" button.

### Step 2 — Schema Exploration (10 seconds)
The Schema Explorer agent activates. The dashboard shows:
- A live log of discovered endpoints and fields streaming in
- A tree visualization of the schema structure building in real-time
- Field count, nesting depth, and anomaly flags appearing progressively
- Final output: structured SchemaReport summary card

**Visual:** Animated tree view, live scrolling log, summary stats.

### Step 3 — Semantic Mapping (15 seconds)
The Semantic Mapper agent activates. The dashboard shows:
- Side-by-side panel: ATS fields (left) → Fairshot fields (right)
- Mapping lines drawn between fields as they're resolved
- Color-coded confidence: 🟢 green (high), 🟡 yellow (medium), 🔴 red (unmappable)
- Reasoning tooltips on hover for each mapping
- Confidence score distribution chart

**Visual:** Interactive mapping diagram, confidence heatmap.

### Step 4 — Code Generation + Cross-Validation (10 seconds)
The Code Generator agent activates. The dashboard shows:
- Generated Python code appearing in a syntax-highlighted code panel
- Gemini validation results appearing alongside:
  - ✅ Approved transforms
  - ⚠️ Flagged edge cases (with Gemini's suggested fixes)
  - Status: "Cross-validated by Gemini 2.5 Pro"
- Final middleware ready indicator

**Visual:** Split code panel (generated code left, Gemini review right).

### Step 5 — Live Data Flow (10 seconds)
A mock candidate record flows through the generated middleware:
- **Input panel:** Raw ATS record (messy format) — e.g., `{"Custom_Req_ID_v3_Final": "REQ-2024-0847", "cand_nm_first": "Jane", ...}`
- **Transformation panel:** Each transform function fires, showing field-by-field conversion
- **Output panel:** Clean Fairshot API payload — e.g., `{"job_id": "REQ-2024-0847", "first_name": "Jane", ...}`
- Visual confirmation: "✅ 47/50 fields mapped — 0 data loss — Ready for deployment"

**Visual:** Three-panel data flow with animated arrows.

### Step 6 — Schema Drift Simulation (15 seconds) ⚡ WOW MOMENT
Mid-demo, the presenter triggers a "schema update":
- A field is renamed (`Custom_Req_ID_v3_Final` → `Requisition_Reference_ID`)
- A new required field appears (`compliance_region`)
- A field type changes (date format `MM/DD/YYYY` → ISO 8601)

The system responds:
1. **Detection:** Dashboard flashes "⚠️ Schema Drift Detected — 3 breaking changes"
2. **Analysis:** Shows diff between old and new schema
3. **Auto-Repair:** Agents re-map affected fields, regenerate middleware, re-validate
4. **Confirmation:** "✅ Schema drift resolved — 0 manual intervention required"

**Visual:** Red alert → diff view → auto-repair animation → green confirmation.

### Total Demo Time: ~65 seconds (with pauses for narration)

---

## 6. Data Models

All models use Pydantic v2 with strict validation.

### 6.1 ATS Schema Models

```python
# src/models/ats_schema.py

from pydantic import BaseModel, Field
from typing import Optional, Any
from enum import Enum

class FieldType(str, Enum):
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"
    OBJECT = "object"
    ARRAY = "array"
    UNKNOWN = "unknown"

class ATSField(BaseModel):
    """Represents a single field discovered in an ATS schema."""
    name: str = Field(description="Raw field name as it appears in the ATS")
    field_type: FieldType = Field(description="Detected data type")
    nullable: bool = Field(default=True, description="Whether the field can be null")
    sample_value: Optional[Any] = Field(default=None, description="Example value from mock data")
    nested_path: str = Field(description="Dot-notation path to this field (e.g., 'candidate.address.city')")
    description: Optional[str] = Field(default=None, description="Inferred description of what this field contains")
    anomalies: list[str] = Field(default_factory=list, description="Detected naming/format anomalies")

class EntityRelationship(BaseModel):
    """Represents a relationship between two entities in the ATS schema."""
    source_entity: str
    source_field: str
    target_entity: str
    target_field: str
    relationship_type: str = Field(description="e.g., 'foreign_key', 'nested_ref', 'lookup'")

class SchemaReport(BaseModel):
    """Complete report from the Schema Explorer agent."""
    ats_name: str = Field(description="Name of the ATS system (e.g., 'Workday Enterprise')")
    endpoints: list[str] = Field(description="Discovered API endpoints or table names")
    fields: list[ATSField] = Field(description="All discovered fields across all endpoints")
    relationships: list[EntityRelationship] = Field(default_factory=list)
    total_field_count: int
    nesting_depth: int = Field(description="Maximum nesting depth observed")
    custom_conventions: list[str] = Field(
        default_factory=list,
        description="Detected naming conventions (e.g., '_v3_Final suffix pattern')"
    )
    anomaly_summary: str = Field(default="", description="Human-readable summary of schema oddities")
```

### 6.2 Mapping Models

```python
# src/models/mapping.py

from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum

class Confidence(str, Enum):
    HIGH = "high"      # > 0.9
    MEDIUM = "medium"  # 0.7 - 0.9
    LOW = "low"        # < 0.7

class FieldMapping(BaseModel):
    """A single field mapping from ATS to Fairshot."""
    ats_field: str = Field(description="Source field path in ATS schema")
    fairshot_field: str = Field(description="Target field in Fairshot API")
    transform_function: str = Field(description="Name of the Python transform function to apply")
    confidence: Confidence
    confidence_score: float = Field(ge=0.0, le=1.0)
    reasoning: str = Field(description="Why this mapping was chosen")
    alternatives: list[str] = Field(
        default_factory=list,
        description="Alternative ATS fields that could also map here"
    )

class MappingDocument(BaseModel):
    """Complete mapping output from the Semantic Mapper agent."""
    ats_name: str
    fairshot_api_version: str = "v1"
    mappings: list[FieldMapping]
    unmapped_ats_fields: list[str] = Field(
        default_factory=list,
        description="ATS fields with no Fairshot equivalent"
    )
    unmapped_fairshot_fields: list[str] = Field(
        default_factory=list,
        description="Fairshot fields with no ATS source"
    )
    warnings: list[str] = Field(default_factory=list)
    overall_confidence: float = Field(description="Average confidence across all mappings")
    mapping_coverage: float = Field(description="Percentage of Fairshot fields successfully mapped")
```

### 6.3 Validation Models

```python
# src/models/validation.py

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
```

### 6.4 Pipeline Models

```python
# src/models/pipeline.py

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
```

---

## 7. Mock ATS Schemas

### 7.1 Workday Enterprise (`src/mock_data/workday_schema.json`)

Simulates a large enterprise Workday instance with maximum messiness.

**Characteristics:**
- Deeply nested structure (4+ levels)
- Custom field suffixes: `_v3_Final`, `_LEGACY`, `_DO_NOT_USE`
- Mixed date formats: `MM/DD/YYYY`, `YYYY-MM-DD`, epoch timestamps
- Redundant fields (e.g., `candidate_name` AND `cand_full_nm` AND `applicant_display_name`)
- 50+ fields across 3 entities

**Entities:**
- `job_requisitions` — job postings with custom fields
- `candidates` — applicant profiles with nested address/education/experience
- `applications` — linking candidates to requisitions with status workflows

**Sample fields (candidates entity):**
```json
{
  "WD_Candidate_Profile": {
    "cand_nm_first": "Jane",
    "cand_nm_last": "Doe",
    "cand_email_primary_v3_Final": "jane.doe@email.com",
    "cand_phone_mobile_INTL": "+1-555-0123",
    "Custom_Diversity_Flag_DO_NOT_USE": null,
    "address_block": {
      "addr_line1": "123 Main St",
      "addr_city_nm": "San Francisco",
      "addr_state_province": "CA",
      "addr_postal_cd": "94105",
      "addr_country_iso": "US"
    },
    "education_history": [
      {
        "edu_institution_nm": "Stanford University",
        "edu_degree_type_cd": "MS",
        "edu_field_of_study": "Computer Science",
        "edu_graduation_dt": "06/15/2020"
      }
    ],
    "work_experience_LEGACY": [
      {
        "exp_company_nm": "Palantir Technologies",
        "exp_title": "Forward Deployed Engineer",
        "exp_start_dt": 1483228800,
        "exp_end_dt": 1704067200,
        "exp_description_txt": "Led enterprise integrations..."
      }
    ],
    "Custom_Req_ID_v3_Final": "REQ-2024-0847",
    "application_status_cd": "ACTIVE_REVIEW",
    "last_modified_ts": "2024-11-15T14:30:00Z",
    "internal_candidate_flag": false,
    "source_channel_cd": "LINKEDIN_APPLY",
    "recruiter_assigned_id": "EMP-00234",
    "screening_score_v2": 87.5,
    "notes_txt_DEPRECATED": ""
  }
}
```

### 7.2 SmartRecruiters Lite (`src/mock_data/smartrecruiters_schema.json`)

Simulates a modern but cryptically-coded ATS.

**Characteristics:**
- Flat JSON structure (minimal nesting)
- Cryptic field codes: `sr_cnd_ext_ref_001`, `sr_job_loc_geo_lat`
- Consistent but opaque naming convention
- 35+ fields across 2 entities
- Enum values as numeric codes (status: 1, 2, 3 instead of names)

**Entities:**
- `sr_candidates` — flat candidate records
- `sr_job_postings` — job listings with location data

### 7.3 Legacy Oracle (`src/mock_data/legacy_oracle_schema.json`)

Simulates a legacy relational database export.

**Characteristics:**
- Relational table structure (not REST API — CSV-style)
- Foreign keys between tables (IDs, not nested objects)
- ALL_CAPS_SNAKE_CASE field names
- VARCHAR length indicators in field names: `CAND_FIRST_NAME_50`
- 40+ fields across 4 tables
- No sample values — just schema definitions

**Tables:**
- `HR_CANDIDATES` — core candidate data
- `HR_APPLICATIONS` — application records (FK to candidates and requisitions)
- `HR_REQUISITIONS` — job requisitions
- `HR_CANDIDATE_EDUCATION` — education history (FK to candidates)

---

## 8. Fairshot Target API Spec

### 8.1 API Overview (`src/mock_data/fairshot_api_spec.json`)

Clean, well-documented REST API that represents Fairshot's ideal data model.

**Base URL:** `https://api.fairshot.ai/v1`

### 8.2 Endpoints

#### `POST /api/v1/candidates`

Create or update a candidate profile.

```json
{
  "candidate_id": "string (optional — auto-generated if omitted)",
  "first_name": "string (required)",
  "last_name": "string (required)",
  "email": "string (required, valid email)",
  "phone": "string (optional, E.164 format)",
  "location": {
    "city": "string",
    "state": "string",
    "country": "string (ISO 3166-1 alpha-2)",
    "postal_code": "string"
  },
  "education": [
    {
      "institution": "string",
      "degree": "string (enum: BS, BA, MS, MBA, PhD, Other)",
      "field_of_study": "string",
      "graduation_date": "string (ISO 8601 date)"
    }
  ],
  "experience": [
    {
      "company": "string",
      "title": "string",
      "start_date": "string (ISO 8601 date)",
      "end_date": "string (ISO 8601 date, nullable)",
      "description": "string"
    }
  ],
  "source_channel": "string (enum: linkedin, indeed, referral, direct, other)",
  "tags": ["string"],
  "metadata": {}
}
```

#### `POST /api/v1/simulations`

Schedule an AI case simulation for a candidate.

```json
{
  "simulation_id": "string (optional — auto-generated)",
  "candidate_id": "string (required)",
  "job_id": "string (required)",
  "simulation_type": "string (enum: case_study, technical, behavioral, mixed)",
  "difficulty_level": "string (enum: junior, mid, senior, executive)",
  "scheduled_at": "string (ISO 8601 datetime, required)",
  "duration_minutes": "integer (default: 60)",
  "language": "string (default: 'en')",
  "custom_parameters": {}
}
```

#### `GET /api/v1/requisitions/{id}`

Retrieve job requisition details.

```json
{
  "job_id": "string",
  "title": "string",
  "department": "string",
  "hiring_manager": "string",
  "location": {
    "city": "string",
    "state": "string",
    "country": "string"
  },
  "employment_type": "string (enum: full_time, part_time, contract, intern)",
  "seniority_level": "string (enum: junior, mid, senior, executive)",
  "required_skills": ["string"],
  "description": "string",
  "status": "string (enum: open, closed, on_hold, filled)",
  "created_at": "string (ISO 8601 datetime)",
  "updated_at": "string (ISO 8601 datetime)"
}
```

#### `GET /api/v1/health`

Health check endpoint for integration validation.

```json
{
  "status": "ok",
  "version": "1.0.0",
  "timestamp": "string (ISO 8601 datetime)"
}
```

---

## 9. Implementation Phases

Each phase is self-contained. Gemini should implement one phase at a time, commit, and wait for review before proceeding.

---

### Phase 1: Foundation — DETAILED SPEC

**Goal:** Project scaffold, data models, mock data files, basic app skeleton.

**Dependencies:** None (first phase)

---

#### 1.1 Project Setup

Create the following files at the project root:

**`requirements.txt`**
```
openai-agents>=0.1.0
openai>=1.60.0
google-genai>=1.0.0
litellm>=1.55.0
pydantic>=2.0.0
streamlit>=1.40.0
python-dotenv>=1.0.0
pytest>=8.0.0
pytest-asyncio>=0.24.0
jinja2>=3.1.0
diskcache>=5.6.0
```

**`.env.example`**
```bash
OPENAI_API_KEY=sk-your-openai-key-here
GOOGLE_API_KEY=your-gemini-api-key-here
OPENAI_MODEL=gpt-4o
GEMINI_MODEL=gemini-2.5-pro
LOG_LEVEL=INFO
```

**`.gitignore`** (add if not present, or append these entries)
```
.env
__pycache__/
*.pyc
.pytest_cache/
src/middleware/*.py
!src/middleware/.gitkeep
.streamlit/
```

---

#### 1.2 Folder Structure

Create all directories and `__init__.py` files. Every `__init__.py` should be empty except where specified below.

```
src/__init__.py
src/models/__init__.py          # see 1.3 for exports
src/agents/__init__.py
src/mock_data/                  # no __init__.py — data only
src/middleware/.gitkeep
src/utils/__init__.py
app/__init__.py
tests/__init__.py
```

---

#### 1.3 Pydantic Data Models

Implement exactly as shown in Section 6 of this PRD. Copy the code verbatim — the models are already fully specified with types, defaults, and docstrings.

**`src/models/__init__.py`** — re-export all public models:
```python
from .ats_schema import FieldType, ATSField, EntityRelationship, SchemaReport
from .mapping import Confidence, FieldMapping, MappingDocument
from .validation import Severity, ValidationIssue, ValidationResult
from .pipeline import PipelineStage, LogEntry, PipelineState
```

**Files to create (copy directly from Section 6):**
| File | Models | Section |
|------|--------|---------|
| `src/models/ats_schema.py` | `FieldType`, `ATSField`, `EntityRelationship`, `SchemaReport` | 6.1 |
| `src/models/mapping.py` | `Confidence`, `FieldMapping`, `MappingDocument` | 6.2 |
| `src/models/validation.py` | `Severity`, `ValidationIssue`, `ValidationResult` | 6.3 |
| `src/models/pipeline.py` | `PipelineStage`, `LogEntry`, `PipelineState` | 6.4 |

---

#### 1.4 Mock ATS Schemas

Create 3 JSON files in `src/mock_data/`. These must be realistic, messy, and large enough to demonstrate the system's capabilities. Each schema follows a consistent top-level structure:

```json
{
  "ats_name": "string",
  "ats_version": "string",
  "entities": {
    "entity_name": {
      "description": "string",
      "fields": { ... },
      "sample_records": [ ... ]
    }
  }
}
```

##### `src/mock_data/workday_schema.json`

Deeply nested, 50+ fields, maximum messiness. 3 entities, 2 sample records per entity.

```json
{
  "ats_name": "Workday Enterprise HCM",
  "ats_version": "2024.R2.3.1-patch4",
  "api_base": "/ccx/api/v1",
  "auth_type": "OAuth2_SAML",
  "entities": {
    "WD_Candidate_Profile": {
      "endpoint": "/ccx/api/v1/recruiting/candidates",
      "description": "Core candidate identity and application data",
      "fields": {
        "cand_nm_first": { "type": "string", "nullable": false, "max_length": 100 },
        "cand_nm_last": { "type": "string", "nullable": false, "max_length": 100 },
        "cand_nm_middle_initial": { "type": "string", "nullable": true, "max_length": 1 },
        "cand_email_primary_v3_Final": { "type": "string", "nullable": false, "format": "email" },
        "cand_email_secondary_DEPRECATED": { "type": "string", "nullable": true, "format": "email" },
        "cand_phone_mobile_INTL": { "type": "string", "nullable": true, "format": "phone_intl" },
        "cand_phone_home_LEGACY": { "type": "string", "nullable": true },
        "Custom_Diversity_Flag_DO_NOT_USE": { "type": "boolean", "nullable": true },
        "cand_gender_cd": { "type": "string", "nullable": true, "enum": ["M", "F", "NB", "NS"] },
        "cand_dob_dt": { "type": "string", "nullable": true, "format": "MM/DD/YYYY" },
        "internal_candidate_flag": { "type": "boolean", "nullable": false, "default": false },
        "source_channel_cd": { "type": "string", "nullable": true, "enum": ["LINKEDIN_APPLY", "INDEED", "REFERRAL_INTERNAL", "CAREERS_PAGE", "AGENCY_EXT", "OTHER"] },
        "recruiter_assigned_id": { "type": "string", "nullable": true, "format": "EMP-NNNNN" },
        "screening_score_v2": { "type": "float", "nullable": true, "min": 0, "max": 100 },
        "notes_txt_DEPRECATED": { "type": "string", "nullable": true },
        "last_modified_ts": { "type": "string", "nullable": false, "format": "ISO8601" },
        "cand_profile_url_txt": { "type": "string", "nullable": true, "format": "url" },
        "cand_resume_blob_id": { "type": "string", "nullable": true },
        "address_block": {
          "type": "object",
          "fields": {
            "addr_line1": { "type": "string", "nullable": false },
            "addr_line2_v2": { "type": "string", "nullable": true },
            "addr_city_nm": { "type": "string", "nullable": false },
            "addr_state_province": { "type": "string", "nullable": false },
            "addr_postal_cd": { "type": "string", "nullable": false },
            "addr_country_iso": { "type": "string", "nullable": false, "format": "ISO3166-alpha2" }
          }
        },
        "education_history": {
          "type": "array",
          "items": {
            "type": "object",
            "fields": {
              "edu_institution_nm": { "type": "string", "nullable": false },
              "edu_degree_type_cd": { "type": "string", "nullable": false, "enum": ["HS", "AS", "BS", "BA", "MS", "MBA", "PhD", "JD", "MD", "Other"] },
              "edu_field_of_study": { "type": "string", "nullable": true },
              "edu_graduation_dt": { "type": "string", "nullable": true, "format": "MM/DD/YYYY" },
              "edu_gpa_val_LEGACY": { "type": "float", "nullable": true }
            }
          }
        },
        "work_experience_LEGACY": {
          "type": "array",
          "items": {
            "type": "object",
            "fields": {
              "exp_company_nm": { "type": "string", "nullable": false },
              "exp_title": { "type": "string", "nullable": false },
              "exp_start_dt": { "type": "integer", "nullable": false, "format": "epoch_seconds" },
              "exp_end_dt": { "type": "integer", "nullable": true, "format": "epoch_seconds" },
              "exp_description_txt": { "type": "string", "nullable": true },
              "exp_location_cd": { "type": "string", "nullable": true }
            }
          }
        },
        "Custom_Req_ID_v3_Final": { "type": "string", "nullable": false, "format": "REQ-YYYY-NNNN" },
        "application_status_cd": { "type": "string", "nullable": false, "enum": ["NEW", "SCREENING", "ACTIVE_REVIEW", "INTERVIEW_SCHEDULED", "OFFER_EXTENDED", "HIRED", "REJECTED", "WITHDRAWN"] },
        "application_submitted_dt": { "type": "string", "nullable": false, "format": "MM/DD/YYYY" },
        "cand_preferred_lang_cd": { "type": "string", "nullable": true, "format": "ISO639-1" },
        "cand_timezone_v2_Final": { "type": "string", "nullable": true, "format": "IANA_timezone" },
        "cand_skills_tags_txt": { "type": "string", "nullable": true, "format": "semicolon_delimited" }
      },
      "sample_records": [
        {
          "cand_nm_first": "Jane",
          "cand_nm_last": "Doe",
          "cand_nm_middle_initial": "M",
          "cand_email_primary_v3_Final": "jane.doe@email.com",
          "cand_email_secondary_DEPRECATED": null,
          "cand_phone_mobile_INTL": "+1-555-0123",
          "cand_phone_home_LEGACY": null,
          "Custom_Diversity_Flag_DO_NOT_USE": null,
          "cand_gender_cd": "F",
          "cand_dob_dt": "03/15/1992",
          "internal_candidate_flag": false,
          "source_channel_cd": "LINKEDIN_APPLY",
          "recruiter_assigned_id": "EMP-00234",
          "screening_score_v2": 87.5,
          "notes_txt_DEPRECATED": "",
          "last_modified_ts": "2024-11-15T14:30:00Z",
          "cand_profile_url_txt": "https://linkedin.com/in/janedoe",
          "cand_resume_blob_id": "blob-9f8e7d6c",
          "address_block": {
            "addr_line1": "123 Main St",
            "addr_line2_v2": "Apt 4B",
            "addr_city_nm": "San Francisco",
            "addr_state_province": "CA",
            "addr_postal_cd": "94105",
            "addr_country_iso": "US"
          },
          "education_history": [
            {
              "edu_institution_nm": "Stanford University",
              "edu_degree_type_cd": "MS",
              "edu_field_of_study": "Computer Science",
              "edu_graduation_dt": "06/15/2020",
              "edu_gpa_val_LEGACY": 3.92
            }
          ],
          "work_experience_LEGACY": [
            {
              "exp_company_nm": "Palantir Technologies",
              "exp_title": "Forward Deployed Engineer",
              "exp_start_dt": 1483228800,
              "exp_end_dt": 1704067200,
              "exp_description_txt": "Led enterprise integrations for Fortune 500 clients across healthcare and financial services verticals.",
              "exp_location_cd": "NYC"
            },
            {
              "exp_company_nm": "Google",
              "exp_title": "Software Engineer III",
              "exp_start_dt": 1704067200,
              "exp_end_dt": null,
              "exp_description_txt": "Cloud infrastructure team, Kubernetes optimization.",
              "exp_location_cd": "MTV"
            }
          ],
          "Custom_Req_ID_v3_Final": "REQ-2024-0847",
          "application_status_cd": "ACTIVE_REVIEW",
          "application_submitted_dt": "10/28/2024",
          "cand_preferred_lang_cd": "en",
          "cand_timezone_v2_Final": "America/Los_Angeles",
          "cand_skills_tags_txt": "Python;Kubernetes;Data Integration;SQL;System Design"
        },
        {
          "cand_nm_first": "Marco",
          "cand_nm_last": "Bianchi",
          "cand_nm_middle_initial": null,
          "cand_email_primary_v3_Final": "m.bianchi@proton.me",
          "cand_email_secondary_DEPRECATED": "marco.b@oldmail.com",
          "cand_phone_mobile_INTL": "+39-02-1234567",
          "cand_phone_home_LEGACY": "+39-02-7654321",
          "Custom_Diversity_Flag_DO_NOT_USE": null,
          "cand_gender_cd": "M",
          "cand_dob_dt": "11/02/1988",
          "internal_candidate_flag": false,
          "source_channel_cd": "REFERRAL_INTERNAL",
          "recruiter_assigned_id": "EMP-00891",
          "screening_score_v2": 72.0,
          "notes_txt_DEPRECATED": "Referred by VP of Engineering",
          "last_modified_ts": "2024-12-01T09:15:00Z",
          "cand_profile_url_txt": null,
          "cand_resume_blob_id": "blob-1a2b3c4d",
          "address_block": {
            "addr_line1": "Via Roma 42",
            "addr_line2_v2": null,
            "addr_city_nm": "Milano",
            "addr_state_province": "MI",
            "addr_postal_cd": "20121",
            "addr_country_iso": "IT"
          },
          "education_history": [
            {
              "edu_institution_nm": "Università Bocconi",
              "edu_degree_type_cd": "MBA",
              "edu_field_of_study": "Finance & Technology",
              "edu_graduation_dt": "07/20/2015",
              "edu_gpa_val_LEGACY": null
            }
          ],
          "work_experience_LEGACY": [
            {
              "exp_company_nm": "McKinsey & Company",
              "exp_title": "Associate",
              "exp_start_dt": 1438387200,
              "exp_end_dt": 1577836800,
              "exp_description_txt": "Strategy consulting for financial services clients across EMEA.",
              "exp_location_cd": "MIL"
            }
          ],
          "Custom_Req_ID_v3_Final": "REQ-2024-1203",
          "application_status_cd": "SCREENING",
          "application_submitted_dt": "11/28/2024",
          "cand_preferred_lang_cd": "it",
          "cand_timezone_v2_Final": "Europe/Rome",
          "cand_skills_tags_txt": "Financial Modeling;Strategy;M&A;Due Diligence"
        }
      ]
    },
    "WD_Job_Requisition": {
      "endpoint": "/ccx/api/v1/recruiting/requisitions",
      "description": "Job requisition definitions with approval workflows",
      "fields": {
        "Custom_Req_ID_v3_Final": { "type": "string", "nullable": false, "format": "REQ-YYYY-NNNN" },
        "req_title_txt": { "type": "string", "nullable": false },
        "req_department_cd": { "type": "string", "nullable": false },
        "req_hiring_mgr_id": { "type": "string", "nullable": false, "format": "EMP-NNNNN" },
        "req_location_primary": {
          "type": "object",
          "fields": {
            "loc_city_nm": { "type": "string", "nullable": false },
            "loc_state_province": { "type": "string", "nullable": true },
            "loc_country_iso": { "type": "string", "nullable": false, "format": "ISO3166-alpha2" }
          }
        },
        "req_employment_type_cd": { "type": "string", "nullable": false, "enum": ["FT", "PT", "CT", "IN"] },
        "req_seniority_band_cd": { "type": "string", "nullable": false, "enum": ["IC1", "IC2", "IC3", "IC4", "MGR1", "MGR2", "DIR", "VP", "EXEC"] },
        "req_skills_required_txt": { "type": "string", "nullable": true, "format": "semicolon_delimited" },
        "req_description_html": { "type": "string", "nullable": true, "format": "html" },
        "req_status_cd": { "type": "string", "nullable": false, "enum": ["DRAFT", "OPEN", "ON_HOLD", "FILLED", "CANCELLED"] },
        "req_created_dt": { "type": "string", "nullable": false, "format": "YYYY-MM-DD" },
        "req_updated_ts": { "type": "string", "nullable": false, "format": "ISO8601" },
        "req_headcount_approved_v2": { "type": "integer", "nullable": false, "default": 1 },
        "req_comp_range_min_LEGACY": { "type": "float", "nullable": true },
        "req_comp_range_max_LEGACY": { "type": "float", "nullable": true },
        "req_comp_currency_cd": { "type": "string", "nullable": true, "format": "ISO4217" }
      },
      "sample_records": [
        {
          "Custom_Req_ID_v3_Final": "REQ-2024-0847",
          "req_title_txt": "Senior Forward Deployed Engineer",
          "req_department_cd": "ENG-PLATFORM",
          "req_hiring_mgr_id": "EMP-00102",
          "req_location_primary": {
            "loc_city_nm": "New York",
            "loc_state_province": "NY",
            "loc_country_iso": "US"
          },
          "req_employment_type_cd": "FT",
          "req_seniority_band_cd": "IC3",
          "req_skills_required_txt": "Python;Data Integration;System Design;SQL;Kubernetes",
          "req_description_html": "<p>Join our platform team to lead enterprise integrations...</p>",
          "req_status_cd": "OPEN",
          "req_created_dt": "2024-09-15",
          "req_updated_ts": "2024-11-15T14:30:00Z",
          "req_headcount_approved_v2": 2,
          "req_comp_range_min_LEGACY": 180000.00,
          "req_comp_range_max_LEGACY": 260000.00,
          "req_comp_currency_cd": "USD"
        },
        {
          "Custom_Req_ID_v3_Final": "REQ-2024-1203",
          "req_title_txt": "Strategy & Operations Manager",
          "req_department_cd": "BIZ-OPS",
          "req_hiring_mgr_id": "EMP-00045",
          "req_location_primary": {
            "loc_city_nm": "London",
            "loc_state_province": null,
            "loc_country_iso": "GB"
          },
          "req_employment_type_cd": "FT",
          "req_seniority_band_cd": "MGR1",
          "req_skills_required_txt": "Strategy;Financial Modeling;Stakeholder Management",
          "req_description_html": "<p>Drive operational excellence across our EMEA expansion...</p>",
          "req_status_cd": "OPEN",
          "req_created_dt": "2024-11-01",
          "req_updated_ts": "2024-12-01T09:00:00Z",
          "req_headcount_approved_v2": 1,
          "req_comp_range_min_LEGACY": 95000.00,
          "req_comp_range_max_LEGACY": 130000.00,
          "req_comp_currency_cd": "GBP"
        }
      ]
    },
    "WD_Application_Workflow": {
      "endpoint": "/ccx/api/v1/recruiting/applications",
      "description": "Links candidates to requisitions with status tracking",
      "fields": {
        "app_id_sys": { "type": "string", "nullable": false, "format": "APP-NNNNNNN" },
        "cand_email_primary_v3_Final": { "type": "string", "nullable": false, "format": "email" },
        "Custom_Req_ID_v3_Final": { "type": "string", "nullable": false, "format": "REQ-YYYY-NNNN" },
        "application_status_cd": { "type": "string", "nullable": false, "enum": ["NEW", "SCREENING", "ACTIVE_REVIEW", "INTERVIEW_SCHEDULED", "OFFER_EXTENDED", "HIRED", "REJECTED", "WITHDRAWN"] },
        "app_submitted_ts": { "type": "string", "nullable": false, "format": "ISO8601" },
        "app_last_action_ts": { "type": "string", "nullable": false, "format": "ISO8601" },
        "app_stage_history_v2": {
          "type": "array",
          "items": {
            "type": "object",
            "fields": {
              "stage_cd": { "type": "string" },
              "entered_ts": { "type": "string", "format": "ISO8601" },
              "exited_ts": { "type": "string", "nullable": true, "format": "ISO8601" }
            }
          }
        },
        "app_rejection_reason_cd_LEGACY": { "type": "string", "nullable": true },
        "app_offer_amount_LEGACY": { "type": "float", "nullable": true }
      },
      "sample_records": [
        {
          "app_id_sys": "APP-0034821",
          "cand_email_primary_v3_Final": "jane.doe@email.com",
          "Custom_Req_ID_v3_Final": "REQ-2024-0847",
          "application_status_cd": "ACTIVE_REVIEW",
          "app_submitted_ts": "2024-10-28T16:45:00Z",
          "app_last_action_ts": "2024-11-15T14:30:00Z",
          "app_stage_history_v2": [
            { "stage_cd": "NEW", "entered_ts": "2024-10-28T16:45:00Z", "exited_ts": "2024-10-29T09:00:00Z" },
            { "stage_cd": "SCREENING", "entered_ts": "2024-10-29T09:00:00Z", "exited_ts": "2024-11-05T11:30:00Z" },
            { "stage_cd": "ACTIVE_REVIEW", "entered_ts": "2024-11-05T11:30:00Z", "exited_ts": null }
          ],
          "app_rejection_reason_cd_LEGACY": null,
          "app_offer_amount_LEGACY": null
        }
      ]
    }
  }
}
```

##### `src/mock_data/smartrecruiters_schema.json`

Flat structure, cryptic codes, numeric enum values. 2 entities, 2 sample records each.

```json
{
  "ats_name": "SmartRecruiters Lite",
  "ats_version": "API-v202401",
  "api_base": "/api/smartrecruiters/v202401",
  "auth_type": "API_KEY_HEADER",
  "entities": {
    "sr_candidates": {
      "endpoint": "/api/smartrecruiters/v202401/candidates",
      "description": "Candidate profiles",
      "fields": {
        "sr_cnd_id": { "type": "string", "nullable": false, "format": "UUID" },
        "sr_cnd_fname": { "type": "string", "nullable": false },
        "sr_cnd_lname": { "type": "string", "nullable": false },
        "sr_cnd_email_01": { "type": "string", "nullable": false },
        "sr_cnd_phone_01": { "type": "string", "nullable": true },
        "sr_cnd_loc_city": { "type": "string", "nullable": true },
        "sr_cnd_loc_region": { "type": "string", "nullable": true },
        "sr_cnd_loc_country_cd": { "type": "string", "nullable": true },
        "sr_cnd_loc_postal": { "type": "string", "nullable": true },
        "sr_cnd_loc_geo_lat": { "type": "float", "nullable": true },
        "sr_cnd_loc_geo_lon": { "type": "float", "nullable": true },
        "sr_cnd_src_cd": { "type": "integer", "nullable": true, "enum_map": { "1": "LinkedIn", "2": "Indeed", "3": "Referral", "4": "Direct", "5": "Agency", "9": "Other" } },
        "sr_cnd_ext_ref_001": { "type": "string", "nullable": true, "description": "External reference ID from client HRIS" },
        "sr_cnd_created_ts": { "type": "string", "nullable": false, "format": "ISO8601" },
        "sr_cnd_updated_ts": { "type": "string", "nullable": false, "format": "ISO8601" },
        "sr_cnd_status_cd": { "type": "integer", "nullable": false, "enum_map": { "0": "Inactive", "1": "Active", "2": "Hired", "3": "Rejected" } },
        "sr_cnd_tags_json": { "type": "string", "nullable": true, "format": "json_array_string" },
        "sr_cnd_resume_url": { "type": "string", "nullable": true },
        "sr_cnd_edu_latest_inst": { "type": "string", "nullable": true },
        "sr_cnd_edu_latest_deg": { "type": "string", "nullable": true },
        "sr_cnd_edu_latest_field": { "type": "string", "nullable": true },
        "sr_cnd_edu_latest_yr": { "type": "integer", "nullable": true },
        "sr_cnd_exp_latest_co": { "type": "string", "nullable": true },
        "sr_cnd_exp_latest_title": { "type": "string", "nullable": true },
        "sr_cnd_exp_yrs_total": { "type": "float", "nullable": true },
        "sr_cnd_lang_pref": { "type": "string", "nullable": true }
      },
      "sample_records": [
        {
          "sr_cnd_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
          "sr_cnd_fname": "Aisha",
          "sr_cnd_lname": "Patel",
          "sr_cnd_email_01": "aisha.patel@techcorp.com",
          "sr_cnd_phone_01": "+44-20-7946-0958",
          "sr_cnd_loc_city": "London",
          "sr_cnd_loc_region": "Greater London",
          "sr_cnd_loc_country_cd": "GB",
          "sr_cnd_loc_postal": "EC2A 1NT",
          "sr_cnd_loc_geo_lat": 51.5225,
          "sr_cnd_loc_geo_lon": -0.0854,
          "sr_cnd_src_cd": 1,
          "sr_cnd_ext_ref_001": "HRIS-UK-44821",
          "sr_cnd_created_ts": "2024-10-05T08:30:00Z",
          "sr_cnd_updated_ts": "2024-11-20T16:45:00Z",
          "sr_cnd_status_cd": 1,
          "sr_cnd_tags_json": "[\"finance\", \"quant\", \"python\"]",
          "sr_cnd_resume_url": "https://storage.sr.io/resumes/a1b2c3d4.pdf",
          "sr_cnd_edu_latest_inst": "Imperial College London",
          "sr_cnd_edu_latest_deg": "MSc",
          "sr_cnd_edu_latest_field": "Financial Mathematics",
          "sr_cnd_edu_latest_yr": 2019,
          "sr_cnd_exp_latest_co": "Goldman Sachs",
          "sr_cnd_exp_latest_title": "VP, Quantitative Strategies",
          "sr_cnd_exp_yrs_total": 5.5,
          "sr_cnd_lang_pref": "en"
        },
        {
          "sr_cnd_id": "f9e8d7c6-b5a4-3210-fedc-ba9876543210",
          "sr_cnd_fname": "Carlos",
          "sr_cnd_lname": "Mendez",
          "sr_cnd_email_01": "carlos.mendez@gmail.com",
          "sr_cnd_phone_01": "+1-212-555-0199",
          "sr_cnd_loc_city": "New York",
          "sr_cnd_loc_region": "NY",
          "sr_cnd_loc_country_cd": "US",
          "sr_cnd_loc_postal": "10001",
          "sr_cnd_loc_geo_lat": 40.7484,
          "sr_cnd_loc_geo_lon": -73.9967,
          "sr_cnd_src_cd": 3,
          "sr_cnd_ext_ref_001": null,
          "sr_cnd_created_ts": "2024-11-12T14:00:00Z",
          "sr_cnd_updated_ts": "2024-11-12T14:00:00Z",
          "sr_cnd_status_cd": 1,
          "sr_cnd_tags_json": "[\"consulting\", \"strategy\"]",
          "sr_cnd_resume_url": null,
          "sr_cnd_edu_latest_inst": "Columbia Business School",
          "sr_cnd_edu_latest_deg": "MBA",
          "sr_cnd_edu_latest_field": "Strategy",
          "sr_cnd_edu_latest_yr": 2021,
          "sr_cnd_exp_latest_co": "Bain & Company",
          "sr_cnd_exp_latest_title": "Senior Associate",
          "sr_cnd_exp_yrs_total": 4.0,
          "sr_cnd_lang_pref": "en"
        }
      ]
    },
    "sr_job_postings": {
      "endpoint": "/api/smartrecruiters/v202401/jobs",
      "description": "Job posting definitions",
      "fields": {
        "sr_job_id": { "type": "string", "nullable": false, "format": "UUID" },
        "sr_job_title": { "type": "string", "nullable": false },
        "sr_job_dept_cd": { "type": "string", "nullable": false },
        "sr_job_hmgr_email": { "type": "string", "nullable": false },
        "sr_job_loc_city": { "type": "string", "nullable": true },
        "sr_job_loc_country_cd": { "type": "string", "nullable": true },
        "sr_job_loc_geo_lat": { "type": "float", "nullable": true },
        "sr_job_loc_geo_lon": { "type": "float", "nullable": true },
        "sr_job_type_cd": { "type": "integer", "nullable": false, "enum_map": { "1": "Full-Time", "2": "Part-Time", "3": "Contract", "4": "Internship" } },
        "sr_job_level_cd": { "type": "integer", "nullable": false, "enum_map": { "1": "Junior", "2": "Mid", "3": "Senior", "4": "Lead", "5": "Director", "6": "VP", "7": "C-Level" } },
        "sr_job_skills_json": { "type": "string", "nullable": true, "format": "json_array_string" },
        "sr_job_desc_html": { "type": "string", "nullable": true },
        "sr_job_status_cd": { "type": "integer", "nullable": false, "enum_map": { "0": "Draft", "1": "Open", "2": "On Hold", "3": "Filled", "4": "Cancelled" } },
        "sr_job_created_ts": { "type": "string", "nullable": false, "format": "ISO8601" },
        "sr_job_updated_ts": { "type": "string", "nullable": false, "format": "ISO8601" }
      },
      "sample_records": [
        {
          "sr_job_id": "job-uuid-1234-5678-abcd",
          "sr_job_title": "Quantitative Analyst",
          "sr_job_dept_cd": "TRADING",
          "sr_job_hmgr_email": "h.manager@firm.com",
          "sr_job_loc_city": "London",
          "sr_job_loc_country_cd": "GB",
          "sr_job_loc_geo_lat": 51.5074,
          "sr_job_loc_geo_lon": -0.1278,
          "sr_job_type_cd": 1,
          "sr_job_level_cd": 3,
          "sr_job_skills_json": "[\"Python\", \"Statistical Modeling\", \"Risk Analysis\"]",
          "sr_job_desc_html": "<p>Seeking a senior quant analyst...</p>",
          "sr_job_status_cd": 1,
          "sr_job_created_ts": "2024-09-20T10:00:00Z",
          "sr_job_updated_ts": "2024-11-01T12:00:00Z"
        }
      ]
    }
  }
}
```

##### `src/mock_data/legacy_oracle_schema.json`

Relational table dumps, ALL_CAPS, foreign keys, no nesting. 4 tables, 2 sample records each.

```json
{
  "ats_name": "Legacy Oracle HRMS",
  "ats_version": "11g_R2_CUSTOM",
  "api_base": null,
  "auth_type": "DB_DIRECT",
  "data_format": "CSV_EXPORT",
  "entities": {
    "HR_CANDIDATES": {
      "endpoint": null,
      "table_name": "HR_CANDIDATES",
      "description": "Core candidate table - exported nightly as CSV",
      "primary_key": "CAND_ID_50",
      "fields": {
        "CAND_ID_50": { "type": "string", "nullable": false, "max_length": 50 },
        "CAND_FIRST_NAME_50": { "type": "string", "nullable": false, "max_length": 50 },
        "CAND_LAST_NAME_50": { "type": "string", "nullable": false, "max_length": 50 },
        "CAND_EMAIL_100": { "type": "string", "nullable": false, "max_length": 100 },
        "CAND_PHONE_20": { "type": "string", "nullable": true, "max_length": 20 },
        "CAND_ADDR_CITY_50": { "type": "string", "nullable": true, "max_length": 50 },
        "CAND_ADDR_STATE_10": { "type": "string", "nullable": true, "max_length": 10 },
        "CAND_ADDR_COUNTRY_5": { "type": "string", "nullable": true, "max_length": 5 },
        "CAND_ADDR_ZIP_10": { "type": "string", "nullable": true, "max_length": 10 },
        "CAND_SOURCE_CD_20": { "type": "string", "nullable": true, "max_length": 20 },
        "CAND_STATUS_CD_10": { "type": "string", "nullable": false, "max_length": 10, "enum": ["NEW", "ACTIVE", "HIRED", "REJECT", "WDRAWN"] },
        "CAND_CREATED_DT": { "type": "string", "nullable": false, "format": "YYYY-MM-DD" },
        "CAND_MODIFIED_DT": { "type": "string", "nullable": false, "format": "YYYY-MM-DD" }
      },
      "sample_records": [
        {
          "CAND_ID_50": "ORA-CAND-000001",
          "CAND_FIRST_NAME_50": "Priya",
          "CAND_LAST_NAME_50": "Sharma",
          "CAND_EMAIL_100": "priya.sharma@outlook.com",
          "CAND_PHONE_20": "+91-98765-43210",
          "CAND_ADDR_CITY_50": "Bangalore",
          "CAND_ADDR_STATE_10": "KA",
          "CAND_ADDR_COUNTRY_5": "IN",
          "CAND_ADDR_ZIP_10": "560001",
          "CAND_SOURCE_CD_20": "NAUKRI",
          "CAND_STATUS_CD_10": "ACTIVE",
          "CAND_CREATED_DT": "2024-08-15",
          "CAND_MODIFIED_DT": "2024-11-30"
        },
        {
          "CAND_ID_50": "ORA-CAND-000002",
          "CAND_FIRST_NAME_50": "David",
          "CAND_LAST_NAME_50": "Kim",
          "CAND_EMAIL_100": "d.kim@samsung.com",
          "CAND_PHONE_20": "+82-10-1234-5678",
          "CAND_ADDR_CITY_50": "Seoul",
          "CAND_ADDR_STATE_10": null,
          "CAND_ADDR_COUNTRY_5": "KR",
          "CAND_ADDR_ZIP_10": "06164",
          "CAND_SOURCE_CD_20": "AGENCY",
          "CAND_STATUS_CD_10": "NEW",
          "CAND_CREATED_DT": "2024-11-20",
          "CAND_MODIFIED_DT": "2024-11-20"
        }
      ]
    },
    "HR_REQUISITIONS": {
      "endpoint": null,
      "table_name": "HR_REQUISITIONS",
      "description": "Job requisitions table",
      "primary_key": "REQ_ID_50",
      "fields": {
        "REQ_ID_50": { "type": "string", "nullable": false, "max_length": 50 },
        "REQ_TITLE_200": { "type": "string", "nullable": false, "max_length": 200 },
        "REQ_DEPT_CD_20": { "type": "string", "nullable": false, "max_length": 20 },
        "REQ_HMGR_ID_50": { "type": "string", "nullable": false, "max_length": 50, "foreign_key": "HR_EMPLOYEES.EMP_ID_50" },
        "REQ_CITY_50": { "type": "string", "nullable": true, "max_length": 50 },
        "REQ_COUNTRY_5": { "type": "string", "nullable": true, "max_length": 5 },
        "REQ_TYPE_CD_5": { "type": "string", "nullable": false, "max_length": 5, "enum": ["FT", "PT", "CT", "INT"] },
        "REQ_LEVEL_CD_10": { "type": "string", "nullable": false, "max_length": 10, "enum": ["JR", "MID", "SR", "LEAD", "DIR", "VP", "EXEC"] },
        "REQ_SKILLS_500": { "type": "string", "nullable": true, "max_length": 500, "format": "comma_delimited" },
        "REQ_DESC_4000": { "type": "string", "nullable": true, "max_length": 4000 },
        "REQ_STATUS_CD_10": { "type": "string", "nullable": false, "max_length": 10, "enum": ["OPEN", "HOLD", "FILLED", "CANCEL"] },
        "REQ_CREATED_DT": { "type": "string", "nullable": false, "format": "YYYY-MM-DD" },
        "REQ_MODIFIED_DT": { "type": "string", "nullable": false, "format": "YYYY-MM-DD" }
      },
      "sample_records": [
        {
          "REQ_ID_50": "ORA-REQ-2024-0001",
          "REQ_TITLE_200": "Senior Data Engineer",
          "REQ_DEPT_CD_20": "ENGINEERING",
          "REQ_HMGR_ID_50": "ORA-EMP-000045",
          "REQ_CITY_50": "Bangalore",
          "REQ_COUNTRY_5": "IN",
          "REQ_TYPE_CD_5": "FT",
          "REQ_LEVEL_CD_10": "SR",
          "REQ_SKILLS_500": "Python,Spark,Airflow,SQL,AWS",
          "REQ_DESC_4000": "Looking for a senior data engineer to lead our data platform team...",
          "REQ_STATUS_CD_10": "OPEN",
          "REQ_CREATED_DT": "2024-10-01",
          "REQ_MODIFIED_DT": "2024-11-15"
        }
      ]
    },
    "HR_APPLICATIONS": {
      "endpoint": null,
      "table_name": "HR_APPLICATIONS",
      "description": "Application records linking candidates to requisitions",
      "primary_key": "APP_ID_50",
      "fields": {
        "APP_ID_50": { "type": "string", "nullable": false, "max_length": 50 },
        "CAND_ID_50": { "type": "string", "nullable": false, "max_length": 50, "foreign_key": "HR_CANDIDATES.CAND_ID_50" },
        "REQ_ID_50": { "type": "string", "nullable": false, "max_length": 50, "foreign_key": "HR_REQUISITIONS.REQ_ID_50" },
        "APP_STATUS_CD_10": { "type": "string", "nullable": false, "max_length": 10, "enum": ["NEW", "SCREEN", "REVIEW", "INTERV", "OFFER", "HIRED", "REJECT"] },
        "APP_SUBMITTED_DT": { "type": "string", "nullable": false, "format": "YYYY-MM-DD" },
        "APP_MODIFIED_DT": { "type": "string", "nullable": false, "format": "YYYY-MM-DD" }
      },
      "sample_records": [
        {
          "APP_ID_50": "ORA-APP-000001",
          "CAND_ID_50": "ORA-CAND-000001",
          "REQ_ID_50": "ORA-REQ-2024-0001",
          "APP_STATUS_CD_10": "REVIEW",
          "APP_SUBMITTED_DT": "2024-08-20",
          "APP_MODIFIED_DT": "2024-11-30"
        }
      ]
    },
    "HR_CANDIDATE_EDUCATION": {
      "endpoint": null,
      "table_name": "HR_CANDIDATE_EDUCATION",
      "description": "Education history - one row per degree",
      "primary_key": "EDU_ID_50",
      "fields": {
        "EDU_ID_50": { "type": "string", "nullable": false, "max_length": 50 },
        "CAND_ID_50": { "type": "string", "nullable": false, "max_length": 50, "foreign_key": "HR_CANDIDATES.CAND_ID_50" },
        "EDU_INSTITUTION_200": { "type": "string", "nullable": false, "max_length": 200 },
        "EDU_DEGREE_CD_10": { "type": "string", "nullable": false, "max_length": 10, "enum": ["HS", "AS", "BS", "BA", "MS", "MBA", "PHD", "JD", "MD", "OTH"] },
        "EDU_FIELD_100": { "type": "string", "nullable": true, "max_length": 100 },
        "EDU_GRAD_DT": { "type": "string", "nullable": true, "format": "YYYY-MM-DD" }
      },
      "sample_records": [
        {
          "EDU_ID_50": "ORA-EDU-000001",
          "CAND_ID_50": "ORA-CAND-000001",
          "EDU_INSTITUTION_200": "Indian Institute of Technology Bombay",
          "EDU_DEGREE_CD_10": "BS",
          "EDU_FIELD_100": "Computer Science",
          "EDU_GRAD_DT": "2018-06-15"
        },
        {
          "EDU_ID_50": "ORA-EDU-000002",
          "CAND_ID_50": "ORA-CAND-000001",
          "EDU_INSTITUTION_200": "Carnegie Mellon University",
          "EDU_DEGREE_CD_10": "MS",
          "EDU_FIELD_100": "Machine Learning",
          "EDU_GRAD_DT": "2020-05-20"
        }
      ]
    }
  }
}
```

##### `src/mock_data/fairshot_api_spec.json`

Clean, well-documented target API. Copy directly from Section 8 of this PRD, structured as:

```json
{
  "api_name": "Fairshot Talent Assessment API",
  "api_version": "v1",
  "base_url": "https://api.fairshot.ai/v1",
  "auth_type": "Bearer",
  "endpoints": {
    "create_candidate": {
      "method": "POST",
      "path": "/api/v1/candidates",
      "description": "Create or update a candidate profile",
      "request_body": {
        "candidate_id": { "type": "string", "required": false, "description": "Auto-generated if omitted" },
        "first_name": { "type": "string", "required": true },
        "last_name": { "type": "string", "required": true },
        "email": { "type": "string", "required": true, "format": "email" },
        "phone": { "type": "string", "required": false, "format": "E.164" },
        "location": {
          "type": "object",
          "required": false,
          "fields": {
            "city": { "type": "string" },
            "state": { "type": "string" },
            "country": { "type": "string", "format": "ISO 3166-1 alpha-2" },
            "postal_code": { "type": "string" }
          }
        },
        "education": {
          "type": "array",
          "required": false,
          "items": {
            "institution": { "type": "string" },
            "degree": { "type": "string", "enum": ["BS", "BA", "MS", "MBA", "PhD", "Other"] },
            "field_of_study": { "type": "string" },
            "graduation_date": { "type": "string", "format": "ISO 8601 date" }
          }
        },
        "experience": {
          "type": "array",
          "required": false,
          "items": {
            "company": { "type": "string" },
            "title": { "type": "string" },
            "start_date": { "type": "string", "format": "ISO 8601 date" },
            "end_date": { "type": "string", "format": "ISO 8601 date", "nullable": true },
            "description": { "type": "string" }
          }
        },
        "source_channel": { "type": "string", "required": false, "enum": ["linkedin", "indeed", "referral", "direct", "other"] },
        "tags": { "type": "array", "required": false, "items": { "type": "string" } },
        "metadata": { "type": "object", "required": false }
      }
    },
    "schedule_simulation": {
      "method": "POST",
      "path": "/api/v1/simulations",
      "description": "Schedule an AI case simulation for a candidate",
      "request_body": {
        "simulation_id": { "type": "string", "required": false },
        "candidate_id": { "type": "string", "required": true },
        "job_id": { "type": "string", "required": true },
        "simulation_type": { "type": "string", "required": true, "enum": ["case_study", "technical", "behavioral", "mixed"] },
        "difficulty_level": { "type": "string", "required": false, "enum": ["junior", "mid", "senior", "executive"] },
        "scheduled_at": { "type": "string", "required": true, "format": "ISO 8601 datetime" },
        "duration_minutes": { "type": "integer", "required": false, "default": 60 },
        "language": { "type": "string", "required": false, "default": "en" },
        "custom_parameters": { "type": "object", "required": false }
      }
    },
    "get_requisition": {
      "method": "GET",
      "path": "/api/v1/requisitions/{id}",
      "description": "Retrieve job requisition details",
      "response_body": {
        "job_id": { "type": "string" },
        "title": { "type": "string" },
        "department": { "type": "string" },
        "hiring_manager": { "type": "string" },
        "location": {
          "type": "object",
          "fields": {
            "city": { "type": "string" },
            "state": { "type": "string" },
            "country": { "type": "string" }
          }
        },
        "employment_type": { "type": "string", "enum": ["full_time", "part_time", "contract", "intern"] },
        "seniority_level": { "type": "string", "enum": ["junior", "mid", "senior", "executive"] },
        "required_skills": { "type": "array", "items": { "type": "string" } },
        "description": { "type": "string" },
        "status": { "type": "string", "enum": ["open", "closed", "on_hold", "filled"] },
        "created_at": { "type": "string", "format": "ISO 8601 datetime" },
        "updated_at": { "type": "string", "format": "ISO 8601 datetime" }
      }
    },
    "health_check": {
      "method": "GET",
      "path": "/api/v1/health",
      "description": "Health check endpoint for integration validation",
      "response_body": {
        "status": { "type": "string", "enum": ["ok"] },
        "version": { "type": "string" },
        "timestamp": { "type": "string", "format": "ISO 8601 datetime" }
      }
    }
  }
}
```

---

#### 1.5 LLM Provider Utilities

**`src/utils/llm_providers.py`**

```python
"""
LLM provider configuration for Virtual FDE.
Initializes OpenAI (primary) and Gemini via LiteLLM (cross-validation).
"""

import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


def get_openai_client() -> OpenAI:
    """Returns a configured OpenAI client."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set")
    return OpenAI(api_key=api_key)


def get_openai_model() -> str:
    """Returns the configured OpenAI model name."""
    return os.getenv("OPENAI_MODEL", "gpt-4o")


def get_gemini_model() -> str:
    """Returns the LiteLLM model string for Gemini."""
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-pro")
    return f"gemini/{model}"


def validate_api_keys() -> dict[str, bool]:
    """Check which API keys are configured. Returns a dict of provider -> is_configured."""
    return {
        "openai": bool(os.getenv("OPENAI_API_KEY")),
        "gemini": bool(os.getenv("GOOGLE_API_KEY")),
    }
```

---

#### 1.6 Streamlit Dashboard Skeleton

**`app/dashboard.py`**

```python
"""
Virtual FDE — Enterprise Integration Concierge
Streamlit dashboard skeleton (Phase 1).
"""

import streamlit as st

st.set_page_config(
    page_title="Virtual FDE — Fairshot Integration Concierge",
    page_icon="🔌",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("Virtual FDE")
st.subheader("Enterprise Integration Concierge")
st.caption("Autonomous ATS → Fairshot integration in under 60 seconds")

st.divider()

# --- Sidebar: Schema Selector ---
with st.sidebar:
    st.header("Configuration")
    schema_choice = st.selectbox(
        "Select ATS Schema",
        options=["Workday Enterprise", "SmartRecruiters Lite", "Legacy Oracle"],
        index=0,
    )
    start_button = st.button("🚀 Start Integration", type="primary", use_container_width=True)
    st.divider()
    st.header("Pipeline Status")
    st.info("Idle — select a schema and click Start")

# --- Main Area: Placeholder Panels ---
col1, col2 = st.columns(2)

with col1:
    with st.expander("📡 Schema Explorer", expanded=True):
        st.caption("Discovered fields and structure will appear here.")
        st.empty()

    with st.expander("💻 Code Generation", expanded=True):
        st.caption("Generated middleware and Gemini validation will appear here.")
        st.empty()

with col2:
    with st.expander("🔗 Semantic Mapping", expanded=True):
        st.caption("Field-by-field ATS → Fairshot mappings will appear here.")
        st.empty()

    with st.expander("🔄 Live Data Flow", expanded=True):
        st.caption("End-to-end data transformation will appear here.")
        st.empty()

st.divider()

with st.expander("📋 Event Log", expanded=False):
    st.caption("Pipeline events will stream here in real-time.")
    st.empty()
```

---

#### 1.7 Tests

**`tests/test_models.py`**

Write tests that verify all Pydantic models can be instantiated with realistic data and that validation works correctly. Test the following:

1. **`ATSField`** — create with all fields, verify `nested_path` is required
2. **`SchemaReport`** — create with a list of ATSFields and EntityRelationships, verify `total_field_count` is required
3. **`FieldMapping`** — verify `confidence_score` enforces 0.0–1.0 range (should raise `ValidationError` for values outside range)
4. **`MappingDocument`** — verify `overall_confidence` and `mapping_coverage` are present
5. **`ValidationResult`** — create with a list of `ValidationIssue` objects
6. **`PipelineState`** — verify default `current_stage` is `IDLE` and `progress_percent` defaults to 0.0
7. **`LogEntry`** — verify `timestamp` is required
8. **Import test** — `from src.models import *` should expose all public models

Use sample data from the mock schemas above to make the test data realistic.

---

#### 1.8 Files Checklist

| File | Action | Notes |
|------|--------|-------|
| `requirements.txt` | Create | Exact content in 1.1 |
| `.env.example` | Create | Exact content in 1.1 |
| `.gitignore` | Create/Update | Append entries from 1.1 |
| `src/__init__.py` | Create | Empty |
| `src/models/__init__.py` | Create | Re-exports from 1.3 |
| `src/models/ats_schema.py` | Create | Copy from PRD Section 6.1 |
| `src/models/mapping.py` | Create | Copy from PRD Section 6.2 |
| `src/models/validation.py` | Create | Copy from PRD Section 6.3 |
| `src/models/pipeline.py` | Create | Copy from PRD Section 6.4 |
| `src/agents/__init__.py` | Create | Empty |
| `src/mock_data/workday_schema.json` | Create | Full content in 1.4 |
| `src/mock_data/smartrecruiters_schema.json` | Create | Full content in 1.4 |
| `src/mock_data/legacy_oracle_schema.json` | Create | Full content in 1.4 |
| `src/mock_data/fairshot_api_spec.json` | Create | Full content in 1.4 |
| `src/middleware/.gitkeep` | Create | Empty file |
| `src/utils/__init__.py` | Create | Empty |
| `src/utils/llm_providers.py` | Create | Exact content in 1.5 |
| `app/__init__.py` | Create | Empty |
| `app/dashboard.py` | Create | Exact content in 1.6 |
| `tests/__init__.py` | Create | Empty |
| `tests/test_models.py` | Create | Follow spec in 1.7 |

---

#### 1.9 Acceptance Criteria

- [ ] `pip install -r requirements.txt` succeeds with no dependency conflicts
- [ ] `python -c "from src.models import ATSField, SchemaReport, FieldMapping, MappingDocument, ValidationResult, PipelineState"` succeeds
- [ ] `python -c "import json; json.load(open('src/mock_data/workday_schema.json'))"` succeeds — and the schema contains 50+ fields across 3 entities
- [ ] `python -c "import json; json.load(open('src/mock_data/smartrecruiters_schema.json'))"` succeeds — flat structure, 2 entities
- [ ] `python -c "import json; json.load(open('src/mock_data/legacy_oracle_schema.json'))"` succeeds — 4 tables with foreign keys
- [ ] `python -c "import json; json.load(open('src/mock_data/fairshot_api_spec.json'))"` succeeds — 4 endpoints
- [ ] `pytest tests/test_models.py -v` — all tests pass
- [ ] `streamlit run app/dashboard.py` — dashboard renders with title, sidebar, and 5 placeholder panels
- [ ] No hardcoded API keys anywhere in the codebase

**Dependencies:** None (first phase)

---

### Phase 2: Schema Explorer Agent

**Goal:** Implement the Schema Explorer as an OpenAI Agents SDK agent that reads mock schemas and outputs a structured `SchemaReport`.

**Scope:**
- Set up OpenAI Agents SDK agent definition in `src/agents/schema_explorer.py`
- Define agent tools:
  - `read_schema_file(path: str) -> dict` — reads and parses JSON schema file
  - `list_endpoints(schema: dict) -> list[str]` — enumerates entities/endpoints
  - `inspect_field(field_path: str) -> ATSField` — extracts field details
- Agent should use GPT-4o to analyze the schema and produce a `SchemaReport`
- Use structured outputs (Pydantic model) for the agent response
- Write unit tests in `tests/test_schema_explorer.py`

**Implementation details:**
- Use `@function_tool` decorator from the SDK for tool definitions
- Agent instruction prompt should emphasize: discover ALL fields, flag anomalies, detect naming conventions
- The agent must handle all 3 mock schema formats (nested Workday, flat SmartRecruiters, relational Oracle)
- For Oracle (relational), the agent should infer relationships from naming conventions and explicit FK references

**Files to create/modify:**
- `src/agents/schema_explorer.py`
- `tests/test_schema_explorer.py`

**Acceptance criteria:**
- [ ] Agent successfully processes `workday_schema.json` and returns a valid `SchemaReport`
- [ ] Agent discovers all 50+ fields in the Workday schema
- [ ] Agent detects naming conventions (`_v3_Final`, `_LEGACY`, `_DO_NOT_USE`)
- [ ] Agent identifies entity relationships
- [ ] `pytest tests/test_schema_explorer.py` passes

**Dependencies:** Phase 1

---

### Phase 3: Semantic Mapper Agent

**Goal:** Implement the Semantic Mapper agent that takes a `SchemaReport` + Fairshot API spec and produces a `MappingDocument`.

**Scope:**
- Set up agent definition in `src/agents/semantic_mapper.py`
- Define agent tools:
  - `load_fairshot_spec(path: str) -> dict` — reads the Fairshot API spec
  - `compute_similarity(ats_field: str, fairshot_field: str) -> float` — uses LLM to compute semantic similarity
  - `lookup_field_context(field_name: str, schema: SchemaReport) -> str` — gets surrounding context for a field
- Agent uses GPT-4o to reason about semantic equivalence between messy ATS fields and clean Fairshot fields
- Confidence scoring: the agent must justify each mapping with a reasoning string
- Write unit tests in `tests/test_semantic_mapper.py`

**Implementation details:**
- The agent prompt should include the full Fairshot API spec as context
- For each Fairshot field, the agent should consider:
  - Exact name matches (rare)
  - Semantic equivalence (e.g., `cand_nm_first` → `first_name`)
  - Abbreviation expansion (e.g., `nm` → name, `cd` → code, `dt` → date)
  - Path-based matching (e.g., `address_block.addr_city_nm` → `location.city`)
- Low-confidence mappings should include alternatives
- Unmappable fields should be explicitly listed

**Files to create/modify:**
- `src/agents/semantic_mapper.py`
- `tests/test_semantic_mapper.py`

**Acceptance criteria:**
- [ ] Agent maps at least 90% of Fairshot fields from the Workday schema
- [ ] All mappings include confidence scores and reasoning
- [ ] Unmapped fields are explicitly listed
- [ ] Mapping handles nested fields (e.g., `address_block.addr_city_nm` → `location.city`)
- [ ] `pytest tests/test_semantic_mapper.py` passes

**Dependencies:** Phase 2

---

### Phase 4: Code Generator + Gemini Cross-Validation

**Goal:** Implement the Code Generator agent that produces Python middleware from a `MappingDocument`, then validates it with Gemini.

**Scope:**
- Set up agent definition in `src/agents/code_generator.py`
- Define agent tools:
  - `generate_transform_function(mapping: FieldMapping) -> str` — generates Python code for a single transform
  - `assemble_middleware(functions: list[str]) -> str` — combines transforms into a complete module
  - `validate_with_gemini(code: str, mapping: MappingDocument) -> ValidationResult` — sends to Gemini for review
  - `run_test_transform(middleware_code: str, sample_input: dict) -> dict` — executes generated code against sample data
- Integrate Gemini 2.5 Pro via LiteLLM in `src/utils/llm_providers.py`
- Write unit tests in `tests/test_code_generator.py`

**Implementation details:**
- Generated middleware should be a standalone Python module with:
  - Individual transform functions per field (e.g., `def transform_first_name(record: dict) -> str`)
  - A main `transform(record: dict) -> dict` function that applies all transforms
  - Type conversion helpers (date parsing, enum mapping, etc.)
  - Null/missing field handling
- Gemini validation prompt should include:
  - The generated code
  - The mapping document (for reference)
  - A sample input record
  - Instructions to check for: correctness, edge cases, data loss, code quality
- If Gemini flags critical issues, the agent should revise (max 2 iterations)

**Files to create/modify:**
- `src/agents/code_generator.py`
- `src/utils/llm_providers.py` (update with Gemini config)
- `tests/test_code_generator.py`

**Acceptance criteria:**
- [ ] Agent generates valid, executable Python middleware
- [ ] Generated middleware correctly transforms a sample Workday record to Fairshot format
- [ ] Gemini cross-validation runs and returns a `ValidationResult`
- [ ] Gemini's feedback is incorporated (if issues found)
- [ ] `pytest tests/test_code_generator.py` passes

**Dependencies:** Phase 3

---

### Phase 5: Deployment Orchestrator (Supervisor)

**Goal:** Wire all agents together using the OpenAI Agents SDK Manager pattern. End-to-end pipeline from schema input to validated middleware.

**Scope:**
- Implement the Deployment Orchestrator in `src/agents/orchestrator.py`
- Use the **agents-as-tools** pattern: register Schema Explorer, Semantic Mapper, and Code Generator as tools
- Implement `PipelineState` management — track progress, store artifacts, emit logs
- End-to-end flow: schema file → SchemaReport → MappingDocument → middleware → ValidationResult
- Add a `run_pipeline(schema_path: str) -> PipelineState` entry point
- Write integration tests in `tests/test_orchestrator.py`

**Implementation details:**
- The orchestrator agent's system prompt should describe the full pipeline and when to call each worker
- Pipeline state should be updated at each stage transition
- Log entries should be created for every significant event (agent started, agent completed, errors)
- Error handling: if any worker fails, the orchestrator should log the error and set pipeline state to ERROR
- The orchestrator should pass the output of each worker as input to the next

**Files to create/modify:**
- `src/agents/orchestrator.py`
- `tests/test_orchestrator.py`

**Acceptance criteria:**
- [ ] `python -m src.agents.orchestrator` runs the full pipeline against the Workday mock schema
- [ ] Pipeline completes in < 60 seconds
- [ ] PipelineState contains all artifacts (SchemaReport, MappingDocument, middleware, ValidationResult)
- [ ] Pipeline logs capture all stage transitions
- [ ] `pytest tests/test_orchestrator.py` passes

**Dependencies:** Phase 4

---

### Phase 6: Frontend Dashboard

**Goal:** Build a Streamlit dashboard that visualizes the pipeline in real-time.

**Scope:**
- Implement `app/dashboard.py` with the following panels:
  1. **Input panel:** Schema selector dropdown + "Start Integration" button
  2. **Pipeline progress bar:** Shows current stage with percentage
  3. **Schema Explorer panel:** Live-streaming field discovery, tree visualization
  4. **Semantic Mapping panel:** Side-by-side ATS↔Fairshot field mapping with confidence colors
  5. **Code Generation panel:** Syntax-highlighted generated code + Gemini validation results
  6. **Data Flow panel:** Input record → transformation → output record visualization
  7. **Log panel:** Scrolling event log
- Connect dashboard to the orchestrator pipeline
- Use Streamlit's `st.status`, `st.expander`, and streaming capabilities for real-time updates

**Implementation details:**
- Use `st.session_state` to manage pipeline state across reruns
- Use `st.columns` for side-by-side layouts
- Use `st.code` with `language="python"` for syntax highlighting
- Use color indicators: green/yellow/red for confidence levels
- The pipeline should run in a background thread or use Streamlit's async support
- Add a "Schema Drift" button (for Phase 7) — disabled/placeholder in this phase
- Style the dashboard to look professional — dark theme preferred, Fairshot branding colors if available

**Files to create/modify:**
- `app/dashboard.py` (rewrite from Phase 1 skeleton)
- `app/static/` (any CSS or assets if needed)

**Acceptance criteria:**
- [ ] `streamlit run app/dashboard.py` launches without errors
- [ ] Selecting a schema and clicking "Start" triggers the full pipeline
- [ ] All 6 panels update in real-time as the pipeline progresses
- [ ] Mapping panel shows color-coded confidence scores
- [ ] Code panel shows both generated code and Gemini review
- [ ] Data flow panel shows end-to-end transformation of a sample record
- [ ] Dashboard is visually polished and demo-ready

**Dependencies:** Phase 5

---

### Phase 7: Schema Drift & Polish

**Goal:** Implement schema drift detection and auto-repair. Final demo polish.

**Scope:**
- Add schema drift simulation capability:
  - A "Trigger Schema Drift" button in the dashboard
  - When clicked, modifies the active schema (renames a field, adds a new field, changes a type)
  - System detects the drift by comparing against the stored `SchemaReport`
  - Orchestrator triggers re-exploration → re-mapping → re-generation for affected fields only
  - Dashboard shows the full drift detection → auto-repair flow with visual indicators
- Error handling and self-healing visualization
- Demo script / walkthrough notes
- Final polish:
  - Loading animations
  - Professional styling
  - Timing optimization (ensure < 60 second total flow)
  - Edge case handling

**Implementation details:**
- Schema drift detection should compare field names, types, and structure between original and modified schema
- Only re-process affected fields (incremental re-mapping, not full restart)
- Dashboard should clearly show:
  - What changed (diff view)
  - What was affected (which mappings broke)
  - How it was fixed (new mappings + regenerated transforms)
- Add a pre-built "drift scenario" for each mock schema

**Files to create/modify:**
- `src/agents/orchestrator.py` (add drift detection logic)
- `app/dashboard.py` (add drift UI)
- `src/mock_data/workday_schema_drifted.json` (modified schema for drift demo)
- Create `DEMO_SCRIPT.md` with step-by-step demo walkthrough

**Acceptance criteria:**
- [ ] "Trigger Schema Drift" button introduces 3 breaking changes to the active schema
- [ ] System detects all 3 changes within 5 seconds
- [ ] Auto-repair completes without manual intervention
- [ ] Dashboard shows clear before/after diff
- [ ] Full demo (including drift) completes in < 90 seconds
- [ ] `DEMO_SCRIPT.md` provides a complete walkthrough for the presenter

**Dependencies:** Phase 6

---

## 10. Acceptance Criteria (Overall)

- [ ] End-to-end: mock ATS schema → semantic mapping → generated middleware → live data flow in < 60 seconds
- [ ] Dual-LLM: OpenAI generates, Gemini validates — both visible in the UI
- [ ] Schema drift: system detects and auto-repairs a mid-demo schema change
- [ ] Zero manual configuration required during the demo
- [ ] Dashboard clearly shows each pipeline stage with real-time progress
- [ ] Generated middleware correctly transforms at least 90% of fields
- [ ] All 3 mock ATS schemas work end-to-end
- [ ] `pytest tests/` — all tests pass
- [ ] No hardcoded API keys — all via environment variables

---

## 11. File Structure

```
fairshot/
├── PRD.md                          # This document
├── CONTEXT.MD                      # Pitch context
├── CLAUDE.md                       # Project-specific instructions
├── DEMO_SCRIPT.md                  # Demo walkthrough (Phase 7)
├── Gemini_context.md               # Gemini feedback log
├── requirements.txt
├── .env.example                    # API keys template
├── .gitignore
├── src/
│   ├── __init__.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── ats_schema.py           # ATSField, SchemaReport, EntityRelationship
│   │   ├── mapping.py              # FieldMapping, MappingDocument, Confidence
│   │   ├── validation.py           # ValidationResult, ValidationIssue, Severity
│   │   └── pipeline.py             # PipelineState, PipelineStage, LogEntry
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── orchestrator.py         # Deployment Orchestrator (supervisor)
│   │   ├── schema_explorer.py      # Schema Explorer agent
│   │   ├── semantic_mapper.py      # Semantic Mapper agent
│   │   └── code_generator.py       # Code Gen + Gemini validator
│   ├── mock_data/
│   │   ├── workday_schema.json
│   │   ├── workday_schema_drifted.json  # (Phase 7)
│   │   ├── smartrecruiters_schema.json
│   │   ├── legacy_oracle_schema.json
│   │   └── fairshot_api_spec.json
│   ├── middleware/                  # Generated middleware output dir
│   │   └── .gitkeep
│   └── utils/
│       ├── __init__.py
│       └── llm_providers.py        # OpenAI + Gemini (LiteLLM) config
├── app/
│   ├── __init__.py
│   ├── dashboard.py                # Streamlit app
│   └── static/                     # Frontend assets
└── tests/
    ├── __init__.py
    ├── test_models.py
    ├── test_schema_explorer.py
    ├── test_semantic_mapper.py
    ├── test_code_generator.py
    └── test_orchestrator.py
```

---

## 12. Dependencies

```
# requirements.txt
openai-agents>=0.1.0
openai>=1.60.0
google-genai>=1.0.0
litellm>=1.55.0
pydantic>=2.0.0
streamlit>=1.40.0
python-dotenv>=1.0.0
pytest>=8.0.0
pytest-asyncio>=0.24.0
jinja2>=3.1.0
diskcache>=5.6.0
```

---

## 13. Environment Variables

```bash
# .env.example
OPENAI_API_KEY=sk-your-openai-key-here
GOOGLE_API_KEY=your-gemini-api-key-here

# Optional
OPENAI_MODEL=gpt-4o
GEMINI_MODEL=gemini-2.5-pro
LOG_LEVEL=INFO
```

---

## 14. Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Agent framework | OpenAI Agents SDK | Native structured outputs, agents-as-tools pattern, active development |
| Gemini integration | LiteLLM | SDK-agnostic provider adapter, minimal code change to swap models |
| Frontend | Streamlit | Fastest path to interactive dashboard, built-in streaming |
| Mock data format | JSON | Universal, easy to parse, supports nesting |
| Orchestration pattern | Sequential pipeline | Demo clarity — audience can follow each step. Parallel would be faster but harder to visualize |
| Schema drift approach | File replacement + diff | Simple, deterministic, impressive visual impact |

---

## 15. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| LLM latency makes demo slow | High — breaks the "< 60 seconds" target | Pre-warm models, use streaming, cache repeated calls during dev |
| Generated code has bugs | Medium — breaks live data flow | Gemini cross-validation + pre-built fallback middleware |
| Semantic mapping is inaccurate | Medium — undermines credibility | Curate mock schemas to have clear (if messy) semantic equivalents |
| API rate limits during demo | High — demo fails live | Use cached responses as fallback, keep demo under 20 API calls |
| Streamlit limitations | Low — UI not polished enough | Can fall back to FastAPI + static HTML if needed |

---

*This PRD is the single source of truth for the Virtual FDE demo. All implementation should reference this document. Questions or ambiguities should be resolved by updating this PRD before proceeding with code.*
