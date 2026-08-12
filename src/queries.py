"""Dynamic filter/query building against the shared ``events`` table.

Raw columns are stored as VARCHAR (see ingest.py), so date parsing and any
typed comparisons happen at query time via SQL expressions built here. This
keeps ingestion fast/robust while still allowing date-range filters, trend
charts, etc.
"""

import datetime

from . import db

DATE_FORMATS = [
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S",
    "%Y/%m/%d %H:%M:%S",
    "%m/%d/%Y %I:%M:%S %p",
    "%m/%d/%Y %H:%M:%S",
    "%d/%m/%Y %H:%M:%S",
    "%d.%m.%Y %H:%M:%S",
    "%m/%d/%Y %I:%M %p",
    "%m/%d/%Y %H:%M",
    "%d/%m/%Y %H:%M",
    "%d.%m.%Y %H:%M",
    "%Y-%m-%d",
    "%m/%d/%Y",
    "%d/%m/%Y",
]


def col(name: str) -> str:
    return f'"{name}"'


def event_time_expr(mapping: dict) -> str:
    raw = mapping.get("event_time")
    if not raw:
        return "NULL"
    casts = ", ".join(f"TRY_STRPTIME({col(raw)}, '{f}')" for f in DATE_FORMATS)
    return f"COALESCE(TRY_CAST({col(raw)} AS TIMESTAMP), {casts})"


# Restricted to real file extensions so this doesn't pick up domain suffixes
# (docs.google.com -> "com") when file_path/file_name is actually a URL, which
# is common for CAP's Source/Matched Item fields on browser-based events.
_FILE_EXTENSIONS = (
    "pdf|docx?|xlsx?|pptx?|csv|txt|rtf|odt|ods|odp|"
    "zip|rar|7z|tar|gz|iso|dmg|"
    "png|jpe?g|gif|bmp|svg|tiff?|webp|heic|"
    "mp3|mp4|wav|avi|mov|mkv|"
    "exe|msi|dll|apk|bat|sh|"
    "json|xml|ya?ml|sql|log|bak|"
    "eml|msg|pst|"
    "py|js|ts|java|cs|cpp|php"
)


def file_ext_expr(mapping: dict) -> str:
    if mapping.get("file_extension"):
        return col(mapping["file_extension"])
    fname = mapping.get("file_name") or mapping.get("file_path")
    if fname:
        # regexp_extract returns '' (not NULL) on no-match, which would slip
        # past every "IS NOT NULL" filter downstream -- NULLIF closes that gap.
        return (
            f"NULLIF(regexp_extract({col(fname)}, "
            f"'\\.({_FILE_EXTENSIONS})$', 1, 'i'), '')"
        )
    return "NULL"


def mapped_expr(mapping: dict, field: str) -> str | None:
    raw = mapping.get(field)
    if not raw:
        return None
    return col(raw)


def get_distinct(con, column: str | None, search: str | None = None, limit: int = 500):
    if not column or not db.table_exists(con, "events"):
        return []
    where = f'"{column}" IS NOT NULL'
    params = []
    if search:
        where += f' AND "{column}" ILIKE ?'
        params.append(f"%{search}%")
    q = f'SELECT DISTINCT "{column}" AS v FROM events WHERE {where} ORDER BY 1 LIMIT {limit}'
    return [r[0] for r in con.execute(q, params).fetchall()]


def get_distinct_expr(con, expr: str, limit: int = 500):
    if not db.table_exists(con, "events"):
        return []
    q = f"SELECT DISTINCT {expr} AS v FROM events WHERE {expr} IS NOT NULL ORDER BY 1 LIMIT {limit}"
    return [r[0] for r in con.execute(q).fetchall()]


class FilterSet:
    """Builds a WHERE clause + params from UI filter selections."""

    def __init__(self, mapping: dict):
        self.mapping = mapping
        self.clauses: list[str] = []
        self.params: list = []

    def date_range(self, start, end):
        if start:
            self.clauses.append(f"{event_time_expr(self.mapping)} >= ?")
            self.params.append(start)
        if end:
            # A bare date (e.g. from st.date_input) compares as midnight, which
            # would exclude the entire end day. Bump to the start of the next
            # day and use a strict "<" so the whole end day is included.
            if isinstance(end, datetime.date) and not isinstance(end, datetime.datetime):
                end = end + datetime.timedelta(days=1)
                self.clauses.append(f"{event_time_expr(self.mapping)} < ?")
            else:
                self.clauses.append(f"{event_time_expr(self.mapping)} <= ?")
            self.params.append(end)
        return self

    def in_list(self, field: str, values: list):
        if not values:
            return self
        raw = self.mapping.get(field)
        if not raw:
            return self
        placeholders = ", ".join(["?"] * len(values))
        self.clauses.append(f'"{raw}" IN ({placeholders})')
        self.params.extend(values)
        return self

    def file_extension_in(self, values: list):
        if not values:
            return self
        placeholders = ", ".join(["?"] * len(values))
        self.clauses.append(f"{file_ext_expr(self.mapping)} IN ({placeholders})")
        self.params.extend(values)
        return self

    def full_text(self, term: str, searchable_columns: list[str]):
        if not term or not searchable_columns:
            return self
        sub = " OR ".join(f'"{c}" ILIKE ?' for c in searchable_columns)
        self.clauses.append(f"({sub})")
        self.params.extend([f"%{term}%"] * len(searchable_columns))
        return self

    def dataset_in(self, dataset_ids: list[int]):
        if not dataset_ids:
            return self
        placeholders = ", ".join(["?"] * len(dataset_ids))
        self.clauses.append(f"dataset_id IN ({placeholders})")
        self.params.extend(dataset_ids)
        return self

    def sql(self) -> str:
        if not self.clauses:
            return "1=1"
        return " AND ".join(self.clauses)


def count_events(con, fs: FilterSet) -> int:
    if not db.table_exists(con, "events"):
        return 0
    q = f"SELECT count(*) FROM events WHERE {fs.sql()}"
    return con.execute(q, fs.params).fetchone()[0]


def fetch_page(con, fs: FilterSet, mapping: dict, order_desc: bool = True, limit: int = 500, offset: int = 0):
    if not db.table_exists(con, "events"):
        return con.sql("SELECT 1 WHERE FALSE").fetchdf()
    time_expr = event_time_expr(mapping)
    order = f"ORDER BY {time_expr} {'DESC' if order_desc else 'ASC'}" if mapping.get("event_time") else ""
    q = f"""
        SELECT * FROM events
        WHERE {fs.sql()}
        {order}
        LIMIT {limit} OFFSET {offset}
    """
    return con.execute(q, fs.params).fetchdf()


def events_over_time(con, fs: FilterSet, mapping: dict, granularity: str = "day"):
    time_expr = event_time_expr(mapping)
    q = f"""
        SELECT date_trunc('{granularity}', {time_expr}) AS bucket, count(*) AS events
        FROM events
        WHERE {fs.sql()} AND {time_expr} IS NOT NULL
        GROUP BY 1
        ORDER BY 1
    """
    return con.execute(q, fs.params).fetchdf()


def file_extension_breakdown(con, fs: FilterSet, mapping: dict, limit: int = 15):
    expr = file_ext_expr(mapping)
    if expr == "NULL":
        return con.sql("SELECT 1 WHERE FALSE").fetchdf()
    q = f"""
        SELECT {expr} AS file_extension, count(*) AS events
        FROM events
        WHERE {fs.sql()} AND {expr} IS NOT NULL
        GROUP BY 1
        ORDER BY 2 DESC
        LIMIT {limit}
    """
    return con.execute(q, fs.params).fetchdf()


def latest_event_time(con, mapping: dict):
    """Newest Event Time across ALL imported data (ignores active filters) so
    it reads as "how fresh is the data", not "what's in the current view"."""
    if not mapping.get("event_time") or not db.table_exists(con, "events"):
        return None
    time_expr = event_time_expr(mapping)
    row = con.execute(f"SELECT max({time_expr}) FROM events").fetchone()
    return row[0] if row else None


def top_values(con, fs: FilterSet, mapping: dict, field: str, limit: int = 15):
    raw = mapping.get(field)
    if not raw:
        return con.sql("SELECT 1 WHERE FALSE").fetchdf()
    q = f"""
        SELECT "{raw}" AS value, count(*) AS events
        FROM events
        WHERE {fs.sql()} AND "{raw}" IS NOT NULL
        GROUP BY 1
        ORDER BY 2 DESC
        LIMIT {limit}
    """
    return con.execute(q, fs.params).fetchdf()


def top_matched_item_destination(con, fs: FilterSet, mapping: dict, limit: int | None = None):
    raw_item = mapping.get("matched_item")
    raw_dest = mapping.get("destination_details")
    if not raw_item or not raw_dest:
        return con.sql("SELECT 1 WHERE FALSE").fetchdf()
    limit_clause = f"LIMIT {limit}" if limit else ""
    q = f"""
        SELECT "{raw_item}" AS matched_item, "{raw_dest}" AS destination_details, count(*) AS events
        FROM events
        WHERE {fs.sql()} AND "{raw_item}" IS NOT NULL AND "{raw_dest}" IS NOT NULL
        GROUP BY 1, 2
        ORDER BY 3 DESC
        {limit_clause}
    """
    return con.execute(q, fs.params).fetchdf()


def action_breakdown(con, fs: FilterSet, mapping: dict):
    raw = mapping.get("action")
    if not raw:
        return con.sql("SELECT 1 WHERE FALSE").fetchdf()
    q = f"""
        SELECT "{raw}" AS action, count(*) AS events
        FROM events
        WHERE {fs.sql()}
        GROUP BY 1
        ORDER BY 2 DESC
    """
    return con.execute(q, fs.params).fetchdf()


def event_type_breakdown(con, fs: FilterSet, mapping: dict):
    raw = mapping.get("event_type")
    if not raw:
        return con.sql("SELECT 1 WHERE FALSE").fetchdf()
    q = f"""
        SELECT "{raw}" AS event_type, count(*) AS events
        FROM events
        WHERE {fs.sql()}
        GROUP BY 1
        ORDER BY 2 DESC
    """
    return con.execute(q, fs.params).fetchdf()
