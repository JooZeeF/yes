"""
Testy dla modułu indicators.
"""

import unittest
from trading_bot.strategy import Candle
from trading_bot.indicators import (
    calculate_sma,
    calculate_ema,
    calculate_bollinger_bands,
    calculate_atr,
    calculate_rsi,
    calculate_macd,
    calculate_donchian_channel,
    calculate_vwap,
    calculate_z_score,
    detect_volume_spike,
)


def create_test_candles(prices: list, volumes: list = None) -> list:
    """Tworzy listę świec testowych."""
    if volumes is None:
        volumes = [1000] * len(prices)
    
    candles = []
    for i, (price, vol) in enumerate(zip(prices, volumes)):
        candles.append(Candle(
            timestamp=1700000000 + i * 3600,
            open=price - 1,
            high=price + 2,
            low=price - 2,
            close=price,
            volume=vol
        ))
    return candles


class TestSMA(unittest.TestCase):
    def test_sma_calculation(self):
        prices = [10, 20, 30, 40, 50]
        result = calculate_sma(prices, 3)
        self.assertAlmostEqual(result, 40.0)  # (30+40+50)/3
    
    def test_sma_insufficient_data(self):
        prices = [10, 20]
        result = calculate_sma(prices, 5)
        self.assertIsNone(result)


class TestEMA(unittest.TestCase):
    def test_ema_calculation(self):
        prices = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
        result = calculate_ema(prices, 5)
        self.assertIsNotNone(result)
        # EMA dla rosnących cen powinna być bliżej końca
        self.assertGreater(result, 50)  # Powyżej środkowej wartości
    
    def test_ema_insufficient_data(self):
        prices = [10, 20]
        result = calculate_ema(prices, 5)
        self.assertIsNone(result)


class TestBollingerBands(unittest.TestCase):
    def test_bb_calculation(self):
        prices = list(range(100, 120))
        candles = create_test_candles(prices)
        result = calculate_bollinger_bands(candles, period=10)
        
        self.assertIsNotNone(result)
        self.assertGreater(result.upper, result.middle)
        self.assertLess(result.lower, result.middle)
        self.assertGreater(result.bandwidth, 0)
    
    def test_bb_insufficient_data(self):
        candles = create_test_candles([100, 101, 102])
        result = calculate_bollinger_bands(candles, period=10)
        self.assertIsNone(result)


class TestATR(unittest.TestCase):
    def test_atr_calculation(self):
        prices = list(range(100, 120))
        candles = create_test_candles(prices)
        result = calculate_atr(candles, period=5)
        
        self.assertIsNotNone(result)
        self.assertGreater(result, 0)
    
    def test_atr_insufficient_data(self):
        candles = create_test_candles([100, 101, 102])
        result = calculate_atr(candles, period=10)
        self.assertIsNone(result)


class TestRSI(unittest.TestCase):
    def test_rsi_uptrend(self):
        # Silny trend wzrostowy
        prices = list(range(100, 125))
        candles = create_test_candles(prices)
        result = calculate_rsi(candles, period=14)
        
        self.assertIsNotNone(result)
        self.assertGreater(result, 70)  # Overbought
    
    def test_rsi_downtrend(self):
        # Silny trend spadkowy
        prices = list(range(125, 100, -1))
        candles = create_test_candles(prices)
        result = calculate_rsi(candles, period=14)
        
        self.assertIsNotNone(result)
        self.assertLess(result, 30)  # Oversold


class TestMACD(unittest.TestCase):
    def test_macd_calculation(self):
        # 50 świec trendu wzrostowego
        prices = list(range(100, 150))
        candles = create_test_candles(prices)
        result = calculate_macd(candles)
        
        self.assertIsNotNone(result)
        self.assertGreater(result.macd_line, 0)  # Trend wzrostowy


class TestDonchian(unittest.TestCase):
    def test_donchian_calculation(self):
        prices = list(range(100, 125))
        candles = create_test_candles(prices)
        result = calculate_donchian_channel(candles, period=10)
        
        self.assertIsNotNone(result)
        self.assertGreater(result.upper, result.middle)
        self.assertLess(result.lower, result.middle)


class TestVWAP(unittest.TestCase):
    def test_vwap_calculation(self):
        prices = [100, 101, 102, 103, 104]
        volumes = [1000, 2000, 1500, 1000, 500]
        candles = create_test_candles(prices, volumes)
        
        result = calculate_vwap(candles)
        self.assertIsNotNone(result)
        self.assertGreater(result, 100)
        self.assertLess(result, 104)


class TestZScore(unittest.TestCase):
    def test_zscore_calculation(self):
        # Cena na poziomie średniej
        prices = [100] * 20
        candles = create_test_candles(prices)
        result = calculate_z_score(candles, period=10)
        
        self.assertEqual(result, 0.0)  # Brak odchylenia
    
    def test_zscore_high_price(self):
        # Cena znacznie powyżej średniej
        prices = [100] * 19 + [120]
        candles = create_test_candles(prices)
        result = calculate_z_score(candles, period=10)
        
        self.assertIsNotNone(result)
        self.assertGreater(result, 0)


class TestVolumeSpike(unittest.TestCase):
    def test_volume_spike_detected(self):
        prices = [100] * 25
        volumes = [1000] * 24 + [10000]  # Ostatni wolumen 10x większy
        candles = create_test_candles(prices, volumes)
        
        result = detect_volume_spike(candles, lookback=20, threshold_percentile=90)
        self.assertTrue(result)
    
    def test_no_volume_spike(self):
        prices = [100] * 25
        volumes = [1000] * 25
        candles = create_test_candles(prices, volumes)
        
        result = detect_volume_spike(candles, lookback=20, threshold_percentile=90)
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
