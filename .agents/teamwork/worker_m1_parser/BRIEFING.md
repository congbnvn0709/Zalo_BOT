# BRIEFING — 2026-10-26T08:12:00Z

## Mission
Implement Milestone 1: Robust Attendance Message Parser with Pydantic models, Vietnamese normalization, break calculation, rate-tier hour allocation, and comprehensive unit test suite.

## 🔒 My Identity
- Archetype: worker
- Roles: implementer, qa, specialist
- Working directory: /Users/congcm/CODE/Vibe_Code/Zalo_BOT/.agents/teamwork/worker_m1_parser/
- Original parent: 9d3ef6c5-77d3-42b3-adab-c1e95bee7211
- Milestone: Milestone 1 (Attendance Message Parser)

## 🔒 Key Constraints
- Own exclusively: models/__init__.py, models/attendance.py, core/__init__.py, core/parser.py, tests/test_parser.py
- DO NOT hardcode test results or create facade implementations.
- Vietnamese name normalization: trim whitespace, title case, accents preserved.
- Date parser supporting DD/MM, DD-MM, YYYY-MM-DD, DD/MM/YYYY, default year 2026, Sunday detection.
- Break deduction: automatic 1h break deduction for shifts >= 8.5 elapsed hours; explicit brackets take precedence.
- Rate allocation: Weekday/Sat Day (<=8h hcn_100, >8h tcn_150), Weekday/Sat Night (<=8h hcd_130, >8h tcd_195), Sunday Day (all sunday_day_200), Sunday Night (all sunday_night_260).
- Non-crashing validation: VALID, WARNING, ERROR statuses.
- Keep tests comprehensive and passing.

## Current Parent
- Conversation ID: 9d3ef6c5-77d3-42b3-adab-c1e95bee7211
- Updated: 2026-10-26T08:12:00Z

## Task Summary
- **What to build**: Attendance Pydantic models, parser logic, unit tests.
- **Success criteria**: 100% test pass on tests/test_parser.py covering standard format, multi-message batching, overtime, night shifts, Sunday shifts, break deduction, various date formats, missing fields, malformed lines.
- **Interface contracts**: PROJECT.md, survey_spec_miner_parser/report.md.
- **Code layout**: models/, core/, tests/.

## Change Tracker
- **Files modified**:
  * `models/__init__.py`: Package export for WorkHours, AttendanceRecord, ParseSummary, ParseResponse.
  * `models/attendance.py`: Pydantic v2 schemas for WorkHours (6 rates + total), AttendanceRecord, ParseSummary, ParseResponse.
  * `core/__init__.py`: Package exports for AttendanceParser and convenience functions.
  * `core/parser.py`: Full AttendanceParser engine with Vietnamese normalization, multi-format date parser, break calculator, rate allocator, meal mapper, and batch segmenter.
  * `tests/__init__.py`: Package initialization for test suite.
  * `tests/test_parser.py`: 73 comprehensive unit tests covering all features, edge cases, boundaries, and acceptance criteria.
- **Build status**: PASS (73/73 tests pass in pytest).
- **Pending issues**: None.

## Quality Status
- **Build/test result**: 73 passed in 0.10s via `.venv/bin/pytest tests/test_parser.py -v`.
- **Lint status**: 0 compilation/syntax errors via `python3 -m py_compile`.
- **Tests added/modified**: 73 tests added in `tests/test_parser.py`.

## Loaded Skills
- None explicitly assigned. Implementer & QA engineering rigor maintained.

## Key Decisions Made
- `AttendanceRecord` provides both `employee_name` (uppercase standard for Excel matching) and `normalized_name` (title case with preserved accents), satisfying both Acceptance Criteria and the dispatch directive.
- `WorkHours` rate calculations correctly map weekday vs Sunday across the 6 payroll tiers.
- Non-crashing architecture captures syntax and semantic errors in `status = ERROR` and `messages = [...]`, preventing unhandled exceptions during large batch processing.

## Artifact Index
- DISPATCH.md — Dispatch instructions from orchestrator
- BRIEFING.md — Working memory and identity
- progress.md — Liveness heartbeat and status log
- handoff.md — 5-Component completion handoff report
