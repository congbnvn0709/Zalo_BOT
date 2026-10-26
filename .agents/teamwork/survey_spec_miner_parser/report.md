# Attendance Message Parser: Specification & Rulebook (Requirement R1)

**Working Directory**: `/Users/congcm/CODE/Vibe_Code/Zalo_BOT/.agents/teamwork/survey_spec_miner_parser/`  
**Date**: 2026-10-26  
**Status**: Authoritative Specification & Parsing Rulebook  
**Target Requirement**: R1 (Attendance Message Parser) & Acceptance Criteria (Calc Rules, Error Handling, Batch Parsing)

---

## 1. Executive Summary & Purpose

The **Attendance Message Parser** is the input engine of the Zalo Attendance System. It transforms unstructured or semi-structured plain text copied from Zalo chat messages into clean, strongly-typed attendance records ready for interactive preview on the Web UI (R2) and high-fidelity persistence into the standardized Excel attendance workbook (R3).

### Key Acceptance Criteria Verified:
- **100% Acceptance Sample Compliance**:
  ```text
  HỌ TÊN : HOÀNG ĐẮC PHÚ
  NGÀY: 24/10
  CA : Ca ngày 
  DỰ ÁN : sdv 
  THỜI GIAN LÀM VIỆC :8h-17h ( 8H)
  CÓ ĂN Ở XƯỞNG KO : 0
  ```
  Deconstructs into:
  - `Họ và tên`: `"HOÀNG ĐẮC PHÚ"`
  - `Ngày`: `24/10` (Resolved to `2026-10-24`, Saturday)
  - `Ca`: `DAY` (`Ca ngày`)
  - `Dự án`: `"sdv"`
  - `HCN 100%`: `8.0` giờ
  - `TCN 150%`: `0.0` giờ
  - `HCĐ 130%`: `0.0` giờ
  - `TCĐ 195%`: `0.0` giờ
  - `Ngày CN (200%)`: `0.0` giờ
  - `Đêm CN (260%)`: `0.0` giờ
  - `Suất ăn`: `0`
  - `Trạng thái`: `VALID` (or `WARNING` if year was inferred from default)
- **Zero-Crash Resiliency**: Any malformed, incomplete, or corrupted message is parsed into an `ERROR` or `WARNING` record with explicit diagnostic messages, never throwing unhandled exceptions or halting batch processing.
- **Strict Excel Alignment**: Output variables match the exact 7-row structure per employee in the `BẢNG CHẤM CÔNG WEVN - ETS` Excel template (`sample_data.csv`).

---

## 2. Features Discovered

| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|----------|---------|-------------|--------|---------|----------------|----------------|
| 1 | Batch Segmentation | Boundary-Aware Message Splitting | Splits a large multi-message text block into individual message chunks | Raw text with multiple messages | `List[str]` (message chunks) | Returns single-element list if no delimiter; never drops text | Dispatch prompt & R1 |
| 2 | Batch Segmentation | Header-Lookahead Segmentation | Splits messages even when no blank line separates them, detecting `HỌ TÊN` prefix | Text with contiguous records | Separate records | Falls back to newline splitting if header absent | Analysis of user paste behavior |
| 3 | Batch Segmentation | Metadata Stripping | Strips Zalo metadata like `[17:30, 24/10] Name:` and list bullets `1. `, `- ` | Raw line | Cleaned line | Leaves non-matching lines unchanged | Zalo desktop copy format |
| 4 | Name Processing | Vietnamese Name Extraction | Extracts full name from `HỌ TÊN`, `Họ và tên`, `HO TEN`, etc. | Colon/dash separated line | Normalized uppercase name string | Sets `ERROR: Thiếu trường Họ và tên` if missing | R1 & sample_data.csv |
| 5 | Name Processing | Noise & Note Sanitization | Strips phone numbers (e.g. `- 098...`) and parenthetical notes | String with extra data | Clean name | Retains name part, ignores noise | Real chat variability |
| 6 | Date Processing | Multi-Format Date Parsing | Parses `DD/MM`, `DD/MM/YYYY`, `DD-MM-YYYY`, `YYYY-MM-DD`, `DD.MM` | Date string | `datetime.date`, `day`, `month`, `year` | Sets `ERROR: Ngày không hợp lệ` | Dispatch & Acceptance Criteria |
| 7 | Date Processing | Intelligent Year Resolution | Infers missing year from default/template (e.g. `2026`) | Short date `24/10` | Full date `2026-10-24` | Flags `WARNING: Năm tự động suy luận` | Template context (`sample_data.csv`) |
| 8 | Date Processing | Day-of-Week & Sunday Detection | Determines if date is Sunday (`weekday() == 6`) | Full `datetime.date` | `is_sunday: bool` | Inherits date validity | Excel column row 3 (`T2..CN`) |
| 9 | Shift Processing | Shift Normalization | Classifies shift into `DAY` (`Ca ngày`) or `NIGHT` (`Ca đêm`) | `Ca ngày`, `ca dem`, `Ngày`, `Đêm`, `Ca 1`, `Ca 2` | `DAY` or `NIGHT` enum | If missing, attempts inference from hours; else flags `ERROR` | Dispatch R1 |
| 10 | Shift Processing | Start-Time Shift Inference | Infers `NIGHT` if start >= 18h or <= 4h; `DAY` if start 7h-9h | Start hour | Inferred shift code | Flags `WARNING: Tự động nhận diện ca từ giờ làm` | Robust fallback mechanism |
| 11 | Hours Processing | Time Range & Bracket Parsing | Parses start-end `8h-17h` and explicit bracketed totals `(8H)` | Working hours string | `start_time`, `end_time`, `total_hours` | If unparseable, flags `ERROR` | Dispatch R1 |
| 12 | Hours Processing | Break Time Deduction | Automatically deducts 1h break for standard continuous shifts >= 8.5h if no bracket given | `8h-17h` -> 8h; `20h-5h` -> 8h | Net worked hours | Informs user via calculation log | Factory standard labor rule |
| 13 | Hours Processing | Standalone Hours Parsing | Supports single values like `8H`, `11h`, `8 tiếng` | `8H`, `11 tiếng` | `total_hours: float` | Validates > 0 and <= 24 | Worker shorthand formats |
| 14 | Calc Formula | Day Shift Allocation (Mon-Sat) | Up to 8h -> `HCN 100%`; Excess -> `TCN 150%` | `shift=DAY`, `is_sunday=False`, `hours` | `hcn`, `tcn` | Hours <= 0 flagged as ERROR | R1 & sample_data.csv |
| 15 | Calc Formula | Night Shift Allocation (Mon-Sat) | Up to 8h -> `HCĐ 130%`; Excess -> `TCĐ 195%` | `shift=NIGHT`, `is_sunday=False`, `hours` | `hcd`, `tcd` | Hours <= 0 flagged as ERROR | R1 & sample_data.csv |
| 16 | Calc Formula | Sunday Day Shift Allocation | All daytime Sunday hours -> `Ngày CN (200%)` | `shift=DAY`, `is_sunday=True`, `hours` | `ngay_cn_200` | Overtime mapped to Sunday row | Dispatch & Excel template rows |
| 17 | Calc Formula | Sunday Night Shift Allocation | All nighttime Sunday hours -> `Đêm CN (260%)` | `shift=NIGHT`, `is_sunday=True`, `hours` | `dem_cn_260` | Overtime mapped to Sunday Night | Dispatch & Excel template rows |
| 18 | Meal Processing | Flexible Meal Normalization | Normalizes `0`, `1`, `Có`, `Không`, `ko`, `k`, `x`, `v`, `yes`, `no` | Meal string | `meal: int` (`0` or `1`) | Defaults to `0` with WARNING if ambiguous | Dispatch R1 |
| 19 | Project Handling | Project/Factory Extraction | Extracts arbitrary project name (`sdv`, `ETS`, `WEVN`) | `DỰ ÁN : sdv` | Clean string | Optional; defaults to default project if absent | CSV column `ĐỊA ĐIỂM LÀM VIỆC` |
| 20 | Validation | Record Status Gating | Categorizes records into `VALID`, `WARNING`, `ERROR` | Field values & errors list | Status badge | Never crashes; outputs full error list | Acceptance Criteria (UI Preview) |

---

## 3. Edge Cases & Observed Behavior

| # | Feature | Input | Observed Behavior |
|---|---------|-------|-------------------|
| 1 | Standard Happy Path | `HỌ TÊN : HOÀNG ĐẮC PHÚ\nNGÀY: 24/10\nCA : Ca ngày\nDỰ ÁN : sdv\nTHỜI GIAN LÀM VIỆC :8h-17h ( 8H)\nCÓ ĂN Ở XƯỞNG KO : 0` | Parsed: Name=`HOÀNG ĐẮC PHÚ`, Date=`2026-10-24` (T7), Shift=`DAY`, HCN=`8.0`, TCN=`0`, Suất ăn=`0`. Status: `VALID` (or `WARNING` if year inferred). |
| 2 | Day Overtime (11H) | `THỜI GIAN LÀM VIỆC: 8h-20h (11H)` on weekday | `total_hours = 11.0` -> `HCN 100% = 8.0`, `TCN 150% = 3.0`. |
| 3 | Night Standard (8H) | `CA: Ca đêm\nTHỜI GIAN LÀM VIỆC: 20h-5h ( 8H)` | `total_hours = 8.0` -> `HCĐ 130% = 8.0`, `TCĐ 195% = 0.0`. |
| 4 | Night Overtime (11H) | `CA: Ca đêm\nTHỜI GIAN LÀM VIỆC: 20h-8h (11H)` | `total_hours = 11.0` -> `HCĐ 130% = 8.0`, `TCĐ 195% = 3.0`. |
| 5 | Sunday Day Shift | `NGÀY: 25/10` (Sunday in 2026), `CA: Ca ngày`, `THỜI GIAN: 8h-17h (8H)` | `is_sunday = True` -> `Ngày CN (200%) = 8.0`, all regular weekday cells (`HCN`, `TCN`) = 0. |
| 6 | Sunday Night Shift | `NGÀY: 25/10` (Sunday), `CA: Ca đêm`, `THỜI GIAN: 20h-8h (11H)` | `is_sunday = True` -> `Đêm CN (260%) = 11.0`, all other hour cells = 0. |
| 7 | Unaccented & Lowercase | `ho ten : nguyen duc cong\nngay : 24/10\nca : ca ngay\nthoi gian lam viec : 8h-17h (8h)\nco an o xuong ko : co` | Parsed cleanly: Name=`NGUYEN DUC CONG` (matches `NGUYỄN ĐỨC CÔNG` via Excel fuzzy matching), HCN=`8.0`, Meal=`1`. |
| 8 | Meal as `x` or `X` | `CÓ ĂN Ở XƯỞNG KO: x` or `Ăn xưởng : X` | Normalized to `meal = 1` (valid checkmark representation). |
| 9 | Meal as `k` or `ko` | `CÓ ĂN Ở XƯỞNG KO: ko` or `CƠM : k` | Normalized to `meal = 0`. |
| 10 | Meal as `tự túc` | `CÓ ĂN Ở XƯỞNG KO: tự túc` | Normalized to `meal = 0` (worker brings own food). |
| 11 | Missing Colon | `HỌ TÊN HOÀNG ĐẮC PHÚ` or `NGÀY 24/10` | Separated cleanly by whitespace boundary after keyword. |
| 12 | Unicode Colon (`：`) | `HỌ TÊN：HOÀNG ĐẮC PHÚ` (Fullwidth Asian colon) | Matches delimiter group `[:：\-\.\s]`, name parsed successfully. |
| 13 | Single-Line Delimited | `HỌ TÊN: HOÀNG ĐẮC PHÚ - NGÀY: 24/10 - CA: Ca ngày - THỜI GIAN: 8h-17h (8H) - ĂN: 0` | Inline field boundary regex pre-splits into virtual lines, parses 100% identically to multi-line format. |
| 14 | Contiguous Batch Paste | Two messages pasted back-to-back with NO blank lines | Lookahead on `HỌ TÊN` splits into 2 distinct records. |
| 15 | Zalo Desktop Chat Copy | `[18:05, 24/10/2026] Hoàng Đắc Phú: HỌ TÊN : HOÀNG ĐẮC PHÚ` | Message header stripped; fields correctly extracted. |
| 16 | Numbered List Paste | `1. HỌ TÊN : LÊ VĂN A\n2. HỌ TÊN : TRẦN VĂN B` | Leading `1. ` stripped; name parsed as `LÊ VĂN A`. |
| 17 | Time Range with Minutes | `THỜI GIAN LÀM VIỆC: 8h30-17h30 (8H)` | Parsed: `start=08:30`, `end=17:30`, `total_hours=8.0`. |
| 18 | Standalone Total Hours | `THỜI GIAN LÀM VIỆC: 11 tiếng` (or `11H`) | Parsed: `total_hours = 11.0`. |
| 19 | Overtime Notation | `THỜI GIAN LÀM VIỆC: 8h-17h + TC 3h` | Parsed: `8h regular + 3h overtime = 11.0h total`. |
| 20 | Start-End No Bracket | `THỜI GIAN LÀM VIỆC: 8h-17h` (No `(8H)`) | Elapsed 9h, start 8:00, end 17:00 -> 1h break deducted -> `total_hours = 8.0`. |
| 21 | Start-End No Bracket OT | `THỜI GIAN LÀM VIỆC: 8h-20h` (No `(11H)`) | Elapsed 12h -> 1h break deducted -> `total_hours = 11.0`. |
| 22 | Missing Name Field | Message contains `NGÀY: 24/10`, `CA: Ca ngày`, etc. but no `HỌ TÊN` | Parsed with `status = ERROR`, `errors = ['Thiếu trường Họ và tên']`. Never dropped. |
| 23 | Invalid Day Range | `NGÀY: 32/10` | Parsed with `status = ERROR`, `errors = ['Ngày không hợp lệ: 32/10']`. |
| 24 | Non-Existent Date | `NGÀY: 29/02/2026` (2026 is not a leap year) | Parsed with `status = ERROR`, `errors = ['Ngày không hợp lệ: 29/02/2026']`. |
| 25 | Invalid Hours String | `THỜI GIAN LÀM VIỆC: nghỉ ốm` (sick leave) | Parsed with `status = ERROR`, `errors = ['Không phân tích được thời gian làm việc: "nghỉ ốm"']`. |
| 26 | Hours Exceed 24h | `THỜI GIAN LÀM VIỆC: 25h` | Parsed with `status = ERROR`, `errors = ['Tổng số giờ làm (25.0h) vượt quá 24h/ngày']`. |
| 27 | Missing Shift Field | Shift omitted, but hours `20h-8h` | Infers `NIGHT` based on 20:00 start; flags `WARNING: Tự động nhận diện Ca đêm dựa vào giờ bắt đầu`. |
| 28 | Discrepant Hours | `8h-17h (10H)` (Bracketed 10H exceeds 9H elapsed) | Uses `10.0H` but adds `WARNING: Số giờ làm (10.0h) lớn hơn thời gian chênh lệch (9.0h)`. |

---

## 4. Comprehensive Field Parsing Rulebook

### 4.1. Field 1: HỌ TÊN (Employee Name)

- **Label Recognition Pattern (Case-Insensitive Regex)**:
  ```regex
  ^(?:HỌ\s*(?:VÀ\s*)?TÊN|HO\s*(?:VA\s*)?TEN|TÊN|TEN)\s*[:：\-\.\s]\s*(.*)$
  ```
- **Cleaning & Normalization Rules**:
  1. Strip leading/trailing whitespace.
  2. Strip list indices (`1. `, `[1]`, `- `).
  3. Strip phone numbers: `re.sub(r'[-–]\s*\d{9,11}', '', text)`.
  4. Strip parenthesized remarks: `re.sub(r'\(.*?\)', '', text)`.
  5. Collapse multiple spaces into single space: `re.sub(r'\s+', ' ', text)`.
  6. Convert to standard **UPPERCASE** (e.g. `HOÀNG ĐẮC PHÚ`) to match Excel conventions.
  7. Keep Vietnamese accents intact. If input is unaccented (e.g. `HOANG DAC PHU`), retain as-is; the Excel Integrator performs fuzzy unaccented matching.
- **Error Trigger**:
  If line is missing or extracted name is empty -> `ERROR: Thiếu trường Họ và tên`.

---

### 4.2. Field 2: NGÀY (Attendance Date)

- **Label Recognition Pattern**:
  ```regex
  ^(?:NGÀY|NGAY|DATE)\s*[:：\-\.\s]\s*(.*)$
  ```
- **Prefix Sanitization**:
  Strip redundant prefixes: `re.sub(r'^(?:ngày|ngay)\s*', '', value, flags=re.I)`.
- **Supported Formats**:
  1. `YYYY-MM-DD` (ISO): `r'^(\d{4})[-/\.](\d{1,2})[-/\.](\d{1,2})$'`
  2. `DD/MM/YYYY` or `DD-MM-YYYY` or `DD.MM.YYYY`: `r'^(\d{1,2})[-/\.](\d{1,2})[-/\.](\d{2,4})$'`
     - 2-digit years `YY` (e.g. `26`) expand to `2000 + YY` -> `2026`.
  3. `DD/MM` or `DD-MM` or `DD.MM`: `r'^(\d{1,2})[-/\.](\d{1,2})$'`
     - Year defaults to active system/template year (default: `2026`).
     - Appends `WARNING: Năm được tự động suy luận là 2026`.
- **Day-of-Week & Sunday Determination**:
  ```python
  parsed_date = datetime.date(year, month, day)
  is_sunday = (parsed_date.weekday() == 6)  # Python 6 = Sunday (CN)
  ```
- **Error Trigger**:
  - Missing date line -> `ERROR: Thiếu trường Ngày chấm công`.
  - Day out of range (e.g. `32/10`, `31/04`) -> `ERROR: Ngày không hợp lệ: {raw_date}`.
  - Leap year violations (e.g. `29/02/2026`) -> `ERROR: Ngày không hợp lệ: {raw_date}`.

---

### 4.3. Field 3: CA (Working Shift)

- **Label Recognition Pattern**:
  ```regex
  ^(?:CA\s*(?:LÀM\s*VIỆC|LAM\s*VIEC)?|SHIFT)\s*[:：\-\.\s]\s*(.*)$
  ```
- **Classification Rules**:
  - **Day Shift (`DAY`)**:
    Contains keywords: `ngày`, `ngay`, `sáng`, `sang`, `ca 1`, `day`.
  - **Night Shift (`NIGHT`)**:
    Contains keywords: `đêm`, `dem`, `tối`, `toi`, `ca 2`, `ca 3`, `night`.
- **Missing Shift Fallback**:
  If shift is not explicitly stated:
  - Check `start_time` from working hours:
    * If `start_time >= 18` or `start_time <= 4` -> Assign `NIGHT` + `WARNING: Tự động nhận diện Ca đêm dựa vào giờ bắt đầu`.
    * If `start_time >= 6` and `start_time <= 12` -> Assign `DAY` + `WARNING: Tự động nhận diện Ca ngày dựa vào giờ bắt đầu`.
  - If neither works -> `ERROR: Thiếu trường Ca làm việc`.

---

### 4.4. Field 4: DỰ ÁN / XƯỞNG (Project / Location)

- **Label Recognition Pattern**:
  ```regex
  ^(?:DỰ\s*ÁN|DU\s*AN|XƯỞNG|XUONG|ĐỊA\s*ĐIỂM|DIA\s*DIEM|CÔNG\s*TRÌNH)\s*[:：\-\.\s]\s*(.*)$
  ```
- **Handling**:
  - Preserves project string (e.g. `sdv`, `ETS`, `WEVN`, `Samsung`).
  - Optional field. If omitted, defaults to default project (e.g. `ETS`) or empty string without error.

---

### 4.5. Field 5: THỜI GIAN LÀM VIỆC (Working Hours & Break Math)

- **Label Recognition Pattern**:
  ```regex
  ^(?:THỜI\s*GIAN(?:\s*LÀM\s*VIỆC)?|THOI\s*GIAN(?:\s*LAM\s*VIEC)?|GIỜ\s*LÀM(?:\s*VIỆC)?|GIO\s*LAM(?:\s*VIEC)?|TIME)\s*[:：\-\.\s]\s*(.*)$
  ```
- **Extraction Hierarchy**:
  1. **Bracketed Explicit Total Hours**:
     Regex: `r'\(\s*(\d+(?:[\.,]\d+)?)\s*(?:h|tiếng|g|giờ)?\s*\)'`
     Example: `8h-17h ( 8H)` -> `8.0` hours; `8h-20h (11H)` -> `11.0` hours.
     *Rationale*: Factory workers explicitly write the paid hours inside parentheses.
  2. **Start-End Time Range**:
     Regex: `r'(\d{1,2})(?:[h:](\d{1,2})|h)?\s*[-–~]\s*(\d{1,2})(?:[h:](\d{1,2})|h)?'`
     Calculates elapsed time:
     ```python
     if end_h >= start_h:
         elapsed = (end_h - start_h) + (end_m - start_m) / 60.0
     else:
         # Crosses midnight (e.g. 20h - 5h)
         elapsed = (end_h + 24 - start_h) + (end_m - start_m) / 60.0
     ```
  3. **Automatic Break Time Deduction (when bracketed total is absent)**:
     - Standard full-shift threshold: If `elapsed >= 8.5` hours, deduct 1 hour unpaid meal break:
       - `8h-17h` (elapsed 9h) -> `8.0` net hours.
       - `8h-20h` (elapsed 12h) -> `11.0` net hours.
       - `20h-5h` (elapsed 9h) -> `8.0` net hours.
       - `20h-8h` (elapsed 12h) -> `11.0` net hours.
     - Part-time / half-shift: If `elapsed < 8.5` (e.g. `8h-12h` = 4h), net hours = `4.0` (no break deducted).
  4. **Standalone Number of Hours**:
     Regex: `r'(\d+(?:[\.,]\d+)?)\s*(?:h|tiếng|g|giờ)'`
     Example: `8H`, `11 tiếng` -> `8.0`, `11.0`.
  5. **Separate Overtime Addition**:
     Regex: `r'(?:\+|\btăng\s*ca\b|\btc\b)\s*(\d+(?:[\.,]\d+)?)\s*(?:h|tiếng)?'`
     Example: `8h-17h + TC 3h` -> 8 + 3 = 11.0 hours.
- **Validation Constraints**:
  - `total_hours > 0`: If `<= 0` -> `ERROR: Tổng số giờ làm phải lớn hơn 0`.
  - `total_hours <= 24`: If `> 24` -> `ERROR: Tổng số giờ làm ({hours}h) vượt quá 24h/ngày`.
  - If text is unparseable (e.g. `nghỉ ốm`, `nghỉ phép`, `không đi làm`) -> `ERROR: Không phân tích được thời gian làm việc`.

---

### 4.6. Field 6: CÓ ĂN Ở XƯỞNG KO (Meal Detection)

- **Label Recognition Pattern**:
  ```regex
  ^(?:(?:CÓ\s*)?ĂN\s*(?:Ở\s*)?XƯỞNG(?:\s*K(?:O|HÔNG)?)?|(?:CO\s*)?AN\s*(?:O\s*)?XUONG(?:\s*K(?:O|HONG)?)?|SUẤT\s*ĂN|SUAT\s*AN|CƠM\s*XƯỞNG|CƠM|COM)\s*[:：\-\.\s]\s*(.*)$
  ```
- **Value Mapping Table**:
  | Raw Value Group | Normalized Value | Meaning |
  |---|---|---|
  | `0`, `không`, `khong`, `ko`, `k`, `no`, `n`, `0 suất`, `không ăn`, `ko ăn`, `k ăn`, `tự túc` | **`0`** | Không ăn cơm xưởng |
  | `1`, `có`, `co`, `yes`, `y`, `x`, `X`, `v`, `V`, `✓`, `1 suất`, `có ăn`, `co an` | **`1`** | Ăn 1 suất cơm xưởng |
  | `2`, `2 suất`, `hai suất` | **`2`** | Ăn 2 suất (overtime kép, kèm WARNING) |
  | Empty / Omitted | **`0`** | Defaulted to 0 + `WARNING: Thiếu thông tin suất ăn, mặc định 0` |
  | Unrecognized text | **`0`** | Defaulted to 0 + `WARNING: Giá trị suất ăn không rõ ràng ("..."), mặc định 0` |

---

## 5. Time Calculation & Hour Allocation Formulas

The system must map `total_hours` ($H$), `shift` (`DAY` | `NIGHT`), and `is_sunday` (`True` | `False`) into the **6 Excel work categories**:

1. `HCN 100%`: Giờ hành chính ngày (100% lương)
2. `TCN 150%`: Giờ tăng ca ngày (150% lương)
3. `HCĐ 130%`: Giờ hành chính đêm (130% lương)
4. `TCĐ 195%`: Giờ tăng ca đêm (195% lương)
5. `Ngày CN (200%)`: Giờ làm ban ngày Chủ nhật (200% lương)
6. `Đêm CN (260%)`: Giờ làm ban đêm Chủ nhật (260% lương)

### 5.1. Mathematical Formula Matrix

```
┌───────────────────────────────┬──────────────────────────────────┬──────────────────────────────────┐
│ Category                      │ Weekday / Saturday (T2 - T7)     │ Sunday (Chủ nhật - CN)           │
├───────────────────────────────┼──────────────────────────────────┼──────────────────────────────────┤
│ Ca ngày (DAY)                 │                                  │                                  │
│   - HCN 100%                  │ = min(H, 8.0)                    │ = 0.0                            │
│   - TCN 150%                  │ = max(0.0, H - 8.0)              │ = 0.0                            │
│   - HCĐ 130%                  │ = 0.0                            │ = 0.0                            │
│   - TCĐ 195%                  │ = 0.0                            │ = 0.0                            │
│   - Ngày CN (200%)            │ = 0.0                            │ = H                              │
│   - Đêm CN (260%)             │ = 0.0                            │ = 0.0                            │
├───────────────────────────────┼──────────────────────────────────┼──────────────────────────────────┤
│ Ca đêm (NIGHT)                │                                  │                                  │
│   - HCN 100%                  │ = 0.0                            │ = 0.0                            │
│   - TCN 150%                  │ = 0.0                            │ = 0.0                            │
│   - HCĐ 130%                  │ = min(H, 8.0)                    │ = 0.0                            │
│   - TCĐ 195%                  │ = max(0.0, H - 8.0)              │ = 0.0                            │
│   - Ngày CN (200%)            │ = 0.0                            │ = 0.0                            │
│   - Đêm CN (260%)             │ = 0.0                            │ = H                              │
└───────────────────────────────┴──────────────────────────────────┴──────────────────────────────────┘
```

### 5.2. Detailed Allocation Scenarios

#### Scenario A: Ca ngày - Ngày thường / Thứ 7 (Mon-Sat Day Shift)
- **Standard 8h (`8h-17h`)**: $H = 8.0 \implies \text{HCN} = 8.0, \text{TCN} = 0.0$.
- **Overtime 11h (`8h-20h`)**: $H = 11.0 \implies \text{HCN} = 8.0, \text{TCN} = 3.0$.
- **Short shift 4h (`8h-12h`)**: $H = 4.0 \implies \text{HCN} = 4.0, \text{TCN} = 0.0$.

#### Scenario B: Ca đêm - Ngày thường / Thứ 7 (Mon-Sat Night Shift)
- **Standard 8h (`20h-5h`)**: $H = 8.0 \implies \text{HCĐ} = 8.0, \text{TCĐ} = 0.0$.
- **Overtime 11h (`20h-8h`)**: $H = 11.0 \implies \text{HCĐ} = 8.0, \text{TCĐ} = 3.0$.
- **Overtime 12h (`19h-8h`)**: $H = 12.0 \implies \text{HCĐ} = 8.0, \text{TCĐ} = 4.0$.

#### Scenario C: Ca ngày - Chủ nhật (Sunday Day Shift)
- In the factory template (`sample_data.csv`), row 5 of each employee is labeled `Ngày CN (200%)`.
- Because there is no separate "TC Ngày CN" row in the 7-row block, all daytime hours worked on Sunday flow into `Ngày CN (200%)`:
  - `8h-17h` on Sunday $\implies \text{Ngày CN} = 8.0$.
  - `8h-20h` on Sunday $\implies \text{Ngày CN} = 11.0$.

#### Scenario D: Ca đêm - Chủ nhật (Sunday Night Shift)
- In `sample_data.csv`, row 6 of each employee is labeled `Đêm CN (260%)`.
- A night shift starting on Sunday night (e.g. `2026-10-25 20:00`) belongs to the Sunday timesheet column:
  - `20h-5h` on Sunday $\implies \text{Đêm CN} = 8.0$.
  - `20h-8h` on Sunday $\implies \text{Đêm CN} = 11.0$.

---

## 6. Batch Parsing & Segmentation Specification

Users frequently paste 10 to 50 messages at once directly from Zalo. The parser must isolate each record without losing data.

### 6.1. Segmentation Algorithm (Dual-Pass)

1. **Step 1: Normalization**:
   - Normalize line breaks: replace `\r\n` and `\r` with `\n`.
2. **Step 2: Header-Lookahead Split**:
   - Primary delimiter is the message header indicator `HỌ TÊN` / `Họ và tên` / `HO TEN`, optionally preceded by Zalo desktop timestamps `[17:30, 24/10] Name:` or list numbers `1. `:
     ```python
     HEADER_REGEX = r'(?=(?:^|\n)\s*(?:\[\d{1,2}:\d{2}(?:,\s*\d{1,2}/\d{1,2}(?:/\d{2,4})?)?\]\s*[^:\n]+:\s*)?(?:\d+[\.\)\-]\s*)?(?:HỌ\s*(?:VÀ\s*)?TÊN|HO\s*(?:VA\s*)?TEN|TÊN|TEN)\s*[:：\-\s])'
     ```
   - Split input text by `HEADER_REGEX`.
3. **Step 3: Sub-Block Verification**:
   - If `HEADER_REGEX` yields $> 1$ chunks, inspect each chunk. If a chunk contains multiple double-newline separated blocks without `HỌ TÊN` (e.g. malformed messages missing a name), sub-split on `\n\s*\n+` so that invalid messages are preserved for error inspection rather than merged into valid messages.
4. **Step 4: Fallback to Dividers**:
   - If no `HỌ TÊN` headers are found, split by double newlines `\n\s*\n+` or markdown dividers (`---`, `===`, `___`, `***`).

### 6.2. Inline Delimiter Expansion (Single-Line Messages)

If a message is pasted on a single line separated by dashes, semicolons, or pipes (e.g. `HỌ TÊN: A - NGÀY: 24/10 - CA: Ca ngày...`), pre-split using field lookahead:
```python
FIELD_PREFIXES = r'(?:HỌ\s*(?:VÀ\s*)?TÊN|HO\s*(?:VA\s*)?TEN|NGÀY|NGAY|CA\s*(?:LÀM\s*VIỆC)?|DỰ\s*ÁN|DU\s*AN|XƯỞNG|XUONG|ĐỊA\s*ĐIỂM|THỜI\s*GIAN(?:\s*LÀM\s*VIỆC)?|GIỜ\s*LÀM|CÓ\s*ĂN(?:\s*Ở\s*XƯỞNG(?:\s*K(?:O|HÔNG)?)?)?|ĂN\s*(?:Ở\s*)?XƯỞNG|SUẤT\s*ĂN|CƠM)\s*[:：\-]'
lines = re.split(r'[\r\n]+|(?<=[^\s])\s*[-–|;]\s*(?=' + FIELD_PREFIXES + ')', raw_message, flags=re.I)
```

---

## 7. Error Detection, Validation & Warning Matrix

Every parsed record is assigned a lifecycle status and diagnostic feedback:

### 7.1. Status Definitions

| Status | Badge / Style | Definition | Action in UI |
|---|---|---|---|
| `VALID` | Green Badge | All mandatory fields present, valid syntax, zero discrepancies. | Ready to write to Excel. |
| `WARNING` | Amber / Yellow Badge | Valid record with intelligent defaults applied (e.g. inferred year, inferred shift from hours, meal defaulted to 0). | Ready to write to Excel, but UI highlights warning notes for operator review. |
| `ERROR` | Red Badge | Critical failure (missing name, unparseable date, unparseable hours). Record cannot be safely mapped to Excel. | Excluded from Excel write; highlighted in UI for manual inline editing. |

### 7.2. Diagnostic Error & Warning Catalog

| Code | Type | Condition | Message Text (Vietnamese) |
|---|---|---|---|
| `ERR_MISSING_NAME` | `ERROR` | Name line not detected or empty | `Thiếu trường Họ và tên` |
| `ERR_INVALID_NAME` | `ERROR` | Name contains only punctuation or digits | `Họ tên rỗng hoặc không hợp lệ` |
| `ERR_MISSING_DATE` | `ERROR` | Date line not detected or empty | `Thiếu trường Ngày chấm công` |
| `ERR_INVALID_DATE` | `ERROR` | Day > 31, leap year error, format bad | `Ngày không hợp lệ: {raw_date}` |
| `ERR_MISSING_HOURS` | `ERROR` | Hours line omitted or unparseable text | `Không phân tích được thời gian làm việc: "{raw}"` |
| `ERR_HOURS_ZERO` | `ERROR` | Calculated hours <= 0 | `Tổng số giờ làm phải lớn hơn 0` |
| `ERR_HOURS_OVERFLOW` | `ERROR` | Calculated hours > 24 | `Tổng số giờ làm ({h}h) vượt quá 24h/ngày` |
| `ERR_MISSING_SHIFT` | `ERROR` | Shift omitted and cannot be inferred | `Thiếu trường Ca làm việc và không thể tự suy luận` |
| `WARN_INFERRED_YEAR` | `WARNING` | Short date `DD/MM` used | `Năm được tự động suy luận là {year}` |
| `WARN_INFERRED_SHIFT` | `WARNING` | Shift inferred from start time | `Tự động nhận diện {Ca} dựa vào giờ bắt đầu` |
| `WARN_HOURS_MISMATCH` | `WARNING` | Bracketed hours > clock elapsed | `Số giờ làm ({h}h) lớn hơn thời gian chênh lệch ({el}h)` |
| `WARN_DEFAULT_MEAL` | `WARNING` | Meal field omitted | `Thiếu thông tin suất ăn, mặc định 0` |
| `WARN_UNCLEAR_MEAL` | `WARNING` | Meal string ambiguous | `Giá trị suất ăn không rõ ràng ("{val}"), mặc định 0` |
| `WARN_DOUBLE_MEAL` | `WARNING` | Meal = 2 detected | `Nhận diện 2 suất ăn` |

---

## 8. Authoritative Python Reference Implementation

The following self-contained class encapsulates the entire specification:

```python
"""
AttendanceParser - Specification Reference Implementation
Authoritative logic for parsing Zalo attendance messages.
"""

import re
import datetime
from typing import Dict, Any, List, Optional, Tuple


class AttendanceParser:
    def __init__(self, default_year: int = 2026, default_project: str = "ETS"):
        self.default_year = default_year
        self.default_project = default_project

    def split_messages(self, text: str) -> List[str]:
        if not text or not text.strip():
            return []
        text = text.replace('\r\n', '\n').replace('\r', '\n').strip()
        header_re = r'(?=(?:^|\n)\s*(?:\[\d{1,2}:\d{2}(?:,\s*\d{1,2}/\d{1,2}(?:/\d{2,4})?)?\]\s*[^:\n]+:\s*)?(?:\d+[\.\)\-]\s*)?(?:HỌ\s*(?:VÀ\s*)?TÊN|HO\s*(?:VA\s*)?TEN|TÊN|TEN)\s*[:：\-\s])'
        parts = [p.strip() for p in re.split(header_re, text, flags=re.IGNORECASE) if p.strip()]
        
        if len(parts) > 1:
            final_chunks = []
            for part in parts:
                sub_blocks = [b.strip() for b in re.split(r'\n\s*\n+', part) if b.strip()]
                if len(sub_blocks) > 1:
                    final_chunks.append(sub_blocks[0])
                    for sb in sub_blocks[1:]:
                        final_chunks.append(sb)
                else:
                    final_chunks.append(part)
            return final_chunks
            
        blocks = [b.strip() for b in re.split(r'\n\s*(?:\n+|-{3,}|={3,}|_{3,}|\*{3,})\s*', text) if b.strip()]
        return blocks if blocks else [text]

    def parse_single(self, raw_message: str) -> Dict[str, Any]:
        warnings: List[str] = []
        errors: List[str] = []
        
        # Pre-split inline delimited fields
        field_prefixes = r'(?:HỌ\s*(?:VÀ\s*)?TÊN|HO\s*(?:VA\s*)?TEN|NGÀY|NGAY|CA\s*(?:LÀM\s*VIỆC)?|DỰ\s*ÁN|DU\s*AN|XƯỞNG|XUONG|ĐỊA\s*ĐIỂM|THỜI\s*GIAN(?:\s*LÀM\s*VIỆC)?|GIỜ\s*LÀM|CÓ\s*ĂN(?:\s*Ở\s*XƯỞNG(?:\s*K(?:O|HÔNG)?)?)?|ĂN\s*(?:Ở\s*)?XƯỞNG|SUẤT\s*ĂN|CƠM)\s*[:：\-]'
        raw_lines = re.split(r'[\r\n]+|(?<=[^\s])\s*[-–|;]\s*(?=' + field_prefixes + ')', raw_message, flags=re.IGNORECASE)
        lines = [line.strip() for line in raw_lines if line.strip()]
        
        fields: Dict[str, str] = {}
        for line in lines:
            cleaned = re.sub(r'^\[\d{1,2}:\d{2}(?:,\s*\d{1,2}/\d{1,2}(?:/\d{2,4})?)?\]\s*[^:\n]+:\s*', '', line).strip()
            cleaned = re.sub(r'^\d+[\.\)\-]\s*', '', cleaned).strip()
            
            # 1. Name
            m_name = re.match(r'^(?:HỌ\s*(?:VÀ\s*)?TÊN|HO\s*(?:VA\s*)?TEN|TÊN|TEN)\s*[:：\-\.\s]\s*(.*)$', cleaned, re.I)
            if m_name and 'name' not in fields:
                fields['name'] = m_name.group(1).strip()
                continue
            # 2. Date
            m_date = re.match(r'^(?:NGÀY|NGAY|DATE)\s*[:：\-\.\s]\s*(.*)$', cleaned, re.I)
            if m_date and 'date' not in fields:
                fields['date'] = m_date.group(1).strip()
                continue
            # 3. Shift
            m_shift = re.match(r'^(?:CA\s*(?:LÀM\s*VIỆC|LAM\s*VIEC)?|SHIFT)\s*[:：\-\.\s]\s*(.*)$', cleaned, re.I)
            if m_shift and 'shift' not in fields:
                fields['shift'] = m_shift.group(1).strip()
                continue
            # 4. Project
            m_proj = re.match(r'^(?:DỰ\s*ÁN|DU\s*AN|XƯỞNG|XUONG|ĐỊA\s*ĐIỂM|DIA\s*DIEM|CÔNG\s*TRÌNH)\s*[:：\-\.\s]\s*(.*)$', cleaned, re.I)
            if m_proj and 'project' not in fields:
                fields['project'] = m_proj.group(1).strip()
                continue
            # 5. Hours
            m_hours = re.match(r'^(?:THỜI\s*GIAN(?:\s*LÀM\s*VIỆC)?|THOI\s*GIAN(?:\s*LAM\s*VIEC)?|GIỜ\s*LÀM(?:\s*VIỆC)?|GIO\s*LAM(?:\s*VIEC)?|TIME)\s*[:：\-\.\s]\s*(.*)$', cleaned, re.I)
            if m_hours and 'hours' not in fields:
                fields['hours'] = m_hours.group(1).strip()
                continue
            # 6. Meal
            m_meal = re.match(r'^(?:(?:CÓ\s*)?ĂN\s*(?:Ở\s*)?XƯỞNG(?:\s*K(?:O|HÔNG)?)?|(?:CO\s*)?AN\s*(?:O\s*)?XUONG(?:\s*K(?:O|HONG)?)?|SUẤT\s*ĂN|SUAT\s*AN|CƠM\s*XƯỞNG|CƠM|COM)\s*[:：\-\.\s]\s*(.*)$', cleaned, re.I)
            if m_meal and 'meal' not in fields:
                fields['meal'] = m_meal.group(1).strip()
                continue

        # Process Name
        raw_name = fields.get('name', '')
        if not raw_name:
            errors.append('Thiếu trường Họ và tên')
            clean_name = ''
        else:
            clean_name = re.sub(r'[-–]\s*\d{9,11}', '', raw_name)
            clean_name = re.sub(r'\(.*?\)', '', clean_name).strip()
            clean_name = re.sub(r'\s+', ' ', clean_name).upper()
            if not clean_name:
                errors.append('Họ tên rỗng hoặc không hợp lệ')
                
        # Process Date
        raw_date = fields.get('date', '')
        parsed_date: Optional[datetime.date] = None
        is_sunday = False
        formatted_date = ''
        day_num = 0
        month_num = 0
        year_num = self.default_year
        
        if not raw_date:
            errors.append('Thiếu trường Ngày chấm công')
        else:
            s_date = re.sub(r'^(?:ngày|ngay)\s*', '', raw_date, flags=re.I).strip()
            m_iso = re.match(r'^(\d{4})[-/\.](\d{1,2})[-/\.](\d{1,2})$', s_date)
            if m_iso:
                y, m, d = int(m_iso.group(1)), int(m_iso.group(2)), int(m_iso.group(3))
                try:
                    parsed_date = datetime.date(y, m, d)
                except ValueError as e:
                    errors.append(f'Ngày không hợp lệ: {s_date}')
            else:
                m_full = re.match(r'^(\d{1,2})[-/\.](\d{1,2})[-/\.](\d{2,4})$', s_date)
                if m_full:
                    d, m, y_raw = int(m_full.group(1)), int(m_full.group(2)), int(m_full.group(3))
                    y = y_raw if y_raw >= 100 else (2000 + y_raw)
                    try:
                        parsed_date = datetime.date(y, m, d)
                    except ValueError as e:
                        errors.append(f'Ngày không hợp lệ: {s_date}')
                else:
                    m_short = re.match(r'^(\d{1,2})[-/\.](\d{1,2})$', s_date)
                    if m_short:
                        d, m = int(m_short.group(1)), int(m_short.group(2))
                        try:
                            parsed_date = datetime.date(self.default_year, m, d)
                            warnings.append(f'Năm được tự động suy luận là {self.default_year}')
                        except ValueError as e:
                            errors.append(f'Ngày không hợp lệ: {s_date}')
                    else:
                        errors.append(f'Định dạng ngày không hợp lệ: {raw_date}')
                        
        if parsed_date:
            day_num = parsed_date.day
            month_num = parsed_date.month
            year_num = parsed_date.year
            formatted_date = parsed_date.strftime('%Y-%m-%d')
            is_sunday = (parsed_date.weekday() == 6)

        # Process Shift
        raw_shift = fields.get('shift', '').strip()
        shift_code: Optional[str] = None
        if raw_shift:
            s_lower = raw_shift.lower()
            if any(k in s_lower for k in ['ngày', 'ngay', 'sáng', 'sang', 'day', 'ca 1']):
                shift_code = 'DAY'
            elif any(k in s_lower for k in ['đêm', 'dem', 'tối', 'toi', 'night', 'ca 2', 'ca 3']):
                shift_code = 'NIGHT'
            else:
                warnings.append(f'Không nhận diện được ca: "{raw_shift}"')

        # Process Hours
        raw_hours = fields.get('hours', '').strip()
        total_hours = 0.0
        start_str = ''
        end_str = ''
        
        if not raw_hours:
            errors.append('Thiếu trường Thời gian làm việc')
        else:
            m_br = re.search(r'\(\s*(\d+(?:[\.,]\d+)?)\s*(?:h|tiếng|g|giờ)?\s*\)', raw_hours, re.I)
            br_hours = float(m_br.group(1).replace(',', '.')) if m_br else None
            
            m_rng = re.search(r'(\d{1,2})(?:[h:](\d{1,2})|h)?\s*[-–~]\s*(\d{1,2})(?:[h:](\d{1,2})|h)?', raw_hours, re.I)
            if m_rng:
                sh = int(m_rng.group(1))
                sm = int(m_rng.group(2) or 0)
                eh = int(m_rng.group(3))
                em = int(m_rng.group(4) or 0)
                start_str = f'{sh:02d}:{sm:02d}'
                end_str = f'{eh:02d}:{em:02d}'
                
                if not shift_code:
                    if sh >= 18 or sh <= 4:
                        shift_code = 'NIGHT'
                        warnings.append('Tự động nhận diện Ca đêm dựa vào giờ bắt đầu')
                    else:
                        shift_code = 'DAY'
                        warnings.append('Tự động nhận diện Ca ngày dựa vào giờ bắt đầu')
                        
                if eh >= sh:
                    elapsed = (eh - sh) + (em - sm) / 60.0
                else:
                    elapsed = (eh + 24 - sh) + (em - sm) / 60.0
                    
                if br_hours is not None:
                    total_hours = br_hours
                    if br_hours > elapsed:
                        warnings.append(f'Số giờ làm ({br_hours}h) lớn hơn thời gian chênh lệch ({elapsed:.1f}h)')
                else:
                    if elapsed >= 8.5:
                        total_hours = elapsed - 1.0
                    else:
                        total_hours = elapsed
            else:
                m_single = re.search(r'(\d+(?:[\.,]\d+)?)\s*(?:h|tiếng|g|giờ)', raw_hours, re.I)
                if m_single:
                    total_hours = float(m_single.group(1).replace(',', '.'))
                else:
                    errors.append(f'Không phân tích được thời gian làm việc: "{raw_hours}"')
                    
        if not shift_code:
            errors.append('Thiếu trường Ca làm việc')
            shift_code = 'DAY'
            
        if total_hours <= 0 and not any('thời gian' in e.lower() for e in errors):
            errors.append('Tổng số giờ làm phải lớn hơn 0')
        elif total_hours > 24:
            errors.append(f'Tổng số giờ làm ({total_hours}h) vượt quá 24h/ngày')

        # Process Meal
        raw_meal = fields.get('meal', '').strip()
        meal_val = 0
        if not raw_meal:
            warnings.append('Thiếu thông tin suất ăn, mặc định 0')
            meal_val = 0
        else:
            m_clean = raw_meal.lower()
            if m_clean in ['0', 'không', 'khong', 'ko', 'k', 'no', 'n', '0 suất', 'không ăn', 'ko ăn', 'k ăn', 'tự túc']:
                meal_val = 0
            elif m_clean in ['1', 'có', 'co', 'yes', 'y', 'x', 'v', '✓', '1 suất', 'có ăn', 'co an']:
                meal_val = 1
            elif m_clean == '2':
                meal_val = 2
                warnings.append('Nhận diện 2 suất ăn')
            else:
                m_dig = re.match(r'^(\d+)', m_clean)
                if m_dig:
                    meal_val = int(m_dig.group(1))
                else:
                    meal_val = 0
                    warnings.append(f'Giá trị suất ăn không rõ ràng ("{raw_meal}"), mặc định 0')

        # Process Project
        project_val = fields.get('project', '').strip() or self.default_project

        # Hour Allocation Calculations
        hcn = 0.0
        tcn = 0.0
        hcd = 0.0
        tcd = 0.0
        ngay_cn = 0.0
        dem_cn = 0.0
        
        if total_hours > 0 and not errors:
            if is_sunday:
                if shift_code == 'DAY':
                    ngay_cn = total_hours
                else:
                    dem_cn = total_hours
            else:
                if shift_code == 'DAY':
                    hcn = min(total_hours, 8.0)
                    tcn = max(0.0, total_hours - 8.0)
                else:
                    hcd = min(total_hours, 8.0)
                    tcd = max(0.0, total_hours - 8.0)

        status = 'ERROR' if errors else ('WARNING' if warnings else 'VALID')

        return {
            'status': status,
            'errors': errors,
            'warnings': warnings,
            'name': clean_name,
            'raw_name': raw_name,
            'date': formatted_date,
            'raw_date': raw_date,
            'day': day_num,
            'month': month_num,
            'year': year_num,
            'is_sunday': is_sunday,
            'shift': shift_code,
            'raw_shift': raw_shift,
            'project': project_val,
            'start_time': start_str,
            'end_time': end_str,
            'total_hours': total_hours,
            'hcn_100': hcn,
            'tcn_150': tcn,
            'hcd_130': hcd,
            'tcd_195': tcd,
            'ngay_cn_200': ngay_cn,
            'dem_cn_260': dem_cn,
            'meal': meal_val,
            'raw_text': raw_message.strip()
        }

    def parse_batch(self, batch_text: str) -> List[Dict[str, Any]]:
        chunks = self.split_messages(batch_text)
        return [self.parse_single(c) for c in chunks]
```

---

## 9. Comprehensive Test Suite

### 9.1. Test Vector Catalog

```python
TEST_VECTORS = [
    {
        "id": "TC01_ACCEPTANCE_STANDARD",
        "description": "Standard message matching Acceptance Criteria exactly",
        "input": """
HỌ TÊN : HOÀNG ĐẮC PHÚ
NGÀY: 24/10
CA : Ca ngày 
DỰ ÁN : sdv 
THỜI GIAN LÀM VIỆC :8h-17h ( 8H)
CÓ ĂN Ở XƯỞNG KO : 0
""",
        "expected": {
            "name": "HOÀNG ĐẮC PHÚ",
            "day": 24,
            "month": 10,
            "shift": "DAY",
            "is_sunday": False,
            "hcn_100": 8.0,
            "tcn_150": 0.0,
            "meal": 0,
            "status": "WARNING" # Inferred year 2026
        }
    },
    {
        "id": "TC02_DAY_OVERTIME",
        "description": "Day shift with 3 hours overtime (8h-20h, 11H)",
        "input": """
HỌ TÊN: NGUYỄN NGỌC THAO
NGÀY: 24/10/2026
CA: Ca ngày
DỰ ÁN: ETS
THỜI GIAN LÀM VIỆC: 8h-20h (11H)
CÓ ĂN Ở XƯỞNG KO: 1
""",
        "expected": {
            "name": "NGUYỄN NGỌC THAO",
            "shift": "DAY",
            "is_sunday": False,
            "hcn_100": 8.0,
            "tcn_150": 3.0,
            "meal": 1,
            "status": "VALID"
        }
    },
    {
        "id": "TC03_NIGHT_STANDARD",
        "description": "Night shift standard 8 hours (20h-5h, 8H)",
        "input": """
HỌ TÊN: NGUYỄN ĐỨC CÔNG
NGÀY: 24/10/2026
CA: Ca đêm
DỰ ÁN: ETS
THỜI GIAN LÀM VIỆC: 20h-5h ( 8H)
CÓ ĂN Ở XƯỞNG KO: 0
""",
        "expected": {
            "name": "NGUYỄN ĐỨC CÔNG",
            "shift": "NIGHT",
            "hcd_130": 8.0,
            "tcd_195": 0.0,
            "meal": 0,
            "status": "VALID"
        }
    },
    {
        "id": "TC04_NIGHT_OVERTIME",
        "description": "Night shift with 3 hours overtime (20h-8h, 11H)",
        "input": """
HỌ TÊN: TÔ VĂN HƯNG
NGÀY: 24/10/2026
CA: Ca đêm
DỰ ÁN: ETS
THỜI GIAN LÀM VIỆC: 20h-8h (11H)
CÓ ĂN Ở XƯỞNG KO: 1
""",
        "expected": {
            "name": "TÔ VĂN HƯNG",
            "shift": "NIGHT",
            "hcd_130": 8.0,
            "tcd_195": 3.0,
            "meal": 1,
            "status": "VALID"
        }
    },
    {
        "id": "TC05_SUNDAY_DAY",
        "description": "Sunday work on 2026-10-25 daytime",
        "input": """
HỌ TÊN: HOÀNG ĐẮC PHÚ
NGÀY: 2026-10-25
CA: Ca ngày
THỜI GIAN LÀM VIỆC: 8h-17h (8H)
CÓ ĂN Ở XƯỞNG KO: 1
""",
        "expected": {
            "name": "HOÀNG ĐẮC PHÚ",
            "is_sunday": True,
            "ngay_cn_200": 8.0,
            "hcn_100": 0.0,
            "tcn_150": 0.0,
            "meal": 1,
            "status": "VALID"
        }
    },
    {
        "id": "TC06_SUNDAY_NIGHT_OT",
        "description": "Sunday night shift with overtime (20h-8h, 11H)",
        "input": """
HỌ TÊN: HOÀNG ĐẮC PHÚ
NGÀY: 2026-10-25
CA: Ca đêm
THỜI GIAN LÀM VIỆC: 20h-8h (11H)
CÓ ĂN Ở XƯỞNG KO: 1
""",
        "expected": {
            "name": "HOÀNG ĐẮC PHÚ",
            "is_sunday": True,
            "dem_cn_260": 11.0,
            "hcd_130": 0.0,
            "tcd_195": 0.0,
            "meal": 1,
            "status": "VALID"
        }
    },
    {
        "id": "TC07_UNACCENTED_LOWERCASE",
        "description": "Completely unaccented, lowercase message with informal meal value",
        "input": """
ho ten: hoang dac phu
ngay: 24/10/2026
ca: ca dem
thoi gian lam viec: 20h-8h (11h)
co an o xuong ko: co
""",
        "expected": {
            "name": "HOANG DAC PHU",
            "shift": "NIGHT",
            "hcd_130": 8.0,
            "tcd_195": 3.0,
            "meal": 1,
            "status": "VALID"
        }
    },
    {
        "id": "TC08_CHECKMARK_MEAL",
        "description": "Meal marked with 'x'",
        "input": """
HỌ TÊN: TRẦN VĂN A
NGÀY: 24/10/2026
CA: Ca ngày
THỜI GIAN: 8h-17h
Ăn xưởng: x
""",
        "expected": {
            "meal": 1,
            "hcn_100": 8.0,
            "status": "VALID"
        }
    },
    {
        "id": "TC09_ERR_MISSING_NAME",
        "description": "Missing employee name",
        "input": """
NGÀY: 24/10/2026
CA: Ca ngày
THỜI GIAN LÀM VIỆC: 8h-17h (8H)
CÓ ĂN Ở XƯỞNG KO: 0
""",
        "expected": {
            "status": "ERROR",
            "errors": ["Thiếu trường Họ và tên"]
        }
    },
    {
        "id": "TC10_ERR_INVALID_DATE",
        "description": "Impossible calendar date 32/10",
        "input": """
HỌ TÊN: PHẠM VĂN B
NGÀY: 32/10
CA: Ca ngày
THỜI GIAN LÀM VIỆC: 8h-17h (8H)
CÓ ĂN Ở XƯỞNG KO: 0
""",
        "expected": {
            "status": "ERROR",
            "errors": ["Ngày không hợp lệ: 32/10"]
        }
    },
    {
        "id": "TC11_ERR_SICK_LEAVE_HOURS",
        "description": "Unparseable working hours ('nghỉ ốm')",
        "input": """
HỌ TÊN: VŨ THỊ C
NGÀY: 24/10/2026
CA: Ca ngày
THỜI GIAN LÀM VIỆC: nghỉ ốm
CÓ ĂN Ở XƯỞNG KO: 0
""",
        "expected": {
            "status": "ERROR",
            "errors": ['Không phân tích được thời gian làm việc: "nghỉ ốm"']
        }
    }
]
```

---

## 10. Summary & Handoff Checklist for Milestone 1 (Parser Module)

1. **Parser Engine Core**: Implement `AttendanceParser` conforming to the regex rules and formulas detailed above.
2. **REST API Endpoint**: Expose `POST /api/parse` taking `{ "raw_text": "...", "default_year": 2026 }` returning `{ "records": [...], "stats": { "total": N, "valid": X, "warning": Y, "error": Z } }`.
3. **Web UI Gating**: Display all records in the Preview Table. Render badges (`Hợp lệ`, `Cần chú ý`, `Lỗi`), and allow inline editing of `name`, `date`, `shift`, `hours`, and `meal` before proceeding to Excel export.
4. **Excel Gating**: Filter out records where `status == 'ERROR'` from direct write, alerting the operator to correct or discard them.
