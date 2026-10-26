# Handoff Report: Milestone 2 Excel Code Review & Adversarial Stress Test

- **Reviewer**: Excel Code Reviewer 1 (`reviewer_m2_1`)
- **Roles**: Reviewer, Adversarial Critic
- **Date**: 2026-10-26T09:06:00Z
- **Target Artifacts**:
  - `core/template_generator.py`
  - `core/excel_integrator.py`
  - `templates_excel/BẢNG CHẤM CÔNG WEVN - ETS.xlsx`
  - `tests/test_excel.py`
- **Verdict**: **APPROVE**

---

## 1. Observation

### 1.1 Direct Inspection of Implementation Files
1. **`core/template_generator.py`**:
   - Lines 47-50 & 247: Creates openpyxl workbook and explicitly sets `wb.calculation.fullCalcOnLoad = True`.
   - Lines 53-83: Reads `sample_data.csv` dynamically, parses 44 columns, skips static formula totals in cols 37..44, and coerces integer/float numbers.
   - Lines 90-99: Injects authentic horizontal `=SUM(...)` formulas per employee block:
     * `AK{r}` = `=SUM(F{r}:AJ{r})` (HCN 100%)
     * `AL{r}` = `=SUM(F{r+1}:AJ{r+1})` (TCN 150%)
     * `AM{r}` = `=SUM(F{r+2}:AJ{r+2})` (HCĐ 130%)
     * `AN{r}` = `=SUM(F{r+3}:AJ{r+3})` (TCĐ 195%)
     * `AO{r}` = `=SUM(F{r+4}:AJ{r+4})` (Ngày CN 200%)
     * `AP{r}` = `=SUM(F{r+5}:AJ{r+5})` (Đêm CN 260%)
     * `AQ{r}` = `=SUM(F{r+6}:AJ{r+6})` (Suất ăn)
     * `AR{r}` = `=SUM(AK{r}:AP{r})` (TỔNG CÔNG strictly excluding AQ meals).
   - Lines 102-106: Populates row 2 grand totals for columns 37..44: `=SUM({col_letter}3,{col_letter}10,{col_letter}17,{col_letter}24)`.
   - Lines 110-122: Configures 21 merged cell ranges for header metadata and employee blocks A..D.
   - Lines 124-222: Establishes visual hierarchy with Navy `#1F4E78`, soft blue `#D9E1F2`, peach `#FCE4D6` / `#FFF9E6` for Sundays, and standard/medium borders.
   - Line 246: Sets freeze panes to `F3`.

2. **`core/excel_integrator.py`**:
   - Lines 68-87: Loads workbook using `openpyxl.load_workbook(..., data_only=False)`, preserving all formula definitions verbatim. Sets `wb.calculation.fullCalcOnLoad = True`.
   - Lines 99-136: Dynamically indexes date columns from Row 1, converting ISO, DD/MM/YYYY, or datetime objects into a structured date registry.
   - Lines 138-165: Discovers employee blocks every 7 rows starting at row 3 in column 3 (C), recording exact NFC, lowercase, and unaccented representations.
   - Lines 166-205: Implements 3-tier employee matching:
     * Tier 1: Case-insensitive normalized NFC match (`score = 1.0`).
     * Tier 2: Diacritic/accent-stripped unaccented match (`score = 0.95`).
     * Tier 3: Difflib SequenceMatcher similarity ratio >= 0.85.
     * Returns `(None, "", 0.0)` for unknown employees.
   - Lines 212-289: Multi-format date resolution supporting ISO `YYYY-MM-DD`, `DD/MM`, `DD-MM`, `DD/MM/YYYY`, day integer `24`, and datetime objects.
   - Lines 290-402: `apply_records` writes numeric hours to 7 row offsets (0: HCN, 1: TCN, 2: HCĐ, 3: TCĐ, 4: Ngày CN, 5: Đêm CN, 6: Suất ăn):
     * Helper `_write_num` guarantees strict `int` or `float` type assignment (`data_type='n'`), preventing string coercion.
     * Meal count writes `int(rec.meal_count)` even when value is 0.
     * Re-applies `wb.calculation.fullCalcOnLoad = True` before saving.
     * Non-destructive: leaves formulas in AK..AR and row 2 completely untouched.

3. **`templates_excel/BẢNG CHẤM CÔNG WEVN - ETS.xlsx`**:
   - Direct OpenXML zip package inspection confirms:
     * `calcPr`: `[{'calcId': '124519', 'fullCalcOnLoad': '1'}]` in `xl/workbook.xml`.
     * Grid size: 30 rows x 44 columns.
     * Worksheet title: `"CHẤM CÔNG WEVN - ETS"`.
     * Freeze panes: `"F3"`.
     * Verified cell formulas:
       + `AK24` = `=SUM(F24:AJ24)`
       + `AR24` = `=SUM(AK24:AP24)`
       + `AK2`  = `=SUM(AK3,AK10,AK17,AK24)`
       + `AR2`  = `=SUM(AR3,AR10,AR17,AR24)`

4. **Official Acceptance Criteria Test Case (AC4 & AC5)**:
   - Input message:
     ```
     HỌ TÊN : HOÀNG ĐẮC PHÚ
     NGÀY: 24/10
     CA : Ca ngày 
     DỰ ÁN : sdv 
     THỜI GIAN LÀM VIỆC :8h-17h ( 8H)
     CÓ ĂN Ở XƯỞNG KO : 0
     ```
   - Parsed record: `employee_name="HOÀNG ĐẮC PHÚ"`, `date_str="24/10"`, `hcn_100=8.0`, `meal_count=0`.
   - Integrator execution:
     * Before write: `K24 = None`, `K30 = None`.
     * After write: `K24 = 8` (`type=<class 'int'>`, `data_type='n'`).
     * After write: `K30 = 0` (`type=<class 'int'>`, `data_type='n'`).
     * Formula in `AK24`: `=SUM(F24:AJ24)` intact.
     * Formula in `AR24`: `=SUM(AK24:AP24)` intact.
     * Formula in `AK2`: `=SUM(AK3,AK10,AK17,AK24)` intact.
     * Formula in `AR2`: `=SUM(AR3,AR10,AR17,AR24)` intact.

### 1.2 Independent Test Execution
1. `.venv/bin/pytest tests/test_excel.py -v`:
   - Result: 41 passed in 0.50s (100% pass rate).
2. `.venv/bin/pytest tests/`:
   - Result: 247 passed in 0.59s (100% pass rate across entire project).
3. `.venv/bin/python3 tests/verify_e2e.py`:
   - Result: 126 passed, 0 failed, 0 errors in 0.193s. All AC1..AC8 criteria marked `[ PASS ]`.

---

## 2. Logic Chain

1. **Integrity & Authenticity**:
   - Observation 1.1 shows that neither `core/template_generator.py` nor `core/excel_integrator.py` contain hardcoded test branches or fake outputs.
   - All employee matching is driven dynamically by `self.employees` scanned from the active worksheet.
   - All date resolution is driven dynamically by `self.date_list` parsed from Row 1 headers.
   - Therefore, there are NO integrity violations or dummy facades.

2. **Acceptance Criteria AC4 & AC5 Conformance**:
   - Observation 1.1 & 1.4 prove that `HOÀNG ĐẮC PHÚ` is resolved to row 24 and `24/10` to column 11 (K).
   - Offset 0 maps to row 24 (`K24`), where integer 8 is written.
   - Offset 6 maps to row 30 (`K30`), where integer 0 is written.
   - Both cells are typed as numeric integers (`data_type='n'`), satisfying AC4.
   - Horizontal formulas in `AK24..AQ24` calculate `=SUM(F{r}:AJ{r})` and `AR24` calculates `=SUM(AK24:AP24)` (excluding meals), satisfying AC5.
   - Vertical formulas in row 2 calculate `=SUM({col}3,{col}10,{col}17,{col}24)`, satisfying AC5.

3. **Formatting & Structure Conformance**:
   - Observation 1.1 confirms `data_only=False` is used during openpyxl workbook load, preventing formula syntax loss.
   - Observation 1.1 & 1.3 verify `fullCalcOnLoad = True` is set on both generator and integrator, ensuring Excel automatically recalculates the formula tree upon user opening.
   - Numeric typing (`int`/`float`) prevents text representation issues in Excel calculations.

---

## 3. Adversarial Review & Stress Test Results

### 3.1 Challenge Summary
- **Overall risk assessment**: LOW
- **Integrity Violation Check**: PASSED (No hardcoded responses, no facades, no bypasses).

### 3.2 Stress Tests Performed
1. **Stress Scenario 1: Multi-employee batch writing across mixed shifts & Sundays**:
   - Scenario: Writing records simultaneously for multiple employees on weekday regular, night shift overtime, and Sunday daytime shifts.
   - Result: Correctly mapped to designated row offsets (offsets 0, 1, 2, 3, 4, 5, 6). Formula simulation confirms AK..AR and row 2 evaluate to exact sums.
   - Status: PASS.

2. **Stress Scenario 2: Zero meal count vs None meal count**:
   - Scenario: Meal count explicitly specified as 0 (`CÓ ĂN Ở XƯỞNG KO : 0`) vs missing.
   - Result: Explicit 0 writes numeric `0` to row offset 6; missing leaves cell intact.
   - Status: PASS.

3. **Stress Scenario 3: Date column uniqueness**:
   - Scenario: Checking if day numbers 1..31 collide across the 31-day period from `2026-10-19` to `2026-11-18`.
   - Result: Days 19..31 in Oct and days 1..18 in Nov are mutually disjoint. All 31 day numbers are unique in this template.
   - Status: PASS.

4. **Stress Scenario 4: Non-matching employee names**:
   - Scenario: Inputting non-target names like `"NGUYỄN VĂN A"`.
   - Result: SequenceMatcher similarity ratios remain <= 0.59 (below 0.85 threshold). Returned `(None, "", 0.0)`.
   - Status: PASS.

5. **Stress Scenario 5: Repeated writes / Reload safety**:
   - Scenario: Calling `reload()` after dirty in-memory edits.
   - Result: Discards dirty memory cells and restores clean template state.
   - Status: PASS.

---

## 4. Caveats & Design Observations

1. **Cell Overwrite Behavior**:
   - If multiple messages for the exact same employee, shift category, and date are processed in sequence, `apply_records` writes the latest value to the cell rather than summing them. In the standard Zalo workflow, messages represent full shift summaries (e.g., `8h-17h`), so overwriting is appropriate.
2. **Template Employee Count Dependency**:
   - The default template defines 4 employee blocks (rows 3, 10, 17, 24). If an external custom template is uploaded with a different number of employees, row 2 grand total formulas in that custom template must correspond to the employee rows of that custom file.

---

## 5. Conclusion

**Verdict: APPROVE**

The Milestone 2 Excel Integrator Engine and Template Generator meet all acceptance criteria, functional requirements, architectural standards, and test benchmarks without regressions or integrity violations. The implementation is ready for Milestone 3 (Interactive Web Dashboard and REST API integration).

---

## 6. Verification Method

To independently reproduce and verify this review verdict:

```bash
# 1. Run Excel Integrator unit test suite (41 tests)
.venv/bin/pytest tests/test_excel.py -v

# 2. Run complete project test suite (247 tests)
.venv/bin/pytest tests/

# 3. Run standalone E2E requirement verification (126 tests)
.venv/bin/python3 tests/verify_e2e.py

# 4. Verify OpenXML calcPr attribute in template
.venv/bin/python3 -c "
import zipfile, xml.etree.ElementTree as ET
with zipfile.ZipFile('templates_excel/BẢNG CHẤM CÔNG WEVN - ETS.xlsx') as z:
    root = ET.parse(z.open('xl/workbook.xml')).getroot()
    print('calcPr:', [e.attrib for e in root.iter() if e.tag.endswith('calcPr')])
"

# 5. Direct verification of official acceptance criteria (HOÀNG ĐẮC PHÚ on 24/10)
.venv/bin/python3 -c "
import io, openpyxl
from core.excel_integrator import ExcelIntegrator
from core.parser import parse_single_message

rec = parse_single_message('''HỌ TÊN : HOÀNG ĐẮC PHÚ
NGÀY: 24/10
CA : Ca ngày 
DỰ ÁN : sdv 
THỜI GIAN LÀM VIỆC :8h-17h ( 8H)
CÓ ĂN Ở XƯỞNG KO : 0''')

buf = io.BytesIO()
ExcelIntegrator().apply_records([rec], output_path=buf)
ws = openpyxl.load_workbook(buf, data_only=False).active

assert ws['K24'].value == 8 and ws['K24'].data_type == 'n'
assert ws['K30'].value == 0 and ws['K30'].data_type == 'n'
assert ws['AK24'].value == '=SUM(F24:AJ24)'
assert ws['AR24'].value == '=SUM(AK24:AP24)'
assert ws['AK2'].value == '=SUM(AK3,AK10,AK17,AK24)'
assert ws['AR2'].value == '=SUM(AR3,AR10,AR17,AR24)'
print('VERIFICATION PASSED!')
"
```
