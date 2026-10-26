## 2026-10-26T07:55:03Z
You are the Attendance Parser Worker for Milestone 1.
Your working directory is: /Users/congcm/CODE/Vibe_Code/Zalo_BOT/.agents/teamwork/worker_m1_parser/

MANDATORY FIRST STEPS:
1. Read /Users/congcm/CODE/Vibe_Code/Zalo_BOT/.agents/teamwork/ORIGINAL_REQUEST.md.
2. Read /Users/congcm/CODE/Vibe_Code/Zalo_BOT/PROJECT.md.
3. Review the specification report: /Users/congcm/CODE/Vibe_Code/Zalo_BOT/.agents/teamwork/survey_spec_miner_parser/report.md.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Task: Implement Milestone 1 (Attendance Message Parser):
Write ownership:
- You exclusively own:
  * models/__init__.py and models/attendance.py
  * core/__init__.py and core/parser.py
  * tests/test_parser.py

Key technical requirements:
1. Pydantic models in models/attendance.py:
   - WorkHours (hcn_100, tcn_150, hcd_130, tcd_195, sunday_day_200, sunday_night_260, total_hours)
   - AttendanceRecord (id, employee_name, normalized_name, date_str, resolved_date, day_number, is_sunday, shift_type, project, time_window, hours, meal_count, status, messages, raw_text)
2. Parser implementation in core/parser.py:
   - Multi-message batch segmentation via header lookahead (HỌ TÊN, Họ và tên, HO TEN)
   - Single-line hyphen-separated message support
   - Vietnamese name normalization (trim whitespace, title case, accents preserved)
   - Date parser supporting DD/MM, DD-MM, YYYY-MM-DD, DD/MM/YYYY, default year 2026, Sunday detection
   - Shift detection: Day (Ca ngày, Ngày), Night (Ca đêm, Đêm)
   - Working hours parser & break calculator:
     * Explicit brackets ( 8H), (11H) take precedence
     * Automatic 1h break deduction for shifts >= 8.5 elapsed hours (8h-17h, 8h-20h, 20h-5h, 20h-8h)
     * Hour allocation:
       - Regular weekday/Sat Day: up to 8h in hcn_100, excess in tcn_150
       - Regular weekday/Sat Night: up to 8h in hcd_130, excess in tcd_195
       - Sunday Day: all in sunday_day_200
       - Sunday Night: all in sunday_night_260
   - Meal detection: 0, 1, Có, Không, ko, k, x, X, v, ✓, 2
   - Non-crashing validation: VALID, WARNING, ERROR with informative diagnostic messages
3. Unit test suite in tests/test_parser.py:
   - Comprehensive test suite covering acceptance criteria standard message (HOÀNG ĐẮC PHÚ), overtime, night shifts, Sunday shifts, break deduction, various date formats, missing fields, malformed lines.
   - Run tests and document passing results.

Deliverables:
- Deliver working code and passing tests.
- Produce your handoff report in /Users/congcm/CODE/Vibe_Code/Zalo_BOT/.agents/teamwork/worker_m1_parser/handoff.md with build/test commands and output.
- Send a completion message back to parent.
