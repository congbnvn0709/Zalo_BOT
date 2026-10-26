"""
Unit & Integration Test Suite for Excel Integrator & Template Generator (Requirement R3).
Covers:
- Template generator functionality, formulas, headers, styles, dimensions
- 3-tier employee matcher (exact NFC, unaccented, difflib fuzzy, whitespace, lowercase, unmatched)
- Date column resolution across multiple formats (ISO, DD/MM, DD-MM, DD/MM/YYYY, day int, out of range)
- Cell coordinate mapping and numeric typing (data_type == 'n')
- Formula preservation in AK..AR and row 2 grand totals
- Official Acceptance Criteria test case: HOÀNG ĐẮC PHÚ on 24/10 -> K24=8, K30=0, AK24==SUM, AR24==SUM
"""
import os
import io
import re
import datetime
import unittest
import openpyxl

from models.attendance import AttendanceRecord, WorkHours
from core.parser import parse_single_message
from core.template_generator import (
    generate_default_template,
    DEFAULT_CSV_PATH,
    DEFAULT_TEMPLATE_PATH,
)
from core.excel_integrator import (
    ExcelIntegrator,
    strip_accents,
    normalize_name_key,
    clean_employee_name_for_matching,
)

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class TestTemplateGenerator(unittest.TestCase):
    """Unit tests for core/template_generator.py."""

    @classmethod
    def setUpClass(cls):
        cls.template_path = generate_default_template()
        cls.wb = openpyxl.load_workbook(cls.template_path, data_only=False)
        cls.ws = cls.wb.active

    def test_01_template_file_exists_and_path_returned(self):
        self.assertTrue(os.path.exists(self.template_path))
        self.assertTrue(self.template_path.endswith(".xlsx"))

    def test_02_worksheet_title(self):
        self.assertEqual(self.ws.title, "CHẤM CÔNG WEVN - ETS")

    def test_03_grid_dimensions(self):
        # 44 columns: A..AR
        self.assertEqual(self.ws.max_column, 44)
        # 2 header rows + 4 employees * 7 rows = 30 rows
        self.assertEqual(self.ws.max_row, 30)

    def test_04_row1_metadata_headers(self):
        self.assertEqual(self.ws.cell(row=1, column=1).value, "STT")
        self.assertEqual(self.ws.cell(row=1, column=2).value, "MNV")
        self.assertEqual(self.ws.cell(row=1, column=3).value, "HỌ VÀ TÊN")
        self.assertEqual(self.ws.cell(row=1, column=4).value, "ĐỊA ĐIỂM LÀM VIỆC")
        self.assertEqual(self.ws.cell(row=1, column=5).value, "CÔNG")

    def test_05_row1_date_columns_range(self):
        # Column 6 (F) is start date
        self.assertEqual(self.ws.cell(row=1, column=6).value, "2026-10-19")
        # Column 36 (AJ) is end date
        self.assertEqual(self.ws.cell(row=1, column=36).value, "2026-11-18")
        # Column 11 (K) is acceptance test date 2026-10-24
        self.assertEqual(self.ws.cell(row=1, column=11).value, "2026-10-24")
        # Exactly 31 consecutive date columns
        self.assertEqual(36 - 6 + 1, 31)

    def test_06_row1_summary_headers(self):
        self.assertIn("HC NGÀY", str(self.ws.cell(row=1, column=37).value))
        self.assertIn("TC NGÀY", str(self.ws.cell(row=1, column=38).value))
        self.assertIn("HC ĐÊM", str(self.ws.cell(row=1, column=39).value))
        self.assertIn("TC ĐÊM", str(self.ws.cell(row=1, column=40).value))
        self.assertIn("Ngày CN", str(self.ws.cell(row=1, column=41).value))
        self.assertIn("Đêm CN", str(self.ws.cell(row=1, column=42).value))
        self.assertIn("Suất ăn", str(self.ws.cell(row=1, column=43).value))
        self.assertIn("TỔNG CÔNG", str(self.ws.cell(row=1, column=44).value))

    def test_07_row2_dow_and_sunday_indicators(self):
        # 2026-10-19 is Monday (T2)
        self.assertEqual(self.ws.cell(row=2, column=6).value, "T2")
        # 2026-10-24 is Saturday (T7)
        self.assertEqual(self.ws.cell(row=2, column=11).value, "T7")
        # 2026-10-25 is Sunday (CN)
        self.assertEqual(self.ws.cell(row=2, column=12).value, "CN")
        # 2026-11-01 is Sunday (CN)
        self.assertEqual(self.ws.cell(row=2, column=19).value, "CN")

    def test_08_employee_blocks_and_labels(self):
        expected_labels = [
            "HCN 100%", "TCN 150%", "HCĐ 130%", "TCĐ 195%",
            "Ngày CN (200%)", "Đêm CN (260%)", "Suất ăn"
        ]
        for r_start in [3, 10, 17, 24]:
            actual_labels = [self.ws.cell(row=r_start + i, column=5).value for i in range(7)]
            self.assertEqual(actual_labels, expected_labels)

    def test_09_employee_names_in_column_c(self):
        self.assertIn("NGUYỄN NGỌC THAO", str(self.ws.cell(row=3, column=3).value))
        self.assertIn("NGUYỄN ĐỨC CÔNG", str(self.ws.cell(row=10, column=3).value))
        self.assertIn("TÔ VĂN HƯNG", str(self.ws.cell(row=17, column=3).value))
        self.assertIn("HOÀNG ĐẮC PHÚ", str(self.ws.cell(row=24, column=3).value))

    def test_10_horizontal_sum_formulas_ak_to_aq(self):
        for r in [3, 10, 17, 24]:
            for offset in range(7):
                col = 37 + offset
                formula = self.ws.cell(row=r, column=col).value
                expected = f"=SUM(F{r+offset}:AJ{r+offset})"
                self.assertEqual(formula, expected)

    def test_11_total_hours_formula_ar_strictly_excludes_aq(self):
        # Column AR must be =SUM(AK{R}:AP{R})
        for r in [3, 10, 17, 24]:
            formula = self.ws.cell(row=r, column=44).value
            self.assertEqual(formula, f"=SUM(AK{r}:AP{r})")
            # Strictly verify AQ (meals) is not in the formula range
            self.assertNotIn("AQ", str(formula))

    def test_12_row2_grand_totals_formulas(self):
        for col in range(37, 45):
            col_letter = openpyxl.utils.get_column_letter(col)
            formula = self.ws.cell(row=2, column=col).value
            expected = f"=SUM({col_letter}3,{col_letter}10,{col_letter}17,{col_letter}24)"
            self.assertEqual(formula, expected)

    def test_13_merged_cells_structure(self):
        ranges = [str(r) for r in self.ws.merged_cells.ranges]
        self.assertIn("A1:A2", ranges)
        self.assertIn("C1:C2", ranges)
        # HOÀNG ĐẮC PHÚ is row 24..30
        self.assertIn("A24:A30", ranges)
        self.assertIn("C24:C30", ranges)

    def test_14_full_calc_on_load_enabled(self):
        self.assertTrue(self.wb.calculation.fullCalcOnLoad)

    def test_15_freeze_panes_configured(self):
        self.assertEqual(self.ws.freeze_panes, "F3")


class TestEmployeeMatcher(unittest.TestCase):
    """Unit tests for 3-tier employee matching."""

    @classmethod
    def setUpClass(cls):
        cls.integrator = ExcelIntegrator()

    def test_01_tier1_exact_match(self):
        row, name, score = self.integrator.match_employee("HOÀNG ĐẮC PHÚ")
        self.assertEqual(row, 24)
        self.assertEqual(score, 1.0)
        self.assertIn("HOÀNG ĐẮC PHÚ", name)

    def test_02_tier1_all_employees(self):
        test_cases = [
            ("NGUYỄN NGỌC THAO", 3),
            ("NGUYỄN ĐỨC CÔNG", 10),
            ("TÔ VĂN HƯNG", 17),
            ("HOÀNG ĐẮC PHÚ", 24),
        ]
        for query, expected_row in test_cases:
            row, _, score = self.integrator.match_employee(query)
            self.assertEqual(row, expected_row)
            self.assertEqual(score, 1.0)

    def test_03_tier1_case_insensitivity(self):
        row, _, score = self.integrator.match_employee("hoàng đắc phú")
        self.assertEqual(row, 24)
        self.assertEqual(score, 1.0)

        row, _, score = self.integrator.match_employee("Nguyễn Đức Công")
        self.assertEqual(row, 10)
        self.assertEqual(score, 1.0)

    def test_04_tier1_whitespace_handling(self):
        row, _, score = self.integrator.match_employee("  HOÀNG    ĐẮC   PHÚ   ")
        self.assertEqual(row, 24)
        self.assertEqual(score, 1.0)

    def test_05_tier1_template_trailing_space_tolerance(self):
        # CSV has "NGUYỄN NGỌC THAO " with trailing space
        row, _, score = self.integrator.match_employee("NGUYỄN NGỌC THAO")
        self.assertEqual(row, 3)
        self.assertEqual(score, 1.0)

    def test_06_tier2_unaccented_matching(self):
        row, _, score = self.integrator.match_employee("HOANG DAC PHU")
        self.assertEqual(row, 24)
        self.assertEqual(score, 0.95)

        row, _, score = self.integrator.match_employee("to van hung")
        self.assertEqual(row, 17)
        self.assertEqual(score, 0.95)

        row, _, score = self.integrator.match_employee("nguyen duc cong")
        self.assertEqual(row, 10)
        self.assertEqual(score, 0.95)

    def test_07_tier3_fuzzy_matching_minor_typos(self):
        # 'HOÀNG ĐĂC PHÚ' has 'ă' instead of 'ắ'
        row, _, score = self.integrator.match_employee("HOÀNG ĐĂC PHÚ")
        self.assertEqual(row, 24)
        self.assertGreaterEqual(score, 0.85)

        # 'Nguyen Duc Congg' with duplicate letter
        row, _, score = self.integrator.match_employee("Nguyen Duc Congg")
        self.assertEqual(row, 10)
        self.assertGreaterEqual(score, 0.85)

    def test_08_unmatched_employee_returns_none(self):
        row, name, score = self.integrator.match_employee("TRẦN THỊ LẠ MẶT")
        self.assertIsNone(row)
        self.assertEqual(name, "")
        self.assertEqual(score, 0.0)

        row, name, score = self.integrator.match_employee("")
        self.assertIsNone(row)
        self.assertEqual(score, 0.0)

    def test_09_resolve_employee_row_helper(self):
        self.assertEqual(self.integrator.resolve_employee_row("HOÀNG ĐẮC PHÚ"), 24)
        self.assertEqual(self.integrator.resolve_employee_row("NGUYỄN NGỌC THAO"), 3)
        self.assertIsNone(self.integrator.resolve_employee_row("UNKNOWN PERSON"))

    def test_10_role_annotations_parenthesized(self):
        """Tests that parenthesized role annotations (e.g. KTV, thợ hàn, Tổ 1) are stripped and matched."""
        test_cases = [
            ("Hoàng Đắc Phú (KTV)", 24, "HOÀNG ĐẮC PHÚ"),
            ("Hoàng Đắc Phú (thợ hàn)", 24, "HOÀNG ĐẮC PHÚ"),
            ("Nguyễn Đức Công (Tổ 1)", 10, "NGUYỄN ĐỨC CÔNG"),
            ("Nguyễn Ngọc Thao (Cơ điện)", 3, "NGUYỄN NGỌC THAO"),
            ("Hoàng Đắc Phú [KTV]", 24, "HOÀNG ĐẮC PHÚ"),
        ]
        for query, expected_row, expected_name in test_cases:
            row, name, score = self.integrator.match_employee(query)
            self.assertEqual(row, expected_row, f"Failed on {query}")
            self.assertIn(expected_name, name)
            self.assertGreaterEqual(score, 0.85)

    def test_11_phone_number_suffixes(self):
        """Tests employee names with phone numbers (plain, hyphenated, +84) match properly."""
        test_cases = [
            ("Hoàng Đắc Phú 0912345678", 24),
            ("Hoàng Đắc Phú - 0912345678", 24),
            ("Hoàng Đắc Phú +84912345678", 24),
            ("Nguyễn Đức Công 0987654321", 10),
            ("Tô Văn Hưng - 0901234567", 17),
        ]
        for query, expected_row in test_cases:
            row, name, score = self.integrator.match_employee(query)
            self.assertEqual(row, expected_row, f"Failed on {query}")
            self.assertGreaterEqual(score, 0.85)

    def test_12_substring_and_token_containment(self):
        """Tests token containment and word-boundary substring matches."""
        test_cases = [
            ("Kỹ thuật viên Hoàng Đắc Phú", 24),
            ("NV Nguyễn Đức Công", 10),
            ("Hoàng Đắc Phú - KTV", 24),
            ("Hoàng Đắc Phú : Tổ 1", 24),
            ("Tô Văn Hưng - Xưởng ETS", 17),
        ]
        for query, expected_row in test_cases:
            row, name, score = self.integrator.match_employee(query)
            self.assertEqual(row, expected_row, f"Failed on {query}")
            self.assertGreaterEqual(score, 0.85)

    def test_13_non_existent_and_invalid_names_return_none(self):
        """Tests that non-existent names, digits, and special characters return (None, '', 0.0)."""
        invalid_names = [
            "Alexander the Great",
            "John Doe",
            "Trần Văn Vô Danh",
            "NonExistent Worker 999",
            "Công ty Cổ phần Xây dựng",
            "!@#$%^&*()",
            "1234567890",
            "",
            "   ",
        ]
        for query in invalid_names:
            row, name, score = self.integrator.match_employee(query)
            self.assertIsNone(row, f"Should be None for {query!r}")
            self.assertEqual(name, "")
            self.assertEqual(score, 0.0)

    def test_14_clean_employee_name_helper(self):
        """Tests the clean_employee_name_for_matching standalone utility function."""
        self.assertEqual(clean_employee_name_for_matching("Hoàng Đắc Phú (KTV)"), "Hoàng Đắc Phú")
        self.assertEqual(clean_employee_name_for_matching("Hoàng Đắc Phú 0912345678"), "Hoàng Đắc Phú")
        self.assertEqual(clean_employee_name_for_matching("Hoàng Đắc Phú - 0912345678"), "Hoàng Đắc Phú")
        self.assertEqual(clean_employee_name_for_matching("Nguyễn Đức Công (Tổ 1)"), "Nguyễn Đức Công")
        self.assertEqual(clean_employee_name_for_matching(""), "")
        self.assertEqual(clean_employee_name_for_matching(None), "")


class TestDateColumnResolution(unittest.TestCase):
    """Unit tests for multi-format date column resolution."""

    @classmethod
    def setUpClass(cls):
        cls.integrator = ExcelIntegrator()

    def test_01_resolve_iso_format(self):
        self.assertEqual(self.integrator.resolve_date_column("2026-10-24"), 11)
        self.assertEqual(self.integrator.resolve_date_column("2026-10-19"), 6)
        self.assertEqual(self.integrator.resolve_date_column("2026-11-18"), 36)

    def test_02_resolve_slash_format_dd_mm(self):
        self.assertEqual(self.integrator.resolve_date_column("24/10"), 11)
        self.assertEqual(self.integrator.resolve_date_column("19/10"), 6)
        self.assertEqual(self.integrator.resolve_date_column("18/11"), 36)

    def test_03_resolve_dash_format_dd_mm(self):
        self.assertEqual(self.integrator.resolve_date_column("24-10"), 11)
        self.assertEqual(self.integrator.resolve_date_column("19-10"), 6)
        self.assertEqual(self.integrator.resolve_date_column("18-11"), 36)

    def test_04_resolve_full_format_dd_mm_yyyy(self):
        self.assertEqual(self.integrator.resolve_date_column("24/10/2026"), 11)
        self.assertEqual(self.integrator.resolve_date_column("19-10-2026"), 6)

    def test_05_resolve_day_number_only(self):
        self.assertEqual(self.integrator.resolve_date_column(24), 11)
        self.assertEqual(self.integrator.resolve_date_column("24"), 11)
        self.assertEqual(self.integrator.resolve_date_column(19), 6)
        self.assertEqual(self.integrator.resolve_date_column(18), 36)

    def test_06_resolve_datetime_date_object(self):
        dt = datetime.date(2026, 10, 24)
        self.assertEqual(self.integrator.resolve_date_column(dt), 11)
        dtt = datetime.datetime(2026, 10, 24, 17, 30)
        self.assertEqual(self.integrator.resolve_date_column(dtt), 11)

    def test_07_resolve_date_out_of_range(self):
        self.assertIsNone(self.integrator.resolve_date_column("15/10"))
        self.assertIsNone(self.integrator.resolve_date_column("25/11"))
        self.assertIsNone(self.integrator.resolve_date_column("2026-10-18"))
        self.assertIsNone(self.integrator.resolve_date_column("2026-11-19"))

    def test_08_resolve_invalid_date_inputs(self):
        self.assertIsNone(self.integrator.resolve_date_column("invalid_date"))
        self.assertIsNone(self.integrator.resolve_date_column(""))
        self.assertIsNone(self.integrator.resolve_date_column(None))
        self.assertIsNone(self.integrator.resolve_date_column(99))


class TestExcelIntegratorApplyRecords(unittest.TestCase):
    """Unit & Integration tests for applying records and preserving formulas."""

    def setUp(self):
        self.integrator = ExcelIntegrator()

    def test_01_template_info_schema(self):
        info = self.integrator.get_template_info()
        self.assertEqual(info["sheet_name"], "CHẤM CÔNG WEVN - ETS")
        self.assertEqual(len(info["employees"]), 4)
        self.assertIn("HOÀNG ĐẮC PHÚ", info["employees"])
        self.assertEqual(info["date_range"], ["2026-10-19", "2026-11-18"])

    def test_02_acceptance_criteria_hoang_dac_phu_24_10(self):
        """
        Official Acceptance Criteria verification:
        HOÀNG ĐẮC PHÚ on 24/10 -> K24=8, K30=0, AK24==SUM(F24:AJ24), AR24==SUM(AK24:AP24).
        """
        raw_msg = (
            "HỌ TÊN : HOÀNG ĐẮC PHÚ\n"
            "NGÀY: 24/10\n"
            "CA : Ca ngày \n"
            "DỰ ÁN : sdv \n"
            "THỜI GIAN LÀM VIỆC :8h-17h ( 8H)\n"
            "CÓ ĂN Ở XƯỞNG KO : 0"
        )
        rec = parse_single_message(raw_msg)
        self.assertEqual(rec.normalized_name.upper(), "HOÀNG ĐẮC PHÚ")
        self.assertEqual(rec.hours.hcn_100, 8.0)
        self.assertEqual(rec.meal_count, 0)

        buf = io.BytesIO()
        result = self.integrator.apply_records([rec], output_path=buf)
        self.assertEqual(result["records_processed"], 1)
        self.assertEqual(result["cells_written"], 2)
        self.assertEqual(result["employees_matched"], 1)
        self.assertEqual(len(result["errors"]), 0)

        # Reload and verify cell coordinates and types
        reloaded = openpyxl.load_workbook(buf, data_only=False)
        ws = reloaded.active

        # 1. K24 is HCN (offset 0), value=8, numeric type
        self.assertEqual(ws["K24"].value, 8)
        self.assertEqual(ws["K24"].data_type, "n")

        # 2. K30 is Suất ăn (offset 6), value=0, numeric type
        self.assertEqual(ws["K30"].value, 0)
        self.assertEqual(ws["K30"].data_type, "n")

        # 3. Formulas in AK24 and AR24 remain formulas verbatim
        self.assertEqual(ws["AK24"].value, "=SUM(F24:AJ24)")
        self.assertEqual(ws["AR24"].value, "=SUM(AK24:AP24)")

        # 4. Row 2 Grand Totals preserved
        self.assertEqual(ws["AK2"].value, "=SUM(AK3,AK10,AK17,AK24)")
        self.assertEqual(ws["AR2"].value, "=SUM(AR3,AR10,AR17,AR24)")

        # 5. Calculation property enabled
        self.assertTrue(reloaded.calculation.fullCalcOnLoad)

    def test_03_numeric_types_integer_and_decimal(self):
        """Verifies integer and fractional hours are stored strictly as numeric, not string."""
        record = AttendanceRecord(
            id="test-num-1",
            employee_name="HOÀNG ĐẮC PHÚ",
            normalized_name="HOÀNG ĐẮC PHÚ",
            date_str="24/10",
            resolved_date="2026-10-24",
            day_number=24,
            is_sunday=False,
            shift_type="DAY",
            project="sdv",
            time_window="8h-18h30 (10.5H)",
            hours=WorkHours(hcn_100=8.0, tcn_150=2.5, total_hours=10.5),
            meal_count=1,
            status="VALID",
            raw_text="mock"
        )
        buf = io.BytesIO()
        self.integrator.apply_records([record], output_path=buf)
        ws = openpyxl.load_workbook(buf, data_only=False).active

        # HCN (8) should be int
        self.assertEqual(type(ws["K24"].value), int)
        self.assertEqual(ws["K24"].value, 8)

        # TCN (2.5) should be float
        self.assertEqual(type(ws["K25"].value), float)
        self.assertEqual(ws["K25"].value, 2.5)

        # Meal (1) should be int
        self.assertEqual(type(ws["K30"].value), int)
        self.assertEqual(ws["K30"].value, 1)

    def test_04_all_7_row_offsets(self):
        """Verifies each work hours category maps to its designated row offset (0..6)."""
        # Employee 2 (NGUYỄN ĐỨC CÔNG) starts at row 10
        # Target date: 2026-10-25 (Sunday, Column 12 / L)
        record = AttendanceRecord(
            id="test-offsets",
            employee_name="NGUYỄN ĐỨC CÔNG",
            normalized_name="NGUYỄN ĐỨC CÔNG",
            date_str="25/10",
            resolved_date="2026-10-25",
            day_number=25,
            is_sunday=True,
            shift_type="DAY",
            project="ets",
            time_window="8h-17h (8H)",
            hours=WorkHours(sunday_day_200=8.0, total_hours=8.0),
            meal_count=1,
            status="VALID",
            raw_text="mock"
        )
        buf = io.BytesIO()
        self.integrator.apply_records([record], output_path=buf)
        ws = openpyxl.load_workbook(buf, data_only=False).active

        # Sunday day is row 10 + 4 = 14, col 12 (L)
        self.assertEqual(ws.cell(row=14, column=12).value, 8)
        self.assertEqual(ws.cell(row=14, column=12).data_type, "n")
        # Meal is row 10 + 6 = 16, col 12
        self.assertEqual(ws.cell(row=16, column=12).value, 1)

    def test_05_night_shift_and_overtime_offsets(self):
        """Verifies night shift regular (offset 2) and night overtime (offset 3)."""
        # TÔ VĂN HƯNG starts at row 17. Date 2026-10-26 (Col 13 / M)
        record = AttendanceRecord(
            id="test-night",
            employee_name="TÔ VĂN HƯNG",
            normalized_name="TÔ VĂN HƯNG",
            date_str="26/10",
            resolved_date="2026-10-26",
            day_number=26,
            is_sunday=False,
            shift_type="NIGHT",
            project="ets",
            time_window="20h-8h (11H)",
            hours=WorkHours(hcd_130=8.0, tcd_195=3.0, total_hours=11.0),
            meal_count=2,
            status="VALID",
            raw_text="mock"
        )
        buf = io.BytesIO()
        self.integrator.apply_records([record], output_path=buf)
        ws = openpyxl.load_workbook(buf, data_only=False).active

        # HCĐ is row 17 + 2 = 19, col 13
        self.assertEqual(ws.cell(row=19, column=13).value, 8)
        # TCĐ is row 17 + 3 = 20, col 13
        self.assertEqual(ws.cell(row=20, column=13).value, 3)
        # Meal is row 17 + 6 = 23, col 13
        self.assertEqual(ws.cell(row=23, column=13).value, 2)

    def test_06_unmatched_employee_handled_gracefully(self):
        record = AttendanceRecord(
            id="test-unmatched",
            employee_name="VÕ HOÀNG YẾN",
            normalized_name="VÕ HOÀNG YẾN",
            date_str="24/10",
            resolved_date="2026-10-24",
            day_number=24,
            is_sunday=False,
            shift_type="DAY",
            project="ets",
            time_window="8h-17h (8H)",
            hours=WorkHours(hcn_100=8.0, total_hours=8.0),
            meal_count=1,
            status="VALID",
            raw_text="mock"
        )
        buf = io.BytesIO()
        result = self.integrator.apply_records([record], output_path=buf)
        self.assertEqual(result["records_processed"], 1)
        self.assertEqual(result["cells_written"], 0)
        self.assertEqual(result["unmatched_records"], 1)
        self.assertIn("VÕ HOÀNG YẾN", result["unmatched_list"])
        self.assertTrue(any("Unmatched" in err for err in result["errors"]))

    def test_07_date_out_of_range_handled_gracefully(self):
        record = AttendanceRecord(
            id="test-out-of-range",
            employee_name="HOÀNG ĐẮC PHÚ",
            normalized_name="HOÀNG ĐẮC PHÚ",
            date_str="15/10",
            resolved_date="2026-10-15",
            day_number=15,
            is_sunday=False,
            shift_type="DAY",
            project="ets",
            time_window="8h-17h (8H)",
            hours=WorkHours(hcn_100=8.0, total_hours=8.0),
            meal_count=0,
            status="VALID",
            raw_text="mock"
        )
        buf = io.BytesIO()
        result = self.integrator.apply_records([record], output_path=buf)
        self.assertEqual(result["cells_written"], 0)
        self.assertTrue(any("Date out of range" in err for err in result["errors"]))

    def test_08_error_status_record_skipped(self):
        record = AttendanceRecord(
            id="test-err",
            employee_name="HOÀNG ĐẮC PHÚ",
            normalized_name="HOÀNG ĐẮC PHÚ",
            date_str="24/10",
            resolved_date="2026-10-24",
            day_number=24,
            is_sunday=False,
            shift_type="DAY",
            project="ets",
            time_window="unknown",
            hours=WorkHours(),
            meal_count=0,
            status="ERROR",
            messages=["Cú pháp không hợp lệ"],
            raw_text="mock"
        )
        buf = io.BytesIO()
        result = self.integrator.apply_records([record], output_path=buf)
        self.assertEqual(result["cells_written"], 0)
        self.assertTrue(any("Skipping error record" in err for err in result["errors"]))

    def test_09_save_to_file_system(self):
        tmp_path = os.path.join(PROJECT_ROOT, "output", "test_output_run.xlsx")
        rec = parse_single_message("HỌ TÊN: HOÀNG ĐẮC PHÚ\nNGÀY: 24/10\nCA: Ca ngày\nTHỜI GIAN: 8h-17h (8H)\nCÓ ĂN: 0")
        result = self.integrator.apply_records([rec], output_path=tmp_path)
        self.assertTrue(os.path.exists(tmp_path))
        self.assertEqual(result["output_path"], tmp_path)

        # Clean up test file
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


if __name__ == "__main__":
    unittest.main()
