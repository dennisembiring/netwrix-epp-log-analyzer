import streamlit as st

from src import config, db

st.set_page_config(page_title=config.APP_TITLE, page_icon="🛡️", layout="wide")

con = db.get_connection()
mapping = db.get_mapping(con)

st.title("🛡️ " + config.APP_TITLE)
st.caption(
    "Import, kelola, dan analisis jutaan event ekspor CSV Netwrix Endpoint "
    "Protector tanpa batasan Excel — didukung DuckDB."
)

total_events = db.total_event_count(con)
datasets_df = db.list_datasets(con)

c1, c2, c3 = st.columns(3)
c1.metric("Total event", f"{total_events:,}")
c2.metric("Dataset diimpor", len(datasets_df))
c3.metric(
    "Field mapping",
    "Sudah diatur" if mapping else "Belum diatur",
)

st.divider()

if total_events == 0:
    st.info(
        "Belum ada data. Buka halaman **1 Import Data** di sidebar untuk "
        "mengimpor file CSV hasil ekspor Endpoint Protector."
    )
elif not mapping:
    st.warning(
        "Data sudah diimpor tetapi field mapping belum diatur. Buka halaman "
        "**1 Import Data** untuk memetakan kolom (user, endpoint, action, dst) "
        "agar dashboard dan filter dapat berfungsi."
    )
else:
    st.success("Aplikasi siap digunakan. Gunakan menu di sidebar untuk mulai analisis.")

st.markdown(
    """
### Navigasi
- **1 Import Data** — impor file CSV (upload atau path lokal) & atur pemetaan kolom
- **2 Dashboard** — tren event, statistik Content Aware (Blocked/Allowed/Detected)
- **3 Log Explorer** — pencarian full-text, filter multi-kriteria, tabel data besar
- **4 SQL Query** — jalankan query SQL bebas terhadap seluruh data
- **5 Reports** — ekspor hasil analisis ke CSV, Excel, atau PDF
"""
)

if not datasets_df.empty:
    st.subheader("Dataset yang telah diimpor")
    st.dataframe(datasets_df, width="stretch", hide_index=True)
