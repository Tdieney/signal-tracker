"""Quarantined client adapter for Vietnam equity EOD quotes (Pending licence verification)."""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from pipeline.models import VN30_SYMBOLS

logger = logging.getLogger("vn_stock_signal.vnstock_client")

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


class VnstockMarketClient:
    """Quarantined HTTP client adapter for fetching daily OHLCV bars.

    STATUS: QUARANTINED / NOT APPROVED FOR PRODUCTION LIVE USE
    NOTE: Access to external third-party market endpoints is strictly disabled in production
    pipelines pending formal licence verification and explicit redistribution authorization.
    """

    def __init__(
        self,
        rate_limit_delay_seconds: float = 0.5,
        max_retries: int = 3,
        timeout_seconds: float = 10.0,
        opener: Optional[urllib.request.OpenerDirector] = None,
    ):
        self.rate_limit_delay_seconds = max(0.0, rate_limit_delay_seconds)
        self.max_retries = max(1, max_retries)
        self.timeout_seconds = max(1.0, timeout_seconds)
        self._opener = opener or urllib.request.build_opener()

    def probe(self, symbol: str = "FPT") -> Tuple[bool, str, Optional[float]]:
        """Perform a lightweight liveness probe."""
        start_t = time.time()
        try:
            bars = self.fetch_daily_bars(symbol, lookback_days=5)
            latency_ms = (time.time() - start_t) * 1000.0
            if bars:
                return True, "Market data endpoint probe succeeded", round(latency_ms, 2)
            return False, "Market data endpoint probe returned empty result", round(latency_ms, 2)
        except Exception:
            latency_ms = (time.time() - start_t) * 1000.0
            return False, "Market data endpoint probe failed", round(latency_ms, 2)

    def fetch_daily_bars(
        self,
        symbol: str,
        lookback_days: int = 180,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch daily OHLCV bars for a given symbol with rate-limiting and retries.

        Preserves raw row accounting: all upstream records (including malformed ones)
        are returned to the provider for strict input/accepted/rejected accounting.
        """
        clean_sym = symbol.strip().upper()
        if not clean_sym:
            return []

        to_ts = int(time.time())
        from_ts = to_ts - (lookback_days * 86400)

        url = (
            f"https://services.entrade.com.vn/chart-api/v2/ohlcs/stock"
            f"?from={from_ts}&to={to_ts}&symbol={clean_sym}&resolution=1D"
        )
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
        }

        raw_payload = None
        for attempt in range(1, self.max_retries + 1):
            if self.rate_limit_delay_seconds > 0:
                time.sleep(self.rate_limit_delay_seconds)

            req = urllib.request.Request(url, headers=headers)
            try:
                with self._opener.open(req, timeout=self.timeout_seconds) as resp:
                    resp_bytes = resp.read()
                    raw_payload = json.loads(resp_bytes.decode("utf-8"))
                break
            except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
                if attempt < self.max_retries:
                    backoff_delay = 0.5 * (2 ** (attempt - 1))
                    time.sleep(backoff_delay)
                else:
                    raw_payload = None

        if not raw_payload or not isinstance(raw_payload, dict):
            return []

        t_list = raw_payload.get("t") or []
        o_list = raw_payload.get("o") or []
        h_list = raw_payload.get("h") or []
        l_list = raw_payload.get("l") or []
        c_list = raw_payload.get("c") or []
        v_list = raw_payload.get("v") or []

        if not isinstance(t_list, list):
            t_list = []
        if not isinstance(o_list, list):
            o_list = []
        if not isinstance(h_list, list):
            h_list = []
        if not isinstance(l_list, list):
            l_list = []
        if not isinstance(c_list, list):
            c_list = []
        if not isinstance(v_list, list):
            v_list = []

        total_raw_rows = max(len(t_list), len(o_list), len(h_list), len(l_list), len(c_list), len(v_list))
        if total_raw_rows == 0:
            return []

        in_vn30 = clean_sym in VN30_SYMBOLS
        results: List[Dict[str, Any]] = []

        for i in range(total_raw_rows):
            # Check array index bounds for each field
            has_all_fields = (
                i < len(t_list)
                and i < len(o_list)
                and i < len(h_list)
                and i < len(l_list)
                and i < len(c_list)
                and i < len(v_list)
            )

            if not has_all_fields:
                # Array length mismatch: return malformed item for strict rejection accounting
                results.append({
                    "trading_date": None,
                    "symbol": clean_sym,
                    "exchange": "HOSE",
                    "open": None,
                    "high": None,
                    "low": None,
                    "close": None,
                    "volume": None,
                    "in_vn30": in_vn30,
                    "_malformed_reason": "Array length mismatch in upstream payload",
                })
                continue

            try:
                ts = int(t_list[i])
                dt_str = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")

                if start_date and dt_str < start_date:
                    continue
                if end_date and dt_str > end_date:
                    continue

                open_p = float(o_list[i])
                high_p = float(h_list[i])
                low_p = float(l_list[i])
                close_p = float(c_list[i])
                vol = int(float(v_list[i]))

                results.append({
                    "trading_date": dt_str,
                    "symbol": clean_sym,
                    "exchange": "HOSE",
                    "open": open_p,
                    "high": high_p,
                    "low": low_p,
                    "close": close_p,
                    "volume": vol,
                    "in_vn30": in_vn30,
                })
            except (ValueError, TypeError):
                results.append({
                    "trading_date": None,
                    "symbol": clean_sym,
                    "exchange": "HOSE",
                    "open": None,
                    "high": None,
                    "low": None,
                    "close": None,
                    "volume": None,
                    "in_vn30": in_vn30,
                    "_malformed_reason": "Type conversion error in raw record",
                })

        return results
