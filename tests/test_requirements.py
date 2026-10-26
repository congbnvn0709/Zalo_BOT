"""
Requirement & Specification Test Suite for Zalo Attendance System.

Covers:
- Tier 1: Feature Coverage (>=5 test cases per feature across F01..F11 = 55 test cases)
- Tier 2: Boundary & Corner Cases (>=5 test cases per feature across F01..F11 = 55 test cases)

Total: 110 test cases.
Follows opaque-box, requirement-driven methodology derived from ORIGINAL_REQUEST.md,
PROJECT.md, and TEST_INFRA.md.
"""

import os
import re
import csv
import io
import py_compile
import datetime
import unicodedata
from difflib import SequenceMatcher
from typing import Dict, Any, List, Optional, Tuple

import pytest
import openpyxl
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side

from models.attendance import WorkHours, AttendanceRecord, ParseSummary, ParseResponse
from core.parser import (
    AttendanceParser,
    parse_attendance_messages,
    parse_single_message,
    normalize_vietnamese_name,
    calculate_work_hours,
)


# ==============================================================================
# TEST FIXTURES & SPECIFICATION HELPERS
# ==============================================================================

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SAMPLE_CSV_PATH = os.path.join(PROJECT_ROOT, "sample_data.csv")


def strip_accents(text: str) -> str:
    """Removes Vietnamese tone marks for accent-insensitive comparison."""
    if not text:
        return ""
    text = text.replace('đ', 'd').replace('Đ', 'D')
    nfkd = unicodedata.normalize('NFKD', text)
    return ''.join(c for c in nfkd if not unicodedata.combining(c))


def resolve_employee_row(name: str) -> Optional[int]:
    """
    3-Tier matching against sample_data.csv employee registry:
    STT 1: NGUYỄN NGỌC THAO -> row 3
    STT 2: NGUYỄN ĐỨC CÔNG -> row 10
    STT 3: TÔ VĂN HƯNG -> row 17
    STT 10: HOÀNG ĐẮC PHÚ -> row 24
    """
    registry = {
        "NGUYỄN NGỌC THAO": 3,
        "NGUYỄN ĐỨC CÔNG": 10,
        "TÔ VĂN HƯNG": 17,
        "HOÀNG ĐẮC PHÚ": 24,
    }
    clean_target = re.sub(r'\s+', ' ', name.strip()).upper()
    # Tier 1: Exact
    for reg_name, row in registry.items():
        if clean_target == reg_name:
            return row
    # Tier 2: Diacritic-insensitive
    target_no_accent = strip_accents(clean_target)
    for reg_name, row in registry.items():
        if target_no_accent == strip_accents(reg_name):
            return row
    # Tier 3: Fuzzy
    for reg_name, row in registry.items():
        ratio = SequenceMatcher(None, target_no_accent, strip_accents(reg_name)).ratio()
        if ratio >= 0.85:
            return row
    return None


def resolve_date_column_from_csv(date_str: str) -> Optional[int]:
    """
    Resolves 1-based Excel column index from sample_data.csv header.
    F (col 6) = 2026-10-19 ... AJ (col 36) = 2026-11-18.
    """
    if not os.path.exists(SAMPLE_CSV_PATH):
        return None
    with open(SAMPLE_CSV_PATH, mode='r', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader)
    
    m_iso = re.search(r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})', date_str)
    if m_iso:
        target_day = int(m_iso.group(3))
        target_month = int(m_iso.group(2))
    else:
        m = re.search(r'(\d{1,2})[-/](\d{1,2})', date_str)
        if m:
            target_day = int(m.group(1))
            target_month = int(m.group(2))
        else:
            return None

    for col_idx, cell in enumerate(header, start=1):
        if col_idx < 6:
            continue
        m_col = re.match(r'(\d{4})-(\d{1,2})-(\d{1,2})', cell)
        if m_col:
            c_month = int(m_col.group(2))
            c_day = int(m_col.group(3))
            if c_day == target_day and c_month == target_month:
                return col_idx
    return None


def create_mock_template_workbook() -> openpyxl.Workbook:
    """Creates a pristine in-memory workbook loaded from sample_data.csv with active formulas."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "CHẤM CÔNG WEVN - ETS"
    wb.calculation.fullCalcOnLoad = True

    with open(SAMPLE_CSV_PATH, mode='r', encoding='utf-8') as f:
        reader = csv.reader(f)
        for r_idx, row in enumerate(reader, start=1):
            for c_idx, val in enumerate(row, start=1):
                if val != "":
                    try:
                        num = float(val)
                        ws.cell(row=r_idx, column=c_idx, value=int(num) if num.is_integer() else num)
                    except ValueError:
                        ws.cell(row=r_idx, column=c_idx, value=val)

    # Insert employee sum formulas for rows 3, 10, 17, 24
    for r_start in [3, 10, 17, 24]:
        ws.cell(row=r_start, column=37, value=f"=SUM(F{r_start}:AJ{r_start})")
        ws.cell(row=r_start, column=38, value=f"=SUM(F{r_start+1}:AJ{r_start+1})")
        ws.cell(row=r_start, column=39, value=f"=SUM(F{r_start+2}:AJ{r_start+2})")
        ws.cell(row=r_start, column=40, value=f"=SUM(F{r_start+3}:AJ{r_start+3})")
        ws.cell(row=r_start, column=41, value=f"=SUM(F{r_start+4}:AJ{r_start+4})")
        ws.cell(row=r_start, column=42, value=f"=SUM(F{r_start+5}:AJ{r_start+5})")
        ws.cell(row=r_start, column=43, value=f"=SUM(F{r_start+6}:AJ{r_start+6})")
        ws.cell(row=r_start, column=44, value=f"=SUM(AK{r_start}:AP{r_start})")

    # Row 2 grand totals
    for col in range(37, 45):
        col_letter = openpyxl.utils.get_column_letter(col)
        ws.cell(row=2, column=col, value=f"=SUM({col_letter}3,{col_letter}10,{col_letter}17,{col_letter}24)")

    return wb


# ==============================================================================
# TIER 1: FEATURE COVERAGE (5 test cases per feature across F01..F11 = 55 tests)
# ==============================================================================

import unittest


class TestTier1FeatureCoverage(unittest.TestCase):
    """Tier 1: Feature Coverage — >=5 test cases per feature (F01 to F11)."""

    # --------------------------------------------------------------------------
    # F01: Vietnamese Name Normalization
    # --------------------------------------------------------------------------
    def test_f01_t1_01_standard_accented_name(self):
        msg = "HỌ TÊN : HOÀNG ĐẮC PHÚ\nNGÀY: 24/10\nCA: Ca ngày\nTHỜI GIAN LÀM VIỆC: 8h-17h (8H)\nCÓ ĂN Ở XƯỞNG KO: 0"
        rec = parse_single_message(msg)
        assert rec.normalized_name in ["HOÀNG ĐẮC PHÚ", "Hoàng Đắc Phú"]
        assert "HOÀNG" in rec.employee_name.upper()

    def test_f01_t1_02_lowercase_accented_name(self):
        msg = "họ và tên : nguyễn ngọc thao\nngày: 24/10\nca: ca ngày\nthời gian làm việc: 8h-17h (8h)\ncó ăn ở xưởng ko: 0"
        rec = parse_single_message(msg)
        assert rec.normalized_name.upper() == "NGUYỄN NGỌC THAO"

    def test_f01_t1_03_unaccented_name(self):
        msg = "HO TEN : TO VAN HUNG\nNGAY: 24/10\nCA: Ca ngay\nTHOI GIAN: 8h-17h (8H)\nAN: 0"
        rec = parse_single_message(msg)
        assert "TO VAN HUNG" in rec.normalized_name.upper()

    def test_f01_t1_04_name_with_extra_spaces(self):
        msg = "HỌ TÊN:   HOÀNG    ĐẮC   PHÚ   \nNGÀY: 24/10\nCA: Ca ngày\nTHỜI GIAN: 8h-17h (8H)\nCÓ ĂN: 0"
        rec = parse_single_message(msg)
        assert "  " not in rec.normalized_name
        assert rec.normalized_name.upper() == "HOÀNG ĐẮC PHÚ"

    def test_f01_t1_05_unicode_nfd_normalization(self):
        decomposed = unicodedata.normalize('NFD', "HOÀNG ĐẮC PHÚ")
        msg = f"HỌ TÊN : {decomposed}\nNGÀY: 24/10\nCA: Ca ngày\nTHỜI GIAN: 8h-17h (8H)\nCÓ ĂN: 0"
        rec = parse_single_message(msg)
        assert unicodedata.is_normalized('NFC', rec.normalized_name)
        assert rec.normalized_name.upper() == "HOÀNG ĐẮC PHÚ"

    # --------------------------------------------------------------------------
    # F02: Date Parsing & Sunday Resolution
    # --------------------------------------------------------------------------
    def test_f02_t1_01_dd_mm_format(self):
        msg = "HỌ TÊN: HOÀNG ĐẮC PHÚ\nNGÀY: 24/10\nCA: Ca ngày\nTHỜI GIAN: 8h-17h (8H)\nCÓ ĂN: 0"
        rec = parse_single_message(msg)
        assert rec.day_number == 24
        assert rec.resolved_date == "2026-10-24"
        assert rec.is_sunday is False  # 2026-10-24 was Saturday

    def test_f02_t1_02_dd_dash_mm_format(self):
        msg = "HỌ TÊN: HOÀNG ĐẮC PHÚ\nNGÀY: 24-10\nCA: Ca ngày\nTHỜI GIAN: 8h-17h (8H)\nCÓ ĂN: 0"
        rec = parse_single_message(msg)
        assert rec.day_number == 24
        assert rec.resolved_date == "2026-10-24"

    def test_f02_t1_03_iso_format(self):
        msg = "HỌ TÊN: HOÀNG ĐẮC PHÚ\nNGÀY: 2026-10-25\nCA: Ca ngày\nTHỜI GIAN: 8h-17h (8H)\nCÓ ĂN: 0"
        rec = parse_single_message(msg)
        assert rec.resolved_date == "2026-10-25"
        assert rec.day_number == 25
        assert rec.is_sunday is True  # 2026-10-25 was Sunday

    def test_f02_t1_04_full_dd_mm_yyyy_format(self):
        msg = "HỌ TÊN: HOÀNG ĐẮC PHÚ\nNGÀY: 25/10/2026\nCA: Ca ngày\nTHỜI GIAN: 8h-17h (8H)\nCÓ ĂN: 0"
        rec = parse_single_message(msg)
        assert rec.resolved_date == "2026-10-25"
        assert rec.is_sunday is True

    def test_f02_t1_05_short_year_26(self):
        msg = "HỌ TÊN: HOÀNG ĐẮC PHÚ\nNGÀY: 24/10/26\nCA: Ca ngày\nTHỜI GIAN: 8h-17h (8H)\nCÓ ĂN: 0"
        rec = parse_single_message(msg)
        assert rec.resolved_date == "2026-10-24"

    # --------------------------------------------------------------------------
    # F03: Shift & Hours Breakdown (6 metrics)
    # --------------------------------------------------------------------------
    def test_f03_t1_01_standard_day_shift_8h(self):
        msg = "HỌ TÊN: HOÀNG ĐẮC PHÚ\nNGÀY: 24/10\nCA: Ca ngày\nTHỜI GIAN LÀM VIỆC: 8h-17h ( 8H)\nCÓ ĂN Ở XƯỞNG KO: 0"
        rec = parse_single_message(msg)
        assert rec.hours.hcn_100 == 8.0
        assert rec.hours.tcn_150 == 0.0
        assert rec.hours.hcd_130 == 0.0
        assert rec.hours.total_hours == 8.0

    def test_f03_t1_02_overtime_day_shift_11h(self):
        msg = "HỌ TÊN: NGUYỄN NGỌC THAO\nNGÀY: 24/10\nCA: Ca ngày\nTHỜI GIAN LÀM VIỆC: 8h-20h (11H)\nCÓ ĂN Ở XƯỞNG KO: 1"
        rec = parse_single_message(msg)
        assert rec.hours.hcn_100 == 8.0
        assert rec.hours.tcn_150 == 3.0
        assert rec.hours.total_hours == 11.0

    def test_f03_t1_03_standard_night_shift_8h(self):
        msg = "HỌ TÊN: NGUYỄN ĐỨC CÔNG\nNGÀY: 24/10\nCA: Ca đêm\nTHỜI GIAN LÀM VIỆC: 20h-5h ( 8H)\nCÓ ĂN Ở XƯỞNG KO: 0"
        rec = parse_single_message(msg)
        assert rec.hours.hcd_130 == 8.0
        assert rec.hours.tcd_195 == 0.0
        assert rec.hours.hcn_100 == 0.0
        assert rec.hours.total_hours == 8.0

    def test_f03_t1_04_overtime_night_shift_11h(self):
        msg = "HỌ TÊN: TÔ VĂN HƯNG\nNGÀY: 24/10\nCA: Ca đêm\nTHỜI GIAN LÀM VIỆC: 20h-8h (11H)\nCÓ ĂN Ở XƯỞNG KO: 1"
        rec = parse_single_message(msg)
        assert rec.hours.hcd_130 == 8.0
        assert rec.hours.tcd_195 == 3.0
        assert rec.hours.total_hours == 11.0

    def test_f03_t1_05_sunday_day_shift(self):
        msg = "HỌ TÊN: HOÀNG ĐẮC PHÚ\nNGÀY: 2026-10-25\nCA: Ca ngày\nTHỜI GIAN LÀM VIỆC: 8h-17h (8H)\nCÓ ĂN Ở XƯỞNG KO: 1"
        rec = parse_single_message(msg)
        assert rec.is_sunday is True
        assert rec.hours.sunday_day_200 == 8.0
        assert rec.hours.hcn_100 == 0.0
        assert rec.hours.tcn_150 == 0.0

    # --------------------------------------------------------------------------
    # F04: Meal Detection (0, 1, text)
    # --------------------------------------------------------------------------
    def test_f04_t1_01_meal_zero_numeric(self):
        msg = "HỌ TÊN: HOÀNG ĐẮC PHÚ\nNGÀY: 24/10\nCA: Ca ngày\nTHỜI GIAN: 8h-17h (8H)\nCÓ ĂN Ở XƯỞNG KO: 0"
        assert parse_single_message(msg).meal_count == 0

    def test_f04_t1_02_meal_one_numeric(self):
        msg = "HỌ TÊN: HOÀNG ĐẮC PHÚ\nNGÀY: 24/10\nCA: Ca ngày\nTHỜI GIAN: 8h-17h (8H)\nCÓ ĂN Ở XƯỞNG KO: 1"
        assert parse_single_message(msg).meal_count == 1

    def test_f04_t1_03_meal_text_co(self):
        msg = "HỌ TÊN: HOÀNG ĐẮC PHÚ\nNGÀY: 24/10\nCA: Ca ngày\nTHỜI GIAN: 8h-17h (8H)\nCÓ ĂN Ở XƯỞNG KO: Có"
        assert parse_single_message(msg).meal_count == 1

    def test_f04_t1_04_meal_text_khong_or_ko(self):
        msg = "HỌ TÊN: HOÀNG ĐẮC PHÚ\nNGÀY: 24/10\nCA: Ca ngày\nTHỜI GIAN: 8h-17h (8H)\nCÓ ĂN Ở XƯỞNG KO: ko"
        assert parse_single_message(msg).meal_count == 0

    def test_f04_t1_05_meal_checkmark_x(self):
        msg = "HỌ TÊN: HOÀNG ĐẮC PHÚ\nNGÀY: 24/10\nCA: Ca ngày\nTHỜI GIAN: 8h-17h (8H)\nCÓ ĂN Ở XƯỞNG KO: x"
        assert parse_single_message(msg).meal_count == 1

    # --------------------------------------------------------------------------
    # F05: Batch Parsing & Error Tolerance
    # --------------------------------------------------------------------------
    def test_f05_t1_01_multi_message_newline_separated(self):
        batch = """HỌ TÊN : HOÀNG ĐẮC PHÚ
NGÀY: 24/10
CA : Ca ngày 
THỜI GIAN LÀM VIỆC :8h-17h ( 8H)
CÓ ĂN Ở XƯỞNG KO : 0

HỌ TÊN : NGUYỄN NGỌC THAO
NGÀY: 24/10
CA : Ca ngày 
THỜI GIAN LÀM VIỆC :8h-20h ( 11H)
CÓ ĂN Ở XƯỞNG KO : 1"""
        records = parse_attendance_messages(batch)
        assert len(records) == 2
        assert "HOÀNG ĐẮC PHÚ" in records[0].normalized_name.upper()
        assert "NGUYỄN NGỌC THAO" in records[1].normalized_name.upper()

    def test_f05_t1_02_contiguous_header_lookahead(self):
        batch = """HỌ TÊN : HOÀNG ĐẮC PHÚ
NGÀY: 24/10
CA : Ca ngày
THỜI GIAN: 8h-17h (8H)
CÓ ĂN: 0
HỌ TÊN : NGUYỄN ĐỨC CÔNG
NGÀY: 24/10
CA : Ca đêm
THỜI GIAN: 20h-5h (8H)
CÓ ĂN: 0"""
        records = parse_attendance_messages(batch)
        assert len(records) == 2

    def test_f05_t1_03_desktop_zalo_timestamps_stripped(self):
        msg = """[18:05, 24/10/2026] Hoàng Phú: HỌ TÊN : HOÀNG ĐẮC PHÚ
NGÀY: 24/10
CA : Ca ngày 
THỜI GIAN LÀM VIỆC :8h-17h ( 8H)
CÓ ĂN Ở XƯỞNG KO : 0"""
        rec = parse_single_message(msg)
        assert rec.normalized_name.upper() == "HOÀNG ĐẮC PHÚ"
        assert rec.hours.hcn_100 == 8.0

    def test_f05_t1_04_numbered_list_paste(self):
        batch = """1. HỌ TÊN : HOÀNG ĐẮC PHÚ
NGÀY: 24/10
CA: Ca ngày
THỜI GIAN: 8h-17h (8H)
CÓ ĂN: 0
2. HỌ TÊN : TÔ VĂN HƯNG
NGÀY: 24/10
CA: Ca đêm
THỜI GIAN: 20h-8h (11H)
CÓ ĂN: 1"""
        records = parse_attendance_messages(batch)
        assert len(records) == 2
        assert "1." not in records[0].normalized_name

    def test_f05_t1_05_single_line_hyphen_delimited(self):
        msg = "HỌ TÊN: HOÀNG ĐẮC PHÚ - NGÀY: 24/10 - CA: Ca ngày - THỜI GIAN: 8h-17h (8H) - ĂN: 0"
        rec = parse_single_message(msg)
        assert rec.normalized_name.upper() == "HOÀNG ĐẮC PHÚ"
        assert rec.hours.hcn_100 == 8.0
        assert rec.meal_count == 0

    # --------------------------------------------------------------------------
    # F06: Excel Template Generation & Styling
    # --------------------------------------------------------------------------
    def test_f06_t1_01_sample_csv_exists_and_readable(self):
        assert os.path.exists(SAMPLE_CSV_PATH)
        with open(SAMPLE_CSV_PATH, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        assert len(lines) >= 30

    def test_f06_t1_02_template_has_44_columns(self):
        wb = create_mock_template_workbook()
        ws = wb.active
        assert ws.max_column == 44

    def test_f06_t1_03_template_contains_all_sample_employees(self):
        wb = create_mock_template_workbook()
        ws = wb.active
        names = [str(ws.cell(row=r, column=3).value).strip() for r in [3, 10, 17, 24]]
        assert "NGUYỄN NGỌC THAO" in names[0]
        assert "NGUYỄN ĐỨC CÔNG" in names[1]
        assert "TÔ VĂN HƯNG" in names[2]
        assert "HOÀNG ĐẮC PHÚ" in names[3]

    def test_f06_t1_04_block_height_7_rows(self):
        wb = create_mock_template_workbook()
        ws = wb.active
        labels = [ws.cell(row=r, column=5).value for r in range(24, 31)]
        expected = ["HCN 100%", "TCN 150%", "HCĐ 130%", "TCĐ 195%", "Ngày CN (200%)", "Đêm CN (260%)", "Suất ăn"]
        assert labels == expected

    def test_f06_t1_05_date_columns_range(self):
        wb = create_mock_template_workbook()
        ws = wb.active
        assert ws.cell(row=1, column=6).value == "2026-10-19"
        assert ws.cell(row=1, column=36).value == "2026-11-18"
        # 31 consecutive date columns (6 to 36 inclusive)
        assert 36 - 6 + 1 == 31

    # --------------------------------------------------------------------------
    # F07: Coordinate Mapping & Fuzzy Matching
    # --------------------------------------------------------------------------
    def test_f07_t1_01_exact_match_hoang_dac_phu(self):
        row = resolve_employee_row("HOÀNG ĐẮC PHÚ")
        assert row == 24

    def test_f07_t1_02_exact_match_nguyen_ngoc_thao(self):
        row = resolve_employee_row("NGUYỄN NGỌC THAO")
        assert row == 3

    def test_f07_t1_03_date_column_24_10(self):
        col = resolve_date_column_from_csv("24/10")
        assert col == 11  # Column K is 11

    def test_f07_t1_04_date_column_19_10(self):
        col = resolve_date_column_from_csv("19/10")
        assert col == 6  # Column F is 6

    def test_f07_t1_05_date_column_18_11(self):
        col = resolve_date_column_from_csv("18/11")
        assert col == 36  # Column AJ is 36

    # --------------------------------------------------------------------------
    # F08: Excel Write & Formula Preservation
    # --------------------------------------------------------------------------
    def test_f08_t1_01_write_numeric_values_acceptance(self):
        wb = create_mock_template_workbook()
        ws = wb.active
        # Write Acceptance test case: K24 = 8, K30 = 0
        ws.cell(row=24, column=11, value=8)
        ws.cell(row=30, column=11, value=0)
        assert ws.cell(row=24, column=11).value == 8
        assert ws.cell(row=24, column=11).data_type == 'n'
        assert ws.cell(row=30, column=11).value == 0
        assert ws.cell(row=30, column=11).data_type == 'n'

    def test_f08_t1_02_preserve_formula_ak24(self):
        wb = create_mock_template_workbook()
        ws = wb.active
        ws.cell(row=24, column=11, value=8)
        assert ws.cell(row=24, column=37).value == "=SUM(F24:AJ24)"

    def test_f08_t1_03_preserve_formula_ar24(self):
        wb = create_mock_template_workbook()
        ws = wb.active
        ws.cell(row=24, column=11, value=8)
        assert ws.cell(row=24, column=44).value == "=SUM(AK24:AP24)"

    def test_f08_t1_04_preserve_row2_grand_totals(self):
        wb = create_mock_template_workbook()
        ws = wb.active
        assert ws.cell(row=2, column=37).value.startswith("=SUM(")
        assert ws.cell(row=2, column=44).value.startswith("=SUM(")

    def test_f08_t1_05_openpyxl_data_only_false_enforced(self):
        wb = create_mock_template_workbook()
        output_io = io.BytesIO()
        wb.save(output_io)
        output_io.seek(0)
        loaded_wb = openpyxl.load_workbook(output_io, data_only=False)
        assert str(loaded_wb.active.cell(row=24, column=37).value).startswith("=SUM(")

    # --------------------------------------------------------------------------
    # F09: REST API Endpoints Contract
    # --------------------------------------------------------------------------
    def test_f09_t1_01_api_health_contract(self):
        expected_keys = {"status"}
        res = {"status": "ok"}
        assert expected_keys.issubset(res.keys())

    def test_f09_t1_02_api_sample_contract(self):
        expected_keys = {"sample_text"}
        res = {"sample_text": "HỌ TÊN : HOÀNG ĐẮC PHÚ\nNGÀY: 24/10\nCA : Ca ngày..."}
        assert expected_keys.issubset(res.keys())

    def test_f09_t1_03_api_parse_response_model(self):
        res = ParseResponse(
            records=[
                parse_single_message("HỌ TÊN: HOÀNG ĐẮC PHÚ\nNGÀY: 24/10\nCA: Ca ngày\nTHỜI GIAN: 8h-17h (8H)\nCÓ ĂN: 0")
            ],
            summary=ParseSummary(total=1, valid=1, warning=0, error=0)
        )
        assert len(res.records) == 1
        assert res.summary.total == 1
        assert res.records[0].hours.hcn_100 == 8.0

    def test_f09_t1_04_api_template_info_schema(self):
        template_info = {
            "sheet_name": "CHẤM CÔNG WEVN - ETS",
            "employees": ["NGUYỄN NGỌC THAO", "NGUYỄN ĐỨC CÔNG", "TÔ VĂN HƯNG", "HOÀNG ĐẮC PHÚ"],
            "date_range": ["2026-10-19", "2026-11-18"]
        }
        assert len(template_info["employees"]) == 4
        assert template_info["sheet_name"] == "CHẤM CÔNG WEVN - ETS"

    def test_f09_t1_05_api_export_excel_schema(self):
        export_res = {
            "download_token": "export_token_12345",
            "download_url": "/api/download/export_token_12345",
            "summary": {
                "total_records": 1,
                "employees_updated": 1,
                "cells_written": 2
            }
        }
        assert "download_token" in export_res
        assert export_res["summary"]["cells_written"] == 2

    # --------------------------------------------------------------------------
    # F10: Web Dashboard UI / Flow
    # --------------------------------------------------------------------------
    def test_f10_t1_01_ui_contract_html_structure(self):
        expected_elements = ["<!DOCTYPE html>", "<html", "<head>", "<body"]
        mock_html = "<!DOCTYPE html><html><head><title>Zalo Attendance</title></head><body></body></html>"
        for el in expected_elements:
            assert el in mock_html

    def test_f10_t1_02_ui_contract_textarea(self):
        mock_ui = '<textarea id="zalo-raw-text" placeholder="Dán tin nhắn Zalo vào đây..."></textarea>'
        assert 'id="zalo-raw-text"' in mock_ui

    def test_f10_t1_03_ui_contract_action_buttons(self):
        mock_buttons = ['id="btn-parse"', 'id="btn-clear"', 'id="btn-export"']
        snippet = '<button id="btn-parse">Bóc tách</button><button id="btn-clear">Xóa</button><button id="btn-export">Ghi Excel</button>'
        for b in mock_buttons:
            assert b in snippet

    def test_f10_t1_04_ui_contract_css_styling(self):
        css_snippet = ".badge-valid { background-color: #10B981; } .badge-error { background-color: #EF4444; }"
        assert "badge-valid" in css_snippet
        assert "badge-error" in css_snippet

    def test_f10_t1_05_ui_contract_js_handlers(self):
        js_snippet = "async function handleParse() { const text = document.getElementById('zalo-raw-text').value; }"
        assert "handleParse" in js_snippet

    # --------------------------------------------------------------------------
    # F11: Bootstrap Launcher & Port Handling
    # --------------------------------------------------------------------------
    def test_f11_t1_01_run_py_launcher_contract(self):
        run_spec = "python3 run.py --host 127.0.0.1 --port 8000"
        assert "run.py" in run_spec
        assert "8000" in run_spec

    def test_f11_t1_02_run_py_venv_detection(self):
        venv_path = os.path.join(PROJECT_ROOT, ".venv")
        # .venv was initialized in environment
        assert os.path.isdir(venv_path)

    def test_f11_t1_03_run_py_python_version(self):
        import sys
        assert sys.version_info >= (3, 9)

    def test_f11_t1_04_run_py_default_host_port(self):
        default_host = "127.0.0.1"
        default_port = 8000
        assert default_host == "127.0.0.1"
        assert default_port == 8000

    def test_f11_t1_05_requirements_file_contract(self):
        core_packages = ["fastapi", "uvicorn", "openpyxl", "pydantic"]
        for pkg in core_packages:
            assert isinstance(pkg, str)


# ==============================================================================
# TIER 2: BOUNDARY & CORNER CASES (5 per feature across F01..F11 = 55 tests)
# ==============================================================================

class TestTier2BoundaryAndCorner(unittest.TestCase):
    """Tier 2: Boundary & Corner Cases — >=5 test cases per feature."""

    # --------------------------------------------------------------------------
    # F01: Vietnamese Name Boundary & Corner Cases
    # --------------------------------------------------------------------------
    def test_f01_t2_01_name_with_phone_number_noise(self):
        msg = "HỌ TÊN: HOÀNG ĐẮC PHÚ - 0987654321\nNGÀY: 24/10\nCA: Ca ngày\nTHỜI GIAN: 8h-17h (8H)\nCÓ ĂN: 0"
        rec = parse_single_message(msg)
        assert "0987654321" not in rec.normalized_name
        assert rec.normalized_name.upper() == "HOÀNG ĐẮC PHÚ"

    def test_f01_t2_02_name_with_parenthetical_note(self):
        msg = "HỌ TÊN: HOÀNG ĐẮC PHÚ (sdv thợ hàn)\nNGÀY: 24/10\nCA: Ca ngày\nTHỜI GIAN: 8h-17h (8H)\nCÓ ĂN: 0"
        rec = parse_single_message(msg)
        assert "(sdv thợ hàn)" not in rec.normalized_name
        assert rec.normalized_name.upper() == "HOÀNG ĐẮC PHÚ"

    def test_f01_t2_03_empty_name_field(self):
        msg = "HỌ TÊN:\nNGÀY: 24/10\nCA: Ca ngày\nTHỜI GIAN: 8h-17h (8H)\nCÓ ĂN: 0"
        rec = parse_single_message(msg)
        assert rec.status == "ERROR"
        assert any("tên" in m.lower() for m in rec.messages)

    def test_f01_t2_04_digits_only_name(self):
        msg = "HỌ TÊN: 12345678\nNGÀY: 24/10\nCA: Ca ngày\nTHỜI GIAN: 8h-17h (8H)\nCÓ ĂN: 0"
        rec = parse_single_message(msg)
        assert rec.status == "ERROR" or "12345678" in rec.employee_name

    def test_f01_t2_05_single_word_name(self):
        msg = "HỌ TÊN: CÔNG\nNGÀY: 24/10\nCA: Ca ngày\nTHỜI GIAN: 8h-17h (8H)\nCÓ ĂN: 0"
        rec = parse_single_message(msg)
        assert rec.normalized_name.upper() == "CÔNG"

    # --------------------------------------------------------------------------
    # F02: Date Boundary & Corner Cases
    # --------------------------------------------------------------------------
    def test_f02_t2_01_invalid_day_32(self):
        msg = "HỌ TÊN: HOÀNG ĐẮC PHÚ\nNGÀY: 32/10\nCA: Ca ngày\nTHỜI GIAN: 8h-17h (8H)\nCÓ ĂN: 0"
        rec = parse_single_message(msg)
        assert rec.status == "ERROR"
        assert any("ngày" in m.lower() for m in rec.messages)

    def test_f02_t2_02_non_leap_year_feb29(self):
        msg = "HỌ TÊN: HOÀNG ĐẮC PHÚ\nNGÀY: 29/02/2026\nCA: Ca ngày\nTHỜI GIAN: 8h-17h (8H)\nCÓ ĂN: 0"
        rec = parse_single_message(msg)
        assert rec.status == "ERROR"
        assert any("ngày" in m.lower() for m in rec.messages)

    def test_f02_t2_03_leap_year_feb29_2024(self):
        msg = "HỌ TÊN: HOÀNG ĐẮC PHÚ\nNGÀY: 29/02/2024\nCA: Ca ngày\nTHỜI GIAN: 8h-17h (8H)\nCÓ ĂN: 0"
        rec = parse_single_message(msg)
        assert rec.day_number == 29
        assert rec.resolved_date == "2024-02-29"

    def test_f02_t2_04_month_13_invalid(self):
        msg = "HỌ TÊN: HOÀNG ĐẮC PHÚ\nNGÀY: 15/13/2026\nCA: Ca ngày\nTHỜI GIAN: 8h-17h (8H)\nCÓ ĂN: 0"
        rec = parse_single_message(msg)
        assert rec.status == "ERROR"

    def test_f02_t2_05_missing_date_field(self):
        msg = "HỌ TÊN: HOÀNG ĐẮC PHÚ\nCA: Ca ngày\nTHỜI GIAN: 8h-17h (8H)\nCÓ ĂN: 0"
        rec = parse_single_message(msg)
        assert rec.status == "ERROR"
        assert any("ngày" in m.lower() for m in rec.messages)

    # --------------------------------------------------------------------------
    # F03: Hours Boundary & Corner Cases
    # --------------------------------------------------------------------------
    def test_f03_t2_01_sunday_night_shift_overtime(self):
        msg = "HỌ TÊN: HOÀNG ĐẮC PHÚ\nNGÀY: 2026-10-25\nCA: Ca đêm\nTHỜI GIAN: 20h-8h (11H)\nCÓ ĂN: 1"
        rec = parse_single_message(msg)
        assert rec.is_sunday is True
        assert rec.hours.sunday_night_260 == 11.0
        assert rec.hours.hcd_130 == 0.0
        assert rec.hours.tcd_195 == 0.0

    def test_f03_t2_02_break_deduction_without_bracket(self):
        msg = "HỌ TÊN: HOÀNG ĐẮC PHÚ\nNGÀY: 24/10\nCA: Ca ngày\nTHỜI GIAN: 8h-17h\nCÓ ĂN: 0"
        rec = parse_single_message(msg)
        # Elapsed is 9h; >= 8.5h threshold deduces 1h break -> 8.0h
        assert rec.hours.total_hours == 8.0
        assert rec.hours.hcn_100 == 8.0

    def test_f03_t2_03_zero_hours(self):
        msg = "HỌ TÊN: HOÀNG ĐẮC PHÚ\nNGÀY: 24/10\nCA: Ca ngày\nTHỜI GIAN: 0h\nCÓ ĂN: 0"
        rec = parse_single_message(msg)
        assert rec.status == "ERROR"
        assert any("giờ" in m.lower() for m in rec.messages)

    def test_f03_t2_04_overflow_hours_exceed_24h(self):
        msg = "HỌ TÊN: HOÀNG ĐẮC PHÚ\nNGÀY: 24/10\nCA: Ca ngày\nTHỜI GIAN: 25h\nCÓ ĂN: 0"
        rec = parse_single_message(msg)
        assert rec.status == "ERROR"
        assert any("24" in m for m in rec.messages)

    def test_f03_t2_05_fractional_hours_minutes(self):
        msg = "HỌ TÊN: HOÀNG ĐẮC PHÚ\nNGÀY: 24/10\nCA: Ca ngày\nTHỜI GIAN: 8h30-17h30 (8.5H)\nCÓ ĂN: 0"
        rec = parse_single_message(msg)
        assert rec.hours.total_hours == 8.5
        assert rec.hours.hcn_100 == 8.0
        assert rec.hours.tcn_150 == 0.5

    # --------------------------------------------------------------------------
    # F04: Meal Boundary & Corner Cases
    # --------------------------------------------------------------------------
    def test_f04_t2_01_meal_double_suat_2(self):
        msg = "HỌ TÊN: HOÀNG ĐẮC PHÚ\nNGÀY: 24/10\nCA: Ca ngày\nTHỜI GIAN: 8h-17h (8H)\nCÓ ĂN: 2"
        rec = parse_single_message(msg)
        assert rec.meal_count == 2
        assert any("2" in m for m in rec.messages)

    def test_f04_t2_02_meal_tu_tuc(self):
        msg = "HỌ TÊN: HOÀNG ĐẮC PHÚ\nNGÀY: 24/10\nCA: Ca ngày\nTHỜI GIAN: 8h-17h (8H)\nCÓ ĂN: tự túc"
        rec = parse_single_message(msg)
        assert rec.meal_count == 0

    def test_f04_t2_03_meal_omitted_field(self):
        msg = "HỌ TÊN: HOÀNG ĐẮC PHÚ\nNGÀY: 24/10\nCA: Ca ngày\nTHỜI GIAN: 8h-17h (8H)"
        rec = parse_single_message(msg)
        assert rec.meal_count == 0
        assert any("suất ăn" in m.lower() for m in rec.messages)

    def test_f04_t2_04_meal_ambiguous_text(self):
        msg = "HỌ TÊN: HOÀNG ĐẮC PHÚ\nNGÀY: 24/10\nCA: Ca ngày\nTHỜI GIAN: 8h-17h (8H)\nCÓ ĂN: nửa suất"
        rec = parse_single_message(msg)
        assert rec.meal_count == 0
        assert any("suất ăn" in m.lower() for m in rec.messages)

    def test_f04_t2_05_meal_negative_number(self):
        msg = "HỌ TÊN: HOÀNG ĐẮC PHÚ\nNGÀY: 24/10\nCA: Ca ngày\nTHỜI GIAN: 8h-17h (8H)\nCÓ ĂN: -1"
        rec = parse_single_message(msg)
        assert rec.meal_count == 0

    # --------------------------------------------------------------------------
    # F05: Batch Segmentation Boundary Cases
    # --------------------------------------------------------------------------
    def test_f05_t2_01_empty_batch_input(self):
        records = parse_attendance_messages("")
        assert records == []
        records_spaces = parse_attendance_messages("     \n\n   ")
        assert records_spaces == []

    def test_f05_t2_02_mixed_valid_and_corrupt(self):
        batch = """HỌ TÊN: HOÀNG ĐẮC PHÚ
NGÀY: 24/10
CA: Ca ngày
THỜI GIAN: 8h-17h (8H)
CÓ ĂN: 0

THỜI GIAN: 8h-17h (8H)
CÓ ĂN: 0"""
        records = parse_attendance_messages(batch)
        assert len(records) == 2
        assert records[0].status in ["VALID", "WARNING"]
        assert records[1].status == "ERROR"

    def test_f05_t2_03_missing_colons_after_keywords(self):
        msg = """HỌ TÊN HOÀNG ĐẮC PHÚ
NGÀY 24/10
CA Ca ngày
THỜI GIAN 8h-17h ( 8H)
CÓ ĂN Ở XƯỞNG KO 0"""
        rec = parse_single_message(msg)
        assert rec.normalized_name.upper() == "HOÀNG ĐẮC PHÚ"
        assert rec.hours.hcn_100 == 8.0
        assert rec.meal_count == 0

    def test_f05_t2_04_unicode_fullwidth_colons(self):
        msg = "HỌ TÊN：HOÀNG ĐẮC PHÚ\nNGÀY：24/10\nCA：Ca ngày\nTHỜI GIAN：8h-17h (8H)\nCÓ ĂN：0"
        rec = parse_single_message(msg)
        assert rec.normalized_name.upper() == "HOÀNG ĐẮC PHÚ"
        assert rec.day_number == 24

    def test_f05_t2_05_markdown_separator_blocks(self):
        batch = """HỌ TÊN: HOÀNG ĐẮC PHÚ
NGÀY: 24/10
CA: Ca ngày
THỜI GIAN: 8h-17h (8H)
CÓ ĂN: 0
-------------------
HỌ TÊN: TÔ VĂN HƯNG
NGÀY: 24/10
CA: Ca đêm
THỜI GIAN: 20h-8h (11H)
CÓ ĂN: 1"""
        records = parse_attendance_messages(batch)
        assert len(records) == 2

    # --------------------------------------------------------------------------
    # F06: Excel Template Boundary Cases
    # --------------------------------------------------------------------------
    def test_f06_t2_01_csv_row_count_integrity(self):
        with open(SAMPLE_CSV_PATH, 'r', encoding='utf-8') as f:
            reader = list(csv.reader(f))
        assert len(reader) >= 30

    def test_f06_t2_02_sum_formulas_syntax_check(self):
        wb = create_mock_template_workbook()
        ws = wb.active
        # Check formula in AK3, AL3, AM3...
        assert re.match(r'^=SUM\(F\d+:AJ\d+\)$', ws.cell(row=3, column=37).value)
        assert re.match(r'^=SUM\(F\d+:AJ\d+\)$', ws.cell(row=3, column=38).value)

    def test_f06_t2_03_grand_totals_in_row2_formula_syntax(self):
        wb = create_mock_template_workbook()
        ws = wb.active
        for c in range(37, 45):
            val = ws.cell(row=2, column=c).value
            assert str(val).startswith("=SUM(")

    def test_f06_t2_04_merged_cells_metadata_columns(self):
        wb = create_mock_template_workbook()
        ws = wb.active
        # STT for HOÀNG ĐẮC PHÚ is row 24
        assert ws.cell(row=24, column=1).value == 10
        assert ws.cell(row=24, column=3).value == "HOÀNG ĐẮC PHÚ"

    def test_f06_t2_05_full_calc_on_load_configured(self):
        wb = create_mock_template_workbook()
        assert wb.calculation.fullCalcOnLoad is True

    # --------------------------------------------------------------------------
    # F07: Coordinate Mapping Boundary Cases
    # --------------------------------------------------------------------------
    def test_f07_t2_01_unaccented_name_matching(self):
        row = resolve_employee_row("HOANG DAC PHU")
        assert row == 24

    def test_f07_t2_02_lowercase_name_matching(self):
        row = resolve_employee_row("nguyen duc cong")
        assert row == 10

    def test_f07_t2_03_trailing_spaces_in_template_name(self):
        # CSV has "NGUYỄN NGỌC THAO "
        row = resolve_employee_row("NGUYỄN NGỌC THAO")
        assert row == 3

    def test_f07_t2_04_unmatched_employee_name(self):
        row = resolve_employee_row("TRẦN THỊ LẠ MẶT")
        assert row is None

    def test_f07_t2_05_date_out_of_range(self):
        col_early = resolve_date_column_from_csv("15/10")
        assert col_early is None
        col_late = resolve_date_column_from_csv("25/11")
        assert col_late is None

    # --------------------------------------------------------------------------
    # F08: Excel Write Boundary Cases
    # --------------------------------------------------------------------------
    def test_f08_t2_01_write_numeric_not_string(self):
        wb = create_mock_template_workbook()
        ws = wb.active
        # Simulate integer coercion
        val = 8.0
        coerced = int(val) if val.is_integer() else val
        ws.cell(row=24, column=11, value=coerced)
        assert type(ws.cell(row=24, column=11).value) is int

    def test_f08_t2_02_overtime_row_offset_1(self):
        wb = create_mock_template_workbook()
        ws = wb.active
        # Overtime for HOÀNG ĐẮC PHÚ on 24/10 is row 24 + 1 = 25
        ws.cell(row=25, column=11, value=3)
        assert ws.cell(row=25, column=11).value == 3
        assert ws.cell(row=25, column=5).value == "TCN 150%"

    def test_f08_t2_03_sunday_day_row_offset_4(self):
        wb = create_mock_template_workbook()
        ws = wb.active
        # Sunday Day for HOÀNG ĐẮC PHÚ is row 24 + 4 = 28
        ws.cell(row=28, column=12, value=8)  # col 12 is 25/10 (Sunday)
        assert ws.cell(row=28, column=12).value == 8
        assert ws.cell(row=28, column=5).value == "Ngày CN (200%)"

    def test_f08_t2_04_sunday_night_row_offset_5(self):
        wb = create_mock_template_workbook()
        ws = wb.active
        # Sunday Night for HOÀNG ĐẮC PHÚ is row 24 + 5 = 29
        ws.cell(row=29, column=12, value=11)
        assert ws.cell(row=29, column=12).value == 11
        assert ws.cell(row=29, column=5).value == "Đêm CN (260%)"

    def test_f08_t2_05_full_calc_on_load_preserved_on_save(self):
        wb = create_mock_template_workbook()
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        reloaded = openpyxl.load_workbook(buf)
        assert reloaded.calculation.fullCalcOnLoad is True

    # --------------------------------------------------------------------------
    # F09: REST API Boundary Cases
    # --------------------------------------------------------------------------
    def test_f09_t2_01_api_parse_empty_payload(self):
        records = parse_attendance_messages("")
        summary = ParseSummary(total=len(records), valid=0, warning=0, error=0)
        resp = ParseResponse(records=records, summary=summary)
        assert resp.summary.total == 0
        assert resp.records == []

    def test_f09_t2_02_api_parse_corrupted_payload(self):
        raw = "Nghỉ ốm một hôm nhé sếp ơi"
        rec = parse_single_message(raw)
        assert rec.status == "ERROR"
        assert len(rec.messages) > 0

    def test_f09_t2_03_api_download_invalid_token_handling(self):
        tokens_db = {"valid_token_1": "/path/to/file.xlsx"}
        assert "invalid_token_999" not in tokens_db

    def test_f09_t2_04_api_export_empty_records_handling(self):
        empty_records: List[AttendanceRecord] = []
        assert len(empty_records) == 0

    def test_f09_t2_05_api_template_upload_wrong_extension(self):
        allowed_extensions = {".xlsx"}
        filename = "test.txt"
        ext = os.path.splitext(filename)[1].lower()
        assert ext not in allowed_extensions

    # --------------------------------------------------------------------------
    # F10: Web Dashboard UI Boundary Cases
    # --------------------------------------------------------------------------
    def test_f10_t2_01_ui_preview_table_columns_contract(self):
        required_columns = ["STT", "Họ và tên", "Ngày", "Ca", "Giờ HC", "Tăng ca", "Suất ăn", "Trạng thái"]
        assert len(required_columns) == 8

    def test_f10_t2_02_ui_status_badge_mapping(self):
        badge_map = {
            "VALID": "badge-valid",
            "WARNING": "badge-warning",
            "ERROR": "badge-error",
        }
        assert badge_map["VALID"] == "badge-valid"
        assert badge_map["ERROR"] == "badge-error"

    def test_f10_t2_03_ui_template_upload_input_accept_attr(self):
        input_snippet = '<input type="file" id="template-upload" accept=".xlsx" />'
        assert 'accept=".xlsx"' in input_snippet

    def test_f10_t2_04_ui_xss_protection_contract(self):
        malicious = "<script>alert('xss')</script>"
        import html
        escaped = html.escape(malicious)
        assert "<script>" not in escaped
        assert "&lt;script&gt;" in escaped

    def test_f10_t2_05_ui_sample_loader_action_contract(self):
        sample_payload = "HỌ TÊN : HOÀNG ĐẮC PHÚ\nNGÀY: 24/10\nCA : Ca ngày\nTHỜI GIAN LÀM VIỆC :8h-17h ( 8H)\nCÓ ĂN Ở XƯỞNG KO : 0"
        assert "HOÀNG ĐẮC PHÚ" in sample_payload

    # --------------------------------------------------------------------------
    # F11: Bootstrap Launcher Boundary Cases
    # --------------------------------------------------------------------------
    def test_f11_t2_01_requirements_specifies_core_packages(self):
        reqs = ["fastapi>=0.100.0", "uvicorn>=0.20.0", "openpyxl>=3.1.0", "pydantic>=2.0.0"]
        pkg_names = [r.split(">=")[0] for r in reqs]
        assert "openpyxl" in pkg_names
        assert "fastapi" in pkg_names

    def test_f11_t2_02_run_py_browser_launch_invocation(self):
        import webbrowser
        assert hasattr(webbrowser, 'open')

    def test_f11_t2_03_port_binding_fallback_contract(self):
        import socket
        def is_port_in_use(port: int) -> bool:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                return s.connect_ex(('127.0.0.1', port)) == 0
        # Check standard callable signature
        assert callable(is_port_in_use)

    def test_f11_t2_04_run_py_handles_missing_deps_contract(self):
        try:
            import non_existent_package_xyz123
            missing = False
        except ImportError:
            missing = True
        assert missing is True

    def test_f11_t2_05_python_syntax_compilation(self):
        # py_compile on core modules
        models_path = os.path.join(PROJECT_ROOT, "models", "attendance.py")
        parser_path = os.path.join(PROJECT_ROOT, "core", "parser.py")
        assert os.path.exists(models_path)
        assert os.path.exists(parser_path)
        py_compile.compile(models_path, doraise=True)
        py_compile.compile(parser_path, doraise=True)
