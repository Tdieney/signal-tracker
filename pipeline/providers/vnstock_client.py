"""Quarantined payload parser and adapter for Vietnam equity EOD quotes (Pending licence verification)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

from pipeline.models import VN30_SYMBOLS

logger = logging.getLogger("vn_stock_signal.vnstock_client")


class VnstockMarketClient:
    """Quarantined market client / payload parser.

    STATUS: QUARANTINED / NETWORK TRANSPORT REMOVED / DISABLED FOR LIVE EXECUTION
    NOTE: All external network transport and hardcoded endpoints have been completely removed.
    This class functions strictly as an offline raw payload parser for test fixtures and mocks.
    """

    def __init__(
        self,
        rate_limit_delay_seconds: float = 0.0,
        max_retries: int = 1,
        timeout_seconds: float = 1.0,
        fixture_fetcher: Optional[Callable[[str], Optional[Dict[str, Any]]]] = None,
    ):
        self.rate_limit_delay_seconds = max(0.0, rate_limit_delay_seconds)
        self.max_retries = max(1, max_retries)
        self.timeout_seconds = max(1.0, timeout_seconds)
        self._fixture_fetcher = fixture_fetcher

    def probe(self, symbol: str = "FPT") -> Tuple[bool, str, Optional[float]]:
        """Perform a quarantined probe without network execution."""
        if self._fixture_fetcher is not None:
            try:
                res = self._fixture_fetcher(symbol)
                if res is not None:
                    return True, "Offline fixture probe succeeded", 0.0
                return False, "Offline fixture probe returned empty", 0.0
            except Exception:
                return False, "Offline fixture probe failed", 0.0
        return False, "Market data endpoint probe disabled (quarantined / no network transport)", None

    def fetch_daily_bars(
        self,
        symbol: str,
        lookback_days: int = 180,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Parse daily OHLCV bars from injected fixture or fail closed if live network is requested.

        Preserves 100% raw row accounting: every single raw element in upstream payload is parsed
        and returned to the provider for strict input/accepted/rejected accounting.
        """
        clean_sym = symbol.strip().upper()
        if not clean_sym:
            return []

        if self._fixture_fetcher is None:
            # Network transport is completely removed
            raise RuntimeError(
                "Network transport disabled: external market endpoint access is quarantined."
            )

        raw_payload = self._fixture_fetcher(clean_sym)
        return self.parse_raw_payload(raw_payload, clean_sym, start_date=start_date, end_date=end_date)

    @classmethod
    def parse_raw_payload(
        cls,
        raw_payload: Optional[Dict[str, Any]],
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Pure parser for upstream raw dictionary payload format {"t": [...], "o": [...], ...}.

        Returns a standardized dictionary for EVERY single raw row index, including:
        - valid rows (with trading_date, open, high, low, close, volume)
        - malformed rows (with _malformed_reason)
        - date-tagged rows (so provider can count input_rows and apply date-filter accounting)
        """
        clean_sym = symbol.strip().upper()
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
            has_all_fields = (
                i < len(t_list)
                and i < len(o_list)
                and i < len(h_list)
                and i < len(l_list)
                and i < len(c_list)
                and i < len(v_list)
            )

            if not has_all_fields:
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
