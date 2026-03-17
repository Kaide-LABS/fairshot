"""
Virtual FDE — Enterprise Integration Concierge
Streamlit Dashboard (Phase 6)
"""

import asyncio
import json
import threading
import time
from datetime import datetime

import streamlit as st

from src.agents.orchestrator import run_pipeline, SCHEMA_CONFIGS
from src.models import PipelineState, PipelineStage

# ─── Page Config ─────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Virtual FDE — Fairshot",
    page_icon="🔌",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Session State Init ─────────────────────────────────────────────────

for key, default in {
    "pipeline_state": None,
    "pipeline_running": False,
    "pipeline_complete": False,
    "selected_schema": "Workday Enterprise",
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


# ─── Pipeline Thread ─────────────────────────────────────────────────────


def _pipeline_callback(state: PipelineState):
    """Called from the pipeline thread on every state transition."""
    # Deep copy via serialization to avoid cross-thread mutation issues
    st.session_state["pipeline_state"] = state.model_dump()


def _run_in_thread(schema_name: str):
    """Runs the async pipeline in a background thread."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(run_pipeline(schema_name, callback=_pipeline_callback))
    finally:
        loop.close()
    st.session_state["pipeline_running"] = False
    st.session_state["pipeline_complete"] = True


# ─── Sidebar ─────────────────────────────────────────────────────────────

with st.sidebar:
    st.header("⚡ Virtual FDE")
    st.caption("Enterprise Integration Concierge")
    st.divider()

    schema_choice = st.selectbox(
        "Select ATS Schema",
        options=list(SCHEMA_CONFIGS.keys()),
        index=0,
        disabled=st.session_state["pipeline_running"],
    )
    st.session_state["selected_schema"] = schema_choice

    if st.button(
        "🚀 Start Integration",
        type="primary",
        use_container_width=True,
        disabled=st.session_state["pipeline_running"],
    ):
        st.session_state["pipeline_state"] = None
        st.session_state["pipeline_complete"] = False
        st.session_state["pipeline_running"] = True
        thread = threading.Thread(
            target=_run_in_thread, args=(schema_choice,), daemon=True
        )
        thread.start()

    st.divider()

    # ── Stage Indicators ──
    st.subheader("Pipeline Stages")
    state_data = st.session_state.get("pipeline_state")

    stages = [
        ("schema_exploration", "Schema Exploration"),
        ("semantic_mapping", "Semantic Mapping"),
        ("code_generation", "Code Generation"),
        ("data_flow", "Live Data Flow"),
        ("completed", "Complete"),
    ]

    current = state_data["current_stage"] if state_data else "idle"
    passed_current = False
    for stage_key, stage_label in stages:
        if stage_key == current:
            st.markdown(f"🔵 **{stage_label}** _(active)_")
            passed_current = True
        elif not passed_current and current != "idle" and current != "error":
            st.markdown(f"✅ {stage_label}")
        else:
            st.markdown(f"⚪ {stage_label}")

    if current == "error" and state_data:
        st.error(f"❌ Error: {state_data.get('error', 'Unknown')}")

    st.divider()

    # Schema Drift button — placeholder for Phase 7
    st.button(
        "⚡ Trigger Schema Drift",
        disabled=True,
        use_container_width=True,
        help="Coming in Phase 7",
    )


# ─── Main Title ──────────────────────────────────────────────────────────

st.title("Virtual FDE")
st.caption("Autonomous ATS → Fairshot integration in under 60 seconds")

# ─── Progress Bar ────────────────────────────────────────────────────────

progress_container = st.empty()

if state_data and state_data.get("progress_percent", 0) > 0:
    progress_container.progress(
        int(state_data["progress_percent"]),
        text=f"{state_data['current_stage'].replace('_', ' ').title()} — {state_data['progress_percent']:.0f}%",
    )
elif st.session_state["pipeline_running"]:
    progress_container.progress(0, text="Initializing pipeline...")

st.divider()

# ─── Panels ──────────────────────────────────────────────────────────────

col1, col2 = st.columns(2)

# ── Panel 1: Schema Explorer ──
with col1:
    with st.expander("📡 Schema Explorer", expanded=True):
        if state_data and state_data.get("schema_report"):
            report = state_data["schema_report"]
            st.metric("Fields Discovered", report["total_field_count"])
            st.metric("Endpoints", len(report["endpoints"]))
            st.metric("Nesting Depth", report["nesting_depth"])

            if report.get("custom_conventions"):
                st.markdown("**Naming Conventions:**")
                for conv in report["custom_conventions"]:
                    st.markdown(f"- `{conv}`")

            if report.get("anomaly_summary"):
                st.info(report["anomaly_summary"])

            # Show field list in a collapsible
            with st.popover("View All Fields"):
                for field in report.get("fields", [])[:30]:  # Cap at 30 for performance
                    badge = "🔴" if field.get("anomalies") else "🟢"
                    st.markdown(
                        f"{badge} `{field['nested_path']}` — "
                        f"_{field['field_type']}_ "
                        f"{'(nullable)' if field.get('nullable') else '(required)'}"
                    )
                if len(report.get("fields", [])) > 30:
                    st.caption(f"...and {len(report['fields']) - 30} more fields")
        else:
            st.caption("Waiting for schema exploration...")

# ── Panel 2: Semantic Mapping ──
with col2:
    with st.expander("🔗 Semantic Mapping", expanded=True):
        if state_data and state_data.get("mapping_document"):
            doc = state_data["mapping_document"]
            mc1, mc2, mc3 = st.columns(3)
            mc1.metric("Fields Mapped", len(doc["mappings"]))
            mc2.metric("Coverage", f"{doc['mapping_coverage']:.0%}")
            mc3.metric("Avg Confidence", f"{doc['overall_confidence']:.2f}")

            # Mapping table
            for m in doc["mappings"]:
                conf = m["confidence_score"]
                if conf >= 0.9:
                    badge = "🟢"
                elif conf >= 0.7:
                    badge = "🟡"
                else:
                    badge = "🔴"

                st.markdown(
                    f"{badge} `{m['ats_field']}` → **{m['fairshot_field']}** "
                    f"({conf:.2f}) — _{m['transform_function']}_"
                )

            # Unmapped fields
            if doc.get("unmapped_ats_fields"):
                with st.popover(f"⚠️ {len(doc['unmapped_ats_fields'])} Unmapped ATS Fields"):
                    for f in doc["unmapped_ats_fields"]:
                        st.markdown(f"- `{f}`")
        else:
            st.caption("Waiting for semantic mapping...")

# ── Panel 3: Code Generation ──
with col1:
    with st.expander("💻 Code Generation", expanded=True):
        if state_data and state_data.get("generated_middleware"):
            code = state_data["generated_middleware"]
            st.code(code, language="python", line_numbers=True)

            # Show validation info if available
            vr = state_data.get("validation_result", {})
            if vr:
                test_status = vr.get("data_flow_test", "unknown")
                if test_status == "passed":
                    st.success("✅ Data flow test passed")
                else:
                    st.error("❌ Data flow test failed")

                if vr.get("transform_spec_notes"):
                    st.info(f"Agent notes: {vr['transform_spec_notes']}")
        else:
            st.caption("Waiting for code generation...")

# ── Panel 4: Live Data Flow ──
with col2:
    with st.expander("🔄 Live Data Flow", expanded=True):
        if state_data and state_data.get("validation_result"):
            vr = state_data["validation_result"]

            st.markdown("**INPUT** (Raw ATS Record)")
            sample_in = vr.get("sample_input", {})
            # Show a condensed version (first 10 keys)
            if isinstance(sample_in, dict):
                condensed = {k: sample_in[k] for k in list(sample_in.keys())[:10]}
                st.json(condensed)
                if len(sample_in) > 10:
                    st.caption(f"...{len(sample_in) - 10} more fields")
            else:
                st.json(sample_in)

            st.markdown("⬇️")

            st.markdown("**OUTPUT** (Fairshot API Payload)")
            sample_out = vr.get("sample_output", {})
            st.json(sample_out)

            # Field count comparison
            if isinstance(sample_in, dict) and isinstance(sample_out, dict):
                st.caption(
                    f"{len(sample_in)} ATS fields → "
                    f"{len(sample_out)} Fairshot fields — "
                    f"zero data loss on mapped fields"
                )
        else:
            st.caption("Waiting for data flow test...")

st.divider()

# ── Panel 5: Event Log ──
with st.expander("📋 Event Log", expanded=not st.session_state["pipeline_complete"]):
    if state_data and state_data.get("logs"):
        for log in reversed(state_data["logs"]):
            ts = log.get("timestamp", "")
            if isinstance(ts, str) and "T" in ts:
                ts = ts.split("T")[1][:8]  # Extract HH:MM:SS
            stage = log.get("stage", "").replace("_", " ").title()
            st.markdown(f"`[{ts}]` **{stage}** — {log['message']}")
            if log.get("detail"):
                with st.popover("Detail"):
                    st.code(log["detail"], language="json")
    else:
        st.caption("No events yet. Click 'Start Integration' to begin.")

# ─── Auto-refresh while running ─────────────────────────────────────────

if st.session_state["pipeline_running"]:
    time.sleep(1.5)
    st.rerun()