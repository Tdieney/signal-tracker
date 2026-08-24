# Bộ tài liệu triển khai VN Stock Signal

Thư mục này là nguồn yêu cầu chuẩn để con người và AI triển khai **Phase 1** của website. Mục tiêu là tránh việc “vibe code” làm sai nghiệp vụ, tạo hai trải nghiệm desktop/mobile lệch nhau, hoặc vô tình công khai secret và dữ liệu không được phép.

Trước khi đọc bộ tài liệu này, mọi coding agent MUST đọc `AGENTS.md` ở root và các entry mới nhất trong `DEVELOPER_LOG.md`. Mọi task làm thay đổi repository phải có entry `STARTED` trước khi sửa và entry đóng `COMPLETED`, `PAUSED` hoặc `BLOCKED` trước khi agent trả lời cuối cùng.

## Thứ tự đọc bắt buộc

1. [01-product-scope.md](01-product-scope.md) — phạm vi, người dùng, thuật ngữ và các quyết định đã khóa.
2. [02-ux-responsive.md](02-ux-responsive.md) — luồng sử dụng và hành vi nhất quán giữa desktop/mobile.
3. [03-design-system.md](03-design-system.md) — token, component, accessibility và quy tắc trình bày.
4. [04-data-contracts.md](04-data-contracts.md) — schema JSON công khai, công thức và quy tắc dữ liệu.
5. [05-architecture.md](05-architecture.md) — kiến trúc repo, frontend, pipeline và deploy.
6. [06-safety-security.md](06-safety-security.md) — threat model, ranh giới public/secret và checklist bảo mật.
7. [07-testing-acceptance.md](07-testing-acceptance.md) — test plan và Definition of Done.
8. [08-implementation-plan.md](08-implementation-plan.md) — trình tự code theo milestone.
9. [AI-CODING-PROMPT.md](AI-CODING-PROMPT.md) — prompt giao toàn bộ việc triển khai cho coding agent.

## Quy tắc ưu tiên khi tài liệu mâu thuẫn

1. Quy trình agent/developer log bắt buộc trong root `AGENTS.md`.
2. Safety/security trong `06-safety-security.md`.
3. Công thức và data contract trong `04-data-contracts.md`.
4. Phạm vi trong `01-product-scope.md`.
5. Acceptance criteria trong `07-testing-acceptance.md`.
6. UX/design/architecture còn lại.

Không được âm thầm chọn một cách hiểu. AI phải ghi lại mâu thuẫn, đề xuất phương án nhỏ nhất và chờ chủ repo xác nhận trước khi thay đổi signal, schema public, ranh giới bảo mật hoặc phạm vi Phase 1.

## Quy ước tài liệu

- Từ khóa **MUST**, **MUST NOT**, **SHOULD**, **MAY** lần lượt có nghĩa: bắt buộc, cấm, nên làm, có thể làm.
- Giao diện mặc định dùng tiếng Việt; tên field, type, enum và code dùng tiếng Anh.
- Giá trị thời gian trong JSON dùng ISO 8601; ngày giao dịch dùng `YYYY-MM-DD`.
- Website là công cụ nghiên cứu kỹ thuật cuối ngày, không phải terminal realtime và không phải tư vấn đầu tư.
- Phase 1 là website public. Mọi file được deploy đều phải được coi là ai trên Internet cũng đọc được.

## Cách cập nhật

Mỗi thay đổi nghiệp vụ phải cập nhật đồng thời:

- tài liệu liên quan;
- schema/type tương ứng;
- fixture;
- unit/integration test;
- `schema_version` nếu có breaking change.

Không đánh dấu một milestone hoàn tất nếu tài liệu và code đang mô tả hai hành vi khác nhau.

## Developer log bắt buộc

`DEVELOPER_LOG.md` ở root là log duy nhất và append-only cho mọi AI/coding agent. Agent không được tạo log riêng theo tên model, milestone hoặc ngày.

- Mở một entry `STARTED` trước thay đổi đầu tiên.
- Dùng cùng session ID để append entry đóng trước final response.
- Ghi file thực sự đã đổi và bằng chứng kiểm thử thực sự đã chạy; không ghi “pass” nếu chưa chạy.
- Không sửa lịch sử entry của agent khác; sai thì append correction.
- Không ghi secret, raw/confidential data hoặc private chain-of-thought.
- Thiếu entry đóng đồng nghĩa task chưa đạt Definition of Done.
