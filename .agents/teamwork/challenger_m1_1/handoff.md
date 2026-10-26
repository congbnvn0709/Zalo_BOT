# Adversarial Challenge Report — Milestone 1 (Attendance Message Parser)

**Verdict**: **REJECT**  
**Agent**: Parser Challenger 1 (`challenger_m1_1`)  
**Target Module**: `core/parser.py`  
**Date**: 2026-10-26T08:22:00Z  

---

## 1. Observation

A stress harness (`.agents/teamwork/challenger_m1_1/stress_test_parser.py`) was constructed and executed against `core/parser.py`, testing 538 distinct test cases across random Unicode fuzzing, extreme values, shift strings, batch segmentation, and unhandled exception conditions.

The following direct observations were recorded:

### Obs 1: `parse_single_message(None)` crashes with unhandled `TypeError`
- **Location**: `core/parser.py:163`
- **Invocation**:
  ```python
  from core.parser import parse_single_message
  parse_single_message(None)
  ```
- **Verbatim Error**:
  ```
  TypeError: expected string or bytes-like object, got 'NoneType'
  File "core/parser.py", line 163, in parse_single:
    raw_lines = re.split(..., raw_message, flags=re.IGNORECASE)
  ```
- **Specification Conflict**: `core/parser.py:147` docstring claims: *"Never raises exceptions; captures errors and warnings in record.messages"*.

### Obs 2: Negative working hours silently converted to positive paid hours with status `VALID`
- **Location**: `core/parser.py:334`, `379`
- **Invocation**:
  ```python
  from core.parser import parse_single_message
  raw = "HỌ TÊN: A\nNGÀY: 24/10/2026\nCA: Ca ngày\nTHỜI GIAN: -5h\nĂN: 0"
  r = parse_single_message(raw)
  print(r.status, r.hours.total_hours, r.hours.hcn_100, r.messages)
  ```
- **Verbatim Result**:
  ```
  VALID 5.0 5.0 []
  ```
- **Details**: Regex `r'(\d+(?:[\.,]\d+)?)\s*(?:h|tiếng|g|giờ)'` does not account for the leading negative sign `-`, matching `5h` and paying 5 hours of regular daytime work (`hcn_100 = 5.0`) with zero warnings or errors. Same behavior observed on `THỜI GIAN: (-5h)` and `THỜI GIAN: -8h to -4h`.

### Obs 3: Messages with internal blank lines are fragmented into broken `ERROR` records
- **Location**: `core/parser.py:126-132`
- **Invocation**:
  ```python
  from core.parser import parse_attendance_messages
  msg = "HỌ TÊN: A\nNGÀY: 24/10/2026\n\nCA: Ca ngày\nTHỜI GIAN: 8h-17h (8H)\nĂN: 0"
  records = parse_attendance_messages(msg)
  print(len(records), [r.status for r in records])
  ```
- **Verbatim Result**:
  ```
  2 ['ERROR', 'ERROR']
  Record 0 messages: ['Thiếu trường Thời gian làm việc', 'Thiếu trường Ca làm việc', 'Thiếu thông tin suất ăn, mặc định 0']
  Record 1 messages: ['Thiếu trường Họ và tên', 'Thiếu trường Ngày chấm công']
  ```
- **Details**: `split_messages` contains sub-splitting logic:
  ```python
  sub_blocks = [b.strip() for b in re.split(r'\n\s*\n+', part) if b.strip()]
  if len(sub_blocks) > 1:
      final_chunks.append(sub_blocks[0])
      for sb in sub_blocks[1:]:
          final_chunks.append(sb)
  ```
  When a user pastes a message containing a blank line between lines (common in Zalo chat), the single valid attendance message is broken into two half-messages, both marked as `ERROR`.

### Obs 4: Impossible clock hours (>24h of clock time) treated as `VALID`
- **Location**: `core/parser.py:344-366`
- **Invocation**:
  ```python
  from core.parser import parse_single_message
  raw = "HỌ TÊN: A\nNGÀY: 24/10/2026\nCA: Ca ngày\nTHỜI GIAN: 25h-30h\nĂN: 0"
  r = parse_single_message(raw)
  print(r.status, r.hours.total_hours, r.messages)
  ```
- **Verbatim Result**:
  ```
  VALID 5.0 []
  ```
- **Details**: Clock hours 25:00 and 30:00 do not exist on the 24-hour clock. `core/parser.py` matches `sh=25, eh=30`, computes `eh - sh = 5.0` hours, and validates the record without error or warning.

### Obs 5: Ambiguous conflicting shift strings silently resolved without warning
- **Location**: `core/parser.py:311-315`
- **Invocation**:
  ```python
  from core.parser import parse_single_message
  raw = "HỌ TÊN: A\nNGÀY: 24/10/2026\nCA: Ca ngày đêm\nTHỜI GIAN: 8h-17h (8H)\nĂN: 0"
  r = parse_single_message(raw)
  print(r.status, r.shift_type, r.messages)
  ```
- **Verbatim Result**:
  ```
  VALID DAY []
  ```
- **Details**: `Ca ngày đêm` contains both `ngày` and `đêm`. Because `ngày` is evaluated first in `if any(...)`, it sets `shift_code = 'DAY'` and produces `status = VALID` with 0 warnings, ignoring the ambiguous night token.

### Obs 6: Large integer string conversion crash
- **Location**: `core/parser.py:422`
- **Invocation**:
  ```python
  from core.parser import parse_single_message
  raw = "HỌ TÊN: A\nNGÀY: 24/10/2026\nCA: Ca ngày\nTHỜI GIAN: 8h\nĂN: " + "9" * 5000
  parse_single_message(raw)
  ```
- **Verbatim Result**:
  ```
  ValueError: Exceeds the limit (4300 digits) for integer string conversion: value has 5000 digits; use sys.set_int_max_str_digits() to increase the limit
  ```

---

## 2. Logic Chain

1. **Crash Prevention Contract**: The dispatcher instructions require: *"Confirm the parser never crashes (raises unhandled exceptions)"*.
   - In Obs 1, passing `None` to `parse_single_message(None)` crashes with `TypeError`.
   - In Obs 6, parsing extreme inputs crashes with `ValueError`.
   - *Inference*: The non-crashing contract is violated under direct API boundary conditions.

2. **Classification & Business Logic Contract**: The dispatcher instructions require: *"correctly classifies invalid messages as status ERROR or WARNING"*.
   - In Obs 2, negative hours (`-5h`, `(-5H)`) represent invalid work durations. The parser classifies them as `VALID` and allocates positive payroll hours (`hcn_100=5.0`).
   - In Obs 4, clock hours exceeding 24 (`25h-30h`) are invalid clock representations. The parser classifies them as `VALID` without warning.
   - In Obs 5, ambiguous shifts containing conflicting day and night indicators (`Ca ngày đêm`) are classified as `VALID` without any warning.
   - *Inference*: Invalid and ambiguous inputs are misclassified as `VALID`, which would result in erroneous payroll calculation and incorrect Excel writes in downstream milestones.

3. **Batch Segmentation Integrity**:
   - In Obs 3, valid messages containing blank lines between fields are shredded into partial fragments by `sub_blocks` splitting.
   - *Inference*: Real-world Zalo chat text frequently contains empty lines between fields. Ingesting such text results in false-positive `ERROR` records and lost attendance data.

4. **Conclusion Derivation**:
   - Because both the non-crashing guarantee and the status classification requirements have reproducible empirical failures, Milestone 1 cannot be approved in its current state.

---

## 3. Caveats

- **Strengths Observed**: The parser demonstrated outstanding resilience against random Unicode fuzzing (500 iterations, 0 crashes), excellent throughput (150 batch messages parsed in 0.005s), correct handling of Vietnamese accents, valid acceptance criteria matching, and proper rate calculations under standard conditions.
- **Scope Limit**: Only `core/parser.py` and its interaction with `models/attendance.py` was evaluated. `core/excel_integrator.py` and web endpoints were out of scope for this Milestone 1 challenge.

---

## 4. Conclusion

**Verdict: REJECT**

The parser is solid in its happy-path implementation and basic variations, but has critical edge-case vulnerabilities that must be remediated:
1. Guard `parse_single` against `None` and non-string inputs (`if not raw_message or not isinstance(raw_message, str): return create_error_record(...)`).
2. Detect negative numbers in hours (`if re.search(r'-\s*\d', raw_hours): errors.append(...)`).
3. Bound clock hours in ranges to `0 <= sh <= 24` and `0 <= eh <= 24`.
4. Detect conflicting shift keywords (`if 'ngày' in s_lower and 'đêm' in s_lower: warnings.append(...)`).
5. Remove `sub_blocks` splitting on `\n\s*\n+` inside `split_messages` when messages already start with `header_re`, preserving multi-line messages with blank lines.
6. Guard meal digit parsing to avoid converting numbers > 10 digits (`m_dig.group(1)[:4]`).

---

## 5. Verification Method

To independently reproduce and verify all 6 reported issues, execute the reproduction harness:

```bash
.venv/bin/python3 -c "
from core.parser import parse_single_message, parse_attendance_messages

# Bug 1: None crash
try:
    parse_single_message(None)
    print('Bug 1 NOT reproduced')
except TypeError as e:
    print('Bug 1 REPRODUCED (None crash):', e)

# Bug 2: Negative hours accepted as VALID
r2 = parse_single_message('HỌ TÊN: A\nNGÀY: 24/10/2026\nCA: Ca ngày\nTHỜI GIAN: -5h\nĂN: 0')
print('Bug 2 REPRODUCED (Negative hours VALID):', r2.status, r2.hours.total_hours)

# Bug 3: Impossible clock hours 25h-30h accepted as VALID
r3 = parse_single_message('HỌ TÊN: A\nNGÀY: 24/10/2026\nCA: Ca ngày\nTHỜI GIAN: 25h-30h\nĂN: 0')
print('Bug 3 REPRODUCED (25h-30h VALID):', r3.status, r3.hours.total_hours)

# Bug 4: Ambiguous shift 'Ca ngày đêm' accepted as VALID with 0 warnings
r4 = parse_single_message('HỌ TÊN: A\nNGÀY: 24/10/2026\nCA: Ca ngày đêm\nTHỜI GIAN: 8h-17h (8H)\nĂN: 0')
print('Bug 4 REPRODUCED (Ambiguous shift VALID, 0 warnings):', r4.status, len(r4.messages))

# Bug 5: Blank line in single message splits into 2 ERROR records
r5 = parse_attendance_messages('HỌ TÊN: A\nNGÀY: 24/10/2026\n\nCA: Ca ngày\nTHỜI GIAN: 8h-17h (8H)\nĂN: 0')
print('Bug 5 REPRODUCED (Blank line fragmentation count):', len(r5), [x.status for x in r5])

# Bug 6: 5000 digit meal conversion crash
try:
    parse_single_message('HỌ TÊN: A\nNGÀY: 24/10/2026\nCA: Ca ngày\nTHỜI GIAN: 8h\nĂN: ' + '9' * 5000)
    print('Bug 6 NOT reproduced')
except ValueError as e:
    print('Bug 6 REPRODUCED (5000 digit meal crash):', type(e).__name__)
"
```

To run the full 538-case adversarial suite:
```bash
.venv/bin/python3 .agents/teamwork/challenger_m1_1/stress_test_parser.py
```
