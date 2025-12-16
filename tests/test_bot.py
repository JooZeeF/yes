"""
Testy dla modułu bota.
"""

import unittest

from trading_bot.bot import TradingBot
from trading_bot.config import TradingConfig
from trading_bot.strategy import Candle, Signal, SimpleMovingAverageStrategy


class TestTradingBot(unittest.TestCase):
    """Testy dla klasy TradingBot."""
    
    def setUp(self):
        """Przygotowanie bota testowego."""
        self.config = TradingConfig(
            symbol="BTC/USDT",
            timeframe="1h",
            max_position_size=0.1,
            stop_loss_percent=2.0,
            take_profit_percent=4.0,
            dry_run=True
        )
        self.strategy = SimpleMovingAverageStrategy(short_period=3, long_period=5)
        self.bot = TradingBot(config=self.config, strategy=self.strategy)
    
    def test_bot_initialization(self):
        """Test inicjalizacji bota."""
        self.assertEqual(self.bot.config.symbol, "BTC/USDT")
        self.assertEqual(self.bot.strategy.name, "SMA_3_5")
        self.assertIsNone(self.bot.position)
        self.assertEqual(self.bot.balance, 10000.0)
    
    def test_get_status(self):
        """Test pobierania statusu bota."""
        status = self.bot.get_status()
        
        self.assertIn("strategy", status)
        self.assertIn("symbol", status)
        self.assertIn("timeframe", status)
        self.assertIn("position", status)
        self.assertIn("balance", status)
        self.assertIn("dry_run", status)
    
    def test_process_empty_candles(self):
        """Test przetwarzania pustych danych."""
        result = self.bot.process_candles([])
        self.assertIsNone(result)
    
    def test_open_position(self):
        """Test otwierania pozycji."""
        result = self.bot._open_position(50000.0)
        
        self.assertEqual(self.bot.position, 50000.0)
        self.assertIn("LONG", result)
    
    def test_close_position(self):
        """Test zamykania pozycji."""
        self.bot._open_position(50000.0)
        result = self.bot._close_position(51000.0)
        
        self.assertIsNone(self.bot.position)
        self.assertIn("Zamknięto", result)
    
    def test_close_position_without_open(self):
        """Test zamykania pozycji bez otwartej pozycji."""
        result = self.bot._close_position(50000.0)
        self.assertEqual(result, "Brak otwartej pozycji")


class TestTradingConfig(unittest.TestCase):
    """Testy dla klasy TradingConfig."""
    
    def test_default_config(self):
        """Test domyślnej konfiguracji."""
        config = TradingConfig()
        
        self.assertEqual(config.symbol, "BTC/USDT")
        self.assertEqual(config.timeframe, "1h")
        self.assertTrue(config.dry_run)
    
    def test_custom_config(self):
        """Test niestandardowej konfiguracji."""
        config = TradingConfig(
            symbol="ETH/USDT",
            timeframe="4h",
            max_position_size=0.2,
            dry_run=False
        )
        
        self.assertEqual(config.symbol, "ETH/USDT")
        self.assertEqual(config.timeframe, "4h")
        self.assertEqual(config.max_position_size, 0.2)
        self.assertFalse(config.dry_run)


if __name__ == "__main__":
    unittest.main()
