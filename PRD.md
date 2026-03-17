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

### Phase 3: Semantic Mapper Agent — DETAILED SPEC

**Goal:** Implement the Semantic Mapper agent that takes a `SchemaReport` (output of Phase 2's Schema Explorer) + the Fairshot API spec and produces a `MappingDocument` with field-by-field mappings, confidence scores, and reasoning.

**Dependencies:** Phase 2 (Schema Explorer must be functional and producing valid `SchemaReport` objects)

---

#### 3.1 Architecture Overview

The Semantic Mapper is an OpenAI Agents SDK agent (`Agent`) with `output_type=MappingDocument`. It receives a serialized `SchemaReport` + the Fairshot API spec as input context, reasons about semantic equivalences between messy ATS fields and clean Fairshot fields, and produces a deterministic `MappingDocument`.

**Key design decision:** The agent does NOT call an LLM per-field for similarity scoring. Instead, it receives the full SchemaReport + Fairshot spec in a single prompt and maps ALL fields in one pass. This keeps latency low (single LLM call) and gives the model full context to resolve ambiguities. The `compute_similarity` tool from the original Phase 3 outline is replaced with a deterministic helper that the agent can optionally call for edge cases.

```
                  ┌──────────────────────────┐
                  │    Semantic Mapper Agent  │
                  │    Model: GPT-4o         │
                  │    output_type:           │
                  │      MappingDocument      │
                  ├──────────────────────────┤
                  │  Tools:                   │
                  │  - load_fairshot_spec()   │
                  │  - get_schema_summary()   │
                  │  - get_field_samples()    │
                  └──────────────────────────┘
                           │
            Input: SchemaReport (JSON) +
                   schema file path +
                   fairshot spec path
                           │
            Output: MappingDocument (Pydantic)
```

---

#### 3.2 File: `src/agents/semantic_mapper.py`

```python
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
        entity_name: The entity key (e.g., 'WD_Candidate_Profile').
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
  `WD_Candidate_Profile.address_block.addr_city_nm` → `location.city`.
- **Array items**: Map array sub-fields individually. E.g., \
  `education_history[].edu_institution_nm` → `education[].institution`.
- **Enum translation**: When ATS uses codes (e.g., `LINKEDIN_APPLY`) and \
  Fairshot uses lowercase (e.g., `linkedin`), note the transform needed.
- **Date format normalization**: When ATS uses `MM/DD/YYYY` or epoch seconds \
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
        model="gpt-4o",
    )
```

---

#### 3.3 How to Run the Semantic Mapper

The Semantic Mapper agent is invoked by passing it a message containing:
1. The serialized `SchemaReport` JSON (from Phase 2's Schema Explorer output)
2. The file paths for the raw schema and Fairshot API spec

**Example invocation (for testing or from the orchestrator):**

```python
import asyncio
import json
from agents import Runner
from src.agents.schema_explorer import create_schema_explorer
from src.agents.semantic_mapper import create_semantic_mapper

async def run_mapping():
    # Step 1: Run Schema Explorer (Phase 2)
    explorer = create_schema_explorer()
    explore_result = await Runner.run(
        explorer,
        input="Analyze the schema at src/mock_data/workday_schema.json"
    )
    schema_report = explore_result.final_output  # SchemaReport

    # Step 2: Run Semantic Mapper (Phase 3)
    mapper = create_semantic_mapper()
    mapper_input = (
        f"Map the following ATS schema to the Fairshot API.\n\n"
        f"Schema Report (JSON):\n{schema_report.model_dump_json(indent=2)}\n\n"
        f"Raw schema file: src/mock_data/workday_schema.json\n"
        f"Fairshot API spec file: src/mock_data/fairshot_api_spec.json"
    )
    map_result = await Runner.run(mapper, input=mapper_input)
    mapping_doc = map_result.final_output  # MappingDocument

    print(f"Mapped {len(mapping_doc.mappings)} fields")
    print(f"Coverage: {mapping_doc.mapping_coverage:.0%}")
    print(f"Confidence: {mapping_doc.overall_confidence:.2f}")

asyncio.run(run_mapping())
```

---

#### 3.4 Expected Mappings (Workday → Fairshot Reference)

This table serves as the ground truth for testing. The agent should produce mappings substantially matching these:

| ATS Field (Workday) | Fairshot Field | Transform | Expected Confidence |
|---|---|---|---|
| `cand_nm_first` | `first_name` | `direct_copy` | HIGH (0.95) |
| `cand_nm_last` | `last_name` | `direct_copy` | HIGH (0.95) |
| `cand_email_primary_v3_Final` | `email` | `direct_copy` | HIGH (0.92) |
| `cand_phone_mobile_INTL` | `phone` | `phone_to_e164` | MEDIUM (0.85) |
| `address_block.addr_city_nm` | `location.city` | `nested_extract` | HIGH (0.93) |
| `address_block.addr_state_province` | `location.state` | `nested_extract` | HIGH (0.93) |
| `address_block.addr_country_iso` | `location.country` | `nested_extract` | HIGH (0.95) |
| `address_block.addr_postal_cd` | `location.postal_code` | `nested_extract` | HIGH (0.93) |
| `education_history[].edu_institution_nm` | `education[].institution` | `direct_copy` | HIGH (0.94) |
| `education_history[].edu_degree_type_cd` | `education[].degree` | `lowercase_enum` | MEDIUM (0.88) |
| `education_history[].edu_field_of_study` | `education[].field_of_study` | `direct_copy` | HIGH (0.95) |
| `education_history[].edu_graduation_dt` | `education[].graduation_date` | `date_mmddyyyy_to_iso` | MEDIUM (0.85) |
| `work_experience_LEGACY[].exp_company_nm` | `experience[].company` | `direct_copy` | HIGH (0.90) |
| `work_experience_LEGACY[].exp_title` | `experience[].title` | `direct_copy` | HIGH (0.92) |
| `work_experience_LEGACY[].exp_start_dt` | `experience[].start_date` | `epoch_to_iso` | MEDIUM (0.80) |
| `work_experience_LEGACY[].exp_end_dt` | `experience[].end_date` | `epoch_to_iso` | MEDIUM (0.80) |
| `work_experience_LEGACY[].exp_description_txt` | `experience[].description` | `direct_copy` | HIGH (0.92) |
| `source_channel_cd` | `source_channel` | `lowercase_enum` | MEDIUM (0.85) |
| `cand_skills_tags_txt` | `tags` | `semicolon_to_list` | MEDIUM (0.78) |
| `Custom_Req_ID_v3_Final` | `job_id` | `direct_copy` | HIGH (0.90) |

**Expected unmapped ATS fields** (should appear in `unmapped_ats_fields`):
- `cand_nm_middle_initial` — no Fairshot equivalent
- `cand_email_secondary_DEPRECATED` — deprecated
- `cand_phone_home_LEGACY` — deprecated, mobile already mapped
- `Custom_Diversity_Flag_DO_NOT_USE` — explicitly flagged
- `cand_gender_cd` — no Fairshot equivalent (sensitive PII)
- `cand_dob_dt` — no Fairshot equivalent (sensitive PII)
- `internal_candidate_flag` — no Fairshot equivalent
- `recruiter_assigned_id` — no Fairshot equivalent
- `screening_score_v2` — could go to `metadata`, but low confidence
- `notes_txt_DEPRECATED` — deprecated
- `cand_profile_url_txt` — no Fairshot equivalent
- `cand_resume_blob_id` — no Fairshot equivalent
- `application_status_cd` — no direct Fairshot candidate field
- `application_submitted_dt` — no direct Fairshot candidate field
- `cand_preferred_lang_cd` — no Fairshot equivalent
- `cand_timezone_v2_Final` — no Fairshot equivalent
- `last_modified_ts` — no Fairshot equivalent
- `edu_gpa_val_LEGACY` — deprecated, no Fairshot equivalent

**Expected unmapped Fairshot fields** (should appear in `unmapped_fairshot_fields`):
- `candidate_id` — auto-generated by Fairshot, no ATS source needed
- `metadata` — optional catch-all, not directly mappable

---

#### 3.5 File: `tests/test_semantic_mapper.py`

```python
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
            "src/mock_data/smartrecruiters_schema.json", "sr_candidates"
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
```

---

#### 3.6 Files Checklist

| File | Action | Notes |
|------|--------|-------|
| `src/agents/semantic_mapper.py` | Create | Full implementation from Section 3.2 |
| `tests/test_semantic_mapper.py` | Create | Full test suite from Section 3.5 |

No other files need modification. The models (`MappingDocument`, `FieldMapping`, `Confidence`) already exist from Phase 1. The Schema Explorer from Phase 2 is consumed as-is.

---

#### 3.7 Implementation Notes for Gemini

1. **Copy the code from 3.2 verbatim** — the agent instructions, tools, and factory function are fully specified. Do not change the tool signatures or the agent instructions.

2. **The `_get_schema_summary` tool** is the key innovation vs. the original Phase 3 spec. Instead of per-field LLM calls, the agent gets a pre-formatted summary of ALL fields and maps them in one reasoning pass. This keeps latency to a single LLM round-trip.

3. **The `_get_field_samples` tool** is optional — the agent calls it only when it needs to inspect actual data values to resolve ambiguous mappings (e.g., figuring out that `sr_cnd_src_cd: 1` means "LinkedIn").

4. **Follow the existing patterns from Phase 2** (`schema_explorer.py`):
   - Underscore-prefixed private functions for tools (`_load_fairshot_spec`)
   - `function_tool()` wrapper in the factory function
   - `create_semantic_mapper()` factory returns the `Agent` instance
   - Module-level cache dicts for file I/O

5. **The agent prompt is long and detailed** — this is intentional. GPT-4o needs explicit instructions for:
   - Abbreviation expansion rules (the ATS schemas use heavy abbreviations)
   - Transform function naming conventions (these names are used by Phase 4's Code Generator)
   - Confidence scoring thresholds
   - How to handle deprecated fields

6. **Do NOT add `diskcache` or caching in this phase** — that's Phase 5/6 territory. Keep this phase focused on the agent itself.

---

#### 3.8 Acceptance Criteria

- [ ] `src/agents/semantic_mapper.py` exists and exports `create_semantic_mapper()`
- [ ] `pytest tests/test_semantic_mapper.py -v -k "not agent"` passes — all tool-level unit tests pass without an API key
- [ ] (With API key) Agent processes the Workday schema and returns a valid `MappingDocument`
- [ ] (With API key) At least 15 field mappings are produced
- [ ] (With API key) `first_name`, `last_name`, `email` are all mapped
- [ ] (With API key) At least one `location.*` field is mapped (nested field handling)
- [ ] (With API key) At least one `education[].*` field is mapped (array field handling)
- [ ] (With API key) Every mapping has a non-empty `reasoning` string
- [ ] (With API key) Deprecated/DO_NOT_USE fields are either unmapped or mapped with low confidence
- [ ] (With API key) `mapping_coverage >= 85%`
- [ ] (With API key) `unmapped_ats_fields` is non-empty (deprecated fields should appear here)

**Dependencies:** Phase 2

---

### Phase 4: Code Generator + Gemini Cross-Validation — DETAILED SPEC

**Goal:** Take a `MappingDocument` (from Phase 3) and produce working Python middleware that transforms ATS records into Fairshot API payloads. Cross-validate the output with Gemini 2.5 Pro.

**Dependencies:** Phase 3 (Semantic Mapper must produce valid `MappingDocument` objects). Phase 1's `src/utils/llm_providers.py` already has `get_gemini_client()` and `get_gemini_model()`.

---

#### 4.1 Architecture Overview — JSON Transform Spec + Jinja2 Templating

**Critical design decision (from Gemini cross-agent feedback):** The LLM does NOT generate raw Python code. Instead:

1. The **GPT-4o agent** outputs a **JSON transform spec** — a structured list of transform operations per field
2. A **deterministic Jinja2 template engine** renders the JSON spec into a valid Python middleware module
3. **Gemini 2.5 Pro** reviews the generated Python for correctness

This eliminates the #1 demo-failure risk: LLM-hallucinated syntax errors, bad indentation, or missing imports.

```
MappingDocument ──► GPT-4o Agent ──► TransformSpec (JSON)
                                          │
                                    Jinja2 Template
                                          │
                                    middleware.py (Python)
                                          │
                                    Gemini 2.5 Pro Review
                                          │
                                    ValidationResult
```

---

#### 4.2 New Data Model: `TransformSpec`

Add to `src/models/validation.py` (extends existing file):

```python
# Add these to src/models/validation.py, after the existing ValidationResult class

class TransformOperation(BaseModel):
    """A single deterministic transform operation."""
    fairshot_field: str = Field(description="Target field in Fairshot API (dot-notation for nested)")
    ats_source_path: str = Field(description="Source field path in ATS record (dot-notation)")
    transform_type: str = Field(description="One of the predefined transform types")
    params: dict = Field(
        default_factory=dict,
        description="Transform-specific parameters (e.g., date_format, enum_map, delimiter)"
    )
    is_array_item: bool = Field(
        default=False,
        description="True if this transform applies inside an array (e.g., education[], experience[])"
    )
    array_source_path: str = Field(
        default="",
        description="If is_array_item, the path to the source array (e.g., 'education_history')"
    )
    array_target_path: str = Field(
        default="",
        description="If is_array_item, the path to the target array (e.g., 'education')"
    )
    nullable: bool = Field(default=True, description="Whether to skip if source value is None")


class TransformSpec(BaseModel):
    """Complete transform specification output by the Code Generator agent.
    This is the structured intermediate representation between the LLM
    and the Jinja2 template engine."""
    ats_name: str
    transforms: list[TransformOperation]
    custom_code_blocks: list[str] = Field(
        default_factory=list,
        description="Any custom Python snippets the agent deems necessary (escape hatch)"
    )
    notes: str = Field(default="", description="Agent notes about edge cases or assumptions")
```

Also update `src/models/__init__.py` to export:
```python
from .validation import Severity, ValidationIssue, ValidationResult, TransformOperation, TransformSpec
```

---

#### 4.3 Predefined Transform Types

The Jinja2 template knows how to render these transform types. The agent MUST use only these (plus `custom` as an escape hatch):

| Transform Type | Params | Behavior |
|---|---|---|
| `direct_copy` | (none) | Copy value as-is |
| `lowercase_enum` | `enum_map: dict` (optional) | Lowercase the value. If `enum_map` provided, use it for explicit mapping (e.g., `{"LINKEDIN_APPLY": "linkedin"}`) |
| `date_mmddyyyy_to_iso` | (none) | Parse `MM/DD/YYYY` → `YYYY-MM-DD` |
| `epoch_to_iso` | (none) | Unix epoch (int) → `YYYY-MM-DD` |
| `nested_extract` | `path: str` | Extract value from nested dict using dot-path |
| `semicolon_to_list` | (none) | `"a;b;c"` → `["a", "b", "c"]` |
| `json_string_to_list` | (none) | `'["a","b"]'` → `["a", "b"]` |
| `phone_to_e164` | (none) | Strip non-numeric chars except leading `+` |
| `numeric_enum` | `enum_map: dict` | Map integer codes to strings (e.g., `{1: "linkedin", 3: "referral"}`) |
| `varchar_strip` | `suffix_pattern: str` | Strip VARCHAR length suffix (e.g., `_50`, `_100`) from field name (Oracle) |
| `custom` | `code: str` | Raw Python expression (escape hatch — Gemini will scrutinize these) |

---

#### 4.4 Jinja2 Middleware Template

Create `src/templates/middleware.py.j2`:

```python
"""
Auto-generated middleware: {{ ats_name }} → Fairshot API
Generated by Virtual FDE Code Generator
"""

from datetime import datetime, timezone
from typing import Any, Optional
import json


# ─── Transform Helpers ───────────────────────────────────────────────────

def _safe_get(record: dict, path: str, default: Any = None) -> Any:
    """Safely extract a value from a nested dict using dot-notation path."""
    keys = path.split(".")
    current = record
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default
    return current


def _direct_copy(value: Any) -> Any:
    return value


def _lowercase_enum(value: Any, enum_map: dict | None = None) -> str | None:
    if value is None:
        return None
    if enum_map and str(value) in enum_map:
        return enum_map[str(value)]
    return str(value).lower().replace("_", " ").split("_")[0] if value else None


def _date_mmddyyyy_to_iso(value: str | None) -> str | None:
    if not value:
        return None
    try:
        dt = datetime.strptime(value, "%m/%d/%Y")
        return dt.strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        return value


def _epoch_to_iso(value: int | float | None) -> str | None:
    if value is None:
        return None
    try:
        dt = datetime.fromtimestamp(int(value), tz=timezone.utc)
        return dt.strftime("%Y-%m-%d")
    except (ValueError, TypeError, OSError):
        return None


def _semicolon_to_list(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(";") if item.strip()]


def _json_string_to_list(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


def _phone_to_e164(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = ""
    for ch in value:
        if ch.isdigit() or (ch == "+" and not cleaned):
            cleaned += ch
    return cleaned if cleaned else None


def _numeric_enum(value: Any, enum_map: dict | None = None) -> str | None:
    if value is None:
        return None
    if enum_map and str(value) in enum_map:
        return enum_map[str(value)]
    return str(value)


# ─── Main Transform Function ────────────────────────────────────────────

def transform(record: dict) -> dict:
    """Transform a raw {{ ats_name }} record into a Fairshot API payload."""
    output = {}

    {% for t in transforms %}
    {% if not t.is_array_item %}
    # {{ t.fairshot_field }} ← {{ t.ats_source_path }} ({{ t.transform_type }})
    {% if t.transform_type == "direct_copy" %}
    _val = _safe_get(record, "{{ t.ats_source_path }}")
    {% if t.nullable %}
    if _val is not None:
        {% endif %}
        _set_nested(output, "{{ t.fairshot_field }}", _direct_copy(_val))
    {% elif t.transform_type == "lowercase_enum" %}
    _val = _safe_get(record, "{{ t.ats_source_path }}")
    if _val is not None:
        _set_nested(output, "{{ t.fairshot_field }}", _lowercase_enum(_val, {{ t.params.get('enum_map', 'None') }}))
    {% elif t.transform_type == "date_mmddyyyy_to_iso" %}
    _val = _safe_get(record, "{{ t.ats_source_path }}")
    if _val is not None:
        _set_nested(output, "{{ t.fairshot_field }}", _date_mmddyyyy_to_iso(_val))
    {% elif t.transform_type == "epoch_to_iso" %}
    _val = _safe_get(record, "{{ t.ats_source_path }}")
    if _val is not None:
        _set_nested(output, "{{ t.fairshot_field }}", _epoch_to_iso(_val))
    {% elif t.transform_type == "nested_extract" %}
    _val = _safe_get(record, "{{ t.ats_source_path }}")
    if _val is not None:
        _set_nested(output, "{{ t.fairshot_field }}", _val)
    {% elif t.transform_type == "semicolon_to_list" %}
    _val = _safe_get(record, "{{ t.ats_source_path }}")
    _set_nested(output, "{{ t.fairshot_field }}", _semicolon_to_list(_val))
    {% elif t.transform_type == "json_string_to_list" %}
    _val = _safe_get(record, "{{ t.ats_source_path }}")
    _set_nested(output, "{{ t.fairshot_field }}", _json_string_to_list(_val))
    {% elif t.transform_type == "phone_to_e164" %}
    _val = _safe_get(record, "{{ t.ats_source_path }}")
    if _val is not None:
        _set_nested(output, "{{ t.fairshot_field }}", _phone_to_e164(_val))
    {% elif t.transform_type == "numeric_enum" %}
    _val = _safe_get(record, "{{ t.ats_source_path }}")
    if _val is not None:
        _set_nested(output, "{{ t.fairshot_field }}", _numeric_enum(_val, {{ t.params.get('enum_map', 'None') }}))
    {% elif t.transform_type == "custom" %}
    # Custom transform
    {{ t.params.get('code', 'pass') }}
    {% endif %}

    {% endif %}
    {% endfor %}

    # ─── Array Transforms ────────────────────────────────────────────
    {% set array_groups = {} %}
    {% for t in transforms if t.is_array_item %}
    {% if t.array_target_path not in array_groups %}
    {% set _ = array_groups.update({t.array_target_path: []}) %}
    {% endif %}
    {% set _ = array_groups[t.array_target_path].append(t) %}
    {% endfor %}

    {% for target_array, items in array_groups.items() %}
    # Array: {{ items[0].array_source_path }} → {{ target_array }}
    _source_arr = _safe_get(record, "{{ items[0].array_source_path }}", [])
    if isinstance(_source_arr, list):
        _target_arr = []
        for _item in _source_arr:
            _mapped = {}
            {% for t in items %}
            # {{ t.fairshot_field }} ← {{ t.ats_source_path }}
            {% set field_key = t.ats_source_path.split(".")[-1] %}
            _arr_val = _item.get("{{ field_key }}")
            {% if t.transform_type == "direct_copy" %}
            if _arr_val is not None:
                _mapped["{{ t.fairshot_field.split('.')[-1] }}"] = _direct_copy(_arr_val)
            {% elif t.transform_type == "date_mmddyyyy_to_iso" %}
            if _arr_val is not None:
                _mapped["{{ t.fairshot_field.split('.')[-1] }}"] = _date_mmddyyyy_to_iso(_arr_val)
            {% elif t.transform_type == "epoch_to_iso" %}
            if _arr_val is not None:
                _mapped["{{ t.fairshot_field.split('.')[-1] }}"] = _epoch_to_iso(_arr_val)
            {% elif t.transform_type == "lowercase_enum" %}
            if _arr_val is not None:
                _mapped["{{ t.fairshot_field.split('.')[-1] }}"] = _lowercase_enum(_arr_val, {{ t.params.get('enum_map', 'None') }})
            {% endif %}
            {% endfor %}
            _target_arr.append(_mapped)
        output["{{ target_array }}"] = _target_arr

    {% endfor %}

    {% for block in custom_code_blocks %}
    # Custom code block
    {{ block }}
    {% endfor %}

    return output


def _set_nested(d: dict, path: str, value: Any) -> None:
    """Set a value in a nested dict using dot-notation path."""
    keys = path.split(".")
    for key in keys[:-1]:
        if key not in d:
            d[key] = {}
        d = d[key]
    d[keys[-1]] = value
```

> **Note for Gemini:** This template is complex. Copy it exactly as specified. The Jinja2 control flow handles both flat field transforms and array transforms (education, experience). The `_set_nested` helper enables dot-notation output paths like `location.city`.

---

#### 4.5 File: `src/agents/code_generator.py`

```python
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
        model="gpt-4o",
    )
```

---

#### 4.6 How to Run the Code Generator

```python
import asyncio
import json
from agents import Runner
from src.agents.code_generator import create_code_generator, _render_middleware
from src.models import TransformSpec

async def run_code_gen(mapping_doc_json: str, schema_path: str, entity_name: str):
    generator = create_code_generator()
    gen_input = (
        f"Generate a TransformSpec for the following mapping.\n\n"
        f"Mapping Document (JSON):\n{mapping_doc_json}\n\n"
        f"Schema file: {schema_path}\n"
        f"Primary entity: {entity_name}\n"
        f"Fairshot spec: src/mock_data/fairshot_api_spec.json"
    )
    result = await Runner.run(generator, input=gen_input)
    transform_spec = result.final_output  # TransformSpec

    # Render final middleware
    middleware_code = _render_middleware(transform_spec)

    # Optionally save to disk
    with open("src/middleware/middleware.py", "w") as f:
        f.write(middleware_code)

    return transform_spec, middleware_code
```

---

#### 4.7 File: `tests/test_code_generator.py`

```python
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
```

---

#### 4.8 Files Checklist

| File | Action | Notes |
|------|--------|-------|
| `src/models/validation.py` | **Modify** | Add `TransformOperation` and `TransformSpec` classes (Section 4.2) |
| `src/models/__init__.py` | **Modify** | Add `TransformOperation, TransformSpec` to exports |
| `src/templates/middleware.py.j2` | **Create** | Jinja2 template from Section 4.4 |
| `src/agents/code_generator.py` | **Create** | Full implementation from Section 4.5 |
| `tests/test_code_generator.py` | **Create** | Full test suite from Section 4.7 |

No changes needed to `src/utils/llm_providers.py` — Gemini already has `get_gemini_client()` and `get_gemini_model()` from Phase 1.

---

#### 4.9 Implementation Notes for Gemini

1. **Create `src/templates/` directory** — this is new. Add an `__init__.py` if desired, but it's not required (Jinja2 uses `FileSystemLoader`, not Python imports).

2. **The Jinja2 template is the hardest part of this phase.** The template handles:
   - Flat field transforms (direct_copy, enum mapping, date conversion, etc.)
   - Nested output fields via `_set_nested()` helper
   - Array transforms (education, experience) with per-item sub-field mapping
   - Custom code blocks (escape hatch)

   **Test the template thoroughly** — the `TestEndToEndTransform` class in the test file validates that a rendered template actually executes correctly against Workday sample data.

3. **The `exec()` in `_run_test_transform`** is intentional — this is a demo, not production. The generated code runs in an isolated namespace dict. Do not add `eval()` or `__import__` restrictions — it would break the generated middleware's `import json` and `from datetime import datetime`.

4. **Gemini validation is a single API call** using `google-genai` directly (not LiteLLM). The `_validate_with_gemini` function constructs a prompt, calls `client.models.generate_content()`, and parses the JSON response into a `ValidationResult`. If Gemini's response isn't valid JSON, the function returns a fallback error result.

5. **The agent's `output_type` is `TransformSpec`, not `ValidationResult`.** The agent outputs the structured transform specification. The Gemini validation happens as a side-effect via the tool call. The orchestrator (Phase 5) will extract both the TransformSpec and the ValidationResult from the pipeline.

6. **Follow the existing file patterns:**
   - Underscore-prefixed private functions for tools
   - `function_tool()` wrapper in the factory
   - `create_code_generator()` factory returns the `Agent`
   - Module-level constants for the instruction prompt

---

#### 4.10 Acceptance Criteria

- [ ] `TransformOperation` and `TransformSpec` models added to `src/models/validation.py` and exported from `src/models/__init__.py`
- [ ] `src/templates/middleware.py.j2` exists and is a valid Jinja2 template
- [ ] `pytest tests/test_code_generator.py -v -k "not agent"` passes — all template, execution, and sample-loading tests pass without API keys
- [ ] `TestEndToEndTransform::test_workday_candidate_transform` passes — proves the full render→execute pipeline works with realistic data
- [ ] (With OPENAI_API_KEY) Agent produces a valid `TransformSpec` from a MappingDocument
- [ ] (With OPENAI_API_KEY) Generated TransformSpec renders into syntactically valid Python (`compile()` succeeds)
- [ ] (With OPENAI_API_KEY + GOOGLE_API_KEY) Gemini cross-validation runs and returns a `ValidationResult`
- [ ] Generated middleware correctly transforms the Workday sample record (Jane Doe) with correct `first_name`, `last_name`, `email`, and `location.city`

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
