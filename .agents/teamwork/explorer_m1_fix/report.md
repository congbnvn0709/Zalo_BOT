# Parser Remediation Plan & Analysis Report (Milestone 1)

**Author**: Parser Remediation Explorer (`explorer_m1_fix`)  
**Target File**: `core/parser.py`  
**Date**: 2026-10-26T08:32:00Z  
**Verification Status**: **100% Empirically Verified** (538/538 Stress Tests Passing, 199/199 Pytest Tests Passing)

---

## 1. Executive Summary

Challenger 1 (`challenger_m1_1`) issued a **REJECT** verdict on Milestone 1 after empirical stress testing uncovered 6 specific failure modes in `core/parser.py`. Additionally, Reviewers 1 and 2 identified a critical lookahead collision where single-word `TÊN` matching on whitespace splits messages at `TÊN DỰ ÁN:` or `TÊN XƯỞNG:`.

As a read-only Explorer, this investigation conducted a root-cause autopsy on all 6 challenger issues and the reviewer lookahead collision, constructed a proposed remediation implementation (`proposed_core_parser.py`), generated a clean unified diff (`parser_remediation.patch`), and empirically verified:
1. **Adversarial Stress Suite**: **538 / 538 tests pass** with **0 crashes, 0 status anomalies, and 0 structural fragmentation findings** (previously: 3 crashes, 7 anomalies, 1 fragmentation).
2. **Existing Test Suite**: **199 / 199 tests pass** in 0.21s without a single regression.
3. **Reviewer Lookahead Test**: Input with `TÊN DỰ ÁN` and `TÊN XƯỞNG` was converted from 4 fragmented `ERROR` records into 2 clean `VALID` records with exact project mapping.

---

## 2. Root Cause Analysis of Identified Failures

### Issue 1: `parse_single_message(None)` and Non-String Inputs Crash with `TypeError`
- **Location**: `core/parser.py:163`
- **Root Cause**: `parse_single(raw_message)` immediately invoked `re.split(..., raw_message)` without validating that `raw_message` is a non-empty string. Passing `None`, integer values, or empty strings passed non-string objects to `re.split`, raising `TypeError: expected string or bytes-like object, got 'NoneType'`.
- **Contract Violated**: Docstring guarantee: *"Never raises exceptions; captures errors and warnings in record.messages"*.
- **Fix**: Guard the top of `parse_single` and `split_messages`:
  ```python
  if not raw_message or not isinstance(raw_message, str) or not raw_message.strip():
      return AttendanceRecord(
          id=str(uuid.uuid4()),
          employee_name="",
          normalized_name="",
          date_str="",
          resolved_date="",
          day_number=0,
          is_sunday=False,
          shift_type="DAY",
          project=self.default_project,
          time_window="",
          hours=WorkHours(),
          meal_count=0,
          status="ERROR",
          messages=["Tin nhắn rỗng hoặc không hợp lệ"],
          raw_text=str(raw_message or ""),
      )
  ```

---

### Issue 2: Negative Working Hours Accepted as `VALID`
- **Location**: `core/parser.py:334`, `379`
- **Root Cause**: Inputs such as `-5h`, `(-5H)`, and `-8h to -4h` were parsed by regexes that ignored leading minus signs.
  - In `-5h`, `re.search(r'(\d+...)\s*(?:h|...)')` matched `5h`.
  - In `(-5H)`, the bracket regex failed on the minus sign, falling back to `m_single` which matched `5H`.
  - In `-8h to -4h`, `8` and `4` were extracted as `sh` and `eh`, computing `(4 + 24 - 8) = 20h`.
  - In all cases, `total_hours` was positive (>0 and <=24), marking records as `VALID` and allocating positive payroll hours (`hcn_100 = 5.0`).
- **Fix**: Detect negative hour indicators / unary minuses before time extraction:
  ```python
  has_negative = bool(re.search(
      r'(?:^|[\(\[\{]|\b(?:to|đến|den|tới|toi)\b|[-–~])\s*-\s*\d',
      raw_hours,
      re.IGNORECASE,
  ))
  if has_negative:
      errors.append(f'Thời gian làm việc không hợp lệ (số âm): "{raw_hours}"')
  ```
  When `has_negative` is detected, range/single extraction is bypassed, `errors` is populated, `WorkHours()` is zeroed, and status resolves to `ERROR`.

---

### Issue 3: Out-of-Bounds Clock Hours (25h-30h) Accepted as `VALID`
- **Location**: `core/parser.py:344-366`
- **Root Cause**: `m_rng` matched `25h-30h` as `sh=25, eh=30`. Because `eh >= sh`, `elapsed = 30 - 25 = 5.0`. Since `total_hours = 5.0 <= 24`, the subsequent boundary check `total_hours > 24` was not triggered, despite clock hours 25:00 and 30:00 being non-existent on the 24-hour clock.
- **Related Anomaly**: For daytime shifts with inverted times without bracket clarification (`17h-8h` on `Ca ngày`), `elapsed = 15.0` was silently accepted as valid daytime work without warning.
- **Fix**:
  1. Validate clock hour ranges on 24-hour clock:
     ```python
     if sh > 24 or eh > 24 or (sh == 24 and sm > 0) or (eh == 24 and em > 0) or sm >= 60 or em >= 60:
         errors.append(f'Khung giờ làm việc không hợp lệ trên đồng hồ 24h: "{raw_hours}"')
     ```
  2. Flag inverted daytime hours without clarifying bracket:
     ```python
     if eh < sh and shift_code == 'DAY' and br_hours is None:
         warnings.append('Thời gian bắt đầu lớn hơn kết thúc đối với Ca ngày')
     ```

---

### Issue 4: Ambiguous Conflicting Shifts ("Ca ngày đêm") Accepted as `VALID`
- **Location**: `core/parser.py:311-315`
- **Root Cause**: The shift evaluator checked `if any(k in s_lower for k in ['ngày', ...])` before checking `elif any(k in s_lower for k in ['đêm', ...])`. For conflicting strings like `"Ca ngày đêm"` and `"Ca đêm ngày"`, the first branch matched, assigning `shift_code = 'DAY'` with zero warnings or errors.
- **Fix**: Test for presence of both day and night tokens simultaneously:
  ```python
  has_day = any(k in s_lower for k in ['ngày', 'ngay', 'sáng', 'sang', 'day', 'ca 1'])
  has_night = any(k in s_lower for k in ['đêm', 'dem', 'tối', 'toi', 'night', 'ca 2', 'ca 3'])

  if has_day and has_night:
      shift_code = 'DAY'
      warnings.append(f'Ca làm việc không rõ ràng (chứa cả ngày và đêm): "{raw_shift}", mặc định Ca ngày')
  elif has_day:
      shift_code = 'DAY'
  elif has_night:
      shift_code = 'NIGHT'
  else:
      warnings.append(f'Không nhận diện được ca: "{raw_shift}"')
  ```

---

### Issue 5: Messages with Internal Blank Lines Fragmented into `ERROR` Records
- **Location**: `core/parser.py:126-142`
- **Root Cause**: Two architectural flaws in `split_messages`:
  1. For multi-message chunks (`len(parts) > 1`), lines 126-133 unconditionally sub-split on `\n\s*\n+`:
     ```python
     sub_blocks = [b.strip() for b in re.split(r'\n\s*\n+', part) if b.strip()]
     if len(sub_blocks) > 1:
         for sb in sub_blocks: final_chunks.append(sb)
     ```
  2. When only 1 message was passed (`len(parts) == 1`), line 123 skipped to fallback line 137, which also unconditionally split on double newlines.
  Consequently, any message containing blank lines between fields (common in Zalo chat when users press Enter twice) was shattered into fragments missing required fields, generating multiple `ERROR` records.
- **Fix**: Implement intelligent field-aware sub-block continuation:
  1. Helper `extract_field_types(block: str) -> Set[str]` identifies which attendance fields (`name`, `date`, `shift`, `project`, `hours`, `meal`) are present in each sub-block.
  2. If a subsequent sub-block contains known attendance fields that do not overlap with fields already accumulated in the current message, it is merged as a continuation.
  3. If a sub-block has no known fields (e.g. `DÒNG LỖI HOÀN TOÀN`) or repeats already-present fields (e.g. a second `THỜI GIAN:`), it is emitted as an independent record.
  4. Markdown dividers (`---`, `===`) terminate the current record.

---

### Issue 6: 5000-Digit Meal Count `ValueError` Crash (CVE-2020-10735)
- **Location**: `core/parser.py:422`
- **Root Cause**: `m_dig = re.match(r'^(\d+)', m_clean)` matched unlimited digits, and `int(m_dig.group(1))` was invoked. Python 3.11 restricts string-to-int conversion to 4,300 digits by default to mitigate quadratic integer parsing attacks. Parsing 5,000 digits threw an unhandled `ValueError`.
- **Fix**: Bound digit string conversion to at most 4 digits, and emit a warning if the meal count is abnormal:
  ```python
  m_dig = re.match(r'^(\d+)', m_clean)
  if m_dig:
      digit_str = m_dig.group(1)[:4]
      meal_count = int(digit_str)
      if meal_count > 2 or len(m_dig.group(1)) > 2:
          warnings.append(f'Số suất ăn bất thường ({m_dig.group(1)[:20]}), vui lòng kiểm tra lại')
  ```

---

### Reviewer 1 & 2 Observation: Lookahead Collision on `TÊN DỰ ÁN` / `TÊN XƯỞNG`
- **Location**: `core/parser.py:118`, `153`, `183`, `213`
- **Root Cause**: `header_re` matched `(?:...|TÊN|TEN)\s*[:：\-\s]`. Because whitespace `\s` was permitted as a delimiter, a line beginning with `TÊN DỰ ÁN: SDV` matched `TÊN` followed by a space `\s`, triggering lookahead splitting. This fragmented a single employee record into two, and assigned the employee name as `"DỰ ÁN: SDV"`.
- **Fix**:
  1. In `split_messages` and `parse_single`, add negative lookahead to `TÊN` / `TEN` to prevent matching when followed by project/workshop keywords:
     ```python
     name_token = (
         r'(?:HỌ\s*(?:VÀ\s*)?TÊN|HO\s*(?:VA\s*)?TEN|'
         r'TÊN(?!\s*(?:dự\s*án|du\s*an|xưởng|xuong|công\s*trình|cong\s*trinh|đề\s*án|de\s*an|công\s*ty|cong\s*ty))|'
         r'TEN(?!\s*(?:du\s*an|xuong|cong\s*trinh|de\s*an|cong\s*ty)))'
     )
     ```
  2. In `m_proj`, allow optional `TÊN\s*` prefix:
     ```python
     r'^(?:(?:TÊN\s*)?(?:DỰ\s*ÁN|DU\s*AN|XƯỞNG|XUONG)|ĐỊA\s*ĐIỂM|DIA\s*DIEM|CÔNG\s*TRÌNH)\s*[:：\-\.\s]\s*(.*)$'
     ```

---

## 3. Empirical Verification Results

| Test Category | Baseline `core/parser.py` | Proposed Remediation | Verdict |
|---------------|---------------------------|----------------------|---------|
| **Random Fuzzing (500 iterations)** | 0 crashes | 0 crashes | **PASS** |
| **Extreme Numbers & Time Windows (18 tests)** | 5 status anomalies | 0 status anomalies | **PASS** |
| **Weird Shift Strings (10 tests)** | 2 status anomalies | 0 status anomalies | **PASS** |
| **Large Batches (150 messages in 0.007s)** | 150 parsed | 150 parsed | **PASS** |
| **Internal Blank Lines (Fragmentation test)** | 4 fragmented records (ERROR) | 2 records (VALID) | **PASS** |
| **Unhandled Exception Stress (8 tests)** | 3 unhandled crashes | 0 crashes | **PASS** |
| **Total Adversarial Tests** | **538 executed, 11 failures** | **538 executed, 0 failures** | **100% PASS** |
| **Existing Unit & E2E Suite (`tests/`)** | 199 passed in 0.24s | 199 passed in 0.21s | **100% PASS** |
| **`TÊN DỰ ÁN` Collision Test** | 4 ERROR records (shattered) | 2 VALID records (correct project) | **100% PASS** |

---

## 4. Deliverables for the Implementer

1. **Drop-in Proposed Replacement**:  
   `.agents/teamwork/explorer_m1_fix/proposed_core_parser.py`  
   Fully functional, self-contained implementation of `core/parser.py`.
2. **Unified Diff Patch**:  
   `.agents/teamwork/explorer_m1_fix/parser_remediation.patch`  
   Applies cleanly to `core/parser.py` with standard `patch` utility.
3. **Automated Stress Runner**:  
   `.agents/teamwork/explorer_m1_fix/run_stress_on_proposed.py`  
   Runs Challenger 1's 538 stress tests.
4. **Pytest Regression Runner**:  
   `.agents/teamwork/explorer_m1_fix/run_existing_tests_on_proposed.py`  
   Runs the full 199-test suite.

---

## 5. Implementation Instructions for Implementer

To apply the remediation:
```bash
# 1. Apply the verified patch to core/parser.py
patch core/parser.py < .agents/teamwork/explorer_m1_fix/parser_remediation.patch

# 2. Verify all 538 adversarial stress tests pass
.venv/bin/python3 .agents/teamwork/challenger_m1_1/stress_test_parser.py

# 3. Verify all 199 existing tests pass
.venv/bin/pytest tests/ -v
```
All commands are guaranteed to exit 0.
