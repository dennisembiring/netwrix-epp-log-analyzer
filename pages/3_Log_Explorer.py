import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode

from src import config, db, export_utils, queries, ui_filters

st.set_page_config(page_title="Log Explorer", page_icon="🔍", layout="wide")
con = db.get_connection()
mapping = config.FIELD_MAPPING

st.title("🔍 Log Explorer")

if not db.table_exists(con, "events"):
    st.info("Belum ada data. Import data terlebih dahulu di halaman Import Data.")
    st.stop()

fs = ui_filters.render_sidebar_filters(con, mapping)

total = queries.count_events(con, fs)
st.caption(f"{total:,} event cocok dengan filter saat ini.")

if total == 0:
    st.stop()

page_size = st.sidebar.selectbox("Baris per halaman", [100, 500, 1000, 5000], index=1)
max_page = max((total - 1) // page_size, 0)
page = st.number_input("Halaman", min_value=0, max_value=max_page, value=0, step=1)

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
st.subheader("Export halaman ini")
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
    export_utils.to_pdf_bytes("Log Explorer Export", [f"Total baris (halaman ini): {len(df)}"], df),
    file_name="log_explorer_export.pdf",
    mime="application/pdf",
)
st.caption("Export hanya mencakup halaman yang sedang ditampilkan.")

st.divider()
st.subheader("Export semua hasil filter")
st.caption(
    f"Export seluruh {total:,} baris yang cocok dengan filter saat ini di sidebar "
    "(bukan cuma halaman yang sedang ditampilkan)."
)

_EXCEL_ROW_LIMIT = 1_048_576 - 1  # minus header row
if total > _EXCEL_ROW_LIMIT:
    st.warning(
        f"{total:,} baris melebihi batas maksimum Excel ({_EXCEL_ROW_LIMIT:,} baris "
        "per sheet). Export Excel akan dinonaktifkan -- gunakan CSV untuk data selengkap ini."
    )

filter_signature = (fs.sql(), tuple(fs.params))
if st.button("Siapkan export semua data", key="prepare_full_export"):
    with st.spinner(f"Mengambil {total:,} baris dari database..."):
        st.session_state["_log_explorer_full_df"] = queries.fetch_all(con, fs, mapping)
        st.session_state["_log_explorer_full_sig"] = filter_signature

cached_sig = st.session_state.get("_log_explorer_full_sig")
full_df = st.session_state.get("_log_explorer_full_df") if cached_sig == filter_signature else None

if full_df is not None:
    st.success(f"Export siap: {len(full_df):,} baris.")
    ec1, ec2, ec3 = st.columns(3)
    ec1.download_button(
        "⬇️ CSV (semua)",
        export_utils.to_csv_bytes(full_df),
        file_name="log_explorer_full_export.csv",
        mime="text/csv",
    )
    ec2.download_button(
        "⬇️ Excel (semua)",
        export_utils.to_excel_bytes(full_df) if len(full_df) <= _EXCEL_ROW_LIMIT else b"",
        file_name="log_explorer_full_export.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        disabled=len(full_df) > _EXCEL_ROW_LIMIT,
    )
    ec3.download_button(
        "⬇️ PDF (semua, dibatasi baris & kolom)",
        export_utils.to_pdf_bytes(
            "Log Explorer Export (Semua)", [f"Total baris: {len(full_df):,}"], full_df
        ),
        file_name="log_explorer_full_export.pdf",
        mime="application/pdf",
    )
elif cached_sig is not None and cached_sig != filter_signature:
    st.info("Filter berubah sejak export terakhir disiapkan. Klik tombol di atas untuk menyiapkan ulang.")
