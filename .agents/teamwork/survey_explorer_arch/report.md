# Architecture & Web Dashboard Specification Report
**Project:** Zalo Attendance Local Web Application (`Zalo_BOT`)  
**Role:** Architecture & Web Explorer  
**Author:** survey_explorer_arch  
**Date:** 2026-10-26  
**Status:** COMPLETE  

---

## 1. Executive Summary

This report establishes the system architecture, technology stack, Web Dashboard UI/UX specification, modular code structure, and End-to-End (E2E) testing harness for the **Zalo Attendance Local Web Application**.

### Key Architectural Decisions:
1. **Runtime & Environment**:
   - **Python 3.11.17** via Homebrew (`/opt/homebrew/bin/python3.11`) configured with an isolated virtual environment (`.venv`). Avoids macOS system Python 3.9 conflicts and PEP 668 restrictions.
   - One-command launcher (`python3 run.py`) that auto-provisions `.venv`, validates dependencies, boots the server, and automatically opens the user's default browser to `http://127.0.0.1:8000`.
2. **Backend Web Framework**:
   - **FastAPI + Uvicorn (ASGI)**. Provides high-performance async execution, native Pydantic schema validation, automatic OpenAPI/Swagger documentation (`/docs`), static file serving, and seamless synchronous integration testing via `TestClient`.
3. **Frontend Architecture**:
   - **Zero-Build Single Page Application (SPA)** using modern Vanilla ES6+ JavaScript and Tailwind CSS (via CDN) complemented by a robust embedded offline CSS stylesheet (`styles.css`).
   - Requires **zero npm, zero Node.js build tools, zero Webpack/Vite complexity**. Operates 100% out-of-the-box in local and offline environments.
4. **Excel Engine**:
   - **openpyxl** configured with `data_only=False` to strictly preserve all existing Excel formulas (`SUM`, `IF`, etc.), merged headers, color fills, cell borders, and font metadata.
5. **E2E Testing Strategy**:
   - Multi-tier automated verification harness using `pytest` + `FastAPI TestClient` covering the full lifecycle: **Raw Zalo Text -> Parse & Hour Calculation -> UI Edit Simulation -> Excel Ingestion -> Excel Cell & Formula Verification**.

---

## 2. System Architecture & Environment Survey

### 2.1 macOS Environment Inspection

Direct probing of the host system yielded the following environment profile:

| Component | Path / Location | Version | Status & Recommendations |
| :--- | :--- | :--- | :--- |
| **System Python** | `/usr/bin/python3` | 3.9.6 | Outdated; lacks pip directly in PATH; subject to Apple CLT restrictions. **Do not use.** |
| **Homebrew Python** | `/opt/homebrew/bin/python3.11` | 3.11.17 | Modern, complete, includes pip 26.2.1 and standard library `venv`. **Recommended primary runtime.** |
| **Pip** | `/opt/homebrew/bin/pip3.11` | 26.2.1 | Fully functional. |
| **Node.js** | `~/.nvm/.../bin/node` | v20.19.1 | Available on machine, but intentionally **not used** for runtime to maintain a zero-dependency Python-only deployment. |
| **PyPI Network Access** | `https://pypi.org` | HTTP/2 200 | Online and responsive for standard package installations. |

### 2.2 Execution & Virtual Environment Strategy

To prevent polluting the global Python environment and ensure smooth local execution for end-users:
- The project will use a standard `.venv` virtual environment in the project root.
- A bootstrap script `run.py` will handle automatic setup:
  ```bash
  # End-user simply runs:
  python3.11 run.py
  ```
  `run.py` logic:
  1. Checks if `.venv` exists; if not, invokes `python3.11 -m venv .venv`.
  2. Checks if dependencies (`fastapi`, `uvicorn`, `openpyxl`, `python-multipart`, `pydantic`) are installed; if missing, runs `.venv/bin/pip install -r requirements.txt`.
  3. Launches Uvicorn server (`.venv/bin/uvicorn web.app:app --host 127.0.0.1 --port 8000`).
  4. Automatically opens `http://127.0.0.1:8000` in the user's default browser via `webbrowser.open()`.

### 2.3 Web Framework Evaluation: FastAPI vs Flask

| Evaluation Criteria | FastAPI + Uvicorn | Flask + Gunicorn / Werkzeug | Recommendation |
| :--- | :--- | :--- | :--- |
| **Data Validation & Typing** | **Native Pydantic v2**: Deep schema validation for parser results and export requests with automatic serialization. | Requires manual validation code or external libraries (Marshmallow, Pydantic). | **FastAPI** |
| **Interactive API Documentation** | **Automatic Swagger UI (`/docs`) & ReDoc (`/redoc`)** out of the box. Superb for debugging and manual testing. | Requires extra dependencies (`flasgger`, `flask-restx`). | **FastAPI** |
| **Static File Serving** | Native `StaticFiles(directory="static", html=True)`. High throughput. | `send_from_directory` or custom blueprint. | **FastAPI** |
| **File Upload & Streaming** | Native `UploadFile` async streaming for large `.xlsx` files. | Werkzeug `request.files`. | **FastAPI** |
| **Testing Harness** | `starlette.testclient.TestClient` (powered by `httpx`) enables instant, synchronous API testing without network sockets. | `flask.testing.FlaskClient`. | **FastAPI** |
| **Async Capability** | Native ASGI async/await. Smooth concurrency for parsing large batches. | Synchronous WSGI by default; requires Celery or gevent for async tasks. | **FastAPI** |

**Conclusion**: **FastAPI** is selected as the backend framework. It provides superior developer experience, rock-solid schema validation, zero-boilerplate API docs, and first-class integration with modern Python 3.11 typing.

### 2.4 Frontend Architecture: Zero-Build SPA

To satisfy the requirement of zero npm complexity and instant local startup:
- **Architecture**: Single Page Application (SPA) served statically by FastAPI from `/static/`.
- **CSS Styling**:
  - Primary: **Tailwind CSS via CDN** (`<script src="https://cdn.tailwindcss.com"></script>`) for modern, responsive, utility-first UI styling.
  - Offline Fallback: A lightweight embedded stylesheet (`/static/css/app.css`) providing essential CSS resets, grid/flex layouts, table borders, and status badges so that the UI remains fully functional even in air-gapped or offline corporate networks.
- **JavaScript Engine**: Modern **Vanilla ES6+** (`async/await`, `fetch`, DOM custom events, reactive state management).
  - Why Vanilla JS instead of React/Vue/Angular?
    - Eliminates `package.json`, `node_modules`, bundling, transpilation, and build steps.
    - Zero load latency: loads directly in < 50ms.
    - Simple state container pattern (`const state = { records: [], template: null, ... }`) easily handles the 3-step workflow (Input -> Preview/Edit -> Export).

---

## 3. Web Dashboard UI/UX Specification

The Web Dashboard is engineered as an intuitive 3-step operational workflow:

```
[ Step 1: Input & Template ]  ──>  [ Step 2: Interactive Preview & Edit ]  ──>  [ Step 3: Confirm & Export ]
   - Paste Zalo Chat Messages         - Validate records (Green/Amber)            - Write to Excel (openpyxl)
   - Select/Upload .xlsx template     - Inline edit names, hours, meals           - Download updated .xlsx
   - 1-Click "Parse / Bóc tách"       - Add / Delete row                          - View success summary
```

### 3.1 Detailed Screen Layout & Component Wireframe

#### Header & Navigation
- **Brand / Title**: "HỆ THỐNG ĐIỀU ĐỘ & CHẤM CÔNG ZALO" (with clock/calendar icon).
- **Status Indicator**: Green pill showing "Sẵn sàng" (Server Connected).
- **Quick Actions**: "Hướng dẫn sử dụng" (Help modal), "Xem tài liệu API" (link to `/docs`).

#### Step 1: Input & Configuration Section
1. **Raw Text Area**:
   - Large auto-expanding textarea (`rows=10`) with clear typography.
   - Placeholder demonstrating exact expected format:
     ```
     HỌ TÊN : HOÀNG ĐẮC PHÚ
     NGÀY: 24/10
     CA : Ca ngày 
     DỰ ÁN : sdv 
     THỜI GIAN LÀM VIỆC :8h-17h ( 8H)
     CÓ ĂN Ở XƯỞNG KO : 0
     ```
2. **Text Area Action Bar**:
   - **"Dán mẫu thử / Load Sample"** button: Pre-populates 5-10 realistic messages covering day shift, night shift, overtime, Sunday shifts, and meal options for instant 1-click verification.
   - **"Xóa trắng / Clear"** button: Clears the text area.
   - **Counter badge**: Live count of detected message blocks as the user types or pastes.
3. **Template Selector & Upload Card**:
   - Radio option 1 (Default): "Sử dụng file mẫu mặc định (`BẢNG CHẤM CÔNG WEVN - ETS.xlsx`)".
     - Displays template badge: `Sheet: T10-2026`, `32 nhân viên`, `Cột ngày: 19/10 -> 18/11`.
   - Radio option 2: "Tải lên file mẫu tùy chỉnh (.xlsx)".
     - Clean drag-and-drop file input accepting `.xlsx`.
     - File validation badge showing upload status and parsed sheet name.
4. **Primary Parse Action**:
   - Button: **"Bóc tách dữ liệu / Parse Messages"** (Indigo/Blue button with lightning icon).
   - Shows loading spinner during parsing.

#### Step 2: Interactive Preview & Edit Table
1. **Summary & Filter Toolbar**:
   - Metric Badges:
     - **Tổng số**: `N tin nhắn` (Gray)
     - **Hợp lệ**: `K bản ghi` (Emerald Green)
     - **Cần chú ý**: `M bản ghi` (Amber/Rose)
   - Filter segmented control: `[ Tất cả (N) ]` | `[ Hợp lệ (K) ]` | `[ Cần chú ý (M) ]`.
   - Action buttons:
     - **"+ Thêm dòng"**: Appends a blank row for manual entry.
     - **"Xóa tất cả"**: Clears preview table.
2. **Interactive Data Grid (Table)**:
   - Columns:
     1. `STT`: Sequential index (1, 2, 3...).
     2. `Họ và tên`: Inline editable text input. If name doesn't match template employee list, displays amber warning underline.
     3. `Ngày`: Inline editable date (e.g. `24/10` or `2026-10-24`).
     4. `Ca`: Dropdown select (`Ca ngày`, `Ca đêm`).
     5. `Giờ HC`: Number input (step 0.5, e.g. `8.0`).
     6. `Giờ Tăng ca`: Number input (step 0.5, e.g. `3.0`).
     7. `Giờ Đêm`: Number input (step 0.5, e.g. `8.0`).
     8. `Suất ăn`: Toggle / dropdown (`0: Không`, `1: Có ăn`).
     9. `Trạng thái`: Status badge:
        - `✓ Hợp lệ` (Green badge).
        - `⚠ Cần chú ý` (Amber badge) with interactive popover listing specific validation warnings (e.g. *"Tên chưa có trong bảng lương"*, *"Tổng giờ > 12h"*).
     10. `Thao tác`:
         - Edit button (opens detailed modal).
         - Delete button (red trash icon) with confirmation.
3. **Quick Edit Modal**:
   - For complex edits, clicking a row opens a modal displaying:
     - Original raw message text.
     - Project name / Xưởng.
     - Start and end time strings.
     - Calculation breakdown: Regular hours, Overtime hours, Night hours, Sunday hours.
     - Fuzzy matching suggestions dropdown with score (e.g. *"HOÀNG ĐẮC PHÚ (100% khớp)"*).

#### Step 3: Confirm & Excel Export Section
1. **Export Action Bar**:
   - Filename input (default: `BẢNG CHẤM CÔNG CẬP NHẬT [YYYY-MM-DD].xlsx`).
   - Primary Button: **"Xác nhận & Điền vào Excel"** (Emerald Green button with download icon).
2. **Result Notification & Feedback Banner**:
   - Appears immediately upon export completion.
   - Visual summary card:
     - `✓ Thành công`: Updated X cells across Y employees.
     - `ℹ Báo cáo`: All Excel formulas recalculated and verified.
     - **"Tải file Excel ngay / Download File"** button (triggers direct browser download).
     - Local file path indicator showing where the file was saved in the `./output/` directory.

---

## 4. REST API Specification

The backend exposes a clean, self-documenting REST API implemented with FastAPI.

### 4.1 Endpoint Overview

| Method | Endpoint | Description | Request Body | Response |
| :--- | :--- | :--- | :--- | :--- |
| `POST` | `/api/parse` | Parses raw batch Zalo messages into structured attendance records | `ParseRequest` (JSON) | `ParseResponse` (JSON) |
| `GET` | `/api/template/info` | Retrieves metadata, employee list, and date range from active template | None | `TemplateInfoResponse` (JSON) |
| `POST` | `/api/template/upload`| Uploads and activates a custom `.xlsx` template | `multipart/form-data` | `TemplateInfoResponse` (JSON) |
| `POST` | `/api/export-excel` | Ingests verified records into Excel and generates updated `.xlsx` | `ExportExcelRequest` (JSON) | `ExportExcelResponse` (JSON) |
| `GET` | `/api/download/{token}` | Downloads the generated Excel file | None | Binary `.xlsx` stream |
| `GET` | `/api/sample` | Returns pre-canned standard test messages for instant UI testing | None | `SampleDataResponse` (JSON) |
| `GET` | `/api/health` | Healthcheck and environment diagnostic status | None | `HealthResponse` (JSON) |

### 4.2 Detailed Schema Contracts (Pydantic Models)

#### `POST /api/parse`
**Request Payload**:
```json
{
  "raw_text": "HỌ TÊN : HOÀNG ĐẮC PHÚ\nNGÀY: 24/10\nCA : Ca ngày \nDỰ ÁN : sdv \nTHỜI GIAN LÀM VIỆC :8h-17h ( 8H)\nCÓ ĂN Ở XƯỞNG KO : 0",
  "default_year": 2026
}
```

**Response Payload**:
```json
{
  "success": true,
  "total_detected": 1,
  "valid_count": 1,
  "warning_count": 0,
  "records": [
    {
      "id": "rec_001",
      "raw_text": "HỌ TÊN : HOÀNG ĐẮC PHÚ\n...",
      "employee_name": "HOÀNG ĐẮC PHÚ",
      "matched_employee_name": "HOÀNG ĐẮC PHÚ",
      "date": "2026-10-24",
      "day_display": "24/10",
      "shift": "Ca ngày",
      "project": "sdv",
      "working_hours_raw": "8h-17h ( 8H)",
      "hcn_100": 8.0,
      "tcn_150": 0.0,
      "hcd_130": 0.0,
      "tcd_195": 0.0,
      "sunday_day_200": 0.0,
      "sunday_night_260": 0.0,
      "meals": 0,
      "status": "VALID",
      "issues": []
    }
  ]
}
```

#### `POST /api/export-excel`
**Request Payload**:
```json
{
  "template_source": "default",
  "output_filename": "BANG_CHAM_CONG_CAP_NHAT.xlsx",
  "records": [
    {
      "employee_name": "HOÀNG ĐẮC PHÚ",
      "date": "2026-10-24",
      "hcn_100": 8.0,
      "tcn_150": 0.0,
      "hcd_130": 0.0,
      "tcd_195": 0.0,
      "sunday_day_200": 0.0,
      "sunday_night_260": 0.0,
      "meals": 0
    }
  ]
}
```

**Response Payload**:
```json
{
  "success": true,
  "download_token": "export_20261026_073901_abc123",
  "download_url": "/api/download/export_20261026_073901_abc123",
  "file_path": "/Users/congcm/CODE/Vibe_Code/Zalo_BOT/output/BANG_CHAM_CONG_CAP_NHAT.xlsx",
  "summary": {
    "total_records_received": 1,
    "employees_updated": 1,
    "cells_written": 2,
    "unmatched_employees": []
  }
}
```

---

## 5. Modular Code Layout & Project Structure

The project structure is organized with strict separation between business logic, data models, web delivery, and test harnesses:

```
/Users/congcm/CODE/Vibe_Code/Zalo_BOT/
├── README.md                          # Quick start, system architecture, usage instructions
├── requirements.txt                   # Production dependencies (fastapi, uvicorn, openpyxl, python-multipart)
├── requirements-dev.txt               # Testing dependencies (pytest, httpx)
├── run.py                             # One-command bootstrapper & browser launcher
├── main.py                            # CLI entrypoint & ASGI application factory
│
├── core/                              # Core Domain & Business Logic (Framework-agnostic)
│   ├── __init__.py
│   ├── parser.py                      # Multi-message splitter & regex-based token extractor
│   ├── rules.py                       # Work hour & overtime calculation engine (HCN, TCN, HCĐ, TCĐ, Sunday)
│   ├── excel_engine.py                # openpyxl engine: formula, style, and structure preservation
│   ├── matcher.py                     # Vietnamese name normalizer & fuzzy matching algorithm
│   └── template_generator.py          # Builds default BẢNG CHẤM CÔNG WEVN - ETS.xlsx from sample_data.csv
│
├── models/                            # Pydantic Schemas & Data Transfer Objects
│   ├── __init__.py
│   ├── attendance.py                  # Domain models: AttendanceRecord, ShiftType, ValidationStatus
│   └── api_schemas.py                 # API contracts: ParseRequest, ExportRequest, TemplateInfo
│
├── api/                               # FastAPI Routers & Web Controllers
│   ├── __init__.py
│   ├── routes_parse.py                # POST /api/parse handler
│   ├── routes_excel.py                # POST /api/export-excel, /api/template handlers
│   └── routes_system.py               # GET /api/health, GET /api/sample handlers
│
├── templates_excel/                   # Bundled Excel Templates
│   └── BANG_CHAM_CONG_WEVN_ETS.xlsx  # Official base template generated with authentic formulas & formatting
│
├── static/                            # Frontend Single Page Application (Zero Build Step)
│   ├── index.html                     # Main interactive dashboard UI
│   ├── css/
│   │   └── app.css                    # Offline fallback stylesheet & custom responsive styles
│   └── js/
│       ├── app.js                     # SPA Controller & State Store
│       ├── table.js                   # Interactive preview table, inline editing & badge rendering
│       └── sample.js                  # Pre-configured sample Zalo messages
│
├── output/                            # Destination for generated Excel files
│   └── .gitkeep
│
└── tests/                             # Comprehensive Automated Test Suite
    ├── __init__.py
    ├── conftest.py                    # Pytest fixtures: sample messages, openpyxl template mocks
    ├── test_parser.py                 # Unit tests for message syntax & tokenization (R1)
    ├── test_rules.py                  # Unit tests for hour calculation rules (HCN, TCN, Sunday)
    ├── test_matcher.py                # Unit tests for Vietnamese name normalization & fuzzy matching
    ├── test_excel_engine.py           # Unit tests for openpyxl read/write & formula preservation (R3)
    ├── test_api.py                    # Integration tests for FastAPI endpoints (R2)
    └── test_e2e.py                    # Complete End-to-End Pipeline test (Parse -> Edit -> Excel -> Verify)
```

### Module Responsibilities:
- `core/parser.py`: Accepts multi-message raw text, identifies message boundaries using delimiter heuristics, extracts fields (`HỌ TÊN`, `NGÀY`, `CA`, `DỰ ÁN`, `THỜI GIAN LÀM VIỆC`, `CÓ ĂN Ở XƯỞNG KO`), and handles formatting anomalies.
- `core/rules.py`: Converts time intervals (e.g. `8h-17h (8H)`, `8h-20h (11H)`, `20h-8h (11H)`) into exact hour classifications (100% Day, 150% Overtime Day, 130% Night, 195%/200% Overtime Night, Sunday multipliers) based on calendar day of week.
- `core/matcher.py`: Normalizes Vietnamese accents, lowercases, removes duplicate whitespace, and matches candidate names against the 32 template employees with similarity scoring.
- `core/excel_engine.py`: Loads the workbook with `data_only=False`. Finds the 7-row block for the target employee, resolves the target date column (columns 6 to 36), writes hours and meal counts, and saves without altering formula cells like `=SUM(F4:AJ4)`.
- `core/template_generator.py`: Generates the default `.xlsx` file using `sample_data.csv` as ground truth, setting up real Excel formulas (`SUM`), bold headers, light gray alternating fills, and thin borders.

---

## 6. End-to-End (E2E) Testing Strategy & Verification Harness

To guarantee absolute software reliability and fulfill every Acceptance Criterion, the project implements a rigorous 4-Tier test harness.

### 6.1 Testing Tiers

```
┌─────────────────────────────────────────────────────────────┐
│ Tier 4: Excel Integrity & Formula Recalculation Check       │
│ (Inspects XML/openpyxl: SUM formulas intact, styles retained)│
├─────────────────────────────────────────────────────────────┤
│ Tier 3: Full End-to-End Pipeline Test                       │
│ (Raw text -> API /parse -> UI edit -> /export-excel -> .xlsx)│
├─────────────────────────────────────────────────────────────┤
│ Tier 2: FastAPI Web API Integration Tests                   │
│ (TestClient tests: payload validation, error codes, headers) │
├─────────────────────────────────────────────────────────────┤
│ Tier 1: Core Domain Unit Tests                              │
│ (Parser regex, Hour calculation, Name matcher, openpyxl IO)  │
└─────────────────────────────────────────────────────────────┘
```

### 6.2 Test Suite Specifications

#### Tier 1: Core Domain Unit Tests
- `test_parser.py`:
  - Standard format parsing: Verifies the reference message:
    ```
    HỌ TÊN : HOÀNG ĐẮC PHÚ
    NGÀY: 24/10
    CA : Ca ngày 
    DỰ ÁN : sdv 
    THỜI GIAN LÀM VIỆC :8h-17h ( 8H)
    CÓ ĂN Ở XƯỞNG KO : 0
    ```
    Extracts: Name="HOÀNG ĐẮC PHÚ", Date="2026-10-24", Shift="Ca ngày", Hours=8.0 HCN, Meals=0.
  - Multi-message batches: 10 messages pasted continuously separated by blank lines or headers.
  - Edge cases: Lowercase headers (`họ tên:`), irregular spaces (`CA:Ca ngày`), varied meal indicators (`có`, `k`, `ko`, `1`, `0`).
- `test_rules.py`:
  - Day shift normal: `8h-17h` -> 8h HCN 100%, 0h TCN.
  - Day shift overtime: `8h-20h (11H)` -> 8h HCN 100%, 3h TCN 150%.
  - Night shift normal: `20h-5h (8H)` -> 8h HCĐ 130%, 0h TCĐ.
  - Night shift overtime: `20h-8h (11H)` -> 8h HCĐ 130%, 3h TCĐ 195%.
  - Sunday multiplier: Any date resolving to Sunday correctly assigns hours to `Ngày CN (200%)` or `Đêm CN (260%)`.
- `test_matcher.py`:
  - Exact match: `"HOÀNG ĐẮC PHÚ"` -> `"HOÀNG ĐẮC PHÚ"`.
  - Case & space insensitivity: `"  hoàng đắc phú  "` -> `"HOÀNG ĐẮC PHÚ"`.
  - Unaccented match fallback: `"Hoang Dac Phu"` -> `"HOÀNG ĐẮC PHÚ"`.
- `test_excel_engine.py`:
  - Template generation: Builds valid `.xlsx` from `sample_data.csv`.
  - Cell coordinate resolution: Accurately maps `HOÀNG ĐẮC PHÚ` + date `2026-10-24` to row 25 (HCN 100%) and row 31 (Suất ăn), column 11 (2026-10-24).
  - Formula preservation: Confirms cell `AK25` contains formula `=SUM(F25:AJ25)` both before and after write.

#### Tier 2: FastAPI API Integration Tests (`test_api.py`)
- Employs `starlette.testclient.TestClient` (zero external network requirement).
- `POST /api/parse`:
  - Valid input returns status 200 with JSON records.
  - Empty or invalid input returns friendly 200 with `records: []` and warning messages (does not crash with 500).
- `POST /api/export-excel`:
  - Accepts validated records, runs Excel engine, returns download token.
  - `GET /api/download/{token}` returns HTTP 200 with headers `Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` and `Content-Disposition`.
- `GET /api/template/info`:
  - Returns template metadata, list of 32 employees, date range from 2026-10-19 to 2026-11-18.

#### Tier 3 & Tier 4: E2E Pipeline & Excel Integrity Verification (`test_e2e.py`)
- End-to-end integration test execution path:
  1. Input raw Zalo text containing 3 test employees (including HOÀNG ĐẮC PHÚ on 24/10).
  2. Call `/api/parse` to extract records.
  3. Simulate user modification in UI (e.g. adjust meal from 0 to 1 for one employee).
  4. Call `/api/export-excel` with the modified records.
  5. Fetch generated `.xlsx` file from the output directory.
  6. Reload the `.xlsx` via `openpyxl`:
     - Inspect cell for HOÀNG ĐẮC PHÚ, date 2026-10-24, row `HCN 100%`: value must be `8`.
     - Inspect cell for HOÀNG ĐẮC PHÚ, date 2026-10-24, row `Suất ăn`: value must be `0`.
     - Inspect summary formula cell for `HCN 100%`: must still contain `=SUM(F25:AJ25)`.
     - Inspect cell styling: background fill, font family, border line styles match original template.
     - Inspect unedited employee cells: remain completely unmodified.

### 6.3 Automated CI / Verification Script

In addition to `pytest`, a standalone script `verify_e2e.py` will be provided. It can be run with standard Python:
```bash
python3 verify_e2e.py
```
This script executes the entire pipeline headless, prints an ASCII status checklist for each acceptance criterion, and exits with code 0 on success or 1 on failure.

---

## 7. Implementation Roadmap & Recommendation for Orchestrator

To ensure clean, defect-free execution across parallel development tracks, the following milestone breakdown is recommended:

| Milestone | Deliverables | Key Verification Gating |
| :--- | :--- | :--- |
| **M0: Environment & Template Foundation** | - `requirements.txt`<br>- `run.py` launcher<br>- `core/template_generator.py`<br>- Bundled `BANG_CHAM_CONG_WEVN_ETS.xlsx` | Run template generator; verify generated Excel matches `sample_data.csv` layout and formulas in openpyxl. |
| **M1: Parser & Rules Engine** | - `models/attendance.py`<br>- `core/parser.py`<br>- `core/rules.py`<br>- `tests/test_parser.py`<br>- `tests/test_rules.py` | 100% pass on reference message (`HOÀNG ĐẮC PHÚ`, 24/10, Ca ngày, 8H, meal 0) + day/night overtime test suite. |
| **M2: Excel Integrator & Fuzzy Matcher** | - `core/matcher.py`<br>- `core/excel_engine.py`<br>- `tests/test_matcher.py`<br>- `tests/test_excel_engine.py` | Write to generated template; verify cell coordinates; confirm openpyxl preserves formulas with `data_only=False`. |
| **M3: FastAPI Backend & API Layer** | - `models/api_schemas.py`<br>- `api/routes_parse.py`<br>- `api/routes_excel.py`<br>- `api/routes_system.py`<br>- `main.py`<br>- `tests/test_api.py` | TestClient passes for `/api/parse`, `/api/export-excel`, `/api/template/info`. |
| **M4: Web Dashboard Frontend (SPA)** | - `static/index.html`<br>- `static/css/app.css`<br>- `static/js/app.js`<br>- `static/js/table.js`<br>- `static/js/sample.js` | UI loads cleanly; paste -> parse -> inline edit -> export download works smoothly in browser without console errors. |
| **M5: Integrated E2E Verification** | - `tests/test_e2e.py`<br>- `verify_e2e.py` | Full E2E suite passes; HOÀNG ĐẮC PHÚ test case verified end-to-end. |

---

## 8. Summary of Findings

1. **Python 3.11** is already installed and fully capable on this host machine.
2. **FastAPI + Vanilla JS SPA** provides the optimal combination of modern software architecture, rapid local development, zero npm build friction, and robust schema validation.
3. **openpyxl** with `data_only=False` satisfies the Excel integrity requirement, allowing cell injection while strictly preserving Excel summary formulas (`SUM`).
4. The 3-step dashboard UX directly addresses user operational efficiency, offering 1-click sample testing, interactive error correction, and instant Excel file export.
