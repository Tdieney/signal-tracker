export const APP_VERSION = "1.0.0";
export const SUPPORTED_SCHEMA_VERSION = "1.0.0";

export const FINANCIAL_DISCLAIMER =
  "Tín hiệu chỉ phản ánh quy tắc kỹ thuật trên dữ liệu cuối ngày, không phải khuyến nghị mua hoặc bán. Dữ liệu có thể chậm, thiếu hoặc sai; hãy kiểm tra lại với nguồn được cấp phép trước khi ra quyết định.";

export const DISCLAIMER_FOOTER =
  "Tín hiệu chỉ phản ánh quy tắc kỹ thuật trên dữ liệu cuối ngày, không phải khuyến nghị mua hoặc bán. Dữ liệu có thể chậm, thiếu hoặc sai; hãy kiểm tra lại với nguồn được cấp phép trước khi ra quyết định. Không cung cấp đặt lệnh, không lưu trữ tài khoản, không cam kết lợi nhuận.";

export const SIGNAL_LABELS: Record<string, string> = {
  ABOVE_MA10: "Trên MA10",
  BELOW_MA10: "Dưới MA10",
  CROSS_UP_MA10: "Vừa cắt lên MA10",
  CROSS_DOWN_MA10: "Vừa cắt xuống MA10",
};

export const DATA_STATUS_LABELS: Record<string, string> = {
  VALID: "Đủ dữ liệu",
  INSUFFICIENT_DATA: "Chưa đủ dữ liệu",
  NO_DATA_FOR_AS_OF_DATE: "Không có GD phiên này",
  INVALID_DATA: "Dữ liệu không hợp lệ",
};

export const FRESHNESS_LABELS: Record<string, string> = {
  FRESH: "Dữ liệu mới",
  STALE: "Dữ liệu có thể đã cũ",
  UNKNOWN: "Chưa rõ độ mới",
};

export const QUALITY_LABELS: Record<string, string> = {
  PASS: "Đạt chuẩn",
  PARTIAL: "Một phần đạt",
  FAIL: "Lỗi kiểm tra",
};

export const EXCHANGES = ["ALL", "HOSE", "HNX", "UPCOM"] as const;
export const UNIVERSES = ["ALL", "VN30"] as const;
export const SIGNALS = ["ALL", "CROSS_UP_MA10", "CROSS_DOWN_MA10", "ABOVE_MA10", "BELOW_MA10"] as const;

export interface DefaultFiltersType {
  exchange: string;
  signal: string;
  universe: string;
  query: string;
  distanceMin: string;
  distanceMax: string;
  minAvgVolume20d: string;
  sort: string;
  direction: 'asc' | 'desc';
  page: number;
  pageSize: number;
}

export const DEFAULT_FILTERS: DefaultFiltersType = {
  exchange: "ALL",
  signal: "ALL",
  universe: "ALL",
  query: "",
  distanceMin: "",
  distanceMax: "",
  minAvgVolume20d: "",
  sort: "distance_pct",
  direction: "desc",
  page: 1,
  pageSize: 20,
};
