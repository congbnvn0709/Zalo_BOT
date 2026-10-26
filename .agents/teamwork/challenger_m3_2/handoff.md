# Milestone 3 Handoff Report — Launcher & End-to-End Challenger 2

**Agent**: `challenger_m3_2` (Launcher & End-to-End Challenger 2)  
**Date**: 2026-10-26T09:44:00Z  
**Verdict**: **APPROVE**

---

## 1. Observation

### 1.1 Launcher & Port Collision Handling (`run.py`)
- In `run.py`, the port detection functions are:
  - `is_port_in_use(port: int, host: str = "127.0.0.1") -> bool` (lines 34-37)
  - `find_free_port(host: str = "127.0.0.1", start_port: int = 8000, max_port: int = 8080) -> int` (lines 40-52)
- **Single Port Collision (8000 -> 8001)**:
  - Binding a dummy socket to `('127.0.0.1', 8000)` with `s.listen(1)` caused `is_port_in_use(8000)` to return `True`.
  - Calling `run.find_free_port(host="127.0.0.1", start_port=8000, max_port=8080)` successfully detected the collision on 8000 and returned `8001`.
- **Multi-Port Collision (8000..8005 -> 8006)**:
  - Binding sockets across all 6 ports 8000..8005 with `s.listen(1)` caused `find_free_port(host="127.0.0.1", start_port=8000, max_port=8080)` to skip 8000, 8001, 8002, 8003, 8004, 8005 and jump to `8006`.
- **API Signature & Function Naming Finding**:
  - `run.py` defines `find_free_port`, not `find_available_port` (`hasattr(run, "find_available_port") == False`).
  - Positional call `run.find_free_port(8000)` passes `host=8000` (integer), raising `TypeError: str, bytes or bytearray expected, not int`. Keyword call `run.find_free_port(start_port=8000)` or `run.find_free_port("127.0.0.1", 8000)` functions correctly. Inside `run.py:102`, launcher invokes `find_free_port(args.host, start_port=chosen_port + 1, max_port=8080)` properly.

### 1.2 End-to-End Full Pipeline (Official Sample)
- Post official sample message to `/api/parse`:
  ```
  HỌ TÊN : HOÀNG ĐẮC PHÚ
  NGÀY: 24/10
  CA : Ca ngày 
  DỰ ÁN : sdv 
  THỜI GIAN LÀM VIỆC :8h-17h ( 8H)
  CÓ ĂN Ở XƯỞNG KO : 0
  ```
- **Response**: HTTP 200, 1 record parsed. `employee_name: "HOÀNG ĐẮC PHÚ"`, `date_str: "24/10"`, `hours.hcn_100: 8.0`, `meal_count: 0`. Status is `WARNING` due to expected year inference message: `"Năm được tự động suy luận là 2026"`.
- **Export**: POST to `/api/export-excel` -> HTTP 200, returns token `export_<uuid>`, `cells_written: 2`, `employees_matched: 1`.
- **Download**: GET `/api/download/{token}` -> HTTP 200, returns binary `.xlsx` stream (`Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`).
- **Excel Inspection with `openpyxl(data_only=False)`**:
  - `ws["K24"].value == 8` (Verified: HCN 100% written to row 24, column 11 K).
  - `ws["K30"].value == 0` (Verified: Suất ăn written to row 30, column 11 K).
  - `ws["AK24"].value == '=SUM(F24:AJ24)'` (Verified: native formula preserved).
  - `ws["AR24"].value == '=SUM(AK24:AP24)'` (Verified: total formula preserved).
  - `wb.calculation.fullCalcOnLoad == True` (Verified: auto-recalculation enabled).

### 1.3 Table Inline-Edit Payload Tolerance
- **Simulated UI Hour Edit (8 -> 10)**:
  - Sent modified record with `hours.hcn_100 = 10.0` to `/api/export-excel` -> downloaded Excel -> `ws["K24"].value == 10` and `ws["K30"].value == 0`.
- **Flat Payload Tolerance**:
  - Sent record with flat keys `{"employee_name": "HOÀNG ĐẮC PHÚ", "date_str": "24/10", "hcn_100": 10.0, "meal_count": 0}` -> `_coerce_to_attendance_record` coerced fields seamlessly -> `ws["K24"].value == 10`.
- **Meal Count Edit (0 -> 1)**:
  - Sent `meal_count = 1` -> `ws["K30"].value == 1`.
- **Date Shift Edit (24/10 -> 25/10)**:
  - Sent `date_str = "25/10"` -> written to column 12 (L): `ws["L24"].value == 8`, `ws["L30"].value == 0`.
- **Decimal Precision**:
  - Sent `hcn_100 = 7.5` -> written as float: `ws["K24"].value == 7.5`.
- **Fuzzy Match Tolerance**:
  - Sent unaccented lowercase name `"hoang dac phu"` -> fuzzy matcher identified row 24 -> `ws["K24"].value == 8`.

### 1.4 Adversarial & Security Tests
- Invalid download token (`/api/download/nonexistent_token`) returned HTTP 404.
- Empty export payload (`records: []`) returned HTTP 400.
- Malformed non-dict items returned HTTP 400/422.
- Unmatched employee names and out-of-range dates handled gracefully without 500 crashes (reported in `summary.errors`).
- Directory traversal payload in `output_filename` (`../../../evil.xlsx`) had slashes stripped and generated inside `output/` safely.

---

## 2. Logic Chain

1. **Launcher Port Collision Resilience**:
   - `run.py` utilizes a two-tier probing strategy: first `is_port_in_use(p)` with TCP connection test, followed by an explicit `socket.bind()` test inside `find_free_port()`.
   - In both single-port (8000) and multi-port (8000..8005) collision tests, the loop accurately advanced to the first unblocked port (8001 and 8006 respectively).
   - Therefore, the launcher safely avoids crashing on startup when default ports are occupied.

2. **Full Pipeline Integrity (Official Sample)**:
   - The official sample text is received by `/api/parse`, tokenized and parsed into `AttendanceRecord(employee_name='HOÀNG ĐẮC PHÚ', date_str='24/10', hours=WorkHours(hcn_100=8.0), meal_count=0)`.
   - Upon submitting to `/api/export-excel`, the server delegates to `ExcelIntegrator`, matching "HOÀNG ĐẮC PHÚ" to row 24 and "24/10" to column K (11).
   - Row offset 0 is HCN 100% -> cell K24 receives numeric `8`.
   - Row offset 6 is Suất ăn -> cell K30 receives numeric `0`.
   - Formulas in columns AK..AR are untouched, styles and headers remain pristine, and `fullCalcOnLoad` is configured for Excel recalculation.
   - Therefore, R1, R2, and R3 requirements for the standard pipeline are verified.

3. **Inline Edit Payload Tolerance**:
   - The backend `_coerce_to_attendance_record()` accommodates both nested Pydantic schemas (`hours: {...}`) and flat property dictionaries (`hcn_100: ...`).
   - Changing hours from 8 to 10 immediately propagated to Excel cell K24 as value 10 without data loss or corruption.
   - Modifying meals, dates, decimal numbers, and lowercase names all mapped accurately to their respective row and column coordinates.
   - Therefore, the UI-backend data exchange is tolerant of manual edits and varied payload shapes.

---

## 3. Caveats

1. **Launcher Function Naming & Positional Arguments**:
   - The launcher function is named `find_free_port`, not `find_available_port`.
   - The signature is `find_free_port(host="127.0.0.1", start_port=8000, max_port=8080)`. Calling `find_free_port(8000)` passes `host=8000`. Callers must use keyword `start_port=8000` or provide host first. Adding an alias `find_available_port(port=8000, host="127.0.0.1")` in `run.py` would improve developer ergonomics.
2. **Filename Sanitization**:
   - `/api/export-excel` sanitizes filenames via `re.sub(r'[^a-zA-Z0-9_\-\. ]', '_', raw_fname)`. This strips directory slashes (`/` and `\`) ensuring files stay in `output/`, but leaves literal `..` intact (e.g. `.._.._evil.xlsx`). Adding a check to replace `..` is recommended for defense-in-depth.
3. **Automated Browser Headless Testing**:
   - Web UI testing was performed via API endpoints and DOM event inspection in `app.js`. Full browser rendering was not driven through WebDriver/Playwright, but REST contract and payload processing were thoroughly validated.

---

## 4. Conclusion

**Verdict: APPROVE**

- Launcher port collision handling correctly identifies busy ports and jumps to free ports (8000 -> 8001, 8000..8005 -> 8006).
- End-to-end full pipeline from official sample message to downloaded Excel satisfies all acceptance criteria: K24=8, K30=0, formula preservation in columns AK/AR, and `fullCalcOnLoad=True`.
- Table inline-edit tolerance successfully absorbs user modifications (hours 8->10, meal count, date shifts, decimals, fuzzy name matching) and accurately updates Excel cells.
- All 18 tests in `stress_test_launcher_e2e.py` and all 268 tests in the project suite pass 100%.

---

## 5. Verification Method

To independently reproduce and verify this assessment:

1. **Run the Challenger M3-2 empirical stress test harness**:
   ```bash
   .venv/bin/python3 .agents/teamwork/challenger_m3_2/stress_test_launcher_e2e.py
   ```
   *Expected output*: `Ran 18 tests in ~8.4s -> OK`.

2. **Run the full project test suite**:
   ```bash
   .venv/bin/pytest
   ```
   *Expected output*: `268 passed in < 1.0s`.

3. **Inspect the test script**:
   - File: `.agents/teamwork/challenger_m3_2/stress_test_launcher_e2e.py`
   - Covers: Port collision (Group A), E2E pipeline & openpyxl cell assertions (Group B), Inline edit modifications (Group C), Adversarial & Sunday rules (Group D).
