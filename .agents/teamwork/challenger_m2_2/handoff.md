# Empirical Challenge Report — Milestone 2 (Challenger 2)

**Evaluator Archetype**: EMPIRICAL CHALLENGER  
**Target Module**: `core/excel_integrator.py`  
**Working Directory**: `/Users/congcm/CODE/Vibe_Code/Zalo_BOT/.agents/teamwork/challenger_m2_2/`  
**Test Runner Harness**: `.agents/teamwork/challenger_m2_2/stress_test_excel_m2.py`  
**Final Verdict**: **REJECT** (Remediation required for employee name matching)

---

## 1. Observation

Direct empirical observations from executing the challenge harness `.agents/teamwork/challenger_m2_2/stress_test_excel_m2.py` against Python 3.11 virtualenv:

### 1.1 Challenge 1: Employee Name Fuzzy Variations
Execution command:
```bash
.venv/bin/python3 .agents/teamwork/challenger_m2_2/stress_test_excel_m2.py
```

Results for required variations:
- Query `'hoàng đắc phú'`:
  - Expected: Row 24 (`HOÀNG ĐẮC PHÚ`)
  - Actual: `(24, 'HOÀNG ĐẮC PHÚ', 1.00)` -> **PASS**
- Query `'HOANG DAC PHU'`:
  - Expected: Row 24 (`HOÀNG ĐẮC PHÚ`)
  - Actual: `(24, 'HOÀNG ĐẮC PHÚ', 0.95)` -> **PASS**
- Query `'HOÀNG  ĐẮC   PHÚ '`:
  - Expected: Row 24 (`HOÀNG ĐẮC PHÚ`)
  - Actual: `(24, 'HOÀNG ĐẮC PHÚ', 1.00)` -> **PASS**
- Query `'Hoàng Đắc Phú (KTV)'`:
  - Expected: Row 24 (`HOÀNG ĐẮC PHÚ`)
  - Actual: `(None, '', 0.00)` -> **FAIL** (CRITICAL DEFECT)
- Query `'Hoàng Đắc Phú 0912345678'`:
  - Expected: Row 24 (`HOÀNG ĐẮC PHÚ`)
  - Actual: `(None, '', 0.00)` -> **FAIL** (CRITICAL DEFECT)

Extended variations tested:
- `'Hoàng Đắc Phú - 0912345678'` -> `(None, '', 0.00)` (**FAIL**)
- `'Hoàng Đắc Phú (thợ hàn)'` -> `(None, '', 0.00)` (**FAIL**)
- `'Nguyễn Đức Công (Tổ 1)'` -> `(None, '', 0.00)` (**FAIL**)
- `'Nguyễn Ngọc Thao (Cơ điện)'` -> `(None, '', 0.00)` (**FAIL**)
- `'HOÀNG ĐĂC PHÚ'` (typo `ă`) -> `(24, 'HOÀNG ĐẮC PHÚ', 0.95)` (**PASS**)
- `'hoang dac phuu'` (typo `uu`) -> `(24, 'HOÀNG ĐẮC PHÚ', 0.96)` (**PASS**)

### 1.2 Code Inspection in `core/excel_integrator.py`
In `core/excel_integrator.py:35-40`:
```python
def normalize_name_key(text: str) -> str:
    """Normalizes whitespace and Unicode NFC representation."""
    if not text:
        return ""
    clean = re.sub(r'\s+', ' ', unicodedata.normalize('NFC', text)).strip()
    return clean
```
`normalize_name_key` solely strips extraneous whitespace and normalizes Unicode NFC. It does **not** strip:
1. Parenthesized annotations or job roles (e.g. `(KTV)`, `(thợ hàn)`, `(Tổ 1)`).
2. Trailing phone numbers (e.g. `0912345678`).

In `core/excel_integrator.py:194-205`:
```python
        # Tier 3: Fuzzy sequence matching (>= 0.85)
        best_emp = None
        best_score = 0.0
        for emp in self.employees:
            score = SequenceMatcher(None, target_unaccented, emp["unaccented"]).ratio()
            if score > best_score:
                best_score = score
                best_emp = emp

        if best_emp and best_score >= 0.85:
            return best_emp["row"], best_emp["clean_name"], round(best_score, 2)

        return None, "", 0.0
```
- For `'Hoàng Đắc Phú (KTV)'`:
  - `target_unaccented` is `"hoang dac phu (ktv)"` (length 20).
  - `emp["unaccented"]` is `"hoang dac phu"` (length 14).
  - `SequenceMatcher` similarity ratio is $2 \times 14 / (20 + 14) = 28 / 34 \approx 0.8235$.
  - Because $0.8235 < 0.85$, Tier 3 rejects the match and returns `(None, "", 0.0)`.
- For `'Hoàng Đắc Phú 0912345678'`:
  - `target_unaccented` is `"hoang dac phu 0912345678"` (length 25).
  - Ratio is $2 \times 14 / (25 + 14) = 28 / 39 \approx 0.7179 < 0.85$.
  - Tier 3 rejects the match and returns `(None, "", 0.0)`.

### 1.3 Challenge 2: Unmatched Names & Non-existent Employees
Tested with 9 invalid inputs (`Alexander the Great`, `Trần Văn Vô Danh`, `John Doe`, `NonExistent Worker 999`, `Công ty Cổ phần Xây dựng`, `!@#$%^&*()`, `1234567890`, `""`, `"   "`):
- No exception or crash occurred: `no_exception = True`
- `stats['records_processed'] = 9`
- `stats['unmatched_records'] = 9`
- `stats['cells_written'] = 0`
- `stats['errors']` length = 9, with descriptive messages e.g. `"Unmatched employee: Alexander the Great"`
- `stats['unmatched_list']` accurately listed all 9 records.
- Result: **100% PASS**.

### 1.4 Challenge 3: Large Batch Insertion Performance & Memory Footprint
Tested with 100, 250, and 500 records on fresh workbook instances:
- **100 records**:
  - Elapsed time: `0.0375 seconds` (Throughput: `2,664.8 records/sec`)
  - Peak memory footprint: `0.46 MB`
  - Cells written: `234`
- **250 records**:
  - Elapsed time: `0.0377 seconds` (Throughput: `6,637.0 records/sec`)
  - Peak memory footprint: `0.45 MB`
  - Cells written: `584`
- **500 records**:
  - Elapsed time: `0.0416 seconds` (Throughput: `12,031.2 records/sec`)
  - Peak memory footprint: `0.45 MB`
  - Cells written: `1,167`
- Result: **100% PASS** (Sub-50ms execution, flat memory footprint < 0.5 MB).

### 1.5 Challenge 4: Output File Validity & XML Integrity
Generated output file `output_stress_test.xlsx` with 120 applied records:
- Zipfile CRC integrity check (`zipfile.ZipFile.testzip()`): `None` (Zero bad files) -> **PASS**
- Presence of critical OPC parts (`xl/worksheets/sheet1.xml`, `xl/workbook.xml`, `[Content_Types].xml`): **PASS**
- `openpyxl.load_workbook(data_only=False)`: Succeeded with 0 warnings or XML corruption errors -> **PASS**
- `openpyxl.load_workbook(data_only=True)`: Succeeded -> **PASS**
- Formula syntax preservation:
  - `ws['AK24'].value`: `=SUM(F24:AJ24)` -> **PASS**
  - `ws['AR24'].value`: `=SUM(AK24:AP24)` -> **PASS**
  - `ws['AK2'].value`: `=SUM(AK3,AK10,AK17,AK24)` -> **PASS**
  - `ws['AR2'].value`: `=SUM(AR3,AR10,AR17,AR24)` -> **PASS**
  - `wb.calculation.fullCalcOnLoad`: `True` -> **PASS**
- Result: **100% PASS**.

---

## 2. Logic Chain

1. **Premise 1**: Real-world attendance messages in Zalo frequently append worker job designations or contact numbers to employee names (e.g. `Hoàng Đắc Phú (KTV)` or `Hoàng Đắc Phú 0912345678`).
2. **Premise 2**: The prompt explicitly established 5 mandatory fuzzy variations to be challenged against `core/excel_integrator.py`:
   `'hoàng đắc phú'`, `'HOANG DAC PHU'`, `'HOÀNG  ĐẮC   PHÚ '`, `'Hoàng Đắc Phú (KTV)'`, `'Hoàng Đắc Phú 0912345678'`.
3. **Inference from Observation 1.1 & 1.2**:
   - `core/excel_integrator.py` failed to match `'Hoàng Đắc Phú (KTV)'` and `'Hoàng Đắc Phú 0912345678'`, returning `(None, '', 0.00)`.
   - The root cause is twofold:
     a. `normalize_name_key` lacks regex cleaning for parenthetical expressions `\(.*?\)` and phone numbers `(?:\+84|0)\d{9,10}`.
     b. `match_employee` lacks substring/token containment matching (`emp['unaccented'] in target_unaccented`), relying solely on a fixed `SequenceMatcher` ratio $\ge 0.85$, which drops to 0.82 for `(KTV)` and 0.72 for phone numbers.
4. **Impact Analysis**:
   When an attendance message contains a role annotation or phone number, `apply_records` classifies the employee as unmatched, drops the record into `unmatched_records`, and writes zero hours into the timesheet. The employee receives no credit on the Excel sheet despite being a legitimate employee in the template.
5. **Conclusion from Logic Chain**:
   Although performance, XML integrity, and error trapping are outstanding, the core matching engine fails 2 out of the 5 mandatory challenge variations, leading to data loss for common real-world message patterns. Therefore, Milestone 2 cannot be approved without remediation.

---

## 3. Caveats

- In the complete pipeline, if messages pass through `core/parser.py`, `normalize_vietnamese_name` strips `\(.*?\)` and hyphenated phone numbers `[-–]\s*\d{9,11}`. However:
  1. It does **not** strip unhyphenated phone numbers (e.g., `Hoàng Đắc Phú 0912345678`).
  2. If the user edits the employee name directly on the Web UI table or sends records via external API, `core/excel_integrator.py` is invoked directly and must be self-reliant.
  3. `core/excel_integrator.py` contract specifies robust fuzzy matching independently.
- No other defects were found in date resolution, formula preservation, 7-row block coordinate mapping, or large batch handling.

---

## 4. Conclusion & Recommended Verdict

### Verdict: **REJECT**

### Recommended Remediation for Worker Agent:
In `core/excel_integrator.py`:
1. Enhance `normalize_name_key(text: str)` or add a name cleaner before matching:
   ```python
   def clean_employee_name_for_matching(text: str) -> str:
       if not text:
           return ""
       # Strip parenthesized annotations e.g. (KTV), (thợ hàn), (Tổ 1)
       t = re.sub(r'\(.*?\)', '', text)
       # Strip phone numbers (both hyphenated and plain 9-11 digits)
       t = re.sub(r'[-–]?\s*(?:0|\+84)\d{8,10}\b', '', t)
       # Strip role notes following dash e.g. - KTV
       t = re.sub(r'[-–]\s*[A-Za-zÀ-ỹ\s]+$', '', t)
       # Normalize whitespace
       return normalize_name_key(t)
   ```
2. In `match_employee`, add a Substring / Token Containment check before or alongside Tier 3:
   ```python
   # Substring / Prefix match: if exact employee unaccented name is a full token sequence in target
   for emp in self.employees:
       # Check word boundary containment or substring
       if emp["unaccented"] in target_unaccented:
           return emp["row"], emp["clean_name"], 0.90
   ```
   Alternatively, if `SequenceMatcher` is used, compare the cleaned name without annotations.

---

## 5. Verification Method

To independently verify all findings and reproduce the bug:

```bash
cd /Users/congcm/CODE/Vibe_Code/Zalo_BOT
.venv/bin/python3 .agents/teamwork/challenger_m2_2/stress_test_excel_m2.py
```

### Direct Python One-Liner Reproduction:
```bash
.venv/bin/python3 -c "from core.excel_integrator import ExcelIntegrator; ei = ExcelIntegrator(); print(ei.match_employee('Hoàng Đắc Phú (KTV)')); print(ei.match_employee('Hoàng Đắc Phú 0912345678'))"
```
**Expected after fix**: `(24, 'HOÀNG ĐẮC PHÚ', >= 0.85)` for both.  
**Actual current bug**: `(None, '', 0.0)` for both.
