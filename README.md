# VN Stock Signal — Dashboard Tín hiệu Kỹ thuật & Market Breadth

VN Stock Signal là dashboard công khai (public static web app), cập nhật **cuối ngày (End-of-Day)**, giúp theo dõi độ rộng thị trường (Market Breadth) và lọc cổ phiếu Việt Nam thuộc rổ chỉ số **VN30** (và toàn thị trường) theo quan hệ giữa giá đóng cửa và đường trung bình 10 phiên (**MA10**).

> **Tuyên bố miễn trừ trách nhiệm quan trọng:**
> Tín hiệu chỉ phản ánh quy tắc kỹ thuật trên dữ liệu cuối ngày, không phải khuyến nghị mua hoặc bán. Dữ liệu có thể chậm, thiếu hoặc sai; hãy kiểm tra lại với nguồn được cấp phép trước khi ra quyết định. Không cung cấp đặt lệnh, không lưu trữ tài khoản, không cam kết lợi nhuận.

---

## 1. Kiến trúc hệ thống & Luồng dữ liệu Phase 3

```text
Vnstock Market Client (EOD Market Quotes) / CsvDataProvider (Offline Baseline)
        ↓
Python Pipeline (Validation + Invariant Accounting + MA10 + Signal Engine)
        ↓
Transactional DatasetManager (Atomic Staging -> Validation -> Staging Promotion -> LKG Backup)
        ↓
Static JSON Files (manifest.json, overview.json, screener.json, symbols/*.json)
        ↓
React + TypeScript + Vite Static SPA (Lightweight Charts + Zod Schema Validation)
        ↓
GitHub Pages (Scheduled Cron 16:30 ICT / Push Deployment via GitHub Actions)
```

- **Sole Source of Truth**: Python pipeline tính toán toàn bộ chỉ báo và phân loại tín hiệu theo quy tắc toán học xác định. Frontend chỉ validate runtime schema (Zod), format hiển thị và thực hiện filter/sort.
- **Tín hiệu Baseline**:
  - `ABOVE_MA10`: Giá đóng cửa lớn hơn MA10 và duy trì từ phiên trước.
  - `BELOW_MA10`: Giá đóng cửa nhỏ hơn MA10 và duy trì từ phiên trước.
  - `CROSS_UP_MA10`: Hôm nay $Close_t > MA10_t$, phiên trước $Close_{t-1} \le MA10_{t-1}$.
  - `CROSS_DOWN_MA10`: Hôm nay $Close_t < MA10_t$, phiên trước $Close_{t-1} \ge MA10_{t-1}$.
  - Bằng nhau ($Close_t == MA10_t$): `signal = null`, `signal_reason = "ON_MA10"`.
  - Chưa đủ 10 phiên: `data_status = "INSUFFICIENT_DATA"`, `signal = null`.

---

## 2. Cấu trúc thư mục

```text
.
├── .github/workflows/
│   ├── ci.yml                     # CI workflow (lint, test, build, security scan)
│   └── deploy-pages.yml           # Pinned GitHub Pages deployment & daily cron (16:30 ICT)
├── docs/                          # Bộ đặc tả yêu cầu (01-product-scope -> 10-provider-decision-record)
├── frontend/                      # React + TypeScript + Vite SPA
│   ├── public/data/               # Static JSON dataset
│   ├── src/
│   │   ├── app/                   # App shell, routing, navigation
│   │   ├── components/            # Design system UI components & charts
│   │   ├── features/              # Overview, Screener, Symbol Detail pages
│   │   ├── lib/                   # API fetcher, formatters, URL filter helpers
│   │   ├── schemas/               # Zod runtime schema validators
│   │   └── styles/                # CSS custom property tokens & global layout
│   └── vite.config.ts
├── pipeline/                      # Python data pipeline
│   ├── models.py                  # Dataclasses, enums, universe definitions
│   ├── validation.py              # OHLC range/type/uniqueness validators
│   ├── indicators.py              # MA10, Distance %, Avg Volume 20D
│   ├── signals.py                 # Signal classification & market breadth
│   ├── freshness.py               # Trading calendar & session status evaluation
│   ├── dataset_manager.py         # Transactional staging, promotion & LKG rollback
│   ├── serialization.py           # JSON serializers & staging builder
│   ├── build_dataset.py           # CLI entrypoint
│   └── providers/
│       ├── base.py                # BaseMarketDataProvider abstract contract
│       ├── vnstock_client.py      # Resilient EOD HTTP quote client
│       ├── vnstock_provider.py    # Production Vnstock live adapter
│       ├── csv_provider.py        # Offline deterministic CSV provider
│       └── company_api_provider.py# Corporate authenticated API provider stub
├── tests/                         # Test suite & fixtures
│   ├── fixtures/                  # Deterministic multi-symbol CSV fixtures
│   ├── test_validation.py
│   ├── test_indicators.py
│   ├── test_signals.py
│   ├── test_serialization.py
│   ├── test_dataset_manager.py
│   ├── test_freshness_engine.py
│   ├── test_vnstock_client.py
│   ├── test_live_dataset_pipeline.py
│   └── test_provider_interface.py
├── scripts/
│   ├── security_check.py          # Secret scanner & artifact allow-list validator
│   └── build_all.py               # Master build orchestrator
├── AGENTS.md                      # Mandatory agent process rules
├── DEVELOPER_LOG.md               # Append-only developer log
└── README.md
```

---

## 3. Cài đặt và Chạy thử cục bộ (Local Development)

### Yêu cầu môi trường
- **Python**: 3.8+ (khuyên dùng Python 3.10+)
- **Node.js**: v18+, v20+ hoặc v24+
- **npm**: v9+

### Bước 1: Cài đặt dependencies cho Frontend
```bash
cd frontend
npm ci
npx playwright install --with-deps chromium firefox webkit
cd ..
```

### Bước 2: Sinh dữ liệu thị trường (Static JSON Dataset)

- **Chế độ trực tiếp VN30 (Vnstock live EOD)**:
  ```bash
  python pipeline/build_dataset.py --provider vnstock --universe VN30 --output frontend/public/data
  ```

- **Chế độ kiểm thử offline (CSV Fixture)**:
  ```bash
  python pipeline/build_dataset.py --provider csv --input tests/fixtures/sample_ohlcv.csv --output frontend/public/data
  ```

### Bước 3: Khởi chạy Frontend ở môi trường phát triển
```bash
cd frontend
npm run dev
```
Mở trình duyệt tại địa chỉ hiển thị (thường là `http://localhost:5173/`).

---

## 4. Các lệnh Kiểm thử và Build sản phẩm

### Chạy toàn bộ quy trình kiểm thử & build tự động
```bash
python scripts/build_all.py
```

### Chạy từng bước độc lập:

1. **Kiểm thử Python Pipeline (78 unit & integration tests)**:
   ```bash
   python -m unittest discover tests -v
   ```

2. **Kiểm thử Frontend (38 Vitest unit tests)**:
   ```bash
   npm --prefix frontend test -- --run
   ```

3. **Kiểm tra kiểu TypeScript (Typecheck)**:
   ```bash
   npm --prefix frontend run typecheck
   ```

4. **Build gói tĩnh cho Production (GitHub Pages base path)**:
   ```bash
   npm --prefix frontend run build:pages
   ```

5. **Quét bảo mật và kiểm tra Allow-list Artifact**:
   ```bash
   python scripts/security_check.py --artifact frontend/dist
   ```

6. **Kiểm thử E2E & Accessibility đa trình duyệt (Playwright 104 tests trên 6 browser profiles + Axe)**:
   ```bash
   npm --prefix frontend run test:e2e
   ```

---

## 5. Triển khai & Lịch cập nhật tự động (GitHub Pages)

1. **Lịch cập nhật tự động**:
   - Workflow `.github/workflows/deploy-pages.yml` chạy tự động vào **16:30 ICT (09:30 UTC), thứ Hai đến thứ Sáu** (sau khi phiên giao dịch HOSE/HNX kết thúc và dữ liệu EOD đã xác nhận).
   - Tự động kích hoạt khi có commit mới push lên branch `main`.

2. **Cơ chế Fail-Closed & Last-Known-Good**:
   - Nếu quá trình fetch dữ liệu từ nhà cung cấp bị gián đoạn hoặc không vượt qua kiểm định tính toàn vẹn, giao dịch cập nhật tự động hủy (`rollback_to_last_known_good`), bảo toàn bản phát hành thành công gần nhất mà không làm sập website.

---

## 6. Chính sách An toàn & Bảo mật

- **Không chứa Secret ở Frontend**: Mọi biến môi trường, API keys, token đều tuyệt đối không được đưa vào frontend hoặc commit lên Git.
- **Static Content Security Policy (CSP)**: `index.html` được thiết lập CSP nghiêm ngặt không cho phép `unsafe-eval` hoặc remote script. Thẻ style của thư viện biểu đồ được cấp quyền qua hash mã hóa tĩnh (`sha256-3pRED1tOXas1FXFoPb9TGCjmYe9XQsmO9OV23khV2nY=`).
- **Fail-Closed Runtime Validation**: Frontend sử dụng Zod schema để kiểm tra tính toàn vẹn của mọi file JSON, tự động khóa hiển thị tín hiệu và hiển thị thông báo an toàn nếu `manifest.json` lỗi hoặc không khớp `dataset_id`.
- **Thao tác dữ liệu an toàn**: Không sử dụng `dangerouslySetInnerHTML`, không dùng `eval`, mã cổ phiếu và query parameter đều được sanitize và kiểm tra qua allow-list.

---

## 7. Giới hạn và Vận hành Phase 3

- **Độ phủ rổ chỉ số**: Phase 3 tập trung vào 30 cổ phiếu đầu ngành thuộc rổ **VN30** (`ACB`, `BCM`, `BID`, `BVH`, `CTG`, `FPT`, `GAS`, `GVR`, `HDB`, `HPG`, `MBB`, `MSN`, `MWG`, `PLX`, `POW`, `SAB`, `SHB`, `SSB`, `SSI`, `STB`, `TCB`, `TPB`, `VCB`, `VHM`, `VIB`, `VIC`, `VJC`, `VNM`, `VPB`, `VRE`).
- **Dữ liệu cuối ngày**: Dữ liệu là **cuối ngày (End-of-Day)** sau khi phiên giao dịch kết thúc (sau 15:30 ICT), không phản ánh biến động realtime trong phiên.
- **Chỉ số kỹ thuật**: Áp dụng cho **MA10** và khối lượng trung bình 20 phiên với giải thích quy tắc kỹ thuật chi tiết.
- Không hỗ trợ đặt lệnh, lưu danh mục trực tuyến hay tích hợp tài khoản cá nhân.
