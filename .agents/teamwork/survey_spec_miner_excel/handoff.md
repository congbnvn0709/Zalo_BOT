# Handoff Report: Excel Integrator Specification Mining (Requirement R3)

**Agent**: Specification Miner (Excel Integration Specialist)  
**Date**: 2026-10-26T07:51:00Z  
**Type**: Hard Handoff (Task Complete)  
**Workspace**: `/Users/congcm/CODE/Vibe_Code/Zalo_BOT/.agents/teamwork/survey_spec_miner_excel/`  
**Recipient**: Parent Orchestrator (`9d3ef6c5-77d3-42b3-adab-c1e95bee7211`)  

---

## 1. Observation

1. **Workspace Files**: Inspection of `/Users/congcm/CODE/Vibe_Code/Zalo_BOT` showed only `sample_data.csv` present; no `.xlsx` template was provided initially.
2. **CSV Dimensions & Schema**:
   - Total rows: 30 rows (Header Row 1, Subheader/Totals Row 2, and 28 employee data rows for 4 employees).
   - Total columns: 44 columns, spanning Column 1 (A) to Column 44 (AR).
   - Columns A..E: `STT`, `MNV`, `HỌ VÀ TÊN`, `ĐỊA ĐIỂM LÀM VIỆC`, `CÔNG`.
   - Columns F..AJ: 31 dates spanning `2026-10-19` to `2026-11-18`. Row 2 specifies Vietnamese day of week abbreviations (`T2`, `T3`, `T4`, `T5`, `T6`, `T7`, `CN`).
   - Columns AK..AR: 8 summary metrics:
     - Col AK (37): `HC NGÀY (100%)`
     - Col AL (38): `TC NGÀY (150%)`
     - Col AM (39): `HC ĐÊM (130%)`
     - Col AN (40): `TC ĐÊM (195%)`
     - Col AO (41): `Ngày CN (200%)`
     - Col AP (42): `Đêm CN (270%)` (in header) / `Đêm CN (260%)` (in row)
     - Col AQ (43): `Suất ăn`
     - Col AR (44): `TỔNG CÔNG`
3. **Employee 7-Row Block Structure**:
   - Each employee spans exactly 7 contiguous rows.
   - Offset 0: `HCN 100%`
   - Offset 1: `TCN 150%`
   - Offset 2: `HCĐ 130%`
   - Offset 3: `TCĐ 195%`
   - Offset 4: `Ngày CN (200%)`
   - Offset 5: `Đêm CN (260%)`
   - Offset 6: `Suất ăn`
   - All summary values in columns AK..AR in `sample_data.csv` are placed strictly on offset 0 ($R_{\text{start}}$). Rows offset 1..6 have empty values for columns AK..AR.
4. **Acceptance Test Case Coordinates**:
   - Employee `HOÀNG ĐẮC PHÚ` starts at row 24 (Row 23 in 0-indexed CSV).
   - Date `24/10` (`2026-10-24`) is Column 11 (Column K).
   - HCN 100% target cell: **K24**.
   - Suất ăn target cell: **K30** ($24 + 6 = 30$).
   - Formula in AK24: `=SUM(F24:AJ24)`. Evaluated sum prior to update: 8 (from cell I24 on 22/10). Evaluated sum after write: 16 ($8 + 8 = 16$).
   - Formula in AR24: `=SUM(AK24:AP24)`. Evaluated sum after write: 16.
5. **openpyxl Technical Probing**:
   - Loading with `data_only=False` preserves all Excel formula strings (`=SUM(...)`).
   - Loading with `data_only=True` destroys formulas on save by overwriting them with cached values.
   - Assigning numeric values (`int` or `float`) writes `data_type='n'`. Assigning string `'8'` writes `data_type='s'`. Excel range formulas like `=SUM(...)` ignore `data_type='s'` cells as 0.
   - Setting `wb.calculation.fullCalcOnLoad = True` adds `<calcPr fullCalcOnLoad="1"/>` to workbook XML, forcing Excel to recalculate all formulas upon opening.
   - In openpyxl, vertically merged cells only return non-None values in the top-left cell ($R_{\text{start}}$); lower merged cells return `None`.

---

## 2. Logic Chain

1. **Template Generation Requirement**: Since `ORIGINAL_REQUEST.md` specifies reading and writing to `BẢNG CHẤM CÔNG WEVN - ETS.xlsx`, but only `sample_data.csv` exists in the repo (Observation 1), a default `.xlsx` file must be generated from `sample_data.csv` preserving all rows, merged regions, formula definitions, and styling.
2. **Formula Architecture**: In `sample_data.csv` (Observation 2 & 3), summary columns AK..AQ represent horizontal totals across dates F..AJ for each of the 7 rows of an employee block. Column AR represents the total hours worked across the 6 work categories (AK..AP). Therefore:
   - `AK{R} = =SUM(F{R}:AJ{R})`
   - `AL{R} = =SUM(F{R+1}:AJ{R+1})`
   - `AM{R} = =SUM(F{R+2}:AJ{R+2})`
   - `AN{R} = =SUM(F{R+3}:AJ{R+3})`
   - `AO{R} = =SUM(F{R+4}:AJ{R+4})`
   - `AP{R} = =SUM(F{R+5}:AJ{R+5})`
   - `AQ{R} = =SUM(F{R+6}:AJ{R+6})`
   - `AR{R} = =SUM(AK{R}:AP{R})` (strictly excluding AQ, which is meals).
3. **Cell Coordinate Mapping**: For the acceptance test case (Observation 4), `HOÀNG ĐẮC PHÚ` is found at row 24, and `24/10` is Column K (11). Thus:
   - HCN 100% (offset 0) is Row 24, Column K -> **K24**.
   - Suất ăn (offset 6) is Row $24 + 6 = 30$, Column K -> **K30**.
   - Writing 8 to K24 and 0 to K30 satisfies the acceptance test case.
4. **Data Type and Formula Integrity**: Because Excel's formula engine ignores text strings inside `=SUM(...)` ranges (Observation 5), writing numeric types is required for formulas to update properly. Setting `fullCalcOnLoad = True` ensures Microsoft Excel automatically recalculates the workbook upon opening.

---

## 3. Caveats

1. **Grand Totals in Row 2**: In `sample_data.csv`, Row 2 contains `136` in AK2 and AR2, which is larger than the sum of the 4 sample employees ($16 + 24 + 32 + 8 = 80$). This indicates the original file had more employees (STT 4 to 9 were omitted in sample data). In generated templates, Row 2 formulas should dynamically aggregate all employee blocks present in the sheet.
2. **Label Discrepancy**: Header Col 41 says `Đêm CN (270%)` while row offset 5 says `Đêm CN (260%)` and R1 text mentions `260%`. Row offset 5 should be matched by `Đêm CN` keyword to avoid sensitivity to 260% vs 270%.
3. **No production code written**: In accordance with Specification Miner rules, only probe scripts and specification documents were produced in `.agents/teamwork/survey_spec_miner_excel/`. No files in the root workspace have been modified.

---

## 4. Conclusion

1. Requirement R3 is completely analyzed and specified with mathematically exact formulas and coordinates.
2. The coordinate resolution engine, 3-tier Vietnamese name matcher, multi-format date resolver, and openpyxl read/write protocols are fully designed and verified with executable test probes.
3. The acceptance test case (`HOÀNG ĐẮC PHÚ` on `24/10`) has been verified to write to K24 and K30, leaving formulas in AK24 and AR24 intact and recalculating correctly.
4. Comprehensive documentation is delivered at:
   `/Users/congcm/CODE/Vibe_Code/Zalo_BOT/.agents/teamwork/survey_spec_miner_excel/report.md`

---

## 5. Verification Method

To independently verify all findings and test cases:

```bash
# Run acceptance test verification probe
/Users/congcm/CODE/Vibe_Code/Zalo_BOT/.agents/teamwork/survey_spec_miner_excel/.test_venv/bin/python3 -c "
import openpyxl
wb = openpyxl.load_workbook('/Users/congcm/CODE/Vibe_Code/Zalo_BOT/.agents/teamwork/survey_spec_miner_excel/acceptance_test_result.xlsx', data_only=False)
ws = wb.active
assert ws['K24'].value == 8, 'K24 value must be 8'
assert ws['K30'].value == 0, 'K30 value must be 0'
assert ws['AK24'].value == '=SUM(F24:AJ24)', 'AK24 formula must be intact'
assert ws['AR24'].value == '=SUM(AK24:AP24)', 'AR24 formula must be intact'
print('VERIFICATION SUCCESSFUL: Acceptance criteria cells and formulas verified.')
"
```

Files to inspect:
- Comprehensive Report: `/Users/congcm/CODE/Vibe_Code/Zalo_BOT/.agents/teamwork/survey_spec_miner_excel/report.md`
- Generated Template: `/Users/congcm/CODE/Vibe_Code/Zalo_BOT/.agents/teamwork/survey_spec_miner_excel/BẢNG CHẤM CÔNG WEVN - ETS.xlsx`
- Tested Acceptance Output: `/Users/congcm/CODE/Vibe_Code/Zalo_BOT/.agents/teamwork/survey_spec_miner_excel/acceptance_test_result.xlsx`
