# 04 — Data contracts và quy tắc tính

## 1. Nguyên tắc

- Pipeline là nơi duy nhất tính indicator và signal. Frontend chỉ validate, format, filter và hiển thị.
- JSON public là API contract có version; không đọc trực tiếp CSV/provider trong browser.
- Mọi số không hợp lệ (`NaN`, `Infinity`) phải bị loại/chuyển thành `null` theo schema trước khi serialize; JSON không được chứa token phi chuẩn.
- Sort và tính toán dùng raw number; chuỗi format chỉ tạo ở UI.
- Tất cả schema phải có fixture hợp lệ, fixture sai và automated validation.

## 2. Input OHLCV chuẩn hóa

```text
trading_date:   date YYYY-MM-DD
symbol:         uppercase string ^[A-Z0-9]{1,10}$
exchange:       HOSE | HNX | UPCOM
open:           number > 0
high:           number > 0
low:            number > 0
close:          number > 0
adjusted_close: number > 0 | null
volume:         integer >= 0
trading_value:  number >= 0 | null
```

Validation OHLC:

```text
high >= max(open, close, low)
low  <= min(open, close, high)
unique(symbol, trading_date)
```

- Loại duplicate theo policy xác định; mặc định fail dataset build và báo lỗi, không “giữ dòng cuối” im lặng.
- Không forward-fill OHLCV cho ngày không giao dịch.
- Mỗi mã tính rolling window trên các phiên hợp lệ của chính mã đó.
- Corporate action: ưu tiên `adjusted_close` nếu provider có dữ liệu đáng tin và metadata nói rõ; Phase 1 mặc định dùng `close` cho tín hiệu để bám đúng định nghĩa README. Không tự đổi sang adjusted data.
- **Quy tắc xử lý lỗi và phân cấp trạng thái chất lượng (`QualityStatus`)**:
  - Khi một dòng dữ liệu vi phạm các trường bắt buộc (thiếu hoặc sai format ngày, mã, sàn, giá OHLC âm/không hữu hạn, vi phạm bất biến OHLC, volume âm): dòng đó bị loại bỏ hoàn toàn (`rejected_rows` tăng), và một cảnh báo đã khử khuẩn (`sanitized warning`) được ghi nhận mà không chứa chuỗi dữ liệu thô nhạy cảm.
  - Khi các trường số tùy chọn (`adjusted_close`, `trading_value`) không hợp lệ: dòng có thể được tiếp nhận với giá trị `None` nhưng lỗi được ghi nhận vào `parse_warnings` và `quality.status` bị hạ cấp, không được phép duy trì ở mức `PASS`.
  - `quality.status` được xác định:
    - `PASS`: 0 dòng bị loại (`rejected_rows == 0`) và không có cảnh báo vi phạm;
    - `PARTIAL` / `WARNING`: Có dòng bị loại hoặc có cảnh báo về trường tùy chọn nhưng vẫn có ít nhất 1 dòng hợp lệ (`accepted_rows > 0`);
    - `FAIL`: Không có dòng hợp lệ nào (`accepted_rows == 0`).

## 3. Công thức baseline

Với phiên hợp lệ thứ `t`:

```text
MA10[t] = mean(close[t-9 : t])
distance_pct[t] = (close[t] - MA10[t]) / MA10[t] * 100
avg_volume_20d[t] = mean(volume[t-19 : t])
```

- `MA10` chỉ có khi đủ 10 close hợp lệ.
- `avg_volume_20d` là `null` nếu chưa đủ 20 phiên.
- Không round trước khi so sánh; chỉ round lúc serialize/display theo policy.
- So sánh dùng giá trị full precision.

Signal tại `t` cần MA10 của cả `t` và phiên hợp lệ trước `t-1`:

```text
CROSS_UP_MA10:
  close[t] > ma10[t]
  AND close[t-1] <= ma10[t-1]

CROSS_DOWN_MA10:
  close[t] < ma10[t]
  AND close[t-1] >= ma10[t-1]

ABOVE_MA10:
  close[t] > ma10[t]
  AND NOT CROSS_UP_MA10

BELOW_MA10:
  close[t] < ma10[t]
  AND NOT CROSS_DOWN_MA10
```

Nếu `close[t] == ma10[t]`, signal là `null` với reason `ON_MA10`; không ép thành ABOVE/BELOW. Nếu chưa đủ dữ liệu để xác định, `data_status = INSUFFICIENT_DATA` và `signal = null`.

`signal_reason` (và `explanation.rule`) MUST là một trong các giá trị enum cố định sau (hoặc `null`):

| SignalReason | Ý nghĩa kỹ thuật | Signal đi kèm |
| --- | --- | --- |
| `CROSS_UP_MA10` | $Close_t > MA10_t$ và $Close_{t-1} \le MA10_{t-1}$ (vừa cắt lên) | `CROSS_UP_MA10` |
| `CROSS_DOWN_MA10` | $Close_t < MA10_t$ và $Close_{t-1} \ge MA10_{t-1}$ (vừa cắt xuống) | `CROSS_DOWN_MA10` |
| `ABOVE_MA10` | $Close_t > MA10_t$ và $Close_{t-1} > MA10_{t-1}$ (duy trì trên MA10) | `ABOVE_MA10` |
| `BELOW_MA10` | $Close_t < MA10_t$ và $Close_{t-1} < MA10_{t-1}$ (duy trì dưới MA10) | `BELOW_MA10` |
| `ON_MA10` | $Close_t == MA10_t$ (đóng cửa đúng bằng MA10) | `null` |
| `INSUFFICIENT_DATA` | Chưa đủ 10 phiên tính MA10 hoặc thiếu phiên $t-1$ | `null` |

Hệ quả cần test rõ:

- phiên hợp lệ 1–9: chưa có MA10, `data_status = INSUFFICIENT_DATA`, `signal_reason = INSUFFICIENT_DATA`;
- phiên hợp lệ thứ 10: có MA10 nhưng chưa có MA10 phiên trước để phân loại cross một cách đáng tin cậy; `signal = null`, `data_status = INSUFFICIENT_DATA`, `signal_reason = INSUFFICIENT_DATA`;
- từ phiên hợp lệ thứ 11: phân loại đủ bốn signal baseline hoặc `ON_MA10`;
- thiếu `avg_volume_20d` không làm signal MA10 mất hiệu lực, nhưng field đó vẫn là `null`.

`data_status` public dùng một trong các giá trị:

| Status | Ý nghĩa | Signal |
| --- | --- | --- |
| `VALID` | Đủ dữ liệu để phân loại signal | enum baseline hoặc `null` khi `ON_MA10` |
| `INSUFFICIENT_DATA` | Chưa đủ lịch sử để tính/phân loại | `null` |
| `NO_DATA_FOR_AS_OF_DATE` | Mã thuộc universe nhưng không có giao dịch hợp lệ ở phiên dataset | `null` |
| `INVALID_DATA` | Record mới nhất vi phạm validation nghiêm trọng | `null` |

`ON_MA10` là `signal_reason`, không phải signal hay data status. Frontend không tự suy diễn `NO_DATA_FOR_AS_OF_DATE` thành “ngừng giao dịch”; UI dùng câu chính xác “Không có dữ liệu giao dịch hợp lệ ở phiên …” vì nguyên nhân có thể là tạm ngừng, thiếu coverage hoặc lỗi provider.

## 4. Breadth

Eligible symbol tại ngày `d` là mã:

- có record hợp lệ ở `d`;
- có MA10 hợp lệ ở `d`;
- không bị loại bởi validation status nghiêm trọng.

```text
above_count = count(close > ma10)
below_count = count(close < ma10)
on_ma10_count = count(close == ma10)
eligible_count = above_count + below_count + on_ma10_count
above_pct = above_count / eligible_count * 100
below_pct = below_count / eligible_count * 100
```

Nếu `eligible_count == 0`, các phần trăm là `null`, không phải `0`.

## 5. Public file layout

```text
frontend/public/data/
├── manifest.json
├── overview.json
├── screener.json
└── symbols/
    ├── FPT.json
    └── ...
```

- Ghi ra thư mục staging, validate toàn bộ rồi mới publish/swap để tránh build nửa vời.
- Manifest được tạo cuối cùng.
- Không để raw provider response, debug dump hoặc file `.env` trong `public/`/artifact.

## 6. `manifest.json`

```json
{
  "schema_version": "1.0.0",
  "dataset_id": "9e364ba5b6d803e8",
  "as_of_date": "2026-08-21",
  "generated_at": "2026-08-21T10:00:00Z",
  "market_timezone": "Asia/Ho_Chi_Minh",
  "market_session_status": "UNKNOWN",
  "freshness": {
    "status": "UNKNOWN",
    "expected_as_of_date": "2026-08-21",
    "reason": "Dữ liệu mẫu thử nghiệm (fixture/demo), không phải dữ liệu thị trường trực tiếp."
  },
  "provider": "csv",
  "universe": "ALL",
  "files": {
    "overview": "overview.json",
    "screener": "screener.json",
    "symbols_base": "symbols/"
  },
  "quality": {
    "status": "PASS",
    "input_rows": 300,
    "accepted_rows": 300,
    "rejected_rows": 0,
    "eligible_symbols": 12,
    "warnings": []
  }
}
```

- `market_session_status`: `CLOSED_CONFIRMED` | `UNKNOWN`. Giá trị an toàn mặc định là `UNKNOWN` đối với fixture/offline data (bỏ enum DEMO để tránh contract drift; tính chất demo được nhận diện qua `provider: "csv"` và `freshness.status: "UNKNOWN"`).
- `freshness.status`: `FRESH` | `STALE` | `UNKNOWN`.
- `provider`: `csv` | `vnstock` | `company_api`. Tên public không nhạy cảm.
- `universe`: `ALL` | `VN30`. Danh sách các universe được hỗ trợ chính thức trong Phase 1.
- `quality.status`: `PASS` | `PARTIAL` | `FAIL`. Trong đó `PASS` chỉ áp dụng khi zero rejected rows và zero warnings.
- `dataset_id`: Chuỗi băm SHA-256 16 ký tự hex (`^[a-f0-9]{16}$`) tính từ canonical sorted JSON của toàn bộ input dữ liệu công khai và quality metadata. Trường `generated_at` là volatile timestamp nên được loại khỏi canonical identity payload để đảm bảo tính tất định.
- Tỷ lệ phần trăm trong `overview.metrics` và `overview.breadth_history` được làm tròn chuẩn 1 chữ số thập phân theo công thức `round(count / eligible_count * 100, 1)`. Khi `eligible_count == 0`, giá trị là `null`.

## 7. `overview.json`

```json
{
  "schema_version": "1.0.0",
  "dataset_id": "9e364ba5b6d803e8",
  "as_of_date": "2026-08-21",
  "metrics": {
    "eligible_count": 1540,
    "above_count": 910,
    "above_pct": 59.1,
    "below_count": 620,
    "below_pct": 40.3,
    "on_ma10_count": 10,
    "cross_up_count": 72,
    "cross_down_count": 41
  },
  "breadth_history": [
    {
      "trading_date": "2026-08-21",
      "eligible_count": 1540,
      "above_count": 910,
      "above_pct": 59.1
    }
  ]
}
```

`breadth_history` tối đa 60 phiên trong Phase 1 và tăng dần theo ngày.

## 8. `screener.json`

```json
{
  "schema_version": "1.0.0",
  "dataset_id": "9e364ba5b6d803e8",
  "as_of_date": "2026-08-21",
  "items": [
    {
      "symbol": "FPT",
      "exchange": "HOSE",
      "in_vn30": true,
      "last_trading_date": "2026-08-21",
      "close": 102.5,
      "ma10": 101.8,
      "distance_pct": 0.69,
      "volume": 2300000,
      "avg_volume_20d": 1800000,
      "signal": "CROSS_UP_MA10",
      "signal_reason": "CROSS_UP_MA10",
      "data_status": "VALID"
    }
  ]
}
```

Frontend giới hạn sort field bằng allow-list; không truy cập property tùy ý từ query string.

`screener.items` SHOULD chứa một row cho mỗi mã thuộc universe đã chốt, kể cả mã không eligible cho breadth. Với status khác `VALID`, các metric không xác định là `null`, `signal` là `null`, và `last_trading_date` cho biết phiên hợp lệ gần nhất nếu có. Nhờ đó UI có thể nói rõ mã thiếu dữ liệu mà breadth denominator vẫn không bị phình sai.

## 9. `symbols/{symbol}.json`

```json
{
  "schema_version": "1.0.0",
  "dataset_id": "9e364ba5b6d803e8",
  "symbol": "FPT",
  "exchange": "HOSE",
  "as_of_date": "2026-08-21",
  "latest": {
    "close": 102.5,
    "ma10": 101.8,
    "distance_pct": 0.69,
    "signal": "CROSS_UP_MA10",
    "data_status": "VALID"
  },
  "series": [
    {
      "trading_date": "2026-08-21",
      "open": 101.0,
      "high": 103.0,
      "low": 100.5,
      "close": 102.5,
      "ma10": 101.8,
      "volume": 2300000,
      "signal": "CROSS_UP_MA10"
    }
  ],
  "explanation": {
    "current_close": 102.5,
    "current_ma10": 101.8,
    "previous_close": 100.4,
    "previous_ma10": 100.8,
    "rule": "CROSS_UP_MA10"
  }
}
```

UI tự tạo câu giải thích từ structured values; pipeline không xuất HTML.

## 10. Consistency và compatibility

- Mọi file trong một deploy MUST có cùng `dataset_id`, `schema_version` và `as_of_date` phù hợp.
- Frontend từ chối major schema không hỗ trợ và hiện lỗi thân thiện.
- Minor/patch field mới phải backward-compatible; frontend bỏ qua field không biết.
- `manifest.json` mismatch với file con là lỗi dataset, không render lẫn dữ liệu hai lần build.
- Fetch JSON với path dựa trên `import.meta.env.BASE_URL`, không hard-code `/`.

## 11. Freshness policy

Frontend dùng metadata do pipeline tạo và calendar policy chung:

- `market_session_status = CLOSED_CONFIRMED`: dữ liệu đã lấy sau đóng cửa và qua validation.
- `quality.status = PARTIAL`: build thành công nhưng có cảnh báo/thiếu coverage vượt ngưỡng.
- `freshness.status = STALE`: chưa có dataset của phiên giao dịch gần nhất được kỳ vọng.
- `freshness.status = UNKNOWN`: pipeline không có trading calendar đủ tin cậy để kết luận fresh/stale.
- Weekend/ngày nghỉ không tự biến dataset phiên trước thành stale chỉ vì đã qua 24 giờ.

Frontend hiển thị status do pipeline cung cấp, không tự đoán ngày giao dịch chỉ từ đồng hồ thiết bị. Nếu chưa có trading calendar đáng tin, pipeline dùng `UNKNOWN`; UI dùng wording thận trọng “Dữ liệu gần nhất là phiên …” và không tuyên bố “mới nhất thị trường”.

## 12. Canonical dataset identity

- `dataset_id` được tính toán thông qua băm SHA-256 (lấy 16 ký tự hexa đầu tiên) của một cấu trúc JSON canonical đã chuẩn hóa và sắp xếp thứ tự:
  - `as_of_date`
  - `provider`
  - `universe`
  - `quality_status`
  - `eligible_count`
  - `quality_metadata` (`input_rows`, `accepted_rows`, `rejected_rows`, `warnings`)
  - `market_session_status`
  - `freshness_status`
  - `freshness_expected_as_of_date`
  - `calendar_version`
  - `records` (toàn bộ các dòng dữ liệu OHLCV hợp lệ, sắp xếp theo mã và ngày)
- **Quy ước về Metadata Vận hành (Operational Metadata)**:
  - Các trường mang tính thời điểm thực thi hoặc văn bản giải thích con người như `generated_at` và `freshness.reason` được coi là operational metadata và cố tình loại trừ khỏi chuỗi băm canonical để bảo đảm tính tất định (deterministic identity): hai lần build với cùng dữ liệu đầu vào và cùng `reference_time` sẽ cho ra `dataset_id` và cây thư mục byte-for-byte hoàn toàn đồng nhất.
