import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode

from src import config, db, export_utils, queries, ui_filters

st.set_page_config(page_title="Log Explorer", page_icon="🔍", layout="wide")
con = db.get_connection()
mapping = config.FIELD_MAPPING

st.title("🔍 Log Explorer")

if not db.table_exists(con, "events"):
    st.info("No data yet. Import data first on the Import Data page.")
    st.stop()

fs = ui_filters.render_sidebar_filters(con, mapping)

total = queries.count_events(con, fs)
st.caption(f"{total:,} events match the current filter.")

if total == 0:
    st.stop()

page_size = st.sidebar.selectbox("Rows per page", [100, 500, 1000, 5000], index=1)
max_page = max((total - 1) // page_size, 0)
page = st.number_input("Page", min_value=0, max_value=max_page, value=0, step=1)

df = queries.fetch_page(con, fs, mapping, limit=page_size, offset=page * page_size)

gb = GridOptionsBuilder.from_dataframe(df)
gb.configure_default_column(filterable=True, sortable=True, resizable=True)
gb.configure_pagination(enabled=False)
grid_options = gb.build()

AgGrid(
    df,
    gridOptions=grid_options,
    update_mode=GridUpdateMode.NO_UPDATE,
    height=600,
    theme="balham",
    fit_columns_on_grid_load=False,
)

st.divider()
st.subheader("Export This Page")
c1, c2, c3 = st.columns(3)
c1.download_button(
    "⬇️ CSV", export_utils.to_csv_bytes(df), file_name="log_explorer_export.csv", mime="text/csv"
)
c2.download_button(
    "⬇️ Excel",
    export_utils.to_excel_bytes(df),
    file_name="log_explorer_export.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)
c3.download_button(
    "⬇️ PDF",
    export_utils.to_pdf_bytes("Log Explorer Export", [f"Total rows (this page): {len(df)}"], df),
    file_name="log_explorer_export.pdf",
    mime="application/pdf",
)
st.caption("Export only covers the page currently displayed.")

st.divider()
st.subheader("Export All Filtered Results")
st.caption(
    f"Export all {total:,} rows matching the current sidebar filter "
    "(not just the page currently displayed)."
)

_EXCEL_ROW_LIMIT = 1_048_576 - 1  # minus header row
if total > _EXCEL_ROW_LIMIT:
    st.warning(
        f"{total:,} rows exceed Excel's maximum ({_EXCEL_ROW_LIMIT:,} rows "
        "per sheet). Excel export will be disabled -- use CSV for the full data."
    )

filter_signature = (fs.sql(), tuple(fs.params))
if st.button("Prepare Full Data Export", key="prepare_full_export"):
    with st.spinner(f"Fetching {total:,} rows from the database..."):
        st.session_state["_log_explorer_full_df"] = queries.fetch_all(con, fs, mapping)
        st.session_state["_log_explorer_full_sig"] = filter_signature

cached_sig = st.session_state.get("_log_explorer_full_sig")
full_df = st.session_state.get("_log_explorer_full_df") if cached_sig == filter_signature else None

if full_df is not None:
    st.success(f"Export ready: {len(full_df):,} rows.")
    ec1, ec2, ec3 = st.columns(3)
    ec1.download_button(
        "⬇️ CSV (all)",
        export_utils.to_csv_bytes(full_df),
        file_name="log_explorer_full_export.csv",
        mime="text/csv",
    )
    ec2.download_button(
        "⬇️ Excel (all)",
        export_utils.to_excel_bytes(full_df) if len(full_df) <= _EXCEL_ROW_LIMIT else b"",
        file_name="log_explorer_full_export.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        disabled=len(full_df) > _EXCEL_ROW_LIMIT,
    )
    ec3.download_button(
        "⬇️ PDF (all, rows & columns capped)",
        export_utils.to_pdf_bytes(
            "Log Explorer Export (All)", [f"Total rows: {len(full_df):,}"], full_df
        ),
        file_name="log_explorer_full_export.pdf",
        mime="application/pdf",
    )
elif cached_sig is not None and cached_sig != filter_signature:
    st.info("Filter changed since the last export was prepared. Click the button above to prepare it again.")
