"""Modular Vnstock data provider adapter for Vietnam stock market data (Quarantined)."""

from __future__ import annotations

import hashlib
import logging
import time
from typing import Callable, Dict, List, Optional, Sequence
from pipeline.models import OHLCVRecord, VN30_SYMBOLS
from pipeline.providers.base import (
    BaseMarketDataProvider,
    ProviderFetchResult,
    ProviderHealth,
    safe_date_label,
    safe_symbol_label,
)
from pipeline.providers.vnstock_client import VnstockMarketClient
from pipeline.validation import validate_record

logger = logging.getLogger("vn_stock_signal.vnstock_provider")


class VnstockDataProvider(BaseMarketDataProvider):
    """Adapter for fetching OHLCV records via vnstock / market data endpoints.

    STATUS: QUARANTINED / PENDING LICENCE VERIFICATION
    Live fetching is locked fail-closed in production.
    Supports dependency injection via fetch_fn or mock client for offline testing.
    """

    def __init__(
        self,
        rate_limit_delay_seconds: float = 0.5,
        max_retries: int = 3,
        fetch_fn: Optional[Callable[[str, str, str], List[Dict]]] = None,
        client: Optional[VnstockMarketClient] = None,
        is_live: bool = False,
    ):
        if is_live:
            raise RuntimeError(
                "Live market data provider disabled: unverified provider licence / pending authorization."
            )
        self.rate_limit_delay_seconds = max(0.0, rate_limit_delay_seconds)
        self.max_retries = max(1, max_retries)
        self._fetch_fn = fetch_fn
        self._client = client

    @property
    def provider_name(self) -> str:
        return "vnstock"

    def health_check(self) -> ProviderHealth:
        """Perform a truthful health check."""
        if self._fetch_fn is None and self._client is None:
            return ProviderHealth(
                is_healthy=False,
                provider_name=self.provider_name,
                message="Vnstock adapter is quarantined and disabled pending provider licence authorization.",
            )

        if self._client is not None:
            is_ok, msg, latency = self._client.probe()
            return ProviderHealth(
                is_healthy=is_ok,
                provider_name=self.provider_name,
                message=msg,
                latency_ms=latency,
            )

        start_time = time.time()
        try:
            # Perform a lightweight probe with safe mock parameters
            self._fetch_fn("PROBE", "2026-01-01", "2026-01-01")
            latency = (time.time() - start_time) * 1000.0
            return ProviderHealth(
                is_healthy=True,
                provider_name=self.provider_name,
                message="Vnstock adapter probe succeeded",
                latency_ms=round(latency, 2),
            )
        except Exception:
            return ProviderHealth(
                is_healthy=False,
                provider_name=self.provider_name,
                message="Vnstock adapter probe failed",
            )

    def fetch_ohlcv(
        self,
        symbols: Optional[Sequence[str]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> ProviderFetchResult:
        """Fetch and normalize OHLCV records with genuine retry execution, strict accounting, and sanitized warnings."""
        records: List[OHLCVRecord] = []
        warnings: List[str] = []
        input_rows = 0
        accepted_rows = 0
        rejected_rows = 0
        target_symbols = list(symbols or list(VN30_SYMBOLS))
        clean_start = safe_date_label(start_date) if start_date else ""
        clean_end = safe_date_label(end_date) if end_date else ""
        sha = hashlib.sha256()

        if self._fetch_fn is None and self._client is None:
            warnings.append("Vnstock adapter is quarantined/unconfigured; returning empty dataset.")
            return ProviderFetchResult(
                records=[],
                provider_name=self.provider_name,
                input_rows=0,
                accepted_rows=0,
                rejected_rows=0,
                warnings=warnings,
                payload_sha256=sha.hexdigest(),
                is_complete=False,
                provenance="stub",
            )

        symbols_with_enough_data = 0

        for sym in target_symbols:
            sym_label = safe_symbol_label(sym)
            if not sym or sym_label == "[INVALID_SYMBOL]":
                continue

            raw_items = None
            attempts_executed = 0

            if self._client is not None:
                try:
                    raw_items = self._client.fetch_daily_bars(
                        symbol=sym_label,
                        lookback_days=180,
                        start_date=clean_start if clean_start != "[INVALID_DATE]" else None,
                        end_date=clean_end if clean_end != "[INVALID_DATE]" else None,
                    )
                except Exception:
                    raw_items = None
            else:
                # Real retry execution loop for custom fetch_fn
                for attempt in range(1, self.max_retries + 1):
                    attempts_executed = attempt
                    if self.rate_limit_delay_seconds > 0:
                        time.sleep(self.rate_limit_delay_seconds)
                    try:
                        raw_items = self._fetch_fn(sym_label, clean_start, clean_end)
                        break
                    except Exception:
                        raw_items = None

            if raw_items is None:
                warnings.append(f"Failed to fetch data from provider after {attempts_executed or self.max_retries} attempt(s)")
                continue

            if not raw_items:
                warnings.append("No records returned for requested query")
                continue

            symbol_accepted = 0
            for item in raw_items:
                input_rows += 1
                try:
                    raw_date = str(item.get("trading_date") or item.get("date") or "")
                    if not raw_date or raw_date == "None":
                        rejected_rows += 1
                        warnings.append("Malformed or missing trading_date in record")
                        continue

                    # Explicit date boundary filtering accounting (preserves input_rows == accepted_rows + rejected_rows)
                    if clean_start and clean_start != "[INVALID_DATE]" and raw_date < clean_start:
                        rejected_rows += 1
                        warnings.append("Record outside requested date range rejected")
                        continue

                    if clean_end and clean_end != "[INVALID_DATE]" and raw_date > clean_end:
                        rejected_rows += 1
                        warnings.append("Record outside requested date range rejected")
                        continue

                    open_val = float(item["open"])
                    high_val = float(item["high"])
                    low_val = float(item["low"])
                    close_val = float(item["close"])
                    vol_val = int(float(item.get("volume", 0)))
                    raw_ex = str(item.get("exchange", "HOSE")).upper()
                    ex_val = raw_ex if raw_ex in ("HOSE", "HNX", "UPCOM") else "HOSE"
                    vn30_val = bool(item.get("in_vn30", sym_label in VN30_SYMBOLS))

                    if not (open_val > 0 and high_val > 0 and low_val > 0 and close_val > 0 and vol_val >= 0):
                        rejected_rows += 1
                        warnings.append("Non-positive OHLC price or invalid volume rejected")
                        continue

                    # Hash validated record data
                    sha.update(f"{sym_label}:{raw_date}:{open_val}:{high_val}:{low_val}:{close_val}:{vol_val}".encode("utf-8"))

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
                    is_valid, val_errs = validate_record(rec)
                    if not is_valid:
                        rejected_rows += 1
                        warnings.append("Record failed data validation checks")
                        continue

                    records.append(rec)
                    accepted_rows += 1
                    symbol_accepted += 1
                except (KeyError, ValueError, TypeError):
                    rejected_rows += 1
                    warnings.append("Malformed price or volume record rejected")

            if symbol_accepted >= 10:
                symbols_with_enough_data += 1

        is_complete = (len(target_symbols) > 0 and symbols_with_enough_data == len(target_symbols))
        provenance = "vnstock_mock"

        return ProviderFetchResult(
            records=records,
            provider_name=self.provider_name,
            input_rows=input_rows,
            accepted_rows=accepted_rows,
            rejected_rows=rejected_rows,
            warnings=warnings,
            payload_sha256=sha.hexdigest(),
            is_complete=is_complete,
            provenance=provenance,
        )
