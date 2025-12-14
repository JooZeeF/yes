"""
Testy dla modułu backtest.
"""

import unittest
from trading_bot.backtest import (
    Backtester,
    BacktestConfig,
    print_backtest_report,
)
from trading_bot.strategy import (
    Candle,
    SimpleMovingAverageStrategy,
    EMAStrategy,
)


def create_trending_candles(count: int, trend: str = "up") -> list:
    """Tworzy świece z trendem."""
    candles = []
    base_price = 100
    
    for i in range(count):
        if trend == "up":
            price = base_price + i * 0.5
        elif trend == "down":
            price = base_price - i * 0.5
        else:
            price = base_price + (i % 10) * 0.1
        
        candles.append(Candle(
            timestamp=1700000000 + i * 3600,
            open=price - 0.2,
            high=price + 0.5,
            low=price - 0.5,
            close=price,
            volume=1000 + i * 10
        ))
    
    return candles


class TestBacktester(unittest.TestCase):
    def setUp(self):
        self.config = BacktestConfig(
            initial_capital=10000.0,
            maker_fee_percent=0.01,
            taker_fee_percent=0.05,
            slippage_percent=0.02,
            position_size_percent=10.0,
            stop_loss_percent=2.0,
            take_profit_percent=4.0
        )
        self.backtester = Backtester(self.config)
    
    def test_backtest_uptrend(self):
        candles = create_trending_candles(100, trend="up")
        strategy = SimpleMovingAverageStrategy(short_period=5, long_period=10)
        
        result = self.backtester.run(candles, strategy)
        
        self.assertEqual(result.initial_capital, 10000.0)
        self.assertIsNotNone(result.final_capital)
        self.assertIsNotNone(result.total_return_percent)
    
    def test_backtest_downtrend(self):
        candles = create_trending_candles(100, trend="down")
        strategy = SimpleMovingAverageStrategy(short_period=5, long_period=10)
        
        result = self.backtester.run(candles, strategy)
        
        self.assertIsNotNone(result.max_drawdown_percent)
        self.assertGreaterEqual(result.max_drawdown_percent, 0)
    
    def test_backtest_insufficient_data(self):
        candles = create_trending_candles(30)  # Za mało
        strategy = SimpleMovingAverageStrategy()
        
        with self.assertRaises(ValueError):
            self.backtester.run(candles, strategy)
    
    def test_backtest_metrics(self):
        candles = create_trending_candles(100, trend="up")
        strategy = EMAStrategy(fast_period=5, slow_period=10)
        
        result = self.backtester.run(candles, strategy)
        
        # Sprawdź czy metryki są sensowne
        self.assertGreaterEqual(result.win_rate, 0)
        self.assertLessEqual(result.win_rate, 1)
        
        self.assertEqual(
            result.winning_trades + result.losing_trades,
            result.total_trades
        )
    
    def test_equity_curve(self):
        candles = create_trending_candles(100)
        strategy = SimpleMovingAverageStrategy(short_period=5, long_period=10)
        
        result = self.backtester.run(candles, strategy)
        
        # Equity curve powinno mieć więcej punktów niż świec
        self.assertGreater(len(result.equity_curve), 0)
        # Pierwszy punkt to początkowy kapitał
        self.assertEqual(result.equity_curve[0], self.config.initial_capital)
    
    def test_drawdown_curve(self):
        candles = create_trending_candles(100)
        strategy = SimpleMovingAverageStrategy(short_period=5, long_period=10)
        
        result = self.backtester.run(candles, strategy)
        
        # Drawdown nie może być ujemny
        for dd in result.drawdown_curve:
            self.assertGreaterEqual(dd, 0)


class TestWalkForwardValidation(unittest.TestCase):
    def test_walk_forward(self):
        candles = create_trending_candles(200)
        strategy = SimpleMovingAverageStrategy(short_period=5, long_period=10)
        
        config = BacktestConfig(initial_capital=10000.0)
        backtester = Backtester(config)
        
        results = backtester.walk_forward_validation(
            candles=candles,
            strategy=strategy,
            train_size=50,
            test_size=30
        )
        
        self.assertGreater(len(results), 0)


class TestBacktestConfig(unittest.TestCase):
    def test_default_config(self):
        config = BacktestConfig()
        
        self.assertEqual(config.initial_capital, 10000.0)
        self.assertGreater(config.taker_fee_percent, config.maker_fee_percent)
    
    def test_custom_config(self):
        config = BacktestConfig(
            initial_capital=50000.0,
            stop_loss_percent=1.5,
            take_profit_percent=3.0
        )
        
        self.assertEqual(config.initial_capital, 50000.0)
        self.assertEqual(config.stop_loss_percent, 1.5)


if __name__ == "__main__":
    unittest.main()
