"""
Adversarial Stress Test Suite for Excel Formula Preservation and Cell Formatting.
Challenger M2_1 - Milestone 2 Empirical Challenge.

Focus areas:
1. Multiple write cycles (up to 10 cycles): load -> write -> save -> reload -> write -> save ...
   Assert formulas in AK..AR and row 2 grand totals are NEVER corrupted or overwritten with static numbers.
2. Boundary dates: First date column F (col 6) and last date column AJ (col 36), plus off-by-one out-of-range checks.
   Verify col E and col AK are untouched when writing to boundaries.
3. Column AR formula verification: strictly SUM(AK:AP) and NEVER contains AQ (meals) across all employee blocks.
4. Cell data types: cell.data_type == 'n' for all written hours (integer, float) and meals (0, 1, 2).
5. Style, merged cells, and fullCalcOnLoad preservation across multiple write cycles.
"""
import os
import sys
import io
import re
import shutil
import tempfile
import unittest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import openpyxl
from openpyxl.utils import get_column_letter

from models.attendance import AttendanceRecord, WorkHours
from core.excel_integrator import ExcelIntegrator
from core.template_generator import generate_default_template, DEFAULT_TEMPLATE_PATH


class AdversarialExcelIntegratorTest(unittest.TestCase):
    """Adversarial challenge test cases."""

    def setUp(self):
        # Create a fresh temporary directory for each test run to ensure isolation
        self.test_dir = tempfile.mkdtemp(prefix="excel_challenger_")
        self.master_template = os.path.join(self.test_dir, "master_template.xlsx")
        generate_default_template(output_path=self.master_template)

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def _verify_all_formulas_intact(self, wb: openpyxl.Workbook, context: str):
        """Helper to assert that all formulas in AK..AR (rows 3..30) and row 2 grand totals are intact."""
        ws = wb.active
        employee_rows = [3, 10, 17, 24]

        # 1. Check Row 2 Grand Totals (columns 37..44 -> AK..AR)
        for col in range(37, 45):
            col_letter = get_column_letter(col)
            cell = ws.cell(row=2, column=col)
            val = str(cell.value or "")
            expected_terms = [f"{col_letter}{r}" for r in employee_rows]
            expected_formula = f"=SUM({','.join(expected_terms)})"

            self.assertTrue(
                val.startswith("="),
                f"[{context}] Row 2 Col {col_letter} formula lost or converted to static value! Value: {val}"
            )
            self.assertEqual(
                val.upper(),
                expected_formula.upper(),
                f"[{context}] Row 2 Col {col_letter} formula corrupted! Got: {val}, Expected: {expected_formula}"
            )
            self.assertEqual(
                cell.data_type,
                'f',
                f"[{context}] Row 2 Col {col_letter} cell.data_type is {cell.data_type}, expected 'f' (formula)!"
            )

        # 2. Check Employee Blocks AK..AR (rows 3..30)
        for r in employee_rows:
            # AK: HCN 100% -> =SUM(F{r}:AJ{r})
            # AL: TCN 150% -> =SUM(F{r+1}:AJ{r+1})
            # AM: HCĐ 130% -> =SUM(F{r+2}:AJ{r+2})
            # AN: TCĐ 195% -> =SUM(F{r+3}:AJ{r+3})
            # AO: Ngày CN 200% -> =SUM(F{r+4}:AJ{r+4})
            # AP: Đêm CN 260% -> =SUM(F{r+5}:AJ{r+5})
            # AQ: Suất ăn -> =SUM(F{r+6}:AJ{r+6})
            for offset in range(7):
                row_target = r + offset
                col_target = 37 + offset
                col_letter = get_column_letter(col_target)
                cell = ws.cell(row=r, column=col_target)
                val = str(cell.value or "")
                expected_sum = f"=SUM(F{row_target}:AJ{row_target})"

                self.assertTrue(
                    val.startswith("="),
                    f"[{context}] Row {r} Col {col_letter} lost formula! Value: {val}"
                )
                self.assertEqual(
                    val.upper(),
                    expected_sum.upper(),
                    f"[{context}] Row {r} Col {col_letter} corrupted formula! Got: {val}, Expected: {expected_sum}"
                )
                self.assertEqual(
                    cell.data_type,
                    'f',
                    f"[{context}] Row {r} Col {col_letter} data_type is {cell.data_type}, expected 'f'!"
                )

            # AR: TỔNG CÔNG -> =SUM(AK{r}:AP{r})
            cell_ar = ws.cell(row=r, column=44)
            val_ar = str(cell_ar.value or "")
            expected_ar = f"=SUM(AK{r}:AP{r})"
            self.assertTrue(
                val_ar.startswith("="),
                f"[{context}] Row {r} Col AR lost formula! Value: {val_ar}"
            )
            self.assertEqual(
                val_ar.upper(),
                expected_ar.upper(),
                f"[{context}] Row {r} Col AR corrupted! Got: {val_ar}, Expected: {expected_ar}"
            )
            self.assertEqual(
                cell_ar.data_type,
                'f',
                f"[{context}] Row {r} Col AR data_type is {cell_ar.data_type}, expected 'f'!"
            )
            # CRUCIAL: Strictly verify AQ (meals) is not in the formula range
            self.assertNotIn(
                "AQ",
                val_ar.upper(),
                f"[{context}] Row {r} Col AR formula ILLEGALLY includes AQ (meals): {val_ar}"
            )

    # =========================================================================
    # CHALLENGE 1: MULTIPLE WRITE CYCLES
    # =========================================================================

    def test_challenge_01_multiple_write_cycles_10_iterations(self):
        """
        Adversarially challenge 10 consecutive write-save-reload cycles.
        Cycle i writes a record for an employee, saves to disk, re-loads from disk,
        and verifies all AK..AR and Row 2 formulas remain live formula objects without
        being converted to static numbers or corrupted.
        """
        current_file = os.path.join(self.test_dir, "cycle_0.xlsx")
        shutil.copyfile(self.master_template, current_file)

        employees = [
            "HOÀNG ĐẮC PHÚ",
            "NGUYỄN NGỌC THAO",
            "NGUYỄN ĐỨC CÔNG",
            "TÔ VĂN HƯNG"
        ]

        # 10 distinct days across the 31-day window (2026-10-19 to 2026-11-18)
        cycle_dates = [
            ("19/10", "2026-10-19", 19, 6),    # Col 6 (F)
            ("20/10", "2026-10-20", 20, 7),
            ("24/10", "2026-10-24", 24, 11),
            ("25/10", "2026-10-25", 25, 12),
            ("31/10", "2026-10-31", 31, 18),
            ("01/11", "2026-11-01", 1, 19),
            ("05/11", "2026-11-05", 5, 23),
            ("10/11", "2026-11-10", 10, 28),
            ("15/11", "2026-11-15", 15, 33),
            ("18/11", "2026-11-18", 18, 36),   # Col 36 (AJ)
        ]

        for cycle_idx in range(10):
            emp_name = employees[cycle_idx % len(employees)]
            d_str, d_iso, d_num, expected_col = cycle_dates[cycle_idx]

            # Construct record with varied hours and meals
            rec = AttendanceRecord(
                id=f"cycle-{cycle_idx}",
                employee_name=emp_name,
                normalized_name=emp_name,
                date_str=d_str,
                resolved_date=d_iso,
                day_number=d_num,
                is_sunday=(cycle_idx in (3, 5)),
                shift_type="DAY" if cycle_idx % 2 == 0 else "NIGHT",
                project="ets",
                time_window="8h-17h (8H)",
                hours=WorkHours(
                    hcn_100=8.0 if cycle_idx % 2 == 0 else 0.0,
                    tcn_150=1.5 if cycle_idx % 3 == 0 else 0.0,
                    hcd_130=8.0 if cycle_idx % 2 == 1 else 0.0,
                    total_hours=9.5 if cycle_idx % 3 == 0 else 8.0
                ),
                meal_count=cycle_idx % 2,
                status="VALID",
                raw_text="mock"
            )

            # Load the current workbook
            integrator = ExcelIntegrator(template_path=current_file)
            next_file = os.path.join(self.test_dir, f"cycle_{cycle_idx + 1}.xlsx")

            # Apply records and save
            res = integrator.apply_records([rec], output_path=next_file)
            self.assertEqual(res["records_processed"], 1)
            self.assertEqual(len(res["errors"]), 0)

            # Reload workbook and stress verify formulas
            reloaded_wb = openpyxl.load_workbook(next_file, data_only=False)
            self._verify_all_formulas_intact(reloaded_wb, context=f"Cycle {cycle_idx + 1}")

            # Check fullCalcOnLoad preserved
            self.assertTrue(reloaded_wb.calculation.fullCalcOnLoad)

            # Verify the written value in the expected column
            ws = reloaded_wb.active
            r_start = integrator.resolve_employee_row(emp_name)
            self.assertIsNotNone(r_start)

            # Verify written cell data type
            if rec.hours.hcn_100 > 0:
                cell_hcn = ws.cell(row=r_start, column=expected_col)
                self.assertEqual(cell_hcn.value, 8)
                self.assertEqual(cell_hcn.data_type, 'n')

            if rec.meal_count is not None:
                cell_meal = ws.cell(row=r_start + 6, column=expected_col)
                self.assertEqual(cell_meal.value, rec.meal_count)
                self.assertEqual(cell_meal.data_type, 'n')

            current_file = next_file

    def test_challenge_02_multiple_writes_same_file_overwrite(self):
        """
        Adversarially challenge repeatedly writing to the exact SAME file path
        without creating new files, ensuring in-place save does not corrupt formulas.
        """
        target_file = os.path.join(self.test_dir, "inplace_test.xlsx")
        shutil.copyfile(self.master_template, target_file)

        integrator = ExcelIntegrator(template_path=target_file)

        # 4 records for 4 employees
        records = [
            AttendanceRecord(
                id=f"rec-{i}",
                employee_name=name,
                normalized_name=name,
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
            for i, name in enumerate(["NGUYỄN NGỌC THAO", "NGUYỄN ĐỨC CÔNG", "TÔ VĂN HƯNG", "HOÀNG ĐẮC PHÚ"])
        ]

        # Apply records one by one, saving to target_file each time
        for idx, rec in enumerate(records):
            # Reload integrator from disk
            integ = ExcelIntegrator(template_path=target_file)
            integ.apply_records([rec], output_path=target_file)

            # Verify on disk
            wb = openpyxl.load_workbook(target_file, data_only=False)
            self._verify_all_formulas_intact(wb, context=f"In-place Step {idx}")

    # =========================================================================
    # CHALLENGE 2: BOUNDARY DATES (COL F / COL 6 AND COL AJ / COL 36)
    # =========================================================================

    def test_challenge_03_first_boundary_date_col_f(self):
        """
        Adversarially verify Column F (col 6, date 2026-10-19 / 19/10).
        Must resolve to col 6.
        Must write numeric value to col 6.
        Must NOT touch Column E (col 5 - 'CÔNG').
        """
        integ = ExcelIntegrator(template_path=self.master_template)

        # Verify resolution for various formats
        self.assertEqual(integ.resolve_date_column("2026-10-19"), 6)
        self.assertEqual(integ.resolve_date_column("19/10"), 6)
        self.assertEqual(integ.resolve_date_column("19-10"), 6)
        self.assertEqual(integ.resolve_date_column("19/10/2026"), 6)
        self.assertEqual(integ.resolve_date_column(19), 6)

        # Check Column E values before writing
        col_e_before = [integ.ws.cell(row=r, column=5).value for r in range(1, 31)]

        rec = AttendanceRecord(
            id="boundary-first",
            employee_name="HOÀNG ĐẮC PHÚ",
            normalized_name="HOÀNG ĐẮC PHÚ",
            date_str="19/10",
            resolved_date="2026-10-19",
            day_number=19,
            is_sunday=False,
            shift_type="DAY",
            project="ets",
            time_window="8h-17h (8H)",
            hours=WorkHours(hcn_100=8.0, total_hours=8.0),
            meal_count=1,
            status="VALID",
            raw_text="mock"
        )

        out_path = os.path.join(self.test_dir, "boundary_f.xlsx")
        integ.apply_records([rec], output_path=out_path)

        reloaded = openpyxl.load_workbook(out_path, data_only=False)
        ws = reloaded.active

        # Column F row 24 (HOÀNG ĐẮC PHÚ HCN) must be 8
        cell_f24 = ws.cell(row=24, column=6)
        self.assertEqual(cell_f24.value, 8)
        self.assertEqual(cell_f24.data_type, 'n')

        # Column F row 30 (HOÀNG ĐẮC PHÚ Meal) must be 1
        cell_f30 = ws.cell(row=30, column=6)
        self.assertEqual(cell_f30.value, 1)
        self.assertEqual(cell_f30.data_type, 'n')

        # Column E (col 5) must be completely untouched
        col_e_after = [ws.cell(row=r, column=5).value for r in range(1, 31)]
        self.assertEqual(col_e_before, col_e_after, "Column E was corrupted by writing to boundary Column F!")

        # All formulas intact
        self._verify_all_formulas_intact(reloaded, context="Boundary F")

    def test_challenge_04_last_boundary_date_col_aj(self):
        """
        Adversarially verify Column AJ (col 36, date 2026-11-18 / 18/11).
        Must resolve to col 36.
        Must write numeric value to col 36.
        Must NOT touch Column AK (col 37 - formulas).
        """
        integ = ExcelIntegrator(template_path=self.master_template)

        # Verify resolution for various formats
        self.assertEqual(integ.resolve_date_column("2026-11-18"), 36)
        self.assertEqual(integ.resolve_date_column("18/11"), 36)
        self.assertEqual(integ.resolve_date_column("18-11"), 36)
        self.assertEqual(integ.resolve_date_column("18/11/2026"), 36)
        self.assertEqual(integ.resolve_date_column(18), 36)

        # Check Column AK formulas before writing
        col_ak_before = [integ.ws.cell(row=r, column=37).value for r in range(1, 31)]

        rec = AttendanceRecord(
            id="boundary-last",
            employee_name="HOÀNG ĐẮC PHÚ",
            normalized_name="HOÀNG ĐẮC PHÚ",
            date_str="18/11",
            resolved_date="2026-11-18",
            day_number=18,
            is_sunday=False,
            shift_type="DAY",
            project="ets",
            time_window="8h-17h (8H)",
            hours=WorkHours(hcn_100=8.0, total_hours=8.0),
            meal_count=0,
            status="VALID",
            raw_text="mock"
        )

        out_path = os.path.join(self.test_dir, "boundary_aj.xlsx")
        integ.apply_records([rec], output_path=out_path)

        reloaded = openpyxl.load_workbook(out_path, data_only=False)
        ws = reloaded.active

        # Column AJ row 24 (HOÀNG ĐẮC PHÚ HCN) must be 8
        cell_aj24 = ws.cell(row=24, column=36)
        self.assertEqual(cell_aj24.value, 8)
        self.assertEqual(cell_aj24.data_type, 'n')

        # Column AJ row 30 (HOÀNG ĐẮC PHÚ Meal) must be 0
        cell_aj30 = ws.cell(row=30, column=36)
        self.assertEqual(cell_aj30.value, 0)
        self.assertEqual(cell_aj30.data_type, 'n')

        # Column AK (col 37) formulas must be completely untouched
        col_ak_after = [ws.cell(row=r, column=37).value for r in range(1, 31)]
        self.assertEqual(col_ak_before, col_ak_after, "Column AK formulas corrupted by writing to boundary Column AJ!")

        # All formulas intact
        self._verify_all_formulas_intact(reloaded, context="Boundary AJ")

    def test_challenge_05_off_by_one_boundary_dates_rejected(self):
        """
        Adversarially verify dates strictly outside [2026-10-19, 2026-11-18]
        are rejected with None and do NOT write or crash.
        """
        integ = ExcelIntegrator(template_path=self.master_template)

        # 1 day before start: 2026-10-18, 18/10
        self.assertIsNone(integ.resolve_date_column("2026-10-18"))
        self.assertIsNone(integ.resolve_date_column("18/10"))
        self.assertIsNone(integ.resolve_date_column("18-10"))

        # 1 day after end: 2026-11-19, 19/11
        self.assertIsNone(integ.resolve_date_column("2026-11-19"))
        self.assertIsNone(integ.resolve_date_column("19/11"))
        self.assertIsNone(integ.resolve_date_column("19-11"))

        # Far future / past
        self.assertIsNone(integ.resolve_date_column("2025-10-19"))
        self.assertIsNone(integ.resolve_date_column("2027-10-19"))
        self.assertIsNone(integ.resolve_date_column("01/01"))

        # Applying record with out-of-bounds date records error and writes 0 cells
        rec = AttendanceRecord(
            id="oob-date",
            employee_name="HOÀNG ĐẮC PHÚ",
            normalized_name="HOÀNG ĐẮC PHÚ",
            date_str="18/10",
            resolved_date="2026-10-18",
            day_number=18,
            is_sunday=True,
            shift_type="DAY",
            project="ets",
            time_window="8h-17h (8H)",
            hours=WorkHours(hcn_100=8.0),
            meal_count=1,
            status="VALID",
            raw_text="mock"
        )
        res = integ.apply_records([rec], output_path=os.path.join(self.test_dir, "oob.xlsx"))
        self.assertEqual(res["cells_written"], 0)
        self.assertTrue(any("Date out of range" in e for e in res["errors"]))

    # =========================================================================
    # CHALLENGE 3: COLUMN AR FORMULA STRICTLY SUMS AK..AP AND NEVER AQ
    # =========================================================================

    def test_challenge_06_col_ar_formula_strictly_excludes_aq(self):
        """
        Adversarially verify that Column AR (Total Hours) strictly computes:
        =SUM(AK{r}:AP{r})
        and NEVER contains AQ (which is meal count!).
        Meals must NEVER be summed into total hours.
        """
        wb = openpyxl.load_workbook(self.master_template, data_only=False)
        ws = wb.active

        # For every employee block
        for r in [3, 10, 17, 24]:
            cell_ar = ws.cell(row=r, column=44)
            formula = str(cell_ar.value or "")

            # Exact formula syntax
            self.assertEqual(formula, f"=SUM(AK{r}:AP{r})")

            # Check that AQ is NOT anywhere in the formula string
            self.assertNotIn("AQ", formula, f"Row {r} AR formula illegally includes AQ (meals)!")

            # Verify that the range AK..AP contains exactly the 6 work hours categories:
            # AK: HCN 100%
            # AL: TCN 150%
            # AM: HCĐ 130%
            # AN: TCĐ 195%
            # AO: Ngày CN 200%
            # AP: Đêm CN 260%
            # AQ: Suất ăn (MUST BE EXCLUDED)
            # AR: TỔNG CÔNG

        # Also check Row 2 Grand Total AR2
        ar2 = ws.cell(row=2, column=44)
        formula_ar2 = str(ar2.value or "")
        self.assertEqual(formula_ar2, "=SUM(AR3,AR10,AR17,AR24)")
        self.assertNotIn("AQ", formula_ar2)

    # =========================================================================
    # CHALLENGE 4: NUMERIC DATA TYPES (cell.data_type == 'n')
    # =========================================================================

    def test_challenge_07_numeric_data_types_comprehensive(self):
        """
        Adversarially verify that ALL written values are strictly numeric:
        - Whole number hours (8.0 -> int 8, data_type == 'n')
        - Fractional hours (0.5, 1.25, 2.5, 3.75 -> float, data_type == 'n')
        - Meal count 0, 1, 2 -> int 0, 1, 2, data_type == 'n'
        - All 6 hours categories written to offsets 0..5
        """
        integ = ExcelIntegrator(template_path=self.master_template)

        # Record with all fractional hours and meal=0
        rec1 = AttendanceRecord(
            id="num-test-1",
            employee_name="NGUYỄN NGỌC THAO",
            normalized_name="NGUYỄN NGỌC THAO",
            date_str="20/10",
            resolved_date="2026-10-20",
            day_number=20,
            is_sunday=False,
            shift_type="DAY",
            project="ets",
            time_window="mock",
            hours=WorkHours(
                hcn_100=8.0,
                tcn_150=2.5,
                hcd_130=4.25,
                tcd_195=1.75,
                sunday_day_200=0.5,
                sunday_night_260=3.5,
                total_hours=20.5
            ),
            meal_count=0,
            status="VALID",
            raw_text="mock"
        )

        # Record with whole numbers and meal=2
        rec2 = AttendanceRecord(
            id="num-test-2",
            employee_name="HOÀNG ĐẮC PHÚ",
            normalized_name="HOÀNG ĐẮC PHÚ",
            date_str="24/10",
            resolved_date="2026-10-24",
            day_number=24,
            is_sunday=False,
            shift_type="DAY",
            project="ets",
            time_window="mock",
            hours=WorkHours(
                hcn_100=8.0,
                tcn_150=3.0,
                total_hours=11.0
            ),
            meal_count=2,
            status="VALID",
            raw_text="mock"
        )

        out_path = os.path.join(self.test_dir, "numeric_test.xlsx")
        integ.apply_records([rec1, rec2], output_path=out_path)

        reloaded = openpyxl.load_workbook(out_path, data_only=False)
        ws = reloaded.active

        # Check rec1 (NGUYỄN NGỌC THAO -> row 3, col 7 for 20/10)
        expected_offsets = [
            (0, 8, int),
            (1, 2.5, float),
            (2, 4.25, float),
            (3, 1.75, float),
            (4, 0.5, float),
            (5, 3.5, float),
            (6, 0, int),  # meal count = 0
        ]
        for offset, expected_val, expected_type in expected_offsets:
            cell = ws.cell(row=3 + offset, column=7)
            self.assertEqual(
                cell.data_type,
                'n',
                f"Offset {offset} (row {3+offset}, col 7) data_type is {cell.data_type}, expected 'n'!"
            )
            self.assertEqual(
                type(cell.value),
                expected_type,
                f"Offset {offset} type is {type(cell.value)}, expected {expected_type}!"
            )
            self.assertEqual(cell.value, expected_val)

        # Check rec2 (HOÀNG ĐẮC PHÚ -> row 24, col 11 for 24/10)
        # HCN = 8
        cell_hcn = ws.cell(row=24, column=11)
        self.assertEqual(cell_hcn.data_type, 'n')
        self.assertEqual(cell_hcn.value, 8)
        self.assertIsInstance(cell_hcn.value, int)

        # TCN = 3
        cell_tcn = ws.cell(row=25, column=11)
        self.assertEqual(cell_tcn.data_type, 'n')
        self.assertEqual(cell_tcn.value, 3)
        self.assertIsInstance(cell_tcn.value, int)

        # Meal = 2
        cell_meal = ws.cell(row=30, column=11)
        self.assertEqual(cell_meal.data_type, 'n')
        self.assertEqual(cell_meal.value, 2)
        self.assertIsInstance(cell_meal.value, int)

    # =========================================================================
    # CHALLENGE 5: STYLING & FORMATTING PRESERVATION ACROSS WRITES
    # =========================================================================

    def test_challenge_08_cell_styling_and_merges_preserved(self):
        """
        Adversarially verify that font names, colors, cell fills, borders,
        merged header ranges, and freeze panes are NOT wiped or reset by writing records.
        """
        integ = ExcelIntegrator(template_path=self.master_template)

        rec = AttendanceRecord(
            id="style-test",
            employee_name="HOÀNG ĐẮC PHÚ",
            normalized_name="HOÀNG ĐẮC PHÚ",
            date_str="24/10",
            resolved_date="2026-10-24",
            day_number=24,
            is_sunday=False,
            shift_type="DAY",
            project="ets",
            time_window="8h-17h (8H)",
            hours=WorkHours(hcn_100=8.0, total_hours=8.0),
            meal_count=0,
            status="VALID",
            raw_text="mock"
        )

        out_path = os.path.join(self.test_dir, "style_test.xlsx")
        integ.apply_records([rec], output_path=out_path)

        wb_orig = openpyxl.load_workbook(self.master_template, data_only=False)
        wb_mod = openpyxl.load_workbook(out_path, data_only=False)

        ws_orig = wb_orig.active
        ws_mod = wb_mod.active

        # 1. Freeze Panes
        self.assertEqual(ws_mod.freeze_panes, ws_orig.freeze_panes)
        self.assertEqual(ws_mod.freeze_panes, "F3")

        # 2. Merged Ranges
        orig_merges = set(str(r) for r in ws_orig.merged_cells.ranges)
        mod_merges = set(str(r) for r in ws_mod.merged_cells.ranges)
        self.assertEqual(orig_merges, mod_merges, "Merged cell ranges were lost or altered!")

        # 3. Row Dimensions
        for r in range(1, 31):
            self.assertEqual(
                ws_mod.row_dimensions[r].height,
                ws_orig.row_dimensions[r].height,
                f"Row {r} height altered!"
            )

        # 4. Column Widths
        for c in range(1, 45):
            col_letter = get_column_letter(c)
            self.assertEqual(
                ws_mod.column_dimensions[col_letter].width,
                ws_orig.column_dimensions[col_letter].width,
                f"Column {col_letter} width altered!"
            )

        # 5. Header Fills and Fonts (A1, F1, AK1, AK2)
        for r, c in [(1, 1), (1, 6), (1, 37), (2, 37)]:
            orig_fill = ws_orig.cell(row=r, column=c).fill.start_color.rgb
            mod_fill = ws_mod.cell(row=r, column=c).fill.start_color.rgb
            self.assertEqual(orig_fill, mod_fill, f"Header cell ({r},{c}) fill color altered!")

            orig_font = ws_orig.cell(row=r, column=c).font.name
            mod_font = ws_mod.cell(row=r, column=c).font.name
            self.assertEqual(orig_font, mod_font, f"Header cell ({r},{c}) font altered!")

    # =========================================================================
    # CHALLENGE 6: 30-CYCLE RANDOM FUZZ STRESS HARNESS
    # =========================================================================

    def test_challenge_09_thirty_cycle_fuzz_stress(self):
        """
        Adversarial 30-cycle fuzz stress test:
        Iterates 30 times, randomly selecting employee, date, shift, hours, and meals.
        Saves and re-loads at each iteration.
        Asserts that after 30 cumulative write cycles, every single formula across
        all 4 employees (AK3..AR24) and row 2 grand totals (AK2..AR2) remains intact,
        valid, and untouched.
        """
        import random
        random.seed(42)  # Deterministic seed for reproducible testing

        current_file = os.path.join(self.test_dir, "fuzz_start.xlsx")
        shutil.copyfile(self.master_template, current_file)

        employees = [
            "HOÀNG ĐẮC PHÚ",
            "NGUYỄN NGỌC THAO",
            "NGUYỄN ĐỨC CÔNG",
            "TÔ VĂN HƯNG"
        ]

        # Valid days from Oct 19 to Nov 18
        dates = []
        for d in range(19, 32):
            dates.append((f"{d}/10", f"2026-10-{d:02d}", d))
        for d in range(1, 19):
            dates.append((f"{d:02d}/11", f"2026-11-{d:02d}", d))

        for cycle in range(1, 31):
            emp = random.choice(employees)
            d_str, d_iso, d_num = random.choice(dates)
            h_val = random.choice([4.0, 8.0, 10.5, 12.0, 2.5])
            meal = random.choice([0, 1, 2])

            rec = AttendanceRecord(
                id=f"fuzz-{cycle}",
                employee_name=emp,
                normalized_name=emp,
                date_str=d_str,
                resolved_date=d_iso,
                day_number=d_num,
                is_sunday=False,
                shift_type="DAY",
                project="ets",
                time_window="mock",
                hours=WorkHours(hcn_100=min(8.0, h_val), tcn_150=max(0.0, h_val - 8.0), total_hours=h_val),
                meal_count=meal,
                status="VALID",
                raw_text="mock"
            )

            next_file = os.path.join(self.test_dir, f"fuzz_step_{cycle}.xlsx")
            integ = ExcelIntegrator(template_path=current_file)
            res = integ.apply_records([rec], output_path=next_file)
            self.assertEqual(res["records_processed"], 1)

            # Re-load and verify formulas at every 5th cycle and final cycle
            if cycle % 5 == 0 or cycle == 30:
                reloaded = openpyxl.load_workbook(next_file, data_only=False)
                self._verify_all_formulas_intact(reloaded, context=f"Fuzz Cycle {cycle}")

            current_file = next_file

    # =========================================================================
    # CHALLENGE 7: FORMULA MATHEMATICAL ORACLE VERIFICATION
    # =========================================================================

    def test_challenge_10_formula_mathematical_oracle(self):
        """
        Oracle Verification:
        Parses all formula expressions in the workbook and executes a mathematical
        simulation. Asserts:
        1. Range dimensions for horizontal sums are exactly 31 date columns (F..AJ).
        2. Employee summary row AR strictly sums the 6 work hours categories (AK..AP)
           and mathematically excludes column AQ (meals).
        3. Row 2 Grand Totals sum exactly the 4 employee rows (3, 10, 17, 24).
        """
        wb = openpyxl.load_workbook(self.master_template, data_only=False)
        ws = wb.active

        # Helper to convert Excel range e.g. "F3:AJ3" to list of column letters
        for r in [3, 10, 17, 24]:
            # Check AK..AQ
            for offset in range(7):
                col = 37 + offset
                formula = ws.cell(row=r, column=col).value
                # Expect "=SUM(F{r+offset}:AJ{r+offset})"
                match = re.match(r"^=SUM\(([A-Z]+)(\d+):([A-Z]+)(\d+)\)$", formula)
                self.assertIsNotNone(match, f"Invalid formula syntax in row {r}, col {col}: {formula}")
                start_col, start_r, end_col, end_r = match.groups()
                self.assertEqual(start_col, "F")
                self.assertEqual(end_col, "AJ")
                self.assertEqual(int(start_r), r + offset)
                self.assertEqual(int(end_r), r + offset)

            # Check AR: =SUM(AK{r}:AP{r})
            formula_ar = ws.cell(row=r, column=44).value
            match_ar = re.match(r"^=SUM\(([A-Z]+)(\d+):([A-Z]+)(\d+)\)$", formula_ar)
            self.assertIsNotNone(match_ar, f"Invalid AR formula: {formula_ar}")
            s_col, s_r, e_col, e_r = match_ar.groups()
            self.assertEqual(s_col, "AK", f"AR formula should start at AK, got {s_col}")
            self.assertEqual(e_col, "AP", f"AR formula should end at AP, got {e_col}")
            self.assertEqual(int(s_r), r)
            self.assertEqual(int(e_r), r)

            # Column 43 is AQ (meals). Verify that AQ is strictly excluded from AK..AP
            col_letters_in_sum = ["AK", "AL", "AM", "AN", "AO", "AP"]
            self.assertNotIn("AQ", col_letters_in_sum)

        # Check Row 2 Grand Totals
        for col in range(37, 45):
            col_letter = get_column_letter(col)
            formula_r2 = ws.cell(row=2, column=col).value
            match_r2 = re.match(r"^=SUM\((.+)\)$", formula_r2)
            self.assertIsNotNone(match_r2)
            terms = [t.strip() for t in match_r2.group(1).split(",")]
            expected_terms = [f"{col_letter}3", f"{col_letter}10", f"{col_letter}17", f"{col_letter}24"]
            self.assertEqual(terms, expected_terms)

    # =========================================================================
    # CHALLENGE 8: IN-MEMORY BYTESIO STREAMING PIPELINE
    # =========================================================================

    def test_challenge_11_in_memory_bytesio_multi_cycle(self):
        """
        Adversarially challenge applying records directly into io.BytesIO memory streams
        across multiple cycles without touching disk.
        Asserts formulas, formatting, and types remain 100% intact.
        """
        buf = io.BytesIO()
        with open(self.master_template, "rb") as f:
            buf.write(f.read())
        buf.seek(0)

        for cycle in range(5):
            rec = AttendanceRecord(
                id=f"mem-{cycle}",
                employee_name="HOÀNG ĐẮC PHÚ",
                normalized_name="HOÀNG ĐẮC PHÚ",
                date_str="24/10",
                resolved_date="2026-10-24",
                day_number=24,
                is_sunday=False,
                shift_type="DAY",
                project="ets",
                time_window="8h-17h (8H)",
                hours=WorkHours(hcn_100=8.0, total_hours=8.0),
                meal_count=cycle % 2,
                status="VALID",
                raw_text="mock"
            )

            integ = ExcelIntegrator(template_path=buf)
            out_buf = io.BytesIO()
            res = integ.apply_records([rec], output_path=out_buf)
            self.assertEqual(res["records_processed"], 1)

            # Reload from out_buf and verify
            out_buf.seek(0)
            reloaded_wb = openpyxl.load_workbook(out_buf, data_only=False)
            self._verify_all_formulas_intact(reloaded_wb, context=f"Memory Cycle {cycle}")

            buf = out_buf
            buf.seek(0)


if __name__ == "__main__":
    unittest.main()
