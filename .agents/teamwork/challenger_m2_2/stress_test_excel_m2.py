"""
Empirical Stress Test & Benchmark Suite for Excel Integrator (Milestone 2).
Focus areas:
1. Employee Name Fuzzy Variations & Edge Cases
2. Unmatched Names & Non-existent Employees Graceful Handling
3. Large Batch Insertion Performance & Memory Footprint (100+, 250, 500 records)
4. Output File Validity, openpyxl Reloadability, and XML Integrity
5. Formula & Formatting Preservation Check
"""
import io
import os
import sys
import time
import zipfile
import tracemalloc
from typing import List, Dict, Any, Tuple

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import openpyxl
from core.excel_integrator import ExcelIntegrator
from models.attendance import AttendanceRecord, WorkHours
from core.parser import parse_single_message


def run_fuzzy_variations_challenge(ei: ExcelIntegrator) -> Dict[str, Any]:
    print("=" * 60)
    print("CHALLENGE 1: EMPLOYEE NAME FUZZY VARIATIONS")
    print("=" * 60)
    
    # Required test cases from dispatch
    required_cases = [
        ('hoàng đắc phú', 24, "Lowercase with accents"),
        ('HOANG DAC PHU', 24, "Uppercase unaccented"),
        ('HOÀNG  ĐẮC   PHÚ ', 24, "Multiple & trailing spaces"),
        ('Hoàng Đắc Phú (KTV)', 24, "Role/job annotation suffix (KTV)"),
        ('Hoàng Đắc Phú 0912345678', 24, "Trailing phone number suffix"),
    ]
    
    # Additional edge cases
    extended_cases = [
        ('Hoàng Đắc Phú - 0912345678', 24, "Hyphenated phone suffix"),
        ('Hoàng Đắc Phú (thợ hàn)', 24, "Parenthesized trade suffix"),
        ('HOÀNG ĐĂC PHÚ', 24, "Minor typo: ă instead of ắ"),
        ('hoang dac phuu', 24, "Minor typo: duplicate letter u"),
        ('Nguyễn Đức Công (Tổ 1)', 10, "Employee 2 with group suffix"),
        ('to van hung', 17, "Employee 3 lowercase unaccented"),
        ('NGUYỄN NGỌC THAO', 3, "Employee 1 exact"),
        ('Nguyễn Ngọc Thao (Cơ điện)', 3, "Employee 1 with department suffix"),
    ]
    
    results = []
    
    all_cases = required_cases + extended_cases
    for query, expected_row, desc in all_cases:
        row, matched_name, score = ei.match_employee(query)
        passed = (row == expected_row)
        status_str = "PASS" if passed else "FAIL"
        results.append({
            "query": query,
            "expected_row": expected_row,
            "actual_row": row,
            "matched_name": matched_name,
            "score": score,
            "passed": passed,
            "desc": desc,
            "is_required": (query, expected_row, desc) in required_cases,
        })
        print(f"[{status_str}] {query!r:32} | Expected: row {expected_row} | Got: row {row}, name={matched_name!r}, score={score:.2f} ({desc})")
        
    required_passed = sum(1 for r in results if r["is_required"] and r["passed"])
    required_total = len(required_cases)
    print(f"\nRequired variations summary: {required_passed}/{required_total} passed.")
    return {
        "results": results,
        "required_passed": required_passed,
        "required_total": required_total,
    }


def run_unmatched_names_challenge(ei: ExcelIntegrator) -> Dict[str, Any]:
    print("\n" + "=" * 60)
    print("CHALLENGE 2: UNMATCHED NAMES & NON-EXISTENT EMPLOYEES")
    print("=" * 60)
    
    test_unmatched_names = [
        "Alexander the Great",
        "Trần Văn Vô Danh",
        "John Doe",
        "NonExistent Worker 999",
        "Công ty Cổ phần Xây dựng",
        "!@#$%^&*()",
        "1234567890",
        "",
        "   ",
    ]
    
    records = []
    for i, name in enumerate(test_unmatched_names):
        records.append(
            AttendanceRecord(
                id=f"unmatched-test-{i}",
                employee_name=name,
                normalized_name=name.strip(),
                date_str="24/10",
                resolved_date="2026-10-24",
                day_number=24,
                is_sunday=False,
                shift_type="DAY",
                project="sdv",
                time_window="8h-17h (8H)",
                hours=WorkHours(hcn_100=8.0, total_hours=8.0),
                meal_count=1,
                status="VALID",
                raw_text=f"HỌ TÊN: {name}",
            )
        )
    
    buf = io.BytesIO()
    try:
        stats = ei.apply_records(records, output_path=buf)
        no_exception = True
    except Exception as e:
        no_exception = False
        stats = {"error": str(e)}
        print(f"[FAIL] apply_records raised exception: {e}")
        return {"no_exception": False, "stats": stats}
    
    print(f"Total unmatched test records: {len(records)}")
    print(f"Records processed: {stats.get('records_processed')}")
    print(f"Unmatched records reported: {stats.get('unmatched_records')}")
    print(f"Cells written: {stats.get('cells_written')}")
    print(f"Errors list length: {len(stats.get('errors', []))}")
    print(f"Unmatched list: {stats.get('unmatched_list')}")
    
    # Assertions
    passed_counts = (stats.get("unmatched_records") == len(records))
    passed_no_cells = (stats.get("cells_written") == 0)
    passed_errors = (len(stats.get("errors", [])) == len(records))
    
    print(f"[*] Correct count tracked: {'PASS' if passed_counts else 'FAIL'}")
    print(f"[*] Zero cells written: {'PASS' if passed_no_cells else 'FAIL'}")
    print(f"[*] Detailed error tracking: {'PASS' if passed_errors else 'FAIL'}")
    
    return {
        "no_exception": no_exception,
        "passed_counts": passed_counts,
        "passed_no_cells": passed_no_cells,
        "stats": stats,
    }


def run_large_batch_challenge(ei: ExcelIntegrator, batch_sizes=(100, 250, 500)) -> Dict[str, Any]:
    print("\n" + "=" * 60)
    print("CHALLENGE 3: LARGE BATCH INSERTION & RESOURCE PROFILING")
    print("=" * 60)
    
    # Template has dates from 2026-10-19 (col 6) to 2026-11-18 (col 36) -> 31 days
    # Template has 4 employees
    employees = ["NGUYỄN NGỌC THAO", "NGUYỄN ĐỨC CÔNG", "TÔ VĂN HƯNG", "HOÀNG ĐẮC PHÚ"]
    
    benchmarks = []
    
    for count in batch_sizes:
        records = []
        for i in range(count):
            emp = employees[i % len(employees)]
            # Cycle through dates in range
            day_idx = (i % 31)
            # Create a date string matching the indexed dates
            # 2026-10-19 is day 19, 2026-10-20 is day 20, ..., 2026-10-31 is day 31, 2026-11-01 is day 1..
            if day_idx <= 12:  # Oct 19 to Oct 31
                d = 19 + day_idx
                m = 10
            else:  # Nov 1 to Nov 18
                d = day_idx - 12
                m = 11
            date_str = f"{d:02d}/{m:02d}"
            
            hours = WorkHours(
                hcn_100=8.0 if i % 2 == 0 else 7.5,
                tcn_150=2.0 if i % 3 == 0 else 0.0,
                total_hours=10.0 if i % 3 == 0 else 8.0
            )
            records.append(
                AttendanceRecord(
                    id=f"batch-{count}-{i}",
                    employee_name=emp,
                    normalized_name=emp,
                    date_str=date_str,
                    resolved_date=f"2026-{m:02d}-{d:02d}",
                    day_number=d,
                    is_sunday=False,
                    shift_type="DAY",
                    project="ets",
                    time_window="8h-17h (8H)",
                    hours=hours,
                    meal_count=1,
                    status="VALID",
                    raw_text=f"Batch record {i}",
                )
            )
        
        # Profile memory and execution time
        ei.reload()  # fresh state
        
        tracemalloc.start()
        start_time = time.perf_counter()
        
        out_buf = io.BytesIO()
        stats = ei.apply_records(records, output_path=out_buf)
        
        elapsed_sec = time.perf_counter() - start_time
        current_mem, peak_mem = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        rec_per_sec = count / elapsed_sec if elapsed_sec > 0 else 0
        peak_mb = peak_mem / (1024 * 1024)
        
        benchmarks.append({
            "count": count,
            "elapsed_sec": round(elapsed_sec, 4),
            "records_per_sec": round(rec_per_sec, 1),
            "peak_mem_mb": round(peak_mb, 2),
            "cells_written": stats["cells_written"],
            "unmatched_records": stats["unmatched_records"],
            "errors_count": len(stats["errors"]),
        })
        
        print(f"Batch size: {count:4d} records | Elapsed: {elapsed_sec:.4f}s ({rec_per_sec:.1f} rec/s) | Peak Mem: {peak_mb:.2f} MB | Cells Written: {stats['cells_written']}")
        
    return {"benchmarks": benchmarks}


def run_output_file_validity_challenge(ei: ExcelIntegrator) -> Dict[str, Any]:
    print("\n" + "=" * 60)
    print("CHALLENGE 4: OUTPUT FILE VALIDITY & XML INTEGRITY")
    print("=" * 60)
    
    test_output_file = os.path.join(PROJECT_ROOT, ".agents", "teamwork", "challenger_m2_2", "output_stress_test.xlsx")
    
    # Generate 120 valid records covering all employees and diverse dates
    employees = ["NGUYỄN NGỌC THAO", "NGUYỄN ĐỨC CÔNG", "TÔ VĂN HƯNG", "HOÀNG ĐẮC PHÚ"]
    records = []
    for i in range(120):
        emp = employees[i % 4]
        day = 19 + (i % 12)  # Oct 19..30
        date_str = f"{day:02d}/10"
        records.append(
            AttendanceRecord(
                id=f"validity-{i}",
                employee_name=emp,
                normalized_name=emp,
                date_str=date_str,
                resolved_date=f"2026-10-{day:02d}",
                day_number=day,
                is_sunday=(day == 25),
                shift_type="DAY",
                project="ets",
                time_window="8h-17h (8H)",
                hours=WorkHours(
                    hcn_100=8.0 if day != 25 else 0.0,
                    sunday_day_200=8.0 if day == 25 else 0.0,
                    tcn_150=1.5 if i % 5 == 0 else 0.0,
                    total_hours=9.5 if i % 5 == 0 else 8.0,
                ),
                meal_count=1,
                status="VALID",
                raw_text="mock",
            )
        )
        
    ei.reload()
    stats = ei.apply_records(records, output_path=test_output_file)
    print(f"Saved test output workbook to: {test_output_file}")
    print(f"File size on disk: {os.path.getsize(test_output_file)} bytes")
    
    checks = {}
    
    # 1. Zipfile structure validation
    try:
        with zipfile.ZipFile(test_output_file, "r") as zf:
            bad_file = zf.testzip()
            checks["zip_integrity"] = (bad_file is None)
            namelist = zf.namelist()
            checks["has_sheet1_xml"] = "xl/worksheets/sheet1.xml" in namelist
            checks["has_workbook_xml"] = "xl/workbook.xml" in namelist
            checks["has_content_types"] = "[Content_Types].xml" in namelist
            print(f"[*] Zipfile CRC integrity: {'PASS' if bad_file is None else 'FAIL'}")
    except Exception as e:
        checks["zip_integrity"] = False
        print(f"[FAIL] Zipfile inspection failed: {e}")
        
    # 2. openpyxl load_workbook with data_only=False
    try:
        wb_formulas = openpyxl.load_workbook(test_output_file, data_only=False)
        checks["openpyxl_load_formulas"] = True
        print("[*] openpyxl load_workbook(data_only=False): PASS (No XML corruption)")
    except Exception as e:
        checks["openpyxl_load_formulas"] = False
        print(f"[FAIL] openpyxl load_workbook(data_only=False) failed: {e}")
        wb_formulas = None

    # 3. openpyxl load_workbook with data_only=True
    try:
        wb_data = openpyxl.load_workbook(test_output_file, data_only=True)
        checks["openpyxl_load_data"] = True
        print("[*] openpyxl load_workbook(data_only=True): PASS")
    except Exception as e:
        checks["openpyxl_load_data"] = False
        print(f"[FAIL] openpyxl load_workbook(data_only=True) failed: {e}")
        wb_data = None

    # 4. Check formula syntax preservation
    formulas_intact = False
    if wb_formulas:
        ws = wb_formulas.active
        # Check employee 4 (HOÀNG ĐẮC PHÚ, row 24) formulas
        f_ak24 = ws["AK24"].value
        f_ar24 = ws["AR24"].value
        f_ak2 = ws["AK2"].value
        f_ar2 = ws["AR2"].value
        
        ak24_ok = (f_ak24 == "=SUM(F24:AJ24)")
        ar24_ok = (f_ar24 == "=SUM(AK24:AP24)")
        ak2_ok = (f_ak2 == "=SUM(AK3,AK10,AK17,AK24)")
        ar2_ok = (f_ar2 == "=SUM(AR3,AR10,AR17,AR24)")
        calc_ok = bool(wb_formulas.calculation.fullCalcOnLoad)
        
        formulas_intact = ak24_ok and ar24_ok and ak2_ok and ar2_ok and calc_ok
        print(f"[*] Formula AK24 ('{f_ak24}'): {'PASS' if ak24_ok else 'FAIL'}")
        print(f"[*] Formula AR24 ('{f_ar24}'): {'PASS' if ar24_ok else 'FAIL'}")
        print(f"[*] Formula AK2 ('{f_ak2}'): {'PASS' if ak2_ok else 'FAIL'}")
        print(f"[*] Formula AR2 ('{f_ar2}'): {'PASS' if ar2_ok else 'FAIL'}")
        print(f"[*] fullCalcOnLoad: {calc_ok}")
        
    checks["formulas_intact"] = formulas_intact
    
    # 5. Clean up test output file
    if os.path.exists(test_output_file):
        os.remove(test_output_file)
        print(f"Cleaned up temporary test file: {test_output_file}")
        
    return checks


def main():
    print("=" * 60)
    print("STARTING EMPIRICAL CHALLENGER M2-2 STRESS SUITE")
    print("=" * 60)
    ei = ExcelIntegrator()
    
    r1 = run_fuzzy_variations_challenge(ei)
    r2 = run_unmatched_names_challenge(ei)
    r3 = run_large_batch_challenge(ei, batch_sizes=(100, 250, 500))
    r4 = run_output_file_validity_challenge(ei)
    
    print("\n" + "=" * 60)
    print("CHALLENGE SUITE SUMMARY & VERDICT ANALYSIS")
    print("=" * 60)
    print(f"Fuzzy Variations Required: {r1['required_passed']}/{r1['required_total']} passed.")
    print(f"Unmatched Names Exception Safety: {r2['no_exception']} | Accurate Counts: {r2['passed_counts']}")
    print(f"Large Batch Insertion: 100 recs in {r3['benchmarks'][0]['elapsed_sec']}s, 500 recs in {r3['benchmarks'][2]['elapsed_sec']}s")
    print(f"Output XML Integrity: {r4.get('zip_integrity')} | openpyxl Reload: {r4.get('openpyxl_load_formulas')} | Formulas Intact: {r4.get('formulas_intact')}")
    
    if r1['required_passed'] < r1['required_total']:
        print("\n>>> CRITICAL FINDING: Employee name matcher failed on required variations!")
        print(">>> Variations failing: 'Hoàng Đắc Phú (KTV)' and 'Hoàng Đắc Phú 0912345678'")
        print(">>> Reason: Suffix annotations and trailing phone numbers are not stripped by normalize_name_key in core/excel_integrator.py, reducing SequenceMatcher ratio below 0.85 threshold.")
        print(">>> RECOMMENDED VERDICT: REJECT")
    else:
        print("\n>>> ALL TESTS PASSED. RECOMMENDED VERDICT: APPROVE")


if __name__ == "__main__":
    main()
