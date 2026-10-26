## 2026-10-26T08:46:20Z
You are the Excel Integrator Worker for Milestone 2.
Your working directory is: /Users/congcm/CODE/Vibe_Code/Zalo_BOT/.agents/teamwork/worker_m2_excel/

MANDATORY FIRST STEPS:
1. Read /Users/congcm/CODE/Vibe_Code/Zalo_BOT/.agents/teamwork/ORIGINAL_REQUEST.md.
2. Read /Users/congcm/CODE/Vibe_Code/Zalo_BOT/PROJECT.md and /Users/congcm/CODE/Vibe_Code/Zalo_BOT/TEST_INFRA.md.
3. Review the Excel survey report: /Users/congcm/CODE/Vibe_Code/Zalo_BOT/.agents/teamwork/survey_spec_miner_excel/report.md and inspect /Users/congcm/CODE/Vibe_Code/Zalo_BOT/sample_data.csv.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Task: Implement Milestone 2 (Excel Integrator Engine & Template Generator):
Write ownership:
- You exclusively own:
  * core/template_generator.py
  * core/excel_integrator.py
  * templates_excel/BẢNG CHẤM CÔNG WEVN - ETS.xlsx
  * tests/test_excel.py
- DO NOT modify models/attendance.py, core/parser.py, or existing test files.

Key Technical Requirements:
1. core/template_generator.py:
   - Generate default templates_excel/BẢNG CHẤM CÔNG WEVN - ETS.xlsx from sample_data.csv.
   - Replicate the exact 44-column structure (A..AR) and 7-row repeating blocks per employee under header rows 1 and 2.
   - Inject authentic Excel formulas:
     * AK{R} = =SUM(F{R}:AJ{R})
     * AL{R} = =SUM(F{R+1}:AJ{R+1})
     * AM{R} = =SUM(F{R+2}:AJ{R+2})
     * AN{R} = =SUM(F{R+3}:AJ{R+3})
     * AO{R} = =SUM(F{R+4}:AJ{R+4})
     * AP{R} = =SUM(F{R+5}:AJ{R+5})
     * AQ{R} = =SUM(F{R+6}:AJ{R+6})
     * AR{R} = =SUM(AK{R}:AP{R}) (strictly excluding AQ meals).
     * Row 2 summary totals across all employees.
   - Preserve borders, font styles, colors, and column widths.
   - Run generator to create templates_excel/BẢNG CHẤM CÔNG WEVN - ETS.xlsx.
2. core/excel_integrator.py:
   - Class ExcelIntegrator(template_path=None):
     * Loads workbook with data_only=False to preserve formula syntax.
     * match_employee(name: str) -> tuple[int, str, float]: 3-tier matcher (NFC normalized exact -> unaccented -> difflib ratio >= 0.85).
     * resolve_date_column(date_str: str) -> int: maps ISO dates (2026-10-24), DD/MM (24/10), DD-MM, DD/MM/YYYY, or day number 24 to 1-based column index.
     * apply_records(records: list[AttendanceRecord], output_path: str = None) -> dict:
       - Locates target employee row block and date column.
       - Maps WorkHours to 7 row offsets (0: HCN, 1: TCN, 2: HCĐ, 3: TCĐ, 4: Ngày CN, 5: Đêm CN, 6: Suất ăn).
       - Writes values strictly as numeric types (int or float), NOT strings '8'.
       - Sets wb.calculation.fullCalcOnLoad = True on workbook before saving.
       - Saves workbook to output/ directory or output_path.
       - Returns summary stats: records_processed, cells_written, employees_matched, unmatched_records.
     * get_template_info() -> dict: returns active sheet name, employee list, and date range.
3. Unit test suite in tests/test_excel.py:
   - Comprehensive test suite covering:
     * Template generator functionality, formulas, headers, styles.
     * Employee matching (exact, accents, typos, lowercase, extra spaces, unmatched).
     * Date column resolution across formats.
     * Cell coordinate mapping and numeric typing (data_type == 'n').
     * Formula preservation in AK..AR and row 2.
     * Official Acceptance Criteria test case: HOÀNG ĐẮC PHÚ on 24/10 -> K24=8, K30=0, AK24==SUM(F24:AJ24), AR24==SUM(AK24:AP24).
4. Verification:
   - Run .venv/bin/pytest tests/test_excel.py -v.
   - Run .venv/bin/pytest tests/ (all tests passing).
   - Run .venv/bin/python3 tests/verify_e2e.py.
   - Deliver handoff report to: /Users/congcm/CODE/Vibe_Code/Zalo_BOT/.agents/teamwork/worker_m2_excel/handoff.md and send message to parent.
