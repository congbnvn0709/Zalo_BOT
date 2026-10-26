# Adversarial Challenge Report — Milestone 4 (Core Hardening)

**Verdict**: **REJECT**  
**Agent**: Tier 5 Adversarial Challenger 1 (Core) (`challenger_m4_1`)  
**Target Modules**: `core/parser.py`, `models/attendance.py`, `core/excel_integrator.py`, `core/template_generator.py`  
**Date**: 2026-10-26T09:58:00Z  

---

## Challenge Summary

**Overall risk assessment**: **HIGH**

An adversarial stress test harness (`.agents/teamwork/challenger_m4_1/stress_test_core.py`) consisting of 22 test suites was constructed and executed against `core/parser.py`, `models/attendance.py`, `core/excel_integrator.py`, and `core/template_generator.py`. The suite rigorously probed all four mandated challenge dimensions:
1. Vietnamese accent variations (Hòa vs Hoà, Thủy vs Thuỷ, diphthong/triphthong tone placements, case variations, precomposed NFC vs decomposed NFD Unicode).
2. Extreme dates (leap year Feb 29 in leap and non-leap years, month boundaries 31/10, 30/11, 28/02, 31/11, 30/02, 31/04, invalid numbers 32/10, 24/13, 00/10, 10/00).
3. Extreme hours (0.25h, 0.5h, 15.5h, 23.75h, 24.0h, upper limit >24h, lower limit <=0h, cross-midnight transitions like 20h-5h, 22h-6h, clock hour violations 25h-8h, Sunday rates).
4. Excel formulas (all 7 rows per employee block consistency, Column AR meal exclusion oracle, Row 2 grand total evaluation, multi-employee scaling up to 300 employees).

**Verdict Rationale**:
While the codebase demonstrated remarkable resilience with **0 unhandled crashes/exceptions** across all tests, it **fails the mandatory requirement of 100% correctness** on decomposed (NFD) Vietnamese Unicode text. In addition, an architectural boundary vulnerability was surfaced in Row 2 grand total formulas when scaling beyond 255 employees.

---

## 1. Observation

### Obs 1: Decomposed (NFD) Unicode Messages Fail Parsing Completely (0% Correctness)
- **Location**: `core/parser.py:140-158`, `core/parser.py:245-250`, `core/parser.py:264-324`, `core/parser.py:396-397`
- **Root Cause**: `AttendanceParser.split_messages()` (line 143) and `AttendanceParser.parse_single()` (line 210) do not normalize input strings to Unicode Normalization Form C (`NFC`) upon entry. In `core/parser.py:24`, `unicodedata.normalize('NFC', name)` is only called inside `normalize_vietnamese_name()`, which runs *after* fields have already been extracted via regex.
- **Mechanism**: The regex patterns throughout `AttendanceParser` use precomposed NFC Vietnamese glyphs (e.g., `HỌ` = `U+0048 U+1ECC`, `TÊN` = `U+0054 U+00CA U+004E`, `NGÀY` = `U+004E U+0047 U+00C0 U+0059`, `ngày` = `U+006E U+0067 U+00E0 U+0079`). When input text is encoded in Decomposed NFD form (standard output from macOS/iOS clipboards and certain Vietnamese IMEs such as UniKey/EVKey composite mode), `HỌ` is encoded as `H` (`U+0048`) + `O` (`U+004F`) + combining dot below (`U+0323`). Consequently, all header regexes fail to match.
- **Empirical Execution**:
  ```bash
  .venv/bin/python .agents/teamwork/challenger_m4_1/stress_test_core.py
  ```
- **Verbatim Test Failure**:
  ```
  FAIL: test_06_decomposed_nfd_message_parsing_correctness (__main__.TestVietnameseAccentVariations.test_06_decomposed_nfd_message_parsing_correctness)
  Adversarial Test: Decomposed NFD Unicode message parsing.
  ----------------------------------------------------------------------
  Traceback (most recent call last):
    File "/Users/congcm/CODE/Vibe_Code/Zalo_BOT/.agents/teamwork/challenger_m4_1/stress_test_core.py", line 167, in test_06_decomposed_nfd_message_parsing_correctness
      self.assertTrue(is_correct, f"NFD parsing failed: {rec.status} - {rec.messages}")
  AssertionError: False is not true : NFD parsing failed: ERROR - ['Thiếu trường Họ và tên', 'Thiếu trường Ngày chấm công', 'Thiếu trường Thời gian làm việc', 'Thiếu trường Ca làm việc', 'Không nhận diện được ca: "Ca ngày"', 'Thiếu thông tin suất ăn, mặc định 0']
  ```
- **Resulting Record**:
  ```python
  status: 'ERROR'
  employee_name: ''
  resolved_date: ''
  hours.total_hours: 0.0
  messages: ['Thiếu trường Họ và tên', 'Thiếu trường Ngày chấm công', 'Thiếu trường Thời gian làm việc', 'Thiếu trường Ca làm việc', 'Không nhận diện được ca: "Ca ngày"', 'Thiếu thông tin suất ăn, mặc định 0']
  ```

---

### Obs 2: Row 2 Excel Grand Total Exceeds Excel Function Argument Limit (255 args) at Scale
- **Location**: `core/template_generator.py:102-106`
- **Code**:
  ```python
  # Row 2 Grand Totals across all employees
  for col in range(37, 45):
      col_letter = get_column_letter(col)
      terms = [f"{col_letter}{r}" for r in employee_start_rows]
      formula = f"=SUM({','.join(terms)})"
      ws.cell(row=2, column=col, value=formula)
  ```
- **Direct Finding**:
  In Excel formula specifications, a single function call supports a maximum of 255 arguments. For a roster exceeding 255 employees (e.g., 300 employees), `terms` produces 300 comma-separated arguments: `=SUM(AK3,AK10,AK17,...,AK2096)`. When opened in Microsoft Excel, this formula is flagged as corrupted or yields `#VALUE!` / formula error.
- **Harness Output**:
  ```
  [BOUNDARY VULNERABILITY FOUND] At 300 employees, Row 2 SUM formula has 300 arguments, exceeding Excel's 255 argument limit! Formula: =SUM(AK3,AK10,AK17,AK24,AK31,AK38,AK45,A... (total 1947 chars)
  ```

---

### Obs 3: Diphthong/Triphthong Accent Placement and Casing (Passes 100%)
- **Harness Tests**: `test_01_hoa_diphthong_variants_matching`, `test_02_thuy_diphthong_variants_matching`, `test_03_other_diphthongs_triphthongs`, `test_04_casing_variations_in_parser_and_matcher`
- **Observation**:
  - `Hòa` (new orthography: U+00F2 U+0061) vs `Hoà` (old orthography: U+006F U+00E0): Both decompose under `strip_accents()` to `"Nguyen Van Hoa"`.
  - `Thủy` (U+1EE7 U+0079) vs `Thuỷ` (U+0075 U+1EF7): Both decompose under `strip_accents()` to `"Le Thi Thuy"`.
  - In `core/excel_integrator.py`, `match_employee()` successfully matches `Hòa` and `Hoà` via Tier 2A unaccented match (`score=0.95`).
  - Casing variations (`HOÀNG ĐẮC PHÚ`, `hoàng đắc phú`, `Hoàng Đắc Phú`, `HoÀnG ĐắC pHú`) are all normalized correctly to uppercase `HOÀNG ĐẮC PHÚ` and match at Tier 1 (`score=1.0`).

---

### Obs 4: Extreme Date & Calendar Boundary Handling (Passes 100%, 0 Crashes)
- **Harness Tests**: `test_01_leap_year_feb29`, `test_02_month_boundaries_valid_and_invalid`, `test_03_invalid_month_and_day_numbers`, `test_04_excel_date_column_resolution_bounds`
- **Observation**:
  - `29/02/2024` and `2024-02-29` (leap year) successfully resolve to `2024-02-29` (`day_number=29`, `status=VALID`).
  - `29/02/2026` and `29/02` (non-leap year) cleanly raise handled `ValueError`, producing `status=ERROR` and message `'Ngày không hợp lệ: 29/02'`. 0 crashes.
  - Month boundary dates `31/10` (Oct 31, 31 days) and `30/11` (Nov 30, 30 days) parse correctly.
  - Invalid calendar dates `31/11` (Nov 31), `30/02`, `31/04`, `31/06`, `31/09` cleanly fail validation with `status=ERROR`. 0 crashes.
  - Invalid numbers `32/10`, `24/13`, `00/10`, `10/00`, `99/99`, and negative dates are safely rejected with `status=ERROR`. 0 crashes.
  - `ExcelIntegrator.resolve_date_column()` correctly maps `2026-10-19` to column 6 (F), `2026-10-31` to column 18, `2026-11-01` to column 19, and `2026-11-18` to column 36 (AJ). Out-of-bounds dates (`2026-10-18`, `2026-11-19`, `32/10`, `None`) safely return `None` and log errors without crashing.

---

### Obs 5: Extreme Hours & Shift Allocation (Passes 100%, 0 Crashes)
- **Harness Tests**: `test_01_fractional_extreme_hours` through `test_06_sunday_rates_day_and_night`
- **Observation**:
  - Fractional hours `0.25h` (15 mins), `0.5h` (30 mins), `15.5h`, `23.75h`, `24.0h` allocate precisely:
    - `0.25h`: `hcn_100 = 0.25`, `tcn_150 = 0.0`.
    - `15.5h`: `hcn_100 = 8.0`, `tcn_150 = 7.5`.
    - `23.75h`: `hcn_100 = 8.0`, `tcn_150 = 15.75`.
    - `24.0h`: `hcn_100 = 8.0`, `tcn_150 = 16.0`.
  - Upper limits exceeding 24h (`24.25h`, `24.5h`, `25h`, `48h`, `8h-10h (26h)`) are rejected with `status=ERROR` and message `'Tổng số giờ làm (...) vượt quá 24h/ngày'`. 0 crashes.
  - Non-positive hours (`0h`, `0.0h`, `-5h`, `8h - -2h`) are rejected with `status=ERROR`. 0 crashes.
  - Cross-midnight transitions:
    - `20h-5h` (Ca đêm): `elapsed = 9.0h` -> automated 1h break deduction -> `total_hours = 8.0h`, `hcd_130 = 8.0`.
    - `20h-8h (11H)`: `elapsed = 12.0h`, bracketed takes precedence -> `total_hours = 11.0h`, `hcd_130 = 8.0`, `tcd_195 = 3.0`.
    - `22h-6h`: `elapsed = 8.0h` (< 8.5h threshold, no deduction) -> `total_hours = 8.0h`.
    - `20h15-5h45 (8.5h)`: `total_hours = 8.5h`, `hcd_130 = 8.0`, `tcd_195 = 0.5`.
  - Clock hour syntax errors (`25h-8h`, `8h-17h75`, `24h15-8h`) are rejected with `status=ERROR`. 0 crashes.
  - Sunday rates: `2026-10-25` correctly detected as Sunday; day shift allocates to `sunday_day_200`, night shift allocates to `sunday_night_260`.

---

### Obs 6: Excel 7-Row Formula Consistency & Cell Numeric Typing (Passes 100%)
- **Harness Tests**: `test_01_all_7_rows_formula_syntax_and_offsets` through `test_04_mathematical_evaluation_consistency_oracle`
- **Observation**:
  - For all employee blocks starting at row `r`:
    - Offset 0: `AK{r} = =SUM(F{r}:AJ{r})` (HCN 100%)
    - Offset 1: `AL{r} = =SUM(F{r+1}:AJ{r+1})` (TCN 150%)
    - Offset 2: `AM{r} = =SUM(F{r+2}:AJ{r+2})` (HCĐ 130%)
    - Offset 3: `AN{r} = =SUM(F{r+3}:AJ{r+3})` (TCĐ 195%)
    - Offset 4: `AO{r} = =SUM(F{r+4}:AJ{r+4})` (Ngày CN 200%)
    - Offset 5: `AP{r} = =SUM(F{r+5}:AJ{r+5})` (Đêm CN 260%)
    - Offset 6: `AQ{r} = =SUM(F{r+6}:AJ{r+6})` (Suất ăn)
    - Total: `AR{r} = =SUM(AK{r}:AP{r})`
  - Formula `AR{r}` strictly sums `AK{r}:AP{r}` and mathematically excludes `AQ{r}` (meals).
  - Writing via `ExcelIntegrator.apply_records()` populates numeric integers/floats without overwriting formula cells or header rows. `wb.calculation.fullCalcOnLoad` is set to `True`.

---

## 2. Logic Chain

1. **Criterion Verification**: The dispatch mandates: *"Assert 0 crashes and 100% correctness. Identify and challenge any unreached branches, boundary limits, or edge cases: 1. Vietnamese accent variations (Hòa vs Hoà, Thủy vs Thuỷ, tone marks over diphthongs/triphthongs, uppercase/lowercase, decomposed vs precomposed Unicode)..."*
2. **Crash Assertion**: Throughout all 22 stress tests (including fuzzing, corrupt data, negative inputs, and out-of-bound dates/hours), zero uncaught exceptions occurred. The system successfully achieved 0 crashes.
3. **Correctness Assertion**: When presented with valid attendance messages encoded in Decomposed NFD Unicode (a common encoding for Vietnamese text on Apple devices and IME clipboards), `core/parser.py` fails to recognize any of the fields (`HỌ TÊN`, `NGÀY`, `CA LÀM VIỆC`, `THỜI GIAN LÀM VIỆC`, `CÓ ĂN Ở XƯỞNG KO`). The parser returns a record with status `ERROR`, empty name, empty date, and 0 hours.
4. **Impact**: Legitimate Zalo messages pasted from macOS/iOS or typed with composite Unicode fail to parse, producing false rejection errors for valid user submissions.
5. **Boundary Scalability**: `core/template_generator.py` constructs Row 2 formulas by enumerating every employee cell (`=SUM(AK3,AK10,AK17,...)`). At >255 employees, this violates Microsoft Excel's hard limit of 255 function arguments.
6. **Verdict**: Because 100% correctness is required across all specified edge cases (specifically including decomposed Unicode), and NFD messages completely fail to parse, the verdict must be **REJECT**.

---

## 3. Caveats

- Testing was performed on Python 3.11 with `openpyxl==3.1.5` and `pydantic==2.10.6`.
- For rosters under 255 employees, the Excel formula structure functions correctly and conforms to all specifications.
- If input text is normalized to NFC before passing to `core/parser.py`, all 22 test suites pass with 100% correctness.

---

## 4. Conclusion

**Verdict: REJECT**

The core modules (`core/parser.py`, `models/attendance.py`, `core/excel_integrator.py`) are robust, crash-resistant, and mathematically accurate across extreme dates, extreme hours, and Excel formula generation. However, **rejection is required** because:
1. `core/parser.py` fails to parse Decomposed NFD Unicode messages due to the omission of top-level `unicodedata.normalize('NFC', ...)` in `AttendanceParser.split_messages` and `AttendanceParser.parse_single`.
2. `core/template_generator.py` uses individual comma-separated cell references in Row 2 grand totals, which exceeds Excel's 255-argument limit when rosters exceed 255 employees.

### Required Remediations for Worker:

1. **In `core/parser.py`**:
   - In `split_messages(self, text: str)`:
     ```python
     if not text or not isinstance(text, str) or not text.strip():
         return []
     text = unicodedata.normalize('NFC', text) # <-- Add NFC normalization
     cleaned_text = text.replace('\r\n', '\n').replace('\r', '\n').strip()
     ```
   - In `parse_single(self, raw_message: str)`:
     ```python
     if not raw_message or not isinstance(raw_message, str) or not raw_message.strip():
         ...
     raw_message = unicodedata.normalize('NFC', raw_message) # <-- Add NFC normalization
     ```

2. **In `core/template_generator.py`**:
   - In Row 2 grand totals (line 101-106):
     When `len(employee_start_rows) > 255`, chunk the terms into groups of <= 250 (e.g. `=SUM(SUM(chunk1), SUM(chunk2))`) or use an Excel array formula/range to avoid exceeding the 255-argument function limit.

---

## 5. Verification Method

To independently verify these findings:

1. **Run the Adversarial Stress Test Suite**:
   ```bash
   cd /Users/congcm/CODE/Vibe_Code/Zalo_BOT
   .venv/bin/python .agents/teamwork/challenger_m4_1/stress_test_core.py
   ```
   *Expected result*: 21 passed, 1 failure (`test_06_decomposed_nfd_message_parsing_correctness`), with boundary vulnerability notice printed for 300 employees.

2. **Run Python One-Liner to Reproduce NFD Defect**:
   ```bash
   .venv/bin/python -c "
   import unicodedata
   from core.parser import parse_single_message
   msg = 'HỌ TÊN : HOÀNG ĐẮC PHÚ\nNGÀY: 24/10\nCA : Ca ngày\nTHỜI GIAN LÀM VIỆC :8h-17h ( 8H)\nCÓ ĂN Ở XƯỞNG KO : 0'
   nfd_msg = unicodedata.normalize('NFD', msg)
   rec = parse_single_message(nfd_msg)
   print('Status:', rec.status)
   print('Employee:', rec.employee_name)
   print('Messages:', rec.messages)
   assert rec.status == 'ERROR', 'Should fail due to NFD'
   "
   ```

3. **Condition to Invalidate Rejection**:
   Adding `unicodedata.normalize('NFC', ...)` at entry to `split_messages()` and `parse_single()` in `core/parser.py` will cause `stress_test_core.py` to achieve 100% pass (22/22 tests passing).
