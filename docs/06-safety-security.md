# 06 — Safety và security

## 1. Security posture

Phase 1 là static public site. Không có authentication không đồng nghĩa “không cần bảo mật”: build pipeline có thể giữ secret, artifact có thể làm lộ dữ liệu, dependency có thể bị chiếm quyền và dữ liệu lỗi có thể gây quyết định tài chính sai.

Nguyên tắc cao nhất:

> Frontend và GitHub Pages là vùng public. Bất kỳ byte nào gửi tới browser hoặc nằm trong artifact đều không được coi là bí mật.

## 2. Tài sản cần bảo vệ

- API/provider credentials trong local/Actions.
- Quyền ghi repo và quyền deploy Pages.
- Tính toàn vẹn của công thức, signal và dataset.
- Dữ liệu có license/hạn chế phân phối.
- Niềm tin của người dùng về freshness, quality và ý nghĩa tín hiệu.
- Máy CI trước dependency/script độc hại.

Phase 1 không chủ động thu thập PII, portfolio, watchlist cloud hay hành vi người dùng.

## 3. Threat model tối thiểu

| Threat | Hậu quả | Control bắt buộc |
| --- | --- | --- |
| Secret bị bundle qua `VITE_*` | Lộ key công khai | Cấm secret trong frontend; scan source/artifact |
| Raw provider data bị copy vào `public/` | Vi phạm license/confidentiality | Allow-list field/file; staging + review artifact |
| Workflow/action bị supply-chain compromise | Lộ secret, sửa artifact | Least privilege; pin full SHA; lock dependency |
| PR không tin cậy chạy với secret | Exfiltration | Không dùng secret trong untrusted PR context; tránh `pull_request_target` checkout code PR |
| JSON bị lỗi/mismatch | Hiển thị signal sai | Runtime schema; cross-file `dataset_id`; fail closed |
| URL/query hoặc symbol độc hại | XSS/path traversal/crash | Parse allow-list; encode; symbol regex; không innerHTML |
| Third-party JS/analytics | Theo dõi hoặc chiếm DOM/data | Không third-party script mặc định; bundle/self-host |
| Dữ liệu cũ bị hiểu là hiện tại | Quyết định sai | Freshness status/banner; không che lỗi pipeline |
| Ngôn ngữ BUY/SELL | Người dùng hiểu là tư vấn | Copy policy, disclaimer và content tests |
| Chart chỉ dùng màu/hover | Người dùng không tiếp cận được thông tin | Text/table alternative; keyboard/touch behavior |

## 4. Ranh giới secret

### MUST

- Secret chỉ tồn tại trong local environment không commit hoặc GitHub Actions Secrets/environment secrets.
- `.env`, `.env.*`, credential file, raw response nhạy cảm và output tạm phải nằm trong `.gitignore` phù hợp.
- `.env.example` chỉ chứa tên biến và giá trị giả rõ ràng.
- Secret có scope/read permission tối thiểu, rotate định kỳ và rotate ngay nếu nghi lộ.
- Workflow mask/log discipline: không echo env, headers, full URL có token hay exception chứa credential.
- Nếu secret từng commit: revoke/rotate trước; chỉ xóa file không đủ vì Git history còn dữ liệu.

### MUST NOT

- Secret/API key trong `frontend/`, `public/`, JSON, source map, test snapshot hoặc client log.
- Prefix `VITE_` cho secret; Vite xác nhận các biến này lộ trong client bundle: [Vite documentation](https://vite.dev/guide/env-and-mode).
- Đưa secret vào prompt/chat, issue, screenshot hoặc build artifact.
- Dùng secret thật trong fixture/test.

## 5. Public-data allow-list

Chỉ các field được mô tả trong `04-data-contracts.md` được publish. Trước deploy, automated check phải:

1. liệt kê mọi file trong artifact;
2. reject extension/file lạ như `.env`, CSV raw, pickle, log, source map nếu policy tắt;
3. validate mọi JSON bằng schema;
4. scan secret patterns/high-entropy token;
5. kiểm tra tổng kích thước và kích thước mỗi file;
6. kiểm tra không có absolute path, provider endpoint, email/account id hoặc debug trace;
7. kiểm tra license/provider policy cho phép public các field đó.

Không publish raw company data lên GitHub Pages. Nếu provider license không rõ, dừng deploy và dùng fixture/demo public đã được phép.

## 6. Input và output safety

- Mọi provider response là untrusted input: validate type, range, symbol, exchange, date, uniqueness và OHLC invariant.
- Network call có HTTPS, hostname allow-list, timeout, retry hữu hạn với backoff và rate-limit hợp lý.
- Không ghép user/provider value vào shell command.
- Không deserialize pickle hoặc executable format từ nguồn ngoài.
- JSON serialization dùng library chuẩn, không string-concatenate.
- Frontend render text bằng React escaping; cấm `dangerouslySetInnerHTML` cho provider/URL content.
- Không dùng `eval`, `new Function`, dynamic script insertion hoặc URL `javascript:`.
- Symbol detail path chỉ được tạo sau khi match `^[A-Z0-9]{1,10}$` và URL encode.
- Filter/sort parse từ allow-list, có min/max; malformed input không làm app crash.

## 7. Browser hardening trên static hosting

- Enforce HTTPS trong GitHub Pages settings và không tải mixed content.
- Không dùng remote script, remote font hoặc analytics mặc định.
- `index.html` có CSP bằng `<meta http-equiv="Content-Security-Policy">` phù hợp static app, tuân thủ đúng policy chuẩn:

```text
default-src 'self';
script-src 'self';
style-src 'self' 'sha256-3pRED1tOXas1FXFoPb9TGCjmYe9XQsmO9OV23khV2nY=';
img-src 'self' data:;
font-src 'self';
connect-src 'self';
object-src 'none';
base-uri 'self';
form-action 'self';
```

- Không dùng `'unsafe-inline'` hoặc `'unsafe-eval'`. Hash `'sha256-3pRED1tOXas1FXFoPb9TGCjmYe9XQsmO9OV23khV2nY='` là bắt buộc cho thẻ style tự động inject bởi thư viện `lightweight-charts@4.2.1`. Mọi wildcard `*`, duplicate directive, hoặc token lạ (như `data:` trong `connect-src`) đều bị bộ quét an ninh từ chối.

- Không nhúng untrusted iframe. Nếu tương lai cần third-party content phải threat-model lại, sandbox và giới hạn origin.
- Không dựa vào client-side code để bảo vệ dữ liệu lẽ ra phải private.

Tham chiếu: [OWASP Content Security Policy Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Content_Security_Policy_Cheat_Sheet.html), [OWASP Third Party JavaScript Management](https://cheatsheetseries.owasp.org/cheatsheets/Third_Party_Javascript_Management_Cheat_Sheet.html), [GitHub Pages HTTPS](https://docs.github.com/en/pages/getting-started-with-github-pages/securing-your-github-pages-site-with-https).

## 8. GitHub Actions và Filesystem hardening

- **GitHub Actions Node 24 runtime**:
  - Toàn bộ các GitHub Actions chính thức được ghim (`pin`) bằng full immutable commit SHA từ upstream và chạy trên runtime Node 24:
    - `actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1`
    - `actions/setup-python@ece7cb06caefa5fff74198d8649806c4678c61a1 # v6.3.0`
    - `actions/setup-node@820762786026740c76f36085b0efc47a31fe5020 # v7.0.0`
    - `actions/configure-pages@45bfe0192ca1faeb007ade9deae92b16b8254a0d # v6.0.0`
    - `actions/upload-pages-artifact@fc324d3547104276b827a68afc52ff2a11cc49c9 # v5.0.0`
    - `actions/deploy-pages@cd2ce8fcbc39b97be8ca5fce6e763baed58fa128 # v5.0.0`
- **Quy trình xuất bản thư mục an toàn (Transactional Directory Replacement with Rollback)**:
  - Dữ liệu luôn được ghi và xác thực tính toàn vẹn đầy đủ trong thư mục staging riêng biệt (`.dataset_build_<uuid>`).
  - Đường dẫn đích được kiểm tra nghiêm ngặt chống thoát workspace (`validate_target_directory` từ chối `.`, `..`, home, filesystem roots, system dirs, symlink escape, và directory overlap).
  - Quá trình publish vào output trực tiếp sử dụng cơ chế: backup thư mục output cũ sang `.backup_<uuid>` -> rename staging sang output -> xóa backup. Nếu xảy ra lỗi giữa chừng, hệ thống tự động rollback phục hồi nguyên vẹn backup về output ban đầu.
  - *Lưu ý về Crash Window*: Trong trường hợp sự cố phần cứng/mất điện đột ngột ngay tại thời điểm giữa 2 bước rename, thư mục backup có thể tạm thời tồn tại và được dọn dẹp ở lần build kế tiếp.

## 9. Dependency và repository hygiene

- Commit lockfile; CI install từ lockfile.
- Review lifecycle/license của dependency; xóa dependency không dùng.
- Bật Dependabot/security alerts nếu repo cho phép; xử lý critical/high trước deploy.
- Secret scanning trong CI và, nếu có, GitHub secret scanning/push protection.
- `.gitignore` bao phủ local env, cache, raw downloads, output tạm và coverage không cần commit.
- Production source map mặc định tắt hoặc chỉ publish sau review vì có thể làm lộ implementation/debug context.
- Không auto-merge dependency update chạm pipeline/deploy mà chưa qua test.

## 10. Financial-safety controls

### Ý nghĩa tín hiệu

- Tín hiệu chỉ được xác nhận khi market session metadata là `CLOSED_CONFIRMED`.
- Luôn hiển thị `as_of_date`, freshness và data quality gần tín hiệu.
- Không biến lỗi/thiếu dữ liệu thành signal.
- Không forward-fill ngày không giao dịch.
- Không dùng look-ahead data.
- Không dùng từ BUY/SELL hoặc hiệu suất kỳ vọng ở Phase 1.

### Disclaimer

Disclaimer phải xuất hiện ở footer toàn app và trang detail:

> Tín hiệu chỉ phản ánh quy tắc kỹ thuật trên dữ liệu cuối ngày, không phải khuyến nghị mua hoặc bán. Dữ liệu có thể chậm, thiếu hoặc sai; hãy kiểm tra lại với nguồn được cấp phép trước khi ra quyết định.

Disclaimer không được dùng để bào chữa cho UI đánh lừa; freshness và lỗi vẫn phải rõ ràng ngay tại vị trí quyết định.

### Scope guard

Nếu yêu cầu mới có đặt lệnh, login, portfolio cá nhân, API công ty hoặc dữ liệu realtime: dừng Phase 1, tạo threat model/architecture mới và cần chủ repo duyệt. Không “thêm tạm” vào static site.

## 11. Incident checklist

### Nghi lộ secret

1. Dừng workflow/deploy liên quan.
2. Revoke/rotate secret tại provider trước.
3. Xác định nơi lộ: Git history, Actions log/artifact, Pages bundle, cache.
4. Gỡ artifact/log public khi có quyền và cần thiết.
5. Làm sạch history theo quy trình được duyệt; thông báo collaborator phải re-clone nếu cần.
6. Bổ sung regression scan/test và ghi incident note không chứa secret.

### Dataset sai

1. Đánh dấu/dừng deploy; không đổi timestamp để giả như mới.
2. Roll forward bằng dataset đã validate hoặc tạm ngừng site với banner rõ.
3. Xác định phạm vi ngày/mã/metric bị ảnh hưởng.
4. Fix + test regression + regenerate toàn bộ dataset nhất quán.
5. Ghi changelog/correction note nếu bản sai đã public.

## 12. Security Definition of Done

- Không có secret trong git diff, frontend bundle, source map hay artifact.
- Public JSON pass schema và allow-list.
- CSP không cần `unsafe-eval`; remote origin bằng 0 ở Phase 1.
- Actions permissions tối thiểu; actions pin SHA.
- Untrusted PR không nhận secret.
- HTTPS được enforce khi cấu hình Pages.
- Malformed URL/JSON có test và không gây XSS/crash toàn app.
- Disclaimer, freshness, partial/stale/error states pass acceptance test.
