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
st.caption(
    "Export hanya mencakup halaman yang sedang ditampilkan. Untuk export seluruh "
    "hasil filter (bisa jutaan baris), gunakan halaman **SQL Query** atau **Reports**."
)
