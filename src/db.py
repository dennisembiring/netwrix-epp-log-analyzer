import duckdb
import streamlit as st

from . import config


@st.cache_resource
def get_connection():
    con = duckdb.connect(str(config.DB_PATH))
    _init_schema(con)
    return con


def _init_schema(con):
    con.execute("CREATE SEQUENCE IF NOT EXISTS dataset_id_seq START 1")
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS datasets (
            dataset_id BIGINT,
            file_name VARCHAR,
            file_path VARCHAR,
            imported_at TIMESTAMP,
            row_count BIGINT,
            column_count BIGINT,
            status VARCHAR
        )
        """
    )


def table_exists(con, name: str) -> bool:
    row = con.execute(
        "SELECT count(*) FROM information_schema.tables WHERE table_name = ?",
        [name],
    ).fetchone()
    return bool(row and row[0] > 0)


def events_columns(con) -> list[str]:
    if not table_exists(con, "events"):
        return []
    return [r[1] for r in con.execute("PRAGMA table_info('events')").fetchall()]


def list_datasets(con):
    return con.execute(
        "SELECT dataset_id, file_name, file_path, imported_at, row_count, "
        "column_count, status FROM datasets ORDER BY imported_at DESC"
    ).fetchdf()


def delete_dataset(con, dataset_id: int) -> None:
    if table_exists(con, "events"):
        con.execute("DELETE FROM events WHERE dataset_id = ?", [dataset_id])
    con.execute("DELETE FROM datasets WHERE dataset_id = ?", [dataset_id])


def wipe_all_events(con) -> None:
    if table_exists(con, "events"):
        con.execute("DROP TABLE events")
    con.execute("DELETE FROM datasets")


def total_event_count(con) -> int:
    if not table_exists(con, "events"):
        return 0
    return con.execute("SELECT count(*) FROM events").fetchone()[0]
