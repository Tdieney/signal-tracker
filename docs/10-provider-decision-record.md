# 10 — Provider Decision Record (PDR): Vietnam EOD Market Data

## 1. Context & Purpose

Phase 3 requires transitioning from static demo CSV fixtures to real End-of-Day (EOD) market data for the Vietnam stock market (HOSE, HNX, UPCOM / VN30, VN100), running automated daily updates via server-side GitHub Actions workflows while maintaining zero secret leakage, fail-closed dataset integrity, and Last-Known-Good preservation.

---

## 2. Evaluation Matrix

| Criterion | Option A: Vnstock (Community / Open Quotes) | Option B: Corporate Market API (SSI FastConnect / Vietstock / FiinGroup) | Option C: Direct Public Portal EOD (CafeF / Exchange Summary) |
| :--- | :--- | :--- | :--- |
| **Licence & Public Rights** | Open-source Python client (MIT). Public quotes used for research & personal technical dashboards. | Commercial API licence. Public web redistribution requires commercial redistribution agreement. | Public aggregated daily market tables. Derived indicators (MA10) redistribution allowed. |
| **Coverage** | All HOSE, HNX, UPCOM tickers (VN30, VN100, custom universes). | Full official exchange coverage (HOSE, HNX, UPCOM, Derivatives). | All listed tickers across HOSE & HNX. |
| **EOD Availability & Reliability** | Available after 15:00–15:30 ICT. High availability with retry and rate-limiting. | High SLA, official exchange feeds, low latency. | Available after 15:30–16:00 ICT daily. |
| **Rate Limit** | ~1–2 requests/sec (handled via sleep backoff). | High limits (10–50+ req/sec). | Moderate rate limits (~2–5 req/sec). |
| **Authentication & Cost** | **Free** ($0). No API key required. | **Paid** ($50–$500+/mo). Requires `DATA_API_KEY` & `DATA_API_BASE_URL` in GitHub Secrets. | **Free** ($0). No API key required. |
| **Secret Safety** | Zero secrets required. | Server-side only via GitHub Actions Secrets (never exposed in frontend). | Zero secrets required. |
| **Fail-Closed & LKG** | Full rollback via `DatasetManager`. Target remains on LKG if fetch/validation fails. | Full rollback via `DatasetManager`. Target remains on LKG if fetch/validation fails. | Full rollback via `DatasetManager`. Target remains on LKG if fetch/validation fails. |

---

## 3. Implementation Blueprint for Phase 3

Regardless of the chosen provider:
1. **Server-Side Execution**: All data fetching and indicator calculation execute strictly in Python during GitHub Actions workflow builds or scheduled cron runs. The frontend remains 100% static JSON consumer.
2. **Zero Secret Leakage**: Any provider credentials exist solely as repository secrets in GitHub Actions and environment variables. Public artifacts (`frontend/dist`, `data/*`) never contain tokens, URLs with credentials, or raw responses.
3. **Data Integrity & Validation**: Every fetched row is validated through `pipeline.validation.validate_record` ensuring strict symbol pattern `^[A-Z0-9]{1,10}$`, OHLC invariants, positive prices, valid calendar dates (2025–2027), and row accounting (`input_rows == accepted_rows + rejected_rows`).
4. **Freshness & Provenance**: `manifest.json` accurately reflects `provenance` (`vnstock` / `company_api`), `data_status`, and `market_session_status`.
5. **Fail-Closed Safety**: Any network failure, rate limit exhaustion, or schema violation aborts the publish transaction cleanly, keeping the live GitHub Pages site on the Last-Known-Good dataset.
