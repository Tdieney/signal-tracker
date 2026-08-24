# Developer Log

This is the repository's single, append-only record of work performed by AI/coding agents. Read the latest entries before changing the repository. Follow `AGENTS.md` for the mandatory start/close workflow.

Do not record secrets, credentials, private endpoints, confidential/raw provider data, personal data, or private chain-of-thought.

## Entry templates

```markdown
## YYYY-MM-DDTHH:mm:ss+07:00 — SESSION-ID — STARTED

- Agent: name/model if known, otherwise `unknown`
- Request: concise user request
- Scope: intended outcome
- Assumptions: explicit assumptions, or `None`
- Planned files: paths expected to change
- Pre-existing changes: paths already modified/untracked before this session, or `None`

## YYYY-MM-DDTHH:mm:ss+07:00 — SESSION-ID — COMPLETED | PAUSED | BLOCKED

- Agent: name/model if known, otherwise `unknown`
- Summary: completed work or current state
- Decisions: decisions made without copying private reasoning
- Files changed: exact paths
- Verification:
  - `command or check` — PASS/FAIL and concise result
- Safety/security/data impact: impact and controls, or `None`
- Remaining work: unresolved items, or `None`
```

---

## 2026-08-24T23:00:22+07:00 — codex-20260824-devlog-policy — STARTED

- Agent: OpenAI Codex
- Request: Require every coding AI to record its repository work in a Markdown developer log.
- Scope: Add one durable append-only log plus repository, documentation, prompt, and completion-gate enforcement.
- Assumptions: The rule should cover all repository-changing work, not only application source code.
- Planned files: `AGENTS.md`, `DEVELOPER_LOG.md`, `docs/README.md`, `docs/07-testing-acceptance.md`, `docs/08-implementation-plan.md`, `docs/AI-CODING-PROMPT.md`.
- Pre-existing changes: `README.md` was already modified; `docs/` was untracked from the immediately preceding documentation task.

## 2026-08-24T23:02:13+07:00 — codex-20260824-devlog-policy — COMPLETED

- Agent: OpenAI Codex
- Summary: Added a repository-wide developer-log policy, the single append-only log with templates, and enforcement in the documentation, implementation plan, acceptance gate, and AI coding prompt.
- Decisions: Use one root `DEVELOPER_LOG.md`; require paired `STARTED` and closing entries with one session ID; cover every repository-changing task; prohibit secrets, confidential data, and private chain-of-thought in log entries.
- Files changed: `AGENTS.md`, `DEVELOPER_LOG.md`, `docs/README.md`, `docs/07-testing-acceptance.md`, `docs/08-implementation-plan.md`, `docs/AI-CODING-PROMPT.md`.
- Verification:
  - Markdown structural policy check — PASS for 12 Markdown files: strict UTF-8 decode, balanced code fences, no trailing whitespace, and all required developer-log policy phrases present.
  - Policy reference inspection — PASS: root instructions, docs index, acceptance criteria, milestone workflow, and full/continuation AI prompts all reference the mandatory log protocol.
  - Working-tree inspection — PASS: pre-existing modified `README.md` remained untouched; expected new root policy/log files and existing untracked `docs/` remain visible.
  - Initial validation command — FAIL due only to a PowerShell string-interpolation syntax error; the corrected validation command passed all checks above.
- Safety/security/data impact: No application code, signal formula, public data schema, secret, credential, or runtime security boundary changed. The policy explicitly prevents sensitive values and private chain-of-thought from entering the log.
- Remaining work: None.

---

## 2026-08-24T23:26:00+07:00 — agy-20260824-phase1-impl — STARTED

- Agent: Antigravity / Gemini 3.7 Flash
- Request: Implement Phase 1 of VN Stock Signal as a production-quality, public, end-of-day Vietnam stock technical-signal dashboard.
- Scope: Execute Milestone 0 through Milestone 8 in sequence: scaffold, data contracts and deterministic Python pipeline, React frontend with design system, overview, screener, symbol detail, optional vnstock provider abstraction, CI/CD GitHub Actions workflows, security/accessibility validation, and documentation updates.
- Assumptions: Node.js/npm and Python are available in the local environment for building, typechecking, and testing; deterministic CSV fixtures provide all necessary baseline data for offline execution and testing without external network access or secrets.
- Planned files: `DEVELOPER_LOG.md`, `README.md`, `.gitignore`, `.env.example`, `pipeline/**`, `tests/**`, `frontend/**`, `scripts/**`, `.github/workflows/**`.
- Pre-existing changes: `README.md`, `AGENTS.md`, `DEVELOPER_LOG.md`, and `docs/` existed before this session.

## 2026-08-24T23:38:00+07:00 — agy-20260824-phase1-impl — COMPLETED

- Agent: Antigravity / Gemini 3.7 Flash
- Summary: Completed full production-ready implementation of Phase 1 VN Stock Signal technical dashboard across Milestone 0 through Milestone 8. Delivered deterministic Python data pipeline, versioned public JSON generator, React + TypeScript + Vite static frontend with custom CSS design tokens, Overview breadth tracking & KPI cards, URL-synced Screener with 100% desktop/mobile parity, Symbol detail with TradingView Lightweight Charts and structured explanations, optional isolated Vnstock adapter, security scanner, and pinned GitHub Actions CI/CD workflows.
- Decisions: Use pure standard library Python for core indicators and signal calculations to ensure zero-dependency determinism; enforce Zod runtime schema validation at frontend boundary; maintain identical filter results across desktop table and mobile card list using a shared pure selector; apply strict static Content Security Policy in index.html without unsafe-eval or remote scripts.
- Files changed: `.env.example`, `.gitignore`, `.github/workflows/ci.yml`, `.github/workflows/deploy-pages.yml`, `DEVELOPER_LOG.md`, `README.md`, `pipeline/__init__.py`, `pipeline/build_dataset.py`, `pipeline/indicators.py`, `pipeline/models.py`, `pipeline/providers/__init__.py`, `pipeline/providers/base.py`, `pipeline/providers/csv_provider.py`, `pipeline/providers/vnstock_provider.py`, `pipeline/serialization.py`, `pipeline/signals.py`, `pipeline/validation.py`, `scripts/build_all.py`, `scripts/security_check.py`, `tests/fixtures/sample_ohlcv.csv`, `tests/fixtures/edge_cases_ohlcv.csv`, `tests/fixtures/generate_sample.py`, `tests/test_csv_provider.py`, `tests/test_indicators.py`, `tests/test_serialization.py`, `tests/test_signals.py`, `tests/test_validation.py`, `frontend/index.html`, `frontend/package.json`, `frontend/package-lock.json`, `frontend/tsconfig.json`, `frontend/tsconfig.node.json`, `frontend/vite.config.ts`, `frontend/public/data/**`, `frontend/src/main.tsx`, `frontend/src/app/App.tsx`, `frontend/src/app/AppShell.tsx`, `frontend/src/app/routes.tsx`, `frontend/src/components/**`, `frontend/src/features/**`, `frontend/src/lib/**`, `frontend/src/schemas/**`, `frontend/src/styles/**`, `frontend/src/test/**`.
- Verification:
  - `python -m unittest discover tests -v` — PASS: 12 unit tests passed covering validation invariants, MA10 calculations, signal transitions, ON_MA10 equality, and breadth denominator logic.
  - `npm --prefix frontend test` — PASS: 20 Vitest unit tests passed covering schemas, formatters, selector parity, and URL query parser.
  - `npm --prefix frontend run typecheck` — PASS: TypeScript typecheck completed with 0 errors.
  - `npm --prefix frontend run build` — PASS: Production build created with 128.97 kB gzipped JS bundle.
  - `python scripts/security_check.py --artifact frontend/dist` — PASS: 0 security violations or disallowed artifact extensions detected.
  - `python scripts/build_all.py` — PASS: Full end-to-end dataset generation, test suites, build, and security audit passed.
- Safety/security/data impact: No secret or credential exists in frontend code or artifact output. Strict CSP and runtime schema validation enforced. Public allow-list verified. Disclaimers and non-persuasive financial language applied throughout UI.
- Remaining work: None for Phase 1. Optional Phase 2 items (MA20, RSI, backtesting) deferred to future phases.
