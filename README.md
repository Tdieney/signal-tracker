# VN Stock Signal — Dashboard Tín hiệu Kỹ thuật & Market Breadth

VN Stock Signal là dashboard công khai (public static web app), cập nhật **cuối ngày (End-of-Day)**, giúp theo dõi độ rộng thị trường (Market Breadth) và lọc cổ phiếu Việt Nam (HOSE, HNX, UPCOM, VN30) theo quan hệ giữa giá đóng cửa và đường trung bình 10 phiên (**MA10**).

> **Tuyên bố miễn trừ trách nhiệm quan trọng:**
> Tín hiệu chỉ phản ánh quy tắc kỹ thuật trên dữ liệu cuối ngày, không phải khuyến nghị mua hoặc bán. Dữ liệu có thể chậm, thiếu hoặc sai; hãy kiểm tra lại với nguồn được cấp phép trước khi ra quyết định. Không cung cấp đặt lệnh, không lưu trữ tài khoản, không cam kết lợi nhuận.

---

## 1. Kiến trúc hệ thống

```text
CSV / Vnstock Provider
        ↓
Python Pipeline (Validation + MA10 + Signal Engine)
        ↓
Static JSON Files (manifest.json, overview.json, screener.json, symbols/*.json)
        ↓
React + TypeScript + Vite Static SPA (Lightweight Charts)
        ↓
GitHub Pages (Static Hosting & GitHub Actions Deployment)
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
│   └── deploy-pages.yml           # Pinned GitHub Pages deployment workflow
├── docs/                          # Bộ đặc tả yêu cầu (01-product-scope -> 08-implementation-plan)
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
│   ├── models.py                  # Dataclasses, enums, data contracts
│   ├── validation.py              # OHLC range/type/uniqueness validators
│   ├── indicators.py              # MA10, Distance %, Avg Volume 20D
│   ├── signals.py                 # Signal classification & market breadth
│   ├── serialization.py           # JSON serializers & staging builder
│   ├── build_dataset.py           # CLI entrypoint
│   └── providers/
│       ├── base.py                # DataProvider protocol
│       ├── csv_provider.py        # Offline deterministic CSV provider
│       └── vnstock_provider.py    # Optional vnstock adapter
├── tests/                         # Test suite & fixtures
│   ├── fixtures/                  # Deterministic multi-symbol CSV fixtures
│   ├── test_validation.py
│   ├── test_indicators.py
│   ├── test_signals.py
│   ├── test_serialization.py
│   └── test_csv_provider.py
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
- **Node.js**: v18+ hoặc v20+
- **npm**: v9+

### Bước 1: Cài đặt dependencies cho Frontend
```bash
cd frontend
npm install
cd ..
```

### Bước 2: Sinh dữ liệu mẫu (Static JSON Dataset)
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

1. **Kiểm thử Python Pipeline**:
   ```bash
   python -m unittest discover tests -v
   ```

2. **Kiểm thử Frontend (Vitest)**:
   ```bash
   npm --prefix frontend test
   ```

3. **Kiểm tra kiểu TypeScript (Typecheck)**:
   ```bash
   npm --prefix frontend run typecheck
   ```

4. **Build gói tĩnh cho Production**:
   ```bash
   npm --prefix frontend run build
   ```

5. **Quét bảo mật và kiểm tra Allow-list Artifact**:
   ```bash
   python scripts/security_check.py --artifact frontend/dist
   ```

---

## 5. Triển khai lên GitHub Pages

1. **Kích hoạt GitHub Pages**:
   - Vào mục **Settings** của repository trên GitHub.
   - Chọn mục **Pages** (tại thanh menu bên trái).
   - Trong phần **Build and deployment > Source**, chọn **GitHub Actions**.
   - Bật tùy chọn **Enforce HTTPS**.

2. **Tự động deploy**:
   - Workflow `.github/workflows/deploy-pages.yml` sẽ tự động chạy theo lịch sau giờ đóng cửa phiên giao dịch (17:30 ICT các ngày làm việc thứ Hai đến thứ Sáu) hoặc khi kích hoạt thủ công qua nút **Run workflow** trên tab Actions.

---

## 6. Chính sách An toàn & Bảo mật

- **Không chứa Secret ở Frontend**: Mọi biến môi trường, API keys, token đều tuyệt đối không được đưa vào frontend hoặc commit lên Git.
- **Static Content Security Policy (CSP)**: `index.html` được thiết lập CSP nghiêm ngặt không cho phép tải script từ xa hoặc dùng `unsafe-eval`.
- **Runtime Data Validation**: Frontend sử dụng Zod schema để kiểm tra tính toàn vẹn của mọi file JSON, tự động từ chối nếu không khớp `schema_version` hoặc `dataset_id`.
- **Thao tác dữ liệu an toàn**: Không sử dụng `dangerouslySetInnerHTML`, không dùng `eval`, mã cổ phiếu và query parameter đều được sanitize và kiểm tra qua allow-list.

---

## 7. Giới hạn đã biết của Phase 1

- Dữ liệu là **cuối ngày (EOD)** sau khi phiên giao dịch kết thúc, không phản ánh biến động realtime trong phiên.
- Chỉ số kỹ thuật chỉ áp dụng cho **MA10** và khối lượng trung bình 20 phiên. Các chỉ báo mở rộng (MA20, RSI, MACD) nằm trong kế hoạch Phase 2.
- Không hỗ trợ đặt lệnh, lưu danh mục trực tuyến hay tích hợp tài khoản cá nhân.
