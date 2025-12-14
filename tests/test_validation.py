"""
Testy dla modułu validation.
"""

import unittest
from trading_bot.validation import (
    DataValidator,
    AnomalyConfig,
    DataQuality,
    FeedHealthMonitor,
)
from trading_bot.guards import MarketData
from trading_bot.strategy import Candle


def create_test_candles(count: int, start_price: float = 100) -> list:
    """Tworzy listę normalnych świec testowych."""
    candles = []
    for i in range(count):
        price = start_price + i * 0.1
        candles.append(Candle(
            timestamp=1700000000 + i * 3600,
            open=price - 0.5,
            high=price + 1,
            low=price - 1,
            close=price,
            volume=1000 + i * 10
        ))
    return candles


class TestDataValidator(unittest.TestCase):
    def test_validate_good_data(self):
        validator = DataValidator()
        candles = create_test_candles(50)
        
        result = validator.validate_candles(candles)
        self.assertEqual(result.quality, DataQuality.GOOD)
        self.assertEqual(len(result.issues), 0)
    
    def test_validate_insufficient_data(self):
        validator = DataValidator()
        candles = create_test_candles(5)
        
        result = validator.validate_candles(candles)
        self.assertEqual(result.quality, DataQuality.WARNING)
    
    def test_detect_timestamp_gap(self):
        validator = DataValidator()
        candles = create_test_candles(30)
        
        # Wstaw dużą lukę czasową
        candles[15] = Candle(
            timestamp=candles[14].timestamp + 3600 * 24,  # 24h gap
            open=100, high=101, low=99, close=100, volume=1000
        )
        
        result = validator.validate_candles(candles)
        self.assertIn("timestamp_gaps", result.details)
    
    def test_detect_price_anomaly(self):
        validator = DataValidator()
        candles = create_test_candles(50)
        
        # Wstaw ekstremalną cenę (anomalia)
        candles[-1] = Candle(
            timestamp=candles[-1].timestamp,
            open=100,
            high=1000,  # 10x normalna
            low=100,
            close=500,  # Ekstremalna zmiana
            volume=1000
        )
        
        result = validator.validate_candles(candles)
        self.assertEqual(result.quality, DataQuality.BAD)
    
    def test_validate_ohlc_consistency(self):
        validator = DataValidator()
        candles = create_test_candles(30)
        
        # Złam spójność OHLC (high < low)
        candles[10] = Candle(
            timestamp=candles[10].timestamp,
            open=100,
            high=95,  # High < Low = błąd
            low=105,
            close=100,
            volume=1000
        )
        
        result = validator.validate_candles(candles)
        self.assertIn("ohlc_issues", result.details)


class TestOrderBookValidation(unittest.TestCase):
    def test_validate_good_order_book(self):
        validator = DataValidator()
        market_data = MarketData(
            bid=100,
            ask=100.1,
            bid_depth=10,
            ask_depth=10,
            last_price=100.05,
            timestamp_exchange=1700000000000,
            timestamp_received=1700000000100
        )
        
        result = validator.validate_order_book(market_data)
        self.assertEqual(result.quality, DataQuality.GOOD)
    
    def test_detect_crossed_book(self):
        validator = DataValidator()
        market_data = MarketData(
            bid=101,  # Bid > Ask = crossed
            ask=100,
            bid_depth=10,
            ask_depth=10,
            last_price=100.5,
            timestamp_exchange=1700000000000,
            timestamp_received=1700000000100
        )
        
        result = validator.validate_order_book(market_data)
        self.assertEqual(result.quality, DataQuality.BAD)
        self.assertTrue(result.details.get("crossed_book", False))


class TestFeedHealthMonitor(unittest.TestCase):
    def test_record_update(self):
        monitor = FeedHealthMonitor()
        monitor.record_update(1700000000000, 1700000000100)
        
        self.assertEqual(monitor.update_count, 1)
        self.assertIsNotNone(monitor.get_average_lag())
    
    def test_average_lag(self):
        monitor = FeedHealthMonitor()
        
        for i in range(10):
            monitor.record_update(
                1700000000000 + i * 1000,
                1700000000100 + i * 1000
            )
        
        avg_lag = monitor.get_average_lag()
        self.assertEqual(avg_lag, 100)
    
    def test_health_report(self):
        monitor = FeedHealthMonitor()
        monitor.record_update(1700000000000, 1700000000100)
        
        report = monitor.get_health_report()
        self.assertIn("update_count", report)
        self.assertIn("average_lag_ms", report)
        self.assertIn("max_lag_ms", report)


class TestFilterAnomalousCandles(unittest.TestCase):
    def test_filter_anomalies(self):
        validator = DataValidator()
        candles = create_test_candles(50)
        
        # Dodaj anomalię
        candles[-5] = Candle(
            timestamp=candles[-5].timestamp,
            open=100,
            high=500,
            low=100,
            close=400,  # Ekstremalna zmiana
            volume=1000
        )
        
        filtered, anomaly_indices = validator.filter_anomalous_candles(candles)
        
        # Anomalia powinna być wykryta
        self.assertGreater(len(anomaly_indices), 0)
        self.assertLess(len(filtered), len(candles))


if __name__ == "__main__":
    unittest.main()
