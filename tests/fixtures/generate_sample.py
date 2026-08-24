"""Generate deterministic test fixtures for VN Stock Signal tests."""

import csv
import os

os.makedirs("tests/fixtures", exist_ok=True)

# 1. Generate realistic sample_ohlcv.csv (25 sessions for 12 symbols across HOSE, HNX, UPCOM)
symbols_config = [
    # (symbol, exchange, in_vn30, start_price, trend, cross_pattern)
    ("FPT", "HOSE", True, 100.0, "up_cross_at_end"),    # cross up on last day
    ("VNM", "HOSE", True, 70.0, "down_cross_at_end"),   # cross down on last day
    ("HPG", "HOSE", True, 28.0, "above"),               # above MA10
    ("VCB", "HOSE", True, 90.0, "below"),               # below MA10
    ("SSI", "HOSE", True, 32.0, "on_ma10_at_end"),      # exact equality on last day
    ("MWG", "HOSE", True, 55.0, "above"),
    ("VIC", "HOSE", True, 45.0, "below"),
    ("TCB", "HOSE", True, 24.0, "cross_up_at_end"),
    ("SHS", "HNX", False, 18.0, "above"),
    ("PVS", "HNX", False, 38.0, "below"),
    ("BSR", "UPCOM", False, 22.0, "above"),
    ("OIL", "UPCOM", False, 14.0, "below"),
]

dates = [
    "2026-07-20", "2026-07-21", "2026-07-22", "2026-07-23", "2026-07-24",
    "2026-07-27", "2026-07-28", "2026-07-29", "2026-07-30", "2026-07-31",
    "2026-08-03", "2026-08-04", "2026-08-05", "2026-08-06", "2026-08-07",
    "2026-08-10", "2026-08-11", "2026-08-12", "2026-08-13", "2026-08-14",
    "2026-08-17", "2026-08-18", "2026-08-19", "2026-08-20", "2026-08-21",
]

fieldnames = ["trading_date", "symbol", "exchange", "open", "high", "low", "close", "adjusted_close", "volume", "trading_value", "in_vn30"]

rows = []
for sym, ex, in_vn30, base_p, behavior, *rest in symbols_config:
    cur_p = base_p
    for i, d in enumerate(dates):
        # Determine day's close
        if i == len(dates) - 1: # Last day 2026-08-21
            if "up_cross" in behavior or "cross_up" in behavior:
                cur_p = cur_p * 1.05  # Jump up
            elif "down_cross" in behavior:
                cur_p = cur_p * 0.95  # Jump down
            elif behavior == "on_ma10_at_end":
                # We will adjust after calculating ma10
                cur_p = cur_p
            elif behavior == "above":
                cur_p = cur_p * 1.01
            elif behavior == "below":
                cur_p = cur_p * 0.99
        elif i == len(dates) - 2: # Day before last 2026-08-20
            if "up_cross" in behavior or "cross_up" in behavior:
                cur_p = cur_p * 0.98  # Below MA10 yesterday
            elif "down_cross" in behavior:
                cur_p = cur_p * 1.02  # Above MA10 yesterday
            else:
                cur_p = cur_p * (1.002 if behavior == "above" else 0.998)
        else:
            # Steady movement
            step = 0.003 if behavior in ("above", "up_cross_at_end", "cross_up_at_end") else -0.003
            cur_p = cur_p * (1.0 + step)

        open_p = round(cur_p * 0.995, 2)
        close_p = round(cur_p, 2)
        high_p = round(max(open_p, close_p) * 1.01, 2)
        low_p = round(min(open_p, close_p) * 0.99, 2)
        vol = 1000000 + (i * 20000)

        rows.append({
            "trading_date": d,
            "symbol": sym,
            "exchange": ex,
            "open": open_p,
            "high": high_p,
            "low": low_p,
            "close": close_p,
            "adjusted_close": close_p,
            "volume": vol,
            "trading_value": round(close_p * vol, 2),
            "in_vn30": "true" if in_vn30 else "false",
        })

with open("tests/fixtures/sample_ohlcv.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

print("Generated tests/fixtures/sample_ohlcv.csv")
