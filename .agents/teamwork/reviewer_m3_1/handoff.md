# Handoff Report: Milestone 3 Web API & Launcher Review

**Reviewer / Critic:** `reviewer_m3_1`  
**Milestone:** M3 (Web Dashboard, REST API & Launcher)  
**Date:** 2026-10-26T09:35:00Z  
**Verdict:** **APPROVE**  

---

## 1. Observation

Direct observations and execution outputs obtained during independent review:

1. **Target Deliverables Examined**:
   - `api/__init__.py`: REST API package definition.
   - `api/routes.py` (404 lines):
     * Endpoints implemented:
       - Line 194: `GET /api/health`
       - Line 200: `GET /api/sample`
       - Line 206: `POST /api/parse`
       - Line 237: `GET /api/template/info`
       - Line 254: `POST /api/template/upload`
       - Line 303: `POST /api/export-excel`
       - Line 377: `GET /api/download/{token}`
     * Schemas implemented: `ParseRequest`, `ExportExcelRequest`, `TemplateInfoResponse`, `ExportExcelResponse`, `SampleDataResponse`, `HealthResponse`.
     * Helper `_coerce_to_attendance_record`: Converts either `AttendanceRecord` or raw client dictionaries into valid `AttendanceRecord` instances with `WorkHours`.
   - `main.py` (52 lines):
     * Line 17: `FastAPI(title="Zalo Attendance Bot", ...)`
     * Line 24: `CORSMiddleware` configured with `allow_origins=["*"]`.
     * Line 33: `app.include_router(api_router, prefix="/api")`
     * Line 37: `app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")`
     * Line 40: `GET /` serves `static/index.html` as `text/html`.
   - `tests/test_api.py` (265 lines):
     * 16 unit and integration tests using `fastapi.testclient.TestClient`.
   - `run.py` (118 lines):
     * Self-bootstrapping launcher: Python version check (>=3.10 recommended, >=3.9 min), free port search (8000..8080), browser auto-launch background thread, and Uvicorn runner.

2. **Test Execution Verbatim Outputs**:
   - **Command 1**: `.venv/bin/pytest tests/test_api.py -v`
     ```
     ============================= test session starts ==============================
     platform darwin -- Python 3.11.17, pytest-9.1.1, pluggy-1.7.0 -- /Users/congcm/CODE/Vibe_Code/Zalo_BOT/.venv/bin/python3.11
     cachedir: .pytest_cache
     rootdir: /Users/congcm/CODE/Vibe_Code/Zalo_BOT
     plugins: anyio-4.15.1
     collecting ... collected 16 items

     tests/test_api.py::TestApiIntegration::test_01_root_serves_html PASSED   [  6%]
     tests/test_api.py::TestApiIntegration::test_02_static_assets_served PASSED [ 12%]
     tests/test_api.py::TestApiIntegration::test_03_api_health PASSED         [ 18%]
     tests/test_api.py::TestApiIntegration::test_04_api_sample PASSED         [ 25%]
     tests/test_api.py::TestApiIntegration::test_05_api_template_info PASSED  [ 31%]
     tests/test_api.py::TestApiIntegration::test_06_api_parse_single_standard_message PASSED [ 37%]
     tests/test_api.py::TestApiIntegration::test_06b_api_parse_full_date_valid PASSED [ 43%]
     tests/test_api.py::TestApiIntegration::test_07_api_parse_batch_mixed_messages PASSED [ 50%]
     tests/test_api.py::TestApiIntegration::test_08_api_parse_empty_payload PASSED [ 56%]
     tests/test_api.py::TestApiIntegration::test_09_api_parse_corrupt_payload PASSED [ 62%]
     tests/test_api.py::TestApiIntegration::test_10_api_export_excel_success_and_download PASSED [ 68%]
     tests/test_api.py::TestApiIntegration::test_11_api_download_invalid_token PASSED [ 75%]
     tests/test_api.py::TestApiIntegration::test_12_api_export_excel_empty_records PASSED [ 81%]
     tests/test_api.py::TestApiIntegration::test_13_api_template_upload_wrong_extension PASSED [ 87%]
     tests/test_api.py::TestApiIntegration::test_14_api_template_upload_valid_xlsx PASSED [ 93%]
     tests/test_api.py::TestApiIntegration::test_15_api_export_with_custom_template_flag PASSED [100%]
     ======================== 16 passed, 1 warning in 0.32s =========================
     ```
   - **Command 2**: `.venv/bin/pytest tests/`
     ```
     ======================== 268 passed, 1 warning in 0.85s ========================
     ```
   - **Command 3**: `.venv/bin/python3 tests/verify_e2e.py`
     ```
     Discovered 126 automated test cases across Tiers 1-4.
     [ PASS ]  AC1: Parser extracts HOÀNG ĐẮC PHÚ (24/10, Ca ngày, 8h, meal 0)
     [ PASS ]  AC2: Day/Night Shift & Overtime (HCN, TCN, HCĐ, TCĐ, CN) distinction
     [ PASS ]  AC3: Fault-tolerant batch parsing (VALID, WARNING, ERROR) with zero crashes
     [ PASS ]  AC4: Excel cell assignment to K24=8 (HCN) and K30=0 (Suất ăn) for HOÀNG ĐẮC PHÚ
     [ PASS ]  AC5: Excel formulas in AK..AR (=SUM) and row 2 grand totals preserved verbatim
     [ PASS ]  AC6: openpyxl data_only=False and fullCalcOnLoad enabled
     [ PASS ]  AC7: Web UI schema contracts (/api/parse, /api/export-excel, /api/template/info)
     [ PASS ]  AC8: One-command launcher run.py environment bootstrapping specification
     ================================================================================
                       4-TIER TEST COVERAGE AUDIT SUMMARY
     ================================================================================
      Tier 1   | Feature Coverage (F01..F11)            | >= 55    | 55       | PASS
      Tier 2   | Boundary & Corner Cases (F01..F11)     | >= 55    | 55       | PASS
      Tier 3   | Cross-Feature Pairwise Interactions    | >= 11    | 11       | PASS
      Tier 4   | Real-World Workload Scenarios          | >= 5     | 5        | PASS
     --------------------------------------------------------------------------------
      TOTAL    | Comprehensive Test Suite               | >= 126   | 126      | PASS
     ================================================================================
     Execution Statistics:
       - Total Run   : 126
       - Passed      : 126
       - Elapsed Time: 0.171 seconds
     >>> OVERALL VERIFICATION: SUCCESSFUL (ALL CRITERIA MET) <<<
     ```
   - **Command 4**: `.venv/bin/python3 run.py --help`
     ```
     usage: run.py [-h] [--host HOST] [--port PORT] [--no-browser] [--reload]
     ```

3. **Adversarial Probing Observations**:
   - Injected fake corrupted zip data labeled as `.xlsx` to `POST /api/template/upload`: returned HTTP 400 (`File is not a zip file`) and cleaned up the temporary file immediately.
   - Injected directory traversal string `../../../../etc/passwd` to `GET /api/download/{token}`: returned HTTP 404 (token store lookup failed; no file traversal possible).
   - Injected path traversal `../../../traversal_test.xlsx` into `output_filename`: regex `re.sub(r'[^a-zA-Z0-9_\-\. ]', '_', raw_fname)` neutralized directory separators (`/` -> `_`), containing output strictly within `output/`.
   - Injected extreme work hour values (999999.0): processed without server crash or formula corruption.
   - Tested empty payload `{records: []}`: returned HTTP 400 as expected.
   - Tested flat dictionary coercion: successfully serialized into domain models.

---

## 2. Logic Chain

1. **Contract Adherence (AC7)**:
   - The dispatch requested verification of 7 required endpoints: `GET /api/health`, `GET /api/sample`, `POST /api/parse`, `GET /api/template/info`, `POST /api/template/upload`, `POST /api/export-excel`, and `GET /api/download/{token}`.
   - Observation 1 confirms that all 7 endpoints are declared in `api/routes.py` with typed Pydantic models (`ParseRequest`, `ExportExcelRequest`, `TemplateInfoResponse`, `ExportExcelResponse`).
   - The test suite `tests/test_api.py` and `tests/verify_e2e.py` specifically validate these schemas and status codes.

2. **Integration & Correctness**:
   - `POST /api/parse` delegates parsing to `core.parser.parse_attendance_messages` rather than hardcoding results.
   - `POST /api/export-excel` instantiates `core.excel_integrator.ExcelIntegrator`, applies records to the Excel template, preserves `=SUM(...)` formulas in AK..AR, sets `fullCalcOnLoad=True`, and issues a download token.
   - `test_10_api_export_excel_success_and_download` downloads the generated binary stream and loads it with `openpyxl`: cell K24 contains 8, cell K30 contains 0, formula `=SUM(F24:AJ24)` is preserved verbatim, and `wb.calculation.fullCalcOnLoad` is True.

3. **Error Handling & Resilience**:
   - Malformed payloads return HTTP 400.
   - Invalid tokens return HTTP 404.
   - Non-xlsx or corrupt uploads return HTTP 400 and are unlinked from disk.

4. **Integrity Violations Check**:
   - Scanned `api/routes.py` and `main.py` for hardcoded fixture branching (e.g. checking if employee is "HOÀNG ĐẮC PHÚ" to bypass parser). No such shortcuts exist. Logic is genuine.
   - Zero facade logic or bypassed processing.

---

## 3. Caveats

- **In-Memory Token Store**: Export tokens are stored in `_EXPORT_TOKEN_STORE` (a module-level dictionary). For a desktop/local app this is fine, but in a long-running multi-user deployment, an LRU or TTL eviction policy should be added to avoid memory accumulation over weeks of uptime.
- **Single Active Uploaded Template**: `_CUSTOM_TEMPLATE_PATH` is stored globally; subsequent uploads replace the active custom template path. For a single-user local application this fulfills requirements completely.

---

## 4. Conclusion

The Milestone 3 REST API (`api/__init__.py`, `api/routes.py`), ASGI server (`main.py`), test suite (`tests/test_api.py`), and bootstrap launcher (`run.py`) are robust, well-structured, secure against common path traversal and malformed input vectors, and pass 100% of the test suite (16 API tests, 268 total pytest tests, 126 verify_e2e tests).

**Final Verdict: APPROVE**

---

## 5. Verification Method

To independently reproduce and verify this assessment:

1. Run API integration tests:
   ```bash
   .venv/bin/pytest tests/test_api.py -v
   ```
2. Run full regression test suite:
   ```bash
   .venv/bin/pytest tests/
   ```
3. Run end-to-end acceptance suite:
   ```bash
   .venv/bin/python3 tests/verify_e2e.py
   ```
4. Test launcher help:
   ```bash
   .venv/bin/python3 run.py --help
   ```
