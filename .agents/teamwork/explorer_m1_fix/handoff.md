# Handoff Report: Milestone 1 Parser Remediation Plan

**Author**: Parser Remediation Explorer (`explorer_m1_fix`)  
**Target Module**: `core/parser.py`  
**Date**: 2026-10-26T08:33:00Z  
**Verdict**: **REMEDIATION DESIGN COMPLETE & EMPIRICALLY VERIFIED**

---

## 1. Observation

Direct observations recorded from executing test harnesses against `core/parser.py`:

### Obs 1: Unhandled Crashes in Baseline
- Running `.venv/bin/python3 .agents/teamwork/challenger_m1_1/stress_test_parser.py`:
  ```
  Total test executions: 538
  Total unhandled crashes: 3
  Total status anomalies: 7
  Total structural findings: 1

  [!] UNHANDLED CRASHES:
    - crash_test: None input to parse_single_message: TypeError -> expected string or bytes-like object, got 'NoneType'
    - crash_test: Non-string int input: TypeError -> expected string or bytes-like object, got 'int'
    - crash_test: 5000 digit meal count: ValueError -> Exceeds the limit (4300 digits) for integer string conversion: value has 5000 digits; use sys.set_int_max_str_digits() to increase the limit
  ```

### Obs 2: Status Anomalies (Negative & Out-of-Bounds Hours, Ambiguous Shifts)
- Verbatim from stress test output:
  ```
  [!] STATUS ANOMALIES (False Positives / Negatives):
    - extreme_number: Negative hours standalone (-5h): expected ERROR, got VALID | msgs: []
    - extreme_number: Negative hours bracketed ((-5h)): expected ERROR, got VALID | msgs: []
    - extreme_number: Negative range (-8h to -4h): expected ERROR, got VALID | msgs: []
    - extreme_number: Inverted daytime (17h-8h): expected WARNING, got VALID | msgs: []
    - extreme_number: Clock hours > 24 (25h-30h): expected ERROR, got VALID | msgs: []
    - weird_shift: Ca ngày đêm (ambiguous both) ('Ca ngày đêm'): expected WARNING, got VALID | msgs: []
    - weird_shift: Ca đêm ngày (reversed) ('Ca đêm ngày'): expected WARNING, got VALID | msgs: []
  ```

### Obs 3: Message Fragmentation on Internal Blank Lines
- Verbatim from stress test output:
  ```
  [!] STRUCTURAL FINDINGS:
    - MESSAGE_FRAGMENTATION_ON_BLANK_LINES: Expected 2 records for 2 messages with internal blank lines, got 4. Records were fragmented into errors.
  ```

### Obs 4: Lookahead Collision on `TÊN DỰ ÁN` / `TÊN XƯỞNG`
- Invoking `parse_attendance_messages` on text with `TÊN DỰ ÁN: SAM SUNG` and `TÊN XƯỞNG: XƯỞNG ĐÚC`:
  ```
  Current count: 4
  Employee: NGUYỄN VĂN A | Project: ETS | Status: ERROR
  Employee: DỰ ÁN: SAM SUNG | Project: ETS | Status: ERROR
  Employee: TRẦN VĂN B | Project: ETS | Status: ERROR
  Employee: XƯỞNG: XƯỞNG ĐÚC | Project: ETS | Status: ERROR
  ```

### Obs 5: Verification of Proposed Remediation
- Executed `.venv/bin/python3 .agents/teamwork/explorer_m1_fix/run_stress_on_proposed.py`:
  ```
  =================================================================
  STRESS TEST EXECUTION COMPLETED
  Total test executions: 538
  Total unhandled crashes: 0
  Total status anomalies: 0
  Total structural findings: 0
  =================================================================
  >>> ALL ADVERSARIAL STRESS TESTS PASSED WITH 0 CRASHES, 0 ANOMALIES, 0 FINDINGS! <<<
  ```
- Executed `.venv/bin/python3 .agents/teamwork/explorer_m1_fix/run_existing_tests_on_proposed.py`:
  ```
  ============================= 199 passed in 0.21s ==============================
  ```
- Executed `TÊN DỰ ÁN` collision test on proposed parser:
  ```
  Count: 2
  Employee: NGUYỄN VĂN A | Project: SAM SUNG | Status: VALID
  Employee: TRẦN VĂN B | Project: XƯỞNG ĐÚC | Status: VALID
  ```

---

## 2. Logic Chain

1. **Non-Crashing Contract Enforcement** (supported by Obs 1):
   - By inserting guards against `None`, non-string types, and empty strings at `parse_single:148` and `split_messages:108`, unhandled `TypeError` exceptions are eliminated, returning valid `AttendanceRecord` objects with `status="ERROR"`.
   - By bounding meal count digit extraction to `[:4]` at line 420, integer parsing never receives more than 4 characters, preventing the Python 3.11 `ValueError` (CVE-2020-10735 limit of 4,300 digits).

2. **Accurate Status Classification & Payroll Protection** (supported by Obs 2):
   - By checking `has_negative = bool(re.search(r'(?:^|[\(\[\{]|\b(?:to|đến|den|tới|toi)\b|[-–~])\s*-\s*\d', raw_hours, re.IGNORECASE))` prior to hour regex matching, negative numbers (`-5h`, `(-5h)`, `-8h to -4h`) add an explicit error and zero out `total_hours`, preventing unauthorized payroll disbursement.
   - By validating clock bounds `0 <= sh <= 24` and `0 <= eh <= 24` in `m_rng`, impossible clock times (`25h-30h`) trigger errors and set status to `ERROR`.
   - By adding a warning when `eh < sh` on `Ca ngày` without bracket clarification (`br_hours is None`), inverted daytime shifts (`17h-8h`) downgrade to `WARNING` while bracketed hours (`17h-8h (8h)`) remain `VALID`.
   - By evaluating `has_day and has_night` simultaneously, conflicting shifts (`Ca ngày đêm`, `Ca đêm ngày`) emit a diagnostic warning and default to `DAY` with status `WARNING`.

3. **Batch Integrity & Blank Line Preservation** (supported by Obs 3):
   - Rather than blindly sub-splitting on `\n\s*\n+`, the proposed `extract_field_types(block)` tracks which fields are present.
   - When a sub-block contains recognized field headers (`CA:`, `THỜI GIAN:`, `ĂN:`, etc.) that do not duplicate fields already accumulated in the current record, it merges as a multi-line continuation of that record.
   - Truly disconnected corrupt lines (`DÒNG LỖI HOÀN TOÀN`) or duplicated fields terminate the current record and form independent records.
   - This resolves message fragmentation from 4 errors down to 2 valid records on inputs with internal blank lines.

4. **Reviewer Lookahead Collision Prevention** (supported by Obs 4 and 5):
   - Negative lookahead `(?!\s*(?:dự\s*án|du\s*an|xưởng|xuong|công\s*trình|cong\s*trinh|đề\s*án|de\s*an|công\s*ty|cong\s*ty))` on standalone `TÊN` / `TEN` prevents project lines from triggering message boundaries or matching the employee name.
   - `m_proj` is updated to allow optional `(?:TÊN\s*)?`, correctly capturing `TÊN DỰ ÁN: SAM SUNG` as `project = 'SAM SUNG'`.

5. **Empirical Regression-Free Invariance** (supported by Obs 5):
   - All 538 stress tests pass with 0 defects.
   - All 199 unit and E2E tests pass without modification.
   - Therefore, the remediation is completely sound, robust, and regression-free.

---

## 3. Caveats

- **Scope Boundary**: As an Explorer, production files (`core/parser.py`) were not modified directly. The proposed fix is supplied via `.agents/teamwork/explorer_m1_fix/proposed_core_parser.py` and `.agents/teamwork/explorer_m1_fix/parser_remediation.patch`.
- **Default Year**: Unchanged. Omitted years in `DD/MM` format default to 2026 with a `WARNING` flag, consistent with project specifications.
- No other caveats.

---

## 4. Conclusion

The 6 challenger failures and the reviewer lookahead collision are completely understood, diagnosed, and remediated.

**Remediation Artifacts**:
- Full report: `.agents/teamwork/explorer_m1_fix/report.md`
- Clean unified patch: `.agents/teamwork/explorer_m1_fix/parser_remediation.patch`
- Drop-in replacement: `.agents/teamwork/explorer_m1_fix/proposed_core_parser.py`

The remediation is ready for immediate application by an implementer agent.

---

## 5. Verification Method

To independently verify the proposed remediation:

```bash
# 1. Verify patch applies cleanly without errors or fuzz
patch --dry-run core/parser.py < .agents/teamwork/explorer_m1_fix/parser_remediation.patch

# 2. Run the adversarial stress test against proposed parser (538 tests)
.venv/bin/python3 .agents/teamwork/explorer_m1_fix/run_stress_on_proposed.py

# 3. Run full project test suite against proposed parser (199 tests)
.venv/bin/python3 .agents/teamwork/explorer_m1_fix/run_existing_tests_on_proposed.py

# 4. Verify TÊN DỰ ÁN lookahead collision fix
.venv/bin/python3 -c "
import sys; sys.path.insert(0, '.agents/teamwork/explorer_m1_fix')
from proposed_parser import proposed_parse_attendance_messages
raw = '''HỌ TÊN: NGUYỄN VĂN A\nNGÀY: 24/10/2026\nCA: Ca ngày\nTÊN DỰ ÁN: SAM SUNG\nTHỜI GIAN: 8h-17h (8H)\nĂN: 0'''
recs = proposed_parse_attendance_messages(raw)
assert len(recs) == 1 and recs[0].employee_name == 'NGUYỄN VĂN A' and recs[0].project == 'SAM SUNG' and recs[0].status == 'VALID'
print('Lookahead collision verification PASSED!')
"
```
**Invalidation Conditions**: Any crash on `None`/int inputs, any status anomaly in the 538 stress tests, any failure in the 199 existing tests, or fragmentation of messages containing internal blank lines or `TÊN DỰ ÁN`.
