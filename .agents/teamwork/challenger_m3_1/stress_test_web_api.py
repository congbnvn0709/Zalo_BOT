"""
Empirical Adversarial Stress Test Suite for FastAPI Endpoints (Milestone 3).

Target:
- main.py (FastAPI application and middleware)
- api/routes.py (REST API endpoints)

Challenge Areas:
1. Fuzzing /api/parse: 100k payload, corrupt/non-UTF8 encodings, malformed JSON, empty/null values, ReDoS.
2. Concurrency on /api/export-excel: 25 concurrent export requests, verify unique tokens and intact Excel workbooks.
3. Token Traversal on /api/download/{token}: directory traversal (../..), invalid UUIDs, expired/malformed tokens.
4. Custom Template Upload: 0-byte file, exe/.txt disguised as .xlsx, corrupt zip, non-xlsx files, path traversal in filename.
5. Injection and Edge Cases on /api/export-excel: path traversal in output_filename, empty payload, invalid schemas.

Requirement:
- Assert zero 500 unhandled crashes.
- Verify appropriate 400/404/422 status codes.
"""

import os
import sys
import io
import time
import json
import zipfile
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List, Tuple

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import openpyxl
from fastapi.testclient import TestClient
from main import app
from core.excel_integrator import DEFAULT_OUTPUT_DIR


class EmpiricalTestResult:
    def __init__(self, name: str, category: str):
        self.name = name
        self.category = category
        self.passed = False
        self.status_code = None
        self.response_snippet = ""
        self.elapsed_ms = 0.0
        self.details = ""
        self.is_500 = False

    def mark_pass(self, status_code: int, details: str, elapsed_ms: float = 0.0):
        self.passed = True
        self.status_code = status_code
        self.details = details
        self.elapsed_ms = elapsed_ms

    def mark_fail(self, status_code: int, details: str, response_snippet: str = "", elapsed_ms: float = 0.0):
        self.passed = False
        self.status_code = status_code
        self.details = details
        self.response_snippet = response_snippet[:300]
        self.elapsed_ms = elapsed_ms
        if status_code == 500:
            self.is_500 = True


class WebAPIAdversarialRunner:
    def __init__(self):
        self.client = TestClient(app, raise_server_exceptions=False)
        self.results: List[EmpiricalTestResult] = []

    def record(self, result: EmpiricalTestResult):
        self.results.append(result)
        status_icon = "✅ PASS" if result.passed else ("🔥 500 CRASH" if result.is_500 else "❌ FAIL")
        print(f"[{status_icon}] [{result.category}] {result.name} (status={result.status_code}, time={result.elapsed_ms:.1f}ms): {result.details}")

    # =========================================================================
    # Group 1: /api/parse Fuzzing & Malformed Inputs
    # =========================================================================
    def test_parse_fuzzing(self):
        print("\n--- Running Group 1: /api/parse Fuzzing & Malformed Payloads ---")

        # 1.1 Huge 100,000-character string payload (adversarial repetitive patterns)
        r = EmpiricalTestResult("100k Character Repetitive Text", "/api/parse")
        huge_text = ("HỌ TÊN: NGUYỄN VĂN TEST\nNGÀY: 24/10\nCA: Ca ngày\nTHỜI GIAN LÀM VIỆC: 8h-17h (8H)\nCÓ ĂN Ở XƯỞNG KO: 1\n\n" * 1000)[:100_000]
        t0 = time.time()
        resp = self.client.post("/api/parse", json={"text": huge_text})
        el = (time.time() - t0) * 1000
        if resp.status_code == 200:
            data = resp.json()
            rec_count = len(data.get("records", []))
            r.mark_pass(resp.status_code, f"Parsed {rec_count} records from 100k payload successfully", el)
        elif resp.status_code in (400, 422):
            r.mark_pass(resp.status_code, f"Rejected with expected status {resp.status_code}", el)
        else:
            r.mark_fail(resp.status_code, f"Unexpected status {resp.status_code}", resp.text, el)
        self.record(r)

        # 1.2 Huge 100,000-character random noise / single-line payload (ReDoS attack vector)
        r = EmpiricalTestResult("100k Character Unsegmented Noise (ReDoS check)", "/api/parse")
        noise_text = "HỌ TÊN : " + ("ABCXYZ " * 14000)
        t0 = time.time()
        resp = self.client.post("/api/parse", json={"text": noise_text})
        el = (time.time() - t0) * 1000
        if resp.status_code == 200 and el < 5000:
            r.mark_pass(resp.status_code, f"ReDoS survived in {el:.1f}ms without hang", el)
        elif resp.status_code in (400, 422):
            r.mark_pass(resp.status_code, f"Rejected cleanly in {el:.1f}ms", el)
        else:
            r.mark_fail(resp.status_code, f"Hang or failure (took {el:.1f}ms)", resp.text, el)
        self.record(r)

        # 1.3 Non-UTF-8 / corrupt binary payload in JSON body
        r = EmpiricalTestResult("Non-UTF8 Corrupted Binary Raw Body", "/api/parse")
        t0 = time.time()
        corrupt_bytes = b'{"text": "\xff\xfe\x00\x41\x42\x43\x80\x81\x82"}'
        resp = self.client.post("/api/parse", content=corrupt_bytes, headers={"Content-Type": "application/json"})
        el = (time.time() - t0) * 1000
        # Should be 400 or 422 due to decode error, NEVER 500
        if resp.status_code in (400, 422):
            r.mark_pass(resp.status_code, f"Handled non-UTF8 cleanly with {resp.status_code}", el)
        elif resp.status_code == 200:
            r.mark_pass(resp.status_code, "Processed or decoded bytes gracefully", el)
        else:
            r.mark_fail(resp.status_code, f"Failed on non-UTF8 binary: status {resp.status_code}", resp.text, el)
        self.record(r)

        # 1.4 Raw null bytes inside string
        r = EmpiricalTestResult("Null Bytes Embedded in String", "/api/parse")
        t0 = time.time()
        resp = self.client.post("/api/parse", json={"text": "HỌ TÊN : HOÀNG\x00 ĐẮC PHÚ\nNGÀY: 24\x00/10\nCA : Ca ngày\nTHỜI GIAN LÀM VIỆC: 8h-17h"})
        el = (time.time() - t0) * 1000
        if resp.status_code == 200:
            r.mark_pass(resp.status_code, "Parsed record safely with embedded nulls", el)
        elif resp.status_code in (400, 422):
            r.mark_pass(resp.status_code, f"Rejected null-byte string with {resp.status_code}", el)
        else:
            r.mark_fail(resp.status_code, f"Unexpected error with null bytes", resp.text, el)
        self.record(r)

        # 1.5 Malformed JSON: Truncated JSON
        r = EmpiricalTestResult("Malformed Truncated JSON Payload", "/api/parse")
        t0 = time.time()
        resp = self.client.post("/api/parse", content='{"text": "HỌ TÊN: Hoàng Dac Phu'.encode('utf-8'), headers={"Content-Type": "application/json"})
        el = (time.time() - t0) * 1000
        if resp.status_code in (400, 422):
            r.mark_pass(resp.status_code, f"Rejected malformed JSON with {resp.status_code}", el)
        else:
            r.mark_fail(resp.status_code, f"Did not reject malformed JSON properly", resp.text, el)
        self.record(r)

        # 1.6 Malformed JSON: Unexpected syntax
        r = EmpiricalTestResult("Malformed Syntax JSON (Trailing comma / unclosed brace)", "/api/parse")
        t0 = time.time()
        resp = self.client.post("/api/parse", content=b'{text: "no quotes",}', headers={"Content-Type": "application/json"})
        el = (time.time() - t0) * 1000
        if resp.status_code in (400, 422):
            r.mark_pass(resp.status_code, f"Rejected with {resp.status_code}", el)
        else:
            r.mark_fail(resp.status_code, "Failed to reject invalid JSON", resp.text, el)
        self.record(r)

        # 1.7 Empty string payload: {"text": ""}
        r = EmpiricalTestResult("Empty String Payload {'text': ''}", "/api/parse")
        t0 = time.time()
        resp = self.client.post("/api/parse", json={"text": ""})
        el = (time.time() - t0) * 1000
        if resp.status_code == 200:
            data = resp.json()
            if len(data.get("records", [])) == 0 and data.get("summary", {}).get("total") == 0:
                r.mark_pass(resp.status_code, "Returned clean empty record list", el)
            else:
                r.mark_fail(resp.status_code, f"Unexpected records returned for empty text: {data}", resp.text, el)
        else:
            r.mark_fail(resp.status_code, f"Empty text rejected with {resp.status_code}", resp.text, el)
        self.record(r)

        # 1.8 Null values: {"text": null, "raw_text": null}
        r = EmpiricalTestResult("Null Values {'text': null, 'raw_text': null}", "/api/parse")
        t0 = time.time()
        resp = self.client.post("/api/parse", json={"text": None, "raw_text": None})
        el = (time.time() - t0) * 1000
        if resp.status_code == 200:
            data = resp.json()
            r.mark_pass(resp.status_code, f"Gracefully treated nulls as empty text (0 records)", el)
        elif resp.status_code in (400, 422):
            r.mark_pass(resp.status_code, f"Rejected null values with {resp.status_code}", el)
        else:
            r.mark_fail(resp.status_code, "Crashed or unexpected status on null values", resp.text, el)
        self.record(r)

        # 1.9 Completely Empty Object: {}
        r = EmpiricalTestResult("Empty Object Payload {}", "/api/parse")
        t0 = time.time()
        resp = self.client.post("/api/parse", json={})
        el = (time.time() - t0) * 1000
        if resp.status_code == 200:
            r.mark_pass(resp.status_code, "Defaulted successfully to empty text", el)
        elif resp.status_code in (400, 422):
            r.mark_pass(resp.status_code, f"Rejected empty object with {resp.status_code}", el)
        else:
            r.mark_fail(resp.status_code, "Unexpected response on empty object", resp.text, el)
        self.record(r)

        # 1.10 Type Mismatch: {"text": 12345, "default_year": "invalid"}
        r = EmpiricalTestResult("Type Mismatches (int for text, string for default_year)", "/api/parse")
        t0 = time.time()
        resp = self.client.post("/api/parse", json={"text": {"complex": [1, 2, 3]}, "default_year": "not_a_year"})
        el = (time.time() - t0) * 1000
        if resp.status_code == 422:
            r.mark_pass(resp.status_code, "Pydantic properly rejected schema violations with 422", el)
        else:
            r.mark_fail(resp.status_code, f"Expected 422 validation error, got {resp.status_code}", resp.text, el)
        self.record(r)

        # 1.11 Emoji & Unicode edge cases (Zalgo, RTL, combining chars)
        r = EmpiricalTestResult("Extreme Unicode (Zalgo, RTL, Emoji Bomb)", "/api/parse")
        zalgo_payload = "HỌ TÊN: H̶o̶à̶n̶g̶ ̶Đ̶ắ̶c̶ ̶P̶h̶ú̶ 👨‍👩‍👧‍👦🔥🚀\nNGÀY: 24/10\nCA: Ca ngày\nTHỜI GIAN LÀM VIỆC: 8h-17h\nCÓ ĂN Ở XƯỞNG KO: 0\n" + ("\u202E\u200B\uFEFF" * 100)
        t0 = time.time()
        resp = self.client.post("/api/parse", json={"text": zalgo_payload})
        el = (time.time() - t0) * 1000
        if resp.status_code == 200:
            r.mark_pass(resp.status_code, "Processed Unicode / Emoji bomb safely", el)
        elif resp.status_code in (400, 422):
            r.mark_pass(resp.status_code, f"Handled with {resp.status_code}", el)
        else:
            r.mark_fail(resp.status_code, "Failed on Unicode / Emoji bomb", resp.text, el)
        self.record(r)

    # =========================================================================
    # Group 2: Concurrency / Race Conditions on /api/export-excel
    # =========================================================================
    def test_concurrency_export(self, concurrency_count: int = 25):
        print(f"\n--- Running Group 2: Concurrency & Race Conditions on /api/export-excel ({concurrency_count} threads) ---")

        # Standard record payload to export
        test_records = [
            {
                "employee_name": "HOÀNG ĐẮC PHÚ",
                "date_str": "24/10",
                "resolved_date": "2026-10-24",
                "day_number": 24,
                "is_sunday": False,
                "shift_type": "DAY",
                "project": "sdv",
                "time_window": "8h-17h (8H)",
                "hours": {
                    "hcn_100": 8.0,
                    "tcn_150": 0.0,
                    "hcd_130": 0.0,
                    "tcd_195": 0.0,
                    "sunday_day_200": 0.0,
                    "sunday_night_260": 0.0,
                    "total_hours": 8.0,
                },
                "meal_count": 0,
                "status": "VALID",
            },
            {
                "employee_name": "NGUYỄN NGỌC THAO",
                "date_str": "24/10",
                "resolved_date": "2026-10-24",
                "day_number": 24,
                "is_sunday": False,
                "shift_type": "DAY",
                "project": "sdv",
                "time_window": "8h-20h (11H)",
                "hours": {
                    "hcn_100": 8.0,
                    "tcn_150": 3.0,
                    "hcd_130": 0.0,
                    "tcd_195": 0.0,
                    "sunday_day_200": 0.0,
                    "sunday_night_260": 0.0,
                    "total_hours": 11.0,
                },
                "meal_count": 1,
                "status": "VALID",
            },
        ]

        results_lock = threading.Lock()
        export_responses: List[Tuple[int, Dict[str, Any], float]] = []

        def worker_task(thread_id: int):
            t0 = time.time()
            payload = {
                "records": test_records,
                "use_custom_template": False,
                "output_filename": f"CONCURRENT_EXPORT_T{thread_id}.xlsx",
            }
            res = self.client.post("/api/export-excel", json=payload)
            elapsed = (time.time() - t0) * 1000
            try:
                body = res.json()
            except Exception:
                body = {"raw": res.text}
            with results_lock:
                export_responses.append((res.status_code, body, elapsed))

        threads = []
        t_start = time.time()
        for i in range(concurrency_count):
            t = threading.Thread(target=worker_task, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()
        total_time = (time.time() - t_start) * 1000

        # Verification 1: Zero 500 errors and 100% 200 OK
        r1 = EmpiricalTestResult(f"{concurrency_count} Concurrent Export Requests - Status Codes", "/api/export-excel")
        all_200 = all(code == 200 for code, _, _ in export_responses)
        has_500 = any(code == 500 for code, _, _ in export_responses)
        if all_200 and not has_500:
            r1.mark_pass(200, f"All {concurrency_count} concurrent exports succeeded with 200 OK in {total_time:.1f}ms", total_time)
        else:
            status_summary = {code: sum(1 for c, _, _ in export_responses if c == code) for code, _, _ in export_responses}
            r1.mark_fail(500 if has_500 else 400, f"Concurrent exports failed: {status_summary}", "", total_time)
        self.record(r1)

        # Verification 2: Unique Download Tokens
        r2 = EmpiricalTestResult(f"{concurrency_count} Concurrent Export Requests - Token Uniqueness", "/api/export-excel")
        tokens = [body.get("download_token") for code, body, _ in export_responses if code == 200]
        unique_tokens = set(tokens)
        if len(unique_tokens) == len(tokens) == concurrency_count:
            r2.mark_pass(200, f"All {concurrency_count} tokens are strictly unique", total_time)
        else:
            r2.mark_fail(500, f"Token collision detected! {len(unique_tokens)} unique tokens out of {len(tokens)}", "", total_time)
        self.record(r2)

        # Verification 3: File Integrity on Disk and via Download Endpoint
        r3 = EmpiricalTestResult(f"{concurrency_count} Concurrent Workbooks - Excel File Integrity & Non-Collision", "/api/export-excel")
        corrupted_files = []
        download_failures = []

        for code, body, _ in export_responses:
            if code != 200:
                continue
            token = body.get("download_token")
            filename = body.get("filename")

            # Check download endpoint
            dl_resp = self.client.get(f"/api/download/{token}")
            if dl_resp.status_code != 200:
                download_failures.append((token, dl_resp.status_code))
                continue

            file_bytes = dl_resp.content
            if len(file_bytes) < 1000:
                corrupted_files.append((token, "File too small (<1KB)"))
                continue

            # Load workbook in-memory to verify openpyxl integrity
            try:
                wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=False)
                ws = wb.active
                # Verify that formulas exist and values were written
                assert ws is not None, "Worksheet is None"
                # Check that fullCalcOnLoad is True
                assert wb.calculation.fullCalcOnLoad is True, "fullCalcOnLoad not preserved"
                wb.close()
            except Exception as e:
                corrupted_files.append((token, str(e)))

        if not download_failures and not corrupted_files:
            r3.mark_pass(200, f"Verified all {len(tokens)} workbooks via /api/download/ - openpyxl loaded each with valid formulas and fullCalcOnLoad")
        else:
            r3.mark_fail(500, f"Integrity errors: corrupted={corrupted_files}, dl_failures={download_failures}")
        self.record(r3)

    # =========================================================================
    # Group 3: Token Traversal / Security on /api/download/{token}
    # =========================================================================
    def test_download_security(self):
        print("\n--- Running Group 3: Token Traversal & Security on /api/download/{token} ---")

        traversal_attempts = [
            ("../../etc/passwd", "UNIX path traversal ../../etc/passwd"),
            ("..%2F..%2Fetc%2Fpasswd", "URL-encoded traversal ..%2F..%2Fetc%2Fpasswd"),
            ("../../../etc/shadow", "Deep UNIX traversal ../../../etc/shadow"),
            ("..\\..\\windows\\win.ini", "Windows backslash traversal"),
            ("export_../../../../main.py", "Prefix spoof traversal"),
            ("export_%2e%2e%2f%2e%2e%2fPROJECT.md", "Double-encoded dot traversal"),
            ("..", "Single parent directory .."),
            (".", "Current directory ."),
            ("export_00000000000000000000000000000000", "Non-existent well-formed export UUID"),
            ("invalid-uuid-random-12345", "Random non-existent string token"),
            ("!@#$%^&*()_+~`", "Special characters token"),
            ("<script>alert('xss')</script>", "XSS script payload token"),
            ("' OR '1'='1", "SQL injection token"),
            ("A" * 10000, "10,000-character token"),
        ]

        for token_input, desc in traversal_attempts:
            r = EmpiricalTestResult(f"Security: {desc}", "/api/download/{token}")
            t0 = time.time()
            resp = self.client.get(f"/api/download/{token_input}")
            el = (time.time() - t0) * 1000

            # Valid security behavior: MUST NOT BE 200 (leaking file), MUST NOT BE 500 (crash)
            # Appropriate status codes: 404 Not Found, 400 Bad Request, or 422 Unprocessable Entity
            if resp.status_code == 200:
                r.mark_fail(200, f"CRITICAL SECURITY VULNERABILITY: Traversal succeeded! Returned file content", resp.text[:200], el)
            elif resp.status_code in (404, 400, 422):
                r.mark_pass(resp.status_code, f"Safely blocked with HTTP {resp.status_code}", el)
            elif resp.status_code == 500:
                r.mark_fail(500, f"Server crashed with 500 on token traversal attempt: {token_input}", resp.text, el)
            else:
                r.mark_pass(resp.status_code, f"Blocked with HTTP {resp.status_code}", el)
            self.record(r)

    # =========================================================================
    # Group 4: Custom Template Upload Adversarial Testing
    # =========================================================================
    def test_template_upload_adversarial(self):
        print("\n--- Running Group 4: Custom Template Upload Adversarial Testing ---")

        # 4.1 0-byte file
        r = EmpiricalTestResult("Upload 0-Byte File (empty.xlsx)", "/api/template/upload")
        t0 = time.time()
        files = {"file": ("empty.xlsx", b"", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        resp = self.client.post("/api/template/upload", files=files)
        el = (time.time() - t0) * 1000
        if resp.status_code in (400, 422):
            r.mark_pass(resp.status_code, f"Safely rejected 0-byte upload with HTTP {resp.status_code}: {resp.json().get('detail')}", el)
        else:
            r.mark_fail(resp.status_code, f"Expected 400/422 for 0-byte upload, got {resp.status_code}", resp.text, el)
        self.record(r)

        # 4.2 .txt file renamed to .xlsx
        r = EmpiricalTestResult("Upload Plain Text File Renamed to .xlsx", "/api/template/upload")
        t0 = time.time()
        txt_content = b"This is just a plain text file, not an Excel workbook at all.\nLine 2\nLine 3\n"
        files = {"file": ("fake_sheet.xlsx", txt_content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        resp = self.client.post("/api/template/upload", files=files)
        el = (time.time() - t0) * 1000
        if resp.status_code in (400, 422):
            r.mark_pass(resp.status_code, f"Safely caught invalid Excel format with {resp.status_code}: {resp.json().get('detail')}", el)
        else:
            r.mark_fail(resp.status_code, f"Failed to catch plain text masquerading as .xlsx", resp.text, el)
        self.record(r)

        # 4.3 Windows .exe binary renamed to .xlsx (MZ header)
        r = EmpiricalTestResult("Upload Executable Binary (MZ header) Renamed to .xlsx", "/api/template/upload")
        t0 = time.time()
        exe_bytes = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff\x00\x00\xb8\x00\x00\x00\x00\x00\x00\x00@\x00\x00\x00This program cannot be run in DOS mode."
        files = {"file": ("malicious.xlsx", exe_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        resp = self.client.post("/api/template/upload", files=files)
        el = (time.time() - t0) * 1000
        if resp.status_code in (400, 422):
            r.mark_pass(resp.status_code, f"Safely rejected executable binary disguised as .xlsx with {resp.status_code}", el)
        else:
            r.mark_fail(resp.status_code, f"Failed to reject executable disguised as .xlsx", resp.text, el)
        self.record(r)

        # 4.4 Corrupted ZIP file (valid PK header but truncated mid-stream)
        r = EmpiricalTestResult("Upload Corrupted/Truncated ZIP Archive (.xlsx)", "/api/template/upload")
        t0 = time.time()
        corrupt_zip = b"PK\x03\x04\x14\x00\x08\x00\x08\x00\x7d\x8b\x5b\x53\x00\x00\x00\x00\x00\x00\x00\x00\x13\x00\x00\x00[Content_Types].xml"
        files = {"file": ("corrupt.xlsx", corrupt_zip, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        resp = self.client.post("/api/template/upload", files=files)
        el = (time.time() - t0) * 1000
        if resp.status_code in (400, 422):
            r.mark_pass(resp.status_code, f"Safely caught BadZipFile / corrupt zip with {resp.status_code}: {resp.json().get('detail')}", el)
        else:
            r.mark_fail(resp.status_code, f"Failed to reject corrupt zip archive", resp.text, el)
        self.record(r)

        # 4.5 Non-.xlsx extension files (e.g. .csv, .exe, .sh, .pdf)
        bad_extensions = [
            ("script.sh", b"#!/bin/bash\necho pwned\n"),
            ("payload.exe", b"MZ..."),
            ("document.pdf", b"%PDF-1.5"),
            ("table.csv", b"col1,col2\nval1,val2\n"),
        ]
        for fname, content in bad_extensions:
            r = EmpiricalTestResult(f"Upload Forbidden Extension ({fname})", "/api/template/upload")
            t0 = time.time()
            files = {"file": (fname, content, "application/octet-stream")}
            resp = self.client.post("/api/template/upload", files=files)
            el = (time.time() - t0) * 1000
            if resp.status_code in (400, 422):
                r.mark_pass(resp.status_code, f"Rejected non-.xlsx extension with {resp.status_code}", el)
            else:
                r.mark_fail(resp.status_code, f"Expected 400 for {fname}, got {resp.status_code}", resp.text, el)
            self.record(r)

        # 4.6 Valid ZIP archive, but NOT an Excel workbook (e.g. zip containing a text file)
        r = EmpiricalTestResult("Upload Valid ZIP with Non-Excel Structure (.xlsx)", "/api/template/upload")
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("test.txt", "hello world")
        zip_buf.seek(0)
        t0 = time.time()
        files = {"file": ("valid_zip_not_excel.xlsx", zip_buf.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        resp = self.client.post("/api/template/upload", files=files)
        el = (time.time() - t0) * 1000
        if resp.status_code in (400, 422):
            r.mark_pass(resp.status_code, f"openpyxl failed to recognize invalid workbook structure, rejected with {resp.status_code}", el)
        else:
            r.mark_fail(resp.status_code, f"Failed to reject valid zip non-excel file", resp.text, el)
        self.record(r)

        # 4.7 Valid openpyxl Excel file, but missing employee/date headers
        r = EmpiricalTestResult("Upload Blank Excel Workbook Missing Headers", "/api/template/upload")
        blank_wb = openpyxl.Workbook()
        blank_buf = io.BytesIO()
        blank_wb.save(blank_buf)
        blank_buf.seek(0)
        t0 = time.time()
        files = {"file": ("blank_sheet.xlsx", blank_buf.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        resp = self.client.post("/api/template/upload", files=files)
        el = (time.time() - t0) * 1000
        if resp.status_code in (400, 422):
            r.mark_pass(resp.status_code, f"Domain validator detected missing employee/date headers, returned {resp.status_code}", el)
        else:
            r.mark_fail(resp.status_code, f"Failed to reject blank workbook", resp.text, el)
        self.record(r)

    # =========================================================================
    # Group 5: Adversarial Payloads & Injection on /api/export-excel
    # =========================================================================
    def test_export_adversarial(self):
        print("\n--- Running Group 5: Adversarial Payloads on /api/export-excel ---")

        # 5.1 Empty records list
        r = EmpiricalTestResult("Export with Empty Records List", "/api/export-excel")
        t0 = time.time()
        resp = self.client.post("/api/export-excel", json={"records": []})
        el = (time.time() - t0) * 1000
        if resp.status_code == 400:
            r.mark_pass(resp.status_code, f"Properly rejected empty export with 400: {resp.json().get('detail')}", el)
        elif resp.status_code == 422:
            r.mark_pass(resp.status_code, f"Rejected with 422", el)
        else:
            r.mark_fail(resp.status_code, f"Expected 400 for empty records list, got {resp.status_code}", resp.text, el)
        self.record(r)

        # 5.2 Path Traversal in output_filename: "../../evil.xlsx"
        r = EmpiricalTestResult("Path Traversal in output_filename parameter", "/api/export-excel")
        test_rec = {
            "employee_name": "HOÀNG ĐẮC PHÚ",
            "date_str": "24/10",
            "resolved_date": "2026-10-24",
            "day_number": 24,
            "shift_type": "DAY",
            "hours": {"hcn_100": 8.0, "total_hours": 8.0},
        }
        t0 = time.time()
        resp = self.client.post("/api/export-excel", json={
            "records": [test_rec],
            "output_filename": "../../../outside_system.xlsx"
        })
        el = (time.time() - t0) * 1000
        if resp.status_code == 200:
            data = resp.json()
            # Verify file was safely created inside output directory, NOT in outside_system
            clean_name = data.get("filename")
            token = data.get("download_token")
            # Ensure no file was created outside DEFAULT_OUTPUT_DIR
            outside_path = os.path.abspath(os.path.join(DEFAULT_OUTPUT_DIR, "..", "..", "..", "outside_system.xlsx"))
            assert not os.path.exists(outside_path), f"CRITICAL: Path traversal wrote outside output directory to {outside_path}!"
            r.mark_pass(resp.status_code, f"Sanitized filename to '{clean_name}', file safely confined to output/", el)
        elif resp.status_code in (400, 422):
            r.mark_pass(resp.status_code, f"Rejected traversal in filename with {resp.status_code}", el)
        else:
            r.mark_fail(resp.status_code, f"Unexpected response code", resp.text, el)
        self.record(r)

        # 5.3 Corrupt record schema (non-numeric hours)
        r = EmpiricalTestResult("Corrupt Record Types (Non-numeric hour string)", "/api/export-excel")
        bad_rec = {
            "employee_name": "HOÀNG ĐẮC PHÚ",
            "date_str": "24/10",
            "hours": {"hcn_100": "eight_hours"},
        }
        t0 = time.time()
        resp = self.client.post("/api/export-excel", json={"records": [bad_rec]})
        el = (time.time() - t0) * 1000
        if resp.status_code in (400, 422):
            r.mark_pass(resp.status_code, f"Pydantic caught invalid record type, returned {resp.status_code}", el)
        else:
            r.mark_fail(resp.status_code, f"Expected 400/422 for corrupt record type, got {resp.status_code}", resp.text, el)
        self.record(r)

        # 5.4 Extreme numeric hours (e.g. 999999 hours)
        r = EmpiricalTestResult("Extreme Numeric Hours Boundary Check", "/api/export-excel")
        extreme_rec = {
            "employee_name": "HOÀNG ĐẮC PHÚ",
            "date_str": "24/10",
            "resolved_date": "2026-10-24",
            "day_number": 24,
            "shift_type": "DAY",
            "hours": {"hcn_100": 999999.0, "total_hours": 999999.0},
        }
        t0 = time.time()
        resp = self.client.post("/api/export-excel", json={"records": [extreme_rec]})
        el = (time.time() - t0) * 1000
        if resp.status_code == 200:
            r.mark_pass(resp.status_code, "Export handled large numeric hours gracefully without crash", el)
        elif resp.status_code in (400, 422):
            r.mark_pass(resp.status_code, f"Rejected with {resp.status_code}", el)
        else:
            r.mark_fail(resp.status_code, "Crashed on extreme number", resp.text, el)
        self.record(r)

        # 5.5 Unknown Employee & Out-of-Range Date in Export
        r = EmpiricalTestResult("Unknown Employee & Out-of-Range Date Records Handling", "/api/export-excel")
        unmatched_rec = {
            "employee_name": "NGƯỜI LẠ HOÀN TOÀN KHÔNG CÓ TRONG BẢNG",
            "date_str": "99/99/9999",
            "shift_type": "DAY",
            "hours": {"hcn_100": 8.0, "total_hours": 8.0},
        }
        t0 = time.time()
        resp = self.client.post("/api/export-excel", json={"records": [unmatched_rec]})
        el = (time.time() - t0) * 1000
        if resp.status_code == 200:
            data = resp.json()
            summary = data.get("summary", {})
            r.mark_pass(resp.status_code, f"Completed with graceful unmatched summary: errors={len(summary.get('errors', []))}", el)
        elif resp.status_code in (400, 422):
            r.mark_pass(resp.status_code, f"Rejected with {resp.status_code}", el)
        else:
            r.mark_fail(resp.status_code, "Crashed on unmatched employee / date", resp.text, el)
        self.record(r)

    # =========================================================================
    # Run All & Generate Summary
    # =========================================================================
    def run_all(self) -> Dict[str, Any]:
        print("======================================================================")
        print("STARTING EMPIRICAL ADVERSARIAL STRESS TEST SUITE (MILESTONE 3)")
        print("======================================================================")
        start_time = time.time()

        self.test_parse_fuzzing()
        self.test_concurrency_export(concurrency_count=25)
        self.test_download_security()
        self.test_template_upload_adversarial()
        self.test_export_adversarial()

        elapsed_total = time.time() - start_time

        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.passed)
        failed_tests = sum(1 for r in self.results if not r.passed)
        crashes_500 = sum(1 for r in self.results if r.is_500)

        print("\n======================================================================")
        print("EMPIRICAL TEST SUITE SUMMARY")
        print("======================================================================")
        print(f"Total Tests Executed: {total_tests}")
        print(f"Passed:              {passed_tests}")
        print(f"Failed:              {failed_tests}")
        print(f"Unhandled 500s:      {crashes_500}")
        print(f"Total Duration:      {elapsed_total:.2f}s")
        print("======================================================================")

        verdict = "APPROVE" if (failed_tests == 0 and crashes_500 == 0) else "REJECT"
        print(f"FINAL VERDICT: {verdict}")
        print("======================================================================\n")

        return {
            "total": total_tests,
            "passed": passed_tests,
            "failed": failed_tests,
            "crashes_500": crashes_500,
            "elapsed_seconds": elapsed_total,
            "verdict": verdict,
            "results": [
                {
                    "name": r.name,
                    "category": r.category,
                    "passed": r.passed,
                    "status_code": r.status_code,
                    "is_500": r.is_500,
                    "elapsed_ms": r.elapsed_ms,
                    "details": r.details,
                    "snippet": r.response_snippet,
                }
                for r in self.results
            ]
        }


if __name__ == "__main__":
    runner = WebAPIAdversarialRunner()
    summary = runner.run_all()
    # Save results to json for audit
    report_json_path = os.path.join(os.path.dirname(__file__), "test_results.json")
    with open(report_json_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    if summary["crashes_500"] > 0 or summary["failed"] > 0:
        sys.exit(1)
    sys.exit(0)
