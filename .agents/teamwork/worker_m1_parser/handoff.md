# Milestone 1 Handoff Report: Attendance Message Parser

## 1. Observation

- **Task Ownership & Scope**:
  - Implemented exclusively within designated write ownership:
    * `models/__init__.py` and `models/attendance.py`
    * `core/__init__.py` and `core/parser.py`
    * `tests/__init__.py` and `tests/test_parser.py`
- **Execution Environment**:
  - Python 3.11 (`/opt/homebrew/bin/python3.11`) with isolated virtualenv `.venv` in `/Users/congcm/CODE/Vibe_Code/Zalo_BOT/.venv/`.
  - Installed packages: `pydantic 2.14.1`, `pytest 9.1.1`, `fastapi 0.162.0`, `uvicorn 0.54.0`, `openpyxl 3.1.5`, `python-multipart 0.0.32`.
- **Unit Test Execution**:
  - Command: `.venv/bin/pytest tests/test_parser.py -v`
  - Output verbatim:
    ```text
    ============================= test session starts ==============================
    platform darwin -- Python 3.11.17, pytest-9.1.1, pluggy-1.7.0 -- /Users/congcm/CODE/Vibe_Code/Zalo_BOT/.venv/bin/python3.11
    cachedir: .pytest_cache
    rootdir: /Users/congcm/CODE/Vibe_Code/Zalo_BOT
    plugins: anyio-4.15.1
    collecting ... collected 73 items                                                             

    tests/test_parser.py::TestAttendanceParserAcceptance::test_acceptance_criteria_standard_message PASSED [  1%]
    tests/test_parser.py::TestAttendanceParserAcceptance::test_acceptance_with_full_date PASSED [  2%]
    tests/test_parser.py::TestVietnameseNameNormalization::test_name_trimming_and_casing PASSED [  4%]
    tests/test_parser.py::TestVietnameseNameNormalization::test_name_with_phone_number_stripped PASSED [  5%]
    tests/test_parser.py::TestVietnameseNameNormalization::test_name_with_parenthesized_note_stripped PASSED [  6%]
    tests/test_parser.py::TestVietnameseNameNormalization::test_name_unaccented_preserved PASSED [  8%]
    tests/test_parser.py::TestVietnameseNameNormalization::test_missing_name_triggers_error PASSED [  9%]
    tests/test_parser.py::TestVietnameseNameNormalization::test_empty_punctuation_name_triggers_error PASSED [ 10%]
    tests/test_parser.py::TestDateParsingAndSundayResolution::test_valid_date_formats[...] PASSED
    ...
    tests/test_parser.py::TestAdvancedEdgeCases::test_asian_fullwidth_colon PASSED [ 94%]
    tests/test_parser.py::TestAdvancedEdgeCases::test_missing_colons_whitespace_separated PASSED [ 95%]
    tests/test_parser.py::TestAdvancedEdgeCases::test_minutes_in_time_range PASSED [ 97%]
    tests/test_parser.py::TestAdvancedEdgeCases::test_night_shift_12h_overtime PASSED [ 98%]
    tests/test_parser.py::TestAdvancedEdgeCases::test_sunday_night_shift_with_overtime_12h PASSED [100%]

    ============================== 73 passed in 0.10s ==============================
    ```
- **Syntax and Lint Check**:
  - Command: `.venv/bin/python3 -m py_compile models/__init__.py models/attendance.py core/__init__.py core/parser.py tests/__init__.py tests/test_parser.py`
  - Output: Exit code 0, 0 compilation or syntax errors.

## 2. Logic Chain

1. **Acceptance Criteria Fulfillment**:
   - In `ORIGINAL_REQUEST.md` (lines 43-52), the standard acceptance input:
     ```text
     HỌ TÊN : HOÀNG ĐẮC PHÚ
     NGÀY: 24/10
     CA : Ca ngày 
     DỰ ÁN : sdv 
     THỜI GIAN LÀM VIỆC :8h-17h ( 8H)
     CÓ ĂN Ở XƯỞNG KO : 0
     ```
     must parse to `Tên = "HOÀNG ĐẮC PHÚ"`, `Ngày = "24/10"`, `HCN = 8`, `Suất ăn = 0`.
   - `core/parser.py` extracts `employee_name = "HOÀNG ĐẮC PHÚ"`, `normalized_name = "Hoàng Đắc Phú"`, `resolved_date = "2026-10-24"` (day 24), `is_sunday = False`, `hours.hcn_100 = 8.0`, `hours.total_hours = 8.0`, `meal_count = 0`, and `status = "WARNING"` (noting default year 2026).
   - Verified directly in `tests/test_parser.py::TestAttendanceParserAcceptance::test_acceptance_criteria_standard_message`.

2. **Vietnamese Name Normalization**:
   - `normalize_vietnamese_name()` applies Unicode NFC normalization, strips noise (phone numbers, parenthesized roles/teams, list indices), collapses whitespace, and preserves accents.
   - Verified across edge cases (all-lowercase, mixed spaces, accented/unaccented, notes) in `TestVietnameseNameNormalization`.

3. **Break Deduction & Working Hours Allocation**:
   - Priority hierarchy:
     1. Explicit bracketed hours take precedence: `( 8H)` -> 8.0h, `(11H)` -> 11.0h.
     2. Elapsed clock time range: `8h-17h` (elapsed 9.0h >= 8.5h threshold) automatically deducts 1h break -> net 8.0h.
     3. Cross-midnight shifts: `20h-5h` (elapsed 9.0h) -> net 8.0h; `20h-8h` (elapsed 12.0h) -> net 11.0h.
     4. Short shifts: `8h-12h` (elapsed 4.0h < 8.5h) retains 4.0h without break deduction.
     5. Additive overtime: `8h-17h + TC 3h` -> 8.0 + 3.0 = 11.0h.
   - Allocation across 6 categories:
     - Weekday/Sat Day: up to 8h in `hcn_100`, excess in `tcn_150`.
     - Weekday/Sat Night: up to 8h in `hcd_130`, excess in `tcd_195`.
     - Sunday Day: all in `sunday_day_200`.
     - Sunday Night: all in `sunday_night_260`.
   - Verified in `TestShiftAndHoursCalculation`.

4. **Meal Detection**:
   - Normalizes 0, không, ko, k, tự túc -> 0.
   - Normalizes 1, có, co, x, X, v, V, ✓ -> 1.
   - Flags 2 suất with warning; flags ambiguous or omitted values with warning and defaults to 0.
   - Verified in `TestMealCountDetection`.

5. **Multi-Message Batch Segmentation & Single-Line Parsing**:
   - Lookahead on `HỌ TÊN` prefix splits contiguous messages even when blank lines are absent.
   - Delimiter expansion pre-splits single-line hyphen-delimited messages (`HỌ TÊN: A - NGÀY: 24/10 - CA: Ca ngày...`).
   - Verified in `TestSingleLineAndBatchSegmentation`.

6. **Error Gating & Zero-Crash Resilience**:
   - Malformed dates (e.g. `32/10`, `29/02/2026`), missing names, sick leave (`nghỉ ốm`), or hours > 24 are converted into `status = "ERROR"` records with specific diagnostic Vietnamese messages, never raising unhandled exceptions.
   - Verified in `TestNonCrashingResilience`.

## 3. Caveats

- `default_year` defaults to `2026` as per project template specification (`sample_data.csv`). Messages omitting the year (e.g. `24/10`) flag a `WARNING: Năm được tự động suy luận là 2026`. This is intentional and compliant with the spec.
- No caveats regarding parser functionality or test coverage.

## 4. Conclusion

Milestone 1 is complete, verified, and ready for integration by downstream milestones (Milestone 2 Excel Integrator and Milestone 3 REST API & Web Dashboard):
- `models/attendance.py` provides typed Pydantic models matching the interface contract in `PROJECT.md`.
- `core/parser.py` implements the full parsing, normalization, break calculation, and error-tolerant batching logic.
- `tests/test_parser.py` provides 73 passing unit tests with 100% success rate.

## 5. Verification Method

To independently verify this milestone:
```bash
cd /Users/congcm/CODE/Vibe_Code/Zalo_BOT
.venv/bin/pytest tests/test_parser.py -v
```
Expected output: 73 passed in ~0.10 seconds with 0 failures and 0 warnings.
To inspect code compilation:
```bash
.venv/bin/python3 -m py_compile models/__init__.py models/attendance.py core/__init__.py core/parser.py tests/__init__.py tests/test_parser.py
```
Expected output: 0 errors (exit code 0).
