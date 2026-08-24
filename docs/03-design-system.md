# 03 — Design system

## 1. Hướng thị giác

Phong cách: dashboard tài chính rõ ràng, bình tĩnh, ưu tiên đọc số liệu hơn trang trí. Light theme là baseline. Không mô phỏng terminal giao dịch, không dùng hiệu ứng neon, ticker chạy liên tục hoặc animation gây cảm giác khẩn cấp.

Font ưu tiên system stack để tải nhanh và hiển thị tiếng Việt ổn định:

```css
font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont,
  "Segoe UI", sans-serif;
font-variant-numeric: tabular-nums;
```

Không bắt buộc tải Inter từ mạng; nếu dùng webfont phải self-host và không làm chặn nội dung.

## 2. Token bắt buộc

Định nghĩa token bằng CSS custom properties, component không hard-code màu/spacing lặp lại.

```css
:root {
  --color-bg: #f6f8fb;
  --color-surface: #ffffff;
  --color-surface-muted: #eef2f7;
  --color-text: #172033;
  --color-text-muted: #566176;
  --color-border: #d7deea;
  --color-primary: #2457d6;
  --color-primary-strong: #173fa8;
  --color-positive: #087a55;
  --color-negative: #b42318;
  --color-warning: #9a6700;
  --color-info: #175cd3;
  --color-focus: #7c3aed;

  --space-1: 0.25rem;
  --space-2: 0.5rem;
  --space-3: 0.75rem;
  --space-4: 1rem;
  --space-5: 1.5rem;
  --space-6: 2rem;
  --space-7: 3rem;

  --radius-sm: 0.375rem;
  --radius-md: 0.625rem;
  --radius-lg: 0.875rem;
  --shadow-card: 0 1px 2px rgb(16 24 40 / 6%), 0 4px 12px rgb(16 24 40 / 5%);
  --content-max: 90rem;
}
```

Các mã màu là baseline, không phải lý do bỏ qua contrast test. Nếu điều chỉnh branding phải test lại mọi cặp màu và chart series.

## 3. Typography

| Role | Size/line-height tham chiếu | Dùng cho |
| --- | --- | --- |
| Display | `clamp(1.75rem, 3vw, 2.5rem) / 1.15` | con số/tiêu đề quan trọng |
| H1 | `clamp(1.5rem, 2.5vw, 2rem) / 1.2` | tiêu đề route |
| H2 | `1.25rem / 1.3` | section |
| Body | `1rem / 1.5` | nội dung |
| Small | `0.875rem / 1.45` | metadata, không dùng cho nội dung cốt lõi |

- Symbol và số dùng `font-variant-numeric: tabular-nums`.
- Không viết cả đoạn in hoa.
- Không dùng font nhỏ hơn `0.75rem`; text tương tác tối thiểu `0.875rem`.

## 4. Layout primitives

- `PageContainer`: max width + gutter `16/24/32px` theo compact/medium/wide.
- `Stack`: khoảng cách dọc theo token.
- `Cluster`: wrap action/filter, không ép một hàng.
- `AutoGrid`: `repeat(auto-fit, minmax(min(100%, var(--min)), 1fr))`.
- `ScrollableRegion`: chỉ cho table/chart, có focus và label nếu keyboard cần cuộn.

Tránh absolute positioning cho layout chính. Nội dung tiếng Việt dài hơn mockup vẫn không vỡ.

## 5. Component contract

### `FreshnessBadge`

- Props từ dữ liệu đã validate: `status`, `asOfDate`, `generatedAt`, `reason`.
- Có icon + text; màu chỉ là hỗ trợ.
- `FRESH`: “Dữ liệu phiên DD/MM/YYYY”.
- `STALE`: “Dữ liệu có thể đã cũ — phiên DD/MM/YYYY”.
- `UNKNOWN`: “Dữ liệu gần nhất là phiên DD/MM/YYYY — chưa xác định độ mới”.
- Không tự suy luận từ clock khác với logic chung.

### `SignalBadge`

- Enum input, không nhận arbitrary HTML/class.
- Cross-up/above dùng positive tone; cross-down/below dùng negative/neutral tone nhưng nhãn không mang nghĩa khuyến nghị.
- Luôn có nhãn đầy đủ ở lần xuất hiện chính; abbreviation chỉ dùng ở vùng chật kèm accessible name.

### `MetricCard`

- Label, value, optional ratio, context và optional link.
- Không để `0` thay cho loading/missing; dùng skeleton hoặc `—` kèm giải thích.

### `FilterControl`

- Label nhìn thấy, help/error text liên kết bằng `aria-describedby`.
- Apply trên mobile, phản hồi trực tiếp trên desktop là được, nhưng URL cuối cùng phải giống nhau.
- “Xóa lọc” reset về một constant duy nhất.

### `DataTable` / `StockCardList`

- Cùng nhận collection đã filter/sort từ một selector/service chung.
- Không viết hai bản logic riêng.
- Table semantic ở wide; card semantic list ở compact.
- Link symbol là phần tử tương tác chính; không lồng button trong link.

### `ChartPanel`

- Có title, legend, accessible summary, loading/error/empty state.
- Series dùng màu + line style/marker khác nhau.
- Tooltip không vượt viewport; giá trị format thống nhất với table.

### `StatusBanner`

- Variant `info | warning | error`.
- Error quan trọng dùng `role="alert"`; info tĩnh không lạm dụng live region.
- Nội dung nêu: chuyện gì xảy ra, ảnh hưởng gì, người dùng làm được gì.

## 6. Trạng thái tương tác

Mọi button/link/input có đủ: default, hover (nếu có hover), active, focus-visible, disabled và error khi phù hợp.

- Focus ring tối thiểu 2 px, offset 2 px, contrast rõ.
- Disabled không được là cách duy nhất giải thích vì sao không thao tác được.
- Loading button giữ label và kích thước; ngăn double-submit dù Phase 1 hầu như không có mutation.
- Transition tối đa khoảng 150–200 ms và tôn trọng reduced motion.

## 7. Icon, số liệu và nội dung

- Icon trang trí `aria-hidden="true"`; icon-only button bắt buộc có accessible name/tooltip.
- Dùng tối đa 2 chữ số thập phân cho giá/MA theo quy ước dataset; distance dùng 2 chữ số; tỷ lệ breadth dùng 1 chữ số.
- Volume có compact display (`1,2 Tr`) nhưng accessible/tooltip hiển thị số đầy đủ.
- Missing value hiển thị `—`, không hiển thị `0`, `null`, `NaN` hoặc `undefined`.
- Error message không đổ stack trace, URL secret hay raw payload ra UI.

## 8. Copy safety

Copy bắt buộc:

> Tín hiệu chỉ phản ánh quy tắc kỹ thuật trên dữ liệu cuối ngày, không phải khuyến nghị mua hoặc bán.

Copy giải thích signal phải dùng dữ liệu cụ thể, ví dụ:

> FPT được đánh dấu “Vừa cắt lên MA10” vì Close phiên 2026-08-21 là 102,50, cao hơn MA10 101,80; ở phiên hợp lệ trước đó Close không cao hơn MA10.

Không dùng: “cơ hội chắc thắng”, “nên mua ngay”, “an toàn”, “AI dự báo”, hoặc phần trăm thành công khi chưa có backtest được duyệt.
