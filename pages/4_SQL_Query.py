import re

import streamlit as st

from src import db, export_utils

st.set_page_config(page_title="SQL Query", page_icon="🧮", layout="wide")
con = db.get_connection()

st.title("🧮 SQL Query")
st.caption(
    "Jalankan query SQL bebas terhadap tabel `events` dan `datasets` (dialek DuckDB). "
    "Hanya statement `SELECT` / `WITH` / `PRAGMA` yang diizinkan untuk mencegah "
    "perubahan data yang tidak disengaja."
)

if not db.table_exists(con, "events"):
    st.info("Belum ada data. Import data terlebih dahulu di halaman Import Data.")
    st.stop()

with st.expander("Skema kolom tabel `events`"):
    cols = db.events_columns(con)
    st.code(", ".join(cols), language="text")

default_query = "SELECT * FROM events LIMIT 100"
query = st.text_area("Query SQL", value=default_query, height=180)

WRITE_KEYWORDS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|ATTACH|COPY|EXPORT|IMPORT|CALL|SET)\b",
    re.IGNORECASE,
)


def is_safe(q: str) -> bool:
    stripped = q.strip().rstrip(";")
    if not re.match(r"^(SELECT|WITH|PRAGMA|EXPLAIN|DESCRIBE|SHOW)\b", stripped, re.IGNORECASE):
        return False
    if WRITE_KEYWORDS.search(stripped):
        return False
    if ";" in stripped:
        return False
    return True


run = st.button("Jalankan Query", type="primary")

if run:
    if not is_safe(query):
        st.error(
            "Query ditolak. Hanya satu statement SELECT/WITH/PRAGMA/EXPLAIN/DESCRIBE/SHOW "
            "yang diizinkan (tanpa INSERT/UPDATE/DELETE/DROP/ALTER/CREATE, dsb)."
        )
    else:
        try:
            with st.spinner("Menjalankan query..."):
                result_df = con.execute(query).fetchdf()
            st.success(f"{len(result_df):,} baris dikembalikan.")
            st.dataframe(result_df, width="stretch", hide_index=True)
            st.session_state["_last_sql_result"] = result_df
        except Exception as e:
            st.error(f"Query error: {e}")

if "_last_sql_result" in st.session_state:
    df = st.session_state["_last_sql_result"]
    st.divider()
    st.subheader("Export hasil query")
    c1, c2, c3 = st.columns(3)
    c1.download_button(
        "⬇️ CSV", export_utils.to_csv_bytes(df), file_name="sql_query_result.csv", mime="text/csv"
    )
    c2.download_button(
        "⬇️ Excel",
        export_utils.to_excel_bytes(df),
        file_name="sql_query_result.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    c3.download_button(
        "⬇️ PDF",
        export_utils.to_pdf_bytes("SQL Query Result", [f"Total baris: {len(df)}"], df),
        file_name="sql_query_result.pdf",
        mime="application/pdf",
    )
