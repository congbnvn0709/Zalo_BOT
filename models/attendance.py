"""
Attendance Data Models.
"""
from typing import List, Optional
from pydantic import BaseModel, Field


class WorkHours(BaseModel):
    hcn_100: float = 0.0  # Regular day hours (<= 8h, non-Sunday)
    tcn_150: float = 0.0  # Overtime day hours (> 8h, non-Sunday)
    hcd_130: float = 0.0  # Regular night hours (<= 8h, non-Sunday)
    tcd_195: float = 0.0  # Overtime night hours (> 8h, non-Sunday)
    sunday_day_200: float = 0.0  # Sunday daytime hours
    sunday_night_260: float = 0.0  # Sunday nighttime hours
    total_hours: float = 0.0


class AttendanceRecord(BaseModel):
    id: str
    employee_name: str
    normalized_name: str
    date_str: str  # Original string, e.g. "24/10" or "2026-10-24"
    resolved_date: str  # ISO YYYY-MM-DD, e.g. "2026-10-24"
    day_number: int  # Day of month (1..31)
    is_sunday: bool
    shift_type: str  # "DAY" | "NIGHT"
    project: str  # e.g. "sdv"
    time_window: str  # e.g. "8h-17h ( 8H)"
    hours: WorkHours
    meal_count: int  # 0 or 1 (or 2)
    status: str  # "VALID" | "WARNING" | "ERROR"
    messages: List[str] = Field(default_factory=list)  # Warnings or errors explanation
    raw_text: str


class ParseSummary(BaseModel):
    total: int = 0
    valid: int = 0
    warning: int = 0
    error: int = 0


class ParseResponse(BaseModel):
    records: List[AttendanceRecord] = Field(default_factory=list)
    summary: ParseSummary = Field(default_factory=ParseSummary)
