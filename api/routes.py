"""
FastAPI REST API Router for Zalo Attendance System (Milestone 3).

Endpoints:
- POST /api/parse: Parses raw Zalo attendance text into structured records.
- GET  /api/template/info: Returns active template metadata (sheet name, employees, date range).
- POST /api/template/upload: Accepts custom .xlsx template file and activates it.
- POST /api/export-excel: Writes attendance records into Excel workbook and generates download token.
- GET  /api/download/{token}: Streams generated Excel workbook as attachment.
- GET  /api/sample: Returns pre-canned standard test messages for instant UI testing.
- GET  /api/health: Returns system health status.
"""

import os
import re
import uuid
import time
import shutil
from typing import List, Dict, Any, Optional, Union

from fastapi import APIRouter, File, UploadFile, HTTPException, Query, status
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from models.attendance import WorkHours, AttendanceRecord, ParseSummary, ParseResponse
from core.parser import parse_attendance_messages
from core.excel_integrator import (
    ExcelIntegrator,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_TEMPLATE_PATH,
    PROJECT_ROOT,
)

router = APIRouter()

# ------------------------------------------------------------------------------
# Module State: Active Template & Export Token Store
# ------------------------------------------------------------------------------
_CUSTOM_TEMPLATE_PATH: Optional[str] = None
_EXPORT_TOKEN_STORE: Dict[str, Dict[str, Any]] = {}

SAMPLE_BATCH_TEXT = """HỌ TÊN : HOÀNG ĐẮC PHÚ
NGÀY: 24/10
CA : Ca ngày 
DỰ ÁN : sdv 
THỜI GIAN LÀM VIỆC :8h-17h ( 8H)
CÓ ĂN Ở XƯỞNG KO : 0

HỌ TÊN: NGUYỄN NGỌC THAO
NGÀY: 24/10
CA: Ca ngày
DỰ ÁN: sdv
THỜI GIAN LÀM VIỆC: 8h-20h (11H)
CÓ ĂN Ở XƯỞNG KO: 1

HỌ TÊN: NGUYỄN ĐỨC CÔNG
NGÀY: 25/10
CA: Ca ngày
DỰ ÁN: sdv
THỜI GIAN LÀM VIỆC: 8h-17h (8H)
CÓ ĂN Ở XƯỞNG KO: 1

HỌ TÊN: TÔ VĂN HƯNG
NGÀY: 24/10
CA: Ca đêm
DỰ ÁN: sdv
THỜI GIAN LÀM VIỆC: 20h-8h (11H)
CÓ ĂN Ở XƯỞNG KO: 1

HỌ TÊN: BÙI VĂN TIẾN
NGÀY: 24/10
CA: Ca đêm
DỰ ÁN: sdv
THỜI GIAN LÀM VIỆC: 20h-5h (8H)
CÓ ĂN Ở XƯỞNG KO: 0"""


# ------------------------------------------------------------------------------
# Pydantic Schemas
# ------------------------------------------------------------------------------
class ParseRequest(BaseModel):
    text: Optional[str] = ""
    raw_text: Optional[str] = None
    default_year: int = 2026
    default_project: str = "ETS"


class ExportExcelRequest(BaseModel):
    records: List[Union[AttendanceRecord, Dict[str, Any]]] = Field(default_factory=list)
    use_custom_template: bool = False
    output_filename: Optional[str] = None


class TemplateInfoResponse(BaseModel):
    sheet_name: str
    employees: List[str]
    date_range: List[str]
    total_employees: int


class ExportExcelResponse(BaseModel):
    success: bool = True
    download_token: str
    filename: str
    download_url: str
    summary: Dict[str, Any]


class SampleDataResponse(BaseModel):
    sample_text: str


class HealthResponse(BaseModel):
    status: str = "ok"


# ------------------------------------------------------------------------------
# Helper Functions
# ------------------------------------------------------------------------------
def _coerce_to_attendance_record(item: Union[AttendanceRecord, Dict[str, Any]]) -> AttendanceRecord:
    """Converts a dict or AttendanceRecord into a fully-validated AttendanceRecord."""
    if isinstance(item, AttendanceRecord):
        return item
    if not isinstance(item, dict):
        raise ValueError("Record must be a dictionary or AttendanceRecord instance.")

    hours_raw = item.get("hours")
    if isinstance(hours_raw, WorkHours):
        hours = hours_raw
    elif isinstance(hours_raw, dict):
        hours = WorkHours(**hours_raw)
    else:
        hours = WorkHours(
            hcn_100=float(item.get("hcn_100", 0.0)),
            tcn_150=float(item.get("tcn_150", 0.0)),
            hcd_130=float(item.get("hcd_130", 0.0)),
            tcd_195=float(item.get("tcd_195", 0.0)),
            sunday_day_200=float(item.get("sunday_day_200", 0.0)),
            sunday_night_260=float(item.get("sunday_night_260", 0.0)),
            total_hours=float(item.get("total_hours", 0.0)),
        )
        if hours.total_hours == 0.0:
            hours.total_hours = (
                hours.hcn_100
                + hours.tcn_150
                + hours.hcd_130
                + hours.tcd_195
                + hours.sunday_day_200
                + hours.sunday_night_260
            )

    emp_name = str(item.get("employee_name", "")).strip()
    norm_name = str(item.get("normalized_name") or emp_name).strip()
    date_str = str(item.get("date_str") or item.get("date") or item.get("day_display") or "").strip()
    resolved_date = str(item.get("resolved_date") or "").strip()

    day_num = int(item.get("day_number", 0))
    if day_num == 0 and date_str:
        m = re.search(r'(\d{1,2})', date_str)
        if m:
            day_num = int(m.group(1))

    meal_val = item.get("meal_count")
    if meal_val is None:
        meal_val = item.get("meals", 0)
    try:
        meal_count = int(meal_val)
    except (ValueError, TypeError):
        meal_count = 0

    return AttendanceRecord(
        id=str(item.get("id") or uuid.uuid4().hex[:8]),
        employee_name=emp_name,
        normalized_name=norm_name,
        date_str=date_str,
        resolved_date=resolved_date or date_str,
        day_number=day_num,
        is_sunday=bool(item.get("is_sunday", False)),
        shift_type=str(item.get("shift_type", "DAY")),
        project=str(item.get("project", "ETS")),
        time_window=str(item.get("time_window", "")),
        hours=hours,
        meal_count=meal_count,
        status=str(item.get("status", "VALID")),
        messages=item.get("messages", []) or item.get("issues", []),
        raw_text=str(item.get("raw_text", "")),
    )


# ------------------------------------------------------------------------------
# API Endpoints
# ------------------------------------------------------------------------------

@router.get("/health", response_model=HealthResponse)
def get_health():
    """Health check endpoint."""
    return HealthResponse(status="ok")


@router.get("/sample", response_model=SampleDataResponse)
def get_sample_messages():
    """Returns realistic sample Zalo attendance messages for instant UI testing."""
    return SampleDataResponse(sample_text=SAMPLE_BATCH_TEXT)


@router.post("/parse", response_model=ParseResponse)
def parse_messages(payload: ParseRequest):
    """
    Parses raw attendance messages and classifies hours across 6 categories.
    Returns structured records and count summaries.
    """
    raw_content = payload.text if payload.text is not None else (payload.raw_text or "")
    if payload.raw_text and not payload.text:
        raw_content = payload.raw_text

    records = parse_attendance_messages(
        text=raw_content,
        default_year=payload.default_year,
        default_project=payload.default_project,
    )

    total = len(records)
    valid_count = sum(1 for r in records if r.status == "VALID")
    warning_count = sum(1 for r in records if r.status == "WARNING")
    error_count = sum(1 for r in records if r.status == "ERROR")

    summary = ParseSummary(
        total=total,
        valid=valid_count,
        warning=warning_count,
        error=error_count,
    )

    return ParseResponse(records=records, summary=summary)


@router.get("/template/info", response_model=TemplateInfoResponse)
def get_template_info():
    """
    Returns active Excel template metadata (sheet name, employees, date range).
    Uses custom uploaded template if present, else default template.
    """
    active_path = _CUSTOM_TEMPLATE_PATH if (_CUSTOM_TEMPLATE_PATH and os.path.exists(_CUSTOM_TEMPLATE_PATH)) else None
    integrator = ExcelIntegrator(template_path=active_path)
    info = integrator.get_template_info()
    return TemplateInfoResponse(
        sheet_name=info["sheet_name"],
        employees=info["employees"],
        date_range=info["date_range"],
        total_employees=len(info["employees"]),
    )


@router.post("/template/upload", response_model=TemplateInfoResponse)
async def upload_custom_template(file: UploadFile = File(...)):
    """
    Uploads a custom .xlsx template file, validates its structure,
    and activates it as the current working template.
    """
    global _CUSTOM_TEMPLATE_PATH

    filename = file.filename or ""
    if not filename.lower().endswith(".xlsx"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Định dạng tệp không hợp lệ. Chỉ chấp nhận tệp Excel có đuôi .xlsx",
        )

    upload_dir = "/tmp/uploaded" if os.environ.get("VERCEL") else os.path.join(PROJECT_ROOT, "templates_excel", "uploaded")
    os.makedirs(upload_dir, exist_ok=True)
    saved_path = os.path.join(upload_dir, f"custom_{int(time.time())}_{filename}")

    try:
        with open(saved_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        # Validate with ExcelIntegrator
        integrator = ExcelIntegrator(template_path=saved_path)
        info = integrator.get_template_info()

        if not info["employees"] or not info["date_range"]:
            raise ValueError("Tệp Excel tải lên không chứa dữ liệu nhân sự hoặc dòng ngày hợp lệ.")

        _CUSTOM_TEMPLATE_PATH = saved_path
        return TemplateInfoResponse(
            sheet_name=info["sheet_name"],
            employees=info["employees"],
            date_range=info["date_range"],
            total_employees=len(info["employees"]),
        )
    except Exception as e:
        if os.path.exists(saved_path):
            try:
                os.remove(saved_path)
            except OSError:
                pass
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Lỗi khi đọc file mẫu Excel: {str(e)}",
        )


@router.post("/export-excel", response_model=ExportExcelResponse)
def export_excel(payload: ExportExcelRequest):
    """
    Applies validated attendance records to the Excel template, preserves formulas,
    saves the updated workbook to output/, and returns a download token.
    """
    if not payload.records:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Không có bản ghi chấm công nào để xuất Excel.",
        )

    # Coerce all records to AttendanceRecord
    domain_records: List[AttendanceRecord] = []
    for item in payload.records:
        try:
            rec = _coerce_to_attendance_record(item)
            domain_records.append(rec)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Dữ liệu bản ghi không hợp lệ: {str(e)}",
            )

    # Select template source
    template_path = None
    if _CUSTOM_TEMPLATE_PATH and os.path.exists(_CUSTOM_TEMPLATE_PATH):
        template_path = _CUSTOM_TEMPLATE_PATH
    elif payload.use_custom_template and _CUSTOM_TEMPLATE_PATH and os.path.exists(_CUSTOM_TEMPLATE_PATH):
        template_path = _CUSTOM_TEMPLATE_PATH

    # Prepare output path
    token = f"export_{uuid.uuid4().hex}"
    raw_fname = payload.output_filename or "BANG_CHAM_CONG_CAP_NHAT.xlsx"
    clean_fname = re.sub(r'[^a-zA-Z0-9_\-\. ]', '_', raw_fname).strip()
    if not clean_fname.lower().endswith(".xlsx"):
        clean_fname += ".xlsx"

    out_dir = "/tmp/output" if os.environ.get("VERCEL") else DEFAULT_OUTPUT_DIR
    os.makedirs(out_dir, exist_ok=True)
    target_filepath = os.path.join(out_dir, f"{token}_{clean_fname}")

    try:
        integrator = ExcelIntegrator(template_path=template_path)
        summary = integrator.apply_records(records=domain_records, output_path=target_filepath)

        # Standardize summary keys for client compatibility
        summary["employees_updated"] = summary.get("employees_matched", 0)
        summary["cells_written"] = summary.get("updated_cells", 0)

        # Register token
        _EXPORT_TOKEN_STORE[token] = {
            "file_path": target_filepath,
            "filename": clean_fname,
            "created_at": time.time(),
        }

        return ExportExcelResponse(
            success=True,
            download_token=token,
            filename=clean_fname,
            download_url=f"/api/download/{token}",
            summary=summary,
        )
    except Exception as e:
        if os.path.exists(target_filepath):
            try:
                os.remove(target_filepath)
            except OSError:
                pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi trong quá trình xử lý ghi file Excel: {str(e)}",
        )


@router.get("/download/{token}")
def download_excel(token: str):
    """
    Validates token and returns generated Excel workbook as attachment.
    """
    token_data = _EXPORT_TOKEN_STORE.get(token)
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mã tải file (token) không tồn tại hoặc đã hết hạn.",
        )

    file_path = token_data.get("file_path", "")
    filename = token_data.get("filename", "BANG_CHAM_CONG.xlsx")

    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tệp Excel không tìm thấy trên máy chủ.",
        )

    return FileResponse(
        path=file_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=filename,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
