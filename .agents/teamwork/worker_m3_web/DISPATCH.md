## 2026-10-26T09:19:46Z
You are the Web Dashboard & API Worker for Milestone 3.
Your working directory is: /Users/congcm/CODE/Vibe_Code/Zalo_BOT/.agents/teamwork/worker_m3_web/

MANDATORY FIRST STEPS:
1. Read /Users/congcm/CODE/Vibe_Code/Zalo_BOT/.agents/teamwork/ORIGINAL_REQUEST.md.
2. Read /Users/congcm/CODE/Vibe_Code/Zalo_BOT/PROJECT.md and /Users/congcm/CODE/Vibe_Code/Zalo_BOT/TEST_INFRA.md.
3. Review the architecture survey report: /Users/congcm/CODE/Vibe_Code/Zalo_BOT/.agents/teamwork/survey_explorer_arch/report.md.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Task: Implement Milestone 3 (Interactive Web Dashboard, REST API & Launcher):
Write ownership:
- You exclusively own:
  * api/__init__.py and api/routes.py
  * main.py
  * static/index.html
  * static/css/app.css
  * static/js/app.js
  * run.py
  * tests/test_api.py
- DO NOT break existing core/parser.py, core/excel_integrator.py, or existing tests.

Key Technical Requirements:
1. api/routes.py:
   - POST /api/parse: receives {"text": str}, calls parse_attendance_messages(text), returns {"records": list[AttendanceRecord], "summary": {"total": int, "valid": int, "warning": int, "error": int}}.
   - GET /api/template/info: calls ExcelIntegrator().get_template_info(), returns {sheet_name, employees, date_range}.
   - POST /api/template/upload: accepts file: UploadFile, validates .xlsx extension, saves to working template store, returns template metadata.
   - POST /api/export-excel: receives {"records": list[dict], "use_custom_template": bool}, converts records to AttendanceRecord objects, executes ExcelIntegrator().apply_records(...), saves output workbook in output/ with token, returns {"download_token": token, "filename": str, "summary": dict}.
   - GET /api/download/{token}: validates token, returns file as FileResponse with application/vnd.openxmlformats-officedocument.spreadsheetml.sheet and Content-Disposition: attachment; filename=....
   - GET /api/sample: returns realistic sample message batch (including HOÀNG ĐẮC PHÚ on 24/10 and multi-shift colleagues).
2. main.py:
   - Creates FastAPI app, includes API router at prefix /api, mounts /static directory, serves / with FileResponse("static/index.html").
3. static/ Frontend:
   - Modern, professional, responsive Zero-build SPA (Tailwind CSS via CDN + offline CSS in static/css/app.css).
   - Clean 3-step intuitive UI:
     * Step 1: Input text area with message counter, "Dán tin nhắn mẫu" 1-click test button, template toggle (Default bundled template vs Custom .xlsx upload), and "Bóc tách dữ liệu" primary button.
     * Step 2: Preview & Edit Table with summary metric badges (Tổng số, Hợp lệ, Cần chú ý, Lỗi), status filter buttons, interactive data grid (STT, Họ tên, Ngày, Ca, Giờ HC, Giờ Tăng ca, Giờ Đêm, Suất ăn, Trạng thái, Thao tác), inline cell editing (double-click/click to edit values directly) + row edit modal, row deletion, and row addition.
     * Step 3: "Xác nhận & Điền vào Excel" action button, execution feedback banner, direct download link/button for the updated .xlsx file, and detailed summary (records updated, cells written, unmatched warnings).
4. run.py:
   - Self-bootstrapping launcher: checks Python version >= 3.10, auto-detects free port (starts at 8000, tries 8001..8080 if bound), prints clean terminal banner, opens browser to http://localhost:<port>/, and runs Uvicorn server.
5. Unit & Integration test suite tests/test_api.py:
   - Comprehensive tests using TestClient:
     * Test / serves HTML
     * Test /api/sample returns sample text
     * Test /api/template/info returns sheet info
     * Test /api/parse parses standard and batch messages
     * Test /api/export-excel generates valid download token and writes cells correctly
     * Test /api/download/{token} streams valid .xlsx binary
     * Test /api/template/upload handles custom template
     * Test error handling for invalid tokens and malformed payloads.
6. Verification:
   - Run .venv/bin/pytest tests/test_api.py -v.
   - Run .venv/bin/pytest tests/ (all tests passing).
   - Run .venv/bin/python3 tests/verify_e2e.py.
   - Deliver handoff report to /Users/congcm/CODE/Vibe_Code/Zalo_BOT/.agents/teamwork/worker_m3_web/handoff.md and send message to parent.
