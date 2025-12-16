"""
Tests for data_provider module.
"""

import unittest
import tempfile
import os
from trading_bot.strategy import Candle
from trading_bot.data_provider import (
    CSVDataProvider,
    BingXDataProvider,
    timestamp_to_datetime,
    datetime_to_timestamp,
)
from datetime import datetime, timezone


class TestCSVDataProvider(unittest.TestCase):
    def setUp(self):
        """Create test data."""
        self.test_candles = [
            Candle(timestamp=1700000000000, open=100.0, high=105.0, low=95.0, close=102.0, volume=1000.0),
            Candle(timestamp=1700000060000, open=102.0, high=108.0, low=100.0, close=106.0, volume=1200.0),
            Candle(timestamp=1700000120000, open=106.0, high=110.0, low=104.0, close=108.0, volume=900.0),
        ]
    
    def test_save_and_load_candles(self):
        """Test saving and loading candles from CSV."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            filepath = f.name
        
        try:
            # Save candles
            CSVDataProvider.save_candles(self.test_candles, filepath)
            
            # Verify file exists
            self.assertTrue(os.path.exists(filepath))
            
            # Load candles
            loaded = CSVDataProvider.load_candles(filepath)
            
            # Verify data
            self.assertEqual(len(loaded), 3)
            self.assertEqual(loaded[0].timestamp, 1700000000000)
            self.assertEqual(loaded[0].open, 100.0)
            self.assertEqual(loaded[0].close, 102.0)
            
        finally:
            os.unlink(filepath)
    
    def test_load_nonexistent_file(self):
        """Test loading from non-existent file."""
        candles = CSVDataProvider.load_candles("/nonexistent/path/file.csv")
        self.assertEqual(len(candles), 0)


class TestBingXDataProvider(unittest.TestCase):
    def test_timeframes_defined(self):
        """Test that timeframes are properly defined."""
        provider = BingXDataProvider()
        
        expected_timeframes = ["1m", "5m", "15m", "30m", "1h", "4h", "12h", "1d"]
        
        for tf in expected_timeframes:
            self.assertIn(tf, provider.TIMEFRAMES)
            self.assertIn(tf, provider.TIMEFRAME_MS)
    
    def test_timeframe_ms_values(self):
        """Test timeframe millisecond values are correct."""
        provider = BingXDataProvider()
        
        self.assertEqual(provider.TIMEFRAME_MS["1m"], 60 * 1000)
        self.assertEqual(provider.TIMEFRAME_MS["1h"], 60 * 60 * 1000)
        self.assertEqual(provider.TIMEFRAME_MS["1d"], 24 * 60 * 60 * 1000)
    
    def test_invalid_interval_raises(self):
        """Test that invalid interval raises ValueError."""
        provider = BingXDataProvider()
        
        with self.assertRaises(ValueError):
            provider.get_klines("BTC-USDT", "invalid_tf")


class TestTimestampConversions(unittest.TestCase):
    def test_timestamp_to_datetime(self):
        """Test timestamp to datetime conversion."""
        ts = 1700000000000  # milliseconds
        dt = timestamp_to_datetime(ts)
        
        self.assertEqual(dt.year, 2023)
        self.assertEqual(dt.month, 11)
        self.assertEqual(dt.day, 14)
    
    def test_datetime_to_timestamp(self):
        """Test datetime to timestamp conversion."""
        dt = datetime(2023, 11, 14, 22, 13, 20, tzinfo=timezone.utc)
        ts = datetime_to_timestamp(dt)
        
        self.assertEqual(ts, 1700000000000)
    
    def test_roundtrip_conversion(self):
        """Test that conversions are reversible."""
        original_ts = 1700000000000
        
        dt = timestamp_to_datetime(original_ts)
        converted_ts = datetime_to_timestamp(dt)
        
        self.assertEqual(original_ts, converted_ts)


if __name__ == "__main__":
    unittest.main()
