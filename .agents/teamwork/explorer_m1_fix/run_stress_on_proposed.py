"""
Executes the stress test harness against proposed_parser.py.
"""
import sys
import os

PROJECT_ROOT = "/Users/congcm/CODE/Vibe_Code/Zalo_BOT"
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

MY_DIR = "/Users/congcm/CODE/Vibe_Code/Zalo_BOT/.agents/teamwork/explorer_m1_fix"
if MY_DIR not in sys.path:
    sys.path.insert(0, MY_DIR)

import proposed_parser
from proposed_parser import (
    ProposedAttendanceParser,
    proposed_parse_attendance_messages,
    proposed_parse_single_message,
)

# Monkeypatch core.parser with proposed implementation to run Challenger 1's harness
import core.parser
core.parser.AttendanceParser = ProposedAttendanceParser
core.parser.parse_attendance_messages = proposed_parse_attendance_messages
core.parser.parse_single_message = proposed_parse_single_message

# Now run Challenger 1's stress test
sys.path.insert(0, os.path.join(PROJECT_ROOT, ".agents/teamwork/challenger_m1_1"))
import stress_test_parser

if __name__ == "__main__":
    results = stress_test_parser.main()
    print("\n--- PROPOSED PARSER EVALUATION SUMMARY ---")
    print(f"Total tests: {results.total_tests}")
    print(f"Crashes: {len(results.crashes)}")
    print(f"Anomalies: {len(results.status_anomalies)}")
    print(f"Structural findings: {len(results.findings)}")

    if len(results.crashes) == 0 and len(results.status_anomalies) == 0 and len(results.findings) == 0:
        print("\n>>> ALL ADVERSARIAL STRESS TESTS PASSED WITH 0 CRASHES, 0 ANOMALIES, 0 FINDINGS! <<<")
    else:
        sys.exit(1)
