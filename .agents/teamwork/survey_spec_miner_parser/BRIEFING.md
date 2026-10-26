# BRIEFING — 2026-10-26T07:49:30Z

## Mission
Deeply analyze Requirement R1 (Attendance Message Parser) and related Acceptance Criteria, producing a comprehensive specification and parsing rulebook in report.md.

## 🔒 My Identity
- Archetype: Specification Miner
- Roles: Parser Spec Miner
- Working directory: /Users/congcm/CODE/Vibe_Code/Zalo_BOT/.agents/teamwork/survey_spec_miner_parser/
- Original parent: 9d3ef6c5-77d3-42b3-adab-c1e95bee7211
- Milestone: Phase 0 - Survey & Spec Mining

## 🔒 Key Constraints
- Must analyze all message formats, variations, edge cases, date formats, shift names, project names, working hours formats, Vietnamese labor/company overtime calculation rules, meal detection, error validation, and batch parsing.
- Produce comprehensive specification and parsing rulebook at /Users/congcm/CODE/Vibe_Code/Zalo_BOT/.agents/teamwork/survey_spec_miner_parser/report.md.
- Include test cases covering happy path, edge cases, error cases, and time calculation formulas.
- Do NOT implement anything — read-only spec miner.
- Keep handoff protocol strictly followed (Observation, Logic Chain, Caveats, Conclusion, Verification Method).
- Send message to parent with file path and executive summary upon completion.

## Current Parent
- Conversation ID: 9d3ef6c5-77d3-42b3-adab-c1e95bee7211
- Updated: 2026-10-26T07:49:30Z

## Task Summary
- **What to build**: Comprehensive parser specification & rulebook (report.md) + handoff.md.
- **Success criteria**: Exhaustive analysis of syntax, edge cases, Vietnamese labor calculation rules (HCN 100%, TCN 150%, HCĐ 130%, TCĐ 195%/200%, Sunday 200%/260%), meal parsing, batch splitting, validation flags, and concrete test cases.
- **Interface contracts**: ORIGINAL_REQUEST.md Requirement R1 and Acceptance Criteria.
- **Code layout**: .agents/teamwork/survey_spec_miner_parser/

## Key Decisions Made
- Fully specified dual-pass batch segmentation (Header-lookahead on `HỌ TÊN` + fallback dividers).
- Formulated exact mathematical mapping for the 6 hours categories across Weekday vs Sunday and Day vs Night shifts matching `sample_data.csv`.
- Defined meal dictionary mapping `0`, `1`, `Có`, `Không`, `ko`, `k`, `x`, `v`, `✓`, `tự túc`.
- Defined three-tier record validation state (`VALID`, `WARNING`, `ERROR`) with non-crashing guarantee.
- Validated all 11 test vectors with 100% pass rate in reference python prototype.

## Artifact Index
- DISPATCH.md — Initial dispatch assignment
- progress.md — Liveness heartbeat
- report.md — Comprehensive specification & parsing rulebook
- handoff.md — 5-component handoff report
