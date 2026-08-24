# Prompt giao cho AI coding agent

Copy toàn bộ prompt tiếng Anh dưới đây vào coding agent đang mở tại root của repository.

```text
You are implementing Phase 1 of this repository as a production-quality, public, end-of-day Vietnam stock technical-signal dashboard.

First, read root `AGENTS.md`, the latest entries in root `DEVELOPER_LOG.md`, every Markdown file in `docs/` in the exact order listed by `docs/README.md`, and then the root `README.md`. Treat `AGENTS.md` as the mandatory agent-process contract and `docs/` as the implementation contract. If documents conflict, follow the precedence rules in `docs/README.md`.

Mandatory developer log protocol:
- `DEVELOPER_LOG.md` at repository root is the only developer log and is append-only.
- Before your first repository modification, append a `STARTED` entry using the template in that file. Include a unique session ID, ISO 8601 timestamp with UTC offset, agent identity if known, request, scope, assumptions, planned files, and pre-existing working-tree changes.
- Before every final response, append a closing entry with the same session ID and status `COMPLETED`, `PAUSED`, or `BLOCKED`. Record the actual summary, decisions, exact changed files, commands/checks and truthful results, safety/security/data impact, and remaining work.
- Never delete, reorder, rewrite, or reformat historical entries. Append a correction if an older entry is wrong.
- Never log secrets, credentials, private endpoints, confidential/raw provider data, personal data, full sensitive output, or private chain-of-thought.
- Do not claim the task or milestone is complete until its closing entry is saved.

Product boundary:
- Build only Phase 1.
- The product is an end-of-day MA10 market-breadth dashboard and technical screener.
- It is not realtime, not an AI prediction system, not investment advice, and not an order-entry system.
- Do not add authentication, a database, a request-time backend, broker integration, portfolio tracking, BUY/SELL recommendations, analytics, or remote third-party scripts.

Required stack and architecture:
- Frontend: React, TypeScript, and Vite.
- Charts: TradingView Lightweight Charts using our own validated JSON data.
- Pipeline: Python and Pandas behind a DataProvider interface.
- Hosting: static GitHub Pages.
- Routing: hash routing, with all assets/data resolved from Vite's BASE_URL.
- CsvDataProvider and deterministic, license-safe fixtures must work without network access or secrets.
- VnstockDataProvider is optional and must be isolated behind the provider interface; do not block the core implementation on it.
- The Python pipeline is the sole authority for indicators and signals. The frontend must never recalculate or redefine them.

Mandatory behavior:
- Implement overview, screener, and symbol-detail routes.
- Implement MA10, average volume 20D, distance percentage, MA10 breadth, ABOVE_MA10, BELOW_MA10, CROSS_UP_MA10, and CROSS_DOWN_MA10 exactly as specified in `docs/04-data-contracts.md`.
- Never forward-fill non-trading days.
- Insufficient or invalid data must remain visibly insufficient/invalid and must never become a signal.
- Generate versioned manifest, overview, screener, and per-symbol static JSON files.
- Runtime-validate JSON at the frontend boundary and fail closed on unsupported schema versions or mismatched dataset IDs.
- Display dataset date, freshness, session confirmation, and data-quality status prominently.
- Use the exact safety language and avoid BUY/SELL or persuasive financial language.

Responsive and accessibility requirements:
- One app, one state model, and one filtering implementation across desktop and mobile.
- Support 320px and wider, 200% zoom, portrait and landscape.
- Wide layouts use a semantic table; compact layouts use a card/list with the same required data and results.
- Mobile filters use an accessible dialog/bottom sheet; desktop filters remain visible.
- Filter/sort/page state is URL-serializable and survives reload.
- Meet the responsive, keyboard, touch, screen-reader, contrast, reduced-motion, and chart-alternative requirements in the docs.
- Target WCAG 2.2 AA.

Security and safety are release blockers:
- Assume every frontend file and GitHub Pages artifact is public.
- Never put credentials or sensitive values in frontend code, `public/`, JSON, source maps, logs, fixtures, or `VITE_*` variables.
- Do not use `dangerouslySetInnerHTML`, eval, dynamic scripts, untrusted iframes, runtime CDN scripts, or remote analytics.
- Validate provider input, URL filters, symbols, schemas, OHLC invariants, and cross-file consistency.
- Add an artifact file/field allow-list and secret scan before deployment.
- Add a restrictive static-compatible CSP without `unsafe-eval` or unnecessary remote origins.
- GitHub Actions must use least-privilege permissions. Untrusted pull requests must never receive secrets. Pin all actions to verified full commit SHAs.
- Never publish raw provider/company data. If redistribution rights are unclear, stop and use the approved CSV fixture.

Implementation process:
1. Inspect the current working tree, append the required `STARTED` log entry, and preserve all unrelated/user-authored changes.
2. Before coding, report:
   - your understanding of the scope;
   - assumptions;
   - proposed final file tree;
   - exact commands you intend to use;
   - security-sensitive decisions.
3. Implement the milestones in `docs/08-implementation-plan.md` in order. Do not jump directly to polished UI before the data contracts and deterministic tests pass.
4. At each milestone:
   - change only what is in scope;
   - keep docs, schemas, types, fixtures, and tests synchronized;
   - run the relevant lint, typecheck, unit/integration tests, and production build;
   - fix failures before continuing;
   - summarize changed files and verification evidence.
5. Use current stable dependency versions that are compatible with each other, commit lockfiles, and prefer a small dependency surface. Do not silently switch the required stack.
6. Do not replace real implementation with TODOs, hidden mocks, fake production data, or tests that only assert implementation details.
7. Finish with the complete validation matrix in `docs/07-testing-acceptance.md`, inspect the production artifact, and update the root README with setup, test, fixture-build, production-build, and GitHub Pages deployment instructions.
8. Append the required closing developer-log entry after verification and before your final response. Ensure its file list and check results match reality.

Stop and ask the repository owner before doing any of the following:
- changing a signal formula, the eligible-universe definition, freshness semantics, or a public schema major version;
- adding realtime data, login, a backend, a database, company/private data, trading, BUY/SELL language, analytics, or a remote script;
- weakening CSP, exposing a new public field, or changing a security boundary;
- deleting or overwriting uncommitted work that you did not create;
- proceeding when data licensing or permission to publish is unclear.

Definition of done:
- All required functionality and routes work with the deterministic CSV fixture.
- Pipeline, frontend, E2E, responsive viewport, accessibility, security, and production-build checks pass.
- Desktop and mobile produce identical filter results and signal meanings.
- GitHub Pages subpath routing/assets work.
- The inspected artifact contains no secret, raw data, unexpected files, or schema mismatch.
- The final response lists changed files, exact verification commands and results, known limitations, and any manual GitHub settings still required (for example enabling Pages and enforcing HTTPS).
- `DEVELOPER_LOG.md` contains truthful `STARTED` and closing entries for the session, and no historical entry was altered.

Start by reading, inspecting the working tree, and appending the `STARTED` developer-log entry. Then report and implement Milestone 0. Continue milestone by milestone unless a stop condition above is reached. Append the closing log entry before every final response.
```

## Prompt ngắn để tiếp tục sau mỗi lần AI dừng

```text
Continue with the next incomplete milestone in `docs/08-implementation-plan.md`. Follow root `AGENTS.md`: read the latest `DEVELOPER_LOG.md` entries, append a `STARTED` entry before changing the repository, preserve user changes, run the milestone gates, append a truthful closing entry, and only then report evidence. Do not expand Phase 1 or weaken any safety/security requirement.
```
