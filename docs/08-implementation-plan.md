# 08 — Kế hoạch triển khai theo milestone

Mỗi milestone phải nhỏ, review được và chạy test/build trước khi sang milestone tiếp. Không làm UI hoàn chỉnh trên fake shape rồi mới “vá” data contract ở cuối.

## Milestone 0 — Scaffold và quyết định công cụ

Deliverables:

- cấu trúc repo theo `05-architecture.md`;
- React + TypeScript + Vite và Python project;
- lockfiles, lint/format/typecheck/test commands;
- `.gitignore`, `.env.example` không có secret;
- CI skeleton với `permissions: contents: read`;
- fixture license-safe tối thiểu.

Gate:

- install deterministic;
- hello production build chạy với non-root base path;
- unit test mẫu hai stack pass;
- không có secret hoặc dependency CDN runtime.

## Milestone 1 — Data contract và pipeline deterministic

Deliverables:

- typed models/schema version `1.0.0`;
- `DataProvider` + `CsvDataProvider`;
- normalize/validation;
- MA10, distance, average volume, signals và breadth;
- serializer cho manifest/overview/screener/detail;
- fixture expected outputs.

Gate:

- toàn bộ pipeline tests trong `07-testing-acceptance.md` pass;
- JSON schema/cross-file invariant pass;
- chạy pipeline hai lần cùng fixture tạo nội dung semantic giống nhau;
- output chỉ chứa allow-listed public field.

## Milestone 2 — App shell và data boundary

Deliverables:

- hash routes, header/nav/footer/skip link;
- design tokens và responsive primitives;
- fetch + AbortController + runtime schema validation;
- loading/error/stale/partial/Not Found;
- formatters tiếng Việt và copy disclaimer.

Gate:

- direct/reload route dưới Pages base path pass;
- malformed/mismatched JSON fail closed;
- keyboard navigation app shell pass;
- CSP baseline không gây violation do code ứng dụng.

## Milestone 3 — Tổng quan

Deliverables:

- KPI cards và filter shortcuts;
- breadth chart 60 phiên;
- cross-up/down preview;
- quality summary;
- layouts compact/medium/wide.

Gate:

- metrics khớp fixture;
- chart có accessible alternative;
- viewport matrix Overview pass;
- không tải symbol detail payload.

## Milestone 4 — Screener

Deliverables:

- canonical filter schema + URL parsing;
- desktop table và mobile card list dùng cùng selector;
- sort, paginate/chunk nếu cần;
- accessible mobile filter dialog;
- empty/no-match/error states.

Gate:

- filter URL reload/share pass;
- malformed query normalize an toàn;
- desktop/mobile result parity test pass;
- keyboard/touch core journey pass.

## Milestone 5 — Chi tiết mã

Deliverables:

- validated lazy-loaded detail data;
- header + structured explanation;
- candlestick, MA10, volume, signal markers;
- chart resize/dispose/touch behavior;
- accessible chart summary/history list.

Gate:

- symbol allow-list/path safety pass;
- no-hover mobile journey pass;
- chart/value/date khớp fixture;
- invalid symbol và fetch error không crash.

## Milestone 6 — Optional Vnstock provider

Chỉ làm khi các milestone deterministic đã xanh và việc sử dụng phù hợp license.

Deliverables:

- adapter mapping sang contract chuẩn;
- timeout/retry/rate limit/log sanitization;
- integration test mock/record đã loại dữ liệu nhạy cảm;
- tài liệu nguồn dữ liệu và hạn chế sử dụng.

Gate:

- provider không làm thay đổi indicator/signal logic;
- không cần secret ở frontend/local demo CSV;
- public output pass allow-list/license review.

## Milestone 7 — CI, security và Pages deploy

Deliverables:

- CI đầy đủ;
- deploy workflow concurrency + minimal permissions + pinned SHA;
- public artifact/secret/schema checks;
- Pages base path và HTTPS checklist;
- build summary có dataset id/count/hash.

Gate:

- production artifact được inspect;
- untrusted PR không có secret;
- security DoD pass;
- deployment smoke test ba route pass.

## Milestone 8 — Release candidate

Deliverables:

- full E2E/viewport/cross-browser/accessibility pass;
- performance budget report;
- README setup/operations/troubleshooting;
- known limitations và correction/incident procedure;
- loại toàn bộ placeholder, debug log và dead code.

Gate: Definition of Done trong `07-testing-acceptance.md` hoàn tất.

## Quy tắc làm việc cho coding agent

Ở đầu mỗi milestone, agent phải:

1. đọc `AGENTS.md`, các entry mới nhất trong `DEVELOPER_LOG.md` và docs liên quan;
2. nếu bắt đầu một task/session mới, append entry `STARTED` trước thay đổi đầu tiên;
3. nêu assumptions và file dự kiến sửa;
4. kiểm tra working tree để không ghi đè thay đổi của chủ repo;
5. implement phạm vi milestone;
6. chạy test/typecheck/lint/build phù hợp;
7. append entry đóng cùng session ID, ghi đúng file đã đổi, bằng chứng kiểm thử, safety/security impact và rủi ro/TODO còn lại;
8. chỉ sau đó mới gửi final response.

Không được sửa entry lịch sử để làm kết quả trông sạch hơn. Nếu một check fail rồi được sửa, entry đóng có thể ghi kết quả cuối cùng và tóm tắt lỗi quan trọng đã xử lý. Nếu task phải dừng, dùng `PAUSED` hoặc `BLOCKED`, không giả `COMPLETED`.

Agent phải dừng và hỏi trước khi:

- đổi công thức/signal/schema major;
- thêm login/backend/order placement/realtime;
- publish field/data/provider mới;
- thêm remote script/analytics;
- nới CSP bằng `unsafe-inline`, `unsafe-eval` hoặc origin ngoài;
- đưa secret vào bất kỳ nơi nào frontend có thể đọc;
- xóa/ghi đè thay đổi chưa commit không do agent tạo.
