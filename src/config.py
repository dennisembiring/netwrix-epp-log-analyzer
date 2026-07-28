from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "eplog.duckdb"
UPLOAD_DIR = DATA_DIR / "uploads"

DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

APP_TITLE = "Netwrix Endpoint Protector - Content Aware Protection Log Analyzer"

# Raw CSV headers for Netwrix Endpoint Protector Content Aware Protection
# (CAP) report exports. This app is scoped to CAP exports only, so the
# mapping below is fixed and never edited via UI.
CAP_RAW_COLUMNS = [
    "Event",
    "Event Time",
    "Machine Name",
    "Source IP-address",
    "Client",
    "Source",
    "Content Policy",
    "Item Type",
    "Matched Item",
    "Item Details",
    "Destination",
    "Destination Type",
    "Destination Details",
    "Email Sender",
    "Email Subject",
    "Filesize(kb)",
    "File Hash",
    "Vid",
    "Pid",
    "Serial Number",
    "Os",
    "Log",
    "Justification",
]

# Semantic field -> normalized column name (see ingest.normalize_col). Fixed
# because CAP exports always use the same schema, so no manual mapping step
# is needed.
FIELD_MAPPING = {
    "event_time": "event_time",
    "user": "client",
    "endpoint": "machine_name",
    "policy": "content_policy",
    "action": "event",
    "event_type": "item_type",
    "file_path": "source",
    "file_size": "filesize_kb",
    "destination_type": "destination_type",
    "destination": "destination",
}
