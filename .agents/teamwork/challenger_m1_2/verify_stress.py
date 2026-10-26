"""
Adversarial stress harness for parser edge cases.
"""
import sys
WORKSPACE_ROOT = "/Users/congcm/CODE/Vibe_Code/Zalo_BOT"
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

from core.parser import AttendanceParser, calculate_work_hours

def test_stress():
    parser = AttendanceParser(default_year=2026)
    
    # 1. Minute arithmetic across midnight
    # 20h30 - 5h15 -> (5 + 24 - 20) + (15 - 30)/60 = 9 - 0.25 = 8.75h elapsed
    # >= 8.5h -> deduct 1h break -> 7.75h net
    rec1 = parser.parse_single("""
HỌ TÊN: TEST A
NGÀY: 24/10/2026
CA: Ca đêm
THỜI GIAN LÀM VIỆC: 20h30 - 5h15
CÓ ĂN Ở XƯỞNG KO: 0
""")
    assert rec1.hours.total_hours == 7.75, f"Expected 7.75, got {rec1.hours.total_hours}"
    assert rec1.hours.hcd_130 == 7.75, f"Expected 7.75, got {rec1.hours.hcd_130}"
    assert rec1.hours.tcd_195 == 0.0

    # 2. Bracket variations: '(8 tiếng)', '(8.5 giờ)', '( 8,5g )'
    rec2a = parser.parse_single("""
HỌ TÊN: TEST B
NGÀY: 24/10/2026
CA: Ca ngày
THỜI GIAN LÀM VIỆC: 8h-17h (8 tiếng)
CÓ ĂN Ở XƯỞNG KO: 1
""")
    assert rec2a.hours.total_hours == 8.0, f"Expected 8.0, got {rec2a.hours.total_hours}"

    rec2b = parser.parse_single("""
HỌ TÊN: TEST B
NGÀY: 24/10/2026
CA: Ca ngày
THỜI GIAN LÀM VIỆC: 8h-17h (8.5 giờ)
CÓ ĂN Ở XƯỞNG KO: 1
""")
    assert rec2b.hours.total_hours == 8.5, f"Expected 8.5, got {rec2b.hours.total_hours}"
    assert rec2b.hours.hcn_100 == 8.0
    assert rec2b.hours.tcn_150 == 0.5

    rec2c = parser.parse_single("""
HỌ TÊN: TEST B
NGÀY: 24/10/2026
CA: Ca ngày
THỜI GIAN LÀM VIỆC: 8h-17h ( 8,5g )
CÓ ĂN Ở XƯỞNG KO: 1
""")
    assert rec2c.hours.total_hours == 8.5, f"Expected 8.5, got {rec2c.hours.total_hours}"

    # 3. Direct calculate_work_hours edge cases
    # Floating point precision check: 8.01h
    wh_float = calculate_work_hours(8.01, "DAY", False)
    assert wh_float.hcn_100 == 8.0 and wh_float.tcn_150 == 0.01

    # Negative hours
    wh_neg = calculate_work_hours(-5.0, "DAY", False)
    assert wh_neg.total_hours == 0.0 and wh_neg.hcn_100 == 0.0

    # Sunday daytime 14 hours
    wh_sun_14 = calculate_work_hours(14.0, "DAY", True)
    assert wh_sun_14.sunday_day_200 == 14.0
    assert wh_sun_14.hcn_100 == 0.0
    assert wh_sun_14.tcn_150 == 0.0
    assert wh_sun_14.hcd_130 == 0.0
    assert wh_sun_14.tcd_195 == 0.0
    assert wh_sun_14.sunday_night_260 == 0.0

    # Sunday nighttime 14 hours
    wh_sun_night_14 = calculate_work_hours(14.0, "NIGHT", True)
    assert wh_sun_night_14.sunday_night_260 == 14.0
    assert wh_sun_night_14.sunday_day_200 == 0.0
    assert wh_sun_night_14.hcn_100 == 0.0
    assert wh_sun_night_14.tcn_150 == 0.0
    assert wh_sun_night_14.hcd_130 == 0.0
    assert wh_sun_night_14.tcd_195 == 0.0

    print("All adversarial stress tests passed successfully!")

if __name__ == "__main__":
    test_stress()
