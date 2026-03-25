"""
Virtual FDE — Enterprise Integration Concierge
Streamlit Dashboard (Phase 6)
"""

import asyncio
import json
import queue
import threading
import time
from datetime import datetime

import streamlit as st

from src.agents.orchestrator import run_pipeline, SCHEMA_CONFIGS
from src.models import PipelineState, PipelineStage

# ─── Page Config ─────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Virtual FDE — Fairshot",
    page_icon="app/static/logo.jpeg",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Fairshot Brand CSS ──────────────────────────────────────────────────

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Figtree:wght@400;500;600;700&display=swap');

    /* Global font */
    html, body, [class*="css"] {
        font-family: 'Figtree', sans-serif;
    }

    /* Main background */
    .stApp {
        background-color: #0D0D0D;
    }

    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background-color: #1A1A1A;
        border-right: 1px solid #2A2A2A;
    }

    /* Purple accent for headers */
    h1, h2, h3 {
        font-family: 'Figtree', sans-serif !important;
        font-weight: 700 !important;
    }

    /* Primary button — Fairshot purple gradient */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #814AC8, #DF7AFE) !important;
        border: none !important;
        color: white !important;
        font-family: 'Figtree', sans-serif !important;
        font-weight: 600 !important;
        border-radius: 8px !important;
    }
    .stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, #986AD4, #DF7AFE) !important;
        box-shadow: 0 0 20px rgba(129, 74, 200, 0.4) !important;
    }

    /* Secondary button */
    .stButton > button[kind="secondary"] {
        border: 1px solid #814AC8 !important;
        color: #DF7AFE !important;
        background: transparent !important;
        font-family: 'Figtree', sans-serif !important;
        border-radius: 8px !important;
    }

    /* Metric cards */
    [data-testid="stMetric"] {
        background-color: #1A1A1A;
        border: 1px solid #2A2A2A;
        border-radius: 10px;
        padding: 12px 16px;
    }
    [data-testid="stMetricValue"] {
        color: #FFFFFF !important;
        font-family: 'Figtree', sans-serif !important;
    }
    [data-testid="stMetricLabel"] {
        color: #999999 !important;
    }

    /* Expander styling */
    .streamlit-expanderHeader {
        background-color: #1A1A1A !important;
        border-radius: 8px !important;
        font-family: 'Figtree', sans-serif !important;
    }

    /* Progress bar — purple */
    .stProgress > div > div > div {
        background: linear-gradient(90deg, #814AC8, #DF7AFE) !important;
    }

    /* Divider */
    hr {
        border-color: #2A2A2A !important;
    }

    /* Code blocks */
    .stCodeBlock {
        border: 1px solid #2A2A2A !important;
        border-radius: 8px !important;
    }

    /* Success/warning/error boxes */
    .stAlert {
        border-radius: 8px !important;
    }

    /* Selectbox */
    .stSelectbox [data-baseweb="select"] {
        border-radius: 8px !important;
    }

    /* Logo container in sidebar */
    .sidebar-logo {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 8px 0;
        margin-bottom: 8px;
    }
    .sidebar-logo img {
        width: 36px;
        height: 36px;
        border-radius: 50%;
    }
    .sidebar-logo span {
        font-family: 'Figtree', sans-serif;
        font-weight: 700;
        font-size: 1.3rem;
        color: #FFFFFF;
    }
</style>
""", unsafe_allow_html=True)

# ─── Session State Init ─────────────────────────────────────────────────

for key, default in {
    "pipeline_state": None,
    "pipeline_running": False,
    "pipeline_complete": False,
    "drift_running": False,
    "selected_schema": "Workday Enterprise",
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# Thread-safe queue for cross-thread state propagation
if "state_queue" not in st.session_state:
    st.session_state["state_queue"] = queue.Queue()


# ─── Drain Queue (called on every rerun) ────────────────────────────────

def _drain_queue():
    """Pull all pending state updates from the background thread queue."""
    q: queue.Queue = st.session_state["state_queue"]
    latest = None
    while True:
        try:
            msg = q.get_nowait()
            if msg.get("_done"):
                st.session_state["pipeline_running"] = False
                st.session_state["drift_running"] = False
                # Only mark complete if pipeline didn't error
                state_data = msg.get("state")
                if state_data and state_data.get("current_stage") != "error":
                    st.session_state["pipeline_complete"] = True
                # Freeze elapsed time from pipeline's own timestamps
                if state_data and state_data.get("started_at") and state_data.get("completed_at"):
                    from datetime import datetime
                    try:
                        t0 = datetime.fromisoformat(state_data["started_at"])
                        t1 = datetime.fromisoformat(state_data["completed_at"])
                        st.session_state["pipeline_elapsed"] = (t1 - t0).total_seconds()
                    except (ValueError, TypeError):
                        pass
                if state_data:
                    latest = state_data
            else:
                latest = msg
        except queue.Empty:
            break
    if latest is not None:
        st.session_state["pipeline_state"] = latest

_drain_queue()


# ─── Pipeline Thread ─────────────────────────────────────────────────────


def _make_callback(q: queue.Queue):
    """Create a thread-safe callback that pushes state to the queue."""
    def _callback(state: PipelineState):
        q.put(state.model_dump())
    return _callback


def _run_in_thread(schema_name: str, q: queue.Queue):
    """Runs the async pipeline in a background thread."""
    cb = _make_callback(q)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(run_pipeline(schema_name, callback=cb))
        q.put({"_done": True, "state": result.model_dump()})
    except Exception as e:
        q.put({"_done": True, "state": {"current_stage": "error", "error": str(e)}})
    finally:
        loop.close()


def _run_drift_in_thread(schema_name: str, current_state_data: dict, q: queue.Queue):
    """Runs drift repair in a background thread."""
    from src.agents.orchestrator import run_drift_repair

    cb = _make_callback(q)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        current_state = PipelineState(**current_state_data)
        result = loop.run_until_complete(
            run_drift_repair(schema_name, current_state, callback=cb)
        )
        q.put({"_done": True, "state": result.model_dump()})
    except Exception as e:
        q.put({"_done": True, "state": {"current_stage": "error", "error": str(e)}})
    finally:
        loop.close()


# ─── Helper: human-readable narrative for each stage ────────────────────

STAGE_NARRATIVES = {
    "schema_exploration": "Exploring the {ats} API... discovering fields and data structures",
    "semantic_mapping": "Mapping {ats} fields to Fairshot's universal schema...",
    "code_generation": "Writing integration middleware and validating with Gemini...",
    "data_flow": "Running live data through the pipeline...",
    "completed": "Integration complete. Ready for production.",
    "error": "Pipeline encountered an error.",
    "drift_detection": "Schema drift detected — analyzing breaking changes...",
}

# ─── Sidebar ─────────────────────────────────────────────────────────────

import base64
import os

with st.sidebar:
    logo_path = os.path.join(os.path.dirname(__file__), "static", "logo.jpeg")
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as f:
            logo_b64 = base64.b64encode(f.read()).decode()
        st.markdown(
            f'<div class="sidebar-logo">'
            f'<img src="data:image/jpeg;base64,{logo_b64}" />'
            f'<span>Fairshot</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
    else:
        st.header("Fairshot")

    st.caption("Virtual FDE — Enterprise Integration Concierge")
    st.divider()

    schema_choice = st.selectbox(
        "Select ATS System",
        options=list(SCHEMA_CONFIGS.keys()),
        index=0,
        disabled=st.session_state["pipeline_running"],
    )
    st.session_state["selected_schema"] = schema_choice
    st.caption("Switch between ATS systems to see instant re-integration")

    if st.button(
        "Start Integration",
        type="primary",
        use_container_width=True,
        disabled=st.session_state["pipeline_running"],
    ):
        st.session_state["pipeline_state"] = None
        st.session_state["pipeline_complete"] = False
        st.session_state["pipeline_running"] = True
        st.session_state["pipeline_start_time"] = time.time()
        st.session_state["pipeline_elapsed"] = None
        st.session_state["state_queue"] = queue.Queue()
        thread = threading.Thread(
            target=_run_in_thread,
            args=(schema_choice, st.session_state["state_queue"]),
            daemon=True,
        )
        thread.start()

    st.divider()

    # ── Compact Stage Indicators ──
    state_data = st.session_state.get("pipeline_state")
    current = state_data["current_stage"] if state_data else "idle"

    stages = [
        ("schema_exploration", "Discover Schema"),
        ("semantic_mapping", "Map Fields"),
        ("code_generation", "Generate Code"),
        ("data_flow", "Test Data Flow"),
        ("completed", "Done"),
    ]

    passed_current = False
    for stage_key, stage_label in stages:
        if stage_key == current:
            st.markdown(f"&nbsp;&nbsp;**{stage_label}**", unsafe_allow_html=True)
            passed_current = True
        elif not passed_current and current not in ("idle", "error"):
            st.markdown(f"&nbsp;&nbsp;~~{stage_label}~~", unsafe_allow_html=True)
        else:
            st.markdown(f"&nbsp;&nbsp;{stage_label}", unsafe_allow_html=True)

    if current == "error" and state_data:
        st.error(state_data.get("error", "Unknown error"))

    st.divider()

    # Schema Drift button
    if st.button(
        "Trigger Schema Drift",
        disabled=not st.session_state.get("pipeline_complete", False)
            or st.session_state.get("pipeline_running", False)
            or st.session_state.get("drift_running", False),
        use_container_width=True,
        type="secondary",
    ):
        st.session_state["drift_running"] = True
        st.session_state["pipeline_complete"] = False
        st.session_state["pipeline_start_time"] = time.time()
        st.session_state["pipeline_elapsed"] = None
        st.session_state["state_queue"] = queue.Queue()
        thread = threading.Thread(
            target=_run_drift_in_thread,
            args=(
                st.session_state["selected_schema"],
                st.session_state["pipeline_state"],
                st.session_state["state_queue"],
            ),
            daemon=True,
        )
        thread.start()


# ─── Main Title ──────────────────────────────────────────────────────────

st.markdown(
    '<h1 style="background: linear-gradient(135deg, #814AC8, #DF7AFE); '
    '-webkit-background-clip: text; -webkit-text-fill-color: transparent; '
    'font-size: 2.5rem; margin-bottom: 0;">Virtual FDE</h1>',
    unsafe_allow_html=True,
)
st.caption("Watch an AI agent integrate any ATS with Fairshot — in under 60 seconds")

# ─── Tabs ───────────────────────────────────────────────────────────────

tab_pipeline, tab_explorer = st.tabs(["Integration Pipeline", "Schema Explorer"])

# ═══════════════════════════════════════════════════════════════════════
# TAB 2: Schema Explorer
# ═══════════════════════════════════════════════════════════════════════

with tab_explorer:
    import pandas as pd

    explorer_schema = st.selectbox(
        "Select schema to explore",
        options=list(SCHEMA_CONFIGS.keys()),
        key="explorer_schema_select",
    )
    explorer_config = SCHEMA_CONFIGS[explorer_schema]

    with open(explorer_config["schema_path"], "r") as _f:
        raw_schema = json.load(_f)

    # Overview card
    ov1, ov2, ov3, ov4 = st.columns(4)
    ov1.metric("ATS System", raw_schema.get("ats_name", explorer_schema))
    ov2.metric("Version", raw_schema.get("ats_version", "—"))
    ov3.metric("Auth Type", raw_schema.get("auth_type", "—"))
    entity_count = len(raw_schema.get("entities", {}))
    ov4.metric("Entities", entity_count)

    st.divider()

    # ── Recursive field counter ──
    def _count_fields(fields_dict: dict) -> tuple[int, int, int, int]:
        """Returns (total, deprecated, enum_count, max_depth)."""
        total = 0
        deprecated = 0
        enums = 0
        max_depth = 1
        for fname, fdef in fields_dict.items():
            if isinstance(fdef, dict) and fdef.get("type") in ("object",):
                sub = fdef.get("fields", {})
                st2, sd, se, smd = _count_fields(sub)
                total += st2
                deprecated += sd
                enums += se
                max_depth = max(max_depth, 1 + smd)
            elif isinstance(fdef, dict) and fdef.get("type") == "array":
                items = fdef.get("items", {})
                if isinstance(items, dict) and items.get("type") == "object":
                    sub = items.get("fields", {})
                    st2, sd, se, smd = _count_fields(sub)
                    total += st2
                    deprecated += sd
                    enums += se
                    max_depth = max(max_depth, 2 + smd)
                else:
                    total += 1
            else:
                total += 1
                if isinstance(fdef, dict):
                    if "DEPRECATED" in fname or "DO_NOT_USE" in fname or "LEGACY" in fname:
                        deprecated += 1
                    if fdef.get("enum") or fdef.get("enum_map"):
                        enums += 1
        return total, deprecated, enums, max_depth

    # ── Recursive field renderer ──
    TYPE_COLORS = {
        "string": "blue", "integer": "green", "float": "green",
        "boolean": "orange", "array": "violet", "object": "gray",
    }

    def _render_fields(fields_dict: dict, prefix: str = "", depth: int = 0):
        for fname, fdef in fields_dict.items():
            if not isinstance(fdef, dict):
                continue
            ftype = fdef.get("type", "unknown")
            color = TYPE_COLORS.get(ftype, "red")
            nullable = fdef.get("nullable", True)
            req_badge = "required" if not nullable else "optional"

            # Deprecated badge
            dep = ""
            if "DEPRECATED" in fname or "DO_NOT_USE" in fname or "LEGACY" in fname:
                dep = " :red[DEPRECATED]"

            # Enum badge
            enum_str = ""
            if fdef.get("enum"):
                enum_str = f" `{fdef['enum']}`"
            elif fdef.get("enum_map"):
                enum_str = f" `{list(fdef['enum_map'].values())}`"

            full_path = f"{prefix}{fname}" if prefix else fname

            if ftype == "object" and "fields" in fdef:
                with st.expander(f":{color}[{ftype}] **{fname}**{dep}", expanded=depth < 1):
                    _render_fields(fdef["fields"], prefix=f"{full_path}.", depth=depth + 1)
            elif ftype == "array" and isinstance(fdef.get("items"), dict) and fdef["items"].get("type") == "object":
                with st.expander(f":{color}[{ftype}[]] **{fname}**{dep}", expanded=depth < 1):
                    _render_fields(fdef["items"].get("fields", {}), prefix=f"{full_path}[].", depth=depth + 1)
            else:
                fmt = fdef.get("format", "")
                fmt_str = f" `{fmt}`" if fmt else ""
                desc = fdef.get("description", "")
                desc_str = f" — _{desc}_" if desc else ""
                st.markdown(
                    f"&nbsp;&nbsp;{'&nbsp;&nbsp;' * depth}"
                    f":{color}[{ftype}] **{fname}** "
                    f"({req_badge}){fmt_str}{enum_str}{dep}{desc_str}",
                    unsafe_allow_html=True,
                )

    # ── Per-entity display ──
    for entity_name, entity_data in raw_schema.get("entities", {}).items():
        st.subheader(f"{entity_name}")
        if entity_data.get("endpoint"):
            st.caption(f"Endpoint: `{raw_schema.get('api_base', '')}{entity_data['endpoint']}`")

        fields = entity_data.get("fields", {})
        total_f, dep_f, enum_f, max_d = _count_fields(fields)

        s1, s2, s3, s4 = st.columns(4)
        s1.metric("Fields", total_f)
        s2.metric("Deprecated", dep_f)
        s3.metric("Enums", enum_f)
        s4.metric("Max Depth", max_d)

        with st.expander("Field Schema", expanded=True):
            _render_fields(fields)

        # Sample records
        samples = entity_data.get("sample_records", [])
        if samples:
            with st.expander(f"Sample Records ({len(samples)})", expanded=False):
                for i, rec in enumerate(samples):
                    st.markdown(f"**Record {i + 1}**")
                    st.json(rec)

        st.divider()


# ═══════════════════════════════════════════════════════════════════════
# TAB 1: Integration Pipeline
# ═══════════════════════════════════════════════════════════════════════

with tab_pipeline:
    import pandas as pd

    # ─── Hero Metrics Row ───────────────────────────────────────────────
    if st.session_state.get("pipeline_elapsed") is not None:
        elapsed_s = st.session_state["pipeline_elapsed"]
    elif st.session_state.get("pipeline_start_time"):
        elapsed_s = time.time() - st.session_state["pipeline_start_time"]
    else:
        elapsed_s = None

    if (current == "completed"
            and st.session_state.get("pipeline_elapsed") is None
            and elapsed_s is not None
            and not st.session_state.get("drift_running", False)
            and not st.session_state.get("pipeline_running", False)):
        st.session_state["pipeline_elapsed"] = elapsed_s

    report = state_data.get("schema_report") if state_data else None
    doc = state_data.get("mapping_document") if state_data else None

    mc1, mc2, mc3, mc4 = st.columns(4)
    mc1.metric("Time Elapsed", f"{elapsed_s:.0f}s" if elapsed_s is not None else "—")
    mc2.metric("Fields Discovered", report["total_field_count"] if report else "—")
    mc3.metric("Mapping Coverage", f"{doc['mapping_coverage']:.0%}" if doc else "—")
    mc4.metric("Confidence Score", f"{doc['overall_confidence']:.2f}" if doc else "—")

    # ─── Progress Bar + Narrative Status ────────────────────────────────
    ats_name = st.session_state.get("selected_schema", "ATS")
    narrative = STAGE_NARRATIVES.get(current, "").format(ats=ats_name)

    if current == "completed":
        st.success(f"Integration complete. {ats_name} integrated with Fairshot in {elapsed_s:.0f}s — ready for production.")
    elif current == "error":
        st.error(f"Pipeline failed: {state_data.get('error', 'Unknown')}" if state_data else "Pipeline failed")
    elif st.session_state["pipeline_running"] or st.session_state.get("drift_running", False):
        progress_pct = state_data.get("progress_percent", 0) if state_data else 0
        st.progress(int(progress_pct), text=narrative)
    else:
        st.info("Select an ATS system and click **Start Integration** to begin.")

    st.divider()

    # ─── Schema Drift Alert ─────────────────────────────────────────────
    if state_data and state_data.get("drift_detected"):
        st.warning(
            f"Schema Drift Detected — **{len(state_data.get('drift_changes', []))} breaking changes** "
            f"in the {ats_name} API"
        )
        for change_desc in state_data.get("drift_changes", []):
            st.markdown(f"- {change_desc}")
        vr_drift = state_data.get("validation_result", {}) or {}
        if vr_drift.get("drift_repaired"):
            st.success(
                f"Auto-Repaired: {vr_drift.get('changes_repaired', 0)} changes resolved — "
                f"zero manual intervention required"
            )
        st.divider()

    # ─── Progressive Stage Summaries ────────────────────────────────────
    if report:
        st.success(
            f"Schema Explored: **{report['total_field_count']} fields** across "
            f"**{len(report.get('endpoints', []))} endpoints**, "
            f"max nesting depth {report.get('nesting_depth', '?')}"
        )
        with st.expander("View discovered fields", expanded=False):
            for field in report.get("fields", [])[:30]:
                badge = "🔴" if field.get("anomalies") else "🟢"
                st.markdown(
                    f"{badge} `{field['nested_path']}` — "
                    f"_{field['field_type']}_ "
                    f"{'(nullable)' if field.get('nullable') else '(required)'}"
                )
            if len(report.get("fields", [])) > 30:
                st.caption(f"...and {len(report['fields']) - 30} more fields")

    if doc:
        st.success(
            f"Mapping Complete: **{len(doc['mappings'])} fields mapped** — "
            f"**{doc['mapping_coverage']:.0%} coverage**, "
            f"{doc['overall_confidence']:.2f} avg confidence"
        )
        with st.expander("View field mappings", expanded=False):
            for m in doc["mappings"]:
                conf = m["confidence_score"]
                badge = "🟢" if conf >= 0.9 else ("🟡" if conf >= 0.7 else "🔴")
                st.markdown(
                    f"{badge} `{m['ats_field']}` → **{m['fairshot_field']}** "
                    f"({conf:.2f}) — _{m['transform_function']}_"
                )
            if doc.get("unmapped_ats_fields"):
                st.caption(f"{len(doc['unmapped_ats_fields'])} ATS fields had no Fairshot equivalent")

    middleware = state_data.get("generated_middleware") if state_data else None
    if middleware:
        line_count = middleware.count("\n") + 1
        st.success(f"Middleware Generated: **{line_count} lines** of Python, validated by Gemini")
        with st.expander("View generated code", expanded=False):
            st.code(middleware, language="python", line_numbers=True)

    # ─── THE HERO: Before → After Transformation ───────────────────────
    vr = (state_data.get("validation_result") or {}) if state_data else {}
    sample_in = vr.get("sample_input", {})
    sample_out = vr.get("sample_output", {})

    if sample_in and sample_out and isinstance(sample_in, dict) and isinstance(sample_out, dict):
        st.divider()
        st.markdown(
            '<h3 style="color: #DF7AFE; margin-bottom: 4px;">The Result</h3>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f"**{len(sample_in)} messy ATS fields → {len(sample_out)} clean Fairshot fields "
            f"in {elapsed_s:.0f}s — zero manual configuration**"
            if elapsed_s else
            f"**{len(sample_in)} messy ATS fields → {len(sample_out)} clean Fairshot fields — zero manual configuration**"
        )

        col_before, col_after = st.columns(2)

        with col_before:
            st.markdown(f"**Raw {ats_name} Record**")
            before_items = []
            for k, v in list(sample_in.items())[:12]:
                display_val = str(v) if not isinstance(v, (dict, list)) else json.dumps(v)[:60] + "..."
                before_items.append({"Field": k, "Value": display_val})
            if before_items:
                st.dataframe(pd.DataFrame(before_items), use_container_width=True, hide_index=True)
            if len(sample_in) > 12:
                st.caption(f"+ {len(sample_in) - 12} more fields")

        with col_after:
            st.markdown("**Fairshot API Payload**")
            after_items = []
            for k, v in list(sample_out.items())[:12]:
                display_val = str(v) if not isinstance(v, (dict, list)) else json.dumps(v)[:60] + "..."
                after_items.append({"Field": k, "Value": display_val})
            if after_items:
                st.dataframe(pd.DataFrame(after_items), use_container_width=True, hide_index=True)

        test_status = vr.get("data_flow_test", "unknown")
        if test_status == "passed":
            st.success("Live data flow test passed — all mapped fields transformed correctly")
        else:
            st.error("Data flow test failed")

        with st.expander("View full JSON payloads", expanded=False):
            j1, j2 = st.columns(2)
            with j1:
                st.markdown("**Input**")
                st.json(sample_in)
            with j2:
                st.markdown("**Output**")
                st.json(sample_out)

    # ─── Activity Log (collapsed) ──────────────────────────────────────
    st.divider()
    with st.expander("Activity Log", expanded=False):
        if state_data and state_data.get("logs"):
            for log in reversed(state_data["logs"]):
                ts = log.get("timestamp", "")
                if isinstance(ts, str) and "T" in ts:
                    ts = ts.split("T")[1][:8]
                stage = log.get("stage", "").replace("_", " ").title()
                st.markdown(f"`{ts}` **{stage}** — {log['message']}")
        else:
            st.caption("No events yet. Click Start Integration to begin.")

# ─── Auto-refresh while running ─────────────────────────────────────────

if st.session_state["pipeline_running"] or st.session_state.get("drift_running", False):
    time.sleep(1.5)
    st.rerun()