import plotly.express as px
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
top_destination_df = queries.top_values(con, fs, mapping, "destination", limit=20) if mapping.get("destination") else None
top_matched_dest_df = (
    queries.top_matched_item_destination(con, fs, mapping)
    if mapping.get("matched_item") and mapping.get("destination_details")
    else None
)
file_type_df = (
    queries.file_extension_breakdown(con, fs, mapping, limit=20)
    if mapping.get("file_path") or mapping.get("file_name") or mapping.get("file_extension")
    else None
)

st.divider()
st.subheader("Tren Event")
trend_df = None
if mapping.get("event_time"):
    granularity = st.selectbox(
        "Granularitas", ["day", "week", "month"], index=0, key="report_trend_granularity"
    )
    trend_df = queries.events_over_time(con, fs, mapping, granularity)
    if not trend_df.empty:
        fig = px.line(trend_df, x="bucket", y="events", markers=True)
        fig.update_layout(margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, width="stretch")
    else:
        st.info("Tidak ada data waktu untuk ditampilkan.")
else:
    st.info("Petakan field 'event_time' untuk melihat tren.")

st.divider()
st.subheader("Repeat Offenders")
st.caption(
    "User dengan jumlah event di atas ambang batas yang ditentukan -- lebih "
    "actionable daripada daftar Top Users biasa untuk menandai user yang "
    "perlu ditindaklanjuti."
)
repeat_offenders_df = None
if mapping.get("user"):
    threshold = st.number_input(
        "Ambang batas jumlah event", min_value=1, value=100, step=10, key="repeat_offender_threshold"
    )
    all_users_df = queries.top_values(con, fs, mapping, "user", limit=100000)
    repeat_offenders_df = all_users_df[all_users_df["events"] >= threshold].reset_index(drop=True)
    if repeat_offenders_df.empty:
        st.info(f"Tidak ada user dengan >= {threshold:,} event pada filter saat ini.")
    else:
        st.write(f"**{len(repeat_offenders_df)} user** dengan >= {threshold:,} event:")
        st.dataframe(repeat_offenders_df, hide_index=True, width="stretch")
else:
    st.info("Petakan field 'user' untuk melihat repeat offenders.")

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

cols2 = st.columns(3)
if top_users_df is not None and not top_users_df.empty:
    with cols2[0]:
        st.write("**Top Users**")
        st.dataframe(top_users_df, hide_index=True, width="stretch")
if top_endpoints_df is not None and not top_endpoints_df.empty:
    with cols2[1]:
        st.write("**Top Endpoints**")
        st.dataframe(top_endpoints_df, hide_index=True, width="stretch")
if top_destination_df is not None and not top_destination_df.empty:
    with cols2[2]:
        st.write("**Top Destination**")
        st.dataframe(top_destination_df, hide_index=True, width="stretch")

if file_type_df is not None and not file_type_df.empty:
    st.write("**Distribusi Tipe File**")
    st.dataframe(file_type_df, hide_index=True, width="stretch")

if top_matched_dest_df is not None and not top_matched_dest_df.empty:
    st.write("**Top Matched Item x Destination Details**")
    st.dataframe(top_matched_dest_df, hide_index=True, width="stretch")

st.divider()
st.subheader("Full Report")
st.caption(
    "Seluruh ringkasan di atas (tren event, repeat offenders, action, event "
    "type, top policy, top users, top endpoints, top destination, distribusi "
    "tipe file, top matched item x destination details) dalam satu file, "
    "sesuai filter yang sedang aktif di sidebar. PDF menggabungkan semua "
    "tabel jadi satu dokumen; Excel memisahkan tiap ringkasan ke sheet-nya "
    "sendiri."
)
full_report_sections = [
    ("Tren Event", trend_df),
    ("Repeat Offenders", repeat_offenders_df),
    ("Content Aware: Action", action_df),
    ("Event Type", event_type_df),
    ("Top Policy", top_policy_df),
    ("Top Users", top_users_df),
    ("Top Endpoints", top_endpoints_df),
    ("Top Destination", top_destination_df),
    ("Distribusi Tipe File", file_type_df),
    ("Top Matched Item x Destination Details", top_matched_dest_df),
]
if any(df is not None and not df.empty for _, df in full_report_sections):
    fr1, fr2 = st.columns(2)
    fr1.download_button(
        "⬇️ Download Full Report (PDF)",
        export_utils.to_full_report_pdf_bytes(
            "Full Report - Netwrix EPP CAP",
            [f"Total event (sesuai filter): {total:,}"],
            full_report_sections,
        ),
        file_name="full_report.pdf",
        mime="application/pdf",
        type="primary",
    )
    fr2.download_button(
        "⬇️ Download Full Report (Excel)",
        export_utils.to_full_report_excel_bytes(full_report_sections),
        file_name="full_report.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
else:
    st.info("Tidak ada data ringkasan untuk digabung jadi Full Report.")

st.divider()
st.subheader("Ekspor Per Ringkasan")

report_choice = st.selectbox(
    "Pilih data untuk diekspor",
    [
        "Tren Event",
        "Repeat Offenders",
        "Ringkasan Action",
        "Ringkasan Event Type",
        "Top Users",
        "Top Endpoints",
        "Top Policy",
        "Top Destination",
        "Distribusi Tipe File",
        "Top Matched Item x Destination Details",
    ],
)
export_map = {
    "Tren Event": trend_df,
    "Repeat Offenders": repeat_offenders_df,
    "Ringkasan Action": action_df,
    "Ringkasan Event Type": event_type_df,
    "Top Users": top_users_df,
    "Top Endpoints": top_endpoints_df,
    "Top Policy": top_policy_df,
    "Distribusi Tipe File": file_type_df,
    "Top Matched Item x Destination Details": top_matched_dest_df,
    "Top Destination": top_destination_df,
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
