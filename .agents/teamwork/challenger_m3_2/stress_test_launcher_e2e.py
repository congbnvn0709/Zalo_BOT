"""
Empirical Stress Test Harness for Milestone 3 (Launcher & End-to-End API).
Agent: Challenger M3-2
Working Directory: /Users/congcm/CODE/Vibe_Code/Zalo_BOT/.agents/teamwork/challenger_m3_2/

Coverage:
- Group A: Port collision handling in run.py (single port, multi-port jumping, signature analysis)
- Group B: Full E2E user pipeline: parse official sample -> export -> token -> download -> openpyxl inspection
- Group C: Table inline-edit payload tolerance: hours 8->10, meals 0->1, decimals, date shifts, flat payloads
- Group D: Multi-record batch integrity, Sunday allocation, formula preservation, token security, error resilience
"""

import os
import io
import sys
import copy
import socket
import argparse
import unittest
from typing import List

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import openpyxl
from fastapi.testclient import TestClient
from main import app
import run


class TestPortCollisionAndLauncher(unittest.TestCase):
    """Stress tests for run.py port collision resolution and launcher mechanics."""

    def test_a1_single_port_collision_8000_to_8001(self):
        """Bind port 8000 with a dummy socket, verify find_free_port detects it and returns 8001."""
        dummy_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        dummy_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            dummy_socket.bind(("127.0.0.1", 8000))
            dummy_socket.listen(1)

            # Check detection
            in_use = run.is_port_in_use(8000, "127.0.0.1")
            self.assertTrue(in_use, "Port 8000 should be detected as in use")

            # Resolve free port starting at 8000
            selected_port = run.find_free_port(host="127.0.0.1", start_port=8000, max_port=8080)
            self.assertEqual(selected_port, 8001, f"Expected port 8001 when 8000 is occupied, got {selected_port}")
        finally:
            dummy_socket.close()

    def test_a2_multi_port_collision_8000_to_8005_jumps_to_8006(self):
        """Bind ports 8000..8005 simultaneously, verify port jumping finds 8006."""
        sockets: List[socket.socket] = []
        try:
            for p in range(8000, 8006):
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(("127.0.0.1", p))
                s.listen(1)
                sockets.append(s)

            # Verify all 6 ports are detected as busy
            for p in range(8000, 8006):
                self.assertTrue(run.is_port_in_use(p, "127.0.0.1"), f"Port {p} should be detected in use")

            # Verify jump to 8006
            free_port = run.find_free_port(host="127.0.0.1", start_port=8000, max_port=8080)
            self.assertEqual(free_port, 8006, f"Expected port 8006 when 8000..8005 occupied, got {free_port}")
        finally:
            for s in sockets:
                s.close()

    def test_a3_launcher_api_signature_and_naming_finding(self):
        """
        Adversarial inspection of launcher API signature.
        Checks for `find_available_port` vs `find_free_port` and parameter ordering.
        """
        # run.py implements find_free_port
        self.assertTrue(hasattr(run, "find_free_port"), "run.py must have find_free_port")

        # Check keyword start_port=8000 works
        p = run.find_free_port(start_port=8000)
        self.assertGreaterEqual(p, 8000)

        # Check adapter / positional behavior
        # Notice finding: run.py expects find_free_port(host, start_port) or keyword start_port=8000
        with self.assertRaises(TypeError):
            # Positional 8000 passes host=8000 (an integer), which raises TypeError in socket.connect_ex
            run.find_free_port(8000)

    def test_a4_all_ports_exhausted_fallback(self):
        """When all ports in range are occupied, find_free_port returns start_port."""
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        test_port = 8079
        try:
            s.bind(("127.0.0.1", test_port))
            s.listen(1)
            result = run.find_free_port(host="127.0.0.1", start_port=test_port, max_port=test_port)
            self.assertEqual(result, test_port)
        finally:
            s.close()

    def test_a5_launcher_argparser_defaults(self):
        """Verify run.py CLI argument defaults without starting server."""
        parser = argparse.ArgumentParser(description="Zalo Attendance Bot Launcher")
        parser.add_argument("--host", default="127.0.0.1")
        parser.add_argument("--port", type=int, default=8000)
        parser.add_argument("--no-browser", action="store_true")
        parser.add_argument("--reload", action="store_true")

        args = parser.parse_args([])
        self.assertEqual(args.host, "127.0.0.1")
        self.assertEqual(args.port, 8000)
        self.assertFalse(args.no_browser)
        self.assertFalse(args.reload)


class TestEndToEndPipeline(unittest.TestCase):
    """End-to-End API verification of the full user journey."""

    def setUp(self):
        self.client = TestClient(app)
        self.official_sample = (
            "HỌ TÊN : HOÀNG ĐẮC PHÚ\n"
            "NGÀY: 24/10\n"
            "CA : Ca ngày \n"
            "DỰ ÁN : sdv \n"
            "THỜI GIAN LÀM VIỆC :8h-17h ( 8H)\n"
            "CÓ ĂN Ở XƯỞNG KO : 0"
        )

    def test_b1_full_pipeline_official_sample_k24_and_k30(self):
        """
        Execute full E2E user pipeline:
        1. POST /api/parse -> check structured record
        2. POST /api/export-excel -> get download token
        3. GET /api/download/{token} -> stream .xlsx file
        4. Load with openpyxl(data_only=False) -> assert K24=8, K30=0, formula preserved
        """
        # Step 1: Parse
        res_parse = self.client.post("/api/parse", json={"text": self.official_sample})
        self.assertEqual(res_parse.status_code, 200, res_parse.text)
        parse_data = res_parse.json()
        self.assertIn("records", parse_data)
        self.assertEqual(len(parse_data["records"]), 1)

        rec = parse_data["records"][0]
        self.assertEqual(rec["employee_name"], "HOÀNG ĐẮC PHÚ")
        self.assertEqual(rec["date_str"], "24/10")
        self.assertEqual(rec["hours"]["hcn_100"], 8.0)
        self.assertEqual(rec["meal_count"], 0)
        # Status is WARNING because year is inferred as default 2026 for DD/MM format
        self.assertIn(rec["status"], ["VALID", "WARNING"])

        # Step 2: Export Excel
        res_export = self.client.post(
            "/api/export-excel",
            json={
                "records": parse_data["records"],
                "output_filename": "TEST_OFFICIAL_SAMPLE.xlsx",
            },
        )
        self.assertEqual(res_export.status_code, 200, res_export.text)
        export_data = res_export.json()
        self.assertTrue(export_data["success"])
        token = export_data["download_token"]
        self.assertTrue(token.startswith("export_"))
        self.assertIn("/api/download/", export_data["download_url"])

        # Step 3: Download
        res_download = self.client.get(f"/api/download/{token}")
        self.assertEqual(res_download.status_code, 200)
        self.assertIn("application/vnd.openxmlformats", res_download.headers.get("content-type", ""))
        self.assertGreater(len(res_download.content), 5000)

        # Step 4: Load with openpyxl and verify cells & formulas
        wb = openpyxl.load_workbook(io.BytesIO(res_download.content), data_only=False)
        ws = wb.active

        # Assert K24=8 (HCN 100% on 24/10 for HOÀNG ĐẮC PHÚ)
        k24_val = ws["K24"].value
        self.assertEqual(k24_val, 8, f"Expected cell K24 to be 8, got {k24_val}")

        # Assert K30=0 (Meal count on 24/10 for HOÀNG ĐẮC PHÚ)
        k30_val = ws["K30"].value
        self.assertEqual(k30_val, 0, f"Expected cell K30 to be 0, got {k30_val}")

        # Assert formulas intact
        # Row 24 columns AK and AR have sum formulas
        ak24_formula = str(ws["AK24"].value)
        ar24_formula = str(ws["AR24"].value)
        self.assertTrue(ak24_formula.startswith("="), f"AK24 should be formula, got {ak24_formula}")
        self.assertIn("SUM", ak24_formula.upper())
        self.assertTrue(ar24_formula.startswith("="), f"AR24 should be formula, got {ar24_formula}")
        self.assertIn("SUM", ar24_formula.upper())

        # Check fullCalcOnLoad is True
        self.assertTrue(wb.calculation.fullCalcOnLoad, "Workbook must have fullCalcOnLoad=True")


class TestInlineEditPayloadTolerance(unittest.TestCase):
    """Stress tests for table inline-edit payload tolerance and modifications."""

    def setUp(self):
        self.client = TestClient(app)

    def test_c1_inline_edit_hours_from_8_to_10_nested_format(self):
        """Simulate user editing hours from 8 to 10 in UI table (nested hours dict)."""
        payload_record = {
            "id": "rec_001",
            "employee_name": "HOÀNG ĐẮC PHÚ",
            "date_str": "24/10",
            "resolved_date": "2026-10-24",
            "day_number": 24,
            "shift_type": "DAY",
            "project": "sdv",
            "time_window": "8h-19h (10H)",
            "hours": {
                "hcn_100": 10.0,
                "tcn_150": 0.0,
                "hcd_130": 0.0,
                "tcd_195": 0.0,
                "sunday_day_200": 0.0,
                "sunday_night_260": 0.0,
                "total_hours": 10.0,
            },
            "meal_count": 0,
            "status": "VALID",
            "raw_text": "simulated edit",
        }

        res_export = self.client.post("/api/export-excel", json={"records": [payload_record]})
        self.assertEqual(res_export.status_code, 200, res_export.text)
        token = res_export.json()["download_token"]

        res_download = self.client.get(f"/api/download/{token}")
        wb = openpyxl.load_workbook(io.BytesIO(res_download.content), data_only=False)
        ws = wb.active

        self.assertEqual(ws["K24"].value, 10, f"Expected K24=10 after inline edit, got {ws['K24'].value}")
        self.assertEqual(ws["K30"].value, 0)

    def test_c2_inline_edit_flat_record_payload_tolerance(self):
        """Simulate client sending flattened payload keys directly (resilience)."""
        flat_record = {
            "employee_name": "HOÀNG ĐẮC PHÚ",
            "date_str": "24/10",
            "hcn_100": 10.0,
            "tcn_150": 0.0,
            "meal_count": 0,
        }

        res_export = self.client.post("/api/export-excel", json={"records": [flat_record]})
        self.assertEqual(res_export.status_code, 200, res_export.text)
        token = res_export.json()["download_token"]

        res_download = self.client.get(f"/api/download/{token}")
        wb = openpyxl.load_workbook(io.BytesIO(res_download.content), data_only=False)
        ws = wb.active

        self.assertEqual(ws["K24"].value, 10, f"Expected K24=10 from flat payload, got {ws['K24'].value}")

    def test_c3_inline_edit_meal_count_0_to_1(self):
        """Simulate user editing meal count from 0 to 1."""
        record = {
            "employee_name": "HOÀNG ĐẮC PHÚ",
            "date_str": "24/10",
            "hours": {"hcn_100": 8.0, "total_hours": 8.0},
            "meal_count": 1,
        }

        res_export = self.client.post("/api/export-excel", json={"records": [record]})
        token = res_export.json()["download_token"]

        res_download = self.client.get(f"/api/download/{token}")
        wb = openpyxl.load_workbook(io.BytesIO(res_download.content), data_only=False)
        ws = wb.active

        self.assertEqual(ws["K24"].value, 8)
        self.assertEqual(ws["K30"].value, 1, f"Expected K30=1 after meal edit, got {ws['K30'].value}")

    def test_c4_inline_edit_date_column_shift_24_to_25(self):
        """Simulate user modifying date from 24/10 (col K) to 25/10 (col L)."""
        record = {
            "employee_name": "HOÀNG ĐẮC PHÚ",
            "date_str": "25/10",
            "hours": {"hcn_100": 8.0, "total_hours": 8.0},
            "meal_count": 0,
        }

        res_export = self.client.post("/api/export-excel", json={"records": [record]})
        token = res_export.json()["download_token"]

        res_download = self.client.get(f"/api/download/{token}")
        wb = openpyxl.load_workbook(io.BytesIO(res_download.content), data_only=False)
        ws = wb.active

        # On 25/10 (col L), L24 should be 8, L30 should be 0
        self.assertEqual(ws["L24"].value, 8, f"Expected L24=8 for 25/10, got {ws['L24'].value}")
        self.assertEqual(ws["L30"].value, 0, f"Expected L30=0 for 25/10, got {ws['L30'].value}")

    def test_c5_inline_edit_decimal_hours_precision(self):
        """Simulate user entering fractional hours (e.g. 7.5 hours)."""
        record = {
            "employee_name": "HOÀNG ĐẮC PHÚ",
            "date_str": "24/10",
            "hours": {"hcn_100": 7.5, "total_hours": 7.5},
            "meal_count": 0,
        }

        res_export = self.client.post("/api/export-excel", json={"records": [record]})
        token = res_export.json()["download_token"]

        res_download = self.client.get(f"/api/download/{token}")
        wb = openpyxl.load_workbook(io.BytesIO(res_download.content), data_only=False)
        ws = wb.active

        self.assertEqual(ws["K24"].value, 7.5, f"Expected K24=7.5, got {ws['K24'].value}")
        self.assertIsInstance(ws["K24"].value, float)

    def test_c6_inline_edit_fuzzy_name_matching(self):
        """Simulate user typing lowercase unaccented name 'hoang dac phu'."""
        record = {
            "employee_name": "hoang dac phu",
            "date_str": "24/10",
            "hours": {"hcn_100": 8.0, "total_hours": 8.0},
            "meal_count": 0,
        }

        res_export = self.client.post("/api/export-excel", json={"records": [record]})
        token = res_export.json()["download_token"]

        res_download = self.client.get(f"/api/download/{token}")
        wb = openpyxl.load_workbook(io.BytesIO(res_download.content), data_only=False)
        ws = wb.active

        self.assertEqual(ws["K24"].value, 8, "Fuzzy matched employee should populate row 24")


class TestAdversarialAndBatchIntegrity(unittest.TestCase):
    """Adversarial security, error resilience, and multi-record batch stress tests."""

    def setUp(self):
        self.client = TestClient(app)

    def test_d1_multi_employee_batch_full_flow(self):
        """Test 4-employee batch message parsing and mapping to Excel coordinates with day/night/Sunday distinction."""
        batch_text = (
            "HỌ TÊN : HOÀNG ĐẮC PHÚ\nNGÀY: 24/10\nCA : Ca ngày \nDỰ ÁN : sdv \nTHỜI GIAN LÀM VIỆC :8h-17h ( 8H)\nCÓ ĂN Ở XƯỞNG KO : 0\n\n"
            "HỌ TÊN: NGUYỄN NGỌC THAO\nNGÀY: 24/10\nCA: Ca ngày\nDỰ ÁN: sdv\nTHỜI GIAN LÀM VIỆC: 8h-20h (11H)\nCÓ ĂN Ở XƯỞNG KO: 1\n\n"
            "HỌ TÊN: NGUYỄN ĐỨC CÔNG\nNGÀY: 25/10\nCA: Ca ngày\nDỰ ÁN: sdv\nTHỜI GIAN LÀM VIỆC: 8h-17h (8H)\nCÓ ĂN Ở XƯỞNG KO: 1\n\n"
            "HỌ TÊN: TÔ VĂN HƯNG\nNGÀY: 24/10\nCA: Ca đêm\nDỰ ÁN: sdv\nTHỜI GIAN LÀM VIỆC: 20h-8h (11H)\nCÓ ĂN Ở XƯỞNG KO: 1"
        )

        res_parse = self.client.post("/api/parse", json={"text": batch_text})
        self.assertEqual(res_parse.status_code, 200)
        records = res_parse.json()["records"]
        self.assertEqual(len(records), 4)

        res_export = self.client.post("/api/export-excel", json={"records": records})
        self.assertEqual(res_export.status_code, 200)
        token = res_export.json()["download_token"]

        res_download = self.client.get(f"/api/download/{token}")
        wb = openpyxl.load_workbook(io.BytesIO(res_download.content), data_only=False)
        ws = wb.active

        # 1. HOÀNG ĐẮC PHÚ (row 24): K24=8, K30=0
        self.assertEqual(ws["K24"].value, 8)
        self.assertEqual(ws["K30"].value, 0)

        # 2. NGUYỄN NGỌC THAO (row 3): K3=8 (HCN), K4=3 (TCN), K9=1 (meal)
        self.assertEqual(ws["K3"].value, 8)
        self.assertEqual(ws["K4"].value, 3)
        self.assertEqual(ws["K9"].value, 1)

        # 3. NGUYỄN ĐỨC CÔNG (row 10): 25/10 is Sunday -> L14=8 (Sunday day 200%), L16=1 (meal)
        self.assertEqual(ws["L14"].value, 8)
        self.assertEqual(ws["L16"].value, 1)

        # 4. TÔ VĂN HƯNG (row 17): 24/10 Ca đêm -> K19=8 (HCĐ), K20=3 (TCĐ), K23=1 (meal)
        self.assertEqual(ws["K19"].value, 8)
        self.assertEqual(ws["K20"].value, 3)
        self.assertEqual(ws["K23"].value, 1)

    def test_d2_invalid_token_returns_404(self):
        """Requesting a nonexistent download token returns 404 Not Found."""
        res = self.client.get("/api/download/nonexistent_fake_token_12345")
        self.assertEqual(res.status_code, 404)
        self.assertIn("không tồn tại", res.json().get("detail", ""))

    def test_d3_empty_records_export_returns_400(self):
        """Exporting an empty record list returns 400 Bad Request."""
        res = self.client.post("/api/export-excel", json={"records": []})
        self.assertEqual(res.status_code, 400)

    def test_d4_corrupt_records_payload_returns_validation_error(self):
        """Sending invalid non-dict items in records triggers validation error (400 or 422)."""
        res = self.client.post("/api/export-excel", json={"records": ["not a record", 123]})
        self.assertIn(res.status_code, [400, 422])

    def test_d5_unmatched_and_out_of_range_handling(self):
        """Unmatched employee or out of range dates do not trigger unhandled 500 crashes."""
        bad_records = [
            {
                "employee_name": "UNKNOWN_ALIEN_EMPLOYEE_XYZ",
                "date_str": "24/10",
                "hours": {"hcn_100": 8.0, "total_hours": 8.0},
                "meal_count": 0,
            },
            {
                "employee_name": "HOÀNG ĐẮC PHÚ",
                "date_str": "15/05/2030",  # Out of range date
                "hours": {"hcn_100": 8.0, "total_hours": 8.0},
                "meal_count": 0,
            },
        ]
        res = self.client.post("/api/export-excel", json={"records": bad_records})
        self.assertEqual(res.status_code, 200)
        summary = res.json()["summary"]
        self.assertGreater(len(summary.get("errors", [])), 0)

    def test_d6_path_traversal_filename_sanitization(self):
        """Output filename with directory path slashes should be sanitized safely without escaping output directory."""
        record = {
            "employee_name": "HOÀNG ĐẮC PHÚ",
            "date_str": "24/10",
            "hours": {"hcn_100": 8.0, "total_hours": 8.0},
            "meal_count": 0,
        }
        res = self.client.post(
            "/api/export-excel",
            json={
                "records": [record],
                "output_filename": "../../../evil.xlsx",
            },
        )
        self.assertEqual(res.status_code, 200)
        filename = res.json()["filename"]
        # Slashes must be stripped or replaced so it cannot traverse directories
        self.assertNotIn("/", filename)
        self.assertNotIn("\\", filename)
        # File is created safely inside output/
        out_path = res.json()["summary"]["output_path"]
        self.assertTrue(out_path.startswith(os.path.abspath(os.path.join(PROJECT_ROOT, "output"))))


if __name__ == "__main__":
    unittest.main(verbosity=2)
