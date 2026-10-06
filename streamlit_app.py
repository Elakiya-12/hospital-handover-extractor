import os
import sys

import streamlit as st

# The NLP and database modules live inside the backend folder.
BACKEND_DIR = os.path.join(os.path.dirname(__file__), "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from nlp_engine import extract_handover
from database import init_db, save_analysis, get_recent_handovers, get_dashboard

st.set_page_config(
    page_title="Hospital Handover Extractor",
    page_icon="🏥",
    layout="wide",
)

init_db()

st.markdown("""
<style>
.main-title { font-size: 2.2rem; font-weight: 700; margin-bottom: 0.2rem; }
.subtitle { color: #666; margin-bottom: 1.5rem; }
.card {
    padding: 1rem 1.2rem;
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    background: white;
    margin-bottom: 1rem;
}
.small-label { color: #666; font-size: 0.9rem; }
</style>
""", unsafe_allow_html=True)


def format_entities(entities):
    """Convert NLP entity dictionaries into a clean table for Streamlit."""
    return [
        {
            "Entity": entity.get("text", ""),
            "Type": entity.get("type", ""),
            "Start": entity.get("start", ""),
            "End": entity.get("end", ""),
        }
        for entity in entities
    ]


def format_events(events):
    """Flatten nested event entities so the UI never shows [object Object]."""
    rows = []
    for event in events:
        related = event.get("entities", [])
        related_text = ", ".join(
            f"{item.get('text', '')} ({item.get('type', '')})" for item in related
        )
        rows.append(
            {
                "Event": event.get("type", ""),
                "Status": event.get("status", ""),
                "Time": event.get("time") or "—",
                "Information": related_text or event.get("text", ""),
            }
        )
    return rows


def format_history(history):
    """Flatten saved history for a readable table."""
    rows = []
    for item in history:
        rows.append(
            {
                "Handover ID": item.get("id", ""),
                "Patient ID": item.get("patient_id", ""),
                "Created At": item.get("created_at", ""),
                "Handover": item.get("handover_text", ""),
                "Entities": len(item.get("entities", [])),
                "Events": len(item.get("events", [])),
                "Pending Tasks": len(item.get("pending_tasks", [])),
            }
        )
    return rows


st.markdown('<div class="main-title">🏥 Hospital Handover Extractor</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="subtitle">Convert unstructured clinical handover notes into structured clinical information.</div>',
    unsafe_allow_html=True,
)

# Read dashboard AFTER previous analysis has been saved.
dashboard = get_dashboard()
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Total Handovers", dashboard.get("total_handovers", 0))
with col2:
    st.metric("Patients", dashboard.get("unique_patients", 0))
with col3:
    st.metric("Pending Tasks", dashboard.get("pending_tasks", 0))

st.divider()

left, right = st.columns([1, 1.2])

with left:
    st.subheader("Enter Handover Information")
    patient_id = st.text_input("Patient ID", placeholder="Example: P1001")
    handover_text = st.text_area(
        "Handover Note",
        height=230,
        placeholder=(
            "Example: Patient was shifted to Ward 3 at 4 PM. BP was stable. "
            "At 5:30 PM, patient complained of chest discomfort. ECG was ordered "
            "and cardiology review is pending. Paracetamol was given at 6 PM."
        ),
    )

    analyze = st.button("🧠 Analyze Handover", type="primary", use_container_width=True)

    if analyze:
        if not patient_id.strip() or not handover_text.strip():
            st.error("Please enter both Patient ID and Handover Note.")
        else:
            analysis = extract_handover(handover_text)
            handover_id = save_analysis(patient_id.strip(), handover_text.strip(), analysis)
            st.session_state["last_analysis"] = {
                "handover_id": handover_id,
                "patient_id": patient_id.strip(),
                "handover_text": handover_text.strip(),
                **analysis,
            }
            st.success(f"Handover analyzed and saved. Handover ID: {handover_id}")
            st.rerun()

with right:
    st.subheader("Extracted Information")
    result = st.session_state.get("last_analysis")

    if not result:
        st.info("Enter a handover note and click **Analyze Handover**.")
    else:
        st.write(f"**Patient ID:** {result['patient_id']}")

        st.markdown("### Entities")
        entities = result.get("entities", [])
        if entities:
            st.table(format_entities(entities))
        else:
            st.write("No entities detected.")

        st.markdown("### Events")
        events = result.get("events", [])
        if events:
            st.table(format_events(events))
        else:
            st.write("No events detected.")

        st.markdown("### Pending Tasks")
        pending = result.get("pending_tasks", [])
        if pending:
            for task in pending:
                task_name = task.get("task", "Pending clinical task")
                task_time = task.get("time") or "—"
                st.warning(
                    f"⏳ **{task_name}**  \n"
                    f"Status: **{task.get('status', 'PENDING')}**  | Time: **{task_time}**"
                )
        else:
            st.success("No pending tasks detected.")

st.divider()

st.subheader("📋 Handover History")
history = get_recent_handovers()
if history:
    st.table(format_history(history))
else:
    st.info("No saved handovers yet.")

st.subheader("📊 Entity Summary")
summary = dashboard.get("entity_counts", [])
if summary:
    summary_rows = [
        {"Entity Type": item.get("type", ""), "Count": item.get("c", 0)}
        for item in summary
    ]
    st.table(summary_rows)
else:
    st.info("No entity summary available yet.")

st.caption(
    "Student prototype: use synthetic or de-identified data rather than real patient information."
)
