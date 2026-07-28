import plotly.express as px
import streamlit as st

from src import config, db, queries, ui_filters

st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")
con = db.get_connection()
mapping = config.FIELD_MAPPING

st.title("📊 Dashboard")

if not db.table_exists(con, "events"):
    st.info("Belum ada data. Import data terlebih dahulu di halaman Import Data.")
    st.stop()

fs = ui_filters.render_sidebar_filters(con, mapping)

total = queries.count_events(con, fs)
st.metric("Total event (sesuai filter)", f"{total:,}")

if total == 0:
    st.info("Tidak ada event yang cocok dengan filter saat ini.")
    st.stop()

st.divider()

col_left, col_right = st.columns([2, 1])

with col_left:
    st.subheader("Tren Event")
    granularity = st.selectbox("Granularitas", ["hour", "day", "week", "month"], index=1)
    if mapping.get("event_time"):
        trend_df = queries.events_over_time(con, fs, mapping, granularity)
        if not trend_df.empty:
            fig = px.line(trend_df, x="bucket", y="events", markers=True)
            fig.update_layout(margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig, width="stretch")
        else:
            st.info("Tidak ada data waktu untuk ditampilkan.")
    else:
        st.info("Petakan field 'event_time' untuk melihat tren.")

with col_right:
    st.subheader("Content Aware: Action")
    if mapping.get("action"):
        action_df = queries.action_breakdown(con, fs, mapping)
        if not action_df.empty:
            fig = px.pie(action_df, names="action", values="events", hole=0.45)
            fig.update_layout(margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig, width="stretch")
    else:
        st.info("Petakan field 'action' untuk melihat breakdown ini.")

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
