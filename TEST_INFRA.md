# E2E Test Infra: Zalo Attendance Web App & Excel Integrator

## Test Philosophy
- Opaque-box, requirement-driven. Derived from `ORIGINAL_REQUEST.md` and user-facing specifications, not internal implementation details.
- Systematic 4-tier methodology:
  1. Category-Partition (Tier 1: Feature coverage >= 5 per feature)
  2. Boundary Value Analysis (Tier 2: Boundary & Corner cases >= 5 per feature)
  3. Pairwise Combinatorial Testing (Tier 3: Cross-feature interactions)
  4. Real-World Workload Testing (Tier 4: Realistic factory shift scenarios)

## Feature Inventory
| # | Feature | Source | Tier 1 | Tier 2 | Tier 3 |
|---|---------|--------|:------:|:------:|:------:|
| 1 | F01: Vietnamese Name Normalization | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ |
| 2 | F02: Date Parsing & Sunday Resolution | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ |
| 3 | F03: Shift & Hours Breakdown (6 metrics) | ORIGINAL_REQUEST §R1, AC1, AC2 | 5 | 5 | ✓ |
| 4 | F04: Meal Detection (0, 1, text) | ORIGINAL_REQUEST §R1, AC1 | 5 | 5 | ✓ |
| 5 | F05: Batch Parsing & Error Tolerance | ORIGINAL_REQUEST §R1, AC3 | 5 | 5 | ✓ |
| 6 | F06: Excel Template Generation & Styling | ORIGINAL_REQUEST §R3, AC4 | 5 | 5 | ✓ |
| 7 | F07: Coordinate Mapping & Fuzzy Matching | ORIGINAL_REQUEST §R3, AC4 | 5 | 5 | ✓ |
| 8 | F08: Excel Write & Formula Preservation | ORIGINAL_REQUEST §R3, AC4, AC5 | 5 | 5 | ✓ |
| 9 | F09: REST API Endpoints | ORIGINAL_REQUEST §R2 | 5 | 5 | ✓ |
| 10 | F10: Web Dashboard UI / Flow | ORIGINAL_REQUEST §R2, AC7, AC8 | 5 | 5 | ✓ |
| 11 | F11: Bootstrap Launcher & Port Handling | ORIGINAL_REQUEST §R2 | 5 | 5 | ✓ |

## Test Architecture
- Test runner: `pytest -v tests/` or `python3 -m unittest discover tests/`
- Verification script: `python3 tests/verify_e2e.py`
- Test cases layout:
  - `tests/test_parser.py`: Unit and boundary tests for parser
  - `tests/test_excel.py`: Unit and formula integrity tests for Excel engine
  - `tests/test_api.py`: FastAPI endpoints and integration tests
  - `tests/test_e2e.py`: End-to-end pipeline verification (Text -> Web API -> Excel generation -> Cell and Formula validation)

## Real-World Application Scenarios (Tier 4)
| # | Scenario | Features Exercised | Complexity |
|---|----------|--------------------|------------|
| 1 | Acceptance Criteria standard batch (HOÀNG ĐẮC PHÚ on 24/10 + other shifts) | F01, F02, F03, F04, F07, F08 | High (Acceptance test) |
| 2 | Multi-employee mixed shifts (Day, Night, Sunday, Overtime) | F01..F08 | High |
| 3 | Messy raw batch with malformed entries, missing colons, typos, trailing spaces | F01, F04, F05, F09, F10 | High |
| 4 | Full pipeline Web UI / API upload custom template & export | F06, F07, F08, F09, F10 | High |
| 5 | Stress batch with 30+ employees over full month dates | F03, F07, F08 | High |

## Coverage Thresholds
- Tier 1: >= 55 test cases (5 per feature across 11 features)
- Tier 2: >= 55 boundary & corner test cases
- Tier 3: >= 11 cross-feature interaction test cases
- Tier 4: >= 5 realistic end-to-end workload test cases
- **Total Minimum Target**: >= 126 test cases
