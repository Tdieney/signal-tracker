# 10 — Provider Decision Record (PDR) — Dữ liệu Thị trường EOD

- **Trạng thái**: `NOT APPROVED / BLOCKED / PAUSED`
- **Phiên bản**: `1.1.0` (Cập nhật sau kiểm tra giấy phép & đánh giá độc lập)
- **Ngày lập**: 2026-08-25
- **Tác giả**: Antigravity / Gemini 3.7 Flash

---

## 1. Bối cảnh & Lịch sử Quyết định

Trong quá trình chuẩn bị Phase 3, chủ repository đã chọn phương án ban đầu:
- *"Sử dụng Vnstock (Community / Open Quotes) cho Phase 3"*

**Ghi nhận đính chính quan trọng:**
1. Lựa chọn trên trong dialog chỉ là định hướng kỹ thuật ban đầu, **không cấu thành việc phê duyệt gọi trực tiếp vào endpoint của các công ty chứng khoán (như DNSE/EnTrade)** hoặc bất kỳ hệ thống phân phối nào khác.
2. Quyền sử dụng lại và phân phối công khai (public redistribution) dữ liệu thị trường từ các cổng dịch vụ bên thứ ba trên GitHub Pages **chưa được xác minh (UNVERIFIED)** về mặt pháp lý và điều khoản dịch vụ (Terms of Service).
3. Thư viện mã nguồn Vnstock áp dụng giấy phép mã nguồn riêng (Custom Personal / Non-Commercial Research License) theo nguồn chính thức tại [Vnstock LICENSE.md](https://github.com/thinh-vu/vnstock/blob/main/LICENSE.md), **không phải giấy phép MIT**.
4. Giấy phép mã nguồn phần mềm **tuyệt đối không đồng nghĩa với quyền phân phối hoặc tái xuất bản dữ liệu thị trường** lấy từ hạ tầng API tài chính của các bên thứ ba.
5. Toàn bộ các tuyên bố chưa có nguồn kiểm chứng độc lập (về tính sẵn sàng cao, giới hạn tốc độ đoán định, quyền phân phối miễn phí) đã được **thu hồi và loại bỏ hoàn toàn**.

---

## 2. Bảng Đánh giá Hiện trạng Nhà cung cấp

| Tiêu chí | Vnstock Community / Direct Scraper | Corporate Licensed API (SSI / VNDIRECT / FiinGroup) | CSV Fixture / Static Demo |
| :--- | :--- | :--- | :--- |
| **Trạng thái cấp phép** | **UNVERIFIED / BLOCKED** (Chưa có văn bản cho phép public redistribution) | Cần hợp đồng thương mại & API key bảo mật | **APPROVED** (Dữ liệu fixture tự tạo) |
| **Chi phí** | Miễn phí (nhưng rủi ro pháp lý/TOS chưa rõ) | Có phí thương mại | Miễn phí |
| **Quyền phân phối GitHub Pages** | **CHƯA ĐƯỢC XÁC MINH** | Phụ thuộc hợp đồng | **ĐẦY ĐỦ** |
| **Độ ổn định & Rate Limit** | Không cam kết SLA, có thể bị chặn bất cứ lúc nào | Có cam kết SLA | 100% Deterministic & Offline |
| **Quản lý Secret** | Không cần API key | Yêu cầu Secret ở backend / CI | Không cần secret |

---

## 3. Quyết định & Hành động Ngăn chặn (Containment)

1. **Khóa toàn bộ Live Data Provider (`fail-closed`)**:
   - `VnstockDataProvider` và mọi client gọi trực tiếp ra ngoài bị đưa vào trạng thái **QUARANTINED / DISABLED**.
   - Bất kỳ nỗ lực khởi chạy `is_live=True` đều lập tức báo lỗi và dừng thực thi.
2. **Không gọi endpoint ngoài trong CI / Build / Test / Deployment**:
   - Mọi quy trình build sản phẩm (`deploy-pages.yml`, `ci.yml`, `scripts/build_all.py`) tuyệt đối không phụ thuộc vào kết nối mạng ngoài.
   - Toàn bộ test suite chuyển sang sử dụng mock / deterministic fixture.
3. **Không bật lịch cron tự động**:
   - Xóa bỏ toàn bộ lịch chạy tự động `schedule` trên GitHub Actions.
4. **Trạng thái hiển thị công khai**:
   - GitHub Pages được đưa về chế độ Demo an toàn (`provider="csv"`, `freshness.status="UNKNOWN"`, `market_session_status="UNKNOWN"`).

---

## 4. Điều kiện Tiên quyết để Mở lại Phase 3

Phase 3 chỉ có thể được xem xét kích hoạt lại khi thỏa mãn **tất cả** các điều kiện sau:
1. Có văn bản / tài liệu điều khoản chính thức (Official Terms of Service / Data Distribution Agreement) từ nhà cung cấp cho phép public redistribution trên web tĩnh.
2. Chủ repository phê duyệt bằng văn bản nhà cung cấp và điều khoản cụ thể.
3. Có cơ chế kế toán dòng dữ liệu hoàn chỉnh (`input_rows == accepted_rows + rejected_rows`) và kiểm tra toàn vẹn rổ chỉ số VN30 tại đúng ngày chốt phiên.
