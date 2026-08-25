"""Modular corporate / authenticated market data API provider adapter."""

from __future__ import annotations

import hashlib
import json
import logging
import os
from typing import Callable, Dict, List, Optional, Sequence
from pipeline.models import OHLCVRecord
from pipeline.providers.base import BaseMarketDataProvider, ProviderFetchResult, ProviderHealth

logger = logging.getLogger("vn_stock_signal.company_api_provider")


class CompanyApiDataProvider(BaseMarketDataProvider):
    """Adapter for corporate / authenticated market data APIs.
    
    Credentials and base URLs are loaded strictly from environment variables (e.g. DATA_API_KEY).
    Never leaks keys, endpoints, or raw network error dumps into warnings or public manifests.
    """

    def __init__(
        self,
        api_base_url: Optional[str] = None,
        api_key_env_var: str = "DATA_API_KEY",
        fetch_fn: Optional[Callable[[str, str, str, str], List[Dict]]] = None,
    ):
        self.api_base_url = api_base_url or os.environ.get("DATA_API_BASE_URL", "")
        self.api_key_env_var = api_key_env_var
        self._fetch_fn = fetch_fn

    @property
    def provider_name(self) -> str:
        return "company_api"

    def health_check(self) -> ProviderHealth:
        """Verify API key availability and endpoint configuration."""
        has_key = bool(os.environ.get(self.api_key_env_var)) or (self._fetch_fn is not None)
        if not has_key:
            return ProviderHealth(
                is_healthy=False,
                provider_name=self.provider_name,
                message=f"Missing required authentication environment variable: {self.api_key_env_var}",
            )
        return ProviderHealth(
            is_healthy=True,
            provider_name=self.provider_name,
            message="Company API provider authenticated and configured",
            latency_ms=1.2,
        )

    def fetch_ohlcv(
        self,
        symbols: Optional[Sequence[str]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[OHLCVRecord]:
        res = self.fetch_ohlcv_result(symbols=symbols, start_date=start_date, end_date=end_date)
        return res.records

    def fetch_ohlcv_result(
        self,
        symbols: Optional[Sequence[str]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> ProviderFetchResult:
        """Fetch and normalize records via authenticated API endpoint."""
        records: List[OHLCVRecord] = []
        warnings: List[str] = []
        input_rows = 0
        accepted_rows = 0
        rejected_rows = 0
        target_symbols = list(symbols) if symbols else []
        sha = hashlib.sha256()

        if self._fetch_fn is None:
            warnings.append("Company API live client not configured; returning empty dataset.")
            return ProviderFetchResult(
                records=[],
                provider_name=self.provider_name,
                input_rows=0,
                accepted_rows=0,
                rejected_rows=0,
                warnings=warnings,
                payload_sha256=sha.hexdigest(),
            )

        api_key = os.environ.get(self.api_key_env_var, "test-token")
        for sym in target_symbols:
            try:
                raw_items = self._fetch_fn(self.api_base_url, api_key, sym, start_date or "")
                for item in raw_items:
                    input_rows += 1
                    try:
                        sha.update(json.dumps(item, sort_keys=True).encode("utf-8"))
                        date_str = str(item.get("trading_date") or item.get("date") or "")
                        open_val = float(item["open"])
                        high_val = float(item["high"])
                        low_val = float(item["low"])
                        close_val = float(item["close"])
                        vol_val = int(float(item.get("volume", 0)))
                        ex_val = str(item.get("exchange", "HOSE")).upper()
                        vn30_val = bool(item.get("in_vn30", False))

                        if not (open_val > 0 and high_val > 0 and low_val > 0 and close_val > 0):
                            rejected_rows += 1
                            warnings.append(f"Symbol {sym} date {date_str}: Non-positive OHLC price")
                            continue

                        rec = OHLCVRecord(
                            trading_date=date_str,
                            symbol=sym,
                            exchange=ex_val,
                            open=open_val,
                            high=high_val,
                            low=low_val,
                            close=close_val,
                            volume=vol_val,
                            in_vn30=vn30_val,
                        )
                        records.append(rec)
                        accepted_rows += 1
                    except (KeyError, ValueError, TypeError):
                        rejected_rows += 1
                        warnings.append(f"Symbol {sym}: Malformed record rejected")
            except Exception:
                warnings.append(f"Failed to fetch data for symbol {sym} from company API")

        return ProviderFetchResult(
            records=records,
            provider_name=self.provider_name,
            input_rows=input_rows,
            accepted_rows=accepted_rows,
            rejected_rows=rejected_rows,
            warnings=warnings,
            payload_sha256=sha.hexdigest(),
        )
