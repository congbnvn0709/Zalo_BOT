# Handoff Report: Milestone 2 (Excel Integrator Engine & Template Generator)

**Worker ID**: `worker_m2_excel`  
**Milestone**: Milestone 2 (`core/template_generator.py`, `core/excel_integrator.py`, `templates_excel/BẢNG CHẤM CÔNG WEVN - ETS.xlsx`, `tests/test_excel.py`)  
**Parent Agent**: `9d3ef6c5-77d3-42b3-adab-c1e95bee7211`  
**Timestamp**: 2026-10-26T08:57:30Z  

---

## 1. Observation

### Directly Observed Code and System Artifacts:
1. **Source Ground Truth**:
   - `/Users/congcm/CODE/Vibe_Code/Zalo_BOT/sample_data.csv` specifies a 44-column timesheet matrix with 31 calendar dates from `2026-10-19` (Column 6 / F) to `2026-11-18` (Column 36 / AJ) and 4 employee blocks (rows 3..9, 10..16, 17..23, 24..30).
   - In `sample_data.csv`, Row 25 corresponds to `HOÀNG ĐẮC PHÚ` (STT 10), and column 11 (K) corresponds to `2026-10-24`.
2. **Formula Syntax**:
   - Per employee row $R \in [3, 10, 17, 24]$:
     * `AK{R}` = `=SUM(F{R}:AJ{R})`
     * `AL{R}` = `=SUM(F{R+1}:AJ{R+1})`
     * `AM{R}` = `=SUM(F{R+2}:AJ{R+2})`
     * `AN{R}` = `=SUM(F{R+3}:AJ{R+3})`
     * `AO{R}` = `=SUM(F{R+4}:AJ{R+4})`
     * `AP{R}` = `=SUM(F{R+5}:AJ{R+5})`
     * `AQ{R}` = `=SUM(F{R+6}:AJ{R+6})`
     * `AR{R}` = `=SUM(AK{R}:AP{R})` (strictly excluding `AQ` meals).
   - Row 2 summary totals:
     * Columns 37..44: `=SUM({col_letter}3,{col_letter}10,{col_letter}17,{col_letter}24)`.
3. **Execution Results**:
   - Running `.venv/bin/python3 core/template_generator.py` generated `templates_excel/BẢNG CHẤM CÔNG WEVN - ETS.xlsx` with 44 columns, 30 rows, 21 merged cell ranges, freeze panes at F3, and `fullCalcOnLoad = True`.
   - Running `.venv/bin/pytest tests/test_excel.py -v`:
     ```
     ============================== 41 passed in 0.52s ==============================
     ```
   - Running `.venv/bin/pytest tests/`:
     ```
     ============================= 247 passed in 0.63s ==============================
     ```
   - Running `.venv/bin/python3 tests/verify_e2e.py`:
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
     >>> OVERALL VERIFICATION: SUCCESSFUL (ALL CRITERIA MET) <<<
     ```

---

## 2. Logic Chain

1. **Template Generation Design**:
   - Based on observation 1 & 2, `core/template_generator.py` reads `sample_data.csv`, converts values into typed cells, structures employee blocks into 7 contiguous rows with merged metadata columns A..D and header rows 1..2, injects live Excel formulas in AK..AQ, sets column AR to `=SUM(AK{R}:AP{R})`, populates row 2 with formula totals across all employee rows, styles headers with Navy `#1F4E78` and soft blue `#D9E1F2`, highlights Sunday columns with peach `#FCE4D6` / `#FFF9E6`, applies thin borders and medium block separators, freezes panes at F3, sets `wb.calculation.fullCalcOnLoad = True`, and exports `templates_excel/BẢNG CHẤM CÔNG WEVN - ETS.xlsx`.
2. **Excel Integrator Engine**:
   - `core/excel_integrator.py` provides `ExcelIntegrator(template_path=None)` which:
     * Enforces `data_only=False` loading so formulas are preserved verbatim.
     * Implements a 3-tier matcher for employee names: Tier 1 exact normalized NFC (score 1.0), Tier 2 unaccented diacritic-stripped (score 0.95), Tier 3 fuzzy `difflib.SequenceMatcher` >= 0.85. Unmatched returns `(None, "", 0.0)`.
     * Implements multi-format date resolution supporting ISO `YYYY-MM-DD`, `DD/MM`, `DD-MM`, `DD/MM/YYYY`, day integer `24`, and `datetime.date` objects.
     * Coordinates mapped into 7 row offsets (0: HCN, 1: TCN, 2: HCĐ, 3: TCĐ, 4: Ngày CN, 5: Đêm CN, 6: Suất ăn).
     * Enforces strict numeric types (`int` or `float`, `data_type='n'`), preventing text coercion issues with Excel `=SUM(...)`.
     * Guarantees `wb.calculation.fullCalcOnLoad = True` on save to trigger formula tree recalculation upon opening.
     * Provides `get_template_info()` returning `{sheet_name: str, employees: list[str], date_range: list[str]}`.
3. **Acceptance Criteria Verification**:
   - For `HOÀNG ĐẮC PHÚ` on `24/10` with shift `Ca ngày 8h-17h (8H)` and `CÓ ĂN Ở XƯỞNG KO : 0`:
     * Matched start row is 24 ($R_{\text{start}}=24$).
     * Matched date column is 11 (Column K).
     * Value 8 is written to `K24` as numeric integer (`data_type='n'`).
     * Value 0 is written to `K30` ($24 + 6 = 30$) as numeric integer (`data_type='n'`).
     * Cell `AK24` retains formula `=SUM(F24:AJ24)` verbatim.
     * Cell `AR24` retains formula `=SUM(AK24:AP24)` verbatim.
     * Cell `AK2` retains formula `=SUM(AK3,AK10,AK17,AK24)` verbatim.
     * Fully verified by `test_02_acceptance_criteria_hoang_dac_phu_24_10` in `tests/test_excel.py`.

---

## 3. Caveats

- **External Template Upload**: `ExcelIntegrator` dynamically indexes employee start rows and date columns from any valid template following the 7-row block structure. If a custom uploaded template has fewer or more employees, row 2 formulas in that custom template should match the employee rows in that file.
- **Ambiguous Day Numbers**: In `sample_data.csv`, date range covers Oct 19 to Nov 18; all day numbers from 1 to 31 are unique across this window. For templates spanning multiple full calendar months where day numbers repeat, input dates should include the month (e.g. `24/10` or `2026-10-24`).
- No other caveats.

---

## 4. Conclusion

Milestone 2 is complete, fully implemented, and strictly verified:
1. `core/template_generator.py`: Generates authentic 44-column timesheet template with live Excel formulas, merged metadata, styling, and freeze panes.
2. `templates_excel/BẢNG CHẤM CÔNG WEVN - ETS.xlsx`: Master template successfully generated and verified.
3. `core/excel_integrator.py`: Implements `ExcelIntegrator` with 3-tier matcher, date resolution, numeric cell writing across 7 offsets, formula preservation, and full calculation on load.
4. `tests/test_excel.py`: 41 unit and integration test cases covering all requirements, passing 100%.
5. Existing codebase integrity: `models/attendance.py`, `core/parser.py`, and existing tests remained completely untouched and passing (247/247 in `pytest tests/`, 126/126 in `tests/verify_e2e.py`).

---

## 5. Verification Method

Independent reproduction commands:

```bash
# 1. Run unit test suite for Excel Integrator & Template Generator
.venv/bin/pytest tests/test_excel.py -v

# 2. Run full pytest suite across entire project
.venv/bin/pytest tests/

# 3. Run stand-alone E2E verification runner
.venv/bin/python3 tests/verify_e2e.py

# 4. Verify template generator standalone execution
.venv/bin/python3 core/template_generator.py

# 5. Direct python verification of Acceptance Criteria
.venv/bin/python3 -c "
import io, openpyxl
from core.excel_integrator import ExcelIntegrator
from core.parser import parse_single_message

msg = '''HỌ TÊN : HOÀNG ĐẮC PHÚ
NGÀY: 24/10
CA : Ca ngày 
DỰ ÁN : sdv 
THỜI GIAN LÀM VIỆC :8h-17h ( 8H)
CÓ ĂN Ở XƯỞNG KO : 0'''

rec = parse_single_message(msg)
buf = io.BytesIO()
integrator = ExcelIntegrator()
stats = integrator.apply_records([rec], output_path=buf)
ws = openpyxl.load_workbook(buf, data_only=False).active

assert ws['K24'].value == 8 and ws['K24'].data_type == 'n'
assert ws['K30'].value == 0 and ws['K30'].data_type == 'n'
assert ws['AK24'].value == '=SUM(F24:AJ24)'
assert ws['AR24'].value == '=SUM(AK24:AP24)'
print('ACCEPTANCE CRITERIA VERIFIED!')
"
```
