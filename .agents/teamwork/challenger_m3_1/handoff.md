# Adversarial Challenge Report — Milestone 3 Web API Hardening

**Agent**: `challenger_m3_1`  
**Working Directory**: `/Users/congcm/CODE/Vibe_Code/Zalo_BOT/.agents/teamwork/challenger_m3_1/`  
**Verdict**: **APPROVE**  
**Date**: 2026-10-26T09:42:00Z  

---

## 1. Observation

Direct empirical observations from executing adversarial tests against the FastAPI REST API (`main.py` and `api/routes.py`):

1. **Test Suite Execution Command & Result**:
   ```bash
   .venv/bin/python .agents/teamwork/challenger_m3_1/stress_test_web_api.py
   ```
   Output:
   ```text
   ======================================================================
   EMPIRICAL TEST SUITE SUMMARY
   ======================================================================
   Total Tests Executed: 43
   Passed:              43
   Failed:              0
   Unhandled 500s:      0
   Total Duration:      1.40s
   ======================================================================
   FINAL VERDICT: APPROVE
   ======================================================================
   ```

2. **Full Regression Test Suite Command & Result**:
   ```bash
   .venv/bin/pytest
   ```
   Output:
   ```text
   ======================== 268 passed, 1 warning in 0.89s ========================
   ```

3. **Fuzzing & Payload Robustness on `/api/parse`**:
   - **100,000-character repetitive payload**: Handled in `67.7ms`, successfully parsed 991 records with HTTP 200 without hanging.
   - **100,000-character unsegmented single-line noise**: Handled in `16.7ms` with HTTP 200, proving no catastrophic regex backtracking (ReDoS) exists in `split_messages` or field lookahead regexes.
   - **Non-UTF8 / Corrupt binary payload**: Sending raw bytes `b'{"text": "\xff\xfe\x00\x41\x42\x43\x80\x81\x82"}'` returned clean `HTTP 400 Bad Request` in `2.6ms`. Zero unhandled 500 crashes.
   - **Malformed JSON payloads**: Truncated JSON returned `HTTP 422`, and syntax errors returned `HTTP 422`.
   - **Null and empty values**: `{"text": ""}`, `{"text": null, "raw_text": null}`, and `{}` all returned `HTTP 200` with an empty record array (`records: []`, `summary: {total: 0, valid: 0, warning: 0, error: 0}`).
   - **Schema type violations**: Objects and invalid types for strings/integers were cleanly caught by Pydantic v2 with `HTTP 422 Unprocessable Entity`.
   - **Zalgo / RTL / Emoji bomb**: Processed in `2.5ms` with `HTTP 200` without encoding crash or buffer overrun.

4. **Concurrency & Race Conditions on `/api/export-excel`**:
   - **25 concurrent threads** dispatched simultaneously against `POST /api/export-excel` completed in `710.1ms`.
   - **HTTP Status**: 25 out of 25 returned `HTTP 200 OK` (0 failures, 0 crashes).
   - **Token Uniqueness**: Generated 25 strictly unique download tokens (`export_<hex_uuid>`). Zero collisions observed (`len(set(tokens)) == 25`).
   - **File Isolation & Integrity**: Verified all 25 output workbooks independently via `GET /api/download/{token}`. Every downloaded file was inspected in memory using `openpyxl.load_workbook(..., data_only=False)`. All workbooks contained valid XML sheets, valid numerical cell allocations, preserved formulas (`AK..AR` and row 2), and `wb.calculation.fullCalcOnLoad = True`.

5. **Token Traversal & Download Endpoint Security on `/api/download/{token}`**:
   - Tested 14 traversal and injection payloads:
     * `../../etc/passwd` -> `HTTP 404` (blocked)
     * `..%2F..%2Fetc%2Fpasswd` -> `HTTP 404` (blocked)
     * `../../../etc/shadow` -> `HTTP 404` (blocked)
     * `..\\..\\windows\\win.ini` -> `HTTP 404` (blocked)
     * `export_../../../../main.py` -> `HTTP 404` (blocked)
     * `export_%2e%2e%2f%2e%2e%2fPROJECT.md` -> `HTTP 404` (blocked)
     * `export_00000000000000000000000000000000` (non-existent UUID) -> `HTTP 404`
     * Injection strings (`<script>alert(1)</script>`, `' OR '1'='1`, `!@#$%^&*()`) -> `HTTP 404`
     * 10,000-character oversized token -> `HTTP 404`
   - Zero sensitive server files were accessed or returned. Zero 500 server crashes.

6. **Custom Template Upload Adversarial Vectors (`POST /api/template/upload`)**:
   - **0-byte file (`empty.xlsx`)**: Returned `HTTP 400 Bad Request` (`detail: "Lỗi khi đọc file mẫu Excel: File is not a zip file"`).
   - **Plain text renamed to `.xlsx` (`fake_sheet.xlsx`)**: Returned `HTTP 400 Bad Request`.
   - **Windows executable binary (`malicious.xlsx` with MZ header)**: Returned `HTTP 400 Bad Request`.
   - **Corrupted / truncated ZIP archive (`corrupt.xlsx`)**: Returned `HTTP 400 Bad Request`.
   - **Forbidden extensions (`.sh`, `.exe`, `.pdf`, `.csv`)**: Rejected with `HTTP 400 Bad Request`.
   - **Valid ZIP without Excel structure**: Rejected with `HTTP 400 Bad Request`.
   - **Blank Excel workbook missing headers**: Caught by domain validator and rejected with `HTTP 400 Bad Request`.
   - **Path traversal in filename (`../../outside.xlsx`)**: Handled safely with `HTTP 400 Bad Request`.
   - **Filesystem Cleanup Verification**: Confirmed that all invalid upload attempts unlinked and deleted their temporary files in `templates_excel/uploaded/` inside the `except Exception` cleanup block; no orphan files remained.

7. **Export Adversarial Payloads (`POST /api/export-excel`)**:
   - **Empty records list (`{"records": []}`)**: Returned `HTTP 400 Bad Request`.
   - **Path traversal in `output_filename` (`"../../../outside_system.xlsx"`)**: Sanitized by regex `re.sub(r'[^a-zA-Z0-9_\-\. ]', '_', raw_fname)` to `".._.._.._outside_system.xlsx"`, strictly confined to `output/` directory (`assert not os.path.exists("../../../outside_system.xlsx")` passed).
   - **Corrupt / non-numeric hour types**: Rejected with `HTTP 400` / `HTTP 422`.
   - **Large numeric hours (999,999.0)**: Processed safely without overflow.
   - **Unmatched employee & date out of range**: Safely aggregated into summary errors array with `HTTP 200`, zero server crashes.

---

## 2. Logic Chain

1. **Requirement Check**:
   - The user dispatch instructed to stress-test `/api/parse`, `/api/export-excel`, `/api/download/{token}`, and `/api/template/upload` with adversarial inputs, concurrency, token traversal, and corrupt file uploads.
   - Requirement specified: zero 500 unhandled crashes, appropriate 400/404/422 status codes, and non-colliding Excel generation.

2. **Empirical Validation**:
   - An independent adversarial test suite (`stress_test_web_api.py`) containing 43 dedicated attack scenarios was written and executed directly against the application endpoints via FastAPI `TestClient`.
   - In all 43 scenarios, the API behaved strictly according to specification:
     * Non-UTF8, invalid JSON, and missing mandatory fields returned client-side error codes (`400 Bad Request` or `422 Unprocessable Entity`).
     * Traversal tokens and unknown tokens returned `404 Not Found`.
     * High-volume concurrency (25 threads) produced 25 independent files with 0 collisions and 100% data integrity verified by openpyxl.
     * All corrupt file uploads were caught, rejected with `400 Bad Request`, and immediately scrubbed from disk.
     * Crucially, exactly zero unhandled 500 exceptions occurred (`crashes_500 == 0`).

3. **Regression Safety**:
   - The entire regression test suite of 268 tests in `tests/` passed in `0.89s` with zero errors.

4. **Conclusion Derivation**:
   - Because all empirical adversarial challenges passed without a single failure or unhandled 500 crash, the Web API implementation meets the robustness and security criteria for Milestone 3.

---

## 3. Caveats

- Tests were run on macOS environment using Python 3.11 with FastAPI `TestClient` (Starlette ASGI transport).
- Hardware network disconnection mid-stream was not tested at the TCP socket layer (out of scope for ASGI application testing).
- Long-term memory accumulation under continuous multi-day uptime was not evaluated, though memory cleanup after each openpyxl load and workbook close was verified.

---

## 4. Conclusion

**VERDICT: APPROVE**

The FastAPI REST API endpoints in `main.py` and `api/routes.py` are robust, concurrency-safe, resilient against malformed/fuzzed inputs, secure against path traversal, and maintain zero unhandled 500 crashes across all test dimensions.

---

## 5. Verification Method

To independently reproduce and verify this assessment:

1. **Run the Empirical Adversarial Challenge Suite**:
   ```bash
   cd /Users/congcm/CODE/Vibe_Code/Zalo_BOT
   .venv/bin/python .agents/teamwork/challenger_m3_1/stress_test_web_api.py
   ```
   *Expected Output*: Exit code `0`, `Total Tests Executed: 43`, `Passed: 43`, `Failed: 0`, `Unhandled 500s: 0`, `FINAL VERDICT: APPROVE`.

2. **Inspect Detailed JSON Test Results**:
   ```bash
   cat /Users/congcm/CODE/Vibe_Code/Zalo_BOT/.agents/teamwork/challenger_m3_1/test_results.json
   ```

3. **Run Existing Full Project Test Suite**:
   ```bash
   .venv/bin/pytest
   ```
   *Expected Output*: Exit code `0`, `268 passed`.
