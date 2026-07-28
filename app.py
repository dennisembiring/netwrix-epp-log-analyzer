import streamlit as st

from src import config, db

st.set_page_config(page_title=config.APP_TITLE, page_icon="🛡️", layout="wide")

con = db.get_connection()

st.title("🛡️ " + config.APP_TITLE)
st.caption(
    "Import, kelola, dan analisis jutaan event ekspor CSV Content Aware "
    "Protection (CAP) Netwrix Endpoint Protector tanpa batasan Excel — "
    "didukung DuckDB."
)

total_events = db.total_event_count(con)
datasets_df = db.list_datasets(con)

c1, c2 = st.columns(2)
c1.metric("Total event", f"{total_events:,}")
c2.metric("Dataset diimpor", len(datasets_df))

st.divider()

if total_events == 0:
    st.info(
        "Belum ada data. Buka halaman **1 Import Data** di sidebar untuk "
        "mengimpor file CSV hasil ekspor Content Aware Protection (CAP)."
    )
else:
    st.success("Aplikasi siap digunakan. Gunakan menu di sidebar untuk mulai analisis.")

st.markdown(
    """
### Navigasi
- **1 Import Data** — impor file CSV CAP (upload atau path lokal)
- **2 Dashboard** — tren event, statistik Content Aware (Blocked/Allowed/Detected)
- **3 Log Explorer** — pencarian full-text, filter multi-kriteria, tabel data besar
- **4 SQL Query** — jalankan query SQL bebas terhadap seluruh data
- **5 Reports** — ekspor hasil analisis ke CSV, Excel, atau PDF

Kolom CSV yang didukung sudah tetap mengikuti skema ekspor CAP Netwrix
Endpoint Protector, jadi tidak perlu pemetaan kolom manual.
"""
)

if not datasets_df.empty:
    st.subheader("Dataset yang telah diimpor")
    st.dataframe(datasets_df, width="stretch", hide_index=True)
