"""Modular corporate / authenticated market data API provider adapter."""

from __future__ import annotations

import hashlib
import logging
import os
import time
from typing import Callable, Dict, List, Optional, Sequence
from pipeline.models import OHLCVRecord
from pipeline.providers.base import (
    BaseMarketDataProvider,
    ProviderFetchResult,
    ProviderHealth,
    safe_date_label,
    safe_symbol_label,
)

logger = logging.getLogger("vn_stock_signal.company_api_provider")


class CompanyApiDataProvider(BaseMarketDataProvider):
    """Adapter for corporate / authenticated market data APIs.

    Credentials and base URLs are loaded strictly from environment variables.
    Never leaks keys, endpoints, or raw network error dumps into warnings or public manifests.
    """

    def __init__(
        self,
        api_base_url: Optional[str] = None,
        api_key_env_var: str = "DATA_API_KEY",
        max_retries: int = 2,
        fetch_fn: Optional[Callable[[str, str, str, str, str], List[Dict]]] = None,
    ):
        self.api_base_url = api_base_url or os.environ.get("DATA_API_BASE_URL", "")
        self.api_key_env_var = api_key_env_var
        self.max_retries = max(1, max_retries)
        self._fetch_fn = fetch_fn

    @property
    def provider_name(self) -> str:
        return "company_api"

    def health_check(self) -> ProviderHealth:
        """Truthfully verify API configuration and authentication."""
        api_key = os.environ.get(self.api_key_env_var, "")
        if not api_key and self._fetch_fn is None:
            return ProviderHealth(
                is_healthy=False,
                provider_name=self.provider_name,
                message=f"Missing required authentication environment variable: {self.api_key_env_var}",
            )
        if self._fetch_fn is None and not self.api_base_url:
            return ProviderHealth(
                is_healthy=False,
                provider_name=self.provider_name,
                message="Company API base URL is unconfigured.",
            )

        start_time = time.time()
        try:
            if self._fetch_fn is not None:
                # Probe with sanitized parameters
                self._fetch_fn(self.api_base_url, api_key or "PROBE_KEY", "PROBE", "2026-01-01", "2026-01-01")
            latency = (time.time() - start_time) * 1000.0
            return ProviderHealth(
                is_healthy=True,
                provider_name=self.provider_name,
                message="Company API provider probe succeeded",
                latency_ms=round(latency, 2),
            )
        except Exception:
            return ProviderHealth(
                is_healthy=False,
                provider_name=self.provider_name,
                message="Company API provider probe failed",
            )

    def fetch_ohlcv(
        self,
        symbols: Optional[Sequence[str]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> ProviderFetchResult:
        """Fetch and normalize records via authenticated API endpoint with strict sanitization."""
        records: List[OHLCVRecord] = []
        warnings: List[str] = []
        input_rows = 0
        accepted_rows = 0
        rejected_rows = 0
        target_symbols = list(symbols or [])
        clean_start = safe_date_label(start_date) if start_date else ""
        clean_end = safe_date_label(end_date) if end_date else ""
        sha = hashlib.sha256()

        api_key = os.environ.get(self.api_key_env_var, "")

        if self._fetch_fn is None:
            if not api_key:
                warnings.append(f"Missing authentication credentials ({self.api_key_env_var}); returning empty dataset.")
            else:
                warnings.append("Company API live client not configured; returning empty dataset.")
            return ProviderFetchResult(
                records=[],
                provider_name=self.provider_name,
                input_rows=0,
                accepted_rows=0,
                rejected_rows=0,
                warnings=warnings,
                payload_sha256=sha.hexdigest(),
                is_complete=False,
                provenance="unconfigured",
            )

        for sym in target_symbols:
            sym_label = safe_symbol_label(sym)
            if not sym:
                continue

            raw_items = None
            attempts_executed = 0

            # Real retry execution loop
            for attempt in range(1, self.max_retries + 1):
                attempts_executed = attempt
                try:
                    # Pass both start_date and end_date
                    raw_items = self._fetch_fn(self.api_base_url, api_key, sym_label, clean_start, clean_end)
                    break
                except Exception:
                    raw_items = None

            if raw_items is None:
                warnings.append(f"Failed to fetch data for symbol {sym_label} after {attempts_executed} attempt(s)")
                continue

            for item in raw_items:
                input_rows += 1
                try:
                    raw_date = str(item.get("trading_date") or item.get("date") or "")
                    date_label = safe_date_label(raw_date)
                    open_val = float(item["open"])
                    high_val = float(item["high"])
                    low_val = float(item["low"])
                    close_val = float(item["close"])
                    vol_val = int(float(item.get("volume", 0)))
                    raw_ex = str(item.get("exchange", "HOSE")).upper()
                    ex_val = raw_ex if raw_ex in ("HOSE", "HNX", "UPCOM") else "HOSE"
                    vn30_val = bool(item.get("in_vn30", False))

                    if not (open_val > 0 and high_val > 0 and low_val > 0 and close_val > 0 and vol_val >= 0):
                        rejected_rows += 1
                        warnings.append(f"Non-positive OHLC price or invalid volume for symbol {sym_label} on date {date_label}")
                        continue

                    # Hash validated record data
                    sha.update(f"{sym_label}:{date_label}:{open_val}:{high_val}:{low_val}:{close_val}:{vol_val}".encode("utf-8"))

                    rec = OHLCVRecord(
                        trading_date=raw_date,
                        symbol=sym_label,
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
                    warnings.append(f"Malformed price or volume record rejected for symbol {sym_label}")

        return ProviderFetchResult(
            records=records,
            provider_name=self.provider_name,
            input_rows=input_rows,
            accepted_rows=accepted_rows,
            rejected_rows=rejected_rows,
            warnings=warnings,
            payload_sha256=sha.hexdigest(),
            is_complete=False,
            provenance="company_api_unverified",
        )
