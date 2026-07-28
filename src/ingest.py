"""CSV import logic.

Files are read directly by DuckDB with ``read_csv_auto`` so multi-million-row
exports never get fully loaded into Python/pandas memory. All raw columns are
read as VARCHAR and normalized to snake_case; a shared ``events`` table is
grown (via ``ALTER TABLE ... ADD COLUMN``) as new CSV exports introduce new
columns, so files with slightly different headers can still be combined.
"""

import re
from pathlib import Path

from . import db


def normalize_col(name: str) -> str:
    name = name.strip().lower()
    name = re.sub(r"[^\w]+", "_", name)
    name = re.sub(r"_+", "_", name).strip("_")
    return name or "col"


def _quote_lit(path: str) -> str:
    return path.replace("'", "''")


def read_headers(con, path: str) -> list[str]:
    escaped = _quote_lit(path)
    rel = con.sql(
        f"SELECT * FROM read_csv_auto('{escaped}', ALL_VARCHAR=TRUE, "
        f"SAMPLE_SIZE=1000, IGNORE_ERRORS=TRUE) LIMIT 0"
    )
    return list(rel.columns)


def import_files(con, paths: list[str], label_prefix: str | None = None) -> list[dict]:
    results = []
    for path in paths:
        results.append(_import_single(con, path, label_prefix))
    return results


def _import_single(con, path: str, label_prefix: str | None) -> dict:
    dataset_id = con.execute("SELECT nextval('dataset_id_seq')").fetchone()[0]
    escaped = _quote_lit(path)
    raw_columns = read_headers(con, path)
    norm_map = {orig: normalize_col(orig) for orig in raw_columns}

    # Guard against duplicate normalized names colliding (e.g. "File Name"
    # and "file_name" both -> "file_name").
    seen = {}
    for orig, norm in list(norm_map.items()):
        if norm in seen:
            seen[norm] += 1
            norm_map[orig] = f"{norm}_{seen[norm]}"
        else:
            seen[norm] = 0

    select_exprs = ", ".join(
        f'"{orig}" AS "{norm}"' for orig, norm in norm_map.items()
    )
    read_csv_expr = (
        f"read_csv_auto('{escaped}', ALL_VARCHAR=TRUE, UNION_BY_NAME=TRUE, "
        f"IGNORE_ERRORS=TRUE)"
    )

    if not db.table_exists(con, "events"):
        con.execute(
            f"""
            CREATE TABLE events AS
            SELECT
                CAST({dataset_id} AS BIGINT) AS dataset_id,
                '{escaped}' AS source_file,
                now() AS ingested_at,
                {select_exprs}
            FROM {read_csv_expr}
            """
        )
    else:
        existing = set(db.events_columns(con))
        for norm in norm_map.values():
            if norm not in existing:
                con.execute(f'ALTER TABLE events ADD COLUMN "{norm}" VARCHAR')
        con.execute(
            f"""
            INSERT INTO events BY NAME
            SELECT
                CAST({dataset_id} AS BIGINT) AS dataset_id,
                '{escaped}' AS source_file,
                now() AS ingested_at,
                {select_exprs}
            FROM {read_csv_expr}
            """
        )

    row_count = con.execute(
        "SELECT count(*) FROM events WHERE dataset_id = ?", [dataset_id]
    ).fetchone()[0]

    con.execute(
        """
        INSERT INTO datasets
        (dataset_id, file_name, file_path, imported_at, row_count, column_count, status)
        VALUES (?, ?, ?, now(), ?, ?, 'imported')
        """,
        [
            dataset_id,
            (label_prefix + "/" if label_prefix else "") + Path(path).name,
            path,
            row_count,
            len(raw_columns),
        ],
    )

    return {
        "dataset_id": dataset_id,
        "file": path,
        "rows": row_count,
        "columns": list(norm_map.values()),
    }
