# Milestone 4 Final System Acceptance Review Report

**Reviewer**: `reviewer_m4_1`  
**Roles**: Reviewer, Adversarial Critic  
**Date**: 2026-10-26  
**Final Verdict**: **APPROVE**  
**Integrity Audit**: **PASS (NO INTEGRITY VIOLATIONS DETECTED)**  

---

## 1. Observation

### 1.1 Fresh Verification Command Executions
1. **Pytest Full Test Suite**:
   - Command: `.venv/bin/pytest tests/ -v`
   - Result: Exit code `0`
   - Output summary:
     ```
     ======================== 268 passed, 1 warning in 0.95s ========================
     ```
   - Total test cases run: 268 passed across `test_requirements.py`, `test_parser.py`, `test_excel.py`, `test_api.py`, and `test_e2e.py`.

2. **Standalone E2E Verification Runner**:
   - Command: `.venv/bin/python3 tests/verify_e2e.py`
   - Result: Exit code `0`
   - Output verbatim snippet:
     ```
     ================================================================================
      ZALO ATTENDANCE WEB APP & EXCEL INTEGRATOR: E2E VERIFICATION SUITE
     ================================================================================
     Discovered 126 automated test cases across Tiers 1-4.
     --------------------------------------------------------------------------------
     --- [ACCEPTANCE CRITERIA VERIFICATION CHECKLIST] ---
       [ PASS ]  AC1: Parser extracts HOÀNG ĐẮC PHÚ (24/10, Ca ngày, 8h, meal 0)
       [ PASS ]  AC2: Day/Night Shift & Overtime (HCN, TCN, HCĐ, TCĐ, CN) distinction
       [ PASS ]  AC3: Fault-tolerant batch parsing (VALID, WARNING, ERROR) with zero crashes
       [ PASS ]  AC4: Excel cell assignment to K24=8 (HCN) and K30=0 (Suất ăn) for HOÀNG ĐẮC PHÚ
       [ PASS ]  AC5: Excel formulas in AK..AR (=SUM) and row 2 grand totals preserved verbatim
       [ PASS ]  AC6: openpyxl data_only=False and fullCalcOnLoad enabled
       [ PASS ]  AC7: Web UI schema contracts (/api/parse, /api/export-excel, /api/template/info)
       [ PASS ]  AC8: One-command launcher run.py environment bootstrapping specification
     --------------------------------------------------------------------------------
      Tier 1   | Feature Coverage (F01..F11)            | >= 55    | 55       | PASS
      Tier 2   | Boundary & Corner Cases (F01..F11)     | >= 55    | 55       | PASS
      Tier 3   | Cross-Feature Pairwise Interactions    | >= 11    | 11       | PASS
      Tier 4   | Real-World Workload Scenarios          | >= 5     | 5        | PASS
     --------------------------------------------------------------------------------
      TOTAL    | Comprehensive Test Suite               | >= 126   | 126      | PASS
     ================================================================================
     Execution Statistics:
       - Total Run   : 126
       - Passed      : 126
       - Failed      : 0
       - Errors      : 0
       - Elapsed Time: 0.205 seconds
     >>> OVERALL VERIFICATION: SUCCESSFUL (ALL CRITERIA MET) <<<
     ```

3. **Launcher CLI Interface**:
   - Command: `.venv/bin/python3 run.py --help`
   - Result: Exit code `0`
   - Flags supported: `--host`, `--port`, `--no-browser`, `--reload`.

4. **Independent Adversarial Stress-Tests**:
   - Executed five adversarial challenge scenarios:
     - Scenario A: Multi-line message with internal blank lines -> correctly merged into single record without fragmenting fields.
     - Scenario B: Midnight-crossing shift ranges (`22h-6h` and `20h-4h`) -> accurately computed to 8.0h.
     - Scenario C: 11 meal count text variants (`Có`, `co`, `1`, `v`, `✓`, `Không`, `ko`, `k`, `tự túc`, `không ăn`, `2 suất`) -> 100% matched to expected integers 0, 1, or 2.
     - Scenario D: High-density batch throughput: 200 records parsed in 0.010s (~19,980 records/sec).
     - Scenario E: High-volume Excel write: 50 records applied in 0.011s with 100 cells written and zero formula corruption.

### 1.2 Direct Code Inspections
- **`core/parser.py`**:
  - Line 14: `normalize_vietnamese_name` performs Unicode NFC normalization, phone number stripping (`[-–]\s*\d{9,11}`), parenthetical notes (`\(.*?\)`), and list index prefixes.
  - Line 46: `calculate_work_hours` implements allocation rules:
    - Day non-Sunday: `hcn_100 = min(total_hours, 8.0)`, `tcn_150 = max(0.0, total_hours - 8.0)`
    - Night non-Sunday: `hcd_130 = min(total_hours, 8.0)`, `tcd_195 = max(0.0, total_hours - 8.0)`
    - Sunday Day: `sunday_day_200 = total_hours`
    - Sunday Night: `sunday_night_260 = total_hours`
  - Lines 134-202: `split_messages` uses regex header lookahead (`header_re`) and continuation tracking (`extract_field_types`).
  - Lines 525-528: `digit_str = m_dig.group(1)[:4]` prevents integer conversion denial of service (CVE-2020-10735).
- **`core/excel_integrator.py`**:
  - Line 99 & 107: `openpyxl.load_workbook(..., data_only=False)`.
  - Line 110 & 458: `wb.calculation.fullCalcOnLoad = True`.
  - Lines 192-289: `match_employee` implements a 4-tier matching algorithm:
    - Tier 1: Exact normalized match (raw score 1.0, cleaned 0.95)
    - Tier 2: Unaccented match (raw score 0.95, cleaned 0.92)
    - Tier 3: Token containment & word-boundary substring match (score 0.90)
    - Tier 4: `difflib.SequenceMatcher` fuzzy ratio >= 0.85
  - Lines 295-371: `resolve_date_column` resolves ISO (`YYYY-MM-DD`), `DD/MM`, `DD-MM`, `DD/MM/YYYY`, and day integers into column indices `6..36` (F..AJ).
  - Lines 429-454: Cell values written are strictly coerced to numeric types (`int` or `float`, `data_type='n'`). Offsets 0..6 correspond to HCN 100%, TCN 150%, HCĐ 130%, TCĐ 195%, Sunday Day 200%, Sunday Night 260%, and Meal count.
  - Summary columns `AK..AR` (cols 37..44) and header row 2 are never overwritten.
- **`core/template_generator.py`**:
  - Injects horizontal employee sum formulas: `AK{r}`: `=SUM(F{r}:AJ{r})` through `AQ{r}`: `=SUM(F{r+6}:AJ{r+6})`.
  - Injects `AR{r}`: `=SUM(AK{r}:AP{r})` strictly excluding `AQ` (Suất ăn).
  - Injects row 2 grand totals: `AK2`: `=SUM(AK3,AK10,AK17,AK24)` through `AR2`.
- **`run.py`**:
  - Validates Python version (`sys.version_info >= (3, 9)`).
  - `find_free_port` probes starting at port 8000 and tests bind availability up to 8080.
- **Integrity Searches**:
  - Grep for `HOÀNG ĐẮC PHÚ` in `core/` returned only docstrings/comments and variable name examples.
  - Grep for `K24` or `K30` in `core/` returned 0 results. Dynamic resolution is 100% genuine.

---

## 2. Logic Chain

1. **AC1 Verification**:
   - Observation 1.1.2 & Observation 1.2 demonstrate that parsing the reference message extracts `HOÀNG ĐẮC PHÚ`, resolves date `24/10` to `2026-10-24` (day 24), shift to `DAY`, hours to `hcn_100=8.0`, and meal count to `0`.
   - Therefore, AC1 is completely satisfied.

2. **AC2 Verification**:
   - Observation 1.1.4 and unit tests in `core/parser.py` demonstrate that hours allocation partitions hours according to all rate categories (HCN 100%, TCN 150%, HCĐ 130%, TCĐ 195%, Sunday 200%, Sunday 260%).
   - Therefore, AC2 is completely satisfied.

3. **AC3 Verification**:
   - Observation 1.1.4 and Tier 2 boundary tests demonstrate that corrupted inputs, missing dates/names, negative values, and non-attendance chatter are classified with diagnostic statuses (`VALID`, `WARNING`, `ERROR`) without raising unhandled exceptions or crashing the runtime.
   - Therefore, AC3 is completely satisfied.

4. **AC4 Verification**:
   - Observation 1.1.2 & direct script inspection demonstrate that applying `HOÀNG ĐẮC PHÚ` on 24/10 matches employee row 24, resolves column 11 (K), and writes numeric `8` into `K24` (`data_type='n'`) and numeric `0` into `K30` (`data_type='n'`).
   - Therefore, AC4 is completely satisfied.

5. **AC5 & AC6 Verification**:
   - Inspection of saved workbooks loaded with `data_only=False` confirms that formulas `=SUM(...)` in columns `AK..AR` (rows 3, 10, 17, 24) and row 2 grand totals are preserved verbatim as formula strings.
   - `wb.calculation.fullCalcOnLoad` is configured to `True`.
   - Therefore, AC5 and AC6 are completely satisfied.

6. **AC7 Verification**:
   - API contract tests via `TestClient` confirmed `/api/template/info`, `/api/parse`, `/api/export-excel`, and `/api/download/{token}` conform to Pydantic v2 schemas and handle round-trip export correctly.
   - Therefore, AC7 is completely satisfied.

7. **AC8 Verification**:
   - `run.py` successfully parses command-line parameters, validates dependencies, checks Python version, and automatically resolves port collisions when port 8000 is occupied.
   - Therefore, AC8 is completely satisfied.

8. **Integrity Verification**:
   - Independent search confirmed no hardcoded coordinates, no facade implementations, and no bypasses. Tests in `tests/verify_e2e.py` execute genuine assertions.
   - Therefore, there are no integrity violations.

---

## 3. Caveats

- **Network Dependency for Frontend CDN**: The HTML file uses Tailwind CSS from CDN (`https://cdn.tailwindcss.com`). However, an embedded offline fallback stylesheet (`static/css/app.css`) is provided to maintain clean styling in air-gapped/offline local environments.
- **Starlette TestClient Deprecation Warning**: A minor warning `StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated` was emitted during tests. This is purely upstream informational feedback in FastAPI/Starlette and does not impact functionality or test results.
- **No further caveats**.

---

## 4. Conclusion

All 8 Acceptance Criteria (AC1 through AC8) are fully met with genuine, non-hardcoded implementations and verified by 268 automated tests (100% pass rate) plus standalone verification and adversarial stress-testing.

**Final Verdict**: **APPROVE**

---

## 5. Verification Method

To independently reproduce this verification:

```bash
# 1. Activate environment and run full pytest suite (268 tests)
.venv/bin/pytest tests/ -v

# 2. Run standalone 4-tier E2E verification reporter (126 tests)
.venv/bin/python3 tests/verify_e2e.py

# 3. Test launcher interface
.venv/bin/python3 run.py --help

# 4. Spot check cell and formula preservation in Python REPL:
.venv/bin/python3 -c "
import openpyxl, io
from core.excel_integrator import ExcelIntegrator
from core.parser import parse_single_message
rec = parse_single_message('HỌ TÊN: HOÀNG ĐẮC PHÚ\nNGÀY: 24/10\nCA: Ca ngày\nTHỜI GIAN: 8h-17h (8H)\nĂN: 0')
integ = ExcelIntegrator()
buf = io.BytesIO()
integ.apply_records([rec], output_path=buf)
buf.seek(0)
wb = openpyxl.load_workbook(buf, data_only=False)
ws = wb.active
assert ws['K24'].value == 8 and ws['K24'].data_type == 'n'
assert ws['K30'].value == 0 and ws['K30'].data_type == 'n'
assert ws['AK24'].value == '=SUM(F24:AJ24)'
assert wb.calculation.fullCalcOnLoad is True
print('Independent verification successful.')
"
```

**Invalidation conditions**:
- Any regression causing `pytest tests/` to fail.
- Any change that writes string values (`data_type='s'`) instead of numeric types to attendance cells.
- Any change that overwrites formulas in columns `AK..AR` or row 2.
- Any change that removes `wb.calculation.fullCalcOnLoad = True`.
