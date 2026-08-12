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
    "skema CAP, tidak perlu pemetaan manual. Untuk dataset sangat besar "
    "(jutaan baris), gunakan mode **Path lokal**: DuckDB membaca langsung dari "
    "disk tanpa memuat seluruh file ke memori."
)


def _show_results(results: list[dict]) -> None:
    if results:
        st.success(f"Berhasil mengimpor {len(results)} file.")
    for r in results:
        st.write(f"- `{Path(r['file']).name}`: {r['rows']:,} baris, {len(r['columns'])} kolom")
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


def _preflight(paths: list[str]) -> tuple[list[dict], list[dict]]:
    """Check each candidate file's header before importing. Returns
    (ok, headerless) so callers can import the good ones and block/warn on
    the rest instead of silently importing a file with no real columns."""
    ok, headerless = [], []
    for path in paths:
        check = ingest.preflight_check(con, path)
        (headerless if check["headerless"] else ok).append(check)
    return ok, headerless


def _warn_headerless(headerless: list[dict]) -> None:
    names = ", ".join(f"`{Path(c['file']).name}`" for c in headerless)
    st.error(
        f"⚠️ File tanpa header terdeteksi: {names}. Baris pertama file ini "
        "berisi data, bukan nama kolom (mis. `Event`, `Event Time`, ...), "
        "sehingga jika diimpor, DuckDB akan memakai nama kolom otomatis "
        "(`column0`, `column1`, ...) dan SEMUA field semantik (waktu event, "
        "user, action, dll) akan kosong/NULL di seluruh dashboard & report "
        "tanpa pesan error lain. Tambahkan baris header yang sesuai skema "
        "CAP (lihat tab **Skema CAP**) sebelum mengimpor file ini."
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
        progress = st.progress(0.0, text="Menyimpan & memeriksa file...")
        saved_paths = []
        for i, uf in enumerate(uploaded):
            dest = config.UPLOAD_DIR / uf.name
            with open(dest, "wb") as f:
                f.write(uf.getbuffer())
            saved_paths.append(str(dest))
            progress.progress((i + 1) / len(uploaded), text=f"Menyimpan {uf.name}...")

        ok, headerless = _preflight(saved_paths)

        results = []
        for i, check in enumerate(ok):
            results.extend(ingest.import_files(con, [check["file"]]))
            progress.progress((i + 1) / len(ok) if ok else 1.0, text=f"Mengimpor {Path(check['file']).name}...")
        progress.empty()

        if results:
            _show_results(results)
        if headerless:
            _warn_headerless(headerless)
            st.session_state["_headerless_upload_pending"] = [c["file"] for c in headerless]
        if results and not headerless:
            st.rerun()

    if st.session_state.get("_headerless_upload_pending"):
        st.divider()
        force_headerless_upload = st.checkbox(
            "Tetap import file tanpa header ini (TIDAK disarankan -- semua field akan kosong)",
            key="force_headerless_upload",
        )
        if force_headerless_upload and st.button("Import ulang dengan paksa", type="secondary"):
            pending = st.session_state.pop("_headerless_upload_pending")
            results = ingest.import_files(con, pending)
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
        ok, headerless = _preflight(candidates)
        ok_paths = [c["file"] for c in ok]
        st.code("\n".join(ok_paths) if ok_paths else "(tidak ada file valid)", language="text")
        if headerless:
            _warn_headerless(headerless)

        if ok_paths and st.button("Import file ini", type="primary"):
            progress = st.progress(0.0, text="Mengimpor...")
            results = []
            for i, path in enumerate(ok_paths):
                results.extend(ingest.import_files(con, [path]))
                progress.progress((i + 1) / len(ok_paths), text=f"Mengimpor {Path(path).name}...")
            progress.empty()
            _show_results(results)
            st.session_state.pop("_import_candidates", None)
            st.rerun()

        if headerless:
            force_headerless_path = st.checkbox(
                "Tetap import file tanpa header di atas (TIDAK disarankan -- semua field akan kosong)",
                key="force_headerless_path",
            )
            if force_headerless_path and st.button("Import file tanpa header dengan paksa", type="secondary"):
                results = ingest.import_files(con, [c["file"] for c in headerless])
                _show_results(results)
                st.session_state.pop("_import_candidates", None)
                st.rerun()
    elif path_input:
        st.warning("Tidak ada file CSV ditemukan pada path tersebut.")

with tab_schema:
    st.subheader("Skema CAP yang didukung")
    st.caption(
        "Aplikasi ini khusus untuk ekspor **Content Aware Protection (CAP)** "
        "Netwrix Endpoint Protector. Kolom berikut dipetakan otomatis, tidak "
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
