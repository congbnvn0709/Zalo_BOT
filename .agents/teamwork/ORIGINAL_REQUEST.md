# Original User Request

## 2026-10-26T07:15:49Z

Xây dựng ứng dụng Web cục bộ (Local Web App) hỗ trợ dán danh sách tin nhắn chấm công Zalo, tự động bóc tách quy đổi giờ làm (giờ hành chính, tăng ca, ca đêm, suất ăn), hiển thị giao diện trực quan cho phép kiểm tra/chỉnh sửa nhanh, và ghi tự động vào file Excel bảng chấm công theo đúng mẫu định sẵn.

Working directory: `/Users/congcm/CODE/Vibe_Code/Zalo_BOT`
Integrity mode: development

## Requirements

### R1. Bộ bóc tách cú pháp tin nhắn Zalo (Attendance Message Parser)
Hệ thống tiếp nhận khối văn bản thô gồm nhiều tin nhắn Zalo cùng lúc. Tự động bóc tách và chuẩn hóa các thông tin:
- Họ và tên ứng viên (chuẩn hóa tiếng Việt, không phân biệt hoa thường).
- Ngày chấm công (hỗ trợ định dạng `DD/MM` hoặc `YYYY-MM-DD`).
- Ca làm việc (`Ca ngày` hoặc `Ca đêm`).
- Dự án / Xưởng.
- Khung thời gian làm việc: Tự động phân tích giờ bắt đầu - kết thúc (ví dụ `8h-17h (8H)`, `8h-20h (11H)`) để tính toán chính xác:
  + Giờ hành chính ngày (100%)
  + Giờ tăng ca ngày (150%)
  + Giờ hành chính đêm (130%)
  + Giờ tăng ca đêm (195% / 200%)
  + Giờ làm ngày Chủ nhật (200% / 260% đêm)
- Suất ăn ở xưởng (nhận diện 0 hoặc 1).
- Tự động nhận diện các tin nhắn sai cú pháp hoặc thiếu thông tin cần thiết và gắn cờ cảnh báo.

### R2. Giao diện Web tương tác trực quan (Interactive Web Dashboard)
- Cung cấp ô nhập liệu (Text Area) để người dùng dán toàn bộ đoạn chat Zalo vào chỉ với một thao tác.
- Chức năng tải lên file Excel bảng chấm công mẫu (hoặc chọn file mẫu mặc định trong thư mục dự án).
- Bảng xem trước (Preview Table): Hiển thị chi tiết danh sách nhân sự đã được bóc tách từ tin nhắn, gồm cột Tên, Ngày, Ca, Giờ HC, Giờ Tăng ca, Suất ăn, Trạng thái (Hợp lệ / Cần chú ý).
- Cho phép người dùng chỉnh sửa nhanh trực tiếp trên bảng xem trước trước khi bấm ghi file.
- Nút bấm thực thi: "Xác nhận & Điền vào Excel", xuất ra file Excel đã cập nhật và cho phép tải về hoặc lưu đè.

### R3. Bộ đọc và ghi dữ liệu Excel (Excel Integrator)
- Đọc cấu trúc bảng chấm công mẫu nhiều dòng cho mỗi nhân viên (khối dòng: HCN 100%, TCN 150%, HCĐ 130%, TCĐ, Suất ăn... trải dài theo các cột ngày trong tháng).
- Đối chiếu chính xác Họ tên nhân viên trong bảng tính với tin nhắn (hỗ trợ so khớp mờ / fuzzy matching nếu sai khác dấu cách hoặc viết hoa/thường).
- Điền đúng số giờ công và suất ăn vào giao điểm giữa [Dòng chỉ tiêu công + Cột ngày chấm công] của nhân viên đó.
- Tuyệt đối bảo toàn toàn bộ cấu trúc bảng, các hàng tiêu đề, định dạng viền/màu sắc và các công thức hàm tính tổng sẵn có của file Excel mẫu.

## Acceptance Criteria

### Tính chính xác bóc tách (Parser Verification)
- [ ] Xử lý chính xác 100% mẫu tin nhắn chuẩn như đã cung cấp:
  ```
  HỌ TÊN : HOÀNG ĐẮC PHÚ
  NGÀY: 24/10
  CA : Ca ngày 
  DỰ ÁN : sdv 
  THỜI GIAN LÀM VIỆC :8h-17h ( 8H)
  CÓ ĂN Ở XƯỞNG KO : 0
  ```
  => Phân tách đúng: Tên = "HOÀNG ĐẮC PHÚ", Ngày = "24/10", HCN = 8, Suất ăn = 0.
- [ ] Phân biệt chính xác giữa Ca ngày và Ca đêm; phân tách đúng giờ hành chính (8h đầu) và giờ tăng ca (các giờ vượt quá 8h hoặc ngoài khung giờ hành chính).
- [ ] Bắt được các tin nhắn sai định dạng hoặc thiếu ngày/tên và hiển thị thông báo lỗi rõ ràng trên UI thay vì làm gián đoạn chương trình.

### Thao tác Excel (Excel Integrity)
- [ ] Dữ liệu được ghi chính xác vào cột ngày 24, dòng HCN 100% (giá trị 8) và dòng Suất ăn (giá trị 0) của nhân viên "HOÀNG ĐẮC PHÚ" trong file mẫu `BẢNG CHẤM CÔNG WEVN - ETS`.
- [ ] Các công thức tính tổng cột `HC NGÀY (100%)`, `TỔNG CÔNG` trong file Excel vẫn hoạt động và tự động cập nhật đúng tổng sau khi điền.
- [ ] Không làm mất định dạng cell, màu sắc hoặc làm hỏng các sheet/bảng kê khác có trong file.

### Trải nghiệm Web UI
- [ ] Giao diện khởi động cục bộ mượt mà, thao tác dán tin nhắn -> xem trước -> ghi file Excel diễn ra trơn tru.
- [ ] Hiển thị thông báo kết quả: tổng số nhân viên được chấm công thành công, danh sách các tin nhắn bị lỗi (nếu có).
