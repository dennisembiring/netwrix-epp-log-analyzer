import streamlit as st

from src import config, db, queries

st.set_page_config(page_title=config.APP_TITLE, page_icon="🛡️", layout="wide")

con = db.get_connection()

st.title("🛡️ " + config.APP_TITLE)
st.caption(
    "Import, manage, and analyze millions of Content Aware Protection (CAP) "
    "CSV export events from Netwrix Endpoint Protector without Excel's "
    "limitations, powered by DuckDB."
)

total_events = db.total_event_count(con)
datasets_df = db.list_datasets(con)
latest_event = queries.latest_event_time(con, config.FIELD_MAPPING) if total_events else None

c1, c2, c3 = st.columns(3)
c1.metric("Total Events", f"{total_events:,}")
c2.metric("Datasets Imported", len(datasets_df))
c3.metric("Latest Data", str(latest_event) if latest_event is not None else "-")

st.divider()

if total_events == 0:
    st.info(
        "No data yet. Open the **1 Import Data** page in the sidebar to "
        "import Content Aware Protection (CAP) export CSV files."
    )
else:
    st.success("The app is ready to use. Use the sidebar menu to start your analysis.")

st.markdown(
    """
### Navigation
- **1 Import Data**: import CAP CSV files (upload or local path)
- **2 Dashboard**: event trends, Content Aware statistics (Blocked/Allowed/Detected)
- **3 Log Explorer**: full-text search, multi-criteria filters, large data table
- **4 SQL Query**: run free-form SQL queries against all the data
- **5 Reports**: export analysis results to CSV, Excel, or PDF

The supported CSV columns follow the fixed Netwrix Endpoint Protector CAP
export schema, so no manual column mapping is needed.
"""
)

if not datasets_df.empty:
    st.subheader("Imported Datasets")
    st.dataframe(datasets_df, width="stretch", hide_index=True)
