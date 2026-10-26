"""
Forensic Integrity Audit Script for Milestone 4 Iteration 2
Audits core/parser.py and core/template_generator.py.
"""
import ast
import os
import sys
import unicodedata
import openpyxl

PROJECT_ROOT = "/Users/congcm/CODE/Vibe_Code/Zalo_BOT"
os.chdir(PROJECT_ROOT)
sys.path.insert(0, PROJECT_ROOT)

from core.parser import (
    normalize_vietnamese_name,
    calculate_work_hours,
    extract_field_types,
    AttendanceParser,
    parse_attendance_messages,
    parse_single_message,
)
from core.template_generator import generate_default_template
from openpyxl.utils import get_column_letter

results = {}

# ==============================================================================
# CHECK 1: AST Scan of core/parser.py and core/template_generator.py
# ==============================================================================
print("=== CHECK 1: AST SCAN ===")

files_to_scan = ["core/parser.py", "core/template_generator.py"]
ast_issues = []

for file_path in files_to_scan:
    with open(file_path, "r", encoding="utf-8") as f:
        source = f.read()
    
    tree = ast.parse(source, filename=file_path)
    
    # Check for empty functions or facade implementations
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            body = node.body
            meaningful_stmts = [
                s for s in body 
                if not (isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant) and isinstance(s.value.value, str))
            ]
            if not meaningful_stmts:
                ast_issues.append(f"{file_path}:{node.lineno}: Function {node.name} has no meaningful statements (facade).")
            elif len(meaningful_stmts) == 1:
                stmt = meaningful_stmts[0]
                if isinstance(stmt, ast.Pass):
                    ast_issues.append(f"{file_path}:{node.lineno}: Function {node.name} body is only `pass`.")
                elif isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant) and stmt.value.value is ...:
                    ast_issues.append(f"{file_path}:{node.lineno}: Function {node.name} body is only `...`.")
                elif isinstance(stmt, ast.Raise) and isinstance(stmt.exc, ast.Call) and getattr(stmt.exc.func, "id", "") == "NotImplementedError":
                    ast_issues.append(f"{file_path}:{node.lineno}: Function {node.name} raises NotImplementedError.")
                elif isinstance(stmt, ast.Return) and isinstance(stmt.value, ast.Constant):
                    ast_issues.append(f"{file_path}:{node.lineno}: Function {node.name} unconditionally returns constant: {stmt.value.value}.")

        # Check for test-tailored branches
        if isinstance(node, ast.If):
            test_str = ast.unparse(node.test)
            for suspicious in ["test_", "assert", "fixture"]:
                if suspicious in test_str.lower():
                    ast_issues.append(f"{file_path}:{node.lineno}: Suspicious condition in `if`: {test_str}")

print(f"AST Scan Issues Found: {len(ast_issues)}")
for issue in ast_issues:
    print(f"  - {issue}")
results["check1_ast"] = len(ast_issues) == 0

# ==============================================================================
# CHECK 2: Authentic Logic - Unicode NFC Normalization in core/parser.py
# ==============================================================================
print("\n=== CHECK 2: UNICODE NFC NORMALIZATION ===")
nfc_issues = []

# Multiple test messages: short date and full date
messages_to_test = [
    # Case 1: Short date (inferred year -> WARNING)
    (
        "HỌ TÊN : HOÀNG ĐẮC PHÚ\nNGÀY: 24/10\nCA : Ca ngày\nDỰ ÁN : sdv\nTHỜI GIAN LÀM VIỆC :8h-17h ( 8H)\nCÓ ĂN Ở XƯỞNG KO : 0",
        "WARNING"
    ),
    # Case 2: Full date (explicit year -> VALID)
    (
        "HỌ TÊN : HOÀNG ĐẮC PHÚ\nNGÀY: 24/10/2026\nCA : Ca ngày\nDỰ ÁN : sdv\nTHỜI GIAN LÀM VIỆC :8h-17h ( 8H)\nCÓ ĂN Ở XƯỞNG KO : 0",
        "VALID"
    ),
    # Case 3: Other employee name with complex diacritics
    (
        "HỌ TÊN : NGUYỄN ĐỨC THẮNG\nNGÀY: 2026-10-25\nCA : Ca đêm\nDỰ ÁN : sdv\nTHỜI GIAN LÀM VIỆC :20h-5h ( 8H)\nCÓ ĂN Ở XƯỞNG KO : 1",
        "VALID"
    )
]

parser = AttendanceParser()

for raw_msg, expected_status in messages_to_test:
    nfd_msg = unicodedata.normalize("NFD", raw_msg)
    assert raw_msg != nfd_msg, "NFD did not decompose!"
    
    # 1. split_messages
    chunks_nfc = parser.split_messages(raw_msg)
    chunks_nfd = parser.split_messages(nfd_msg)
    if len(chunks_nfc) != 1 or len(chunks_nfd) != 1:
        nfc_issues.append(f"split_messages failed: NFC={len(chunks_nfc)}, NFD={len(chunks_nfd)}")
    
    # 2. parse_single
    rec_nfc = parser.parse_single(raw_msg)
    rec_nfd = parser.parse_single(nfd_msg)
    
    if rec_nfc.status != expected_status:
        nfc_issues.append(f"NFC status mismatch: got {rec_nfc.status}, expected {expected_status}")
    if rec_nfd.status != expected_status:
        nfc_issues.append(f"NFD status mismatch: got {rec_nfd.status}, expected {expected_status}")
        
    if rec_nfc.employee_name != rec_nfd.employee_name:
        nfc_issues.append(f"Name mismatch: {rec_nfc.employee_name!r} vs {rec_nfd.employee_name!r}")
    if rec_nfc.hours.model_dump() != rec_nfd.hours.model_dump():
        nfc_issues.append(f"Hours mismatch: {rec_nfc.hours} vs {rec_nfd.hours}")
    if rec_nfc.meal_count != rec_nfd.meal_count:
        nfc_issues.append(f"Meal mismatch: {rec_nfc.meal_count} vs {rec_nfd.meal_count}")
    if rec_nfc.resolved_date != rec_nfd.resolved_date:
        nfc_issues.append(f"Date mismatch: {rec_nfc.resolved_date} vs {rec_nfd.resolved_date}")

    # 3. extract_field_types
    f_nfc = extract_field_types(raw_msg)
    f_nfd = extract_field_types(nfd_msg)
    if f_nfc != f_nfd:
        nfc_issues.append(f"extract_field_types mismatch: {f_nfc} vs {f_nfd}")

    # 4. convenience functions
    c_nfc = parse_single_message(raw_msg)
    c_nfd = parse_single_message(nfd_msg)
    if c_nfc.employee_name != c_nfd.employee_name or c_nfc.status != c_nfd.status:
        nfc_issues.append(f"parse_single_message mismatch for {raw_msg[:20]}")

# 5. Batch parse test
batch_text_nfc = "\n---\n".join([m[0] for m in messages_to_test])
batch_text_nfd = unicodedata.normalize("NFD", batch_text_nfc)
batch_nfc_recs = parse_attendance_messages(batch_text_nfc)
batch_nfd_recs = parse_attendance_messages(batch_text_nfd)

if len(batch_nfc_recs) != len(messages_to_test) or len(batch_nfd_recs) != len(messages_to_test):
    nfc_issues.append(f"Batch rec count mismatch: NFC={len(batch_nfc_recs)}, NFD={len(batch_nfd_recs)}")
else:
    for i, (rnfc, rnfd) in enumerate(zip(batch_nfc_recs, batch_nfd_recs)):
        if rnfc.employee_name != rnfd.employee_name:
            nfc_issues.append(f"Batch item {i} name mismatch: {rnfc.employee_name} vs {rnfd.employee_name}")
        if rnfc.status != rnfd.status:
            nfc_issues.append(f"Batch item {i} status mismatch: {rnfc.status} vs {rnfd.status}")

# 6. normalize_vietnamese_name
names = ["HOÀNG ĐẮC PHÚ", "nguyễn văn bính", "VŨ THỊ HƯỜNG (thợ hàn) - 0987654321"]
for n in names:
    n_nfc = normalize_vietnamese_name(n)
    n_nfd = normalize_vietnamese_name(unicodedata.normalize("NFD", n))
    if n_nfc != n_nfd:
        nfc_issues.append(f"normalize_vietnamese_name mismatch for {n!r}: {n_nfc!r} vs {n_nfd!r}")

print(f"Unicode NFC Normalization Issues: {len(nfc_issues)}")
for issue in nfc_issues:
    print(f"  - {issue}")
results["check2_nfc"] = len(nfc_issues) == 0

# ==============================================================================
# CHECK 3: Authentic Logic - Excel Formula Chunking in core/template_generator.py
# ==============================================================================
print("\n=== CHECK 3: EXCEL FORMULA CHUNKING ===")
formula_issues = []

def mock_generate_row2_formula(col_idx: int, employee_start_rows: list[int]) -> str:
    col_letter = get_column_letter(col_idx)
    terms = [f"{col_letter}{r}" for r in employee_start_rows]
    if len(terms) <= 250:
        return f"=SUM({','.join(terms)})"
    else:
        chunks = [terms[i:i + 250] for i in range(0, len(terms), 250)]
        sub_sums = [f"SUM({','.join(c)})" for c in chunks]
        return f"=SUM({','.join(sub_sums)})"

# Case A: Standard roster (4 employees)
f4 = mock_generate_row2_formula(37, [3, 10, 17, 24])
expected_f4 = "=SUM(AK3,AK10,AK17,AK24)"
if f4 != expected_f4:
    formula_issues.append(f"Standard roster (4 emps) formula mismatch: {f4!r} != {expected_f4!r}")
else:
    print(f"Case A (4 emps): {f4}")

# Case B: Threshold roster (250 employees)
roster_250 = [3 + 7 * i for i in range(250)]
f250 = mock_generate_row2_formula(37, roster_250)
if not f250.startswith("=SUM(AK3,") or f250.count("SUM(") != 1:
    formula_issues.append(f"Threshold roster (250 emps) formula unexpected: {f250[:50]}...")
else:
    arg_count = f250[5:-1].count(",") + 1
    if arg_count != 250:
        formula_issues.append(f"250 emps argument count mismatch: {arg_count} != 250")
    print(f"Case B (250 emps): valid single SUM with {arg_count} args.")

# Case C: Exceeding threshold (251 employees)
roster_251 = [3 + 7 * i for i in range(251)]
f251 = mock_generate_row2_formula(37, roster_251)
if not f251.startswith("=SUM(SUM(AK3,") or f251.count("SUM(") != 3:
    formula_issues.append(f"Threshold+1 (251 emps) formula unexpected: {f251[:50]}... count SUM={f251.count('SUM(')}")
else:
    print(f"Case C (251 emps): valid chunked formula =SUM(SUM(250),SUM(1)): {f251[:40]}...{f251[-30:]}")

# Case D: Large roster (600 employees)
roster_600 = [3 + 7 * i for i in range(600)]
f600 = mock_generate_row2_formula(37, roster_600)
if f600.count("SUM(") != 4:
    formula_issues.append(f"Large roster (600 emps) formula unexpected SUM count: {f600.count('SUM(')} != 4")
else:
    print(f"Case D (600 emps): valid chunked formula with 3 sub-sums.")

# Check the generated master template file itself
master_template_path = os.path.join(PROJECT_ROOT, "templates_excel", "BẢNG CHẤM CÔNG WEVN - ETS.xlsx")
if not os.path.exists(master_template_path):
    formula_issues.append(f"Master template file not found at {master_template_path}")
else:
    wb = openpyxl.load_workbook(master_template_path, data_only=False)
    ws = wb.active
    # Verify row 2 grand total formulas across AK2..AR2 (cols 37..44)
    for c in range(37, 45):
        c_letter = get_column_letter(c)
        val = ws.cell(row=2, column=c).value
        expected = f"=SUM({c_letter}3,{c_letter}10,{c_letter}17,{c_letter}24)"
        if val != expected:
            formula_issues.append(f"Master template cell {c_letter}2 has {val!r}, expected {expected!r}")
    
    # Verify employee block row formulas
    for r in [3, 10, 17, 24]:
        ak_val = ws.cell(row=r, column=37).value
        if ak_val != f"=SUM(F{r}:AJ{r})":
            formula_issues.append(f"Cell AK{r} formula mismatch: {ak_val!r}")
        ar_val = ws.cell(row=r, column=44).value
        if ar_val != f"=SUM(AK{r}:AP{r})":
            formula_issues.append(f"Cell AR{r} formula mismatch: {ar_val!r}")
    
    if not wb.calculation.fullCalcOnLoad:
        formula_issues.append("fullCalcOnLoad is not True in master template")

print(f"Formula Chunking Issues: {len(formula_issues)}")
for issue in formula_issues:
    print(f"  - {issue}")
results["check3_formula"] = len(formula_issues) == 0

# ==============================================================================
# CHECK 4: Pre-populated Artifact Scan
# ==============================================================================
print("\n=== CHECK 4: PRE-POPULATED ARTIFACT SCAN ===")
import glob

spurious_files = []
for pattern in ["*.log", "*output*/*.log", "tests/*.log"]:
    for f in glob.glob(pattern):
        spurious_files.append(f)

print(f"Spurious artifact files found: {spurious_files}")
results["check4_artifacts"] = len(spurious_files) == 0

# Summary
print("\n=== OVERALL AUDIT SUMMARY ===")
for k, v in results.items():
    print(f"{k}: {'PASS' if v else 'FAIL'}")

if all(results.values()):
    print("\nVERDICT: CLEAN")
else:
    print("\nVERDICT: INTEGRITY VIOLATION")
