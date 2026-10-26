## 2026-10-26T09:07:44Z
You are the Excel Integrator Remediation Worker for Milestone 2.
Your working directory is: /Users/congcm/CODE/Vibe_Code/Zalo_BOT/.agents/teamwork/worker_m2_remediation/

MANDATORY FIRST STEPS:
1. Read /Users/congcm/CODE/Vibe_Code/Zalo_BOT/.agents/teamwork/ORIGINAL_REQUEST.md.
2. Read /Users/congcm/CODE/Vibe_Code/Zalo_BOT/PROJECT.md.
3. Read the Challenger 2 failure report: /Users/congcm/CODE/Vibe_Code/Zalo_BOT/.agents/teamwork/challenger_m2_2/handoff.md and inspect /Users/congcm/CODE/Vibe_Code/Zalo_BOT/.agents/teamwork/challenger_m2_2/stress_test_excel_m2.py.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Task:
Remediate core/excel_integrator.py to support role annotations e.g. (KTV) and phone numbers in employee name matching:
Write ownership:
- You exclusively own core/excel_integrator.py and tests/test_excel.py.
- DO NOT modify other files.

Requirements:
1. In core/excel_integrator.py:
   - Add name cleaning prior to matching: strip parenthetical annotations (e.g. (KTV), (thợ hàn), (Tổ 1)), phone numbers (e.g. 0912345678, +84...), and trailing role notes.
   - In match_employee:
     * Match against both the raw target and the cleaned target.
     * Add token containment / substring matching (if an employee's full clean name is contained as a word-boundary substring in the query or vice-versa, award high match score e.g. 0.90-0.95).
     * Verify that 'Hoàng Đắc Phú (KTV)' and 'Hoàng Đắc Phú 0912345678' match row 24 (HOÀNG ĐẮC PHÚ) with score >= 0.85.
     * Ensure non-existent names (e.g. Alexander the Great, John Doe) still return (None, '', 0.0).
2. In tests/test_excel.py:
   - Add unit tests for parenthesized role annotations, phone numbers, and substring containment.
3. Run verification suites:
   - .venv/bin/pytest tests/test_excel.py -v
   - .venv/bin/python3 .agents/teamwork/challenger_m2_2/stress_test_excel_m2.py (verify 100% PASS on all variations)
   - .venv/bin/pytest tests/ (all tests passing)
   - .venv/bin/python3 tests/verify_e2e.py (126 tests passing)
4. Deliver handoff report to:
   /Users/congcm/CODE/Vibe_Code/Zalo_BOT/.agents/teamwork/worker_m2_remediation/handoff.md
   Send a completion message back to parent.
