# 02 — UX và responsive

## 1. Nguyên tắc chung

Chỉ có một ứng dụng, một data source và một state model. Desktop/tablet/mobile khác cách sắp xếp, không khác nghiệp vụ. Không branch logic signal hoặc filter theo `window.innerWidth`; CSS và component composition xử lý layout.

Ứng dụng MUST hỗ trợ từ 320 px, zoom trình duyệt 200% và cả portrait/landscape mà không làm mất chức năng.

## 2. Information architecture

```text
App shell
├── Tổng quan              #/
├── Bộ lọc                 #/screener
└── Chi tiết mã            #/symbols/:symbol
```

- Logo/tên ứng dụng luôn quay về Tổng quan.
- Desktop: navigation ngang trong header.
- Mobile: header gọn và navigation dạng tab có thể cuộn ngang; không dùng hamburger nếu chỉ có ba route.
- Disclaimer ngắn và timestamp xuất hiện trong footer; cảnh báo stale/partial xuất hiện gần đầu nội dung, không chỉ ở footer.
- Deep-link phải phục hồi được route, query filter và selected symbol sau reload.

## 3. Breakpoint và container

Breakpoint là điểm layout thay đổi, không phải danh sách thiết bị:

| Mode | Khoảng tham chiếu | Hành vi chính |
| --- | --- | --- |
| Compact | `320–767 px` | 1 cột; card list; filter drawer/bottom sheet |
| Medium | `768–1023 px` | 2 cột khi đủ chỗ; table có scroll có chủ đích |
| Wide | `>=1024 px` | grid dashboard; filter rail/toolbar; data table đầy đủ |

- Content container tối đa `1440px`, căn giữa, padding responsive.
- Không dùng breakpoint để ẩn field bắt buộc. Có thể chuyển field phụ vào vùng “Xem thêm”.
- Không tạo horizontal scroll cho toàn trang. Chỉ chart/table wrapper được phép scroll, có nhãn và affordance rõ.
- Component tự co giãn bằng CSS Grid/Flex và `minmax`; ưu tiên container-aware layout nếu đơn giản.

## 4. App shell và trạng thái toàn cục

Thứ tự từ trên xuống:

1. Skip link “Bỏ qua đến nội dung chính”.
2. Header: brand, navigation, thời điểm cập nhật ngắn.
3. Banner `STALE`, `PARTIAL` hoặc lỗi dataset nếu có.
4. `<main>` chứa route hiện tại.
5. Footer: disclaimer, nguồn dữ liệu, schema/app version.

Mỗi route có đúng một `<h1>`. Khi đổi route, cập nhật document title và đưa focus hợp lý về đầu nội dung mà không gây jump khó chịu.

## 5. Trang Tổng quan

### Nội dung

1. Tiêu đề + phiên dữ liệu + trạng thái “Đã xác nhận sau đóng cửa”.
2. KPI cards:
   - số mã đủ dữ liệu;
   - số và tỷ lệ trên MA10;
   - số và tỷ lệ dưới MA10;
   - số vừa cắt lên;
   - số vừa cắt xuống.
3. Biểu đồ MA10 breadth 60 phiên.
4. Hai preview list: cắt lên và cắt xuống gần nhất.
5. Data quality summary.

### Responsive

- Compact: KPI thành grid 2 cột; card “đủ dữ liệu” có thể chiếm 2 cột. Chart cao tối thiểu 260 px. Preview list dùng row/card.
- Medium: KPI 3 cột; chart full width; hai preview list đặt cạnh nhau nếu mỗi vùng còn ít nhất 320 px.
- Wide: KPI 5 cột; chart và quality summary có thể theo tỷ lệ 2:1; preview list cạnh nhau.
- KPI card là link/filter shortcut khi có đích rõ, ví dụ “Vừa cắt lên” mở screener với signal tương ứng.

Không dùng màu một mình để diễn đạt trên/dưới/cross; luôn kèm nhãn/icon/text.

## 6. Trang Bộ lọc

### Filter state chuẩn

Filter phải được serialize trong URL query để chia sẻ/reload:

```text
#/screener?exchange=HOSE&signal=CROSS_UP_MA10&universe=ALL&minAvgVolume20d=100000
```

Field:

- `exchange`: `ALL | HOSE | HNX | UPCOM`
- `signal`: một hoặc nhiều signal baseline
- `universe`: `ALL | VN30`
- `distanceMin`, `distanceMax`: phần trăm
- `minAvgVolume20d`: số nguyên không âm
- `query`: mã cổ phiếu
- `sort`: field allow-list
- `direction`: `asc | desc`
- `page`: số nguyên dương

Giá trị URL không hợp lệ phải được bỏ qua hoặc normalize về mặc định, không làm crash và không được đưa trực tiếp vào HTML.

### Desktop/wide

- Filter toolbar/rail luôn thấy.
- Hiển thị bảng semantic; header sortable bằng button có `aria-sort` đúng.
- Cột mặc định: Mã, Sàn, Close, MA10, Distance %, Volume, Avg Volume 20D, Signal, Data status.
- Header bảng có thể sticky trong chính vùng bảng; không che focus.
- Row click không phải cách duy nhất để mở chi tiết: mã là link thật.

### Mobile/compact

- Thanh tóm tắt gồm số kết quả, sort và nút “Bộ lọc”.
- Bộ lọc mở trong dialog/bottom sheet có focus trap, nút Áp dụng, Xóa lọc, Đóng và hỗ trợ phím Escape.
- Kết quả là card/list. Mỗi card vẫn hiển thị tối thiểu: mã, sàn, close, MA10, distance, signal, avg volume và data status.
- Chi tiết phụ (volume hiện tại, timestamp) nằm trong vùng mở rộng bằng button semantic.
- Không biến bảng desktop thành bảng 9 cột bị thu nhỏ khó đọc.

### Empty state

Phân biệt:

- không có mã khớp filter: cho nút “Xóa bộ lọc”;
- dataset rỗng/lỗi: cho hướng xử lý và nút thử lại;
- dữ liệu chưa đủ: giải thích điều kiện tối thiểu 10 phiên.

## 7. Trang Chi tiết mã

### Thứ tự nội dung

1. Breadcrumb/back link.
2. Symbol header: mã, sàn, close, MA10, distance, signal, phiên dữ liệu, freshness.
3. Khối “Vì sao có tín hiệu này?” bằng câu có số liệu cụ thể.
4. Candlestick + MA10.
5. Volume chart đồng bộ trục thời gian.
6. Bảng/list lịch sử signal gần nhất.
7. Data-quality notes và disclaimer.

### Chart interaction

- Chart phải responsive theo container qua `ResizeObserver`; dispose listener/instance khi unmount.
- Desktop có crosshair/tooltip bằng hover và keyboard-accessible summary thay thế.
- Mobile không phụ thuộc hover; tap chọn phiên, drag/pinch không chặn cuộn dọc ngoài vùng chart.
- Có bảng tóm tắt dữ liệu hoặc accessible description để thông tin cốt lõi không chỉ tồn tại trên canvas.
- Không tải toàn bộ lịch sử mọi mã ở trang đầu; detail JSON tải khi mở route.

## 8. Loading, lỗi và dữ liệu cũ

- Loading lần đầu: skeleton giữ gần đúng kích thước, không flash số `0` giả.
- Fetch lỗi: thông báo trong vùng `role="alert"`, nêu file/dataset không tải được ở mức thân thiện, có Retry.
- Partial: render phần hợp lệ và banner cảnh báo số record bị loại; không trộn record invalid.
- Stale: banner màu cảnh báo + text “Dữ liệu gần nhất: …”; tín hiệu vẫn xem được nhưng không được mô tả như hiện tại.
- Route/symbol không tồn tại: trang Not Found có link về screener; không crash app shell.
- Không dùng toast tự biến mất cho lỗi dữ liệu quan trọng.

## 9. Accessibility và input

- Mục tiêu WCAG 2.2 AA.
- Mọi chức năng dùng được bằng keyboard; focus visible và không bị sticky element che.
- Touch target trong sản phẩm đặt mục tiêu tối thiểu `44 × 44 CSS px`; không thấp hơn yêu cầu WCAG 2.2 AA `24 × 24 CSS px` nếu có ngoại lệ layout hợp lệ.
- Text thường đạt contrast tối thiểu `4.5:1`; text lớn `3:1`; UI/focus indicator `3:1` so với màu kề.
- Hỗ trợ `prefers-reduced-motion`; animation không cần thiết phải tắt/giảm.
- Input có label nhìn thấy; lỗi gắn với field; number input có min/max và giải thích đơn vị.
- Format số bằng `Intl.NumberFormat('vi-VN')`; không dùng chỉ dấu màu để biểu đạt.

Tham chiếu: [WCAG 2.2](https://www.w3.org/TR/WCAG22/) và [Target Size (Minimum)](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html).
