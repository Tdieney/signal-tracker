"""Tests for signal classification and market breadth."""

import unittest
from pipeline.indicators import calculate_symbol_indicators
from pipeline.models import DataStatus, OHLCVRecord, SignalType
from pipeline.signals import calculate_market_breadth, classify_signals_for_symbol


class TestSignals(unittest.TestCase):

    def test_signal_classification_transitions(self):
        # 12 sessions
        # 0..8 (1..9): insufficient
        # 9 (10th): ma10 exists, but signal is None & INSUFFICIENT_DATA
        # 10 (11th): CROSS_UP_MA10
        # 11 (12th): ABOVE_MA10
        prices = [10, 10, 10, 10, 10, 10, 10, 10, 10, 9, 12, 13]
        records = [
            OHLCVRecord(
                trading_date=f"2026-08-{i+1:02d}",
                symbol="CROSS",
                exchange="HOSE",
                open=p,
                high=p + 1,
                low=p - 1,
                close=p,
                volume=1000,
            )
            for i, p in enumerate(prices)
        ]

        ind_recs = calculate_symbol_indicators(records)
        classified = classify_signals_for_symbol(ind_recs)

        # 1..9: INSUFFICIENT_DATA
        for i in range(9):
            self.assertEqual(classified[i].data_status, DataStatus.INSUFFICIENT_DATA)
            self.assertIsNone(classified[i].signal)

        # 10th: INSUFFICIENT_DATA because previous MA10 was None
        self.assertEqual(classified[9].data_status, DataStatus.INSUFFICIENT_DATA)
        self.assertIsNone(classified[9].signal)

        # 11th (index 10):
        # Session 9 MA10 = (10*9 + 9)/10 = 9.9. Close = 9 <= 9.9
        # Session 10 MA10 = (10*8 + 9 + 12)/10 = 10.1. Close = 12 > 10.1
        # Previous close (9) <= previous MA10 (9.9) AND current close (12) > current MA10 (10.1) -> CROSS_UP_MA10
        self.assertEqual(classified[10].data_status, DataStatus.VALID)
        self.assertEqual(classified[10].signal, SignalType.CROSS_UP_MA10)

        # 12th (index 11):
        # Session 11 MA10 = (10*7 + 9 + 12 + 13)/10 = 10.4. Close = 13 > 10.4
        # Previous close (12) > previous MA10 (10.1) -> ABOVE_MA10
        self.assertEqual(classified[11].data_status, DataStatus.VALID)
        self.assertEqual(classified[11].signal, SignalType.ABOVE_MA10)

    def test_equality_on_ma10(self):
        # Prices constant 10 for 12 days
        prices = [10.0] * 12
        records = [
            OHLCVRecord(
                trading_date=f"2026-08-{i+1:02d}",
                symbol="EQ",
                exchange="HOSE",
                open=p,
                high=p + 1,
                low=p - 1,
                close=p,
                volume=1000,
            )
            for i, p in enumerate(prices)
        ]
        ind_recs = calculate_symbol_indicators(records)
        classified = classify_signals_for_symbol(ind_recs)

        # On 11th and 12th session, close == 10, MA10 == 10 -> signal is None, signal_reason == 'ON_MA10'
        self.assertEqual(classified[10].data_status, DataStatus.VALID)
        self.assertIsNone(classified[10].signal)
        self.assertEqual(classified[10].signal_reason, "ON_MA10")

    def test_breadth_invariants(self):
        # Create symbols dictionary
        # Sym A: Above MA10
        # Sym B: Below MA10
        # Sym C: On MA10
        # Sym D: Insufficient data (only 5 sessions)
        sym_a = [
            OHLCVRecord(f"2026-08-{i+1:02d}", "SYMA", "HOSE", 10.0, 11.0, 9.0, 10.0 + i, 1000)
            for i in range(12)
        ]
        sym_b = [
            OHLCVRecord(f"2026-08-{i+1:02d}", "SYMB", "HOSE", 10.0, 11.0, 9.0, 20.0 - i, 1000)
            for i in range(12)
        ]
        sym_c = [
            OHLCVRecord(f"2026-08-{i+1:02d}", "SYMC", "HOSE", 10.0, 11.0, 9.0, 10.0, 1000)
            for i in range(12)
        ]
        sym_d = [
            OHLCVRecord(f"2026-08-{i+1:02d}", "SYMD", "HOSE", 10.0, 11.0, 9.0, 10.0, 1000)
            for i in range(5)
        ]

        ind_dict = {
            "SYMA": classify_signals_for_symbol(calculate_symbol_indicators(sym_a)),
            "SYMB": classify_signals_for_symbol(calculate_symbol_indicators(sym_b)),
            "SYMC": classify_signals_for_symbol(calculate_symbol_indicators(sym_c)),
            "SYMD": classify_signals_for_symbol(calculate_symbol_indicators(sym_d)),
        }

        metric, history = calculate_market_breadth(ind_dict, "2026-08-12")

        # Eligible count should be 3 (SYMA, SYMB, SYMC), SYMD has no MA10 so not eligible
        self.assertEqual(metric.eligible_count, 3)
        self.assertEqual(metric.above_count, 1)
        self.assertEqual(metric.below_count, 1)
        self.assertEqual(metric.on_ma10_count, 1)
        # Denominator invariant: eligible == above + below + on_ma10
        self.assertEqual(metric.eligible_count, metric.above_count + metric.below_count + metric.on_ma10_count)
        self.assertAlmostEqual(metric.above_pct, 33.3, places=1)
        self.assertAlmostEqual(metric.below_pct, 33.3, places=1)


if __name__ == "__main__":
    unittest.main()
