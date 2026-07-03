"""
app.py
------
Streamlit dashboard for the SOC Alert Fatigue Reduction Engine.

Run locally:
    streamlit run app.py

Deploy:
    Push this repo to GitHub, then deploy via https://share.streamlit.io
    (Streamlit Community Cloud) pointing at app.py.
"""

import io

import pandas as pd
import plotly.express as px
import streamlit as st

from generate_data import generate_alerts
from scoring_engine import score_alerts
from correlation import correlate_alerts

st.set_page_config(
    page_title="SOC Alert Fatigue Reduction Engine",
    page_icon="🛡️",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Sidebar - data source & controls
# ---------------------------------------------------------------------------

st.sidebar.title("🛡️ Controls")
st.sidebar.markdown(
    "Simulate a SOC's daily alert stream, then see how scoring + "
    "correlation logic cuts noise down to actionable incidents."
)

data_source = st.sidebar.radio(
    "Data source", ["Generate synthetic data", "Upload my own CSV"]
)

if data_source == "Generate synthetic data":
    days = st.sidebar.slider("Days to simulate", 1, 30, 7)
    alerts_per_day = st.sidebar.slider("Raw alerts per day", 50, 1000, 400, step=50)
    regenerate = st.sidebar.button("🔁 Regenerate data", use_container_width=True)

    if "raw_df" not in st.session_state or regenerate:
        st.session_state["raw_df"] = generate_alerts(days, alerts_per_day)
    raw_df = st.session_state["raw_df"]
else:
    uploaded = st.sidebar.file_uploader(
        "Upload raw alerts CSV",
        type=["csv"],
        help=(
            "Expected columns: timestamp, alert_name, base_severity, src_ip, "
            "user, asset, asset_criticality, is_chronic_noise_source"
        ),
    )
    if uploaded is None:
        st.info("Upload a CSV in the sidebar, or switch to synthetic data to explore the demo.")
        st.stop()
    raw_df = pd.read_csv(uploaded)

st.sidebar.markdown("---")
window = st.sidebar.slider(
    "Correlation window (minutes)", 5, 60, 20,
    help="Alerts from the same source IP + user within this window get grouped into one incident."
)
import correlation as _corr_mod
_corr_mod.CORRELATION_WINDOW_MINUTES = window

# ---------------------------------------------------------------------------
# Pipeline: score -> correlate
# ---------------------------------------------------------------------------

scored_df = score_alerts(raw_df)
incidents_df = correlate_alerts(scored_df)

# ---------------------------------------------------------------------------
# Header + top-line metrics
# ---------------------------------------------------------------------------

st.title("🛡️ SOC Alert Fatigue Reduction Engine")
st.caption(
    "Turns a raw, noisy SIEM alert stream into a prioritized, correlated "
    "incident queue — so analysts spend time on real threats, not noise."
)

raw_count = len(scored_df)
incident_count = len(incidents_df)
reduction_pct = 100 * (1 - incident_count / raw_count) if raw_count else 0
high_priority_incidents = (incidents_df["highest_priority"] == "High").sum() if raw_count else 0

c1, c2, c3, c4 = st.columns(4)
c1.metric("Raw Alerts", f"{raw_count:,}")
c2.metric("Correlated Incidents", f"{incident_count:,}")
c3.metric("Volume Reduction", f"{reduction_pct:.1f}%")
c4.metric("High-Priority Incidents", f"{high_priority_incidents:,}")

st.markdown("---")

# ---------------------------------------------------------------------------
# Charts row
# ---------------------------------------------------------------------------

col1, col2 = st.columns(2)

with col1:
    st.subheader("Raw Alerts by Severity")
    sev_counts = scored_df["base_severity"].value_counts().reindex(
        ["low", "medium", "high", "critical"]
    ).fillna(0)
    fig1 = px.bar(
        x=sev_counts.index, y=sev_counts.values,
        labels={"x": "Severity", "y": "Count"},
        color=sev_counts.index,
        color_discrete_map={
            "low": "#4C9A2A", "medium": "#E7C11B",
            "high": "#E76F1B", "critical": "#C21807",
        },
    )
    fig1.update_layout(showlegend=False, height=350)
    st.plotly_chart(fig1, use_container_width=True)

with col2:
    st.subheader("Alert Volume Over Time")
    ts_counts = (
        scored_df.set_index("timestamp")
        .resample("D")
        .size()
        .rename("alerts")
        .reset_index()
    )
    fig2 = px.line(ts_counts, x="timestamp", y="alerts", markers=True)
    fig2.update_layout(height=350)
    st.plotly_chart(fig2, use_container_width=True)

col3, col4 = st.columns(2)

with col3:
    st.subheader("Top Source IPs by Alert Count")
    top_ips = scored_df["src_ip"].value_counts().head(10).reset_index()
    top_ips.columns = ["src_ip", "count"]
    fig3 = px.bar(top_ips, x="count", y="src_ip", orientation="h")
    fig3.update_layout(height=350, yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig3, use_container_width=True)

with col4:
    st.subheader("Incident Priority Breakdown")
    if incident_count:
        prio_counts = incidents_df["highest_priority"].value_counts().reindex(
            ["Info", "Low", "Medium", "High"]
        ).fillna(0)
        fig4 = px.pie(
            names=prio_counts.index, values=prio_counts.values, hole=0.45,
            color=prio_counts.index,
            color_discrete_map={
                "Info": "#4C9A2A", "Low": "#8FBF3F",
                "Medium": "#E7C11B", "High": "#C21807",
            },
        )
        fig4.update_layout(height=350)
        st.plotly_chart(fig4, use_container_width=True)

st.markdown("---")

# ---------------------------------------------------------------------------
# Triage queue - the main analyst-facing table
# ---------------------------------------------------------------------------

st.subheader("🚨 Prioritized Incident Triage Queue")
st.caption("This is what an analyst would actually work from — sorted by risk, not by arrival time.")

if incident_count:
    priority_filter = st.multiselect(
        "Filter by priority", ["High", "Medium", "Low", "Info"],
        default=["High", "Medium"],
    )
    display_df = incidents_df[incidents_df["highest_priority"].isin(priority_filter)] if priority_filter else incidents_df

    st.dataframe(
        display_df[[
            "incident_id", "highest_priority", "max_risk_score", "avg_risk_score",
            "alert_count", "src_ip", "user", "asset", "alert_types",
            "start_time", "end_time", "is_multi_stage",
        ]],
        use_container_width=True,
        hide_index=True,
    )

    csv_buf = io.StringIO()
    display_df.to_csv(csv_buf, index=False)
    st.download_button(
        "⬇️ Download triage queue as CSV",
        data=csv_buf.getvalue(),
        file_name="triage_queue.csv",
        mime="text/csv",
    )
else:
    st.info("No incidents to display.")

with st.expander("🔍 View raw, un-correlated alert feed (what analysts see WITHOUT this tool)"):
    st.dataframe(
        scored_df[[
            "alert_id", "timestamp", "alert_name", "base_severity",
            "risk_score", "priority", "src_ip", "user", "asset",
            "is_chronic_noise_source",
        ]].sort_values("timestamp", ascending=False),
        use_container_width=True,
        hide_index=True,
    )

st.markdown("---")
st.caption(
    "Built as a SOC analyst portfolio project — demonstrates alert triage logic, "
    "correlation rule design, and SIEM-style dashboarding. Not a production "
    "detection system; scoring weights are illustrative and should be tuned "
    "against real environment data."
)
