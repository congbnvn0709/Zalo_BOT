"""
Core package for Zalo Attendance System.
"""
from core.parser import (
    AttendanceParser,
    parse_attendance_messages,
    parse_single_message,
    normalize_vietnamese_name,
    calculate_work_hours,
)

__all__ = [
    "AttendanceParser",
    "parse_attendance_messages",
    "parse_single_message",
    "normalize_vietnamese_name",
    "calculate_work_hours",
]
