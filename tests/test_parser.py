"""
Unit Test Suite for Attendance Parser (Milestone 1).
Covers Acceptance Criteria, Edge Cases, Boundary Conditions, Rate Allocation,
Vietnamese Normalization, and Zero-Crash Resilience.
"""
import pytest
from core.parser import (
    AttendanceParser,
    parse_attendance_messages,
    parse_single_message,
    normalize_vietnamese_name,
    calculate_work_hours,
)
from models.attendance import AttendanceRecord, WorkHours


class TestAttendanceParserAcceptance:
    """Acceptance criteria test cases from ORIGINAL_REQUEST.md."""

    def test_acceptance_criteria_standard_message(self):
        """
        Original Acceptance Criteria:
        HỌ TÊN : HOÀNG ĐẮC PHÚ
        NGÀY: 24/10
        CA : Ca ngày 
        DỰ ÁN : sdv 
        THỜI GIAN LÀM VIỆC :8h-17h ( 8H)
        CÓ ĂN Ở XƯỞNG KO : 0
        => Tên = 'HOÀNG ĐẮC PHÚ', Ngày = '24/10', HCN = 8, Suất ăn = 0.
        """
        raw = """HỌ TÊN : HOÀNG ĐẮC PHÚ
NGÀY: 24/10
CA : Ca ngày 
DỰ ÁN : sdv 
THỜI GIAN LÀM VIỆC :8h-17h ( 8H)
CÓ ĂN Ở XƯỞNG KO : 0"""

        record = parse_single_message(raw, default_year=2026)

        assert record.employee_name == "HOÀNG ĐẮC PHÚ"
        assert record.normalized_name == "Hoàng Đắc Phú"
        assert record.date_str == "24/10"
        assert record.resolved_date == "2026-10-24"
        assert record.day_number == 24
        assert record.is_sunday is False
        assert record.shift_type == "DAY"
        assert record.project == "sdv"
        assert record.hours.hcn_100 == 8.0
        assert record.hours.tcn_150 == 0.0
        assert record.hours.hcd_130 == 0.0
        assert record.hours.tcd_195 == 0.0
        assert record.hours.sunday_day_200 == 0.0
        assert record.hours.sunday_night_260 == 0.0
        assert record.hours.total_hours == 8.0
        assert record.meal_count == 0
        assert record.status == "WARNING"  # Inferred year 2026
        assert any("2026" in msg for msg in record.messages)

    def test_acceptance_with_full_date(self):
        """Standard message with explicit year 2026 should be completely VALID."""
        raw = """HỌ TÊN : HOÀNG ĐẮC PHÚ
NGÀY: 24/10/2026
CA : Ca ngày 
DỰ ÁN : sdv 
THỜI GIAN LÀM VIỆC :8h-17h ( 8H)
CÓ ĂN Ở XƯỞNG KO : 0"""

        record = parse_single_message(raw)
        assert record.employee_name == "HOÀNG ĐẮC PHÚ"
        assert record.resolved_date == "2026-10-24"
        assert record.status == "VALID"
        assert len(record.messages) == 0


class TestVietnameseNameNormalization:
    """Tests for Vietnamese name extraction and normalization."""

    def test_name_trimming_and_casing(self):
        assert normalize_vietnamese_name("   hoàng   đắc   phú   ", title_case=True) == "Hoàng Đắc Phú"
        assert normalize_vietnamese_name("   hoàng   đắc   phú   ", title_case=False) == "HOÀNG ĐẮC PHÚ"

    def test_name_with_phone_number_stripped(self):
        raw = """HỌ TÊN : NGUYỄN VĂN A - 0987654321
NGÀY: 24/10/2026
CA : Ca ngày
THỜI GIAN: 8h-17h (8H)
CÓ ĂN Ở XƯỞNG KO : 0"""
        record = parse_single_message(raw)
        assert record.employee_name == "NGUYỄN VĂN A"
        assert record.normalized_name == "Nguyễn Văn A"

    def test_name_with_parenthesized_note_stripped(self):
        raw = """HỌ TÊN: TRẦN THỊ MAI (TỔ 3 - THỢ HÀN)
NGÀY: 24/10/2026
CA: Ca ngày
THỜI GIAN: 8h-17h (8H)
ĂN XƯỞNG: 1"""
        record = parse_single_message(raw)
        assert record.employee_name == "TRẦN THỊ MAI"
        assert record.normalized_name == "Trần Thị Mai"

    def test_name_unaccented_preserved(self):
        raw = """HỌ TÊN: HOANG DAC PHU
NGÀY: 24/10/2026
CA: Ca ngày
THỜI GIAN: 8h-17h (8H)
ĂN XƯỞNG: 0"""
        record = parse_single_message(raw)
        assert record.employee_name == "HOANG DAC PHU"
        assert record.normalized_name == "Hoang Dac Phu"

    def test_missing_name_triggers_error(self):
        raw = """NGÀY: 24/10/2026
CA: Ca ngày
THỜI GIAN: 8h-17h (8H)
ĂN XƯỞNG: 0"""
        record = parse_single_message(raw)
        assert record.status == "ERROR"
        assert any("Họ và tên" in msg for msg in record.messages)

    def test_empty_punctuation_name_triggers_error(self):
        raw = """HỌ TÊN: ---
NGÀY: 24/10/2026
CA: Ca ngày
THỜI GIAN: 8h-17h (8H)
ĂN XƯỞNG: 0"""
        record = parse_single_message(raw)
        assert record.status == "ERROR"


class TestDateParsingAndSundayResolution:
    """Tests for multi-format dates, default year 2026, and Sunday resolution."""

    @pytest.mark.parametrize(
        "date_input,expected_iso,expected_day,expected_warning",
        [
            ("24/10", "2026-10-24", 24, True),
            ("24-10", "2026-10-24", 24, True),
            ("24.10", "2026-10-24", 24, True),
            ("24/10/2026", "2026-10-24", 24, False),
            ("24-10-2026", "2026-10-24", 24, False),
            ("24.10.2026", "2026-10-24", 24, False),
            ("2026-10-24", "2026-10-24", 24, False),
            ("2026/10/24", "2026-10-24", 24, False),
            ("24/10/26", "2026-10-24", 24, False),
            ("ngày 24/10", "2026-10-24", 24, True),
        ],
    )
    def test_valid_date_formats(self, date_input, expected_iso, expected_day, expected_warning):
        raw = f"""HỌ TÊN: LÊ VĂN C
NGÀY: {date_input}
CA: Ca ngày
THỜI GIAN: 8h-17h (8H)
ĂN XƯỞNG: 0"""
        record = parse_single_message(raw)
        assert record.resolved_date == expected_iso
        assert record.day_number == expected_day
        has_year_warning = any("Năm được tự động suy luận" in msg for msg in record.messages)
        assert has_year_warning == expected_warning

    @pytest.mark.parametrize(
        "invalid_date",
        [
            "32/10",
            "00/10",
            "29/02/2026",  # 2026 is non-leap year
            "31/04/2026",  # April has 30 days
            "abc/xyz",
            "2026-13-01",
        ],
    )
    def test_invalid_dates_trigger_error(self, invalid_date):
        raw = f"""HỌ TÊN: LÊ VĂN C
NGÀY: {invalid_date}
CA: Ca ngày
THỜI GIAN: 8h-17h (8H)
ĂN XƯỞNG: 0"""
        record = parse_single_message(raw)
        assert record.status == "ERROR"
        assert any("Ngày không hợp lệ" in msg for msg in record.messages)

    def test_missing_date_field_triggers_error(self):
        raw = """HỌ TÊN: LÊ VĂN C
CA: Ca ngày
THỜI GIAN: 8h-17h (8H)
ĂN XƯỞNG: 0"""
        record = parse_single_message(raw)
        assert record.status == "ERROR"
        assert any("Ngày chấm công" in msg for msg in record.messages)

    def test_sunday_flag_resolution(self):
        # 2026-10-24 is Saturday (is_sunday = False)
        # 2026-10-25 is Sunday (is_sunday = True)
        r_sat = parse_single_message("""HỌ TÊN: A\nNGÀY: 2026-10-24\nCA: Ca ngày\nTHỜI GIAN: 8h-17h (8H)\nĂN: 0""")
        r_sun = parse_single_message("""HỌ TÊN: A\nNGÀY: 2026-10-25\nCA: Ca ngày\nTHỜI GIAN: 8h-17h (8H)\nĂN: 0""")

        assert r_sat.is_sunday is False
        assert r_sun.is_sunday is True


class TestShiftAndHoursCalculation:
    """Tests for Day/Night shifts, break deduction, rate-tier allocation."""

    def test_day_shift_regular_8h(self):
        raw = """HỌ TÊN: A
NGÀY: 2026-10-24
CA: Ca ngày
THỜI GIAN: 8h-17h (8H)
ĂN: 0"""
        r = parse_single_message(raw)
        assert r.shift_type == "DAY"
        assert r.hours.hcn_100 == 8.0
        assert r.hours.tcn_150 == 0.0
        assert r.hours.total_hours == 8.0

    def test_day_shift_overtime_11h(self):
        raw = """HỌ TÊN: A
NGÀY: 2026-10-24
CA: Ca ngày
THỜI GIAN: 8h-20h (11H)
ĂN: 1"""
        r = parse_single_message(raw)
        assert r.shift_type == "DAY"
        assert r.hours.hcn_100 == 8.0
        assert r.hours.tcn_150 == 3.0
        assert r.hours.total_hours == 11.0

    def test_night_shift_regular_8h(self):
        raw = """HỌ TÊN: A
NGÀY: 2026-10-24
CA: Ca đêm
THỜI GIAN: 20h-5h ( 8H)
ĂN: 0"""
        r = parse_single_message(raw)
        assert r.shift_type == "NIGHT"
        assert r.hours.hcd_130 == 8.0
        assert r.hours.tcd_195 == 0.0
        assert r.hours.hcn_100 == 0.0
        assert r.hours.total_hours == 8.0

    def test_night_shift_overtime_11h(self):
        raw = """HỌ TÊN: A
NGÀY: 2026-10-24
CA: Ca đêm
THỜI GIAN: 20h-8h (11H)
ĂN: 1"""
        r = parse_single_message(raw)
        assert r.shift_type == "NIGHT"
        assert r.hours.hcd_130 == 8.0
        assert r.hours.tcd_195 == 3.0
        assert r.hours.hcn_100 == 0.0
        assert r.hours.total_hours == 11.0

    def test_sunday_day_shift_all_mapped_to_sunday_row(self):
        raw = """HỌ TÊN: A
NGÀY: 2026-10-25
CA: Ca ngày
THỜI GIAN: 8h-20h (11H)
ĂN: 1"""
        r = parse_single_message(raw)
        assert r.is_sunday is True
        assert r.hours.sunday_day_200 == 11.0
        assert r.hours.hcn_100 == 0.0
        assert r.hours.tcn_150 == 0.0
        assert r.hours.total_hours == 11.0

    def test_sunday_night_shift_all_mapped_to_sunday_night_row(self):
        raw = """HỌ TÊN: A
NGÀY: 2026-10-25
CA: Ca đêm
THỜI GIAN: 20h-8h (11H)
ĂN: 1"""
        r = parse_single_message(raw)
        assert r.is_sunday is True
        assert r.hours.sunday_night_260 == 11.0
        assert r.hours.hcd_130 == 0.0
        assert r.hours.tcd_195 == 0.0
        assert r.hours.total_hours == 11.0

    def test_automatic_break_deduction_without_bracket(self):
        # 8h-17h: elapsed 9h >= 8.5h -> 1h break deducted = 8h
        r1 = parse_single_message("""HỌ TÊN: A\nNGÀY: 2026-10-24\nCA: Ca ngày\nTHỜI GIAN: 8h-17h\nĂN: 0""")
        assert r1.hours.total_hours == 8.0
        assert r1.hours.hcn_100 == 8.0

        # 8h-20h: elapsed 12h >= 8.5h -> 1h break deducted = 11h
        r2 = parse_single_message("""HỌ TÊN: A\nNGÀY: 2026-10-24\nCA: Ca ngày\nTHỜI GIAN: 8h-20h\nĂN: 0""")
        assert r2.hours.total_hours == 11.0
        assert r2.hours.hcn_100 == 8.0
        assert r2.hours.tcn_150 == 3.0

        # 20h-5h: elapsed 9h >= 8.5h -> 1h break deducted = 8h
        r3 = parse_single_message("""HỌ TÊN: A\nNGÀY: 2026-10-24\nCA: Ca đêm\nTHỜI GIAN: 20h-5h\nĂN: 0""")
        assert r3.hours.total_hours == 8.0
        assert r3.hours.hcd_130 == 8.0

        # 20h-8h: elapsed 12h >= 8.5h -> 1h break deducted = 11h
        r4 = parse_single_message("""HỌ TÊN: A\nNGÀY: 2026-10-24\nCA: Ca đêm\nTHỜI GIAN: 20h-8h\nĂN: 0""")
        assert r4.hours.total_hours == 11.0
        assert r4.hours.hcd_130 == 8.0
        assert r4.hours.tcd_195 == 3.0

    def test_short_shift_no_break_deducted(self):
        # 8h-12h: elapsed 4h < 8.5h -> 4h net
        r = parse_single_message("""HỌ TÊN: A\nNGÀY: 2026-10-24\nCA: Ca ngày\nTHỜI GIAN: 8h-12h\nĂN: 0""")
        assert r.hours.total_hours == 4.0
        assert r.hours.hcn_100 == 4.0

    def test_overtime_additive_notation(self):
        # 8h-17h + TC 3h = 8 + 3 = 11h
        r = parse_single_message("""HỌ TÊN: A\nNGÀY: 2026-10-24\nCA: Ca ngày\nTHỜI GIAN: 8h-17h + TC 3h\nĂN: 0""")
        assert r.hours.total_hours == 11.0
        assert r.hours.hcn_100 == 8.0
        assert r.hours.tcn_150 == 3.0

    def test_standalone_hours_format(self):
        r1 = parse_single_message("""HỌ TÊN: A\nNGÀY: 2026-10-24\nCA: Ca ngày\nTHỜI GIAN: 8H\nĂN: 0""")
        assert r1.hours.total_hours == 8.0

        r2 = parse_single_message("""HỌ TÊN: A\nNGÀY: 2026-10-24\nCA: Ca ngày\nTHỜI GIAN: 11 tiếng\nĂN: 0""")
        assert r2.hours.total_hours == 11.0

    def test_shift_inference_from_start_hour(self):
        # Start at 20:00 -> NIGHT shift inferred
        r_night = parse_single_message("""HỌ TÊN: A\nNGÀY: 2026-10-24\nTHỜI GIAN: 20h-5h (8H)\nĂN: 0""")
        assert r_night.shift_type == "NIGHT"
        assert any("Tự động nhận diện Ca đêm" in m for m in r_night.messages)

        # Start at 8:00 -> DAY shift inferred
        r_day = parse_single_message("""HỌ TÊN: A\nNGÀY: 2026-10-24\nTHỜI GIAN: 8h-17h (8H)\nĂN: 0""")
        assert r_day.shift_type == "DAY"
        assert any("Tự động nhận diện Ca ngày" in m for m in r_day.messages)

    def test_unparseable_hours_triggers_error(self):
        r_sick = parse_single_message("""HỌ TÊN: A\nNGÀY: 2026-10-24\nCA: Ca ngày\nTHỜI GIAN: nghỉ ốm\nĂN: 0""")
        assert r_sick.status == "ERROR"
        assert any("nghỉ ốm" in m for m in r_sick.messages)

    def test_hours_overflow_exceeds_24h_triggers_error(self):
        r = parse_single_message("""HỌ TÊN: A\nNGÀY: 2026-10-24\nCA: Ca ngày\nTHỜI GIAN: 25h\nĂN: 0""")
        assert r.status == "ERROR"
        assert any("vượt quá 24h" in m for m in r.messages)


class TestMealCountDetection:
    """Tests for meal allowance normalization across various input formats."""

    @pytest.mark.parametrize("meal_str", ["0", "không", "khong", "ko", "k", "tự túc", "0 suất", "ko ăn", "k ăn"])
    def test_meal_zero(self, meal_str):
        raw = f"""HỌ TÊN: A\nNGÀY: 2026-10-24\nCA: Ca ngày\nTHỜI GIAN: 8h-17h (8H)\nCÓ ĂN Ở XƯỞNG KO: {meal_str}"""
        r = parse_single_message(raw)
        assert r.meal_count == 0

    @pytest.mark.parametrize("meal_str", ["1", "có", "co", "yes", "x", "X", "v", "V", "✓", "1 suất", "có ăn"])
    def test_meal_one(self, meal_str):
        raw = f"""HỌ TÊN: A\nNGÀY: 2026-10-24\nCA: Ca ngày\nTHỜI GIAN: 8h-17h (8H)\nCÓ ĂN Ở XƯỞNG KO: {meal_str}"""
        r = parse_single_message(raw)
        assert r.meal_count == 1

    def test_meal_two_with_warning(self):
        raw = """HỌ TÊN: A\nNGÀY: 2026-10-24\nCA: Ca ngày\nTHỜI GIAN: 8h-17h (8H)\nCÓ ĂN Ở XƯỞNG KO: 2"""
        r = parse_single_message(raw)
        assert r.meal_count == 2
        assert any("2 suất" in m for m in r.messages)

    def test_missing_meal_defaults_to_zero_with_warning(self):
        raw = """HỌ TÊN: A\nNGÀY: 2026-10-24\nCA: Ca ngày\nTHỜI GIAN: 8h-17h (8H)"""
        r = parse_single_message(raw)
        assert r.meal_count == 0
        assert any("Thiếu thông tin suất ăn" in m for m in r.messages)

    def test_ambiguous_meal_defaults_to_zero_with_warning(self):
        raw = """HỌ TÊN: A\nNGÀY: 2026-10-24\nCA: Ca ngày\nTHỜI GIAN: 8h-17h (8H)\nCÓ ĂN Ở XƯỞNG KO: chưa rõ"""
        r = parse_single_message(raw)
        assert r.meal_count == 0
        assert any("chưa rõ" in m for m in r.messages)


class TestSingleLineAndBatchSegmentation:
    """Tests for single-line format and multi-message batching."""

    def test_single_line_hyphen_separated(self):
        raw = "HỌ TÊN: HOÀNG ĐẮC PHÚ - NGÀY: 24/10/2026 - CA: Ca ngày - THỜI GIAN: 8h-17h (8H) - ĂN: 0"
        r = parse_single_message(raw)
        assert r.employee_name == "HOÀNG ĐẮC PHÚ"
        assert r.resolved_date == "2026-10-24"
        assert r.shift_type == "DAY"
        assert r.hours.hcn_100 == 8.0
        assert r.meal_count == 0
        assert r.status == "VALID"

    def test_batch_segmentation_contiguous_without_blank_lines(self):
        raw = """HỌ TÊN: HOÀNG ĐẮC PHÚ
NGÀY: 24/10/2026
CA: Ca ngày
THỜI GIAN: 8h-17h (8H)
CÓ ĂN Ở XƯỞNG KO: 0
HỌ TÊN: NGUYỄN NGỌC THAO
NGÀY: 24/10/2026
CA: Ca ngày
THỜI GIAN: 8h-20h (11H)
CÓ ĂN Ở XƯỞNG KO: 1"""

        records = parse_attendance_messages(raw)
        assert len(records) == 2
        assert records[0].employee_name == "HOÀNG ĐẮC PHÚ"
        assert records[0].hours.hcn_100 == 8.0
        assert records[1].employee_name == "NGUYỄN NGỌC THAO"
        assert records[1].hours.tcn_150 == 3.0

    def test_batch_segmentation_with_list_numbers_and_timestamps(self):
        raw = """[18:05, 24/10/2026] Hoàng Đắc Phú: HỌ TÊN : HOÀNG ĐẮC PHÚ
NGÀY: 24/10/2026
CA : Ca ngày 
THỜI GIAN LÀM VIỆC :8h-17h ( 8H)
CÓ ĂN Ở XƯỞNG KO : 0

1. HỌ TÊN: NGUYỄN ĐỨC CÔNG
NGÀY: 24/10/2026
CA: Ca đêm
THỜI GIAN LÀM VIỆC: 20h-5h ( 8H)
CÓ ĂN Ở XƯỞNG KO: 0"""

        records = parse_attendance_messages(raw)
        assert len(records) == 2
        assert records[0].employee_name == "HOÀNG ĐẮC PHÚ"
        assert records[1].employee_name == "NGUYỄN ĐỨC CÔNG"
        assert records[1].shift_type == "NIGHT"

    def test_empty_or_whitespace_input(self):
        assert parse_attendance_messages("") == []
        assert parse_attendance_messages("   \n\n  \t  ") == []


class TestNonCrashingResilience:
    """Tests ensuring the parser never raises unhandled exceptions on garbage text."""

    def test_garbage_text_returns_error_record(self):
        raw = "Dòng này hoàn toàn vô nghĩa và không có cấu trúc chấm công nào cả"
        record = parse_single_message(raw)
        assert isinstance(record, AttendanceRecord)
        assert record.status == "ERROR"
        assert len(record.messages) > 0

    def test_mixed_valid_and_corrupt_records(self):
        raw = """HỌ TÊN: HOÀNG ĐẮC PHÚ
NGÀY: 24/10/2026
CA: Ca ngày
THỜI GIAN: 8h-17h (8H)
ĂN: 0

DÒNG LỖI HOÀN TOÀN

HỌ TÊN: TÔ VĂN HƯNG
NGÀY: 24/10/2026
CA: Ca đêm
THỜI GIAN: 20h-8h (11H)
ĂN: 1"""

        records = parse_attendance_messages(raw)
        assert len(records) == 3
        assert records[0].status == "VALID"
        assert records[1].status == "ERROR"
        assert records[2].status == "VALID"


class TestAdvancedEdgeCases:
    """Advanced formatting edge cases: Asian colons, minutes, multi-shift combinations."""

    def test_asian_fullwidth_colon(self):
        raw = """HỌ TÊN：HOÀNG ĐẮC PHÚ
NGÀY：24/10/2026
CA：Ca ngày
THỜI GIAN LÀM VIỆC：8h-17h (8H)
CÓ ĂN Ở XƯỞNG KO：0"""
        r = parse_single_message(raw)
        assert r.employee_name == "HOÀNG ĐẮC PHÚ"
        assert r.resolved_date == "2026-10-24"
        assert r.shift_type == "DAY"
        assert r.hours.hcn_100 == 8.0
        assert r.status == "VALID"

    def test_missing_colons_whitespace_separated(self):
        raw = """HỌ TÊN HOÀNG ĐẮC PHÚ
NGÀY 24/10/2026
CA Ca ngày
THỜI GIAN 8h-17h (8H)
CÓ ĂN Ở XƯỞNG KO 0"""
        r = parse_single_message(raw)
        assert r.employee_name == "HOÀNG ĐẮC PHÚ"
        assert r.resolved_date == "2026-10-24"
        assert r.hours.hcn_100 == 8.0
        assert r.status == "VALID"

    def test_minutes_in_time_range(self):
        # 8h30-17h30: elapsed 9.0h -> 1h break deducted = 8.0h
        raw = """HỌ TÊN: A
NGÀY: 2026-10-24
CA: Ca ngày
THỜI GIAN: 8h30-17h30
ĂN: 0"""
        r = parse_single_message(raw)
        assert r.hours.total_hours == 8.0
        assert r.hours.hcn_100 == 8.0

    def test_night_shift_12h_overtime(self):
        # 19h-8h: elapsed 13.0h -> 1h break deducted = 12.0h -> 8h HCĐ, 4h TCĐ
        raw = """HỌ TÊN: A
NGÀY: 2026-10-24
CA: Ca đêm
THỜI GIAN: 19h-8h
ĂN: 1"""
        r = parse_single_message(raw)
        assert r.hours.total_hours == 12.0
        assert r.hours.hcd_130 == 8.0
        assert r.hours.tcd_195 == 4.0

    def test_sunday_night_shift_with_overtime_12h(self):
        # Sunday Night 12h: all in sunday_night_260
        raw = """HỌ TÊN: A
NGÀY: 2026-10-25
CA: Ca đêm
THỜI GIAN: 19h-8h
ĂN: 1"""
        r = parse_single_message(raw)
        assert r.is_sunday is True
        assert r.hours.sunday_night_260 == 12.0
        assert r.hours.hcd_130 == 0.0
        assert r.hours.tcd_195 == 0.0


class TestRemediationEdgeCases:
    """Tests covering adversarial stress findings and parser remediation fixes."""

    def test_none_and_non_string_input_safe(self):
        """None or non-string objects should safely return ERROR record without crashing."""
        r_none = parse_single_message(None)
        assert r_none.status == "ERROR"
        assert any("không hợp lệ" in msg.lower() for msg in r_none.messages)

        r_int = parse_single_message(12345)
        assert r_int.status == "ERROR"

        r_empty = parse_single_message("   \n   ")
        assert r_empty.status == "ERROR"

    def test_negative_hours_rejected(self):
        """Negative hours (-5h, (-5H), -8h to -4h) must result in ERROR status and 0 allocated hours."""
        for neg_hours in ["-5h", "(-5H)", "-8h to -4h", "8h - -4h"]:
            raw = f"""HỌ TÊN: NGUYỄN VĂN A
NGÀY: 2026-10-24
CA: Ca ngày
THỜI GIAN: {neg_hours}
ĂN: 0"""
            r = parse_single_message(raw)
            assert r.status == "ERROR", f"Failed for {neg_hours}: got status {r.status}"
            assert r.hours.total_hours == 0.0
            assert any("số âm" in msg.lower() or "không hợp lệ" in msg.lower() for msg in r.messages)

    def test_clock_hours_out_of_bounds_rejected(self):
        """Out of bounds clock hours like 25h-30h or 24h30-26h must be rejected with ERROR."""
        for invalid_time in ["25h-30h", "24h30-25h"]:
            raw = f"""HỌ TÊN: NGUYỄN VĂN A
NGÀY: 2026-10-24
CA: Ca ngày
THỜI GIAN: {invalid_time}
ĂN: 0"""
            r = parse_single_message(raw)
            assert r.status == "ERROR"
            assert any("24h" in msg for msg in r.messages)

    def test_ambiguous_shift_day_night_tokens(self):
        """Shift with conflicting tokens like 'Ca ngày đêm' should default to DAY with warning."""
        raw = """HỌ TÊN: NGUYỄN VĂN A
NGÀY: 2026-10-24
CA: Ca ngày đêm
THỜI GIAN: 8h-17h (8H)
ĂN: 0"""
        r = parse_single_message(raw)
        assert r.shift_type == "DAY"
        assert any("không rõ ràng" in msg for msg in r.messages)

    def test_internal_blank_lines_not_fragmented(self):
        """Message with internal blank lines should be parsed as a single record, not shattered."""
        batch = """HỌ TÊN: NGUYỄN VĂN A

NGÀY: 2026-10-24

CA: Ca ngày

THỜI GIAN: 8h-17h (8H)

ĂN: 0

HỌ TÊN: TRẦN VĂN B

NGÀY: 2026-10-24
THỜI GIAN: 8h-17h (8H)"""
        parser = AttendanceParser()
        records = parser.parse_batch(batch)
        assert len(records) == 2
        assert records[0].employee_name == "NGUYỄN VĂN A"
        assert records[0].status == "VALID"
        assert records[1].employee_name == "TRẦN VĂN B"

    def test_huge_meal_digits_no_value_error_crash(self):
        """5000-digit meal count string should not raise ValueError (CVE-2020-10735)."""
        huge_digits = "1" * 5000
        raw = f"""HỌ TÊN: NGUYỄN VĂN A
NGÀY: 2026-10-24
CA: Ca ngày
THỜI GIAN: 8h-17h (8H)
ĂN: {huge_digits}"""
        r = parse_single_message(raw)
        assert r.meal_count == 1111
        assert any("bất thường" in msg for msg in r.messages)

    def test_ten_du_an_lookahead_collision(self):
        """TÊN DỰ ÁN or TÊN XƯỞNG should not be treated as employee name or split message."""
        raw = """HỌ TÊN: NGUYỄN VĂN A
NGÀY: 2026-10-24
CA: Ca ngày
TÊN DỰ ÁN: NHÀ MÁY THÉP
THỜI GIAN: 8h-17h (8H)
ĂN: 0"""
        r = parse_single_message(raw)
        assert r.employee_name == "NGUYỄN VĂN A"
        assert r.project == "NHÀ MÁY THÉP"
        assert r.status == "VALID"


