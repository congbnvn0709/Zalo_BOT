## 2026-10-26T10:00:41Z
You are the Milestone 4 Core Remediation Worker.
Your working directory is: /Users/congcm/CODE/Vibe_Code/Zalo_BOT/.agents/teamwork/worker_m4_remediation/

MANDATORY FIRST STEPS:
1. Read /Users/congcm/CODE/Vibe_Code/Zalo_BOT/.agents/teamwork/ORIGINAL_REQUEST.md.
2. Read /Users/congcm/CODE/Vibe_Code/Zalo_BOT/PROJECT.md.
3. Read the failure findings in /Users/congcm/CODE/Vibe_Code/Zalo_BOT/.agents/teamwork/challenger_m4_1/handoff.md and inspect /Users/congcm/CODE/Vibe_Code/Zalo_BOT/.agents/teamwork/challenger_m4_1/stress_test_core.py.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Task:
Remediate the two edge cases surfaced by Challenger 1:
Write ownership:
- You exclusively own: core/parser.py, core/template_generator.py, and templates_excel/BẢNG CHẤM CÔNG WEVN - ETS.xlsx.
- DO NOT touch models/, api/, static/, run.py, or existing tests.

Requirements:
1. In core/parser.py:
   - In AttendanceParser.split_messages(self, text: str):
     Immediately normalize input text to Unicode Normalization Form C:
     text = unicodedata.normalize('NFC', text)
   - In AttendanceParser.parse_single(self, raw_message: str):
     Immediately normalize input message to Unicode Normalization Form C:
     raw_message = unicodedata.normalize('NFC', raw_message)
   - In parse_single_message and parse_attendance_messages:
     Ensure NFC normalization is safely applied so all decomposed (NFD) text from macOS/iOS clipboards or composite IMEs parses identically to precomposed NFC.
2. In core/template_generator.py:
   - In Row 2 grand total formula generation (lines 101-106):
     Handle rosters of any size without exceeding Excel's 255-argument limit per function:
     When len(terms) <= 250:
         formula = f"=SUM({','.join(terms)})"
     Else:
         chunks = [terms[i:i + 250] for i in range(0, len(terms), 250)]
         sub_sums = [f"SUM({','.join(c)})" for c in chunks]
         formula = f"=SUM({','.join(sub_sums)})"
   - Re-generate templates_excel/BẢNG CHẤM CÔNG WEVN - ETS.xlsx by running template_generator.py so bundled template reflects the clean formulas.
3. Verification:
   - Run .venv/bin/python3 .agents/teamwork/challenger_m4_1/stress_test_core.py (verify 22/22 PASS with 0 failures and 0 warnings).
   - Run .venv/bin/python3 .agents/teamwork/challenger_m4_2/stress_test_m4_2.py (verify 70/70 PASS).
   - Run .venv/bin/pytest tests/ -v (all tests pass).
   - Run .venv/bin/python3 tests/verify_e2e.py (all 126 tests across Tiers 1-4 pass).
4. Deliver handoff report to:
   /Users/congcm/CODE/Vibe_Code/Zalo_BOT/.agents/teamwork/worker_m4_remediation/handoff.md
Send a completion message back to parent.
