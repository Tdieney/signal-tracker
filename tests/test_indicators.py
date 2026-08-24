"""Tests for indicator calculations."""

import unittest
from pipeline.indicators import calculate_symbol_indicators
from pipeline.models import OHLCVRecord


class TestIndicators(unittest.TestCase):

    def setUp(self):
        # Create 22 sessions of data
        self.records = [
            OHLCVRecord(
                trading_date=f"2026-08-{i+1:02d}",
                symbol="TEST",
                exchange="HOSE",
                open=100.0 + i,
                high=102.0 + i,
                low=98.0 + i,
                close=100.0 + i,  # 100, 101, 102, ..., 121
                volume=10000 * (i + 1),
            )
            for i in range(22)
        ]

    def test_ma10_window(self):
        results = calculate_symbol_indicators(self.records)
        
        # Sessions 0..8 (1..9): ma10 is None
        for i in range(9):
            self.assertIsNone(results[i].ma10, f"Session {i+1} should have no MA10")
            self.assertIsNone(results[i].distance_pct)

        # Session 9 (10th session): prices are 100, 101, ..., 109. Sum = 1045, Mean = 104.5
        self.assertIsNotNone(results[9].ma10)
        self.assertAlmostEqual(results[9].ma10, 104.5)
        # distance_pct: (109 - 104.5) / 104.5 * 100 = 4.5 / 104.5 * 100 = 4.30622%
        expected_distance = ((109.0 - 104.5) / 104.5) * 100.0
        self.assertAlmostEqual(results[9].distance_pct, expected_distance)

        # Session 10 (11th session): prices 101..110. Mean = 105.5
        self.assertAlmostEqual(results[10].ma10, 105.5)

    def test_avg_volume_20d(self):
        results = calculate_symbol_indicators(self.records)

        # Sessions 0..18 (1..19): avg_volume_20d is None
        for i in range(19):
            self.assertIsNone(results[i].avg_volume_20d, f"Session {i+1} should have no avg volume 20D")

        # Session 19 (20th session): volumes 10000 * (1..20). Sum = 10000 * 210 = 2100000. Mean = 105000
        self.assertIsNotNone(results[19].avg_volume_20d)
        self.assertEqual(results[19].avg_volume_20d, 105000.0)


if __name__ == "__main__":
    unittest.main()
