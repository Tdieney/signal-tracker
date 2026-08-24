# 07 — Testing và acceptance criteria

## 1. Test pyramid

### Pipeline unit tests — Pytest

Bắt buộc test:

- MA10 dùng đúng 10 phiên hợp lệ, không phải 10 ngày calendar;
- 1–9 phiên → `INSUFFICIENT_DATA`, `ma10 = null`, `signal = null`;
- đúng 10 phiên → có MA10 nhưng chưa đủ previous MA10 để phân loại, `signal = null`;
- từ phiên 11 mới có thể phân loại đủ cross/above/below;
- `CROSS_UP_MA10` với previous `<=` và current `>`;
- `CROSS_DOWN_MA10` với previous `>=` và current `<`;
- equality hiện tại → `ON_MA10`, không above/below;
- missing trading day không forward-fill;
- average volume 20D chỉ có khi đủ 20 phiên;
- duplicate `(symbol, trading_date)` fail;
- invalid OHLC/range/type bị reject;
- breadth denominator chỉ gồm eligible symbols;
- eligible count bằng tổng above + below + on-MA10;
- mã `NO_DATA_FOR_AS_OF_DATE` vẫn có thể có row trong screener nhưng không thuộc breadth denominator;
- zero denominator → percentage `null`;
- JSON không chứa `NaN`/`Infinity`;
- mọi file cùng dataset id/schema/as-of;
- deterministic fixture tạo snapshot/expected model ổn định.

Nên dùng giá trị phân số/decimal được chọn cẩn thận để test boundary, không chỉ happy path.

### Frontend unit/component tests — Vitest + Testing Library

- runtime schema accept/reject fixtures đúng;
- number/date/status formatting;
- URL filter parser normalize malformed value;
- cùng selector tạo cùng result cho table và mobile cards;
- sort ổn định, numeric sort không phải lexicographic;
- loading/empty/error/stale/partial states;
- signal/freshness badges có text, không chỉ màu;
- dialog filter quản lý focus, Escape, Apply/Reset;
- route invalid symbol hiển thị Not Found;
- error message không render raw HTML.

Test theo role/name như người dùng; hạn chế assert class/implementation detail.

### Integration/E2E — Playwright

Core journeys:

1. Mở Tổng quan → thấy ngày dữ liệu, disclaimer và KPI đúng fixture.
2. Bấm KPI cắt lên → screener có URL filter và đúng kết quả.
3. Lọc HOSE + min volume → reload → state/result giữ nguyên.
4. Sort distance → mở FPT → thấy explanation và chart summary.
5. Mobile mở filter sheet, áp dụng/xóa filter và đóng bằng Escape.
6. JSON lỗi/mismatch → app hiện error, không render số liệu lẫn lộn.
7. Dataset stale/partial → banner vẫn thấy trên các route liên quan.
8. Direct load hash detail URL hoạt động trên Pages-like base path.

## 2. Viewport matrix

Chạy ít nhất các viewport:

| Nhóm | Kích thước |
| --- | --- |
| Mobile nhỏ | `320 × 568` |
| Mobile phổ biến | `390 × 844` |
| Tablet portrait | `768 × 1024` |
| Laptop | `1024 × 768` |
| Desktop | `1440 × 900` |

Ở từng viewport kiểm tra:

- không horizontal overflow toàn trang;
- navigation, filter, link symbol và chart dùng được;
- không text/control bị cắt;
- sticky element không che focus/nội dung;
- field bắt buộc có thể truy cập dù layout khác;
- xoay portrait/landscape không mất state.

Không dùng screenshot test làm bằng chứng duy nhất; kết hợp behavior và accessibility assertions.

## 3. Accessibility acceptance

- Automated axe không có violation nghiêm trọng trên ba route và các trạng thái dialog/error.
- Keyboard-only hoàn thành core journeys; thứ tự tab hợp lý; focus visible.
- Screen reader semantics: landmarks, một H1, table headers, aria-sort, dialog name, error association.
- Zoom 200% ở viewport 1280 CSS px vẫn reflow không mất content/function.
- Contrast đạt WCAG 2.2 AA.
- Touch target theo mục tiêu 44 × 44 px cho control chính.
- `prefers-reduced-motion` giảm/tắt animation không thiết yếu.
- Chart có text/table alternative cho dữ liệu cốt lõi.

## 4. Security tests

- Scan source, git diff và production artifact cho secret pattern/high entropy.
- Assert bundle không chứa tên/giá trị secret test sentinel.
- Artifact file allow-list và public JSON field allow-list.
- CSP smoke test: không remote script/connect, không `unsafe-eval`.
- Malicious query/symbol strings không tạo DOM HTML, JS URL hoặc path traversal.
- Oversized/malformed JSON fail thân thiện; không freeze vô hạn.
- Workflow lint/review permissions và untrusted PR secret boundary.
- Dependency audit không có unresolved critical vulnerability; high cần quyết định ghi lại.

## 5. Performance budgets

Đo trên production build với fixture đại diện, mobile throttling hợp lý:

- route đầu không tải detail JSON của mọi symbol;
- initial JS gzip mục tiêu `<= 250 KB` (không tính JSON data); vượt phải ghi lý do và được duyệt;
- overview JSON mục tiêu `<= 200 KB` gzip;
- screener JSON mục tiêu `<= 1 MB` gzip cho Phase 1; nếu vượt, chunk/paginate dữ liệu tĩnh;
- interaction filter/sort trên dataset mục tiêu hoàn tất trong 100 ms trên laptop phổ thông và không khóa main thread dài trên mobile;
- không layout shift lớn do skeleton/font/chart;
- Lighthouse CI mục tiêu: Accessibility ≥ 95, Best Practices ≥ 90, Performance ≥ 85 trên route Overview. Đây là guardrail, không thay kiểm thử thật.

## 6. Acceptance criteria theo route

### Tổng quan

- KPI khớp `overview.json` và breadth invariant.
- Timestamp/freshness xuất hiện trước hoặc cùng vùng nhìn đầu tiên.
- Chart 60 phiên không bịa/interpolate ngày thiếu.
- KPI link tạo đúng screener filter.
- Có quality state và disclaimer.

### Bộ lọc

- Tất cả filter trong spec hoạt động và serialize URL.
- Sort/filter cho cùng kết quả trên desktop/mobile.
- Bảng desktop và card mobile không mất field bắt buộc.
- Empty state phân biệt no-match với data error.
- Mã là link semantic tới detail.

### Chi tiết

- Header và explanation khớp `latest`/`explanation` trong JSON.
- Candlestick, MA10, volume và signal marker dùng cùng trading date.
- Mobile không phụ thuộc hover.
- Invalid/missing symbol có Not Found an toàn.
- Có freshness, data quality và disclaimer.

## 7. Cross-browser

Pass bản stable gần nhất trong CI/local tại thời điểm release:

- Chromium;
- Firefox;
- WebKit/Safari engine.

Ít nhất Chromium mobile + desktop chạy đầy đủ mỗi PR; Firefox/WebKit chạy core journeys trước release/deploy nếu thời gian CI hạn chế.

## 8. Definition of Done toàn sản phẩm

Một implementation chỉ hoàn tất khi:

- có entry `STARTED` và entry đóng cùng session ID trong root `DEVELOPER_LOG.md`, đúng với diff và kết quả kiểm thử thực tế;
- code đúng phạm vi `01-product-scope.md`;
- docs/schema/types/fixture/test nhất quán;
- toàn bộ unit/integration/E2E required pass;
- production build pass với Pages base path;
- responsive matrix và accessibility acceptance pass;
- security DoD trong `06-safety-security.md` pass;
- artifact đã được kiểm tra, không có secret/raw data;
- README có hướng dẫn setup, command test/build/deploy và giới hạn sản phẩm;
- không còn TODO blocker, mock ngầm hoặc lỗi console trên core journeys.

Reviewer SHOULD đối chiếu `Files changed` và `Verification` trong entry đóng với working tree/CI. Developer log thiếu, ghi đè lịch sử, chứa secret hoặc khai sai kết quả là release blocker.
