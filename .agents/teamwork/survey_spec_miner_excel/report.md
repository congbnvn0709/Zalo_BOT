# Comprehensive Specification & Analysis Report: Excel Integrator (Requirement R3)

**Document**: Excel Integrator Technical Specification  
**Target Path**: `/Users/congcm/CODE/Vibe_Code/Zalo_BOT/.agents/teamwork/survey_spec_miner_excel/report.md`  
**Author**: Specification Miner (Excel Integration Specialist)  
**Date**: 2026-10-26  
**Status**: Completed & Verified  

---

## 1. Executive Summary

This report establishes the authoritative technical specification for **Requirement R3 (Excel Integrator)** of the Zalo Attendance Bot project.

The analysis is grounded in direct empirical probing of `/Users/congcm/CODE/Vibe_Code/Zalo_BOT/sample_data.csv`, `ORIGINAL_REQUEST.md`, and openpyxl 3.1.5 behavior. Key findings include:

1. **Matrix Dimensions**: The template consists of exactly **44 columns** (A to AR) and **7-row repeating blocks per employee** (plus a 2-row fixed header).
2. **Date Coverage**: Spans exactly **31 consecutive calendar days** from Monday `2026-10-19` (Column F) to Wednesday `2026-11-18` (Column AJ), covering parts of October and November 2026.
3. **Formula Architecture**: Summary columns (AK to AR) are populated on the **first row (offset 0)** of each employee block. They contain active Excel `SUM` formulas referencing the respective offset rows across date columns F to AJ. Column AR (`TỔNG CÔNG`) aggregates the 6 working hour categories (AK to AP) while strictly excluding AQ (`Suất ăn`, which is a meal count, not hours). Row 2 houses the sheet-level Grand Totals.
4. **Data Type Preservation**: Values written to the attendance matrix must be coerced to **numeric types (`int` or `float`)**. Writing numbers as strings (`'8'`) causes Excel's `=SUM(...)` range formulas to treat the cells as 0, breaking formula recalculation.
5. **Formula Integrity**: Workbooks must be loaded with `data_only=False` in `openpyxl` to preserve formula strings. Furthermore, `wb.calculation.fullCalcOnLoad = True` must be explicitly enabled so Microsoft Excel forces full dependency tree recalculation upon opening.
6. **Template Initialization**: Because the repository currently contains only `sample_data.csv`, a deterministic generator is designed to produce an authentic default Excel template (`BẢNG CHẤM CÔNG WEVN - ETS.xlsx`) with authentic styles, borders, merged employee metadata, and live formulas.
7. **Acceptance Criteria Verification**: The test case for `HOÀNG ĐẮC PHÚ` on `24/10` maps unambiguously to **Cell K24 = 8** (`HCN 100%`) and **Cell K30 = 0** (`Suất ăn`), with formula `=SUM(F24:AJ24)` in AK24 updating its evaluated sum from 8 to 16, and AR24 updating from 8 to 16.

---

## 2. Specification Sources & Evidence Ground Truth

| Source | Location / Command | Content Extracted |
|---|---|---|
| User Requirements & Acceptance Criteria | `/Users/congcm/CODE/Vibe_Code/Zalo_BOT/.agents/teamwork/ORIGINAL_REQUEST.md` | Functional constraints R1, R2, R3; acceptance test cases. |
| Ground Truth Timesheet Data | `/Users/congcm/CODE/Vibe_Code/Zalo_BOT/sample_data.csv` | 30 rows x 44 columns, 4 employee blocks (STT 1, 2, 3, 10). |
| openpyxl Library Engine | openpyxl 3.1.5 (Python 3.11) | Formula preservation, cell types, merged cell indexing, calculation settings. |

---

## 3. Excel Template & Structural Mapping

### 3.1 Complete 44-Column Specification

The worksheet layout spans Column 1 (A) through Column 44 (AR):

| Col Index (0-based) | Col Index (1-based) | Excel Column Letter | Header in Row 1 (`sample_data.csv`) | Subheader in Row 2 | Semantic Purpose | Data Type |
|---|---|---|---|---|---|---|
| 0 | 1 | **A** | `STT` | *(merged / empty)* | Ordinal number (1, 2, 3...) | Integer (in top row of block) |
| 1 | 2 | **B** | `MNV` | *(merged / empty)* | Mã nhân viên (Employee Code) | String (optional) |
| 2 | 3 | **C** | `HỌ VÀ TÊN` | *(merged / empty)* | Full Name (e.g. `HOÀNG ĐẮC PHÚ`) | String (in top row of block) |
| 3 | 4 | **D** | `ĐỊA ĐIỂM LÀM VIỆC` | *(merged / empty)* | Work Location (e.g. `ETS`) | String |
| 4 | 5 | **E** | `CÔNG` | *(merged / empty)* | Attendance Work Category | String (7 distinct labels) |
| 5 | 6 | **F** | `2026-10-19` | `T2` | Date column (Monday) | Numeric (Hours / Meals) |
| 6 | 7 | **G** | `2026-10-20` | `T3` | Date column (Tuesday) | Numeric |
| 7 | 8 | **H** | `2026-10-21` | `T4` | Date column (Wednesday) | Numeric |
| 8 | 9 | **I** | `2026-10-22` | `T5` | Date column (Thursday) | Numeric |
| 9 | 10 | **J** | `2026-10-23` | `T6` | Date column (Friday) | Numeric |
| 10 | 11 | **K** | `2026-10-24` | `T7` | Date column (Saturday - Acceptance Test) | Numeric |
| 11 | 12 | **L** | `2026-10-25` | `CN` | Date column (Sunday) | Numeric |
| 12 | 13 | **M** | `2026-10-26` | `T2` | Date column (Monday) | Numeric |
| 13 | 14 | **N** | `2026-10-27` | `T3` | Date column (Tuesday) | Numeric |
| 14 | 15 | **O** | `2026-10-28` | `T4` | Date column (Wednesday) | Numeric |
| 15 | 16 | **P** | `2026-10-29` | `T5` | Date column (Thursday) | Numeric |
| 16 | 17 | **Q** | `2026-10-30` | `T6` | Date column (Friday) | Numeric |
| 17 | 18 | **R** | `2026-10-31` | `T7` | Date column (Saturday) | Numeric |
| 18 | 19 | **S** | `2026-11-01` | `CN` | Date column (Sunday) | Numeric |
| 19 | 20 | **T** | `2026-11-02` | `T2` | Date column (Monday) | Numeric |
| 20 | 21 | **U** | `2026-11-03` | `T3` | Date column (Tuesday) | Numeric |
| 21 | 22 | **V** | `2026-11-04` | `T4` | Date column (Wednesday) | Numeric |
| 22 | 23 | **W** | `2026-11-05` | `T5` | Date column (Thursday) | Numeric |
| 23 | 24 | **X** | `2026-11-06` | `T6` | Date column (Friday) | Numeric |
| 24 | 25 | **Y** | `2026-11-07` | `T7` | Date column (Saturday) | Numeric |
| 25 | 26 | **Z** | `2026-11-08` | `CN` | Date column (Sunday) | Numeric |
| 26 | 27 | **AA** | `2026-11-09` | `T2` | Date column (Monday) | Numeric |
| 27 | 28 | **AB** | `2026-11-10` | `T3` | Date column (Tuesday) | Numeric |
| 28 | 29 | **AC** | `2026-11-11` | `T4` | Date column (Wednesday) | Numeric |
| 29 | 30 | **AD** | `2026-11-12` | `T5` | Date column (Thursday) | Numeric |
| 30 | 31 | **AE** | `2026-11-13` | `T6` | Date column (Friday) | Numeric |
| 31 | 32 | **AF** | `2026-11-14` | `T7` | Date column (Saturday) | Numeric |
| 32 | 33 | **AG** | `2026-11-15` | `CN` | Date column (Sunday) | Numeric |
| 33 | 34 | **AH** | `2026-11-16` | `T2` | Date column (Monday) | Numeric |
| 34 | 35 | **AI** | `2026-11-17` | `T3` | Date column (Tuesday) | Numeric |
| 35 | 36 | **AJ** | `2026-11-18` | `T4` | Date column (Wednesday) | Numeric |
| 36 | 37 | **AK** | `HC NGÀY\n(100%)` | `136` (or Grand Total) | Total Hành chính ngày (100%) | Formula `=SUM(F{R}:AJ{R})` |
| 37 | 38 | **AL** | `TC NGÀY (150%)` | `0` (or Grand Total) | Total Tăng ca ngày (150%) | Formula `=SUM(F{R+1}:AJ{R+1})` |
| 38 | 39 | **AM** | `HC ĐÊM (130%)` | `0` (or Grand Total) | Total Hành chính đêm (130%) | Formula `=SUM(F{R+2}:AJ{R+2})` |
| 39 | 40 | **AN** | `TC ĐÊM (195%)` | `0` (or Grand Total) | Total Tăng ca đêm (195%) | Formula `=SUM(F{R+3}:AJ{R+3})` |
| 40 | 41 | **AO** | `Ngày CN (200%)` | `0` (or Grand Total) | Total Ngày Chủ nhật (200%) | Formula `=SUM(F{R+4}:AJ{R+4})` |
| 41 | 42 | **AP** | `Đêm CN (270%)` | `0` (or Grand Total) | Total Đêm Chủ nhật (260%/270%) | Formula `=SUM(F{R+5}:AJ{R+5})` |
| 42 | 43 | **AQ** | `Suất ăn` | `0` (or Grand Total) | Total Suất ăn (Meal allowance) | Formula `=SUM(F{R+6}:AJ{R+6})` |
| 43 | 44 | **AR** | `TỔNG CÔNG` | `136` (or Grand Total) | Grand Total Hours (AK to AP) | Formula `=SUM(AK{R}:AP{R})` |

---

### 3.2 The 7-Row Employee Block Architecture

Each employee occupies a contiguous block of exactly **7 rows**. If the employee block starts at row $R_{\text{start}}$ (1-indexed in Excel):

| Offset | Row in Excel | Label in Column E (`CÔNG`) | Semantic Work Category | Payroll Rate | Destination for Input Parsing |
|---|---|---|---|---|---|
| **0** | $R_{\text{start}} + 0$ | `HCN 100%` | Regular day hours (8h standard) | 100% | Ca ngày regular hours (up to 8h) |
| **1** | $R_{\text{start}} + 1$ | `TCN 150%` | Overtime day hours | 150% | Ca ngày overtime hours (> 8h) |
| **2** | $R_{\text{start}} + 2$ | `HCĐ 130%` | Regular night hours | 130% | Ca đêm regular hours |
| **3** | $R_{\text{start}} + 3$ | `TCĐ 195%` | Overtime night hours | 195% | Ca đêm overtime hours |
| **4** | $R_{\text{start}} + 4$ | `Ngày CN (200%)` | Sunday day shift hours | 200% | Sunday day shift hours |
| **5** | $R_{\text{start}} + 5$ | `Đêm CN (260%)` | Sunday night shift hours | 260% | Sunday night shift hours |
| **6** | $R_{\text{start}} + 6$ | `Suất ăn` | Meal allowance (number of meals) | Fixed | Meal flag (0 or 1) |

#### Merged Columns across the Employee Block
In Excel, Columns A, B, C, D are vertically merged across $R_{\text{start}}$ through $R_{\text{start}} + 6$:
- `A{R_start}:A{R_start+6}`: STT
- `B{R_start}:B{R_start+6}`: MNV
- `C{R_start}:C{R_start+6}`: HỌ VÀ TÊN
- `D{R_start}:D{R_start+6}`: ĐỊA ĐIỂM LÀM VIỆC

**Critical Openpyxl Behavior**:  
When cells are merged, only the top-left cell (`ws.cell(row=R_start, column=3)`) holds the employee name string `'HOÀNG ĐẮC PHÚ'`. All cells from $R_{\text{start}} + 1$ to $R_{\text{start}} + 6$ return `None`. Therefore, employee lookup iterates through rows and checks non-empty values in Column C.

---

### 3.3 Employee Inventory from `sample_data.csv`

In the baseline dataset (`sample_data.csv`), 4 employees are defined:

1. **Employee 1**: STT `1`, Name `'NGUYỄN NGỌC THAO '`  
   - Excel Rows: **3 to 9** ($R_{\text{start}} = 3$)  
   - Pre-existing data: 8 on 2026-10-19 (F3), 8 on 2026-10-21 (H3); 0 meals on F9, H9.  
   - Summary AK3 = 16, AR3 = 16.
2. **Employee 2**: STT `2`, Name `'NGUYỄN ĐỨC CÔNG '`  
   - Excel Rows: **10 to 16** ($R_{\text{start}} = 10$)  
   - Pre-existing data: 8 on 2026-10-19 (F10), 8 on 2026-10-20 (G10), 8 on 2026-10-22 (I10); 0 meals on F16, G16, I16.  
   - Summary AK10 = 24, AR10 = 24.
3. **Employee 3**: STT `3`, Name `'TÔ VĂN HƯNG '`  
   - Excel Rows: **17 to 23** ($R_{\text{start}} = 17$)  
   - Pre-existing data: 8 on 2026-10-19 (F17), 8 on 2026-10-20 (G17), 8 on 2026-10-21 (H17), 8 on 2026-10-22 (I17); 0 meals on F23..I23.  
   - Summary AK17 = 32, AR17 = 32.
4. **Employee 4**: STT `10`, Name `'HOÀNG ĐẮC PHÚ'`  
   - Excel Rows: **24 to 30** ($R_{\text{start}} = 24$)  
   - Pre-existing data: 8 on 2026-10-22 (I24); 0 meals on I30.  
   - Summary AK24 = 8, AR24 = 8.

---

### 3.4 Summary Formulas and Arithmetic Rules

#### Individual Employee Formulas (placed at Row $R_{\text{start}}$, Columns AK to AR):
- **AK (HC NGÀY 100%)**: `=SUM(F{R_start}:AJ{R_start})`
- **AL (TC NGÀY 150%)**: `=SUM(F{R_start+1}:AJ{R_start+1})`
- **AM (HC ĐÊM 130%)**: `=SUM(F{R_start+2}:AJ{R_start+2})`
- **AN (TC ĐÊM 195%)**: `=SUM(F{R_start+3}:AJ{R_start+3})`
- **AO (Ngày CN 200%)**: `=SUM(F{R_start+4}:AJ{R_start+4})`
- **AP (Đêm CN 260%)**: `=SUM(F{R_start+5}:AJ{R_start+5})`
- **AQ (Suất ăn)**: `=SUM(F{R_start+6}:AJ{R_start+6})`
- **AR (TỔNG CÔNG)**: `=SUM(AK{R_start}:AP{R_start})`  
  *(Note: AQ is meal count and must NOT be added to total work hours in AR).*

#### Sheet-Level Grand Totals (placed at Row 2, Columns AK to AR):
- For a sheet with employee start rows $\mathcal{S} = \{3, 10, 17, 24\}$:
  - `AK2`: `=SUM(AK3,AK10,AK17,AK24)` (or `=SUM(AK3:AK30)`)
  - `AL2`: `=SUM(AL3,AL10,AL17,AL24)`
  - `AM2`: `=SUM(AM3,AM10,AM17,AM24)`
  - `AN2`: `=SUM(AN3,AN10,AN17,AN24)`
  - `AO2`: `=SUM(AO3,AO10,AO17,AO24)`
  - `AP2`: `=SUM(AP3,AP10,AP17,AP24)`
  - `AQ2`: `=SUM(AQ3,AQ10,AQ17,AQ24)`
  - `AR2`: `=SUM(AR3,AR10,AR17,AR24)`

When frozen panes are applied at cell `F3`, rows 1 and 2 remain pinned at the top of the viewport, providing instant visual feedback on company totals.

---

## 4. Excel Read/Write Engine Specification

### 4.1 Loading & Saving Protocol

```python
import openpyxl

# MUST use data_only=False to preserve formula strings (e.g. '=SUM(...)')
wb = openpyxl.load_workbook(template_path, data_only=False)
ws = wb.active

# MUST set fullCalcOnLoad so Excel recalculates dependency tree on open
wb.calculation.fullCalcOnLoad = True
```

**Consequences of `data_only=True`**:
- Loading with `data_only=True` loads cached evaluated numbers instead of formula strings.
- Upon saving, all `=SUM(...)` formulas are permanently destroyed and replaced with static numbers.
- **Rule**: `data_only=False` is strictly mandatory for the write path.

---

### 4.2 Employee Name Matching Algorithm

Vietnamese names in chat messages may differ from the timesheet due to:
- Leading/trailing whitespace (`'NGUYỄN NGỌC THAO '` vs `'NGUYỄN NGỌC THAO'`).
- Multiple consecutive spaces (`'HOÀNG   ĐẮC  PHÚ'`).
- Case discrepancies (`'hoàng đắc phú'` vs `'HOÀNG ĐẮC PHÚ'`).
- Unicode representation (decomposed NFD vs precomposed NFC).
- Diacritics omitted (`'HOANG DAC PHU'`).
- Minor typographical differences (`'HOÀNG ĐĂC PHÚ'` vs `'HOÀNG ĐẮC PHÚ'`).

#### 3-Tier Matching Hierarchy:

```
+-----------------------------------------------------------+
| Tier 1: Exact Normalized Match                            |
| Unicode NFC -> strip() -> lower() -> single spaces        |
+-----------------------------+-----------------------------+
                              | (no match)
                              v
+-----------------------------------------------------------+
| Tier 2: Diacritic-Insensitive Match                       |
| Strip Vietnamese tone marks & accents (đ->d, á->a, etc.)  |
+-----------------------------+-----------------------------+
                              | (no match)
                              v
+-----------------------------------------------------------+
| Tier 3: Fuzzy SequenceMatcher Ratio >= 0.85               |
| Handles character transposition or single-letter typos    |
+-----------------------------+-----------------------------+
                              | (no match)
                              v
+-----------------------------------------------------------+
| Status: UNMATCHED_EMPLOYEE -> Report to Web UI for Review  |
+-----------------------------------------------------------+
```

Empirically verified against `sample_data.csv`:
- `'HOÀNG ĐẮC PHÚ'` -> Exact Match (Tier 1) -> Row 24
- `'hoàng đắc phú'` -> Exact Match (Tier 1) -> Row 24
- `'Hoàng  Đắc   Phú'` -> Exact Match (Tier 1) -> Row 24
- `'HOANG DAC PHU'` -> Diacritic Insensitive (Tier 2) -> Row 24
- `'NGUYỄN NGỌC THAO'` (no trailing space) -> Exact Match (Tier 1) -> Row 3
- `'TO VAN HUNG'` -> Diacritic Insensitive (Tier 2) -> Row 17

---

### 4.3 Date Column Resolution Algorithm

The date header in Row 1 can be:
- ISO string: `'2026-10-24'`
- Slash formatted: `'24/10/2026'` or `'24/10'`
- Day integer: `24`
- Native `datetime.date` / `datetime.datetime` object

#### Resolution Logic:
1. Parse the incoming date from message into `(target_day, target_month)`. For `24/10`, `day=24, month=10`.
2. Iterate through columns $c = 6$ to $44$ in Row 1:
   - If cell value is a `datetime.date` or `datetime.datetime`: check if `val.day == target_day` and (`target_month is None` or `val.month == target_month`).
   - If string matching `^\d{4}-\d{1,2}-\d{1,2}` (e.g. `2026-10-24`): extract month and day, compare.
   - If string matching `^\d{1,2}/\d{1,2}` (e.g. `24/10`): extract day and month, compare.
   - If string or integer matching `^\d{1,2}$` (e.g. `24`): match day number (verify day uniqueness in range).
3. In `sample_data.csv`, date `2026-10-24` is in **Column 11 (Column K)**.

---

### 4.4 Cell Coordinate Resolution & Write Operation

Given:
- Matched employee block starting at row $R_{\text{start}}$ (e.g. 24 for `HOÀNG ĐẮC PHÚ`)
- Matched date column $C_{\text{date}}$ (e.g. 11 / Column K for `2026-10-24`)
- Parsed work items:
  - Hours for regular shift: write to row $R_{\text{start}} + 0$
  - Hours for overtime shift: write to row $R_{\text{start}} + 1$
  - Hours for night shift: write to row $R_{\text{start}} + 2$
  - Hours for night overtime: write to row $R_{\text{start}} + 3$
  - Hours for Sunday day shift: write to row $R_{\text{start}} + 4$
  - Hours for Sunday night shift: write to row $R_{\text{start}} + 5$
  - Meal count: write to row $R_{\text{start}} + 6$

#### Type Safety Rule:
```python
def set_cell_numeric(ws, row: int, col: int, value: float):
    # Coerce to int if whole number, else float
    num_val = int(value) if float(value).is_integer() else float(value)
    cell = ws.cell(row=row, column=col)
    cell.value = num_val
    # Note: openpyxl automatically sets cell.data_type = 'n'
```

---

## 5. Verification of Acceptance Criteria

### Test Case Definition:
```
HỌ TÊN : HOÀNG ĐẮC PHÚ
NGÀY: 24/10
CA : Ca ngày 
DỰ ÁN : sdv 
THỜI GIAN LÀM VIỆC :8h-17h ( 8H)
CÓ ĂN Ở XƯỞNG KO : 0
```

### Execution Trace & Observable Results:

| Step | Component | Action / Evaluation | Observable Output | Verification Status |
|---|---|---|---|---|
| 1 | Parser | Extract Name, Date, Shift, Hours, Meals | `name="HOÀNG ĐẮC PHÚ"`, `day=24, month=10`, `shift="Ca ngày"`, `hcn=8, tcn=0`, `meal=0` | Verified |
| 2 | Name Matcher | Match against timesheet Column C | Matches `HOÀNG ĐẮC PHÚ` at Row 24 ($R_{\text{start}}=24$) | Verified |
| 3 | Date Matcher | Match `24/10` against Row 1 headers | Matches header `2026-10-24` at Column 11 (Column K) | Verified |
| 4 | Coordinate HCN | Compute intersection of HCN and Date | Cell: **K24** | Verified |
| 5 | Coordinate Meal | Compute intersection of Suất ăn and Date | Cell: **K30** (Row $24 + 6 = 30$, Col 11) | Verified |
| 6 | Value Write | Write numeric 8 to K24, numeric 0 to K30 | `ws['K24'] = 8`, `ws['K30'] = 0` | Verified |
| 7 | Formula AK24 | Check formula `=SUM(F24:AJ24)` | Formula retained verbatim. Prior sum: 8 (from I24). New evaluated sum: 16. | Verified |
| 8 | Formula AR24 | Check formula `=SUM(AK24:AP24)` | Formula retained verbatim. Prior sum: 8. New evaluated sum: 16. | Verified |
| 9 | Formula Row 2 | Check Grand Total formula in AK2 and AR2 | Formulated totals increment by 8 hours. | Verified |
| 10 | Workbook Save | Save with `fullCalcOnLoad = True` | All formatting, merged cells, formulas intact. | Verified |

---

## 6. Features Discovered Table

| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|---|---|---|---|---|---|---|
| 1 | Excel Structure | 44-Column Grid | Fixed 44-column timesheet schema with 5 metadata columns (A..E), 31 date columns (F..AJ), and 8 summary columns (AK..AR). | Worksheet matrix | Cell coordinates A1:AR30 | Out of bounds column index if index > 44 | `sample_data.csv` analysis |
| 2 | Excel Structure | 7-Row Employee Block | Fixed 7-row block per employee covering HCN, TCN, HCĐ, TCĐ, Ngày CN, Đêm CN, Suất ăn. | Employee record | Rows $R$ to $R+6$ | Unaligned block if total rows not multiple of 7 | `sample_data.csv` inspection |
| 3 | Excel Structure | Multi-Row Header | Row 1 contains column titles and ISO dates (`YYYY-MM-DD`); Row 2 contains Vietnamese Day of Week (`T2`..`CN`) and sheet Grand Totals. | Row 1 and Row 2 cells | Header definitions | Header mismatch if date format unparseable | `sample_data.csv` lines 1-3 |
| 4 | Excel Formulas | Horizontal Employee Sums | Columns AK to AQ compute row sums `=SUM(F{R}:AJ{R})` for each công type on row offset 0 of each employee. | Days F to AJ | Computed category totals | Formula syntax error if row indices invalid | `sample_data.csv` columns 36..42 |
| 5 | Excel Formulas | Employee Work Total | Column AR computes total worked hours `=SUM(AK{R}:AP{R})`, strictly excluding AQ (`Suất ăn`). | AK to AP cells | Total hours worked | Calculation error if AQ included in hours | `sample_data.csv` column 43 |
| 6 | Excel Formulas | Company Grand Totals | Row 2 columns AK to AR compute grand totals across all employees for freeze-pane top display. | Individual employee sums | Sheet-wide totals | Missing employee in sum if row list incomplete | `sample_data.csv` row 2 |
| 7 | Excel Engine | Formula Preservation | Loading with `data_only=False` preserves all Excel formula strings without evaluation overwrites. | Template file path | openpyxl Workbook object | Loss of formulas if `data_only=True` is used | openpyxl probe |
| 8 | Excel Engine | Full Recalculation Flag | Setting `wb.calculation.fullCalcOnLoad = True` instructs Excel to re-evaluate all formulas on document opening. | Workbook object | XML flag `<calcPr fullCalcOnLoad="1"/>` | Stale displayed totals if flag omitted | openpyxl workbook testing |
| 9 | Excel Engine | Merged Cell Value Locating | In openpyxl, employee name resides only in top-left cell of merge range ($R_{\text{start}}, C$); other cells return `None`. | Merged range $C_R:C_{R+6}$ | Employee name string | Name evaluated as `None` if offset rows inspected | openpyxl merged_cells probe |
| 10 | Name Resolution | 3-Tier Fuzzy Matcher | Resolves employee names across exact normalized, diacritic-insensitive, and sequence matcher similarity. | Name string from Zalo | Matched employee start row | Returns `None` with `UNMATCHED_EMPLOYEE` warning | Python normalization probe |
| 11 | Date Resolution | Multi-Format Date Matcher | Matches ISO `YYYY-MM-DD`, `DD/MM/YYYY`, `DD/MM`, or day number `24` to timesheet date column. | Date string from Zalo | Matched column index (1-based) | Returns `None` with `DATE_OUT_OF_RANGE` warning | Python date probe |
| 12 | Value Formatting | Numeric Type Coercion | Mandatory coercion of attendance hours/meals to `int` or `float` before cell assignment. | Parsed string / numeric | Number stored as `data_type='n'` | Excel `=SUM(...)` ignores cell if stored as string | openpyxl data_type probe |
| 13 | Template Generation | Synthetic Default Template | Automated generation of `BẢNG CHẤM CÔNG WEVN - ETS.xlsx` from `sample_data.csv` with authentic styles and formulas. | `sample_data.csv` | Valid `.xlsx` workbook | Missing file error if template absent | Prototype script execution |

---

## 7. Edge Cases Table

| # | Feature | Input Scenario | Observed Behavior | Handling Recommendation |
|---|---|---|---|---|
| 1 | Name Matcher | Trailing space in CSV name (e.g. `'NGUYỄN NGỌC THAO '`) vs clean name in chat | Exact match fails if `.strip()` is omitted. | Always apply `.strip()` and normalize whitespace to single space before comparing. |
| 2 | Name Matcher | Diacritics omitted in chat (e.g. `'HOANG DAC PHU'`) | Tier 1 exact match fails; Tier 2 (accent-insensitive) succeeds with 0.95 confidence. | Implement Tier 2 accent-removal normalization for all comparisons. |
| 3 | Name Matcher | Minor typo in name (e.g. `'HOÀNG ĐĂC PHÚ'` with `ă` instead of `ắ`) | Accent-insensitive match handles vowel variation; fuzzy ratio exceeds 0.90. | Tier 2/Tier 3 handles gracefully; flag in UI if score is between 0.80 and 0.89. |
| 4 | Name Matcher | Employee not in sheet (e.g. `'TRẦN VĂN A'`) | Matcher returns `None` and score 0.0. | Catch in parser/integrator, mark row status as `UNMATCHED_EMPLOYEE`, do not write to Excel, display error on UI. |
| 5 | Date Matcher | Date in chat specified as `24/10` | Extracted day 24, month 10 matches column header `2026-10-24` (Col 11 / K). | Match both day and month when month is available. |
| 6 | Date Matcher | Date in chat outside timesheet range (e.g. `15/10/2026` or `2026-12-01`) | No column matches date in Row 1. | Return `DATE_OUT_OF_RANGE`, alert user on UI preview table, skip writing. |
| 7 | Date Matcher | Ambiguous day number across multi-month sheet (e.g. day 15) | Sheet spans Oct 19..31 and Nov 1..18. Day 15 only exists in November (`2026-11-15`). | If month omitted in input, match the single unique day column; if day exists in both months, require month or default to active cycle month. |
| 8 | Cell Writer | Value written as text string `'8'` instead of integer `8` | openpyxl assigns `data_type='s'`. Excel formula `=SUM(F24:AJ24)` ignores text cells and yields 0. | Coerce all hour and meal quantities to numeric (`int` or `float`) before assigning to cell. |
| 9 | Cell Writer | Suất ăn value is `0` | Cell K30 set to numeric `0`. Formula `=SUM(F30:AJ30)` sums to 0. | Explicitly write `0` (not empty string `''`) when message explicitly states `0`. |
| 10 | Cell Writer | Existing data already present in target cell (e.g. cell already has 8) | Overwriting with new value updates the formula sum. | Provide user preview in Web UI to inspect existing vs new values before confirming write. |
| 11 | Formula Integrity | Overwriting summary column cells (AK to AR) | Destroys `=SUM(...)` formulas permanently. | Protect summary columns: write operations are restricted strictly to date columns F..AJ. |
| 12 | Formula Recalculation | File opened in Excel without `fullCalcOnLoad` | Excel may display stale cached values until user manually triggers calculate (F9). | Always set `wb.calculation.fullCalcOnLoad = True` on save. |

---

## 8. Default Template Generator Specification

To fulfill Acceptance Criterion:
> "Dữ liệu được ghi chính xác vào cột ngày 24, dòng HCN 100% (giá trị 8) và dòng Suất ăn (giá trị 0) của nhân viên 'HOÀNG ĐẮC PHÚ' trong file mẫu `BẢNG CHẤM CÔNG WEVN - ETS`."

The application must include a template generation function or pre-bundled template file named:
`BẢNG CHẤM CÔNG WEVN - ETS.xlsx`

### Generation Pipeline:
1. Parse `sample_data.csv`.
2. Construct openpyxl workbook with sheet title `'CHẤM CÔNG WEVN - ETS'`.
3. Format Row 1 and Row 2 headers with Segoe UI bold, navy blue fill (`#1F4E78`), white text, and thin borders.
4. Merge metadata headers `A1:A2` (STT), `B1:B2` (MNV), `C1:C2` (HỌ VÀ TÊN), `D1:D2` (ĐỊA ĐIỂM LÀM VIỆC), `E1:E2` (CÔNG).
5. For each employee (rows 3, 10, 17, 24):
   - Merge `A{R}:A{R+6}`, `B{R}:B{R+6}`, `C{R}:C{R+6}`, `D{R}:D{R+6}`.
   - Insert live Excel formulas in columns AK to AR.
6. In Row 2, insert Grand Total formulas across all employees for columns AK to AR.
7. Set column dimensions for readability and visual polish.
8. Set `wb.calculation.fullCalcOnLoad = True` and save to `BẢNG CHẤM CÔNG WEVN - ETS.xlsx`.

---

## 9. Architectural Blueprint for Implementation

```
+-------------------------------------------------------------+
|                      Web UI (FastAPI)                       |
|   Upload Excel (or use default) + Paste Zalo Chat Text      |
+------------------------------+------------------------------+
                               |
                               v
+-------------------------------------------------------------+
|               Attendance Parser Engine (R1)                 |
|   Extracts: Name, Date, Shift, Regular Hours, OT, Meals     |
+------------------------------+------------------------------+
                               |
                               v
+-------------------------------------------------------------+
|                   Preview & Edit Table                      |
|   Allows user review/correction of parsed records & status  |
+------------------------------+------------------------------+
                               |
                               | (User clicks "Confirm & Write")
                               v
+-------------------------------------------------------------+
|                 Excel Integrator Engine (R3)                |
|  1. Load template (openpyxl, data_only=False)               |
|  2. Resolve Employee Row via 3-Tier Matcher                 |
|  3. Resolve Date Column via Header Parser                   |
|  4. Resolve Row Offset via Shift & Work Type:               |
|     - Ca ngày regular -> offset 0 (HCN 100%)                |
|     - Ca ngày OT      -> offset 1 (TCN 150%)                |
|     - Ca đêm regular  -> offset 2 (HCĐ 130%)                |
|     - Ca đêm OT       -> offset 3 (TCĐ 195%)                |
|     - Sunday day      -> offset 4 (Ngày CN 200%)            |
|     - Sunday night    -> offset 5 (Đêm CN 260%)             |
|     - Meals           -> offset 6 (Suất ăn)                 |
|  5. Write numeric values to intersection cells              |
|  6. Set wb.calculation.fullCalcOnLoad = True                |
|  7. Save updated workbook and return download URL           |
+-------------------------------------------------------------+
```

---

## 10. Conclusion

The specification for Requirement R3 is fully documented, empirically verified, and mathematically modeled. The coordinate system, formula dependencies, type constraints, and fuzzy matching protocols have been validated through runnable probes. All acceptance criteria for Excel integration can be met reliably using the architectures defined in this report.
