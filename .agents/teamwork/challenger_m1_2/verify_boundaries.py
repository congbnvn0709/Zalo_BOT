"""
Empirical verification script for Milestone 1 attendance parser.
Tests boundary conditions, threshold shifts, cross-midnight transitions,
Sunday bucket isolation, and bracketed overrides.
"""
import sys
import os

# Add workspace root to sys.path
WORKSPACE_ROOT = "/Users/congcm/CODE/Vibe_Code/Zalo_BOT"
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

from core.parser import AttendanceParser, calculate_work_hours, parse_single_message
from models.attendance import WorkHours, AttendanceRecord

def run_tests():
    parser = AttendanceParser(default_year=2026)
    passed = 0
    failed = 0
    results = []

    def check(test_id, condition, msg):
        nonlocal passed, failed
        if condition:
            passed += 1
            results.append(f"[PASS] {test_id}: {msg}")
        else:
            failed += 1
            results.append(f"[FAIL] {test_id}: {msg}")

    print("=== STARTING EMPIRICAL BOUNDARY CHALLENGE TESTS ===")

    # ---------------------------------------------------------
    # TEST SUITE 1: EXACT THRESHOLD SHIFTS
    # ---------------------------------------------------------
    print("\n--- Suite 1: Exact Threshold Shifts ---")
    
    # 1.1: 8.0h elapsed (8h-16h) without bracket -> no break deduction expected
    msg_8h = """
HỌ TÊN: NGUYỄN VĂN A
NGÀY: 24/10/2026
CA: Ca ngày
THỜI GIAN LÀM VIỆC: 8h-16h
CÓ ĂN Ở XƯỞNG KO: 0
"""
    rec_8h = parser.parse_single(msg_8h)
    check("T1.1_ELAPSED_8.0H", 
          rec_8h.hours.total_hours == 8.0 and rec_8h.hours.hcn_100 == 8.0 and rec_8h.hours.tcn_150 == 0.0,
          f"8h-16h (8.0h elapsed) -> total={rec_8h.hours.total_hours}, hcn={rec_8h.hours.hcn_100}, tcn={rec_8h.hours.tcn_150}")

    # 1.2: 8.5h elapsed (8h-16h30) without bracket -> 1.0h break deducted -> 7.5h net
    msg_8_5h = """
HỌ TÊN: NGUYỄN VĂN A
NGÀY: 24/10/2026
CA: Ca ngày
THỜI GIAN LÀM VIỆC: 8h-16h30
CÓ ĂN Ở XƯỞNG KO: 0
"""
    rec_8_5h = parser.parse_single(msg_8_5h)
    check("T1.2_ELAPSED_8.5H", 
          rec_8_5h.hours.total_hours == 7.5 and rec_8_5h.hours.hcn_100 == 7.5 and rec_8_5h.hours.tcn_150 == 0.0,
          f"8h-16h30 (8.5h elapsed) -> total={rec_8_5h.hours.total_hours}, hcn={rec_8_5h.hours.hcn_100}, tcn={rec_8_5h.hours.tcn_150}")

    # 1.3: 9.0h elapsed (8h-17h) without bracket -> 1.0h break deducted -> 8.0h net
    msg_9h = """
HỌ TÊN: NGUYỄN VĂN A
NGÀY: 24/10/2026
CA: Ca ngày
THỜI GIAN LÀM VIỆC: 8h-17h
CÓ ĂN Ở XƯỞNG KO: 0
"""
    rec_9h = parser.parse_single(msg_9h)
    check("T1.3_ELAPSED_9.0H", 
          rec_9h.hours.total_hours == 8.0 and rec_9h.hours.hcn_100 == 8.0 and rec_9h.hours.tcn_150 == 0.0,
          f"8h-17h (9.0h elapsed) -> total={rec_9h.hours.total_hours}, hcn={rec_9h.hours.hcn_100}, tcn={rec_9h.hours.tcn_150}")

    # 1.4: 8.4h elapsed (8h-16h24) -> elapsed < 8.5h -> no deduction
    msg_8_4h = """
HỌ TÊN: NGUYỄN VĂN A
NGÀY: 24/10/2026
CA: Ca ngày
THỜI GIAN LÀM VIỆC: 8h-16h24
CÓ ĂN Ở XƯỞNG KO: 0
"""
    rec_8_4h = parser.parse_single(msg_8_4h)
    check("T1.4_ELAPSED_8.4H",
          round(rec_8_4h.hours.total_hours, 2) == 8.4 and rec_8_4h.hours.hcn_100 == 8.0 and round(rec_8_4h.hours.tcn_150, 2) == 0.4,
          f"8h-16h24 (8.4h elapsed) -> total={rec_8_4h.hours.total_hours}, hcn={rec_8_4h.hours.hcn_100}, tcn={rec_8_4h.hours.tcn_150}")

    # 1.5: Short shift 4h (8h-12h) -> elapsed 4.0h < 8.5h -> 4.0h net
    msg_4h = """
HỌ TÊN: NGUYỄN VĂN A
NGÀY: 24/10/2026
CA: Ca ngày
THỜI GIAN LÀM VIỆC: 8h-12h
CÓ ĂN Ở XƯỞNG KO: 0
"""
    rec_4h = parser.parse_single(msg_4h)
    check("T1.5_ELAPSED_4.0H",
          rec_4h.hours.total_hours == 4.0 and rec_4h.hours.hcn_100 == 4.0 and rec_4h.hours.tcn_150 == 0.0,
          f"8h-12h (4.0h elapsed) -> total={rec_4h.hours.total_hours}, hcn={rec_4h.hours.hcn_100}, tcn={rec_4h.hours.tcn_150}")

    # ---------------------------------------------------------
    # TEST SUITE 2: CROSS-MIDNIGHT TRANSITIONS
    # ---------------------------------------------------------
    print("\n--- Suite 2: Cross-Midnight Transitions ---")

    # 2.1: 22h-6h (8.0h elapsed, non-Sunday, no bracket)
    msg_22_6 = """
HỌ TÊN: NGUYỄN VĂN B
NGÀY: 24/10/2026
CA: Ca đêm
THỜI GIAN LÀM VIỆC: 22h-6h
CÓ ĂN Ở XƯỞNG KO: 0
"""
    rec_22_6 = parser.parse_single(msg_22_6)
    check("T2.1_CROSS_22H_6H",
          rec_22_6.hours.total_hours == 8.0 and rec_22_6.hours.hcd_130 == 8.0 and rec_22_6.hours.tcd_195 == 0.0 and rec_22_6.shift_type == "NIGHT",
          f"22h-6h (8.0h elapsed) -> total={rec_22_6.hours.total_hours}, hcd={rec_22_6.hours.hcd_130}, tcd={rec_22_6.hours.tcd_195}")

    # 2.2: 23h-7h (8.0h elapsed, non-Sunday, no bracket)
    msg_23_7 = """
HỌ TÊN: NGUYỄN VĂN B
NGÀY: 24/10/2026
CA: Ca đêm
THỜI GIAN LÀM VIỆC: 23h-7h
CÓ ĂN Ở XƯỞNG KO: 0
"""
    rec_23_7 = parser.parse_single(msg_23_7)
    check("T2.2_CROSS_23H_7H",
          rec_23_7.hours.total_hours == 8.0 and rec_23_7.hours.hcd_130 == 8.0 and rec_23_7.hours.tcd_195 == 0.0,
          f"23h-7h (8.0h elapsed) -> total={rec_23_7.hours.total_hours}, hcd={rec_23_7.hours.hcd_130}, tcd={rec_23_7.hours.tcd_195}")

    # 2.3: 21h-6h (9.0h elapsed, non-Sunday, no bracket -> 1h break deducted -> 8.0h net)
    msg_21_6 = """
HỌ TÊN: NGUYỄN VĂN B
NGÀY: 24/10/2026
CA: Ca đêm
THỜI GIAN LÀM VIỆC: 21h-6h
CÓ ĂN Ở XƯỞNG KO: 0
"""
    rec_21_6 = parser.parse_single(msg_21_6)
    check("T2.3_CROSS_21H_6H",
          rec_21_6.hours.total_hours == 8.0 and rec_21_6.hours.hcd_130 == 8.0 and rec_21_6.hours.tcd_195 == 0.0,
          f"21h-6h (9.0h elapsed - 1h break) -> total={rec_21_6.hours.total_hours}, hcd={rec_21_6.hours.hcd_130}, tcd={rec_21_6.hours.tcd_195}")

    # 2.4: 20h-8h (12.0h elapsed, non-Sunday, no bracket -> 1h break deducted -> 11.0h net -> 8h HCĐ, 3h TCĐ)
    msg_20_8 = """
HỌ TÊN: NGUYỄN VĂN B
NGÀY: 24/10/2026
CA: Ca đêm
THỜI GIAN LÀM VIỆC: 20h-8h
CÓ ĂN Ở XƯỞNG KO: 0
"""
    rec_20_8 = parser.parse_single(msg_20_8)
    check("T2.4_CROSS_20H_8H",
          rec_20_8.hours.total_hours == 11.0 and rec_20_8.hours.hcd_130 == 8.0 and rec_20_8.hours.tcd_195 == 3.0,
          f"20h-8h (12.0h elapsed - 1h break) -> total={rec_20_8.hours.total_hours}, hcd={rec_20_8.hours.hcd_130}, tcd={rec_20_8.hours.tcd_195}")

    # 2.5: Inferred shift when CA is omitted for 22h-6h
    msg_22_6_noshift = """
HỌ TÊN: NGUYỄN VĂN B
NGÀY: 24/10/2026
THỜI GIAN LÀM VIỆC: 22h-6h
CÓ ĂN Ở XƯỞNG KO: 0
"""
    rec_22_6_noshift = parser.parse_single(msg_22_6_noshift)
    check("T2.5_CROSS_INFER_NIGHT",
          rec_22_6_noshift.shift_type == "NIGHT" and rec_22_6.hours.hcd_130 == 8.0 and rec_22_6_noshift.status == "WARNING",
          f"22h-6h with omitted shift -> inferred {rec_22_6_noshift.shift_type}, warnings={rec_22_6_noshift.messages}")

    # ---------------------------------------------------------
    # TEST SUITE 3: SUNDAY DAYTIME VS SUNDAY NIGHTTIME BUCKETS
    # ---------------------------------------------------------
    print("\n--- Suite 3: Sunday vs Weekday Bucket Isolation ---")

    # 2026-10-25 is Sunday
    # 3.1: Sunday Daytime 8h (8h-17h, 8H) -> all in sunday_day_200, 0 in weekday
    msg_sun_day_8h = """
HỌ TÊN: LÊ VĂN C
NGÀY: 25/10/2026
CA: Ca ngày
THỜI GIAN LÀM VIỆC: 8h-17h ( 8H)
CÓ ĂN Ở XƯỞNG KO: 1
"""
    rec_sun_day_8h = parser.parse_single(msg_sun_day_8h)
    check("T3.1_SUN_DAY_8H_ISOLATION",
          rec_sun_day_8h.is_sunday is True and
          rec_sun_day_8h.hours.sunday_day_200 == 8.0 and
          rec_sun_day_8h.hours.sunday_night_260 == 0.0 and
          rec_sun_day_8h.hours.hcn_100 == 0.0 and
          rec_sun_day_8h.hours.tcn_150 == 0.0 and
          rec_sun_day_8h.hours.hcd_130 == 0.0 and
          rec_sun_day_8h.hours.tcd_195 == 0.0,
          f"Sunday Day 8H -> sunday_day_200={rec_sun_day_8h.hours.sunday_day_200}, weekday all 0.0")

    # 3.2: Sunday Daytime Overtime 11h (8h-20h, 11H) -> all 11.0 in sunday_day_200
    msg_sun_day_11h = """
HỌ TÊN: LÊ VĂN C
NGÀY: 25/10/2026
CA: Ca ngày
THỜI GIAN LÀM VIỆC: 8h-20h (11H)
CÓ ĂN Ở XƯỞNG KO: 1
"""
    rec_sun_day_11h = parser.parse_single(msg_sun_day_11h)
    check("T3.2_SUN_DAY_11H_ISOLATION",
          rec_sun_day_11h.is_sunday is True and
          rec_sun_day_11h.hours.sunday_day_200 == 11.0 and
          rec_sun_day_11h.hours.sunday_night_260 == 0.0 and
          rec_sun_day_11h.hours.hcn_100 == 0.0 and
          rec_sun_day_11h.hours.tcn_150 == 0.0 and
          rec_sun_day_11h.hours.hcd_130 == 0.0 and
          rec_sun_day_11h.hours.tcd_195 == 0.0,
          f"Sunday Day 11H -> sunday_day_200={rec_sun_day_11h.hours.sunday_day_200}, weekday all 0.0")

    # 3.3: Sunday Night 8h (20h-5h, 8H) -> all in sunday_night_260, 0 in weekday
    msg_sun_night_8h = """
HỌ TÊN: LÊ VĂN C
NGÀY: 25/10/2026
CA: Ca đêm
THỜI GIAN LÀM VIỆC: 20h-5h ( 8H)
CÓ ĂN Ở XƯỞNG KO: 0
"""
    rec_sun_night_8h = parser.parse_single(msg_sun_night_8h)
    check("T3.3_SUN_NIGHT_8H_ISOLATION",
          rec_sun_night_8h.is_sunday is True and
          rec_sun_night_8h.hours.sunday_night_260 == 8.0 and
          rec_sun_night_8h.hours.sunday_day_200 == 0.0 and
          rec_sun_night_8h.hours.hcn_100 == 0.0 and
          rec_sun_night_8h.hours.tcn_150 == 0.0 and
          rec_sun_night_8h.hours.hcd_130 == 0.0 and
          rec_sun_night_8h.hours.tcd_195 == 0.0,
          f"Sunday Night 8H -> sunday_night_260={rec_sun_night_8h.hours.sunday_night_260}, weekday all 0.0")

    # 3.4: Sunday Night Overtime 12h (19h-8h, 12H) -> all in sunday_night_260
    msg_sun_night_12h = """
HỌ TÊN: LÊ VĂN C
NGÀY: 25/10/2026
CA: Ca đêm
THỜI GIAN LÀM VIỆC: 19h-8h (12H)
CÓ ĂN Ở XƯỞNG KO: 0
"""
    rec_sun_night_12h = parser.parse_single(msg_sun_night_12h)
    check("T3.4_SUN_NIGHT_12H_ISOLATION",
          rec_sun_night_12h.is_sunday is True and
          rec_sun_night_12h.hours.sunday_night_260 == 12.0 and
          rec_sun_night_12h.hours.sunday_day_200 == 0.0 and
          rec_sun_night_12h.hours.hcn_100 == 0.0 and
          rec_sun_night_12h.hours.tcn_150 == 0.0 and
          rec_sun_night_12h.hours.hcd_130 == 0.0 and
          rec_sun_night_12h.hours.tcd_195 == 0.0,
          f"Sunday Night 12H -> sunday_night_260={rec_sun_night_12h.hours.sunday_night_260}, weekday all 0.0")

    # 3.5: Non-Sunday shifts must NEVER spill into Sunday buckets
    msg_weekday_day = """
HỌ TÊN: LÊ VĂN C
NGÀY: 26/10/2026
CA: Ca ngày
THỜI GIAN LÀM VIỆC: 8h-20h (11H)
CÓ ĂN Ở XƯỞNG KO: 1
"""
    rec_weekday_day = parser.parse_single(msg_weekday_day)
    check("T3.5_WEEKDAY_NEVER_SPILLS_INTO_SUNDAY",
          rec_weekday_day.is_sunday is False and
          rec_weekday_day.hours.sunday_day_200 == 0.0 and
          rec_weekday_day.hours.sunday_night_260 == 0.0 and
          rec_weekday_day.hours.hcn_100 == 8.0 and
          rec_weekday_day.hours.tcn_150 == 3.0,
          f"Monday Day 11H -> hcn={rec_weekday_day.hours.hcn_100}, tcn={rec_weekday_day.hours.tcn_150}, Sunday buckets are 0.0")

    # ---------------------------------------------------------
    # TEST SUITE 4: BRACKETED OVERRIDES
    # ---------------------------------------------------------
    print("\n--- Suite 4: Bracketed Overrides ---")

    # 4.1: '8h-20h ( 10H)' -> total 10.0h -> HCN=8.0, TCN=2.0
    msg_br_10h = """
HỌ TÊN: PHẠM VĂN D
NGÀY: 24/10/2026
CA: Ca ngày
THỜI GIAN LÀM VIỆC: 8h-20h ( 10H)
CÓ ĂN Ở XƯỞNG KO: 1
"""
    rec_br_10h = parser.parse_single(msg_br_10h)
    check("T4.1_BRACKET_10H",
          rec_br_10h.hours.total_hours == 10.0 and rec_br_10h.hours.hcn_100 == 8.0 and rec_br_10h.hours.tcn_150 == 2.0 and rec_br_10h.status == "VALID",
          f"'8h-20h ( 10H)' -> total={rec_br_10h.hours.total_hours}, hcn={rec_br_10h.hours.hcn_100}, tcn={rec_br_10h.hours.tcn_150}, status={rec_br_10h.status}")

    # 4.2: '8h-20h ( 11H)' -> total 11.0h -> HCN=8.0, TCN=3.0
    msg_br_11h = """
HỌ TÊN: PHẠM VĂN D
NGÀY: 24/10/2026
CA: Ca ngày
THỜI GIAN LÀM VIỆC: 8h-20h ( 11H)
CÓ ĂN Ở XƯỞNG KO: 1
"""
    rec_br_11h = parser.parse_single(msg_br_11h)
    check("T4.2_BRACKET_11H",
          rec_br_11h.hours.total_hours == 11.0 and rec_br_11h.hours.hcn_100 == 8.0 and rec_br_11h.hours.tcn_150 == 3.0 and rec_br_11h.status == "VALID",
          f"'8h-20h ( 11H)' -> total={rec_br_11h.hours.total_hours}, hcn={rec_br_11h.hours.hcn_100}, tcn={rec_br_11h.hours.tcn_150}, status={rec_br_11h.status}")

    # 4.3: '8h-20h ( 12H)' -> total 12.0h -> HCN=8.0, TCN=4.0
    msg_br_12h = """
HỌ TÊN: PHẠM VĂN D
NGÀY: 24/10/2026
CA: Ca ngày
THỜI GIAN LÀM VIỆC: 8h-20h ( 12H)
CÓ ĂN Ở XƯỞNG KO: 1
"""
    rec_br_12h = parser.parse_single(msg_br_12h)
    check("T4.3_BRACKET_12H",
          rec_br_12h.hours.total_hours == 12.0 and rec_br_12h.hours.hcn_100 == 8.0 and rec_br_12h.hours.tcn_150 == 4.0 and rec_br_12h.status == "VALID",
          f"'8h-20h ( 12H)' -> total={rec_br_12h.hours.total_hours}, hcn={rec_br_12h.hours.hcn_100}, tcn={rec_br_12h.hours.tcn_150}, status={rec_br_12h.status}")

    # 4.4: Discrepancy warning when bracket > elapsed: '8h-17h ( 10H)' (elapsed=9h, br=10h)
    msg_br_disc = """
HỌ TÊN: PHẠM VĂN D
NGÀY: 24/10/2026
CA: Ca ngày
THỜI GIAN LÀM VIỆC: 8h-17h ( 10H)
CÓ ĂN Ở XƯỞNG KO: 1
"""
    rec_br_disc = parser.parse_single(msg_br_disc)
    check("T4.4_BRACKET_DISCREPANCY_WARNING",
          rec_br_disc.hours.total_hours == 10.0 and rec_br_disc.status == "WARNING" and any("lớn hơn thời gian chênh lệch" in m for m in rec_br_disc.messages),
          f"'8h-17h ( 10H)' -> total={rec_br_disc.hours.total_hours}, status={rec_br_disc.status}, messages={rec_br_disc.messages}")

    # 4.5: Decimal notation with comma: '8h-20h ( 10,5H)'
    msg_br_comma = """
HỌ TÊN: PHẠM VĂN D
NGÀY: 24/10/2026
CA: Ca ngày
THỜI GIAN LÀM VIỆC: 8h-20h ( 10,5H)
CÓ ĂN Ở XƯỞNG KO: 1
"""
    rec_br_comma = parser.parse_single(msg_br_comma)
    check("T4.5_BRACKET_COMMA_DECIMAL",
          rec_br_comma.hours.total_hours == 10.5 and rec_br_comma.hours.hcn_100 == 8.0 and rec_br_comma.hours.tcn_150 == 2.5,
          f"'8h-20h ( 10,5H)' -> total={rec_br_comma.hours.total_hours}, hcn={rec_br_comma.hours.hcn_100}, tcn={rec_br_comma.hours.tcn_150}")

    # ---------------------------------------------------------
    # TEST SUITE 5: EXTENDED ADVERSARIAL STRESS CASES
    # ---------------------------------------------------------
    print("\n--- Suite 5: Extended Adversarial Stress Cases ---")

    # 5.1: Zero hours: '8h-17h ( 0H)' -> triggers ERROR
    msg_zero = """
HỌ TÊN: PHẠM VĂN D
NGÀY: 24/10/2026
CA: Ca ngày
THỜI GIAN LÀM VIỆC: 8h-17h ( 0H)
CÓ ĂN Ở XƯỞNG KO: 1
"""
    rec_zero = parser.parse_single(msg_zero)
    check("T5.1_ZERO_HOURS_ERROR",
          rec_zero.status == "ERROR" and any("phải lớn hơn 0" in m for m in rec_zero.messages),
          f"0 hours -> status={rec_zero.status}, errors={rec_zero.messages}")

    # 5.2: Hours > 24: '8h-20h ( 25H)' -> triggers ERROR
    msg_overflow = """
HỌ TÊN: PHẠM VĂN D
NGÀY: 24/10/2026
CA: Ca ngày
THỜI GIAN LÀM VIỆC: 8h-20h ( 25H)
CÓ ĂN Ở XƯỞNG KO: 1
"""
    rec_overflow = parser.parse_single(msg_overflow)
    check("T5.2_OVERFLOW_HOURS_ERROR",
          rec_overflow.status == "ERROR" and any("vượt quá 24h" in m for m in rec_overflow.messages),
          f"25 hours -> status={rec_overflow.status}, errors={rec_overflow.messages}")

    # 5.3: Additive overtime notation: '8h-17h + TC 3h' -> 8 + 3 = 11h
    msg_ot_add = """
HỌ TÊN: PHẠM VĂN D
NGÀY: 24/10/2026
CA: Ca ngày
THỜI GIAN LÀM VIỆC: 8h-17h + TC 3h
CÓ ĂN Ở XƯỞNG KO: 1
"""
    rec_ot_add = parser.parse_single(msg_ot_add)
    check("T5.3_ADDITIVE_OVERTIME",
          rec_ot_add.hours.total_hours == 11.0 and rec_ot_add.hours.hcn_100 == 8.0 and rec_ot_add.hours.tcn_150 == 3.0,
          f"'8h-17h + TC 3h' -> total={rec_ot_add.hours.total_hours}, hcn={rec_ot_add.hours.hcn_100}, tcn={rec_ot_add.hours.tcn_150}")

    # 5.4: Both bracket and additive: bracket must take precedence without double counting
    msg_both = """
HỌ TÊN: PHẠM VĂN D
NGÀY: 24/10/2026
CA: Ca ngày
THỜI GIAN LÀM VIỆC: 8h-17h (11H) + TC 3h
CÓ ĂN Ở XƯỞNG KO: 1
"""
    rec_both = parser.parse_single(msg_both)
    check("T5.4_BRACKET_AND_ADDITIVE_NO_DOUBLE_COUNT",
          rec_both.hours.total_hours == 11.0,
          f"'(11H) + TC 3h' -> total={rec_both.hours.total_hours} (bracket 11H wins without +3h double count)")

    # 5.5: Non-standard separators in range: '8:00 – 17:00' (en-dash)
    msg_endash = """
HỌ TÊN: PHẠM VĂN D
NGÀY: 24/10/2026
CA: Ca ngày
THỜI GIAN LÀM VIỆC: 8:00 – 17:00
CÓ ĂN Ở XƯỞNG KO: 1
"""
    rec_endash = parser.parse_single(msg_endash)
    check("T5.5_ENDASH_TIME_RANGE",
          rec_endash.hours.total_hours == 8.0 and rec_endash.hours.hcn_100 == 8.0,
          f"'8:00 – 17:00' -> total={rec_endash.hours.total_hours}, hcn={rec_endash.hours.hcn_100}")

    print("\n" + "="*50)
    print(f"TEST RESULTS: {passed} PASSED, {failed} FAILED (TOTAL {passed + failed})")
    print("="*50)
    for r in results:
        print(r)

    if failed > 0:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    run_tests()
