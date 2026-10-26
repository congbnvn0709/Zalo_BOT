"""
Adversarial Stress Test Suite for Attendance Message Parser (Milestone 1).
Designed and executed by Parser Challenger 1.
"""
import sys
import os
import time
import random
import unicodedata
from typing import List, Dict, Any

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.parser import (
    AttendanceParser,
    parse_attendance_messages,
    parse_single_message,
    normalize_vietnamese_name,
    calculate_work_hours,
)
from models.attendance import AttendanceRecord, WorkHours


class StressTestResults:
    def __init__(self):
        self.total_tests = 0
        self.crashes = []
        self.status_anomalies = []
        self.findings = []
        self.stats = {}

    def record_crash(self, scenario: str, exception: Exception, payload: str):
        self.crashes.append({
            "scenario": scenario,
            "exception_type": type(exception).__name__,
            "exception_msg": str(exception),
            "payload_snippet": payload[:100] if payload else str(payload),
        })

    def record_anomaly(self, scenario: str, expected_status: str, actual_status: str, record: AttendanceRecord):
        self.status_anomalies.append({
            "scenario": scenario,
            "expected_status": expected_status,
            "actual_status": actual_status,
            "messages": record.messages,
            "hours": record.hours.model_dump(),
            "shift": record.shift_type,
            "name": record.employee_name,
        })


def run_random_fuzzing(results: StressTestResults, iterations: int = 500):
    print(f"--- 1. Random Fuzzing ({iterations} iterations) ---")
    base_template = (
        "HỌ TÊN: HOÀNG ĐẮC PHÚ\n"
        "NGÀY: 24/10/2026\n"
        "CA: Ca ngày\n"
        "DỰ ÁN: sdv\n"
        "THỜI GIAN LÀM VIỆC: 8h-17h (8H)\n"
        "CÓ ĂN Ở XƯỞNG KO: 0"
    )

    fuzz_chars = [
        "\u200b", "\u200c", "\u200d", "\ufeff", "\u00a0",  # Zero-width & non-breaking spaces
        "：", ";", "-", "–", "—", ":", " ", "  ", "\t",      # Colon corruptions
        "\r\n", "\r", "\n\n", "\n\n\n",                     # Newline variations
        "👨‍🏭", "🕒", "📅", "🍚", "👍", "❌", "❓", "⭐",         # Emojis
        "\x00", "\x01", "\x1f", "\x7f",                     # Control characters
        "'\"><script>alert(1)</script>", "-- drop table",   # Injection artifacts
        "̣̀́̃̉", "Z͑AͫLͨGͮOͤ",                                 # Combining diacritics / Zalgo
        "а", "е", "о", "р", "с",                             # Cyrillic lookalikes (homoglyphs)
    ]

    crash_count = 0
    t0 = time.time()
    for i in range(iterations):
        results.total_tests += 1
        # Randomly mutate the base template
        chars = list(base_template)
        num_mutations = random.randint(1, 10)
        for _ in range(num_mutations):
            pos = random.randint(0, len(chars) - 1)
            op = random.choice(["insert", "replace", "delete"])
            fuzz_char = random.choice(fuzz_chars)
            if op == "insert":
                chars.insert(pos, fuzz_char)
            elif op == "replace":
                chars[pos] = fuzz_char
            elif op == "delete" and len(chars) > 10:
                del chars[pos]
        mutated_text = "".join(chars)

        try:
            records = parse_attendance_messages(mutated_text)
            for r in records:
                # Valid invariant: status MUST be one of VALID, WARNING, ERROR
                assert r.status in ["VALID", "WARNING", "ERROR"], f"Invalid status: {r.status}"
                # If ERROR, hours should be zeroed out
                if r.status == "ERROR":
                    assert r.hours.total_hours == 0.0, "ERROR record had non-zero total_hours"
        except Exception as e:
            crash_count += 1
            results.record_crash("random_fuzzing", e, mutated_text)

    t1 = time.time()
    results.stats["fuzzing_duration_sec"] = round(t1 - t0, 3)
    results.stats["fuzzing_crashes"] = crash_count
    print(f"Random fuzzing finished: {iterations} tests in {t1 - t0:.3f}s. Crashes: {crash_count}")


def run_extreme_numbers_tests(results: StressTestResults):
    print("--- 2. Extreme Numbers & Time Windows ---")
    test_cases = [
        # (description, hours_str, expected_status, notes)
        ("Zero hours explicit", "0h", "ERROR", "Total hours <= 0"),
        ("Zero hours range", "8h-8h", "ERROR", "Zero elapsed"),
        ("Zero hours bracketed", "8h-8h (0h)", "ERROR", "Zero bracketed"),
        ("24h work standalone", "24h", "VALID", "Max valid work day"),
        ("24h work range", "0h-24h (24h)", "VALID", "24h continuous"),
        ("25h work standalone", "25h", "ERROR", "Exceeds 24h"),
        ("25h work bracketed", "8h-9h (25H)", "ERROR", "Bracket exceeds 24h"),
        ("100h work", "100h", "ERROR", "Massive hours"),
        ("Negative hours standalone", "-5h", "ERROR", "Negative hour invalid"),
        ("Negative hours bracketed", "(-5h)", "ERROR", "Negative bracket invalid"),
        ("Negative range", "-8h to -4h", "ERROR", "Negative times"),
        ("Inverted daytime", "17h-8h", "WARNING", "Inverted start-end on daytime"),
        ("Inverted daytime with bracket", "17h-8h (8h)", "VALID", "Bracket clarifies 8h"),
        ("Clock hours > 24", "25h-30h", "ERROR", "Clock hours 25 and 30 don't exist"),
        ("Fractional hours comma", "8,5h", "VALID", "Vietnamese decimal comma"),
        ("Fractional hours dot", "8.5h", "VALID", "Standard decimal dot"),
        ("Clock minutes", "8h30-17h30", "VALID", "Half-hour shift"),
        ("Clock minutes with overtime", "8h00-20h30", "VALID", "12.5h - 1h break = 11.5h"),
    ]

    for desc, hours_str, expected_status, notes in test_cases:
        results.total_tests += 1
        raw = (
            "HỌ TÊN: TRẦN VĂN TEST\n"
            "NGÀY: 24/10/2026\n"
            "CA: Ca ngày\n"
            f"THỜI GIAN LÀM VIỆC: {hours_str}\n"
            "CÓ ĂN Ở XƯỞNG KO: 0"
        )
        try:
            record = parse_single_message(raw)
            if record.status != expected_status:
                results.record_anomaly(
                    scenario=f"extreme_number: {desc} ({hours_str})",
                    expected_status=expected_status,
                    actual_status=record.status,
                    record=record,
                )
        except Exception as e:
            results.record_crash(f"extreme_number: {desc}", e, raw)


def run_weird_shift_tests(results: StressTestResults):
    print("--- 3. Weird Shift Strings ---")
    test_cases = [
        # (description, shift_str, hours_str, expected_shift, expected_status, notes)
        ("Ca ngày đêm (ambiguous both)", "Ca ngày đêm", "8h-17h (8H)", "DAY", "WARNING", "Ambiguous shift should warn"),
        ("Ca đêm ngày (reversed)", "Ca đêm ngày", "8h-17h (8H)", "DAY", "WARNING", "Ambiguous shift should warn"),
        ("Ca 3 (manufacturing night)", "ca 3", "22h-6h (7H)", "NIGHT", "VALID", "Ca 3 is night shift in VN factories"),
        ("Nghỉ bù (compensatory leave)", "nghỉ bù", "8h-17h (8H)", "DAY", "WARNING", "Leave treated as work or warning"),
        ("Đi muộn về sớm", "đi muộn về sớm", "9h-16h (7H)", "DAY", "WARNING", "Irregular attendance"),
        ("Ca gãy (split shift)", "ca gãy", "8h-17h (8H)", "DAY", "WARNING", "Unrecognized shift code"),
        ("Nghỉ phép (annual leave)", "nghỉ phép", "8H", "DAY", "ERROR", "Leave with no clock times"),
        ("Missing shift, night hours", "", "20h-5h (8H)", "NIGHT", "WARNING", "Inferred night from 20h start"),
        ("Missing shift, day hours", "", "8h-17h (8H)", "DAY", "WARNING", "Inferred day from 8h start"),
        ("Missing shift, afternoon hours", "", "14h-18h (4H)", "DAY", "ERROR", "Cannot infer shift between 12-18h"),
    ]

    for desc, shift_str, hours_str, exp_shift, exp_status, notes in test_cases:
        results.total_tests += 1
        raw = (
            "HỌ TÊN: NGUYỄN VĂN SHIFT\n"
            "NGÀY: 24/10/2026\n"
            f"CA: {shift_str}\n"
            f"THỜI GIAN LÀM VIỆC: {hours_str}\n"
            "CÓ ĂN Ở XƯỞNG KO: 0"
        )
        try:
            record = parse_single_message(raw)
            if exp_status and record.status != exp_status:
                results.record_anomaly(
                    scenario=f"weird_shift: {desc} ('{shift_str}')",
                    expected_status=exp_status,
                    actual_status=record.status,
                    record=record,
                )
        except Exception as e:
            results.record_crash(f"weird_shift: {desc}", e, raw)


def run_batch_and_newline_tests(results: StressTestResults):
    print("--- 4. Large Batches & Segmentation Integrity ---")

    # Sub-test 4A: 150 concatenated messages
    messages = []
    employees = [
        "Hoàng Đắc Phú", "Nguyễn Ngọc Thao", "Tô Văn Hưng", "Trần Thị Mai",
        "Lê Văn Cường", "Phạm Quốc Tuấn", "Vũ Minh Hiếu", "Đặng Đình Bách"
    ]
    shifts = [
        ("Ca ngày", "8h-17h (8H)", 0),
        ("Ca ngày", "8h-20h (11H)", 1),
        ("Ca đêm", "20h-5h (8H)", 0),
        ("Ca đêm", "20h-8h (11H)", 1),
    ]

    for i in range(150):
        emp = random.choice(employees)
        shift, hours, meal = random.choice(shifts)
        day = (i % 28) + 1
        date_str = f"{day:02d}/10/2026"
        # Alternate formats: standard, single line, timestamped, numbered
        fmt_type = i % 4
        if fmt_type == 0:
            msg = (
                f"HỌ TÊN: {emp}\n"
                f"NGÀY: {date_str}\n"
                f"CA: {shift}\n"
                f"THỜI GIAN: {hours}\n"
                f"ĂN: {meal}"
            )
        elif fmt_type == 1:
            msg = f"HỌ TÊN: {emp} - NGÀY: {date_str} - CA: {shift} - THỜI GIAN: {hours} - ĂN: {meal}"
        elif fmt_type == 2:
            msg = (
                f"[{18 + (i % 4):02d}:30, {date_str}] {emp}: HỌ TÊN : {emp}\n"
                f"NGÀY: {date_str}\n"
                f"CA: {shift}\n"
                f"THỜI GIAN: {hours}\n"
                f"ĂN: {meal}"
            )
        else:
            msg = (
                f"{i + 1}. HỌ TÊN: {emp}\n"
                f"NGÀY: {date_str}\n"
                f"CA: {shift}\n"
                f"THỜI GIAN: {hours}\n"
                f"ĂN: {meal}"
            )
        messages.append(msg)

    batch_text = "\n\n".join(messages)
    t0 = time.time()
    try:
        results.total_tests += 1
        parsed = parse_attendance_messages(batch_text)
        t1 = time.time()
        results.stats["batch_150_duration_sec"] = round(t1 - t0, 3)
        results.stats["batch_150_count"] = len(parsed)
        print(f"Batch 150 parsed: got {len(parsed)} records in {t1 - t0:.3f}s")
        assert len(parsed) == 150, f"Expected 150 records, got {len(parsed)}"
    except Exception as e:
        results.record_crash("batch_150_messages", e, batch_text[:200])

    # Sub-test 4B: Internal Blank Lines in messages (Vulnerability Test)
    print("Testing blank lines inside messages...")
    msg_with_blanks = (
        "HỌ TÊN: NGUYỄN VĂN A\n"
        "NGÀY: 24/10/2026\n"
        "\n"  # blank line inside
        "CA: Ca ngày\n"
        "THỜI GIAN: 8h-17h (8H)\n"
        "\n"  # another blank line
        "ĂN: 0\n"
        "\n"  # separator between messages
        "HỌ TÊN: TRẦN VĂN B\n"
        "NGÀY: 24/10/2026\n"
        "CA: Ca ngày\n"
        "THỜI GIAN: 8h-17h (8H)\n"
        "ĂN: 0"
    )

    results.total_tests += 1
    try:
        parsed_blanks = parse_attendance_messages(msg_with_blanks)
        if len(parsed_blanks) != 2:
            results.findings.append({
                "type": "MESSAGE_FRAGMENTATION_ON_BLANK_LINES",
                "details": f"Expected 2 records for 2 messages with internal blank lines, got {len(parsed_blanks)}. Records were fragmented into errors.",
                "record_statuses": [r.status for r in parsed_blanks],
            })
    except Exception as e:
        results.record_crash("internal_blank_lines", e, msg_with_blanks)


def run_unhandled_crash_tests(results: StressTestResults):
    print("--- 5. Unhandled Crash / Exception Stress ---")
    extreme_cases = [
        ("None input to parse_attendance_messages", lambda: parse_attendance_messages(None)),
        ("None input to parse_single_message", lambda: parse_single_message(None)),
        ("Non-string int input", lambda: parse_single_message(12345)),
        ("Empty string", lambda: parse_single_message("")),
        ("Pure whitespace", lambda: parse_single_message("   \n\t   \n   ")),
        ("5000 digit meal count", lambda: parse_single_message("HỌ TÊN: A\nNGÀY: 24/10/2026\nCA: Ca ngày\nTHỜI GIAN: 8h\nĂN: " + "9" * 5000)),
        ("5000 digit hour count", lambda: parse_single_message("HỌ TÊN: A\nNGÀY: 24/10/2026\nCA: Ca ngày\nTHỜI GIAN: " + "9" * 5000 + "h\nĂN: 0")),
        ("Zero byte string", lambda: parse_single_message("\x00\x00\x00")),
    ]

    for desc, func in extreme_cases:
        results.total_tests += 1
        try:
            func()
        except Exception as e:
            results.record_crash(f"crash_test: {desc}", e, desc)


def main():
    results = StressTestResults()
    print("=================================================================")
    print("STARTING EMPIRICAL ADVERSARIAL STRESS TEST ON core/parser.py")
    print("=================================================================")

    run_random_fuzzing(results, iterations=500)
    run_extreme_numbers_tests(results)
    run_weird_shift_tests(results)
    run_batch_and_newline_tests(results)
    run_unhandled_crash_tests(results)

    print("\n=================================================================")
    print("STRESS TEST EXECUTION COMPLETED")
    print(f"Total test executions: {results.total_tests}")
    print(f"Total unhandled crashes: {len(results.crashes)}")
    print(f"Total status anomalies: {len(results.status_anomalies)}")
    print(f"Total structural findings: {len(results.findings)}")
    print("=================================================================")

    if results.crashes:
        print("\n[!] UNHANDLED CRASHES:")
        for c in results.crashes:
            print(f"  - {c['scenario']}: {c['exception_type']} -> {c['exception_msg']}")

    if results.status_anomalies:
        print("\n[!] STATUS ANOMALIES (False Positives / Negatives):")
        for a in results.status_anomalies:
            print(f"  - {a['scenario']}: expected {a['expected_status']}, got {a['actual_status']} | msgs: {a['messages']}")

    if results.findings:
        print("\n[!] STRUCTURAL FINDINGS:")
        for f in results.findings:
            print(f"  - {f['type']}: {f['details']}")

    return results


if __name__ == "__main__":
    main()
