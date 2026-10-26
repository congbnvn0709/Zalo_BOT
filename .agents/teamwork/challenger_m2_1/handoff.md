# Adversarial Challenge Report — Milestone 2 (Excel Integrator & Template Generator)

**Verdict**: **APPROVE**  
**Agent**: Excel Challenger 1 (`challenger_m2_1`)  
**Target Modules**: `core/excel_integrator.py`, `core/template_generator.py`, `templates_excel/BẢNG CHẤM CÔNG WEVN - ETS.xlsx`  
**Date**: 2026-10-26T09:08:00Z  

---

## Challenge Summary

**Overall risk assessment**: **LOW**

An adversarial stress test harness (`.agents/teamwork/challenger_m2_1/stress_test_excel.py`) containing 11 rigorous test suites was executed against `core/excel_integrator.py` and `core/template_generator.py`. The suite subjected the Excel integration engine to multi-cycle write degradation, boundary column stress, off-by-one boundary validation, mathematical formula regex and AST oracles, cell numeric typing audits, styling/merging preservation checks, and 30-cycle randomized fuzzing.

All 11 challenge test cases passed cleanly with 0 failures, confirming that:
1. Excel formulas in columns AK..AR and Row 2 grand totals are strictly preserved as live formula strings (`=SUM(...)`) with `cell.data_type == 'f'` across multiple sequential, overwrite, in-memory, and randomized fuzz write cycles.
2. Boundary dates at Column F (col 6, 2026-10-19) and Column AJ (col 36, 2026-11-18) write to the exact target coordinates without touching or corrupting neighboring Columns E (col 5) or AK (col 37).
3. Column AR formulas across all employee blocks strictly compute `=SUM(AK{r}:AP{r})`, aggregating only the 6 work hours categories and mathematically excluding Column AQ (meals).
4. All written cell values are strictly numeric (`cell.data_type == 'n'`), whether whole hours (`int`), fractional hours (`float`), or meals (`int`).

---

## 1. Observation

Direct empirical observations recorded during adversarial harness execution:

### Obs 1: Multi-Cycle Formula Preservation (10 Sequential Cycles & 30-Cycle Fuzz)
- **Harness Test**: `test_challenge_01_multiple_write_cycles_10_iterations`, `test_challenge_09_thirty_cycle_fuzz_stress`
- **Command**: `.venv/bin/python .agents/teamwork/challenger_m2_1/stress_test_excel.py -v`
- **Output**:
  ```
  test_challenge_01_multiple_write_cycles_10_iterations ... ok
  test_challenge_09_thirty_cycle_fuzz_stress ... ok
  ```
- **Direct Finding**: After 10 consecutive write-save-reload cycles across different employees and dates, and after 30 cumulative randomized fuzz write cycles:
  * In Row 2, grand total cells AK2..AR2 retained their formula strings `=SUM(AK3,AK10,AK17,AK24)` through `=SUM(AR3,AR10,AR17,AR24)` verbatim. `cell.data_type` remained `'f'` across 100% of inspections.
  * In rows 3, 10, 17, 24, all employee formula cells AK..AR retained their formula strings `=SUM(F{row}:AJ{row})` and `=SUM(AK{row}:AP{row})` verbatim with `cell.data_type == 'f'`.
  * No formula was replaced by a static cached float or integer.
  * `wb.calculation.fullCalcOnLoad` remained `True` across all saved files.

### Obs 2: Boundary Date Column Resolution & Isolation (Col F and Col AJ)
- **Harness Test**: `test_challenge_03_first_boundary_date_col_f`, `test_challenge_04_last_boundary_date_col_aj`, `test_challenge_05_off_by_one_boundary_dates_rejected`
- **Direct Finding**:
  * First boundary date (2026-10-19 / 19/10 / 19): `resolve_date_column` returns 6 (Column F). Applying a record writes strictly to column 6 (e.g. F24=8, F30=1). Column E (col 5 - "CÔNG") was compared before and after writing for rows 1..30; 0 differences were found (`col_e_before == col_e_after`).
  * Last boundary date (2026-11-18 / 18/11 / 18): `resolve_date_column` returns 36 (Column AJ). Applying a record writes strictly to column 36 (e.g. AJ24=8, AJ30=0). Column AK (col 37 - `=SUM(F{r}:AJ{r})`) was compared before and after writing for rows 1..30; 0 differences were found (`col_ak_before == col_ak_after`).
  * Off-by-one dates: 2026-10-18 (one day before start) and 2026-11-19 (one day after end) return `None`. Attempting to write records with out-of-bounds dates generates a clear error message in `res["errors"]` (`Date out of range: 18/10 for HOÀNG ĐẮC PHÚ`) and writes 0 cells without crashing.

### Obs 3: Column AR Formula Excludes AQ (Meals)
- **Harness Test**: `test_challenge_06_col_ar_formula_strictly_excludes_aq`, `test_challenge_10_formula_mathematical_oracle`
- **Location**: `core/template_generator.py:99`
- **Source Code Verification**:
  ```python
  ws.cell(row=r, column=44, value=f"=SUM(AK{r}:AP{r})")
  ```
- **Direct Finding**:
  * For all employee rows `r ∈ {3, 10, 17, 24}`, `cell.value` at column 44 (AR) is strictly `=SUM(AK{r}:AP{r})`.
  * Column 43 (AQ) corresponds to "Suất ăn" (meals). The range `AK:AP` encompasses:
    - AK: HCN 100%
    - AL: TCN 150%
    - AM: HCĐ 130%
    - AN: TCĐ 195%
    - AO: Ngày CN 200%
    - AP: Đêm CN 260%
  * AQ is strictly excluded from the summation range. Formula strings were tested for regex match `r"^=SUM\(AK\d+:AP\d+\)$"` and absence of substring `"AQ"`; both conditions passed with 100% compliance.
  * In Row 2, column 44 (AR2) computes `=SUM(AR3,AR10,AR17,AR24)`, correctly rolling up only total work hours.

### Obs 4: Cell Numeric Data Type Conformance (`cell.data_type == 'n'`)
- **Harness Test**: `test_challenge_07_numeric_data_types_comprehensive`
- **Location**: `core/excel_integrator.py:348-350`, `368-370`
- **Source Code Verification**:
  ```python
  num_val = int(val) if float(val).is_integer() else float(val)
  cell = self.ws.cell(row=r_start + row_offset, column=col_date)
  cell.value = num_val
  ...
  cell_meal = self.ws.cell(row=r_start + 6, column=col_date)
  cell_meal.value = int(rec.meal_count)
  ```
- **Direct Finding**:
  * Whole hours (e.g., 8.0, 3.0) -> written as `int`, `cell.data_type == 'n'`.
  * Fractional hours (e.g., 0.5, 1.75, 2.5, 3.5, 4.25) -> written as `float`, `cell.data_type == 'n'`.
  * Meal counts 0, 1, 2 -> written as `int`, `cell.data_type == 'n'`.
  * Openpyxl underlying XML generates `<c r="..." t="n"><v>...</v></c>`. No values are written as strings (`t="s"`).

### Obs 5: Layout, Merges, Dimensions, and Formatting Survival
- **Harness Test**: `test_challenge_08_cell_styling_and_merges_preserved`
- **Direct Finding**:
  * Merged cell ranges `A1:A2`, `C1:C2`, `A24:A30`, `C24:C30`, etc. remain identical before and after writes (`orig_merges == mod_merges`).
  * Freeze pane setting (`ws.freeze_panes == "F3"`) survives without alteration.
  * Column widths (cols 1..44) and row heights (rows 1..30) remain identical before and after writes.
  * Header fill color hexes (Navy `1F4E78`, `2F5597`, `162D4A`) and font names (`Segoe UI`) remain intact.

---

## 2. Logic Chain

1. **Premise 1 (Formula Preservation)**: `ExcelIntegrator` loads workbooks strictly via `openpyxl.load_workbook(path, data_only=False)`. Openpyxl preserves XML `<f>` elements and exposes them as string formula representations prefixed with `=`. Because `apply_records` only targets columns resolved from `date_list` (which is restricted to columns 6..36 in `_index_sheet`), columns 37..44 (AK..AR) and row 2 are never touched during write operations. Empirically, after 10 sequential write cycles and 30 randomized fuzz cycles, 100% of formula cells retain `=SUM(...)` syntax and `cell.data_type == 'f'`.
2. **Premise 2 (Boundary Safety)**: The template header row 1 indexes date columns starting at column 6 (F, "2026-10-19") and ending at column 36 (AJ, "2026-11-18"). Writing to column 6 operates exclusively at `column=6`, leaving column 5 (`CÔNG`) untouched. Writing to column 36 operates exclusively at `column=36`, leaving column 37 (`AK`) untouched. Off-by-one dates ("18/10", "19/11") fail `resolve_date_column` and are rejected with non-zero error logs without corrupting the sheet.
3. **Premise 3 (AR Formula Integrity)**: Requirement R3 mandates that total work hours exclude meals. `core/template_generator.py` injects `=SUM(AK{r}:AP{r})` into Column AR (col 44). Column AQ (col 43) represents meal count. Mathematically and syntactically, `AK:AP` spans exactly columns 37 to 42, which excludes column 43. The AST/regex oracle confirmed no occurrence of `AQ` in AR cells across any row.
4. **Premise 4 (Numeric Type Conformance)**: Excel numerical formula calculations (`=SUM`) require cell values to have numerical types. In `apply_records`, values are converted via `int(val) if float(val).is_integer() else float(val)` and `int(rec.meal_count)`. When openpyxl assigns Python `int` or `float` to `cell.value`, it automatically assigns `data_type = 'n'`. All 7 row offsets for all employee blocks were inspected, and all exhibited `data_type == 'n'`.
5. **Conclusion**: The implementation satisfies all Excel integrity requirements R3, F06, F07, and F08 with zero formula corruption, zero type mismatch, and robust boundary containment.

---

## 3. Caveats

- **External Excel Viewer Recalculation**: Openpyxl does not compute formula values itself (it does not contain a full spreadsheet calculation engine). It preserves formula text and sets `wb.calculation.fullCalcOnLoad = True`. When opened in Microsoft Excel, LibreOffice Calc, or Google Sheets, the application recalculates the live values upon opening.
- **Concurrent File Access**: If multiple processes attempt to write to the same physical `.xlsx` file simultaneously without locking, file contention could occur. However, the system architecture operates as a local web application where exports are written to unique timestamped files or downloaded via in-memory streaming (`io.BytesIO`).

---

## 4. Conclusion

**VERDICT: APPROVE**

The Excel Integrator (`core/excel_integrator.py`) and Template Generator (`core/template_generator.py`) fully satisfy all empirical challenge criteria:
- Formula preservation is 100% intact across up to 30 sequential and fuzz write cycles.
- Boundary columns F (6) and AJ (36) are strictly isolated from metadata and formula columns.
- Column AR strictly excludes Column AQ (meals) in both syntax and range.
- Cell data types are strictly numeric (`'n'`) for all hours and meals.
- Sheet formatting, styling, merged ranges, and freeze panes survive all write cycles intact.

---

## 5. Verification Method

To independently reproduce and verify this assessment:

1. **Run the Adversarial Stress Test Harness**:
   ```bash
   .venv/bin/python .agents/teamwork/challenger_m2_1/stress_test_excel.py -v
   ```
   *Expected Result*: 11 tests pass in ~2.5 seconds with `OK`.

2. **Run the Complete Workspace Test Suite**:
   ```bash
   .venv/bin/pytest -v .agents/teamwork/challenger_m2_1/stress_test_excel.py tests/
   ```
   *Expected Result*: 258 tests pass in ~3.0 seconds with `100% PASSED`.

3. **Inspect Generated Test Artifacts**:
   Inspect `.agents/teamwork/challenger_m2_1/stress_test_excel.py` lines 86-136 (`_verify_all_formulas_intact`), lines 138-232 (`test_challenge_01_multiple_write_cycles_10_iterations`), lines 330-360 (`test_challenge_06_col_ar_formula_strictly_excludes_aq`), and lines 362-450 (`test_challenge_07_numeric_data_types_comprehensive`).
