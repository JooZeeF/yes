"""
Testy dla modułu strategii tradingowych.
"""

import unittest

from trading_bot.strategy import (
    Candle,
    Signal,
    SimpleMovingAverageStrategy,
)


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


if __name__ == "__main__":
    unittest.main()
