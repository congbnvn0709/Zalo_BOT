# Handoff Report: Web Frontend & Launcher Review (Milestone 3)

**Reviewer:** `reviewer_m3_2` (Reviewer 2, Roles: reviewer, critic)  
**Milestone:** Milestone 3 (Web Dashboard, REST API & Launcher)  
**Date:** 2026-10-26T09:36:00Z  
**Verdict:** **APPROVE**  

---

## 1. Observation

Direct observations and evidence verified during the review:

1. **Acceptance Criteria AC8 & Launcher (`run.py`)**:
   - Python version check (`run.py:22-28`): Evaluates `sys.version_info`; enforces >= 3.9 as fatal requirement (`sys.exit(1)`) and >= 3.10 as recommended baseline.
   - Automatic port probing (`run.py:40-53`): `find_free_port(host, start_port=8000, max_port=8080)` verifies availability using socket connection check and socket `bind` attempt. Tested by artificially binding port 8000 in a background socket: `find_free_port` correctly detected occupancy and returned `8001`.
   - Browser launch automation (`run.py:69-76`): Safely executes `webbrowser.open(url)` inside a daemon background thread (`run.py:110`) protected by `try...except Exception`, ensuring non-blocking execution and graceful degradation in headless/CI environments.
   - CLI arguments: Tested via `.venv/bin/python3 run.py --help`:
     ```
     usage: run.py [-h] [--host HOST] [--port PORT] [--no-browser] [--reload]

     Zalo Attendance Bot Launcher

     options:
       -h, --help    show this help message and exit
       --host HOST   Host interface (default: 127.0.0.1)
       --port PORT   Initial port to bind (default: 8000)
       --no-browser  Do not automatically launch browser
       --reload      Enable auto-reload on code change
     ```
     Tested direct parser execution with `--port 9000 --host 0.0.0.0 --no-browser --reload`, confirming Uvicorn receives matching arguments.

2. **Web UI & UX Architecture (`static/index.html`, `static/css/app.css`, `static/js/app.js`)**:
   - **Zero-build SPA**: Uses Tailwind CSS via CDN (`https://cdn.tailwindcss.com`) and Vanilla ES6+ JavaScript without npm, webpack, or any compilation step.
   - **Offline CSS fallback (`static/css/app.css`)**: Implements standalone layout and component styling, including custom status badges (`.badge-valid`, `.badge-warning`, `.badge-error`), modal overlays (`.modal-overlay`, `.modal-content`), inline editable cells (`.editable-cell`), and spinners (`.spinner`).
   - **3-step operational workflow**:
     * *Step 1 (Input)*: Textarea with live message count listener (`#zalo-raw-text`, `#text-counter`), 1-click test button ("Dán tin nhắn mẫu" calling `/api/sample`), clear button ("Xóa trắng"), template radio toggle (default vs custom upload `.xlsx`), and "Bóc tách dữ liệu" button.
     * *Step 2 (Preview Grid)*: Status filtering tabs ("Tất cả", "Hợp lệ", "Cần chú ý", "Lỗi"), interactive table columns (STT, Họ và tên, Ngày, Ca, Giờ HC, Giờ Tăng ca, Giờ Đêm, Suất ăn, Trạng thái, Thao tác), inline click-to-edit with blur/Enter commit and Escape cancel, detailed modal edit dialog, row addition (`#btn-add-row`), and row deletion (`.btn-delete-row`).
     * *Step 3 (Excel Export & Download)*: Custom filename field, execution button ("Xác nhận & Điền vào Excel"), feedback banner with detailed metrics (records processed, employees matched, cells written, 100% SUM formula preservation), warnings list for unmapped employees, and direct download anchor pointing to `/api/download/{token}`.

3. **Integrity & Adversarial Checks**:
   - **Integrity**: Checked for hardcoding or facade implementations. Core calculations and parsing are dynamically delegated to `core.parser` and `core.excel_integrator`. The API properly coerces both Pydantic models and flat UI dictionaries (`api/routes.py:_coerce_to_attendance_record`). No dummy mock data or bypassed checks detected.
   - **XSS Sanitization**: User-controlled strings are escaped via `escapeHtml()` in `static/js/app.js:20-28` before being injected into HTML attributes or table cells, and DOM element assignment uses `.textContent` where appropriate.
   - **Path Traversal Defense**: In `api/routes.py:335`, `re.sub(r'[^a-zA-Z0-9_\-\. ]', '_', raw_fname)` sanitizes path separators, and files are saved strictly under `DEFAULT_OUTPUT_DIR` prefixed with a random token (`export_{uuid}_{filename}`). Tested with adversarial filename `../../etc/passwd.xlsx` -> confirmed safely confined to `output/export_{token}_.._.._etc_passwd.xlsx`.

4. **Integration Test Suite Execution**:
   - `.venv/bin/pytest tests/test_api.py -v`: 16 passed in 0.40s.
   - `.venv/bin/python3 tests/verify_e2e.py`: 126 passed across Tiers 1-4, all Acceptance Criteria PASS.
   - `.venv/bin/pytest tests/ -v`: 268 passed in 0.92s with zero failures.
   - Simulated 3-step UI workflow with inline edits and manual row addition:
     * Parsed 5 sample messages.
     * Edited HOÀNG ĐẮC PHÚ's HCN to 7.5 and meal to 1.
     * Added manual record for NGUYỄN NGỌC THAO on Sunday 25/10 (8h Sunday day).
     * Exported to Excel and loaded resulting binary into `openpyxl`: verified K24=7.5, K30=1, NGUYỄN NGỌC THAO Sunday day row (row 7 col 12)=8.0, and formula `=SUM(F24:AJ24)` intact.

---

## 2. Logic Chain

1. **Launcher Conformance**:
   - Observations 1 show that `run.py` fulfills all launcher requirements in AC8: verifies Python version, probes free ports in the range 8000..8080 when 8000 is occupied, auto-opens the browser gracefully, and parses CLI arguments without crash.

2. **Web Frontend Conformance**:
   - Observations 2 confirm that `static/index.html`, `static/css/app.css`, and `static/js/app.js` satisfy R2 and the 3-step operational flow without requiring any build system (zero-build).
   - In-memory state in `app.js` correctly maintains parsed records, responds to status filters, supports inline editing, and translates UI changes into payload structures recognized by `api/routes.py`.

3. **Backend & Excel Integration Conformance**:
   - Observations 3 and 4 confirm that edits made on the frontend are faithfully written to the Excel template via `POST /api/export-excel` and can be downloaded immediately via `/api/download/{token}` with preserved formulas.

4. **Adversarial Resilience & Integrity**:
   - The implementation was checked against all integrity violation criteria. No hardcoded outputs, facade implementations, or verification shortcuts exist.

Therefore, the work product meets all specified criteria and is approved.

---

## 3. Caveats

- **Upload Filename Sanitization**: In `api/routes.py:upload_custom_template`, `file.filename` is used in `saved_path = os.path.join(upload_dir, f"custom_{int(time.time())}_{filename}")`. While running in a local environment, applying `os.path.basename(file.filename)` is recommended for maximum hardening against malicious path components.
- **In-Memory Token Store**: `_EXPORT_TOKEN_STORE` is stored in process memory. Download tokens expire if the server process is restarted. For a local desktop launcher workflow, this is completely acceptable.

---

## 4. Conclusion

**Verdict: APPROVE**

Milestone 3 (Web Frontend & Launcher) is robust, well-structured, completely adheres to specifications (AC8, zero-build SPA, 3-step workflow, offline CSS), passes 100% of integration and unit tests, and exhibits no integrity violations.

---

## 5. Verification Method

To independently reproduce the verification:

1. **Verify API Integration Tests**:
   ```bash
   .venv/bin/pytest tests/test_api.py -v
   ```
   *Expected*: 16 passed in ~0.4s.

2. **Verify End-to-End Acceptance Harness**:
   ```bash
   .venv/bin/python3 tests/verify_e2e.py
   ```
   *Expected*: Exit code 0, 126 test cases passed, all AC items PASS.

3. **Verify Full Pytest Suite**:
   ```bash
   .venv/bin/pytest tests/ -v
   ```
   *Expected*: 268 passed in < 1.0s.

4. **Verify Launcher CLI Options**:
   ```bash
   .venv/bin/python3 run.py --help
   ```
   *Expected*: Exit code 0, displays `--host`, `--port`, `--no-browser`, `--reload`.
