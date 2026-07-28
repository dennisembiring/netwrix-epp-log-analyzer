from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "eplog.duckdb"
UPLOAD_DIR = DATA_DIR / "uploads"

DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

APP_TITLE = "Netwrix Endpoint Protector Log Analyzer"

# Semantic fields the app needs for filtering/dashboards. The user maps these
# to whatever raw column names their specific EPP CSV export uses, since
# column names vary across EPP versions/languages/report types.
SEMANTIC_FIELDS = {
    "event_time": "Waktu event (tanggal & jam)",
    "user": "User / akun",
    "endpoint": "Nama komputer / endpoint",
    "domain": "Domain",
    "policy": "Nama policy",
    "action": "Action / status (Blocked, Allowed, Detected, dll)",
    "event_type": "Jenis event (Content Aware, Device Control, dll)",
    "file_name": "Nama file",
    "file_path": "Path file",
    "file_extension": "Ekstensi file",
    "file_size": "Ukuran file",
    "application": "Aplikasi / proses",
    "destination_type": "Tipe tujuan (USB, Cloud, Email, dll)",
    "destination": "Detail tujuan (drive/URL/path spesifik)",
}

REQUIRED_SEMANTIC_FIELDS = {"event_time", "user", "endpoint", "action"}
