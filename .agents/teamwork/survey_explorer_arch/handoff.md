# 5-Component Handoff Report: Architecture & Web Explorer

**Agent:** `survey_explorer_arch`  
**Milestone:** `architecture_and_web_survey`  
**Working Directory:** `/Users/congcm/CODE/Vibe_Code/Zalo_BOT/.agents/teamwork/survey_explorer_arch/`  
**Date:** 2026-10-26T07:44:00Z  
**Handoff Type:** Hard (Task Complete)  

---

## 1. Observation
- **System Environment**:
  - `/usr/bin/python3` is macOS system Python 3.9.6, lacking pip directly in PATH.
  - `/opt/homebrew/bin/python3.11` is available on the machine (`Python 3.11.17`, pip 26.2.1), with working standard `venv`.
  - Node.js v20.19.1 and npm are present at `~/.nvm/versions/node/v20.19.1/bin/node`, but the project specification explicitly mandates zero-build frontend (no npm complexity).
  - Outbound network connectivity to PyPI (`https://pypi.org`) is confirmed functional (HTTP/2 200).
- **Existing Project Files**:
  - `/Users/congcm/CODE/Vibe_Code/Zalo_BOT/sample_data.csv` exists and defines the structure of the attendance sheet:
    - 32 employees, 7-row block per employee (`HCN 100%`, `TCN 150%`, `HCĐ 130%`, `TCĐ 195%`, `Ngày CN (200%)`, `Đêm CN (260%)`, `Suất ăn`).
    - Dates range across columns from 2026-10-19 to 2026-11-18.
    - Summary formula columns for `HC NGÀY (100%)`, `TC NGÀY (150%)`, ..., `TỔNG CÔNG`.
    - Employee #10 is `HOÀNG ĐẮC PHÚ`, who has `8` in `2026-10-24` row `HCN 100%` and `0` in `Suất ăn`.
- **Target Deliverable**:
  - Comprehensive report written to `/Users/congcm/CODE/Vibe_Code/Zalo_BOT/.agents/teamwork/survey_explorer_arch/report.md`.

---

## 2. Logic Chain
1. **Python Runtime Selection**:
   - macOS system Python 3.9 is outdated and subject to Apple CLT restrictions. Homebrew Python 3.11 (`/opt/homebrew/bin/python3.11`) is modern and supports Pydantic v2 and FastAPI seamlessly.
   - Therefore, use standard `.venv` created via `python3.11 -m venv .venv` and manage via a self-bootstrapping `run.py` launcher.
2. **Backend Framework Selection (FastAPI vs Flask)**:
   - The application requires parsing batch text into typed structures, validating fields, and returning structured data to the frontend grid.
   - FastAPI natively integrates Pydantic schemas, provides automatic interactive API documentation at `/docs`, supports async static file mounting, and provides `starlette.testclient.TestClient` for synchronous, socket-free integration testing.
   - Therefore, FastAPI + Uvicorn is the superior choice over Flask.
3. **Frontend Architecture Selection**:
   - Requirement R2 specifies an interactive web dashboard running out-of-the-box locally without npm complexity.
   - A Single Page Application (SPA) with Vanilla ES6+ JS and Tailwind CSS (via CDN) with an embedded CSS fallback (`/static/css/app.css`) ensures zero build step, instant local startup, offline resilience, and modern visual design.
4. **Excel Read/Write Engine Selection**:
   - The original request mandates preserving all formatting, merged cells, colors, and formula summaries (`HC NGÀY`, `TỔNG CÔNG`).
   - `openpyxl` with `data_only=False` preserves existing Excel formula syntax without overwriting formulas with static values.
   - Because `sample_data.csv` is currently a CSV, a template generator (`core/template_generator.py`) is designed to produce the authentic default `.xlsx` workbook (`BẢNG CHẤM CÔNG WEVN - ETS.xlsx`) with real Excel formulas (`=SUM(...)`).
5. **E2E Testing Architecture**:
   - By structuring the application into pure Python business logic (`core/`), Pydantic models (`models/`), API routers (`api/`), and static frontend (`static/`), the testing harness can test every tier deterministically:
     - Tier 1: Unit tests for parser, rules, and matcher.
     - Tier 2: FastAPI API tests via `TestClient`.
     - Tier 3: Full pipeline test (Text -> API -> openpyxl -> Output file inspection).
     - Tier 4: Excel formula and styling retention check.

---

## 3. Caveats
- **Offline CDN Dependency**: If the user operates completely offline without internet access, Tailwind CSS CDN may not load. To safeguard against this, an embedded fallback CSS stylesheet (`/static/css/app.css`) must define base responsive tables, grid layouts, and status badge styles.
- **Excel Formula Evaluation in openpyxl**: `openpyxl` writes and preserves formula strings (e.g. `=SUM(F4:AJ4)`), but does not recalculate formula values itself unless opened in Microsoft Excel / LibreOffice. Automated tests verifying formula presence must assert the formula string (`cell.value == "=SUM(F4:AJ4)"`) rather than relying on cached formula evaluation results.
- **Port Conflicts**: Port 8000 might already be in use on the user's machine. The bootstrap launcher `run.py` should implement fallback port detection (e.g. trying 8000, then 8001, 8080) if port 8000 is bound.

---

## 4. Conclusion
The architecture and web dashboard design are fully analyzed and specified:
- **Backend**: FastAPI + Uvicorn + Pydantic v2 in an isolated Python 3.11 `.venv`.
- **Frontend**: Zero-build Vanilla JS SPA with Tailwind CDN and offline CSS fallback.
- **Excel Engine**: `openpyxl` with `data_only=False` reading/writing to `BẢNG CHẤM CÔNG WEVN - ETS.xlsx`.
- **UI/UX Flow**: 3-step workflow (Input/Template -> Interactive Preview/Edit Grid -> Confirm & Download).
- **Code Layout**: Modular directory structure under `/Users/congcm/CODE/Vibe_Code/Zalo_BOT/` clearly separating domain logic, API, templates, static frontend, and automated tests.
- **E2E Strategy**: 4-Tier test harness ensuring 100% adherence to all Acceptance Criteria.

---

## 5. Verification Method
To verify the architecture report and environment readiness:
1. **Verify Report Artifacts**:
   - Inspect `/Users/congcm/CODE/Vibe_Code/Zalo_BOT/.agents/teamwork/survey_explorer_arch/report.md`
2. **Verify Python 3.11 Runtime**:
   ```bash
   /opt/homebrew/bin/python3.11 --version
   /opt/homebrew/bin/pip3.11 --version
   ```
3. **Verify sample data structure**:
   ```bash
   head -n 12 /Users/congcm/CODE/Vibe_Code/Zalo_BOT/sample_data.csv
   ```
4. **Verify PyPI accessibility**:
   ```bash
   curl -I -m 5 https://pypi.org
   ```
