import streamlit as st

from src import config, db, export_utils, queries, ui_filters

st.set_page_config(page_title="Reports", page_icon="📄", layout="wide")
con = db.get_connection()
mapping = config.FIELD_MAPPING

st.title("📄 Reports")
st.caption(
    "Hasilkan ringkasan laporan berdasarkan filter yang dipilih dan ekspor ke "
    "CSV, Excel, atau PDF."
)

if not db.table_exists(con, "events"):
    st.info("Belum ada data. Import data terlebih dahulu di halaman Import Data.")
    st.stop()

fs = ui_filters.render_sidebar_filters(con, mapping)
total = queries.count_events(con, fs)
st.metric("Total event sesuai filter", f"{total:,}")

if total == 0:
    st.stop()

action_df = queries.action_breakdown(con, fs, mapping) if mapping.get("action") else None
event_type_df = queries.event_type_breakdown(con, fs, mapping) if mapping.get("event_type") else None
top_users_df = queries.top_values(con, fs, mapping, "user", limit=20) if mapping.get("user") else None
top_endpoints_df = queries.top_values(con, fs, mapping, "endpoint", limit=20) if mapping.get("endpoint") else None
top_policy_df = queries.top_values(con, fs, mapping, "policy", limit=20) if mapping.get("policy") else None

st.subheader("Ringkasan")
cols = st.columns(3)
if action_df is not None and not action_df.empty:
    with cols[0]:
        st.write("**Content Aware: Action**")
        st.dataframe(action_df, hide_index=True, width="stretch")
if event_type_df is not None and not event_type_df.empty:
    with cols[1]:
        st.write("**Event Type**")
        st.dataframe(event_type_df, hide_index=True, width="stretch")
if top_policy_df is not None and not top_policy_df.empty:
    with cols[2]:
        st.write("**Top Policy**")
        st.dataframe(top_policy_df, hide_index=True, width="stretch")

cols2 = st.columns(2)
if top_users_df is not None and not top_users_df.empty:
    with cols2[0]:
        st.write("**Top Users**")
        st.dataframe(top_users_df, hide_index=True, width="stretch")
if top_endpoints_df is not None and not top_endpoints_df.empty:
    with cols2[1]:
        st.write("**Top Endpoints**")
        st.dataframe(top_endpoints_df, hide_index=True, width="stretch")

st.divider()
st.subheader("Ekspor Laporan")

report_choice = st.selectbox(
    "Pilih data untuk diekspor",
    ["Ringkasan Action", "Ringkasan Event Type", "Top Users", "Top Endpoints", "Top Policy"],
)
export_map = {
    "Ringkasan Action": action_df,
    "Ringkasan Event Type": event_type_df,
    "Top Users": top_users_df,
    "Top Endpoints": top_endpoints_df,
    "Top Policy": top_policy_df,
}
export_df = export_map.get(report_choice)

if export_df is None or export_df.empty:
    st.info("Tidak ada data untuk pilihan ini (kemungkinan field belum dipetakan).")
else:
    c1, c2, c3 = st.columns(3)
    fname = report_choice.lower().replace(" ", "_")
    c1.download_button(
        "⬇️ CSV", export_utils.to_csv_bytes(export_df), file_name=f"{fname}.csv", mime="text/csv"
    )
    c2.download_button(
        "⬇️ Excel",
        export_utils.to_excel_bytes(export_df),
        file_name=f"{fname}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    c3.download_button(
        "⬇️ PDF",
        export_utils.to_pdf_bytes(
            report_choice,
            [f"Total event (semua filter): {total:,}"],
            export_df,
        ),
        file_name=f"{fname}.pdf",
        mime="application/pdf",
    )
