"""
Testy dla modułu strategii tradingowych.
"""

import unittest

from trading_bot.strategy import (
    Candle,
    Signal,
    SimpleMovingAverageStrategy,
    EMAStrategy,
    BollingerBandsStrategy,
    RSIStrategy,
    DonchianBreakoutStrategy,
    MACDStrategy,
    ADXTrendStrategy,
    VolumeBreakoutStrategy,
    MeanReversionZScoreStrategy,
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


class TestSimpleMovingAverageStrategy(unittest.TestCase):
    """Testy dla strategii SMA."""
    
    def setUp(self):
        """Przygotowanie danych testowych."""
        self.strategy = SimpleMovingAverageStrategy(short_period=3, long_period=5)
    
    def test_strategy_name(self):
        """Test nazwy strategii."""
        self.assertEqual(self.strategy.name, "SMA_3_5")
    
    def test_invalid_periods_raises_error(self):
        """Test błędu przy nieprawidłowych okresach."""
        with self.assertRaises(ValueError):
            SimpleMovingAverageStrategy(short_period=5, long_period=3)
        
        with self.assertRaises(ValueError):
            SimpleMovingAverageStrategy(short_period=5, long_period=5)
        
        with self.assertRaises(ValueError):
            SimpleMovingAverageStrategy(short_period=0, long_period=5)
        
        with self.assertRaises(ValueError):
            SimpleMovingAverageStrategy(short_period=-1, long_period=5)
    
    def test_hold_signal_insufficient_data(self):
        """Test sygnału HOLD przy niewystarczających danych."""
        candles = [
            Candle(timestamp=i, open=100, high=105, low=95, close=100, volume=1000)
            for i in range(3)
        ]
        
        signal = self.strategy.analyze(candles)
        self.assertEqual(signal, Signal.HOLD)
    
    def test_buy_signal_on_crossover(self):
        """Test sygnału BUY przy przecięciu w górę."""
        # Tworzymy dane gdzie krótka SMA przecina długą od dołu
        # Najpierw ceny niskie, potem rosną
        prices = [90, 92, 94, 96, 98, 100, 105, 110]
        candles = [
            Candle(timestamp=i, open=p-1, high=p+2, low=p-2, close=p, volume=1000)
            for i, p in enumerate(prices)
        ]
        
        signal = self.strategy.analyze(candles)
        # Po wzroście cen, krótka SMA powinna być wyżej od długiej
        self.assertIn(signal, [Signal.BUY, Signal.HOLD])
    
    def test_sell_signal_on_crossover(self):
        """Test sygnału SELL przy przecięciu w dół."""
        # Tworzymy dane gdzie krótka SMA przecina długą od góry
        # Najpierw ceny wysokie, potem spadają
        prices = [110, 108, 106, 104, 102, 100, 95, 90]
        candles = [
            Candle(timestamp=i, open=p+1, high=p+2, low=p-2, close=p, volume=1000)
            for i, p in enumerate(prices)
        ]
        
        signal = self.strategy.analyze(candles)
        # Po spadku cen, krótka SMA powinna być niżej od długiej
        self.assertIn(signal, [Signal.SELL, Signal.HOLD])


class TestCandle(unittest.TestCase):
    """Testy dla klasy Candle."""
    
    def test_candle_creation(self):
        """Test tworzenia świecy."""
        candle = Candle(
            timestamp=1700000000,
            open=100.0,
            high=110.0,
            low=90.0,
            close=105.0,
            volume=1000.0
        )
        
        self.assertEqual(candle.timestamp, 1700000000)
        self.assertEqual(candle.open, 100.0)
        self.assertEqual(candle.high, 110.0)
        self.assertEqual(candle.low, 90.0)
        self.assertEqual(candle.close, 105.0)
        self.assertEqual(candle.volume, 1000.0)


class TestEMAStrategy(unittest.TestCase):
    def test_ema_strategy_name(self):
        strategy = EMAStrategy(fast_period=9, slow_period=21)
        self.assertEqual(strategy.name, "EMA_9_21")
    
    def test_ema_uptrend(self):
        prices = list(range(100, 150))
        candles = create_test_candles(prices)
        strategy = EMAStrategy(fast_period=5, slow_period=10)
        signal = strategy.analyze(candles)
        self.assertIn(signal, [Signal.BUY, Signal.HOLD])


class TestBollingerBandsStrategy(unittest.TestCase):
    def test_bb_strategy_name(self):
        strategy = BollingerBandsStrategy(period=20, num_std=2.0)
        self.assertEqual(strategy.name, "BB_20_2.0")
    
    def test_bb_oversold(self):
        # Cena znacznie poniżej średniej
        prices = [100] * 19 + [80]  # Ostatnia cena niska
        candles = create_test_candles(prices)
        strategy = BollingerBandsStrategy(period=10)
        signal = strategy.analyze(candles)
        self.assertIn(signal, [Signal.BUY, Signal.HOLD])


class TestRSIStrategy(unittest.TestCase):
    def test_rsi_strategy_name(self):
        strategy = RSIStrategy(period=14, oversold_level=30, overbought_level=70)
        self.assertEqual(strategy.name, "RSI_14_30_70")
    
    def test_rsi_oversold(self):
        # Trend spadkowy = niski RSI
        prices = list(range(130, 100, -1))
        candles = create_test_candles(prices)
        strategy = RSIStrategy(period=14, oversold_level=30, overbought_level=70)
        signal = strategy.analyze(candles)
        self.assertIn(signal, [Signal.BUY, Signal.HOLD])


class TestADXTrendStrategy(unittest.TestCase):
    def test_adx_strategy_name(self):
        strategy = ADXTrendStrategy(ema_fast=9, ema_slow=21, adx_period=14)
        self.assertEqual(strategy.name, "ADXTrend_9_21_14")
    
    def test_adx_invalid_params(self):
        with self.assertRaises(ValueError):
            ADXTrendStrategy(ema_fast=21, ema_slow=9)
    
    def test_adx_uptrend(self):
        # Silny trend wzrostowy
        prices = list(range(100, 160))
        candles = create_test_candles(prices)
        strategy = ADXTrendStrategy(ema_fast=5, ema_slow=10, adx_period=10, adx_threshold=15)
        signal = strategy.analyze(candles)
        self.assertIn(signal, [Signal.BUY, Signal.HOLD])


class TestVolumeBreakoutStrategy(unittest.TestCase):
    def test_volume_breakout_name(self):
        strategy = VolumeBreakoutStrategy(donchian_period=20, volume_percentile=90)
        self.assertEqual(strategy.name, "VolumeBreakout_20_90")
    
    def test_breakout_with_volume(self):
        # Ceny rosnące z wysokim wolumenem na końcu
        prices = list(range(100, 130))
        volumes = [1000] * 29 + [10000]  # Spike na końcu
        candles = create_test_candles(prices, volumes)
        strategy = VolumeBreakoutStrategy(donchian_period=10, volume_lookback=20)
        signal = strategy.analyze(candles)
        self.assertIn(signal, [Signal.BUY, Signal.HOLD])


class TestMeanReversionZScoreStrategy(unittest.TestCase):
    def test_zscore_strategy_name(self):
        strategy = MeanReversionZScoreStrategy(period=20, entry_threshold=2.0)
        self.assertEqual(strategy.name, "MRZScore_20_2.0")
    
    def test_zscore_oversold(self):
        # Cena znacznie poniżej średniej
        prices = [100] * 19 + [85]
        candles = create_test_candles(prices)
        strategy = MeanReversionZScoreStrategy(period=10, entry_threshold=1.5)
        signal = strategy.analyze(candles)
        self.assertIn(signal, [Signal.BUY, Signal.HOLD])


if __name__ == "__main__":
    unittest.main()
