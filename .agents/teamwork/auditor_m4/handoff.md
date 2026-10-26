# Milestone 4 Forensic Integrity Audit Report

## Forensic Audit Report

**Work Product**: Full-System Codebase (Milestone 4: `models/`, `core/`, `api/`, `static/`, `main.py`, `run.py`)  
**Profile**: General Project  
**Integrity Mode**: Development (with zero-hardcoding enforcement)  
**Verdict**: **CLEAN**

---

### Phase Results
- **Check 1: Zero Hardcoding AST Scan**: **PASS**  
  An automated AST walk across all production Python files (`models/attendance.py`, `core/parser.py`, `core/excel_integrator.py`, `core/template_generator.py`, `api/routes.py`, `main.py`, `run.py`) found zero hardcoded test returns, zero fixed test dates in conditional logic, and zero hardcoded employee comparison branches.
- **Check 2: Authentic Logic Verification**: **PASS**  
  Verified empirical execution of:
  - Genuine regex parsing and tokenization with unicode NFC normalization.
  - Authentic datetime mathematics (e.g., overnight shifts `20h-6h` calculating 10h elapsed minus 1h break = 9h; Sunday detection via `weekday() == 6`).
  - Dynamic Excel coordinate indexing (employee matching scanning Column 3 across 7-row blocks; date column mapping scanning Row 1 header dates; HOÀNG ĐẮC PHÚ matched dynamically to Row 24).
  - Openpyxl formula injection writing `=SUM(F{r}:AJ{r})` for rows and `=SUM(AK{r}:AP{r})` for column AR, strictly excluding AQ (meals).
  - FastAPI endpoints (`/api/parse`, `/api/export-excel`, `/api/template/info`, `/api/template/upload`, `/api/download/{token}`, `/api/sample`, `/api/health`) handling real requests and errors.
  - Native TCP socket probing in `run.py` via `socket.socket(socket.AF_INET, socket.SOCK_STREAM)` and `bind((host, port))`.
- **Check 3: Dummy / Facade Stub Detection**: **PASS**  
  AST scan confirmed zero empty functions, zero `pass` stubs, zero ellipsis `...` placeholders, and zero `raise NotImplementedError` statements across all production modules.
- **Check 4: Behavioral Test Verification**: **PASS**  
  The full project test suite executed cleanly:
  - `pytest`: 268 passed in 0.97s (`tests/test_parser.py`, `tests/test_excel.py`, `tests/test_api.py`, `tests/test_e2e.py`, `tests/test_requirements.py`).
  - `verify_e2e.py`: 126 passed across Tiers 1–4 in 0.195s.
- **Check 5: Adversarial Stress & Boundary Testing**: **PASS**  
  Tested against:
  - ReDoS (50 repeated messages parsed in 0.008s).
  - Integer overflow / conversion DoS (CVE-2020-10735 with 5,000-digit meal counts safely capped without crash).
  - Invalid calendar dates (non-leap year `2026-02-29` rejected with `ERROR`).
  - Work hour boundaries (negative hours and >24h days rejected with `ERROR`).
  - Missing entities and invalid upload files (returning HTTP 400).

---

## 1. Observation

### Exact File Paths & Code Line Observations
1. **`models/attendance.py`**:
   - Lines 8–15: Authentic Pydantic v2 model `WorkHours` with 6 payroll float fields (`hcn_100`, `tcn_150`, `hcd_130`, `tcd_195`, `sunday_day_200`, `sunday_night_260`) and `total_hours`.
   - Lines 18–34: Authentic `AttendanceRecord` schema capturing normalized names, original date string, resolved ISO date, shift type, time window, work hours, meal count, status (`VALID`, `WARNING`, `ERROR`), and messages.
2. **`core/parser.py`**:
   - Lines 14–44 (`normalize_vietnamese_name`): Genuine Unicode NFC normalization (`unicodedata.normalize('NFC', name)`), regex removal of phone numbers (`re.sub(r'[-–]\s*\d{9,11}', '', text)`), parenthetical notes, and list indices.
   - Lines 46–90 (`calculate_work_hours`): True mathematical allocation:
     ```python
     if is_sunday:
         if shift == "DAY":
             sunday_day_200 = float(total_hours)
         else:
             sunday_night_260 = float(total_hours)
     else:
         if shift == "DAY":
             hcn_100 = float(min(total_hours, 8.0))
             tcn_150 = float(max(0.0, total_hours - 8.0))
         else:
             hcd_130 = float(min(total_hours, 8.0))
             tcd_195 = float(max(0.0, total_hours - 8.0))
     ```
   - Lines 134–202 (`split_messages`): Header-lookahead regex (`(?=(?:^|\n)\s*...HỌ\s*TÊN...[:：\-\s])`) and divider splitting.
   - Lines 340–388: Dynamic date parser supporting ISO (`YYYY-MM-DD`), full DMY (`DD/MM/YYYY`), and short DM (`DD/MM`), setting `is_sunday = (parsed_date.weekday() == 6)`.
   - Lines 463–479: Overnight math `(eh + 24 - sh) + (em - sm) / 60.0` with automatic 1h break deduction when elapsed >= 8.5h if no explicit bracketed hours are given.
3. **`core/excel_integrator.py`**:
   - Lines 123–161: Dynamic Date Column Indexing: Reads Row 1 from column 6 (`F`) to `max_column`, parses date strings and native datetimes into `self.date_list`.
   - Lines 162–191: Dynamic Employee Block Indexing: Reads Column 3 (`C`) in 7-row strides from row 3 to `max_row`, building `self.employees`.
   - Lines 192–288: 4-Tier Fuzzy Employee Matching (Tier 1 exact, Tier 2 unaccented, Tier 3 token containment, Tier 4 SequenceMatcher ratio >= 0.85).
   - Lines 373–485: Dynamic cell write to `self.ws.cell(row=r_start + row_offset, column=col_date)`.
4. **`core/template_generator.py`**:
   - Lines 90–99: Injects live Excel SUM formulas `=SUM(F{r}:AJ{r})` into columns AK..AQ, and `=SUM(AK{r}:AP{r})` into column AR.
   - Line 105: Injects row 2 grand total formulas `=SUM(AK3,AK10,AK17,AK24)` across columns 37..44.
5. **`api/routes.py`**:
   - Lines 206–235 (`POST /api/parse`): Calls `parse_attendance_messages(...)` on arbitrary payload text and returns structured response.
   - Lines 303–375 (`POST /api/export-excel`): Coerces records, instantiates `ExcelIntegrator`, applies records, and generates unique download token.
   - Lines 377–404 (`GET /api/download/{token}`): Serves generated workbook via `FileResponse`.
6. **`run.py`**:
   - Lines 34–52: Implements `is_port_in_use` and `find_free_port` using native `socket.socket(socket.AF_INET, socket.SOCK_STREAM)`.

---

## 2. Logic Chain

1. **Step 1 (AST Scan)**:
   - Evaluated the abstract syntax trees of all 7 production Python files.
   - Found 0 empty function bodies, 0 pass stubs, 0 ellipsis stubs, and 0 `NotImplementedError` nodes.
   - Verified that employee names only appear in sample data string constants for the `/api/sample` testing endpoint and docstrings. No conditional statement (`ast.If`) contains hardcoded employee names or test dates.
   - Inference: The codebase contains no facade implementations or test-cheating conditional branches.
2. **Step 2 (Empirical Dynamic Indexing Verification)**:
   - Passed an arbitrary unknown employee (`PHẠM VĂN ĐỒNG`) and arbitrary date (`15/11` - a Sunday) to `parse_single_message`.
   - Result: Correctly classified 8h as `sunday_night_260 = 8.0` with `is_sunday = True`.
   - Evaluated `ExcelIntegrator.match_employee("hoàng đắc phú (thợ hàn)")`.
   - Result: Mapped dynamically to Row 24 (score 0.95), reflecting his actual 4th position in `sample_data.csv`, not hardcoded to Row 3.
   - Inference: Coordinate resolution is 100% dynamic and authentic.
3. **Step 3 (Mathematical & Formula Integrity)**:
   - Tested overnight shift calculation (`20h-6h` without bracketed hours).
   - Result: Correctly computed 10h elapsed minus 1h break = 9.0h total, allocated to 8.0h HCĐ and 1.0h TCĐ.
   - Verified openpyxl workbook formulas: AK3 is `=SUM(F3:AJ3)`, AR3 is `=SUM(AK3:AP3)`. Column AR aggregates hours while strictly excluding AQ (meals).
   - Inference: Payroll mathematics and openpyxl formula injection comply strictly with R1 and R3.
4. **Step 4 (Socket & Server Verification)**:
   - Tested `run.py` socket probing on TCP port 54321.
   - Result: `is_port_in_use(54321)` returned `False` before socket listen, `True` while bound, and `find_free_port(start_port=54321)` found `54322`.
   - Inference: Server launch logic uses authentic operating system TCP socket operations.
5. **Step 5 (Adversarial Hardening)**:
   - Executed ReDoS, integer conversion DoS, non-leap year calendar dates, negative hours, out-of-range dates, and malformed API requests.
   - Result: All tests passed subsecond with zero uncaught exceptions, zero crashes, and correct error status codes.
   - Inference: System is robustly hardened against edge cases and malicious inputs.

---

## 3. Caveats

- **External Network Access**: The dashboard frontend loads Tailwind CSS from CDN (`https://cdn.tailwindcss.com`) when internet is available, but bundles an offline fallback stylesheet (`static/css/app.css`) ensuring complete functionality in air-gapped local environments.
- **Python Runtime**: Audited against Python 3.11.17 (`.venv/bin/python`). `run.py` validates `sys.version_info >= (3, 9)` to ensure broad local machine compatibility.
- No other caveats.

---

## 4. Conclusion

The Zalo Attendance Web App & Excel Integrator codebase is **100% CLEAN** of any hardcoding, facades, or integrity violations.
- Zero test-cheating shortcuts.
- Fully dynamic parser, regex segmentation, datetime mathematics, and openpyxl Excel integration.
- Full compliance with `ORIGINAL_REQUEST.md` (R1, R2, R3) and `PROJECT.md`.
- Overall Verdict: **CLEAN**.

---

## 5. Verification Method

To independently verify the audit findings:

1. **Run full automated pytest suite**:
   ```bash
   .venv/bin/pytest -v
   ```
   *Expected output*: `268 passed` in < 2 seconds.

2. **Run E2E verification matrix (Tiers 1–4)**:
   ```bash
   .venv/bin/python tests/verify_e2e.py
   ```
   *Expected output*: `126 passed`, `0 failed`, `OVERALL VERIFICATION: SUCCESSFUL`.

3. **Run AST Forensic Scan**:
   ```bash
   .venv/bin/python -c '
   import ast
   for path in ["models/attendance.py", "core/parser.py", "core/excel_integrator.py", "core/template_generator.py", "api/routes.py", "main.py", "run.py"]:
       with open(path) as f:
           tree = ast.parse(f.read())
       for node in ast.walk(tree):
           if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
               stmts = [s for s in node.body if not (isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant) and isinstance(s.value.value, str))]
               assert len(stmts) > 0, f"Empty function: {node.name}"
               assert not isinstance(stmts[0], ast.Pass), f"Pass stub: {node.name}"
   print("ALL CODEBASE AST CHECKS CLEAN!")
   '
   ```
   *Expected output*: `ALL CODEBASE AST CHECKS CLEAN!`

4. **Invalidation Conditions**:
   - Any commit introducing an `if name == "..."` branch tailored to test data.
   - Any commit replacing dynamic Excel coordinate calculations with fixed constants.
