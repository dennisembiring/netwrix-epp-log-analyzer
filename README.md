# Netwrix Endpoint Protector Log Analyzer

Aplikasi web lokal untuk mengimpor, mengelola, dan menganalisis jutaan hingga
puluhan juta event hasil ekspor CSV **Netwrix Endpoint Protector** — tanpa
batasan baris Microsoft Excel.

Dibangun dengan **Streamlit** (UI) dan **DuckDB** (query engine kolumnar) yang
membaca CSV langsung dari disk tanpa memuat seluruh data ke memori Python,
sehingga tetap ringan untuk dataset berskala besar.

## Fitur

- **Import fleksibel** — upload lewat browser (hingga 5 GB) atau baca langsung
  dari path lokal/glob pattern (`/data/logs/*.csv`), tanpa batas ukuran karena
  dibaca langsung oleh DuckDB dari disk.
- **Multi-file, skema berkembang otomatis** — file CSV dengan kolom yang
  sedikit berbeda antar ekspor tetap bisa digabung; kolom baru otomatis
  ditambahkan ke tabel gabungan.
- **Field mapping** — petakan kolom mentah CSV (yang bisa berbeda-beda nama
  antar versi/laporan EPP) ke field semantik (user, endpoint, policy, action,
  waktu, dsb) lewat UI, tanpa mengubah kode.
- **Dashboard interaktif** — tren event dari waktu ke waktu, breakdown
  Content Aware (Blocked/Allowed/Detected), top user/endpoint/policy.
- **Log Explorer** — filter multi-kriteria (tanggal, user, endpoint, policy,
  action, destination, ekstensi file) + pencarian full-text + tabel data besar
  (streamlit-aggrid) dengan paginasi.
- **SQL Query** — jalankan query SQL bebas (read-only) terhadap seluruh data.
- **Reports & Export** — ekspor hasil analisis ke CSV, Excel, atau PDF.
- **Kelola dataset** — hapus dataset satu per satu, atau reset total untuk
  mulai analisis baru dari nol.

## Tech Stack

| Komponen | Fungsi |
|---|---|
| Python 3.12 | Bahasa pemrograman |
| Streamlit | Framework antarmuka web |
| DuckDB | Query engine untuk baca/gabung CSV tanpa load penuh ke memori |
| Pandas | Manipulasi data |
| Plotly | Visualisasi interaktif |
| streamlit-aggrid | Tabel data berskala besar |
| OpenPyXL | Ekspor Excel |
| ReportLab | Ekspor PDF |

## Struktur Proyek

```
.
├── app.py                   # Halaman utama (overview & navigasi)
├── pages/
│   ├── 1_Import_Data.py     # Upload/path import + field mapping + kelola dataset
│   ├── 2_Dashboard.py       # Tren event & statistik Content Aware
│   ├── 3_Log_Explorer.py    # Filter, full-text search, tabel data besar
│   ├── 4_SQL_Query.py       # Query SQL bebas (read-only)
│   └── 5_Reports.py         # Ringkasan & ekspor CSV/Excel/PDF
├── src/
│   ├── config.py            # Path & daftar field semantik
│   ├── db.py                # Koneksi DuckDB, skema, mapping, kelola dataset
│   ├── ingest.py             # Logika import CSV (skema berkembang otomatis)
│   ├── queries.py            # Filter dinamis & query agregasi
│   ├── ui_filters.py         # Widget filter sidebar (dipakai lintas halaman)
│   └── export_utils.py       # Helper ekspor CSV/Excel/PDF
├── data/                     # Database DuckDB & folder upload (di-gitignore)
├── .streamlit/config.toml    # Konfigurasi Streamlit (batas upload, dll)
├── run.sh / run.command      # Launcher portable (pakai runtime/python bila ada)
└── requirements.txt
```

## Instalasi & Menjalankan

### Opsi 1 — Python biasa

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

### Opsi 2 — Runtime portable (tanpa install Python)

Jika folder `runtime/python` (bundle Python + dependency) tersedia — bisa
dibuat dengan mem-bundle build [python-build-standalone](https://github.com/astral-sh/python-build-standalone)
lalu `pip install -r requirements.txt` ke dalamnya:

```bash
./run.sh
# atau double-click run.command di Finder (macOS)
```

Folder `runtime/` sengaja **tidak** ikut masuk ke repo Git (ukurannya
ratusan MB) — didistribusikan lewat salinan folder langsung, bukan lewat Git.

Aplikasi terbuka di `http://localhost:8501`.

## Panduan Pemakaian

1. **Import Data** — upload CSV atau isi path/folder lokal, lalu klik Import.
2. **Field Mapping** (di halaman yang sama) — petakan kolom mentah CSV ke
   field semantik (`event_time`, `user`, `endpoint`, `policy`, `action`, dst).
   Field wajib: `event_time`, `user`, `endpoint`, `action`. Mapping ini
   tersimpan dan berlaku untuk semua dataset yang diimpor berikutnya.
3. **Dashboard** — pantau tren & statistik Content Aware sesuai filter.
4. **Log Explorer** — telusuri baris event mentah dengan filter & pencarian.
5. **SQL Query** — untuk analisis ad-hoc lewat query SQL langsung.
6. **Reports** — unduh ringkasan hasil analisis dalam format CSV/Excel/PDF.

Untuk memulai analisis dari data baru, buka **Import Data → tab Kelola
Dataset** dan gunakan tombol hapus per-dataset atau "Hapus SEMUA dataset".

## Catatan

- Batas upload lewat browser diset 5 GB (`.streamlit/config.toml`). Untuk
  dataset puluhan juta baris, mode **path lokal** lebih efisien karena DuckDB
  membaca langsung dari disk tanpa lewat memori Python.
- Pencarian full-text saat ini memakai `ILIKE` lintas kolom (cukup untuk
  kebutuhan umum); untuk dataset sangat besar bisa ditingkatkan ke FTS index
  bawaan DuckDB bila diperlukan.
- Jangan menjalankan lebih dari satu instance aplikasi secara bersamaan
  terhadap database yang sama — DuckDB hanya mendukung satu writer aktif.
