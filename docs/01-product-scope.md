# 01 — Phạm vi sản phẩm

## 1. Tuyên bố sản phẩm

VN Stock Signal là dashboard public, cập nhật cuối ngày, giúp người dùng quan sát market breadth và lọc cổ phiếu Việt Nam theo quan hệ giữa giá đóng cửa và MA10.

Sản phẩm trình bày **tín hiệu kỹ thuật có thể kiểm chứng**, không dự đoán thị trường, không gọi tín hiệu là khuyến nghị mua/bán và không đặt lệnh.

## 2. Người dùng và nhu cầu chính

Người dùng mục tiêu là nhà đầu tư cá nhân cần:

- biết dữ liệu đang phản ánh phiên nào và có còn mới hay không;
- xem nhanh độ rộng thị trường theo MA10;
- tìm mã vừa cắt lên/cắt xuống MA10;
- lọc theo sàn, nhóm mã, khoảng cách tới MA10 và thanh khoản;
- mở chi tiết để hiểu chính xác vì sao một mã nhận tín hiệu;
- có cùng kết quả và cùng ý nghĩa trên điện thoại lẫn máy tính.

## 3. Phạm vi bắt buộc của Phase 1

### Pipeline

- `DataProvider` abstraction.
- `CsvDataProvider` dùng fixture xác định để test và demo.
- `VnstockDataProvider` là provider tùy chọn cho prototype cá nhân.
- Chuẩn hóa OHLCV, kiểm tra dữ liệu, tính MA10, MA10 breadth và bốn signal baseline.
- Sinh JSON tĩnh, có version và metadata về độ mới/chất lượng.

### Website

- Trang Tổng quan.
- Trang Bộ lọc cổ phiếu.
- Trang Chi tiết mã.
- Trạng thái loading, empty, error, stale và partial data.
- Responsive từ chiều rộng 320 px trở lên; keyboard và screen reader sử dụng được.
- Deploy GitHub Pages bằng GitHub Actions.

### Tín hiệu baseline

- `ABOVE_MA10`
- `BELOW_MA10`
- `CROSS_UP_MA10`
- `CROSS_DOWN_MA10`
- `INSUFFICIENT_DATA` là data status, không phải tín hiệu giao dịch.

## 4. Ngoài phạm vi Phase 1

MUST NOT triển khai:

- tài khoản, đăng nhập, phân quyền hay lưu hồ sơ người dùng;
- dữ liệu realtime/intraday, websocket hay auto-refresh dày;
- dự đoán bằng AI/ML;
- backtest và tuyên bố hiệu suất chiến lược;
- recommendation `BUY`, `SELL`, target price hoặc position sizing;
- kết nối broker, đặt lệnh hoặc giả lập đặt lệnh;
- API/key công ty, dữ liệu mật, dữ liệu có giới hạn phân phối;
- database/backend chạy theo request;
- push notification, email alert hoặc paywall;
- indicator ngoài MA10 nếu chưa có yêu cầu mới được duyệt.

Nếu một thư viện kéo theo telemetry, quảng cáo hoặc script bên thứ ba không cần thiết, không sử dụng trong Phase 1.

## 5. Các quyết định đã khóa

| Chủ đề | Quyết định Phase 1 |
| --- | --- |
| Loại ứng dụng | Static SPA trên GitHub Pages |
| Stack UI | React + TypeScript + Vite |
| Biểu đồ | TradingView Lightweight Charts, dùng dữ liệu của hệ thống |
| Pipeline | Python + Pandas |
| Dữ liệu | Cuối ngày, không realtime |
| Routing | Hash routing để deep-link hoạt động ổn định trên GitHub Pages |
| Ngôn ngữ UI | Tiếng Việt |
| Múi giờ hiển thị | `Asia/Ho_Chi_Minh` |
| Chủ đề màu | Light mặc định; dark mode là tùy chọn sau khi core flow đạt DoD |
| Lưu preference | Chỉ `localStorage`, không chứa dữ liệu nhạy cảm |
| Analytics | Không có mặc định |

## 6. Nguyên tắc trải nghiệm

1. **Freshness before signal:** ngày/giờ dữ liệu và cảnh báo stale phải dễ thấy hơn tín hiệu.
2. **Explain, do not persuade:** giải thích điều kiện toán học; không dùng copy tạo cảm giác chắc chắn hay thúc giục giao dịch.
3. **Same task, every device:** mobile không bị mất filter, dữ liệu hay giải thích có trên desktop.
4. **Progressive density:** desktop dùng bảng dày thông tin; mobile dùng card/list nhưng giữ cùng field và kết quả.
5. **Fail visibly:** thiếu, lỗi hoặc cũ phải hiện rõ; không lặng lẽ dùng giá trị cũ như mới.
6. **Deterministic:** cùng dataset và schema phải tạo cùng signal, không phụ thuộc AI.

## 7. Thuật ngữ hiển thị

| Internal enum | Nhãn tiếng Việt | Giải thích ngắn |
| --- | --- | --- |
| `ABOVE_MA10` | Trên MA10 | Close lớn hơn MA10; không có giao cắt mới |
| `BELOW_MA10` | Dưới MA10 | Close nhỏ hơn MA10; không có giao cắt mới |
| `CROSS_UP_MA10` | Vừa cắt lên MA10 | Hôm nay trên MA10, phiên trước không ở trên |
| `CROSS_DOWN_MA10` | Vừa cắt xuống MA10 | Hôm nay dưới MA10, phiên trước không ở dưới |
| `INSUFFICIENT_DATA` | Chưa đủ dữ liệu | Không đủ phiên hợp lệ để tính signal |
| `STALE` | Dữ liệu cũ | Dataset vượt ngưỡng freshness đã công bố |

Không thay các nhãn trên bằng “Mua”, “Bán”, “Tốt”, “Xấu” hoặc ngôn ngữ mang tính khuyến nghị.

## 8. Success metrics của MVP

- Người dùng thấy phiên dữ liệu và trạng thái freshness ngay khi mở trang.
- Có thể từ Tổng quan tới danh sách `CROSS_UP_MA10`, rồi mở chi tiết mã trong tối đa 3 thao tác.
- Cùng URL/filter cho cùng tập kết quả trên desktop và mobile.
- Không có secret hay dữ liệu ngoài allow-list trong build artifact.
- Signal và breadth vượt toàn bộ test xác định trong `07-testing-acceptance.md`.
