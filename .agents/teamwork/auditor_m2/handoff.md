# Forensic Integrity Audit Handoff Report — Milestone 2

**Target Work Product**: `core/template_generator.py` and `core/excel_integrator.py`  
**Profile**: General Project  
**Integrity Mode**: Development Mode (as defined in `ORIGINAL_REQUEST.md`)  
**Verdict**: **CLEAN**

---

## 1. Observation

### Observation 1.1: Zero Hardcoding of Coordinates or Names
- Exact search across `core/excel_integrator.py` and `core/template_generator.py` for `"HOÀNG ĐẮC PHÚ"`, `"K24"`, `"K30"`, `"AK24"`, and `"AR24"` yielded **0 occurrences** in code logic.
- In `core/excel_integrator.py`, employee block indexing is dynamic (`lines 140-164`):
  ```python
  max_row = self.ws.max_row
  r = 3
  while r <= max_row:
      name_cell = self.ws.cell(row=r, column=3).value
      if name_cell is not None and str(name_cell).strip():
          # dynamically builds entry with row r
          self.employees.append(emp_entry)
          r += 7
      else:
          r += 1
  ```
- Date columns are dynamically scanned from Row 1 (`lines 100-136`):
  ```python
  for col_idx in range(6, max_col + 1):
      val = self.ws.cell(row=1, column=col_idx).value
      # parses ISO YYYY-MM-DD or DD/MM/YYYY into date_list entry with col=col_idx
  ```
- Cell targets are resolved at runtime as `row = r_start + row_offset` and `column = col_date` (`lines 346-370`). When `HOÀNG ĐẮC PHÚ` is found at row 24 and date `24/10` is resolved to column 11, coordinates `K24` (offset 0) and `K30` (offset 6) emerge purely as mathematical values `(24, 11)` and `(30, 11)`.

### Observation 1.2: Dynamic Formula Generation
- In `core/template_generator.py` (`lines 90-106`), formula strings are generated dynamically using row and column variables:
  ```python
  for r in employee_start_rows:
      ws.cell(row=r, column=37, value=f"=SUM(F{r}:AJ{r})")          # AK
      ws.cell(row=r, column=38, value=f"=SUM(F{r+1}:AJ{r+1})")      # AL
      ws.cell(row=r, column=39, value=f"=SUM(F{r+2}:AJ{r+2})")      # AM
      ws.cell(row=r, column=40, value=f"=SUM(F{r+3}:AJ{r+3})")      # AN
      ws.cell(row=r, column=41, value=f"=SUM(F{r+4}:AJ{r+4})")      # AO
      ws.cell(row=r, column=42, value=f"=SUM(F{r+5}:AJ{r+5})")      # AP
      ws.cell(row=r, column=43, value=f"=SUM(F{r+6}:AJ{r+6})")      # AQ
      ws.cell(row=r, column=44, value=f"=SUM(AK{r}:AP{r})")          # AR strictly excludes AQ

  for col in range(37, 45):
      col_letter = get_column_letter(col)
      terms = [f"{col_letter}{r}" for r in employee_start_rows]
      formula = f"=SUM({','.join(terms)})"
      ws.cell(row=2, column=col, value=formula)
  ```
- No hardcoded string constants like `"=SUM(F24:AJ24)"` exist; formulas expand dynamically to any number of employees or arbitrary starting rows.

### Observation 1.3: Openpyxl `data_only=False` and Formula Preservation
- In `core/excel_integrator.py` (`lines 75, 83`), workbooks are loaded with `data_only=False`:
  ```python
  self.wb = openpyxl.load_workbook(self.template_source, data_only=False)
  self.wb = openpyxl.load_workbook(self.template_path, data_only=False)
  ```
- The calculation engine flag `fullCalcOnLoad = True` is explicitly configured on the workbook in both `template_generator.py` (`lines 50, 247`) and `excel_integrator.py` (`lines 86, 375`).
- Testing confirmed that upon saving the workbook, formula cells retain their verbatim formula strings (`=SUM(...)`) rather than evaluated cached values or `None`.

### Observation 1.4: Authentic Fuzzy Matching & Diacritic Stripping
- `core/excel_integrator.py` implements an authentic 3-tier matcher using standard library `unicodedata` and `difflib.SequenceMatcher` (`lines 26-40, 166-205`):
  - Tier 1: Exact case-insensitive and whitespace-collapsed NFC match (`score 1.0`).
  - Tier 2: Unaccented match stripping tone marks and diacritics including `đ/Đ` (`score 0.95`).
  - Tier 3: `difflib.SequenceMatcher(None, target_unaccented, emp["unaccented"]).ratio()` requiring `ratio >= 0.85`.
  - Non-matching names return `(None, "", 0.0)`.

### Observation 1.5: Numeric Data Typing
- In `core/excel_integrator.py` (`lines 346-351`):
  ```python
  def _write_num(row_offset: int, val: float):
      nonlocal cells_written
      num_val = int(val) if float(val).is_integer() else float(val)
      cell = self.ws.cell(row=r_start + row_offset, column=col_date)
      cell.value = num_val
      cells_written += 1
  ```
- Meal counts are written as `int(rec.meal_count)` (`line 369`).
- Verification via openpyxl confirmed `cell.data_type == 'n'` for both integer and decimal hour values.

### Observation 1.6: Pre-populated Artifact Inspection
- Inspection of the workspace and `output/` directory found no pre-populated log files, fake test result stubs, or pre-rendered outputs. `output/` is completely clean.

### Observation 1.7: Behavioral & Stress Verification
- Execution of unit test suite: `.venv/bin/pytest tests/test_excel.py -v` -> **41 passed in 0.46s**.
- Execution of full project test suite: `.venv/bin/pytest tests/ -v` -> **247 passed in 0.60s**.
- Independent stress tests:
  1. Relocated `HOÀNG ĐẮC PHÚ` to row 3, added a new employee `TRẦN ĐĂNG KHOA` at row 10, shifted `NGUYỄN NGỌC THAO` to row 17: Successfully mapped and wrote to correct arbitrary rows without modification.
  2. Generated template with 6 employees: Grand total row 2 dynamically generated `=SUM(AK3,AK10,AK17,AK24,AK31,AK38)` and all employee formulas scaled dynamically.
  3. Preserved all formulas across multiple batch writes with zero corruption.

---

## 2. Logic Chain

1. **Premise**: An integrity violation occurs if coordinates are hardcoded to satisfy specific test cases, formulas are static strings, openpyxl runs with `data_only=True` destroying formulas, fuzzy matching is a mocked lookup table, or numeric values are stored as strings.
2. **Analysis of Code Structure**:
   - `core/template_generator.py` parses `sample_data.csv` to detect 7-row employee blocks and generates formula strings via f-strings containing variables `{r}`, `{r+offset}`, `{col_letter}`, and `{','.join(terms)}`.
   - `core/excel_integrator.py` parses template headers at startup to map employee names to row indices and dates to column indices.
   - Coordinate writing uses relative offsets `(r_start + row_offset, col_date)` rather than static cell references (`K24`, etc.).
   - `data_only=False` preserves formula ASTs and `fullCalcOnLoad=True` prompts Excel to calculate values on open.
   - Fuzzy matching uses `difflib.SequenceMatcher` with genuine string similarity calculation.
   - Numbers are written as `int` or `float` Python primitives, resulting in Excel numeric cell types (`'n'`).
3. **Empirical Proof**:
   - Adversarial shift tests confirmed that changing employee rows or dates immediately updates target cells accordingly.
   - Formula expansion test proved that 6 employee blocks produce dynamic 6-term formulas in row 2 and proper block formulas.
   - All 41 unit/integration tests and all 247 project tests execute genuinely and pass.
4. **Deduction**: The work product is clean of hardcoding, facades, formula destruction, and artificial passes.

---

## 3. Caveats

- **No Caveats**: The implementation was audited both statically via line-by-line inspection and dynamically via adversarial stress tests. All checks passed unconditionally.

---

## 4. Conclusion

## Forensic Audit Report

**Work Product**: `core/template_generator.py` and `core/excel_integrator.py`  
**Profile**: General Project  
**Verdict**: **CLEAN**

### Phase Results
- [Phase 1.1] Zero Hardcoded Coordinates: **PASS** — Coordinates computed dynamically via `(r_start + offset, col_date)`. Zero instances of `K24`/`K30` in logic.
- [Phase 1.2] Dynamic Formula Generation: **PASS** — Formulas dynamically generated via `=SUM(F{r}:AJ{r})`, `=SUM(AK{r}:AP{r})`, and row 2 grand total aggregates.
- [Phase 1.3] Openpyxl Formula Preservation: **PASS** — `data_only=False` strictly enforced; formulas preserved verbatim across write operations.
- [Phase 1.4] Authentic Fuzzy Matching: **PASS** — 3-tier matcher using `unicodedata` NFKD diacritic removal and `difflib.SequenceMatcher(ratio >= 0.85)`.
- [Phase 1.5] Numeric Cell Typing: **PASS** — Int/float coercion applied; cells verified with openpyxl `data_type == 'n'`.
- [Phase 1.6] Pre-populated Artifact Detection: **PASS** — No fake stubs or pre-populated artifacts detected.
- [Phase 2.1] Build and Test Suite: **PASS** — 41/41 `test_excel.py` passed; 247/247 full suite passed.
- [Phase 2.2] Adversarial Stress Testing: **PASS** — Dynamic row displacement and 6-employee template expansion verified.

---

## 5. Verification Method

To independently verify this audit, run the following commands in `/Users/congcm/CODE/Vibe_Code/Zalo_BOT`:

1. **Verify absence of hardcoded coordinates**:
   ```bash
   grep -En "K24|K30|AK24|AR24" core/template_generator.py core/excel_integrator.py
   ```
   *Expected output: 0 matches.*

2. **Run Excel test suite**:
   ```bash
   .venv/bin/pytest tests/test_excel.py -v
   ```
   *Expected output: 41 passed in < 1s.*

3. **Run full regression test suite**:
   ```bash
   .venv/bin/pytest tests/ -v
   ```
   *Expected output: 247 passed.*

4. **Verify dynamic coordinate shifting and formula expansion**:
   ```bash
   .venv/bin/python3.11 -c "
   import io, openpyxl
   from core.excel_integrator import ExcelIntegrator
   from core.template_generator import generate_default_template

   # Verify formula generation
   tpl = generate_default_template()
   wb = openpyxl.load_workbook(tpl, data_only=False)
   ws = wb.active
   assert ws['AK24'].value == '=SUM(F24:AJ24)'
   assert ws['AR24'].value == '=SUM(AK24:AP24)'
   assert ws['AK2'].value == '=SUM(AK3,AK10,AK17,AK24)'
   print('Formula verification: 100% PASS')
   "
   ```
   *Expected output: `Formula verification: 100% PASS`.*
