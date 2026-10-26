"""
Excel Integrator Engine (Requirement R3).
Loads Excel template with data_only=False, performs 3-tier fuzzy employee matching,
resolves multi-format date columns, writes numeric attendance values to 7-row blocks,
preserves formulas and styling, and sets fullCalcOnLoad.
"""
import os
import io
import re
import datetime
import unicodedata
from difflib import SequenceMatcher
from typing import List, Dict, Any, Optional, Tuple, Union

import openpyxl
from openpyxl.utils import get_column_letter

from models.attendance import AttendanceRecord, WorkHours
from core.template_generator import generate_default_template, DEFAULT_TEMPLATE_PATH


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DEFAULT_OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")


def strip_accents(text: str) -> str:
    """Strips Vietnamese accents and decomposes diacritics (e.g. 'Đ' -> 'D', 'á' -> 'a')."""
    if not text:
        return ""
    text = text.replace('đ', 'd').replace('Đ', 'D')
    nfkd = unicodedata.normalize('NFKD', text)
    return ''.join(c for c in nfkd if not unicodedata.combining(c))


def normalize_name_key(text: str) -> str:
    """Normalizes whitespace and Unicode NFC representation."""
    if not text:
        return ""
    clean = re.sub(r'\s+', ' ', unicodedata.normalize('NFC', text)).strip()
    return clean


def clean_employee_name_for_matching(text: str) -> str:
    """
    Cleans an employee name prior to matching:
    - Strips parenthetical / bracketed annotations (e.g. (KTV), [thợ hàn], (Tổ 1), (Cơ điện)).
    - Strips phone numbers (e.g. 0912345678, +84912345678, - 0912345678).
    - Strips trailing role/department notes following dashes or colons (e.g. '- KTV', '- Thợ hàn').
    - Normalizes Unicode NFC and collapses whitespace.
    """
    if not text:
        return ""

    t = unicodedata.normalize('NFC', text)
    # Strip parenthetical annotations: (KTV), [thợ hàn], {Tổ 1}, etc.
    t = re.sub(r'[\(\[\{].*?[\)\]\}]', ' ', t)
    # Strip phone numbers: 8-11 digits starting with 0 or +84 / 84, with optional preceding hyphen/dash
    t = re.sub(r'[-–—]?\s*(?:\+?84|0)(?:[\s\.\-]?\d){8,10}\b', ' ', t)
    # Strip trailing role notes after hyphen/dash/slash/pipe/colon (e.g. ' - KTV', ' - thợ hàn')
    t = re.sub(r'[-–—/|:]\s*[^\d\W].*$', ' ', t)
    # Strip trailing punctuation/dashes
    t = re.sub(r'[-–—:]+\s*$', ' ', t)
    # Normalize whitespace
    return normalize_name_key(t)


class ExcelIntegrator:
    """
    Integrator engine for reading from and writing to Excel attendance workbooks.
    Preserves all formulas, merged headers, formatting, and calculation settings.
    """

    def __init__(self, template_path: Optional[Union[str, io.BytesIO, openpyxl.Workbook]] = None):
        """
        Initializes the ExcelIntegrator.
        If template_path is None, defaults to templates_excel/BẢNG CHẤM CÔNG WEVN - ETS.xlsx.
        Generates the default template if it does not yet exist.
        """
        self.template_source = template_path
        self.template_path: Optional[str] = None
        self.wb: openpyxl.Workbook
        self.ws: openpyxl.worksheet.worksheet.Worksheet
        self.employees: List[Dict[str, Any]] = []
        self.date_columns: Dict[str, Any] = {}
        self.date_list: List[Dict[str, Any]] = []
        self.min_date_iso: str = ""
        self.max_date_iso: str = ""

        self._load_workbook()
        self._index_sheet()

    def _load_workbook(self):
        """Loads the workbook with data_only=False to preserve formula syntax."""
        if isinstance(self.template_source, openpyxl.Workbook):
            self.wb = self.template_source
            self.template_path = None
        elif isinstance(self.template_source, io.BytesIO):
            self.template_source.seek(0)
            self.wb = openpyxl.load_workbook(self.template_source, data_only=False)
            self.template_path = None
        else:
            path = self.template_source or DEFAULT_TEMPLATE_PATH
            if not os.path.exists(path):
                # Auto-generate default template if missing
                generate_default_template(output_path=path)
            self.template_path = os.path.abspath(path)
            self.wb = openpyxl.load_workbook(self.template_path, data_only=False)

        self.ws = self.wb.active
        self.wb.calculation.fullCalcOnLoad = True

    def reload(self):
        """Reloads the workbook from the original template path, discarding unsaved memory edits."""
        self._load_workbook()
        self._index_sheet()

    def _index_sheet(self):
        """Discovers employee blocks and date columns in the worksheet dynamically."""
        self.employees.clear()
        self.date_columns.clear()
        self.date_list.clear()

        max_row = min(self.ws.max_row, 2000)
        max_col = min(self.ws.max_column, 100)

        # 1. Detect Header Row, Name Column, and Công Column
        header_row = 1
        name_col = 3
        cong_col = 5
        date_header_row = 1

        name_keywords = ["họ và tên", "họ tên", "ho va ten", "ho ten", "họ_tên", "nhân viên", "nhan vien"]
        cong_keywords = ["công", "loại công", "cong", "chỉ tiêu", "dien giai"]

        found_header = False
        for r in range(1, min(max_row + 1, 20)):
            for c in range(1, min(max_col + 1, 10)):
                cell_val = str(self.ws.cell(row=r, column=c).value or "").strip().lower()
                if any(kw in cell_val for kw in name_keywords):
                    header_row = r
                    name_col = c
                    found_header = True
                    break
            if found_header:
                break

        # Look for cong_col in header_row or header_row + 1
        for r in [header_row, header_row + 1]:
            for c in range(name_col + 1, min(max_col + 1, name_col + 6)):
                cell_val = str(self.ws.cell(row=r, column=c).value or "").strip().lower()
                if any(kw in cell_val for kw in cong_keywords):
                    cong_col = c
                    break

        # 2. Find Date Header Row (look in rows around header_row)
        best_date_count = 0
        best_date_row = header_row

        for test_r in range(max(1, header_row - 2), min(max_row + 1, header_row + 3)):
            d_count = 0
            for c in range(max(name_col, cong_col) + 1, max_col + 1):
                val = self.ws.cell(row=test_r, column=c).value
                if val is not None and str(val).strip():
                    if isinstance(val, (datetime.date, datetime.datetime)):
                        d_count += 1
                    elif re.search(r'\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}', str(val)):
                        d_count += 1
                    elif re.match(r'^\s*([1-9]|[12]\d|3[01])\s*$', str(val)):
                        d_count += 1
            if d_count > best_date_count:
                best_date_count = d_count
                best_date_row = test_r

        date_header_row = best_date_row

        # Index Date Columns
        current_year = datetime.datetime.now().year
        current_month = datetime.datetime.now().month

        for col_idx in range(max(name_col, cong_col) + 1, max_col + 1):
            val = self.ws.cell(row=date_header_row, column=col_idx).value
            if val is None or val == "":
                continue

            parsed_date: Optional[Tuple[int, int, int]] = None  # (year, month, day)
            raw_str = str(val).strip()

            if isinstance(val, (datetime.date, datetime.datetime)):
                parsed_date = (val.year, val.month, val.day)
                raw_str = val.strftime("%Y-%m-%d")
            else:
                m_iso = re.search(r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})', raw_str)
                if m_iso:
                    parsed_date = (int(m_iso.group(1)), int(m_iso.group(2)), int(m_iso.group(3)))
                else:
                    m_dmy = re.search(r'(\d{1,2})[-/](\d{1,2})[-/](\d{4})', raw_str)
                    if m_dmy:
                        parsed_date = (int(m_dmy.group(3)), int(m_dmy.group(2)), int(m_dmy.group(1)))
                    else:
                        m_dm = re.search(r'(\d{1,2})[-/](\d{1,2})', raw_str)
                        if m_dm:
                            parsed_date = (current_year, int(m_dm.group(2)), int(m_dm.group(1)))
                        else:
                            m_pure_day = re.match(r'^\s*([1-9]|[12]\d|3[01])\s*$', raw_str)
                            if m_pure_day:
                                day_int = int(m_pure_day.group(1))
                                parsed_date = (current_year, current_month, day_int)

            if parsed_date:
                year, month, day = parsed_date
                iso_str = f"{year:04d}-{month:02d}-{day:02d}"
                entry = {
                    "col": col_idx,
                    "year": year,
                    "month": month,
                    "day": day,
                    "iso": iso_str,
                    "raw": raw_str,
                }
                self.date_list.append(entry)

        if self.date_list:
            self.min_date_iso = self.date_list[0]["iso"]
            self.max_date_iso = self.date_list[-1]["iso"]

        # 3. Index Employee Blocks & Map Their Category Rows
        ignore_names = [
            "tổng", "tong", "cộng", "cong", "hc ngày", "hc đêm", "tổng công",
            "trợ cấp", "bên cung ứng", "bên nhận", "kèm theo", "giám đốc", "chữ ký",
            "mst", "địa chỉ", "bảng chấm công", "tháng", "ngày", "stt", "họ và tên"
        ]

        r = date_header_row + 1
        # Skip sub-header row (e.g. T2, T3, T4...)
        if r <= max_row:
            sample_sub = str(self.ws.cell(row=r, column=self.date_list[0]["col"] if self.date_list else name_col + 1).value or "").strip().lower()
            if sample_sub in ["t2", "t3", "t4", "t5", "t6", "t7", "cn"]:
                r += 1

        while r <= max_row:
            name_cell = self.ws.cell(row=r, column=name_col).value
            if name_cell is not None and str(name_cell).strip():
                raw_name = str(name_cell).strip()
                clean_name = normalize_name_key(raw_name)
                clean_lower = clean_name.lower()

                # Skip header/summary/footer rows
                if any(ign == clean_lower or clean_lower.startswith(ign + " ") or clean_lower.startswith(ign + ":") for ign in ignore_names):
                    r += 1
                    continue

                matching_clean = clean_employee_name_for_matching(clean_name)
                stt = self.ws.cell(row=r, column=1).value if name_col > 1 else None
                mnv = self.ws.cell(row=r, column=2).value if name_col > 2 else None

                # Detect category rows for this employee
                category_rows: Dict[str, int] = {}

                # Look forward up to 15 rows for this employee
                block_limit = min(r + 15, max_row + 1)
                for sub_r in range(r, block_limit):
                    if sub_r > r:
                        next_name = self.ws.cell(row=sub_r, column=name_col).value
                        if next_name is not None and str(next_name).strip():
                            # Next employee begins!
                            break

                    cong_val = str(self.ws.cell(row=sub_r, column=cong_col).value or "").strip().lower()
                    if not cong_val:
                        continue

                    if "hành chính ngày" in cong_val or "hcn" in cong_val or "hc ngày" in cong_val:
                        category_rows["HCN"] = sub_r
                    elif "tăng ca ngày" in cong_val or "tcn" in cong_val or "tc ngày" in cong_val:
                        category_rows["TCN"] = sub_r
                    elif "hành chính đêm" in cong_val or "hcđ" in cong_val or "hcd" in cong_val or "hc đêm" in cong_val:
                        category_rows["HCD"] = sub_r
                    elif "tăng ca đêm" in cong_val or "tcđ" in cong_val or "tcd" in cong_val or "tc đêm" in cong_val:
                        category_rows["TCD"] = sub_r
                    elif "ngày cn" in cong_val or "chủ nhật" in cong_val:
                        category_rows["SUN_DAY"] = sub_r
                    elif "đêm cn" in cong_val:
                        category_rows["SUN_NIGHT"] = sub_r
                    elif "ăn" in cong_val or "suất ăn" in cong_val or "suat an" in cong_val:
                        category_rows["MEAL"] = sub_r

                # Default fallback if 7 rows ETS pattern
                if not category_rows:
                    category_rows = {
                        "HCN": r,
                        "TCN": r + 1,
                        "HCD": r + 2,
                        "TCD": r + 3,
                        "SUN_DAY": r + 4,
                        "SUN_NIGHT": r + 5,
                        "MEAL": r + 6,
                    }

                emp_entry = {
                    "row": r,
                    "category_rows": category_rows,
                    "raw_name": raw_name,
                    "clean_name": clean_name,
                    "name_lower": clean_name.lower(),
                    "unaccented": strip_accents(clean_name).lower(),
                    "clean_unaccented": strip_accents(matching_clean).lower(),
                    "stt": stt,
                    "mnv": mnv,
                }
                self.employees.append(emp_entry)

                # Jump ahead by length of detected block
                jump = max(len(category_rows), 7)
                r += jump
            else:
                r += 1

    def match_employee(self, name: str) -> Tuple[Optional[int], str, float]:
        """
        Multi-Tier Employee Matcher supporting role annotations, phone numbers,
        token containment / word-boundary substrings, and fuzzy SequenceMatcher.
        
        Tiers:
        - Input validation: returns (None, "", 0.0) if empty or contains no letters.
        - Tier 1: Exact normalized match (raw target score 1.0, cleaned target score 0.95)
        - Tier 2: Unaccented match (raw target score 0.95, cleaned target score 0.92)
        - Tier 3: Token containment / word-boundary substring match -> score 0.90
        - Tier 4: Difflib SequenceMatcher similarity ratio >= 0.85 -> score ratio
        
        Returns (start_row, matched_clean_name, score).
        If unmatched, returns (None, "", 0.0).
        """
        if not name or not str(name).strip():
            return None, "", 0.0

        raw_clean = normalize_name_key(name)
        if not any(c.isalpha() for c in raw_clean):
            return None, "", 0.0

        cleaned = clean_employee_name_for_matching(raw_clean)

        raw_lower = raw_clean.lower()
        raw_unacc = strip_accents(raw_clean).lower()

        clean_lower = cleaned.lower() if cleaned else ""
        clean_unacc = strip_accents(cleaned).lower() if cleaned else ""

        # Tier 1A: Exact normalized match on raw target
        for emp in self.employees:
            if raw_lower == emp["name_lower"]:
                return emp["row"], emp["clean_name"], 1.0

        # Tier 1B: Exact normalized match on cleaned target
        if clean_lower:
            for emp in self.employees:
                if clean_lower == emp["name_lower"]:
                    return emp["row"], emp["clean_name"], 0.95

        # Tier 2A: Unaccented match on raw target
        for emp in self.employees:
            if raw_unacc == emp["unaccented"] or raw_unacc == emp.get("clean_unaccented"):
                return emp["row"], emp["clean_name"], 0.95

        # Tier 2B: Unaccented match on cleaned target
        if clean_unacc:
            for emp in self.employees:
                if clean_unacc == emp["unaccented"] or clean_unacc == emp.get("clean_unaccented"):
                    return emp["row"], emp["clean_name"], 0.92

        # Tier 3: Token containment / word-boundary substring match
        target_texts_unacc = [t for t in (clean_unacc, raw_unacc) if t]

        # Case A: Full employee unaccented name is contained as a word-boundary substring in query
        best_contain_emp = None
        best_contain_len = 0
        for emp in self.employees:
            emp_u = emp["unaccented"]
            pattern = rf'(?<!\w){re.escape(emp_u)}(?!\w)'
            for tgt in target_texts_unacc:
                if re.search(pattern, tgt):
                    if len(emp_u) > best_contain_len:
                        best_contain_len = len(emp_u)
                        best_contain_emp = emp
                    break

        if best_contain_emp:
            return best_contain_emp["row"], best_contain_emp["clean_name"], 0.90

        # Case B: Vice-versa: Query (at least 2 words) is contained as word-boundary substring in employee name
        for tgt in target_texts_unacc:
            tgt_words = tgt.split()
            if len(tgt_words) >= 2 and len(tgt) >= 5:
                pattern = rf'(?<!\w){re.escape(tgt)}(?!\w)'
                matching_emps = [emp for emp in self.employees if re.search(pattern, emp["unaccented"])]
                if len(matching_emps) == 1:
                    matched_emp = matching_emps[0]
                    return matched_emp["row"], matched_emp["clean_name"], 0.90

        # Tier 4: Fuzzy sequence matching (>= 0.85)
        best_emp = None
        best_score = 0.0
        for emp in self.employees:
            emp_u = emp["unaccented"]
            score_raw = SequenceMatcher(None, raw_unacc, emp_u).ratio()
            score_clean = SequenceMatcher(None, clean_unacc, emp_u).ratio() if clean_unacc else 0.0
            score = max(score_raw, score_clean)
            if score > best_score:
                best_score = score
                best_emp = emp

        if best_emp and best_score >= 0.85:
            return best_emp["row"], best_emp["clean_name"], round(best_score, 2)

        return None, "", 0.0

    def resolve_employee_row(self, name: str) -> Optional[int]:
        """Convenience method returning the 1-based start row index, or None if unmatched."""
        row, _, _ = self.match_employee(name)
        return row

    def resolve_date_column(self, date_input: Union[str, int, datetime.date, datetime.datetime]) -> Optional[int]:
        """
        Resolves 1-based column index from various date formats:
        - ISO YYYY-MM-DD (e.g. '2026-10-24')
        - DD/MM or DD-MM (e.g. '24/10', '24-10')
        - DD/MM/YYYY or DD-MM-YYYY (e.g. '24/10/2026')
        - Day number integer or string (e.g. 24, '24')
        - Native datetime.date or datetime.datetime
        
        Returns 1-based column index (e.g. 11 for 2026-10-24 / 24/10), or None if out of range.
        """
        if date_input is None:
            return None

        target_day: Optional[int] = None
        target_month: Optional[int] = None
        target_year: Optional[int] = None

        if isinstance(date_input, (datetime.date, datetime.datetime)):
            target_year = date_input.year
            target_month = date_input.month
            target_day = date_input.day
        elif isinstance(date_input, int):
            if 1 <= date_input <= 31:
                target_day = date_input
            else:
                return None
        else:
            s = str(date_input).strip()
            if not s:
                return None

            # 1. ISO format: YYYY-MM-DD or YYYY/MM/DD
            m_iso = re.search(r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})', s)
            if m_iso:
                target_year = int(m_iso.group(1))
                target_month = int(m_iso.group(2))
                target_day = int(m_iso.group(3))
            else:
                # 2. DD/MM/YYYY or DD-MM-YYYY
                m_dmy = re.search(r'(\d{1,2})[-/](\d{1,2})[-/](\d{4})', s)
                if m_dmy:
                    target_day = int(m_dmy.group(1))
                    target_month = int(m_dmy.group(2))
                    target_year = int(m_dmy.group(3))
                else:
                    # 3. DD/MM or DD-MM
                    m_dm = re.search(r'(\d{1,2})[-/](\d{1,2})', s)
                    if m_dm:
                        target_day = int(m_dm.group(1))
                        target_month = int(m_dm.group(2))
                    else:
                        # 4. Pure day number e.g. "24"
                        m_day = re.match(r'^\s*(\d{1,2})\s*$', s)
                        if m_day:
                            target_day = int(m_day.group(1))
                        else:
                            return None

        if target_day is None:
            return None

        # Compare against indexed columns
        for entry in self.date_list:
            if target_month is not None:
                if entry["day"] == target_day and entry["month"] == target_month:
                    if target_year is not None:
                        if entry["year"] == target_year:
                            return entry["col"]
                    else:
                        return entry["col"]
            else:
                # Only day number provided: match unique day in range
                if entry["day"] == target_day:
                    return entry["col"]

        return None

    def apply_records(
        self,
        records: List[AttendanceRecord],
        output_path: Optional[Union[str, io.BytesIO]] = None
    ) -> Dict[str, Any]:
        """
        Applies a list of AttendanceRecords to the openpyxl workbook.
        
        Row offsets:
        - Offset 0: HCN 100% (rec.hours.hcn_100)
        - Offset 1: TCN 150% (rec.hours.tcn_150)
        - Offset 2: HCĐ 130% (rec.hours.hcd_130)
        - Offset 3: TCĐ 195% (rec.hours.tcd_195)
        - Offset 4: Ngày CN 200% (rec.hours.sunday_day_200)
        - Offset 5: Đêm CN 260% (rec.hours.sunday_night_260)
        - Offset 6: Suất ăn (rec.meal_count)
        
        Preserves all formulas in AK..AR and row 2.
        Values written are strictly numeric types (int or float).
        Sets fullCalcOnLoad = True.
        Saves workbook to output_path or output/ directory.
        
        Returns summary statistics dictionary.
        """
        records_processed = 0
        cells_written = 0
        employees_matched: set = set()
        unmatched_records: List[AttendanceRecord] = []
        errors: List[str] = []

        for rec in records:
            records_processed += 1
            if getattr(rec, "status", "") == "ERROR":
                err_msg = f"Skipping error record: {rec.employee_name} ({getattr(rec, 'messages', [])})"
                errors.append(err_msg)
                continue

            # Match employee
            emp_name = getattr(rec, "normalized_name", None) or getattr(rec, "employee_name", "")
            r_start, matched_name, score = self.match_employee(emp_name)
            if not r_start:
                unmatched_records.append(rec)
                errors.append(f"Unmatched employee: {emp_name}")
                continue

            # Resolve date column
            date_val = getattr(rec, "date_str", None) or getattr(rec, "resolved_date", None)
            col_date = self.resolve_date_column(date_val)
            if not col_date:
                errors.append(f"Date out of range: {date_val} for {emp_name}")
                continue

            # Write hours and meals to mapped category rows
            h: WorkHours = rec.hours

            # Find matching employee dict to retrieve specific category rows
            emp_dict = next((e for e in self.employees if e["clean_name"] == matched_name), None)
            cat_rows = emp_dict.get("category_rows", {}) if emp_dict else {}

            def _get_target_row(cat_key: str, default_offset: int) -> int:
                return cat_rows.get(cat_key, r_start + default_offset)

            # Helper for numeric write
            def _write_num(row_idx: int, val: float):
                nonlocal cells_written
                num_val = int(val) if float(val).is_integer() else float(val)
                cell = self.ws.cell(row=row_idx, column=col_date)
                cell.value = num_val
                cells_written += 1

            if h.hcn_100 > 0:
                _write_num(_get_target_row("HCN", 0), h.hcn_100)
            if h.tcn_150 > 0:
                _write_num(_get_target_row("TCN", 1), h.tcn_150)
            if h.hcd_130 > 0:
                _write_num(_get_target_row("HCD", 2), h.hcd_130)
            if h.tcd_195 > 0:
                _write_num(_get_target_row("TCD", 3), h.tcd_195)
            if h.sunday_day_200 > 0:
                _write_num(_get_target_row("SUN_DAY", 4), h.sunday_day_200)
            if h.sunday_night_260 > 0:
                _write_num(_get_target_row("SUN_NIGHT", 5), h.sunday_night_260)

            # Meal count (Suất ăn)
            if rec.meal_count is not None:
                _write_num(_get_target_row("MEAL", 6), rec.meal_count)

            employees_matched.add(matched_name)

        # Force Excel full calculation tree rebuild
        self.wb.calculation.fullCalcOnLoad = True

        # Save workbook
        save_target = output_path
        if save_target is None:
            save_target = os.path.join(DEFAULT_OUTPUT_DIR, "BẢNG CHẤM CÔNG WEVN - ETS.xlsx")

        if isinstance(save_target, io.BytesIO):
            self.wb.save(save_target)
            save_target.seek(0)
            final_path_str = "memory_buffer"
        else:
            final_path_str = os.path.abspath(str(save_target))
            os.makedirs(os.path.dirname(final_path_str), exist_ok=True)
            self.wb.save(final_path_str)

        return {
            "records_processed": records_processed,
            "total_records": records_processed,
            "cells_written": cells_written,
            "updated_cells": cells_written,
            "employees_matched": len(employees_matched),
            "employees_count": len(employees_matched),
            "unmatched_records": len(unmatched_records),
            "unmatched_list": [r.employee_name for r in unmatched_records],
            "errors": errors,
            "output_path": final_path_str,
        }

    def get_template_info(self) -> Dict[str, Any]:
        """
        Returns template metadata for Web API / UI:
        - sheet_name: Active worksheet title
        - employees: List of cleaned employee names
        - date_range: [start_date_iso, end_date_iso]
        """
        return {
            "sheet_name": self.ws.title,
            "employees": [e["clean_name"] for e in self.employees],
            "date_range": [self.min_date_iso, self.max_date_iso],
        }
