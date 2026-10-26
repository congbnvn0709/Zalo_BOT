# Project: Zalo Attendance Web App & Excel Integrator

## Architecture
- **Runtime**: Python 3.11 (`/opt/homebrew/bin/python3.11`) using isolated `.venv`. Self-bootstrapping launcher `run.py`.
- **Backend Framework**: FastAPI + Uvicorn ASGI server with Pydantic v2 schemas for robust validation, clean REST APIs, static file mount, and socket-free testing via `TestClient`.
- **Frontend Architecture**: Zero-build Single Page Application (SPA) using Vanilla ES6+ JS and Tailwind CSS (CDN) with an embedded offline fallback stylesheet (`static/css/app.css`). Interactive data grid with summary badges, inline editing, modal editor, and immediate download feedback.
- **Excel Engine**: `openpyxl` with `data_only=False` preserving all native formulas (`=SUM(...)`), merged headers, styles, and column widths. `fullCalcOnLoad=True` configured for automatic recalculation in Excel.
- **Data Flow**:
  1. Raw batch messages pasted into Web UI textarea -> `POST /api/parse`
  2. Parser segments messages, extracts fields, normalizes names/dates/shifts/meals, calculates hours across 6 categories + meal -> returns JSON list of structured records with validity status (`VALID`, `WARNING`, `ERROR`).
  3. Web UI displays interactive table with inline cell editing and error tooltips. User reviews and adjusts any exceptions.
  4. User clicks "Xác nhận & Điền vào Excel" -> `POST /api/export-excel` with verified records.
  5. Excel Integrator loads template (`templates_excel/BẢNG CHẤM CÔNG WEVN - ETS.xlsx`), fuzzy-matches employee rows, resolves date columns, writes numeric values to target offsets, preserves formulas, and saves output to `output/`.
  6. User downloads updated workbook directly via `/api/download/{token}` or accesses local output file.

## Code Layout
```
/Users/congcm/CODE/Vibe_Code/Zalo_BOT/
├── core/
│   ├── __init__.py
│   ├── parser.py              # R1 Message parser, tokenization, regex, hour allocation
│   ├── excel_integrator.py    # R3 openpyxl read/write engine, fuzzy matcher, coordinate resolver
│   └── template_generator.py  # Generates default .xlsx template from sample_data.csv with formulas
├── models/
│   ├── __init__.py
│   └── attendance.py          # Pydantic models for parsed records, shifts, API requests/responses
├── api/
│   ├── __init__.py
│   └── routes.py              # FastAPI endpoints (/api/parse, /api/template/*, /api/export-excel, etc.)
├── static/
│   ├── index.html             # Zero-build SPA interactive web dashboard
│   ├── css/
│   │   └── app.css            # Responsive styles and offline fallback
│   └── js/
│       └── app.js             # Reactive UI logic, inline table editing, API client
├── templates_excel/
│   └── BẢNG CHẤM CÔNG WEVN - ETS.xlsx  # Bundled default template workbook
├── output/                    # Generated/updated Excel files
├── tests/
│   ├── __init__.py
│   ├── test_parser.py         # Unit tests for parser and time calculation
│   ├── test_excel.py          # Unit tests for excel reading, writing, formulas
│   ├── test_api.py            # API integration tests using TestClient
│   └── test_e2e.py            # Full end-to-end integration and formula verification
├── sample_data.csv            # Original sample attendance matrix specification
├── requirements.txt           # Dependencies (fastapi, uvicorn, pydantic, openpyxl, python-multipart, pytest)
├── run.py                     # Self-bootstrapping local server launcher
└── PROJECT.md                 # Master project blueprint
```

## Interface Contracts

### 1. Parser ↔ Domain Model (`models/attendance.py`)
```python
class WorkHours(BaseModel):
    hcn_100: float = 0.0     # Regular day hours (<= 8h, non-Sunday)
    tcn_150: float = 0.0     # Overtime day hours (> 8h, non-Sunday)
    hcd_130: float = 0.0     # Regular night hours (<= 8h, non-Sunday)
    tcd_195: float = 0.0     # Overtime night hours (> 8h, non-Sunday)
    sunday_day_200: float = 0.0    # Sunday daytime hours
    sunday_night_260: float = 0.0  # Sunday nighttime hours
    total_hours: float = 0.0

class AttendanceRecord(BaseModel):
    id: str
    employee_name: str
    normalized_name: str
    date_str: str            # Original string, e.g. "24/10" or "2026-10-24"
    resolved_date: str       # ISO YYYY-MM-DD, e.g. "2026-10-24"
    day_number: int          # Day of month (1..31)
    is_sunday: bool
    shift_type: str          # "DAY" | "NIGHT"
    project: str             # e.g. "sdv"
    time_window: str         # e.g. "8h-17h ( 8H)"
    hours: WorkHours
    meal_count: int          # 0 or 1 (or 2)
    status: str              # "VALID" | "WARNING" | "ERROR"
    messages: list[str] = [] # Warnings or errors explanation
    raw_text: str
```

### 2. Core ↔ Excel Engine (`core/excel_integrator.py`)
```python
class ExcelIntegrator:
    def __init__(self, template_path: str): ...
    def match_employee(self, name: str) -> tuple[int, str, float]:
        """Returns (start_row, matched_name, score)"""
    def resolve_date_column(self, date_str: str) -> int:
        """Returns 1-based column index (e.g. 11 for 24/10)"""
    def apply_records(self, records: list[AttendanceRecord], output_path: str) -> dict:
        """Applies records to workbook, preserves formulas, saves to output_path.
           Returns summary stats: total_records, updated_cells, errors."""
```

### 3. REST API Endpoints (`api/routes.py`)
- `POST /api/parse`: `{"text": str}` -> `{"records": list[AttendanceRecord], "summary": dict}`
- `GET /api/template/info`: -> `{"sheet_name": str, "employees": list[str], "date_range": list[str]}`
- `POST /api/template/upload`: `multipart/form-data` -> `{"status": "ok", "message": str}`
- `POST /api/export-excel`: `{"records": list[AttendanceRecord], "use_custom_template": bool}` -> `{"download_token": str, "summary": dict}`
- `GET /api/download/{token}`: -> StreamingResponse (`.xlsx` file download)
- `GET /api/sample`: -> `{"sample_text": str}`

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | F01_VIETNAMESE_NAME_NORM | Unicode NFC normalization, accent-insensitive & fuzzy matching | M1, M2 | survey_spec_miner_parser, survey_spec_miner_excel |
| 2 | F02_DATE_PARSING | Multi-format date parsing (DD/MM, DD-MM, YYYY-MM-DD), default 2026, Sunday detection | M1 | survey_spec_miner_parser |
| 3 | F03_SHIFT_HOUR_CALC | Accurate time calculation: HCN (100%), TCN (150%), HCĐ (130%), TCĐ (195%), Sunday day (200%), Sunday night (260%) | M1 | survey_spec_miner_parser |
| 4 | F04_MEAL_DETECTION | Detection of meal count (0, 1, Có, Không, ko, k, x, v) | M1 | survey_spec_miner_parser |
| 5 | F05_BATCH_SEGMENTATION | Dual-pass header lookahead regex parsing batch messages, non-crashing status tiers (VALID, WARNING, ERROR) | M1 | survey_spec_miner_parser |
| 6 | F06_TEMPLATE_GENERATION | Generate authentic default `BẢNG CHẤM CÔNG WEVN - ETS.xlsx` from `sample_data.csv` with Excel SUM formulas and styling | M2 | survey_spec_miner_excel |
| 7 | F07_EXCEL_COORDINATE_MAP | 7-row employee block resolution, date column mapping, 3-tier fuzzy employee matcher | M2 | survey_spec_miner_excel |
| 8 | F08_EXCEL_PRESERVATION | openpyxl `data_only=False` numeric writing, formula preservation (AK..AR and row 2), fullCalcOnLoad | M2 | survey_spec_miner_excel |
| 9 | F09_REST_API | FastAPI endpoints for parsing, preview, template inspection, export, and download | M3 | survey_explorer_arch |
| 10 | F10_WEB_DASHBOARD_UI | Zero-build interactive SPA: paste textarea, sample button, template selector, editable data grid, download | M3 | survey_explorer_arch |
| 11 | F11_BOOTSTRAP_LAUNCHER | Self-bootstrapping `run.py` launcher with environment check, venv setup, port fallback | M3 | survey_explorer_arch |
| 12 | F12_E2E_TEST_SUITE | Multi-tier test suite (Tiers 1-4) covering all features, boundary cases, pairwise combinations, realistic workloads | E2E | survey_explorer_arch |
| 13 | F13_ADVERSARIAL_HARDENING | Tier 5 adversarial stress testing, code coverage audit, and edge-case hardening | M4 | orchestrator plan |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| E2E | E2E Testing Track | Requirement-driven test suite (Tiers 1-4), harness, runner, TEST_READY.md | none | DONE |
| M1 | Attendance Message Parser | `models/attendance.py`, `core/parser.py`, unit test suite (F01, F02, F03, F04, F05) | none | DONE |
| M2 | Excel Integrator Engine | `core/template_generator.py`, `core/excel_integrator.py`, bundled xlsx (F06, F07, F08) | M1 models | DONE |
| M3 | Interactive Web Dashboard | `api/routes.py`, `main.py`, `static/`, `run.py` (F09, F10, F11) | M1, M2 | DONE |
| M4 | Final E2E Pass & Hardening | Phase 1: 100% pass of E2E suite (Tiers 1-4); Phase 2: Tier 5 Adversarial Hardening | M3, E2E | DONE |
