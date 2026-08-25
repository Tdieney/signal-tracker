# 09 — Vận hành, Giám sát và Quy trình xử lý sự cố (Operations & Incident Runbook)

## 1. Lịch vận hành hệ thống

- **Thị trường**: HOSE / HNX / UPCOM (Việt Nam).
- **Khung giờ giao dịch**: 09:00 – 15:00 ICT (Thứ Hai – Thứ Sáu, trừ ngày lễ theo Luật Lao động).
- **Khung giờ xác nhận dữ liệu EOD**: 15:30 ICT trở đi.
- **Lịch chạy tự động GitHub Actions**: `30 9 * * 1-5` (16:30 ICT / 09:30 UTC hàng ngày từ Thứ Hai đến Thứ Sáu).

---

## 2. Quy trình Cập nhật & Kiểm tra tính toàn vẹn

1. **Thu thập dữ liệu**:
   - `VnstockMarketClient` thực hiện fetch dữ liệu OHLCV 180 ngày gần nhất cho toàn bộ 30 mã thuộc rổ VN30.
   - Cơ chế rate-limit (0.05s delay) và tự động thử lại (3 attempts với exponential backoff).
2. **Kiểm định dữ liệu (Pipeline Invariants)**:
   - Kiểm tra định dạng ngày (`YYYY-MM-DD`), mã cổ phiếu (`^[A-Z0-9]{1,10}$`), sàn giao dịch (`HOSE`/`HNX`/`UPCOM`).
   - Kiểm tra bất biến giá: `High >= max(Open, Close, Low)`, `Low <= min(Open, Close, High)`, `Volume >= 0`, giá đóng cửa dương.
   - Kế toán dòng dữ liệu: `input_rows == accepted_rows + rejected_rows`.
3. **Cập nhật giao dịch nguyên tử (Transactional DatasetManager)**:
   - Toàn bộ file JSON được sinh tại thư mục tạm `staging/`.
   - Kiểm định sâu toàn bộ file JSON qua `validate_data_directory()`.
   - Đẩy `staging/` thành `target/` và lưu bản sao lưu `lkg/` (Last-Known-Good).
4. **Bảo mật & Build tĩnh**:
   - Quét secret, kiểm tra allow-list artifact, build Vite SPA và deploy lên GitHub Pages.

---

## 3. Quy trình Xử lý sự cố (Incident Runbook)

### Sự cố 1: Endpoint dữ liệu ngoài bị gián đoạn / timeout
- **Triệu chứng**: GitHub Actions workflow bước `Build Live Dataset` cảnh báo không kết nối được hoặc retry hết lượt.
- **Hành vi tự động**: `DatasetManager` tự động kích hoạt cơ chế fail-closed rollback. Bản deploy thành công gần nhất (`lkg/`) được bảo toàn nguyên vẹn, không làm gián đoạn website đang chạy.
- **Khắc phục thủ công**:
  1. Kiểm tra trạng thái mạng của endpoint thị trường.
  2. Kích hoạt lại workflow trên GitHub Actions qua nút **Run workflow** khi endpoint phục hồi.
  3. Nếu cần khẩn cấp, chạy fallback từ CSV:
     ```bash
     python pipeline/build_dataset.py --provider csv --input tests/fixtures/sample_ohlcv.csv --output frontend/public/data
     ```

### Sự cố 2: Lệch `dataset_id` giữa các file dữ liệu (Cross-file mismatch)
- **Triệu chứng**: Giao diện hiển thị banner đỏ `Lỗi xác thực dữ liệu` trên Overview, Screener hoặc Symbol Detail.
- **Hành vi tự động**: Frontend chặn hiển thị tín hiệu sai lệch.
- **Khắc phục**:
  Chạy lệnh build lại toàn bộ dataset để đảm bảo tính đồng bộ hash:
  ```bash
  python pipeline/build_dataset.py --provider vnstock --universe VN30 --output frontend/public/data
  npm --prefix frontend run build:pages
  ```

### Sự cố 3: Dữ liệu bị quá hạn (STALE status)
- **Triệu chứng**: Header hiển thị badge `Dữ liệu có thể đã cũ — phiên YYYY-MM-DD`.
- **Nguyên nhân**: Phiên giao dịch hôm nay đã kết thúc sau 15:30 ICT nhưng pipeline chưa được kích hoạt hoặc workflow bị hoãn (delayed by GitHub queue).
- **Khắc phục**:
  Vào tab **Actions > Deploy to GitHub Pages > Run workflow** để kích hoạt pipeline ngay lập tức.
