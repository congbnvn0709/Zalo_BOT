"""
Runs full pytest suite with ProposedAttendanceParser monkeypatched in core.parser.
"""
import sys
import os
import pytest

PROJECT_ROOT = "/Users/congcm/CODE/Vibe_Code/Zalo_BOT"
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

MY_DIR = "/Users/congcm/CODE/Vibe_Code/Zalo_BOT/.agents/teamwork/explorer_m1_fix"
if MY_DIR not in sys.path:
    sys.path.insert(0, MY_DIR)

from proposed_parser import (
    ProposedAttendanceParser,
    proposed_parse_attendance_messages,
    proposed_parse_single_message,
)

import core.parser
core.parser.AttendanceParser = ProposedAttendanceParser
core.parser.parse_attendance_messages = proposed_parse_attendance_messages
core.parser.parse_single_message = proposed_parse_single_message

if __name__ == "__main__":
    exit_code = pytest.main(["-v", os.path.join(PROJECT_ROOT, "tests")])
    sys.exit(exit_code)
