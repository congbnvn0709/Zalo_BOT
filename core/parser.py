"""
Attendance Message Parser.
Parses unstructured/semi-structured Zalo attendance messages into structured AttendanceRecord models.
"""
import re
import uuid
import datetime
import unicodedata
from typing import List, Dict, Any, Optional, Tuple, Set

from models.attendance import WorkHours, AttendanceRecord, ParseSummary, ParseResponse


def normalize_vietnamese_name(name: str, title_case: bool = True) -> str:
    """
    Cleans and normalizes Vietnamese names.
    Strips phone numbers, parenthesized notes, trims whitespace, preserves accents.
    Returns title case if title_case=True (e.g. 'Hoàng Đắc Phú'),
    or uppercase if title_case=False (e.g. 'HOÀNG ĐẮC PHÚ').
    """
    if not name:
        return ""
    
    # Normalize unicode to NFC
    text = unicodedata.normalize('NFC', name)
    
    # Strip phone numbers (e.g. - 0981234567, 0987654321)
    text = re.sub(r'[-–]\s*\d{9,11}', '', text)
    # Strip parenthesized annotations (e.g. (thợ hàn), (tổ 1))
    text = re.sub(r'\(.*?\)', '', text)
    # Strip list indices e.g. 1. or [1]
    text = re.sub(r'^\s*\d+[\.\)\-]\s*', '', text)
    # Collapse multiple spaces
    text = re.sub(r'\s+', ' ', text).strip()
    
    if not text or not any(c.isalpha() for c in text):
        return ""
        
    if title_case:
        # Title case while preserving Vietnamese accents
        return " ".join(word[0].upper() + word[1:].lower() if word else "" for word in text.split())
    else:
        return text.upper()


def calculate_work_hours(total_hours: float, shift_type: str, is_sunday: bool) -> WorkHours:
    """
    Allocates total worked hours across the 6 payroll/Excel categories:
    - HCN 100%: Regular day hours (<= 8h, non-Sunday)
    - TCN 150%: Overtime day hours (> 8h, non-Sunday)
    - HCĐ 130%: Regular night hours (<= 8h, non-Sunday)
    - TCĐ 195%: Overtime night hours (> 8h, non-Sunday)
    - Sunday day 200%: Sunday daytime hours
    - Sunday night 260%: Sunday nighttime hours
    """
    hcn_100 = 0.0
    tcn_150 = 0.0
    hcd_130 = 0.0
    tcd_195 = 0.0
    sunday_day_200 = 0.0
    sunday_night_260 = 0.0

    if total_hours <= 0:
        return WorkHours(total_hours=0.0)

    shift = (shift_type or "DAY").upper()

    if is_sunday:
        if shift == "DAY":
            sunday_day_200 = float(total_hours)
        else:
            sunday_night_260 = float(total_hours)
    else:
        if shift == "DAY":
            hcn_100 = float(min(total_hours, 8.0))
            tcn_150 = float(max(0.0, total_hours - 8.0))
        else:
            hcd_130 = float(min(total_hours, 8.0))
            tcd_195 = float(max(0.0, total_hours - 8.0))

    return WorkHours(
        hcn_100=round(hcn_100, 2),
        tcn_150=round(tcn_150, 2),
        hcd_130=round(hcd_130, 2),
        tcd_195=round(tcd_195, 2),
        sunday_day_200=round(sunday_day_200, 2),
        sunday_night_260=round(sunday_night_260, 2),
        total_hours=round(total_hours, 2),
    )


def extract_field_types(block: str) -> Set[str]:
    """
    Detects which attendance field categories appear in a text block.
    Used by split_messages to identify multi-line field continuations vs independent records.
    """
    if not block or not isinstance(block, str):
        return set()
    block = unicodedata.normalize('NFC', block)
    found: Set[str] = set()
    for line in block.split('\n'):
        line = line.strip()
        if not line:
            continue
        cleaned = re.sub(
            r'^\[\d{1,2}:\d{2}(?:,\s*\d{1,2}/\d{1,2}(?:/\d{2,4})?)?\]\s*[^:\n]+:\s*',
            '',
            line,
        ).strip()
        cleaned = re.sub(r'^\d+[\.\)\-]\s*', '', cleaned).strip()
        if re.match(r'^(?:HỌ\s*(?:VÀ\s*)?TÊN|HO\s*(?:VA\s*)?TEN|TÊN(?!\s*(?:dự|du|xưởng|xuong|công\s*trình|cong\s*trinh|đề\s*án|de\s*an|công\s*ty|cong\s*ty))|TEN(?!\s*(?:du|xuong|cong\s*trinh|de\s*an|cong\s*ty)))\s*[:：\-\.\s]', cleaned, re.I):
            found.add('name')
        elif re.match(r'^(?:NGÀY|NGAY|DATE)\s*[:：\-\.\s]', cleaned, re.I):
            found.add('date')
        elif re.match(r'^(?:CA\s*(?:LÀM\s*VIỆC|LAM\s*VIEC)?|SHIFT)\s*[:：\-\.\s]', cleaned, re.I):
            found.add('shift')
        elif re.match(r'^(?:(?:TÊN\s*)?(?:DỰ\s*ÁN|DU\s*AN|XƯỞNG|XUONG)|ĐỊA\s*ĐIỂM|DIA\s*DIEM|CÔNG\s*TRÌNH)\s*[:：\-\.\s]', cleaned, re.I):
            found.add('project')
        elif re.match(r'^(?:THỜI\s*GIAN(?:\s*LÀM\s*VIỆC)?|THOI\s*GIAN(?:\s*LAM\s*VIEC)?|GIỜ\s*LÀM(?:\s*VIỆC)?|GIO\s*LAM(?:\s*VIEC)?|TIME)\s*[:：\-\.\s]', cleaned, re.I):
            found.add('hours')
        elif re.match(r'^(?:(?:CÓ\s*)?ĂN(?:\s*(?:Ở\s*)?XƯỞNG)?(?:\s*K(?:O|HÔNG)?)?|(?:CO\s*)?AN(?:\s*(?:O\s*)?XUONG)?(?:\s*K(?:O|HONG)?)?|SUẤT\s*ĂN|SUAT\s*AN|CƠM\s*(?:Ở\s*)?XƯỞNG|CƠM|COM|ĂN|AN)\s*[:：\-\.\s]', cleaned, re.I):
            found.add('meal')
    return found


class AttendanceParser:
    """
    Parser for Zalo attendance messages.
    Supports batch segmentation, single-line format, multi-format dates,
    break calculation, rate allocation, and non-crashing error handling.
    """

    def __init__(self, default_year: int = 2026, default_project: str = "ETS"):
        self.default_year = default_year
        self.default_project = default_project

    def split_messages(self, text: str) -> List[str]:
        """
        Segments a multi-message batch text into individual message chunks.
        Uses header-lookahead on 'HỌ TÊN' / 'HO TEN' and divider fallback.
        Preserves multi-line messages containing internal blank lines.
        """
        if not text or not isinstance(text, str) or not text.strip():
            return []

        text = unicodedata.normalize('NFC', text)
        cleaned_text = text.replace('\r\n', '\n').replace('\r', '\n').strip()

        # Regex lookahead on message start (with optional timestamp and list numbering)
        # Standalone TÊN / TEN excludes project/workshop phrases (TÊN DỰ ÁN, TÊN XƯỞNG)
        name_token = (
            r'(?:HỌ\s*(?:VÀ\s*)?TÊN|HO\s*(?:VA\s*)?TEN|'
            r'TÊN(?!\s*(?:dự\s*án|du\s*an|xưởng|xuong|công\s*trình|cong\s*trinh|đề\s*án|de\s*an|công\s*ty|cong\s*ty))|'
            r'TEN(?!\s*(?:du\s*an|xuong|cong\s*trinh|de\s*an|cong\s*ty)))'
        )
        header_re = (
            r'(?=(?:^|\n)\s*'
            r'(?:\[\d{1,2}:\d{2}(?:,\s*\d{1,2}/\d{1,2}(?:/\d{2,4})?)?\]\s*[^:\n]+:\s*)?'
            r'(?:\d+[\.\)\-]\s*)?'
            + name_token +
            r'\s*[:：\-\s])'
        )

        has_headers = bool(re.search(header_re, cleaned_text, flags=re.IGNORECASE))

        if has_headers:
            parts = [p.strip() for p in re.split(header_re, cleaned_text, flags=re.IGNORECASE) if p.strip()]
            final_chunks: List[str] = []
            for part in parts:
                sub_blocks = [b.strip() for b in re.split(r'\n\s*\n+', part) if b.strip()]
                if not sub_blocks:
                    continue

                current_chunk = sub_blocks[0]
                current_fields = extract_field_types(sub_blocks[0])

                for sb in sub_blocks[1:]:
                    if re.match(r'^(?:-{3,}|={3,}|_{3,}|\*{3,})$', sb.strip()):
                        if current_chunk:
                            final_chunks.append(current_chunk)
                        current_chunk = ""
                        current_fields = set()
                        continue

                    sb_fields = extract_field_types(sb)
                    # If sb has valid fields and none overlap with current_fields, it is a continuation of the same message
                    if sb_fields and not (sb_fields & current_fields):
                        current_chunk = current_chunk + "\n" + sb
                        current_fields.update(sb_fields)
                    else:
                        if current_chunk:
                            final_chunks.append(current_chunk)
                        current_chunk = sb
                        current_fields = sb_fields

                if current_chunk:
                    final_chunks.append(current_chunk)
            return final_chunks

        # Fallback to double newline or markdown horizontal dividers
        blocks = [
            b.strip()
            for b in re.split(r'\n\s*(?:\n+|-{3,}|={3,}|_{3,}|\*{3,})\s*', cleaned_text)
            if b.strip()
        ]
        return blocks if blocks else [cleaned_text]

    def parse_single(self, raw_message: str) -> AttendanceRecord:
        """
        Parses a single message into an AttendanceRecord model.
        Never raises exceptions; captures errors and warnings in record.messages.
        """
        # Non-string or empty input guard
        if not raw_message or not isinstance(raw_message, str) or not raw_message.strip():
            return AttendanceRecord(
                id=str(uuid.uuid4()),
                employee_name="",
                normalized_name="",
                date_str="",
                resolved_date="",
                day_number=0,
                is_sunday=False,
                shift_type="DAY",
                project=self.default_project,
                time_window="",
                hours=WorkHours(),
                meal_count=0,
                status="ERROR",
                messages=["Tin nhắn rỗng hoặc không hợp lệ"],
                raw_text=str(raw_message or ""),
            )

        raw_message = unicodedata.normalize('NFC', raw_message)

        warnings: List[str] = []
        errors: List[str] = []

        field_prefixes = (
            r'(?:HỌ\s*(?:VÀ\s*)?TÊN|HO\s*(?:VA\s*)?TEN|'
            r'TÊN(?!\s*(?:dự\s*án|du\s*an|xưởng|xuong|công\s*trình|cong\s*trinh|đề\s*án|de\s*an|công\s*ty|cong\s*ty))|'
            r'TEN(?!\s*(?:du\s*an|xuong|cong\s*trinh|de\s*an|cong\s*ty))|'
            r'NGÀY|NGAY|DATE|'
            r'CA\s*(?:LÀM\s*VIỆC|LAM\s*VIEC)?|SHIFT|'
            r'(?:TÊN\s*)?(?:DỰ\s*ÁN|DU\s*AN|XƯỞNG|XUONG)|ĐỊA\s*ĐIỂM|DIA\s*DIEM|CÔNG\s*TRÌNH|'
            r'THỜI\s*GIAN(?:\s*LÀM\s*VIỆC)?|THOI\s*GIAN(?:\s*LAM\s*VIEC)?|GIỜ\s*LÀM(?:\s*VIỆC)?|GIO\s*LAM(?:\s*VIEC)?|TIME|'
            r'(?:CÓ\s*)?ĂN(?:\s*(?:Ở\s*)?XƯỞNG)?(?:\s*K(?:O|HÔNG)?)?|(?:CO\s*)?AN(?:\s*(?:O\s*)?XUONG)?(?:\s*K(?:O|HONG)?)?|'
            r'SUẤT\s*ĂN|SUAT\s*AN|CƠM\s*(?:Ở\s*)?XƯỞNG|CƠM|COM|ĂN|AN)'
            r'\s*[:：\-\.\s]'
        )

        raw_lines = re.split(
            r'[\r\n]+|(?<=[^\s])\s*[-–|;]\s*(?=' + field_prefixes + ')',
            raw_message,
            flags=re.IGNORECASE,
        )
        lines = [line.strip() for line in raw_lines if line.strip()]

        fields: Dict[str, str] = {}
        for line in lines:
            # Strip Zalo copy metadata: [17:30, 24/10] Name:
            cleaned = re.sub(
                r'^\[\d{1,2}:\d{2}(?:,\s*\d{1,2}/\d{1,2}(?:/\d{2,4})?)?\]\s*[^:\n]+:\s*',
                '',
                line,
            ).strip()
            # Strip list numbering e.g. 1.
            cleaned = re.sub(r'^\d+[\.\)\-]\s*', '', cleaned).strip()

            # 1. Name
            m_name = re.match(
                r'^(?:HỌ\s*(?:VÀ\s*)?TÊN|HO\s*(?:VA\s*)?TEN|'
                r'TÊN(?!\s*(?:dự\s*án|du\s*an|xưởng|xuong|công\s*trình|cong\s*trinh|đề\s*án|de\s*an|công\s*ty|cong\s*ty))|'
                r'TEN(?!\s*(?:du\s*an|xuong|cong\s*trinh|de\s*an|cong\s*ty)))\s*[:：\-\.\s]\s*(.*)$',
                cleaned,
                re.IGNORECASE,
            )
            if m_name and 'name' not in fields:
                fields['name'] = m_name.group(1).strip()
                continue

            # 2. Date
            m_date = re.match(
                r'^(?:NGÀY|NGAY|DATE)\s*[:：\-\.\s]\s*(.*)$',
                cleaned,
                re.IGNORECASE,
            )
            if m_date and 'date' not in fields:
                fields['date'] = m_date.group(1).strip()
                continue

            # 3. Shift
            m_shift = re.match(
                r'^(?:CA\s*(?:LÀM\s*VIỆC|LAM\s*VIEC)?|SHIFT)\s*[:：\-\.\s]\s*(.*)$',
                cleaned,
                re.IGNORECASE,
            )
            if m_shift and 'shift' not in fields:
                fields['shift'] = m_shift.group(1).strip()
                continue

            # 4. Project
            m_proj = re.match(
                r'^(?:(?:TÊN\s*)?(?:DỰ\s*ÁN|DU\s*AN|XƯỞNG|XUONG)|ĐỊA\s*ĐIỂM|DIA\s*DIEM|CÔNG\s*TRÌNH)\s*[:：\-\.\s]\s*(.*)$',
                cleaned,
                re.IGNORECASE,
            )
            if m_proj and 'project' not in fields:
                fields['project'] = m_proj.group(1).strip()
                continue

            # 5. Hours
            m_hours = re.match(
                r'^(?:THỜI\s*GIAN(?:\s*LÀM\s*VIỆC)?|THOI\s*GIAN(?:\s*LAM\s*VIEC)?|GIỜ\s*LÀM(?:\s*VIỆC)?|GIO\s*LAM(?:\s*VIEC)?|TIME)\s*[:：\-\.\s]\s*(.*)$',
                cleaned,
                re.IGNORECASE,
            )
            if m_hours and 'hours' not in fields:
                fields['hours'] = m_hours.group(1).strip()
                continue

            # 6. Meal
            m_meal = re.match(
                r'^(?:(?:CÓ\s*)?ĂN(?:\s*(?:Ở\s*)?XƯỞNG)?(?:\s*K(?:O|HÔNG)?)?|(?:CO\s*)?AN(?:\s*(?:O\s*)?XUONG)?(?:\s*K(?:O|HONG)?)?|SUẤT\s*ĂN|SUAT\s*AN|CƠM\s*(?:Ở\s*)?XƯỞNG|CƠM|COM|ĂN|AN)\s*[:：\-\.\s]\s*(.*)$',
                cleaned,
                re.IGNORECASE,
            )
            if m_meal and 'meal' not in fields:
                fields['meal'] = m_meal.group(1).strip()
                continue

        # ==========================================
        # 1. Process Employee Name
        # ==========================================
        raw_name = fields.get('name', '')
        clean_name = ''
        norm_name = ''
        if not raw_name:
            errors.append('Thiếu trường Họ và tên')
        else:
            clean_name = normalize_vietnamese_name(raw_name, title_case=False)  # Uppercase e.g. "HOÀNG ĐẮC PHÚ"
            norm_name = normalize_vietnamese_name(raw_name, title_case=True)    # Title case e.g. "Hoàng Đắc Phú"
            if not clean_name:
                errors.append('Họ tên rỗng hoặc không hợp lệ')

        # ==========================================
        # 2. Process Date & Sunday Resolution
        # ==========================================
        raw_date = fields.get('date', '')
        parsed_date: Optional[datetime.date] = None
        is_sunday = False
        formatted_date = ''
        day_num = 0

        if not raw_date:
            errors.append('Thiếu trường Ngày chấm công')
        else:
            s_date = re.sub(r'^(?:ngày|ngay)\s*', '', raw_date, flags=re.IGNORECASE).strip()

            # Format 1: YYYY-MM-DD
            m_iso = re.match(r'^(\d{4})[-/\.](\d{1,2})[-/\.](\d{1,2})$', s_date)
            if m_iso:
                y, m, d = int(m_iso.group(1)), int(m_iso.group(2)), int(m_iso.group(3))
                try:
                    parsed_date = datetime.date(y, m, d)
                except ValueError:
                    errors.append(f'Ngày không hợp lệ: {raw_date}')
            else:
                # Format 2: DD/MM/YYYY or DD-MM-YYYY
                m_full = re.match(r'^(\d{1,2})[-/\.](\d{1,2})[-/\.](\d{2,4})$', s_date)
                if m_full:
                    d, m, y_raw = int(m_full.group(1)), int(m_full.group(2)), int(m_full.group(3))
                    y = y_raw if y_raw >= 100 else (2000 + y_raw)
                    try:
                        parsed_date = datetime.date(y, m, d)
                    except ValueError:
                        errors.append(f'Ngày không hợp lệ: {raw_date}')
                else:
                    # Format 3: DD/MM or DD-MM
                    m_short = re.match(r'^(\d{1,2})[-/\.](\d{1,2})$', s_date)
                    if m_short:
                        d, m = int(m_short.group(1)), int(m_short.group(2))
                        try:
                            parsed_date = datetime.date(self.default_year, m, d)
                            warnings.append(f'Năm được tự động suy luận là {self.default_year}')
                        except ValueError:
                            errors.append(f'Ngày không hợp lệ: {raw_date}')
                    else:
                        errors.append(f'Ngày không hợp lệ: {raw_date}')

        if parsed_date:
            day_num = parsed_date.day
            formatted_date = parsed_date.strftime('%Y-%m-%d')
            is_sunday = (parsed_date.weekday() == 6)

        # ==========================================
        # 3. Process Shift
        # ==========================================
        raw_shift = fields.get('shift', '').strip()
        shift_code: Optional[str] = None
        if raw_shift:
            s_lower = raw_shift.lower()
            has_day = any(k in s_lower for k in ['ngày', 'ngay', 'sáng', 'sang', 'day', 'ca 1'])
            has_night = any(k in s_lower for k in ['đêm', 'dem', 'tối', 'toi', 'night', 'ca 2', 'ca 3'])

            if has_day and has_night:
                shift_code = 'DAY'
                warnings.append(f'Ca làm việc không rõ ràng (chứa cả ngày và đêm): "{raw_shift}", mặc định Ca ngày')
            elif has_day:
                shift_code = 'DAY'
            elif has_night:
                shift_code = 'NIGHT'
            else:
                warnings.append(f'Không nhận diện được ca: "{raw_shift}"')

        # ==========================================
        # 4. Process Working Hours & Break Math
        # ==========================================
        raw_hours = fields.get('hours', '').strip()
        total_hours = 0.0
        start_h: Optional[int] = None
        m_br = None
        m_rng = None
        m_single = None
        m_ot = None

        if not raw_hours:
            errors.append('Thiếu trường Thời gian làm việc')
        else:
            # Check for negative numbers / unary minus
            has_negative = bool(re.search(r'(?:^|[\(\[\{]|\b(?:to|đến|den|tới|toi)\b|[-–~])\s*-\s*\d', raw_hours, re.IGNORECASE))
            if has_negative:
                errors.append(f'Thời gian làm việc không hợp lệ (số âm): "{raw_hours}"')

            # 1. Bracketed hours take highest precedence: ( 8H), (11H)
            m_br = re.search(r'\(\s*(\d+(?:[\.,]\d+)?)\s*(?:h|tiếng|g|giờ)?\s*\)', raw_hours, re.IGNORECASE)
            br_hours = float(m_br.group(1).replace(',', '.')) if m_br else None

            # 2. Time range: 8h-17h, 8:00-17:00, 20h-5h
            m_rng = re.search(
                r'(\d{1,2})(?:[h:](\d{1,2})|h)?\s*[-–~]\s*(\d{1,2})(?:[h:](\d{1,2})|h)?',
                raw_hours,
                re.IGNORECASE,
            )

            if m_rng and not has_negative:
                sh = int(m_rng.group(1))
                sm = int(m_rng.group(2) or 0)
                eh = int(m_rng.group(3))
                em = int(m_rng.group(4) or 0)
                start_h = sh

                # Clock hour bounds check: valid hours are 0..24
                if sh > 24 or eh > 24 or (sh == 24 and sm > 0) or (eh == 24 and em > 0) or sm >= 60 or em >= 60:
                    errors.append(f'Khung giờ làm việc không hợp lệ trên đồng hồ 24h: "{raw_hours}"')

                # Infer shift from start hour if shift wasn't explicitly stated
                if not shift_code:
                    if sh >= 18 or sh <= 4:
                        shift_code = 'NIGHT'
                        warnings.append('Tự động nhận diện Ca đêm dựa vào giờ bắt đầu')
                    elif 6 <= sh <= 12:
                        shift_code = 'DAY'
                        warnings.append('Tự động nhận diện Ca ngày dựa vào giờ bắt đầu')

                # Warning for inverted daytime shift without clarifying bracket
                if eh < sh and shift_code == 'DAY' and br_hours is None:
                    warnings.append('Thời gian bắt đầu lớn hơn kết thúc đối với Ca ngày')

                # Calculate elapsed time
                if eh >= sh:
                    elapsed = (eh - sh) + (em - sm) / 60.0
                else:
                    # Shifts crossing midnight e.g. 20h-5h
                    elapsed = (eh + 24 - sh) + (em - sm) / 60.0

                if br_hours is not None:
                    total_hours = br_hours
                    if br_hours > elapsed:
                        warnings.append(f'Số giờ làm ({br_hours}h) lớn hơn thời gian chênh lệch ({elapsed:.1f}h)')
                else:
                    # Automatic 1h break deduction for full shifts >= 8.5 hours
                    if elapsed >= 8.5:
                        total_hours = elapsed - 1.0
                    else:
                        total_hours = elapsed
            elif not has_negative:
                # Standalone hours: 8H, 11 tiếng
                m_single = re.search(r'(\d+(?:[\.,]\d+)?)\s*(?:h|tiếng|g|giờ)', raw_hours, re.IGNORECASE)
                if m_single:
                    total_hours = float(m_single.group(1).replace(',', '.'))
                else:
                    errors.append(f'Không phân tích được thời gian làm việc: "{raw_hours}"')

            # Separate overtime addition check: + TC 3h
            m_ot = re.search(r'(?:\+|\btăng\s*ca\b|\btc\b)\s*(\d+(?:[\.,]\d+)?)\s*(?:h|tiếng)?', raw_hours, re.IGNORECASE)
            if m_ot and not m_br and not has_negative:
                ot_hours = float(m_ot.group(1).replace(',', '.'))
                total_hours += ot_hours

        # Shift final validation
        if not shift_code:
            errors.append('Thiếu trường Ca làm việc')
            shift_code = 'DAY'

        # Hours boundary validation
        if total_hours <= 0 and not any('thời gian' in e.lower() for e in errors):
            errors.append('Tổng số giờ làm phải lớn hơn 0')
        elif total_hours > 24:
            errors.append(f'Tổng số giờ làm ({total_hours}h) vượt quá 24h/ngày')

        # ==========================================
        # 5. Process Meal Count
        # ==========================================
        raw_meal = fields.get('meal', '').strip()
        meal_count = 0
        if not raw_meal:
            warnings.append('Thiếu thông tin suất ăn, mặc định 0')
            meal_count = 0
        else:
            m_clean = raw_meal.lower().strip()
            if m_clean in ['0', 'không', 'khong', 'ko', 'k', 'no', 'n', '0 suất', 'không ăn', 'ko ăn', 'k ăn', 'tự túc']:
                meal_count = 0
            elif m_clean in ['1', 'có', 'co', 'yes', 'y', 'x', 'v', '✓', '1 suất', 'có ăn', 'co an']:
                meal_count = 1
            elif m_clean in ['2', '2 suất', 'hai suất']:
                meal_count = 2
                warnings.append('Nhận diện 2 suất ăn')
            else:
                m_dig = re.match(r'^(\d+)', m_clean)
                if m_dig:
                    # Truncate digits to at most 4 digits to prevent integer conversion limit crashes (CVE-2020-10735)
                    digit_str = m_dig.group(1)[:4]
                    meal_count = int(digit_str)
                    if meal_count > 2 or len(m_dig.group(1)) > 2:
                        warnings.append(f'Số suất ăn bất thường ({m_dig.group(1)[:20]}), vui lòng kiểm tra lại')
                else:
                    meal_count = 0
                    warnings.append(f'Giá trị suất ăn không rõ ràng ("{raw_meal}"), mặc định 0')

        # ==========================================
        # 6. Process Project
        # ==========================================
        project_val = fields.get('project', '').strip() or self.default_project

        # ==========================================
        # 7. Hour Allocation
        # ==========================================
        if errors:
            work_hours = WorkHours()
        else:
            work_hours = calculate_work_hours(total_hours, shift_code, is_sunday)

        # Status determination
        if errors:
            status = 'ERROR'
        elif warnings:
            status = 'WARNING'
        else:
            status = 'VALID'

        all_messages = errors + warnings

        return AttendanceRecord(
            id=str(uuid.uuid4()),
            employee_name=clean_name,
            normalized_name=norm_name,
            date_str=raw_date,
            resolved_date=formatted_date,
            day_number=day_num,
            is_sunday=is_sunday,
            shift_type=shift_code,
            project=project_val,
            time_window=raw_hours,
            hours=work_hours,
            meal_count=meal_count,
            status=status,
            messages=all_messages,
            raw_text=raw_message.strip(),
        )

    def parse_batch(self, batch_text: str) -> List[AttendanceRecord]:
        """
        Splits and parses a batch of attendance messages into AttendanceRecord objects.
        """
        if isinstance(batch_text, str):
            batch_text = unicodedata.normalize('NFC', batch_text)
        chunks = self.split_messages(batch_text)
        return [self.parse_single(c) for c in chunks]


def parse_attendance_messages(
    text: str,
    default_year: int = 2026,
    default_project: str = "ETS",
) -> List[AttendanceRecord]:
    """
    Convenience function to parse multiple attendance messages.
    """
    if isinstance(text, str):
        text = unicodedata.normalize('NFC', text)
    parser = AttendanceParser(default_year=default_year, default_project=default_project)
    return parser.parse_batch(text)


def parse_single_message(
    text: str,
    default_year: int = 2026,
    default_project: str = "ETS",
) -> AttendanceRecord:
    """
    Convenience function to parse a single attendance message.
    """
    if isinstance(text, str):
        text = unicodedata.normalize('NFC', text)
    parser = AttendanceParser(default_year=default_year, default_project=default_project)
    return parser.parse_single(text)
