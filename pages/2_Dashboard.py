import plotly.express as px
import streamlit as st

from src import config, db, queries, ui_filters

st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")
con = db.get_connection()
mapping = config.FIELD_MAPPING

st.title("📊 Dashboard")

if not db.table_exists(con, "events"):
    st.info("No data yet. Import data first on the Import Data page.")
    st.stop()

fs = ui_filters.render_sidebar_filters(con, mapping)

total = queries.count_events(con, fs)
st.metric("Total Events (filtered)", f"{total:,}")

if total == 0:
    st.info("No events match the current filter.")
    st.stop()

st.divider()

col_left, col_right = st.columns([2, 1])

with col_left:
    st.subheader("Event Trend")
    granularity = st.selectbox("Granularity", ["hour", "day", "week", "month"], index=1)
    if mapping.get("event_time"):
        trend_df = queries.events_over_time(con, fs, mapping, granularity)
        if not trend_df.empty:
            fig = px.line(trend_df, x="bucket", y="events", markers=True)
            fig.update_layout(margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig, width="stretch")
        else:
            st.info("No time data to display.")
    else:
        st.info("Map the 'event_time' field to see the trend.")

with col_right:
    st.subheader("Content Aware: Action")
    if mapping.get("action"):
        action_df = queries.action_breakdown(con, fs, mapping)
        if not action_df.empty:
            fig = px.pie(action_df, names="action", values="events", hole=0.45)
            fig.update_layout(margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig, width="stretch")
    else:
        st.info("Map the 'action' field to see this breakdown.")

st.divider()

c1, c2 = st.columns(2)
with c1:
    st.subheader("Top Users")
    if mapping.get("user"):
        df = queries.top_values(con, fs, mapping, "user")
        if not df.empty:
            fig = px.bar(df.sort_values("events"), x="events", y="value", orientation="h")
            fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), yaxis_title=None)
            st.plotly_chart(fig, width="stretch")

with c2:
    st.subheader("Top Endpoints")
    if mapping.get("endpoint"):
        df = queries.top_values(con, fs, mapping, "endpoint")
        if not df.empty:
            fig = px.bar(df.sort_values("events"), x="events", y="value", orientation="h")
            fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), yaxis_title=None)
            st.plotly_chart(fig, width="stretch")

c3, c4 = st.columns(2)
with c3:
    st.subheader("Top Policy")
    if mapping.get("policy"):
        df = queries.top_values(con, fs, mapping, "policy")
        if not df.empty:
            fig = px.bar(df.sort_values("events"), x="events", y="value", orientation="h")
            fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), yaxis_title=None)
            st.plotly_chart(fig, width="stretch")

with c4:
    st.subheader("Event Type")
    if mapping.get("event_type"):
        df = queries.event_type_breakdown(con, fs, mapping)
        if not df.empty:
            fig = px.bar(df.sort_values("events"), x="events", y="event_type", orientation="h")
            fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), yaxis_title=None)
            st.plotly_chart(fig, width="stretch")

c5, c6 = st.columns(2)
with c5:
    st.subheader("Top Destination")
    if mapping.get("destination"):
        df = queries.top_values(con, fs, mapping, "destination")
        if not df.empty:
            fig = px.bar(df.sort_values("events"), x="events", y="value", orientation="h")
            fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), yaxis_title=None)
            st.plotly_chart(fig, width="stretch")

with c6:
    st.subheader("Destination Type")
    if mapping.get("destination_type"):
        df = queries.top_values(con, fs, mapping, "destination_type")
        if not df.empty:
            fig = px.bar(df.sort_values("events"), x="events", y="value", orientation="h")
            fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), yaxis_title=None)
            st.plotly_chart(fig, width="stretch")
