## 2026-10-26T07:37:17Z

You are the Parser Spec Miner for the Zalo Attendance project.
Your working directory is: /Users/congcm/CODE/Vibe_Code/Zalo_BOT/.agents/teamwork/survey_spec_miner_parser/

MANDATORY FIRST STEP:
Read /Users/congcm/CODE/Vibe_Code/Zalo_BOT/.agents/teamwork/ORIGINAL_REQUEST.md.

Task: Deeply analyze Requirement R1 (Attendance Message Parser) and related Acceptance Criteria.
1. Message formats:
   - Analyze standard format:
     HỌ TÊN : HOÀNG ĐẮC PHÚ
     NGÀY: 24/10
     CA : Ca ngày 
     DỰ ÁN : sdv 
     THỜI GIAN LÀM VIỆC :8h-17h ( 8H)
     CÓ ĂN Ở XƯỞNG KO : 0
   - Variations and edge cases:
     * Case sensitivity, whitespace around colons, missing accents or uppercase/lowercase.
     * Date formats: DD/MM, DD-MM, YYYY-MM-DD, DD/MM/YYYY.
     * Shift names: Ca ngày, Ca đêm, ca ngay, ca dem, Ngày, Đêm.
     * Project name / Xưởng: arbitrary string, optional or required.
     * Working hours formats: 8h-17h (8H), 8h-20h (11H), 8:00 - 17:00, 20h-8h (11H), 20h-5h (8H), overtime notation, Sunday shifts.
     * Calculation rules:
       - Regular day shift (HCN 100%): up to 8 hours during daytime.
       - Overtime day (TCN 150%): excess hours over 8h in daytime.
       - Regular night shift (HCĐ 130%): night hours.
       - Overtime night (TCĐ 195% / 200%): excess hours in night shift.
       - Sunday work (200% day, 260% night).
     * Meal detection: CÓ ĂN Ở XƯỞNG KO: 0, 1, Có, Không, ko, k, x.
   - Error detection & validation:
     * Missing fields (name, date, shift, hours).
     * Malformed time format.
     * How to flag warnings/errors without crashing.
   - Batch parsing:
     * Multi-message delimiter: multiple messages pasted together in a single text block, separated by blank lines or headers.

Deliverable:
Write a comprehensive specification and parsing rulebook to:
/Users/congcm/CODE/Vibe_Code/Zalo_BOT/.agents/teamwork/survey_spec_miner_parser/report.md
Include test cases covering happy path, edge cases, error cases, and time calculation formulas.
When finished, send a message back to parent with the file path and executive summary.
