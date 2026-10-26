"""
Independent Forensic Integrity & Adversarial Verification Script
Auditor: auditor_m1_it2
Target: core/parser.py
"""
import sys
import os
sys.path.insert(0, os.path.abspath("."))
import datetime
import random
import unicodedata
from core.parser import (
    AttendanceParser,
    parse_attendance_messages,
    parse_single_message,
    normalize_vietnamese_name,
    calculate_work_hours,
    extract_field_types,
)
from models.attendance import AttendanceRecord, WorkHours

def test_hardcoding_randomized():
    """Verify parser works on arbitrary randomized names and dates."""
    random_first = ["Nguyễn", "Trần", "Lê", "Phạm", "Hoàng", "Huỳnh", "Phan", "Vũ", "Võ", "Đặng", "Bùi", "Đỗ"]
    random_mid = ["Văn", "Thị", "Đức", "Minh", "Hữu", "Xuân", "Thanh", "Quốc", "Gia", "Bảo"]
    random_last = ["Hùng", "Lan", "Nam", "Phương", "Tuấn", "Thảo", "Long", "Dũng", "Khánh", "Cường"]

    parser = AttendanceParser()
    for i in range(50):
        name = f"{random.choice(random_first)} {random.choice(random_mid)} {random.choice(random_last)}"
        d = random.randint(1, 28)
        m = random.randint(1, 12)
        y = 2026
        dt = datetime.date(y, m, d)
        is_sun = (dt.weekday() == 6)
        shift = "Ca ngày" if i % 2 == 0 else "Ca đêm"
        expected_shift = "DAY" if i % 2 == 0 else "NIGHT"
        
        # Consistent time windows
        if shift == "Ca ngày":
            time_window = "8h-17h (8H)"
            expected_h = 8.0
        else:
            time_window = "20h-8h (11H)"
            expected_h = 11.0

        meal = random.choice([0, 1])

        raw = f"""HỌ TÊN: {name.lower()}
NGÀY: {d:02d}/{m:02d}/{y}
CA: {shift}
THỜI GIAN: {time_window}
CÓ ĂN Ở XƯỞNG KO: {meal}"""

        rec = parser.parse_single(raw)
        assert rec.status == "VALID", f"Randomized input failed: {raw} -> {rec.messages}"
        assert rec.employee_name == name.upper()
        assert rec.resolved_date == f"{y}-{m:02d}-{d:02d}"
        assert rec.day_number == d
        assert rec.is_sunday == is_sun
        assert rec.shift_type == expected_shift
        assert rec.meal_count == meal
        assert rec.hours.total_hours == expected_h
    print("PASS: test_hardcoding_randomized (50 dynamic cases)")

def test_boundary_checks():
    """Verify authentic boundary checks on negative hours, 24h clock, and meal digits."""
    parser = AttendanceParser()

    # 1. Negative hours
    neg_cases = ["-8h", "-5", "(-6H)", "8h - -4h", "8h to -4h", "8h đến -2h"]
    for neg in neg_cases:
        raw = f"HỌ TÊN: A\nNGÀY: 2026-10-24\nCA: Ca ngày\nTHỜI GIAN: {neg}\nĂN: 0"
        rec = parser.parse_single(raw)
        assert rec.status == "ERROR", f"Negative hours {neg} did not trigger ERROR"
        assert rec.hours.total_hours == 0.0
        assert any("số âm" in msg.lower() or "không hợp lệ" in msg.lower() for msg in rec.messages)
    print("PASS: Negative hours boundary checks")

    # 2. Clock bounds
    invalid_clock = ["25h-30h", "24h30-26h", "08h65-17h00", "08h00-17h60", "24h10-05h00"]
    for clk in invalid_clock:
        raw = f"HỌ TÊN: A\nNGÀY: 2026-10-24\nCA: Ca ngày\nTHỜI GIAN: {clk}\nĂN: 0"
        rec = parser.parse_single(raw)
        assert rec.status == "ERROR", f"Invalid clock {clk} did not trigger ERROR"
        assert any("24h" in msg or "không hợp lệ" in msg for msg in rec.messages)
    print("PASS: 24h clock boundary checks")

    # 3. CVE-2020-10735 digit bounds
    huge_meal = "9" * 10000
    raw = f"HỌ TÊN: A\nNGÀY: 2026-10-24\nCA: Ca ngày\nTHỜI GIAN: 8h-17h (8H)\nĂN: {huge_meal}"
    rec = parser.parse_single(raw)
    assert rec.meal_count == 9999
    assert any("bất thường" in msg for msg in rec.messages)
    print("PASS: Bounded meal integer conversion (10,000 digits)")

def test_dynamic_datetime_math():
    """Verify dynamic leap year and Sunday math."""
    parser = AttendanceParser()

    # Leap day in leap year
    rec_leap_valid = parser.parse_single("HỌ TÊN: A\nNGÀY: 29/02/2024\nCA: Ca ngày\nTHỜI GIAN: 8h-17h (8H)\nĂN: 0")
    assert rec_leap_valid.resolved_date == "2024-02-29"
    assert rec_leap_valid.status == "VALID"

    # Leap day in non-leap year
    rec_leap_invalid = parser.parse_single("HỌ TÊN: A\nNGÀY: 29/02/2026\nCA: Ca ngày\nTHỜI GIAN: 8h-17h (8H)\nĂN: 0")
    assert rec_leap_invalid.status == "ERROR"
    assert any("không hợp lệ" in msg for msg in rec_leap_invalid.messages)

    # Sunday calculation
    # 2026-10-25 is Sunday
    rec_sun = parser.parse_single("HỌ TÊN: A\nNGÀY: 25/10/2026\nCA: Ca ngày\nTHỜI GIAN: 8h-17h (8H)\nĂN: 0")
    assert rec_sun.is_sunday is True
    assert rec_sun.hours.sunday_day_200 == 8.0
    assert rec_sun.hours.hcn_100 == 0.0

    # 2026-10-25 Sunday Night
    rec_sun_night = parser.parse_single("HỌ TÊN: A\nNGÀY: 25/10/2026\nCA: Ca đêm\nTHỜI GIAN: 20h-5h (8H)\nĂN: 0")
    assert rec_sun_night.is_sunday is True
    assert rec_sun_night.hours.sunday_night_260 == 8.0
    assert rec_sun_night.hours.hcd_130 == 0.0

    print("PASS: Dynamic datetime & leap year math")

def test_segmentation_and_lookahead():
    """Verify message segmentation and TÊN DỰ ÁN negative lookahead."""
    parser = AttendanceParser()

    # TÊN DỰ ÁN collision test
    raw_proj = """HỌ TÊN: VŨ ĐÌNH TRỌNG
NGÀY: 24/10/2026
CA: Ca ngày
TÊN DỰ ÁN: NHÀ MÁY ĐIỆN NHƠN TRẠCH 3
THỜI GIAN: 8h-17h (8H)
CƠM Ở XƯỞNG: 1"""
    rec_proj = parser.parse_single(raw_proj)
    assert rec_proj.employee_name == "VŨ ĐÌNH TRỌNG"
    assert rec_proj.project == "NHÀ MÁY ĐIỆN NHƠN TRẠCH 3"
    assert rec_proj.status == "VALID"

    # Multi-line with internal blanks
    batch_with_blanks = """HỌ TÊN: BÙI QUANG HUY

NGÀY: 2026-10-24

CA: Ca ngày

THỜI GIAN: 8h-17h (8H)

ĂN: 0

HỌ TÊN: PHAN TIẾN DŨNG

NGÀY: 2026-10-24
THỜI GIAN: 8h-17h (8H)"""
    records = parser.parse_batch(batch_with_blanks)
    assert len(records) == 2
    assert records[0].employee_name == "BÙI QUANG HUY"
    assert records[0].status == "VALID"
    assert records[1].employee_name == "PHAN TIẾN DŨNG"
    # Second record inferred shift from start hour and defaulted meal to 0 -> status WARNING
    assert records[1].status == "WARNING"
    assert records[1].shift_type == "DAY"
    assert records[1].meal_count == 0
    assert any("nhận diện ca" in msg.lower() for msg in records[1].messages)

    print("PASS: Segmentation & negative lookahead tests")

def test_robustness_weird_inputs():
    """Verify parser never crashes on extreme inputs."""
    parser = AttendanceParser()
    weird_inputs = [
        None,
        12345,
        3.14159,
        [],
        {},
        "",
        "   ",
        "\n\n\t\n",
        "??? :::: ---",
        "A" * 100000,
        "\x00\x01\x02\x03\x04\x05",
    ]
    for w in weird_inputs:
        rec = parser.parse_single(w)
        assert isinstance(rec, AttendanceRecord)
        assert rec.status == "ERROR"

    chunks = parser.split_messages(None)
    assert chunks == []
    chunks = parser.split_messages("")
    assert chunks == []

    print("PASS: Robustness against non-string and malformed inputs")

if __name__ == "__main__":
    test_hardcoding_randomized()
    test_boundary_checks()
    test_dynamic_datetime_math()
    test_segmentation_and_lookahead()
    test_robustness_weird_inputs()
    print("\nALL FORENSIC AUDIT CHECKS PASSED EMPIRICALLY!")
