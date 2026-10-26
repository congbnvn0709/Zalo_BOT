## 2026-10-26T07:37:17Z
You are the Excel Integration Miner for the Zalo Attendance project.
Your working directory is: /Users/congcm/CODE/Vibe_Code/Zalo_BOT/.agents/teamwork/survey_spec_miner_excel/

MANDATORY FIRST STEP:
Read /Users/congcm/CODE/Vibe_Code/Zalo_BOT/.agents/teamwork/ORIGINAL_REQUEST.md and view /Users/congcm/CODE/Vibe_Code/Zalo_BOT/sample_data.csv.

Task: Deeply analyze Requirement R3 (Excel Integrator) and Acceptance Criteria.
1. Excel Template & Structure:
   - Deeply inspect sample_data.csv to map the exact rows, columns, headers, employee blocks, and summary formulas.
   - Map the 7-row block per employee:
     1. HCN 100%
     2. TCN 150%
     3. HCĐ 130%
     4. TCĐ 195%
     5. Ngày CN (200%)
     6. Đêm CN (260%)
     7. Suất ăn
   - Column layout: STT, MNV, HỌ VÀ TÊN, ĐỊA ĐIỂM LÀM VIỆC, CÔNG, followed by date columns (e.g. 2026-10-19 to 2026-11-18, or days 1..31), and summary columns (HC NGÀY, TC NGÀY, HC ĐÊM, TC ĐÊM, Ngày CN, Đêm CN, Suất ăn, TỔNG CÔNG).
   - Day of week row (T2..CN).
2. Template generation & format preservation:
   - Since only sample_data.csv exists in the repo initially, how to generate an authentic default .xlsx template file (BẢNG CHẤM CÔNG WEVN - ETS.xlsx) preserving Excel formulas (SUM for totals), merged header cells, borders, colors, font styling.
3. Excel Read/Write Engine:
   - How to use openpyxl with data_only=False to preserve existing formulas and styles.
   - Fuzzy name matching: Matching normalized names like 'HOÀNG ĐẮC PHÚ' to employee names in the sheet, handling spaces, accents, case.
   - Cell coordinate resolution: Locating employee row block, matching target date column (matching either day number 24 or date string), setting cell value, and ensuring summary formula cells recalculate when opened in Excel.
4. Acceptance criteria verification:
   - Specifically verify the test case: HOÀNG ĐẮC PHÚ on 24/10 gets 8 in HCN 100% and 0 in Suất ăn, and formulas update.

Deliverable:
Write a comprehensive specification and analysis report to:
/Users/congcm/CODE/Vibe_Code/Zalo_BOT/.agents/teamwork/survey_spec_miner_excel/report.md
When finished, send a message back to parent with the file path and executive summary.
