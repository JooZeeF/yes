"""
Testy dla modułu guards.
"""

import unittest
from trading_bot.guards import (
    SpreadGuard,
    DepthGuard,
    ClockDriftGuard,
    PriceBandGuard,
    DailyDrawdownGuard,
    CostAwareFilter,
    VolatilityRegimeFilter,
    GuardManager,
    GuardConfig,
    GuardStatus,
    VolatilityRegime,
    MarketData,
)
from trading_bot.strategy import Candle


def create_market_data(bid=100, ask=100.1, bid_depth=10, ask_depth=10) -> MarketData:
    return MarketData(
        bid=bid,
        ask=ask,
        bid_depth=bid_depth,
        ask_depth=ask_depth,
        last_price=(bid + ask) / 2,
        timestamp_exchange=1700000000000,
        timestamp_received=1700000000100,
    )


class TestSpreadGuard(unittest.TestCase):
    def test_spread_ok(self):
        guard = SpreadGuard(max_spread_bps=20)
        market_data = create_market_data(bid=100, ask=100.1)  # 10 bps
        
        result = guard.check(market_data)
        self.assertEqual(result.status, GuardStatus.OK)
    
    def test_spread_too_wide(self):
        guard = SpreadGuard(max_spread_bps=5)
        market_data = create_market_data(bid=100, ask=100.1)  # 10 bps
        
        result = guard.check(market_data)
        self.assertEqual(result.status, GuardStatus.BLOCKED)


class TestDepthGuard(unittest.TestCase):
    def test_depth_ok(self):
        guard = DepthGuard(min_bid_depth=5, min_ask_depth=5)
        market_data = create_market_data(bid_depth=10, ask_depth=10)
        
        result = guard.check(market_data)
        self.assertEqual(result.status, GuardStatus.OK)
    
    def test_depth_insufficient(self):
        guard = DepthGuard(min_bid_depth=20, min_ask_depth=20)
        market_data = create_market_data(bid_depth=10, ask_depth=10)
        
        result = guard.check(market_data)
        self.assertEqual(result.status, GuardStatus.BLOCKED)


class TestClockDriftGuard(unittest.TestCase):
    def test_clock_ok(self):
        guard = ClockDriftGuard(max_drift_ms=500)
        market_data = create_market_data()  # 100ms drift
        
        result = guard.check(market_data)
        self.assertEqual(result.status, GuardStatus.OK)
    
    def test_clock_drift_warning(self):
        guard = ClockDriftGuard(max_drift_ms=50)
        market_data = create_market_data()  # 100ms drift
        
        result = guard.check(market_data)
        self.assertEqual(result.status, GuardStatus.WARNING)


class TestPriceBandGuard(unittest.TestCase):
    def test_price_within_band(self):
        guard = PriceBandGuard(band_percent=5)
        guard.set_reference_price(100)
        
        result = guard.check(103)  # +3%
        self.assertEqual(result.status, GuardStatus.OK)
    
    def test_price_outside_band(self):
        guard = PriceBandGuard(band_percent=5)
        guard.set_reference_price(100)
        
        result = guard.check(110)  # +10%
        self.assertEqual(result.status, GuardStatus.BLOCKED)


class TestDailyDrawdownGuard(unittest.TestCase):
    def test_drawdown_ok(self):
        guard = DailyDrawdownGuard(max_drawdown_percent=5)
        guard.reset_daily(10000)
        
        result = guard.check(9800)  # -2%
        self.assertEqual(result.status, GuardStatus.OK)
    
    def test_drawdown_exceeded(self):
        guard = DailyDrawdownGuard(max_drawdown_percent=5)
        guard.reset_daily(10000)
        
        result = guard.check(9000)  # -10%
        self.assertEqual(result.status, GuardStatus.BLOCKED)


class TestCostAwareFilter(unittest.TestCase):
    def test_edge_covers_costs(self):
        filter = CostAwareFilter(
            maker_fee_bps=1,
            taker_fee_bps=5,
            expected_slippage_bps=2,
            min_edge_bps=5
        )
        
        result = filter.check(expected_edge_bps=20, is_maker=False)
        self.assertEqual(result.status, GuardStatus.OK)
    
    def test_edge_insufficient(self):
        filter = CostAwareFilter(
            maker_fee_bps=1,
            taker_fee_bps=5,
            expected_slippage_bps=2,
            min_edge_bps=5
        )
        
        result = filter.check(expected_edge_bps=5, is_maker=False)
        self.assertEqual(result.status, GuardStatus.BLOCKED)


class TestGuardManager(unittest.TestCase):
    def test_check_market_data(self):
        config = GuardConfig()
        manager = GuardManager(config)
        market_data = create_market_data()
        
        results = manager.check_market_data(market_data)
        self.assertEqual(len(results), 3)  # spread, depth, clock
    
    def test_is_trading_allowed(self):
        config = GuardConfig()
        manager = GuardManager(config)
        market_data = create_market_data()
        
        results = manager.check_market_data(market_data)
        self.assertTrue(manager.is_trading_allowed(results))


if __name__ == "__main__":
    unittest.main()
