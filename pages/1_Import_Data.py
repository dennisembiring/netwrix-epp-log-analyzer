import glob
from pathlib import Path

import streamlit as st

from src import config, db, ingest

st.set_page_config(page_title="Import Data", page_icon="📥", layout="wide")
con = db.get_connection()

st.title("📥 Import Data")
st.caption(
    "Import satu atau beberapa file CSV hasil ekspor Netwrix Endpoint Protector. "
    "Untuk dataset sangat besar (jutaan baris), gunakan mode **Path lokal** — "
    "DuckDB membaca langsung dari disk tanpa memuat seluruh file ke memori."
)

tab_upload, tab_path, tab_mapping, tab_manage = st.tabs(
    ["Upload File", "Path Lokal / Folder", "Field Mapping", "Kelola Dataset"]
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
        st.success(f"Berhasil mengimpor {len(results)} file.")
        for r in results:
            st.write(f"- `{Path(r['file']).name}` — {r['rows']:,} baris, {len(r['columns'])} kolom")
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
            st.success(f"Berhasil mengimpor {len(results)} file.")
            for r in results:
                st.write(f"- `{Path(r['file']).name}` — {r['rows']:,} baris, {len(r['columns'])} kolom")
            st.session_state.pop("_import_candidates", None)
            st.rerun()
    elif path_input:
        st.warning("Tidak ada file CSV ditemukan pada path tersebut.")

with tab_mapping:
    st.subheader("Field Mapping")
    st.caption(
        "Petakan kolom mentah dari CSV ke field semantik yang dipakai dashboard & "
        "filter. Mapping ini berlaku untuk semua dataset yang sudah/akan diimpor."
    )
    columns = db.events_columns(con)
    columns = [c for c in columns if c not in ("dataset_id", "source_file", "ingested_at")]

    if not columns:
        st.info("Import setidaknya satu file CSV terlebih dahulu untuk mengatur mapping.")
    else:
        current = db.get_mapping(con)
        new_mapping = {}
        options = ["(tidak ada)"] + columns
        cols_ui = st.columns(2)
        for i, (field, desc) in enumerate(config.SEMANTIC_FIELDS.items()):
            target_col = cols_ui[i % 2]
            default = current.get(field)
            idx = options.index(default) if default in options else 0
            choice = target_col.selectbox(
                f"{field} — {desc}",
                options,
                index=idx,
                key=f"map_{field}",
            )
            if choice != "(tidak ada)":
                new_mapping[field] = choice

        missing_required = config.REQUIRED_SEMANTIC_FIELDS - set(new_mapping)
        if missing_required:
            st.warning(
                "Field wajib belum dipetakan: " + ", ".join(sorted(missing_required))
            )

        if st.button("Simpan Mapping", type="primary"):
            db.set_mapping(con, new_mapping)
            st.success("Mapping tersimpan.")
            st.rerun()

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
            "analisis dari nol dengan data baru. Field mapping tidak ikut terhapus."
        )
        confirm_wipe = st.checkbox(
            "Saya yakin ingin menghapus semua dataset & event", key="confirm_wipe_all"
        )
        if st.button("Hapus SEMUA dataset", type="primary", disabled=not confirm_wipe):
            db.wipe_all_events(con)
            st.success("Semua dataset & event telah dihapus.")
            st.rerun()
