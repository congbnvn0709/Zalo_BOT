# BRIEFING — 2026-10-26T08:33:00Z

## Mission
Analyze 6 failure modes from Challenger 1 and Reviewer observations on `core/parser.py`, and design a complete, robust, regression-free remediation plan for Milestone 1.

## 🔒 My Identity
- Archetype: explorer
- Roles: investigation, synthesis, architectural analysis
- Working directory: /Users/congcm/CODE/Vibe_Code/Zalo_BOT/.agents/teamwork/explorer_m1_fix/
- Original parent: 9d3ef6c5-77d3-42b3-adab-c1e95bee7211
- Milestone: Milestone 1 (Attendance Message Parser remediation)

## 🔒 Key Constraints
- Read-only investigation — do NOT implement production code
- Must fix all 6 challenger issues
- Must satisfy all 538 stress tests in stress_test_parser.py
- Must maintain all existing 199 unit & E2E tests passing
- Account for reviewer observations regarding split_messages lookahead on TÊN\s*

## Current Parent
- Conversation ID: 9d3ef6c5-77d3-42b3-adab-c1e95bee7211
- Updated: not yet

## Investigation State
- **Explored paths**: `ORIGINAL_REQUEST.md`, `PROJECT.md`, `core/parser.py`, `challenger_m1_1/handoff.md`, `challenger_m1_1/stress_test_parser.py`, `reviewer_m1_1/handoff.md`, `reviewer_m1_2/handoff.md`, `tests/test_parser.py`, `tests/test_requirements.py`, `tests/test_e2e.py`
- **Key findings**:
  1. `parse_single_message(None)` crashes with `TypeError` due to unguarded `re.split` on `raw_message`.
  2. Negative hours (`-5h`, `(-5h)`, `-8h to -4h`) evade regex and get paid 5.0h with `status="VALID"`.
  3. Clock hours > 24 (`25h-30h`) evade boundary check because `elapsed = 5.0 <= 24`, marked `VALID`.
  4. Ambiguous shifts (`Ca ngày đêm`, `Ca đêm ngày`) match `ngày` first and silently validate as `VALID`.
  5. Unconditional double-newline splitting in `split_messages` shreds messages with internal blank lines into fragments.
  6. Unlimited digits in meal parsing crash on `int(string)` with Python 3.11 `ValueError` limit (4300 digits).
  7. `TÊN\s*[\s]` lookahead splits messages on `TÊN DỰ ÁN:` or `TÊN XƯỞNG:` lines.
- **Unexplored areas**: None. All 6 challenger issues and reviewer lookahead issues are fully diagnosed, remediated, and empirically verified.

## Key Decisions Made
- Designed field-aware sub-block continuation in `split_messages` preserving messages with internal blank lines while maintaining corrupt line isolation.
- Bound meal digit strings to `[:4]` to eliminate CVE-2020-10735 `ValueError` crashes.
- Added negative lookahead to `TÊN|TEN` to prevent collisions with `TÊN DỰ ÁN` and `TÊN XƯỞNG`.
- Bounded clock hours on 24-hour clock and added negative hour detection.
- Empirically verified proposed parser passes all 538 stress tests and all 199 existing tests.

## Artifact Index
- `DISPATCH.md` — Initial dispatch instructions
- `BRIEFING.md` — Persistent awareness and state
- `progress.md` — Liveness and step tracking
- `proposed_core_parser.py` — Drop-in replacement implementation of `core/parser.py`
- `parser_remediation.patch` — Unified diff patch applicable cleanly via `patch` utility
- `run_stress_on_proposed.py` — 538-case adversarial stress runner
- `run_existing_tests_on_proposed.py` — Full 199 pytest regression runner
- `report.md` — Comprehensive remediation analysis report
- `handoff.md` — Self-contained 5-component handoff report
