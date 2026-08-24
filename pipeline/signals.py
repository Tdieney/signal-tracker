"""Signal classification and market breadth module for VN Stock Signal pipeline."""

from __future__ import annotations

from typing import Dict, List, Optional
from pipeline.models import (
    BreadthHistoryPoint,
    BreadthMetric,
    DataStatus,
    IndicatorRecord,
    SignalReason,
    SignalType,
)


def classify_signals_for_symbol(records: List[IndicatorRecord]) -> List[IndicatorRecord]:
    """Classify signals for each session of a symbol according to docs/04-data-contracts.md.
    
    Rules:
    - Sessions 1..9: no MA10 -> data_status = INSUFFICIENT_DATA, signal = None.
    - Session 10: has MA10, but previous session (9) has no MA10 -> data_status = INSUFFICIENT_DATA, signal = None.
    - Sessions 11+: has MA10 and previous MA10 -> data_status = VALID:
        - CROSS_UP_MA10: close[t] > ma10[t] and close[t-1] <= ma10[t-1]
        - CROSS_DOWN_MA10: close[t] < ma10[t] and close[t-1] >= ma10[t-1]
        - ABOVE_MA10: close[t] > ma10[t] and not CROSS_UP_MA10
        - BELOW_MA10: close[t] < ma10[t] and not CROSS_DOWN_MA10
        - Equality close[t] == ma10[t]: signal = None, signal_reason = ON_MA10
    """
    for i, rec in enumerate(records):
        # Check if MA10 exists
        if rec.ma10 is None:
            rec.data_status = DataStatus.INSUFFICIENT_DATA
            rec.signal = None
            rec.signal_reason = SignalReason.INSUFFICIENT_DATA.value
            continue

        # Check if previous MA10 exists for cross classification
        prev_rec = records[i - 1] if i > 0 else None
        if prev_rec is None or prev_rec.ma10 is None or prev_rec.close is None:
            rec.data_status = DataStatus.INSUFFICIENT_DATA
            rec.signal = None
            rec.signal_reason = SignalReason.INSUFFICIENT_DATA.value
            continue

        # Session 11+: both current and previous have valid MA10 and close
        rec.data_status = DataStatus.VALID
        cur_close = rec.close
        cur_ma10 = rec.ma10
        prev_close = prev_rec.close
        prev_ma10 = prev_rec.ma10

        if cur_close > cur_ma10:
            if prev_close <= prev_ma10:
                rec.signal = SignalType.CROSS_UP_MA10
                rec.signal_reason = SignalReason.CROSS_UP_MA10.value
            else:
                rec.signal = SignalType.ABOVE_MA10
                rec.signal_reason = SignalReason.ABOVE_MA10.value
        elif cur_close < cur_ma10:
            if prev_close >= prev_ma10:
                rec.signal = SignalType.CROSS_DOWN_MA10
                rec.signal_reason = SignalReason.CROSS_DOWN_MA10.value
            else:
                rec.signal = SignalType.BELOW_MA10
                rec.signal_reason = SignalReason.BELOW_MA10.value
        else:
            # cur_close == cur_ma10
            rec.signal = None
            rec.signal_reason = SignalReason.ON_MA10.value

    return records


def calculate_market_breadth(
    indicators_by_symbol: Dict[str, List[IndicatorRecord]],
    as_of_date: str,
    max_history_sessions: int = 60
) -> tuple[BreadthMetric, List[BreadthHistoryPoint]]:
    """Calculate market breadth metrics as of the target date and historical points.
    
    Eligible symbol at date d:
    - has valid record at d;
    - has valid MA10 at d.
    """
    # Collect all unique trading dates across all symbols up to as_of_date
    all_dates_set = set()
    records_by_date: Dict[str, List[IndicatorRecord]] = {}

    for sym, records in indicators_by_symbol.items():
        for r in records:
            if r.trading_date <= as_of_date:
                all_dates_set.add(r.trading_date)
                records_by_date.setdefault(r.trading_date, []).append(r)

    sorted_dates = sorted(all_dates_set)

    # Calculate breadth for each date
    history_points: List[BreadthHistoryPoint] = []
    as_of_metric: Optional[BreadthMetric] = None

    for d in sorted_dates:
        day_records = records_by_date.get(d, [])
        # Filter eligible records: must have valid ma10 and valid close
        eligible = [r for r in day_records if r.ma10 is not None and r.close is not None and r.data_status != DataStatus.INVALID_DATA]
        
        above = [r for r in eligible if r.close > r.ma10]
        below = [r for r in eligible if r.close < r.ma10]
        on_ma10 = [r for r in eligible if r.close == r.ma10]
        cross_up = [r for r in day_records if r.signal == SignalType.CROSS_UP_MA10]
        cross_down = [r for r in day_records if r.signal == SignalType.CROSS_DOWN_MA10]

        eligible_cnt = len(eligible)
        above_cnt = len(above)
        below_cnt = len(below)
        on_cnt = len(on_ma10)
        cross_up_cnt = len(cross_up)
        cross_down_cnt = len(cross_down)

        above_pct = (above_cnt / eligible_cnt * 100.0) if eligible_cnt > 0 else None
        below_pct = (below_cnt / eligible_cnt * 100.0) if eligible_cnt > 0 else None

        metric = BreadthMetric(
            eligible_count=eligible_cnt,
            above_count=above_cnt,
            above_pct=round(above_pct, 1) if above_pct is not None else None,
            below_count=below_cnt,
            below_pct=round(below_pct, 1) if below_pct is not None else None,
            on_ma10_count=on_cnt,
            cross_up_count=cross_up_cnt,
            cross_down_count=cross_down_cnt,
        )

        history_points.append(
            BreadthHistoryPoint(
                trading_date=d,
                eligible_count=eligible_cnt,
                above_count=above_cnt,
                above_pct=round(above_pct, 1) if above_pct is not None else None,
            )
        )

        if d == as_of_date:
            as_of_metric = metric

    if as_of_metric is None:
        # If no records exist on as_of_date
        as_of_metric = BreadthMetric(
            eligible_count=0,
            above_count=0,
            above_pct=None,
            below_count=0,
            below_pct=None,
            on_ma10_count=0,
            cross_up_count=0,
            cross_down_count=0,
        )

    # Cap breadth history to latest max_history_sessions
    recent_history = history_points[-max_history_sessions:] if history_points else []

    return as_of_metric, recent_history
