# 09 — Vận hành và Quy trình Xử lý Sự cố (Operations & Runbook)

## 1. Trạng thái Vận hành Hiện tại

- **Chế độ hoạt động**: **Demo / Test Mode** (Dữ liệu mẫu từ deterministic CSV fixture).
- **Lịch chạy tự động (Cron Schedule)**: **TẮT** (Không có workflow chạy định kỳ).
- **Trạng thái Phase 3**: **TẠM DỪNG (PAUSED)** chờ xác minh giấy phép nhà cung cấp dữ liệu.
- **Trạng thái Session**: `UNKNOWN` (Dữ liệu mẫu thử nghiệm).
- **Trạng thái Freshness**: `UNKNOWN` (Hiển thị banner cảnh báo dữ liệu mẫu trên website).

---

## 2. Quy trình Cập nhật & Kiểm tra Tính Toàn vẹn (Offline / CI)

1. **Sinh dữ liệu tĩnh deterministic**:
   - Sử dụng `CsvDataProvider` đọc từ file fixture chuẩn `tests/fixtures/sample_ohlcv.csv`.
   - Cố định thời điểm sinh dữ liệu qua cờ `--generated-at 2026-08-21T10:00:00Z` để đảm bảo kết quả build byte-for-byte nhất quán.
2. **Kiểm định tính toàn vẹn (Pipeline Invariants)**:
   - Kế toán dòng: `input_rows == accepted_rows + rejected_rows`.
   - Bất biến OHLC: `High >= max(Open, Close, Low)`, `Low <= min(Open, Close, High)`, `Volume >= 0`.
   - Không chứa mã độc, secret, hoặc dữ liệu không kiểm chứng.
3. **Quy tắc Kiểm tra Rổ Chỉ số (Universe Completeness)**:
   - Một tập dữ liệu rổ chỉ số chỉ được đánh giá là hoàn chỉnh khi **100% các mã trong rổ** có đầy đủ dữ liệu tính toán tại đúng ngày chốt phiên (`as_of_date`).
   - Nếu thiếu bất kỳ mã nào, hệ thống bắt buộc chuyển trạng thái về `is_complete=False` và không công bố `FRESH` hay `CLOSED_CONFIRMED`.

---

## 3. Quy trình Xử lý Sự cố (Incident Runbook)

### Sự cố 1: Lỗi Xác thực Dữ liệu trên Frontend
- **Triệu chứng**: Giao diện hiển thị banner `Lỗi xác thực dữ liệu` hoặc không tải được bảng screener.
- **Khắc phục**:
  Chạy lại quy trình build chuẩn:
  ```bash
  python pipeline/build_dataset.py --provider csv --input tests/fixtures/sample_ohlcv.csv --output frontend/public/data --generated-at 2026-08-21T10:00:00Z
  npm --prefix frontend run build:pages
  ```

### Sự cố 2: Có thay đổi unapproved live provider
- **Hành vi**: Mọi live provider adapter đều bị khóa `fail-closed` (`RuntimeError: Live market data provider disabled`).
- **Khắc phục**: Giữ nguyên chế độ CSV demo cho đến khi có phê duyệt chính thức từ chủ repository.
