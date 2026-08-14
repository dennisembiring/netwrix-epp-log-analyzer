import glob
from pathlib import Path

import streamlit as st

from src import config, db, ingest, queries

st.set_page_config(page_title="Import Data", page_icon="📥", layout="wide")
con = db.get_connection()

st.title("📥 Import Data")
st.caption(
    "Import one or more **Content Aware Protection (CAP)** export CSV files "
    "from Netwrix Endpoint Protector. Columns are mapped automatically to the "
    "CAP schema, no manual mapping needed. For very large datasets (millions "
    "of rows), use **Local path** mode: DuckDB reads directly from disk "
    "without loading the whole file into memory."
)


def _show_results(results: list[dict]) -> None:
    if results:
        st.success(f"Successfully imported {len(results)} file(s).")
    for r in results:
        st.write(f"- `{Path(r['file']).name}`: {r['rows']:,} rows, {len(r['columns'])} columns")
        check = r["schema_check"]
        if check["missing"]:
            st.warning(
                f"  CAP columns not found in this file (related filters "
                f"will be empty): {', '.join(check['missing'])}"
            )
        if check["extra"]:
            st.caption(
                f"  Extra columns outside the standard CAP schema (still "
                f"stored, usable via SQL Query/full-text search): "
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
        f"⚠️ Headerless file(s) detected: {names}. This file's first row "
        "contains data, not column names (e.g. `Event`, `Event Time`, ...), "
        "so if imported, DuckDB will use auto-generated column names "
        "(`column0`, `column1`, ...) and EVERY semantic field (event time, "
        "user, action, etc.) will be empty/NULL across all dashboards & "
        "reports with no other error message. Add a header row matching the "
        "CAP schema (see the **CAP Schema** tab) before importing this file."
    )


tab_upload, tab_path, tab_schema, tab_manage = st.tabs(
    ["Upload File", "Local Path / Folder", "CAP Schema", "Manage Datasets"]
)

with tab_upload:
    st.subheader("Upload via browser")
    st.caption("Suitable for small-to-medium files (recommended < 500 MB per file).")
    uploaded = st.file_uploader(
        "Choose CSV file(s)", type=["csv"], accept_multiple_files=True
    )
    if uploaded and st.button("Import Uploaded File(s)", type="primary"):
        progress = st.progress(0.0, text="Saving & checking file(s)...")
        saved_paths = []
        for i, uf in enumerate(uploaded):
            dest = config.UPLOAD_DIR / uf.name
            with open(dest, "wb") as f:
                f.write(uf.getbuffer())
            saved_paths.append(str(dest))
            progress.progress((i + 1) / len(uploaded), text=f"Saving {uf.name}...")

        ok, headerless = _preflight(saved_paths)

        results = []
        for i, check in enumerate(ok):
            results.extend(ingest.import_files(con, [check["file"]]))
            progress.progress((i + 1) / len(ok) if ok else 1.0, text=f"Importing {Path(check['file']).name}...")
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
            "Import this headerless file anyway (NOT recommended -- all fields will be empty)",
            key="force_headerless_upload",
        )
        if force_headerless_upload and st.button("Force Re-import", type="secondary"):
            pending = st.session_state.pop("_headerless_upload_pending")
            results = ingest.import_files(con, pending)
            _show_results(results)
            st.rerun()

with tab_path:
    st.subheader("Import from local path")
    st.caption(
        "Enter a file path, folder, or glob pattern (e.g. `/data/epp_logs/*.csv`). "
        "Recommended for datasets with tens of millions of rows."
    )
    path_input = st.text_input(
        "Path / pattern", placeholder="/Users/name/exports/*.csv or /Users/name/exports/"
    )
    if st.button("Search Files"):
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
        st.write(f"Found {len(candidates)} file(s):")
        ok, headerless = _preflight(candidates)
        ok_paths = [c["file"] for c in ok]
        st.code("\n".join(ok_paths) if ok_paths else "(no valid files)", language="text")
        if headerless:
            _warn_headerless(headerless)

        if ok_paths and st.button("Import These Files", type="primary"):
            progress = st.progress(0.0, text="Importing...")
            results = []
            for i, path in enumerate(ok_paths):
                results.extend(ingest.import_files(con, [path]))
                progress.progress((i + 1) / len(ok_paths), text=f"Importing {Path(path).name}...")
            progress.empty()
            _show_results(results)
            st.session_state.pop("_import_candidates", None)
            st.rerun()

        if headerless:
            force_headerless_path = st.checkbox(
                "Import the headerless file(s) above anyway (NOT recommended -- all fields will be empty)",
                key="force_headerless_path",
            )
            if force_headerless_path and st.button("Force Import Headerless File(s)", type="secondary"):
                results = ingest.import_files(con, [c["file"] for c in headerless])
                _show_results(results)
                st.session_state.pop("_import_candidates", None)
                st.rerun()
    elif path_input:
        st.warning("No CSV files found at that path.")

with tab_schema:
    st.subheader("Supported CAP Schema")
    st.caption(
        "This app is dedicated to **Content Aware Protection (CAP)** exports "
        "from Netwrix Endpoint Protector. The following columns are mapped "
        "automatically -- there's no manual mapping step."
    )
    st.code("\n".join(config.CAP_RAW_COLUMNS), language="text")

    st.markdown("**Fields used for filters & dashboards:**")
    mapping_display = {
        "Event Time": "Event Time",
        "User": "Client",
        "Endpoint": "Machine Name",
        "Policy": "Content Policy",
        "Action (Blocked/Allowed/Detected)": "Event",
        "Item Type": "Item Type",
        "File path": "Source",
        "File size": "Filesize(kb)",
        "Destination Type": "Destination Type",
        "Destination": "Destination",
    }
    st.dataframe(
        {"Field": list(mapping_display.keys()), "CSV Column": list(mapping_display.values())},
        hide_index=True,
        width="stretch",
    )
    st.caption(
        "Columns outside this list are still stored in the `events` table and "
        "can be accessed via the SQL Query page or full-text search."
    )

with tab_manage:
    st.subheader("Imported Datasets")
    datasets_df = db.list_datasets(con)
    if datasets_df.empty:
        st.info("No datasets yet.")
    else:
        latest = queries.latest_event_time(con, config.FIELD_MAPPING)
        if latest is not None:
            st.metric("Latest Data (last Event Time)", str(latest))
        st.dataframe(datasets_df, width="stretch", hide_index=True)
        del_id = st.selectbox(
            "Delete dataset (by dataset_id)",
            options=[None] + datasets_df["dataset_id"].tolist(),
        )
        if del_id and st.button("Delete This Dataset", type="secondary"):
            db.delete_dataset(con, int(del_id))
            st.success(f"Dataset {del_id} deleted.")
            st.rerun()

        st.divider()
        st.subheader("Full Reset")
        st.caption(
            "Delete ALL stored datasets & events. Use this to start a fresh "
            "analysis with new data."
        )
        confirm_wipe = st.checkbox(
            "I'm sure I want to delete all datasets & events", key="confirm_wipe_all"
        )
        if st.button("Delete ALL Datasets", type="primary", disabled=not confirm_wipe):
            db.wipe_all_events(con)
            st.success("All datasets & events have been deleted.")
            st.rerun()
