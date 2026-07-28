import glob
from pathlib import Path

import streamlit as st

from src import config, db, ingest

st.set_page_config(page_title="Import Data", page_icon="📥", layout="wide")
con = db.get_connection()

st.title("📥 Import Data")
st.caption(
    "Import satu atau beberapa file CSV hasil ekspor **Content Aware Protection "
    "(CAP)** Netwrix Endpoint Protector. Kolom sudah dipetakan otomatis sesuai "
    "skema CAP — tidak perlu pemetaan manual. Untuk dataset sangat besar "
    "(jutaan baris), gunakan mode **Path lokal** — DuckDB membaca langsung dari "
    "disk tanpa memuat seluruh file ke memori."
)


def _show_results(results: list[dict]) -> None:
    st.success(f"Berhasil mengimpor {len(results)} file.")
    for r in results:
        st.write(f"- `{Path(r['file']).name}` — {r['rows']:,} baris, {len(r['columns'])} kolom")
        check = r["schema_check"]
        if check["missing"]:
            st.warning(
                f"  Kolom CAP yang tidak ditemukan di file ini (filter terkait "
                f"tidak akan terisi): {', '.join(check['missing'])}"
            )
        if check["extra"]:
            st.caption(
                f"  Kolom tambahan di luar skema CAP standar (tetap disimpan, "
                f"bisa dipakai lewat SQL Query/full-text search): "
                f"{', '.join(check['extra'])}"
            )


tab_upload, tab_path, tab_schema, tab_manage = st.tabs(
    ["Upload File", "Path Lokal / Folder", "Skema CAP", "Kelola Dataset"]
)

with tab_upload:
    st.subheader("Upload via browser")
    st.caption("Cocok untuk file berukuran kecil-menengah (disarankan < 500 MB per file).")
    uploaded = st.file_uploader(
        "Pilih file CSV", type=["csv"], accept_multiple_files=True
    )
    if uploaded and st.button("Import file yang diupload", type="primary"):
        progress = st.progress(0.0, text="Menyimpan & mengimpor file...")
        results = []
        for i, uf in enumerate(uploaded):
            dest = config.UPLOAD_DIR / uf.name
            with open(dest, "wb") as f:
                f.write(uf.getbuffer())
            results.extend(ingest.import_files(con, [str(dest)]))
            progress.progress((i + 1) / len(uploaded), text=f"Mengimpor {uf.name}...")
        progress.empty()
        _show_results(results)
        st.rerun()

with tab_path:
    st.subheader("Import dari path lokal")
    st.caption(
        "Masukkan path file, folder, atau glob pattern (mis. `/data/epp_logs/*.csv`). "
        "Direkomendasikan untuk dataset puluhan juta baris."
    )
    path_input = st.text_input(
        "Path / pattern", placeholder="/Users/nama/exports/*.csv atau /Users/nama/exports/"
    )
    if st.button("Cari file"):
        candidates = []
        p = Path(path_input) if path_input else None
        if path_input:
            if any(ch in path_input for ch in "*?[]"):
                candidates = sorted(glob.glob(path_input))
            elif p and p.is_dir():
                candidates = sorted(str(x) for x in p.glob("*.csv"))
            elif p and p.is_file():
                candidates = [str(p)]
        st.session_state["_import_candidates"] = candidates

    candidates = st.session_state.get("_import_candidates", [])
    if candidates:
        st.write(f"Ditemukan {len(candidates)} file:")
        st.code("\n".join(candidates), language="text")
        if st.button("Import file ini", type="primary"):
            progress = st.progress(0.0, text="Mengimpor...")
            results = []
            for i, path in enumerate(candidates):
                results.extend(ingest.import_files(con, [path]))
                progress.progress((i + 1) / len(candidates), text=f"Mengimpor {Path(path).name}...")
            progress.empty()
            _show_results(results)
            st.session_state.pop("_import_candidates", None)
            st.rerun()
    elif path_input:
        st.warning("Tidak ada file CSV ditemukan pada path tersebut.")

with tab_schema:
    st.subheader("Skema CAP yang didukung")
    st.caption(
        "Aplikasi ini khusus untuk ekspor **Content Aware Protection (CAP)** "
        "Netwrix Endpoint Protector. Kolom berikut dipetakan otomatis — tidak "
        "ada langkah pemetaan manual."
    )
    st.code("\n".join(config.CAP_RAW_COLUMNS), language="text")

    st.markdown("**Field yang dipakai untuk filter & dashboard:**")
    mapping_display = {
        "Waktu event": "Event Time",
        "User": "Client",
        "Endpoint": "Machine Name",
        "Policy": "Content Policy",
        "Action (Blocked/Allowed/Detected)": "Event",
        "Item Type": "Item Type",
        "File path": "Source",
        "Ukuran file": "Filesize(kb)",
        "Destination Type": "Destination Type",
        "Destination": "Destination",
    }
    st.dataframe(
        {"Field": list(mapping_display.keys()), "Kolom CSV": list(mapping_display.values())},
        hide_index=True,
        width="stretch",
    )
    st.caption(
        "Kolom lain di luar daftar ini tetap tersimpan di tabel `events` dan bisa "
        "diakses lewat halaman SQL Query atau pencarian full-text."
    )

with tab_manage:
    st.subheader("Dataset yang telah diimpor")
    datasets_df = db.list_datasets(con)
    if datasets_df.empty:
        st.info("Belum ada dataset.")
    else:
        st.dataframe(datasets_df, width="stretch", hide_index=True)
        del_id = st.selectbox(
            "Hapus dataset (berdasarkan dataset_id)",
            options=[None] + datasets_df["dataset_id"].tolist(),
        )
        if del_id and st.button("Hapus dataset ini", type="secondary"):
            db.delete_dataset(con, int(del_id))
            st.success(f"Dataset {del_id} dihapus.")
            st.rerun()

        st.divider()
        st.subheader("Refresh total")
        st.caption(
            "Hapus SEMUA dataset & event yang tersimpan. Gunakan ini untuk memulai "
            "analisis dari nol dengan data baru."
        )
        confirm_wipe = st.checkbox(
            "Saya yakin ingin menghapus semua dataset & event", key="confirm_wipe_all"
        )
        if st.button("Hapus SEMUA dataset", type="primary", disabled=not confirm_wipe):
            db.wipe_all_events(con)
            st.success("Semua dataset & event telah dihapus.")
            st.rerun()
