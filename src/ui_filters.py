"""Shared sidebar filter widget used by Dashboard and Log Explorer pages."""

import streamlit as st

from . import queries


def render_sidebar_filters(con, mapping: dict) -> queries.FilterSet:
    st.sidebar.header("Filter")

    fs = queries.FilterSet(mapping)

    if mapping.get("event_time"):
        c1, c2 = st.sidebar.columns(2)
        start = c1.date_input("From date", value=None, key="filter_start")
        end = c2.date_input("To date", value=None, key="filter_end")
        fs.date_range(start if start else None, end if end else None)
    else:
        st.sidebar.caption("Map the 'event_time' field to enable date filtering.")

    def multiselect_for(field: str, label: str):
        raw = mapping.get(field)
        if not raw:
            return
        values = queries.get_distinct(con, raw)
        chosen = st.sidebar.multiselect(label, values, key=f"filter_{field}")
        fs.in_list(field, chosen)

    multiselect_for("user", "User")
    multiselect_for("endpoint", "Endpoint")
    multiselect_for("policy", "Policy")
    multiselect_for("action", "Action")
    multiselect_for("event_type", "Event Type")
    multiselect_for("destination_type", "Destination Type")
    multiselect_for("destination", "Destination")

    if mapping.get("file_extension") or mapping.get("file_name") or mapping.get("file_path"):
        ext_expr = queries.file_ext_expr(mapping)
        values = queries.get_distinct_expr(con, ext_expr)
        chosen = st.sidebar.multiselect("File Extension", values, key="filter_ext")
        fs.file_extension_in(chosen)

    search = st.sidebar.text_input("Full-text search", key="filter_search")
    if search:
        # Search across every text column present, not just mapped ones.
        from . import db as _db

        all_cols = [
            c for c in _db.events_columns(con)
            if c not in ("dataset_id", "source_file", "ingested_at")
        ]
        fs.full_text(search, all_cols)

    return fs
