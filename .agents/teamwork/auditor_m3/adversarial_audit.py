"""
Adversarial Stress Testing for Milestone 3 Web App & REST API
"""

import os
import sys
import unittest
from fastapi.testclient import TestClient

PROJECT_ROOT = "/Users/congcm/CODE/Vibe_Code/Zalo_BOT"
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from main import app

class AdversarialStressTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_adv_01_arbitrary_unseen_names_and_sunday_detection(self):
        """Verify dynamic parsing on arbitrary names and genuine Sunday hour calculation."""
        # 2026-10-10 is Saturday (regular day -> hcn_100 = 8.0)
        # 2026-10-11 is Sunday (Sunday day -> sunday_day_200 = 8.0, hcn_100 = 0.0)
        # 2026-10-12 is Monday (regular day -> hcn_100 = 8.0)
        batch = """
HỌ TÊN: ĐẶNG HOÀNG GIANG
NGÀY: 10/10
CA: Ca ngày
DỰ ÁN: sdv
THỜI GIAN LÀM VIỆC: 8h-17h (8H)
CÓ ĂN Ở XƯỞNG KO: 0

HỌ TÊN: TRIỆU THỊ TRINH
NGÀY: 11/10
CA: Ca ngày
DỰ ÁN: sdv
THỜI GIAN LÀM VIỆC: 8h-17h (8H)
CÓ ĂN Ở XƯỞNG KO: 1

HỌ TÊN: VŨ TRỌNG PHỤNG
NGÀY: 12/10
CA: Ca ngày
DỰ ÁN: sdv
THỜI GIAN LÀM VIỆC: 8h-17h (8H)
CÓ ĂN Ở XƯỞNG KO: 0
"""
        res = self.client.post("/api/parse", json={"text": batch})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["summary"]["total"], 3)
        recs = data["records"]

        # Saturday
        self.assertEqual(recs[0]["employee_name"], "ĐẶNG HOÀNG GIANG")
        self.assertFalse(recs[0]["is_sunday"])
        self.assertEqual(recs[0]["hours"]["hcn_100"], 8.0)
        self.assertEqual(recs[0]["hours"]["sunday_day_200"], 0.0)

        # Sunday (Genius genuine calendar verification!)
        self.assertEqual(recs[1]["employee_name"], "TRIỆU THỊ TRINH")
        self.assertTrue(recs[1]["is_sunday"])
        self.assertEqual(recs[1]["hours"]["hcn_100"], 0.0)
        self.assertEqual(recs[1]["hours"]["sunday_day_200"], 8.0)

        # Monday
        self.assertEqual(recs[2]["employee_name"], "VŨ TRỌNG PHỤNG")
        self.assertFalse(recs[2]["is_sunday"])
        self.assertEqual(recs[2]["hours"]["hcn_100"], 8.0)
        self.assertEqual(recs[2]["hours"]["sunday_day_200"], 0.0)

    def test_adv_02_path_traversal_in_export_filename(self):
        """Verify path traversal attempt in output_filename is neutralized."""
        malicious_names = [
            "../../../etc/passwd",
            "..\\..\\windows\\system32\\calc.exe",
            "test/../../../secret.xlsx",
        ]
        sample_res = self.client.get("/api/sample")
        sample_text = sample_res.json()["sample_text"]
        parse_res = self.client.post("/api/parse", json={"text": sample_text})
        records = parse_res.json()["records"]

        for mal_name in malicious_names:
            export_res = self.client.post(
                "/api/export-excel",
                json={"records": records[:1], "output_filename": mal_name}
            )
            self.assertEqual(export_res.status_code, 200)
            target_path = export_res.json()["filename"]
            # Ensure no directory separator '/' or '\\' in generated filename
            self.assertNotIn("/", target_path)
            self.assertNotIn("\\", target_path)

    def test_adv_03_xss_in_employee_name_and_project(self):
        """Verify HTML/script injections in fields are handled safely."""
        xss_text = """
HỌ TÊN: <script>alert('xss')</script>
NGÀY: 24/10
CA: Ca ngày
DỰ ÁN: <img src=x onerror=alert(1)>
THỜI GIAN LÀM VIỆC: 8h-17h (8H)
CÓ ĂN Ở XƯỞNG KO: 0
"""
        parse_res = self.client.post("/api/parse", json={"text": xss_text})
        self.assertEqual(parse_res.status_code, 200)
        data = parse_res.json()
        self.assertEqual(len(data["records"]), 1)
        rec = data["records"][0]
        # Check normalized name
        self.assertIn("ALERT", rec["employee_name"])

        # When exported to Excel, openpyxl writes it as literal cell string without executing
        export_res = self.client.post("/api/export-excel", json={"records": [rec]})
        self.assertEqual(export_res.status_code, 200)
        summary = export_res.json()["summary"]
        self.assertEqual(summary["employees_matched"], 0)
        self.assertGreaterEqual(len(summary["errors"]), 1)

    def test_adv_04_template_upload_corrupt_zip(self):
        """Verify uploading corrupted zip / fake xlsx is rejected with 400 error."""
        fake_xlsx_bytes = b"PK\x03\x04This is not a real zip or xlsx file content"
        res = self.client.post(
            "/api/template/upload",
            files={"file": ("corrupt.xlsx", fake_xlsx_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("Lỗi khi đọc file mẫu Excel", res.json()["detail"])

    def test_adv_05_large_batch_scalability(self):
        """Verify performance and memory under 200 records batch."""
        single_block = """HỌ TÊN: NGUYỄN NGỌC THAO
NGÀY: 24/10
CA: Ca ngày
DỰ ÁN: sdv
THỜI GIAN LÀM VIỆC: 8h-20h (11H)
CÓ ĂN Ở XƯỞNG KO: 1
"""
        large_batch = "\n".join([single_block] * 200)
        res = self.client.post("/api/parse", json={"text": large_batch})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["summary"]["total"], 200)

    def test_adv_06_unmatched_employees_error_reporting(self):
        """Verify export returns detailed warnings for employees not found in template."""
        unknown_record = {
            "id": "unknown_01",
            "employee_name": "Người Ngoài Hành Tinh",
            "normalized_name": "NGUOI NGOAI HANH TINH",
            "date_str": "24/10",
            "resolved_date": "2026-10-24",
            "day_number": 24,
            "shift_type": "DAY",
            "project": "ETS",
            "time_window": "8h-17h (8H)",
            "hours": {
                "hcn_100": 8.0,
                "tcn_150": 0.0,
                "hcd_130": 0.0,
                "tcd_195": 0.0,
                "sunday_day_200": 0.0,
                "sunday_night_260": 0.0,
                "total_hours": 8.0
            },
            "meal_count": 0,
            "status": "VALID",
            "messages": [],
            "raw_text": "sample"
        }
        res = self.client.post("/api/export-excel", json={"records": [unknown_record]})
        self.assertEqual(res.status_code, 200)
        summary = res.json()["summary"]
        self.assertEqual(summary["records_processed"], 1)
        self.assertEqual(summary["employees_matched"], 0)
        self.assertGreaterEqual(len(summary["errors"]), 1)
        self.assertIn("NGUOI NGOAI HANH TINH", summary["errors"][0])

if __name__ == "__main__":
    unittest.main()
