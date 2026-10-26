# Empirical Challenge Handoff Report: Time Calculation Math & Break Deductions

**Role**: Parser Challenger 2 (Milestone 1)  
**Working Directory**: `/Users/congcm/CODE/Vibe_Code/Zalo_BOT/.agents/teamwork/challenger_m1_2/`  
**Verdict**: **APPROVE**

---

## 1. Observation

Direct observations from inspecting code and executing empirical challenge test scripts against `core/parser.py`:

1. **Codebase Inspection**:
   - `core/parser.py:68-80`: `calculate_work_hours(total_hours, shift_type, is_sunday)` allocates hours:
     ```python
     if is_sunday:
         if shift == "DAY":
             sunday_day_200 = float(total_hours)
         else:
             sunday_night_260 = float(total_hours)
     else:
         if shift == "DAY":
             hcn_100 = float(min(total_hours, 8.0))
             tcn_150 = float(max(0.0, total_hours - 8.0))
         else:
             hcd_130 = float(min(total_hours, 8.0))
             tcd_195 = float(max(0.0, total_hours - 8.0))
     ```
   - `core/parser.py:333-376`: Break deduction and bracket priority:
     * Explicit bracketed hours: `m_br = re.search(r'\(\s*(\d+(?:[\.,]\d+)?)\s*(?:h|tiếng|g|giờ)?\s*\)', raw_hours, re.IGNORECASE)` takes first priority (`total_hours = br_hours`).
     * Clock range elapsed time: `elapsed = (eh - sh) + (em - sm) / 60.0` or `(eh + 24 - sh) + (em - sm) / 60.0`.
     * If bracket is absent: `if elapsed >= 8.5: total_hours = elapsed - 1.0 else: total_hours = elapsed`.
   - `core/parser.py:385-389`: Additive overtime (`+ TC 3h`) is evaluated only `if m_ot and not m_br`, preventing double counting.

2. **Empirical Boundary Verification Suite (`verify_boundaries.py`)**:
   - Command: `.venv/bin/python3 .agents/teamwork/challenger_m1_2/verify_boundaries.py`
   - Output verbatim:
     ```text
     === STARTING EMPIRICAL BOUNDARY CHALLENGE TESTS ===

     --- Suite 1: Exact Threshold Shifts ---

     --- Suite 2: Cross-Midnight Transitions ---

     --- Suite 3: Sunday vs Weekday Bucket Isolation ---

     --- Suite 4: Bracketed Overrides ---

     --- Suite 5: Extended Adversarial Stress Cases ---

     ==================================================
     TEST RESULTS: 25 PASSED, 0 FAILED (TOTAL 25)
     ==================================================
     [PASS] T1.1_ELAPSED_8.0H: 8h-16h (8.0h elapsed) -> total=8.0, hcn=8.0, tcn=0.0
     [PASS] T1.2_ELAPSED_8.5H: 8h-16h30 (8.5h elapsed) -> total=7.5, hcn=7.5, tcn=0.0
     [PASS] T1.3_ELAPSED_9.0H: 8h-17h (9.0h elapsed) -> total=8.0, hcn=8.0, tcn=0.0
     [PASS] T1.4_ELAPSED_8.4H: 8h-16h24 (8.4h elapsed) -> total=8.4, hcn=8.0, tcn=0.4
     [PASS] T1.5_ELAPSED_4.0H: 8h-12h (4.0h elapsed) -> total=4.0, hcn=4.0, tcn=0.0
     [PASS] T2.1_CROSS_22H_6H: 22h-6h (8.0h elapsed) -> total=8.0, hcd=8.0, tcd=0.0
     [PASS] T2.2_CROSS_23H_7H: 23h-7h (8.0h elapsed) -> total=8.0, hcd=8.0, tcd=0.0
     [PASS] T2.3_CROSS_21H_6H: 21h-6h (9.0h elapsed - 1h break) -> total=8.0, hcd=8.0, tcd=0.0
     [PASS] T2.4_CROSS_20H_8H: 20h-8h (12.0h elapsed - 1h break) -> total=11.0, hcd=8.0, tcd=3.0
     [PASS] T2.5_CROSS_INFER_NIGHT: 22h-6h with omitted shift -> inferred NIGHT, warnings=['Tự động nhận diện Ca đêm dựa vào giờ bắt đầu']
     [PASS] T3.1_SUN_DAY_8H_ISOLATION: Sunday Day 8H -> sunday_day_200=8.0, weekday all 0.0
     [PASS] T3.2_SUN_DAY_11H_ISOLATION: Sunday Day 11H -> sunday_day_200=11.0, weekday all 0.0
     [PASS] T3.3_SUN_NIGHT_8H_ISOLATION: Sunday Night 8H -> sunday_night_260=8.0, weekday all 0.0
     [PASS] T3.4_SUN_NIGHT_12H_ISOLATION: Sunday Night 12H -> sunday_night_260=12.0, weekday all 0.0
     [PASS] T3.5_WEEKDAY_NEVER_SPILLS_INTO_SUNDAY: Monday Day 11H -> hcn=8.0, tcn=3.0, Sunday buckets are 0.0
     [PASS] T4.1_BRACKET_10H: '8h-20h ( 10H)' -> total=10.0, hcn=8.0, tcn=2.0, status=VALID
     [PASS] T4.2_BRACKET_11H: '8h-20h ( 11H)' -> total=11.0, hcn=8.0, tcn=3.0, status=VALID
     [PASS] T4.3_BRACKET_12H: '8h-20h ( 12H)' -> total=12.0, hcn=8.0, tcn=4.0, status=VALID
     [PASS] T4.4_BRACKET_DISCREPANCY_WARNING: '8h-17h ( 10H)' -> total=10.0, status=WARNING, messages=['Số giờ làm (10.0h) lớn hơn thời gian chênh lệch (9.0h)']
     [PASS] T4.5_BRACKET_COMMA_DECIMAL: '8h-20h ( 10,5H)' -> total=10.5, hcn=8.0, tcn=2.5
     [PASS] T5.1_ZERO_HOURS_ERROR: 0 hours -> status=ERROR, errors=['Tổng số giờ làm phải lớn hơn 0']
     [PASS] T5.2_OVERFLOW_HOURS_ERROR: 25 hours -> status=ERROR, errors=['Tổng số giờ làm (25.0h) vượt quá 24h/ngày', 'Số giờ làm (25.0h) lớn hơn thời gian chênh lệch (12.0h)']
     [PASS] T5.3_ADDITIVE_OVERTIME: '8h-17h + TC 3h' -> total=11.0, hcn=8.0, tcn=3.0
     [PASS] T5.4_BRACKET_AND_ADDITIVE_NO_DOUBLE_COUNT: '(11H) + TC 3h' -> total=11.0 (bracket 11H wins without +3h double count)
     [PASS] T5.5_ENDASH_TIME_RANGE: '8:00 – 17:00' -> total=8.0, hcn=8.0
     ```

3. **Adversarial Stress Harness (`verify_stress.py`)**:
   - Command: `.venv/bin/python3 .agents/teamwork/challenger_m1_2/verify_stress.py`
   - Result: All tests passed (minute calculations across midnight, Vietnamese bracket keywords `tiếng`/`giờ`/`g`, floating point precision, negative hours boundary).

4. **Milestone 1 Test Suite Regression Check**:
   - Command: `.venv/bin/pytest tests/test_parser.py -v`
   - Result: 73 passed in 0.08s with 0 errors and 0 warnings.

---

## 2. Logic Chain

1. **Exact Threshold Shift Behavior (Observed T1.1, T1.2, T1.3, T1.4, T1.5)**:
   - When a worker specifies a clock range without explicit bracketed hours:
     * `8h-16h` has an elapsed time of `16.0 - 8.0 = 8.0h`. Since `8.0 < 8.5`, no break deduction occurs, resulting in `total_hours = 8.0` (allocated as `hcn_100 = 8.0`).
     * `8h-16h30` has an elapsed time of `16.5 - 8.0 = 8.5h`. Since `8.5 >= 8.5`, a 1.0h meal break is deducted, yielding `total_hours = 7.5` (`hcn_100 = 7.5`).
     * `8h-17h` has an elapsed time of `17.0 - 8.0 = 9.0h`. Since `9.0 >= 8.5`, a 1.0h meal break is deducted, yielding `total_hours = 8.0` (`hcn_100 = 8.0`).
   - This matches the factory labor specification where standard full shifts spanning 8.5+ clock hours deduct 1h unpaid lunch/dinner break.

2. **Cross-Midnight Shift Arithmetic (Observed T2.1, T2.2, T2.3, T2.4, T2.5, and verify_stress)**:
   - For `22h-6h`: `(6 + 24 - 22) = 8.0h elapsed`. With elapsed < 8.5h, net hours = 8.0h, correctly mapped to `hcd_130 = 8.0`.
   - For `23h-7h`: `(7 + 24 - 23) = 8.0h elapsed`. Net hours = 8.0h, mapped to `hcd_130 = 8.0`.
   - For `21h-6h`: `(6 + 24 - 21) = 9.0h elapsed`. Since 9.0 >= 8.5h, 1h break is deducted -> 8.0h net, mapped to `hcd_130 = 8.0`.
   - For `20h-8h`: `(8 + 24 - 20) = 12.0h elapsed`. Break deducted -> 11.0h net, correctly allocated as `hcd_130 = 8.0` and `tcd_195 = 3.0`.
   - When shift keyword is omitted, `start_h >= 18` successfully infers `NIGHT` shift with a warning.
   - Fractional minute shifts crossing midnight (`20h30 - 5h15`) calculate 8.75h elapsed, deducting 1h break to produce 7.75h net with 0 floating point errors.

3. **Sunday Daytime vs Sunday Night Shifts Isolation (Observed T3.1, T3.2, T3.3, T3.4, T3.5)**:
   - When `is_sunday = True` and `shift = DAY`:
     * All hours (e.g. 8.0h or 11.0h) are mapped to `sunday_day_200`.
     * `hcn_100`, `tcn_150`, `hcd_130`, `tcd_195`, and `sunday_night_260` are strictly `0.0`.
   - When `is_sunday = True` and `shift = NIGHT`:
     * All hours (e.g. 8.0h or 12.0h) are mapped to `sunday_night_260`.
     * `hcn_100`, `tcn_150`, `hcd_130`, `tcd_195`, and `sunday_day_200` are strictly `0.0`.
   - When `is_sunday = False`:
     * `sunday_day_200` and `sunday_night_260` are strictly `0.0`.
   - Conclusion: Zero cross-contamination between weekday and Sunday buckets.

4. **Bracketed Override Hierarchy (Observed T4.1, T4.2, T4.3, T4.4, T4.5, T5.3, T5.4)**:
   - Given `8h-20h`:
     * `( 10H)` -> 10.0h total (`hcn = 8.0`, `tcn = 2.0`).
     * `( 11H)` -> 11.0h total (`hcn = 8.0`, `tcn = 3.0`).
     * `( 12H)` -> 12.0h total (`hcn = 8.0`, `tcn = 4.0`).
   - If bracketed hours exceed clock difference (e.g. `8h-17h ( 10H)`), bracketed hours (10.0h) are honored while flagging a diagnostic `WARNING` (`Số giờ làm (10.0h) lớn hơn thời gian chênh lệch (9.0h)`).
   - If both bracketed hours and additive notation are present (e.g. `(11H) + TC 3h`), bracketed hours take precedence and additive overtime is not double-counted.

---

## 3. Caveats

- In the absence of an explicit bracket, continuous shifts between 8.0h and 8.49h do not trigger break deduction, whereas shifts >= 8.5h trigger a 1.0h deduction. This design adheres strictly to the factory domain specification documented in `survey_spec_miner_parser/report.md` (Table 2 item 12 and Section 4.5).
- No functional defects, regressions, or mathematical inconsistencies were detected.

---

## 4. Conclusion

**Verdict: APPROVE**

The time calculation, break deduction logic, cross-midnight modular arithmetic, Sunday rate isolation, and bracketed hour precedence in `core/parser.py` are robust, mathematically sound, and fully verified against all boundary conditions and stress tests.

---

## 5. Verification Method

To independently reproduce all empirical challenge results:
```bash
cd /Users/congcm/CODE/Vibe_Code/Zalo_BOT

# 1. Run empirical boundary challenge tests (25 tests)
.venv/bin/python3 .agents/teamwork/challenger_m1_2/verify_boundaries.py

# 2. Run adversarial stress tests
.venv/bin/python3 .agents/teamwork/challenger_m1_2/verify_stress.py

# 3. Run full parser unit test suite (73 tests)
.venv/bin/pytest tests/test_parser.py -v
```
Expected output: All test suites exit with code 0 and 0 failures.
