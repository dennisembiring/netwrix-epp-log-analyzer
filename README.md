# Netwrix Endpoint Protector: Content Aware Protection (CAP) Log Analyzer

A local web application for importing, managing, and analyzing millions to
tens of millions of events from **Content Aware Protection (CAP)** CSV
exports from Netwrix Endpoint Protector, without Microsoft Excel's row
limits.

Built with **Streamlit** (UI) and **DuckDB** (columnar query engine) that
reads CSV files directly from disk without loading the full dataset into
Python memory, keeping it lightweight even for very large datasets.

This app is **scoped specifically to the CAP export schema**: columns are
mapped in code, so there is no manual column-mapping step at all.

## Supported CSV schema

```
Event, Event Time, Machine Name, Source IP-address, Client, Source,
Content Policy, Item Type, Matched Item, Item Details, Destination,
Destination Type, Destination Details, Email Sender, Email Subject,
Filesize(kb), File Hash, Vid, Pid, Serial Number, Os, Log, Justification
```

Columns outside this list are still stored (accessible via SQL Query or
full-text search); they're just not wired into the built-in filters/dashboard.

## Features

- **Flexible import**: upload via browser (up to 5 GB) or read directly from
  a local path/glob pattern (`/data/logs/*.csv`), with no practical size
  limit since DuckDB reads straight from disk.
- **No manual mapping**: CAP columns are mapped to semantic fields (user,
  endpoint, policy, action, time, destination, etc.) directly in code.
- **Schema validation on import**: if a CSV is missing expected CAP columns,
  the app shows a warning (non-blocking) so it's clear which filters may end
  up empty.
- **Multi-file, auto-evolving schema**: CSVs with extra columns beyond the
  standard CAP schema can still be merged without error.
- **Interactive dashboard**: event trends over time, Content Aware breakdown
  (Blocked/Allowed/Detected), top users/endpoints/policies.
- **Log Explorer**: multi-criteria filters (date, user, endpoint, policy,
  action, item type, destination/destination type, file extension) plus
  full-text search and a large-data table (streamlit-aggrid) with pagination.
- **SQL Query**: run free-form SQL (read-only) against the full dataset.
- **Reports & Export**: summary breakdowns (Event Trend, Repeat Offenders,
  Content Aware: Action, Event Type, Top Policy/Users/Endpoints/Destination,
  File Type Distribution, Top Matched Item x Destination Details, Destination
  Match, Policy x Destination x Event Type) with CSV/Excel/PDF export, plus a
  combined Full Report (PDF/Excel).
- **Dataset management**: delete datasets one at a time, or wipe everything
  to start a fresh analysis.

## Tech Stack

| Component | Purpose |
|---|---|
| Python 3.12 | Programming language |
| Streamlit | Web UI framework |
| DuckDB | Query engine for reading/joining CSVs without full memory load |
| Pandas | Data manipulation |
| Plotly | Interactive visualization |
| streamlit-aggrid | Large-scale data tables |
| OpenPyXL | Excel export |
| ReportLab | PDF export |

## Project Structure

```
.
├── app.py                   # Home page (overview & navigation)
├── pages/
│   ├── 1_Import_Data.py     # Upload/path import + CAP schema info + dataset management
│   ├── 2_Dashboard.py       # Event trends & Content Aware statistics
│   ├── 3_Log_Explorer.py    # Filters, full-text search, large-data table
│   ├── 4_SQL_Query.py       # Free-form SQL query (read-only)
│   └── 5_Reports.py         # Summary & CSV/Excel/PDF export
├── src/
│   ├── config.py             # Paths, CAP column schema, and fixed field mapping
│   ├── db.py                 # DuckDB connection, table schema, dataset management
│   ├── ingest.py              # CSV import logic and CAP schema validation
│   ├── queries.py             # Dynamic filters and aggregate queries
│   ├── ui_filters.py          # Sidebar filter widgets (shared across pages)
│   └── export_utils.py        # CSV/Excel/PDF export helpers
├── data/                     # DuckDB database & upload folder (gitignored)
├── .streamlit/config.toml    # Streamlit config (upload limit, etc.)
├── run.sh / run.command      # Portable launcher (uses runtime/python if present)
└── requirements.txt
```

## Installation & Running

### Option 1: Plain Python

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

### Option 2: Portable runtime (no Python install needed)

If a `runtime/python` folder (bundled Python + dependencies) is present, it
can be built by bundling a [python-build-standalone](https://github.com/astral-sh/python-build-standalone)
release and running `pip install -r requirements.txt` into it:

```bash
./run.sh
# or double-click run.command in Finder (macOS)
```

The `runtime/` folder is intentionally **not** committed to Git (it's
hundreds of MB); it's distributed by copying the folder directly, not via Git.

The app opens at `http://localhost:8501`.

## Usage Guide

1. **Import Data**: upload a CSV or enter a local path/folder, then click
   Import. There's no mapping step, just make sure the CSV is a CAP export
   from Netwrix Endpoint Protector.
2. **CAP Schema** (tab on the same page): see the list of supported columns
   and which fields are used for filters/dashboard.
3. **Dashboard**: monitor trends & Content Aware statistics per your filters.
4. **Log Explorer**: browse raw event rows with filters & search.
5. **SQL Query**: for ad-hoc analysis via direct SQL.
6. **Reports**: download summarized analysis results as CSV/Excel/PDF.

To start fresh with new data, go to **Import Data > "Manage Dataset" tab**
and use the per-dataset delete button or "Delete ALL datasets".

## Notes

- Browser upload limit is set to 5 GB (`.streamlit/config.toml`). For
  datasets with tens of millions of rows, **local path** import is more
  efficient since DuckDB reads straight from disk without going through
  Python memory.
- Full-text search currently uses `ILIKE` across columns (fine for general
  use); it could be upgraded to DuckDB's built-in FTS index for very large
  datasets if needed.
- CSV import tolerates quoted fields containing commas (`QUOTE`/`ESCAPE`
  parsing) and recognizes several common `Event Time` formats (e.g.
  `MM/DD/YYYY hh:mm AM/PM`, `MM/DD/YYYY HH:mm`, `DD/MM/YYYY HH:mm`,
  `DD.MM.YYYY HH:mm`) in addition to ISO and slash-separated dates.
- Don't run more than one instance of the app against the same database at
  the same time. DuckDB only supports a single active writer.
- This app is purpose-built for **Content Aware Protection** exports; other
  EPP report types (e.g. Device Control) have a different column schema and
  aren't supported by the current fixed mapping.
- Report breakdowns (e.g. Destination Type, Destination Match) only show
  categories actually present in the imported CSV for the active filter --
  see the Changelog note below for why a lower count in one period vs.
  another is expected, not a bug.

## Changelog

- **Reports: Destination Match table** -- new breakdown of Destination Type
  x Destination Details with event counts (`src/queries.py`:
  `top_destination_type_details`), added to the Summary section, Full
  Report (PDF/Excel), and per-summary export.
- **Reports: Policy x Destination x Event Type table** -- new correlated
  breakdown showing how each policy splits across destination, destination
  type, and event/content type, capped at the top 100 combinations by event
  count (`src/queries.py`: `policy_destination_breakdown`), wired into the
  same three places as above.
- **Reports: consistent table naming** -- all Reports table labels were
  mixed Indonesian/English (e.g. "Ringkasan Action" in the export dropdown
  vs. "Content Aware: Action" in the on-page summary); labels are now
  unified and consistent across the Summary section, Full Report bundle,
  and export dropdown.

  > **Note on breakdown tables (Destination Match, Policy x Destination x
  > Event Type, Top Destination, Destination Type, etc.):** these only
  > reflect what's present in the imported CAP CSV export(s) for the
  > currently active filter. If a given month's report shows fewer distinct
  > Destination Types (e.g. only 10-11) than another month, that is not a
  > data or query error -- the CAP export itself only includes the
  > destination types that actually had matching events in that reporting
  > period. This app reports the data exactly as exported, it does not
  > invent or backfill categories that weren't in the source file. For the
  > full, authoritative list of all destination types configured on your
  > Endpoint Protector deployment (including ones with zero events in a
  > given period), check the Content Aware report filter directly on the
  > EPP server.
- **Full UI translation to English** -- every user-facing string across
  `app.py`, all pages, and `src/ui_filters.py`/`src/export_utils.py`
  (titles, captions, buttons, info/warning/success/error messages, PDF
  export notes) was translated from Bahasa Indonesia to English for a
  consistent single-language UI.
