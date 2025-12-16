#!/usr/bin/env python3
"""
Flash Crash Analysis Script

Analyzes trading bot strategy performance during market crashes
using BingX historical data.

Usage:
    python -m trading_bot.analyze_crash [--symbols N] [--recent-days N]
    
Arguments:
    --symbols N      Number of top symbols to analyze (default: 20)
    --recent-days N  Analyze last N days instead of predefined crashes
"""

import argparse
import logging
import sys
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from trading_bot.data_provider import BingXDataProvider, MarketInfo
from trading_bot.strategy import (
    Candle, Signal,
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
from trading_bot.backtest import Backtester, BacktestConfig, BacktestResult

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class CrashEvent:
    """Represents a market crash event."""
    name: str
    start_date: datetime
    end_date: datetime
    description: str


@dataclass
class AnalysisResult:
    """Result of analyzing a single strategy on a crash event."""
    strategy_name: str
    symbol: str
    timeframe: str
    crash_event: str
    total_trades: int
    pnl_percent: float
    max_drawdown: float
    win_rate: float
    sharpe_ratio: Optional[float]


def get_strategies() -> Dict[str, Any]:
    """Get all strategies to test."""
    return {
        "SMA_10_20": SimpleMovingAverageStrategy(short_period=10, long_period=20),
        "EMA_9_21": EMAStrategy(fast_period=9, slow_period=21),
        "Bollinger_20_2": BollingerBandsStrategy(period=20, num_std=2.0),
        "RSI_14": RSIStrategy(period=14, oversold_level=30, overbought_level=70),
        "Donchian_20": DonchianBreakoutStrategy(period=20),
        "MACD_12_26_9": MACDStrategy(fast_period=12, slow_period=26, signal_period=9),
        "ADXTrend_9_21": ADXTrendStrategy(ema_fast=9, ema_slow=21, adx_period=14, adx_threshold=20),
        "VolumeBreakout_20": VolumeBreakoutStrategy(donchian_period=20, volume_lookback=20),
        "MeanReversion_ZScore": MeanReversionZScoreStrategy(period=20, entry_threshold=2.0),
    }


def get_crash_events() -> List[CrashEvent]:
    """
    Define crash events to analyze.
    
    Note: These dates should be updated based on actual market events.
    If no specific crashes are known, use --recent-days flag to analyze recent data.
    """
    return [
        CrashEvent(
            name="Flash_Crash_Oct_10",
            start_date=datetime(2025, 10, 9, 0, 0, tzinfo=timezone.utc),
            end_date=datetime(2025, 10, 11, 23, 59, tzinfo=timezone.utc),
            description="Flash crash on October 10, 2025"
        ),
        CrashEvent(
            name="Dynamic_Drop_Dec_12-16",
            start_date=datetime(2025, 12, 11, 0, 0, tzinfo=timezone.utc),
            end_date=datetime(2025, 12, 17, 23, 59, tzinfo=timezone.utc),
            description="Two dynamic drops from December 12-16, 2025"
        ),
    ]


def get_recent_period(days: int = 7) -> List[CrashEvent]:
    """Get a recent time period for analysis."""
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)
    
    return [
        CrashEvent(
            name=f"Recent_{days}_Days",
            start_date=start_date,
            end_date=end_date,
            description=f"Recent {days} days analysis"
        )
    ]


def detect_crash_periods(candles: List[Candle], threshold_percent: float = -5.0) -> List[Dict]:
    """
    Detect crash periods in candle data.
    
    Args:
        candles: List of candles
        threshold_percent: Price drop threshold to consider as crash
        
    Returns:
        List of detected crash periods
    """
    crashes = []
    
    if len(candles) < 10:
        return crashes
    
    for i in range(1, len(candles)):
        # Calculate percentage change from open of previous candle to close of current
        price_change = ((candles[i].close - candles[i-1].open) / candles[i-1].open) * 100
        
        if price_change <= threshold_percent:
            crashes.append({
                "index": i,
                "timestamp": candles[i].timestamp,
                "price_change": price_change,
                "open_price": candles[i-1].open,
                "close_price": candles[i].close
            })
    
    return crashes


def analyze_strategy_on_crash(
    candles: List[Candle],
    strategy: Any,
    strategy_name: str,
    symbol: str,
    timeframe: str,
    crash_name: str
) -> Optional[AnalysisResult]:
    """
    Analyze a single strategy's performance during a crash.
    
    Returns:
        AnalysisResult or None if insufficient data
    """
    if len(candles) < 100:
        logger.warning(f"Insufficient data for {symbol} {timeframe} ({len(candles)} candles)")
        return None
    
    # Configure backtester
    config = BacktestConfig(
        initial_capital=10000.0,
        maker_fee_percent=0.02,  # 2 bps
        taker_fee_percent=0.05,  # 5 bps
        slippage_percent=0.03,   # 3 bps
        position_size_percent=10.0,
        stop_loss_percent=3.0,
        take_profit_percent=5.0
    )
    
    backtester = Backtester(config)
    
    try:
        result = backtester.run(candles, strategy)
        
        return AnalysisResult(
            strategy_name=strategy_name,
            symbol=symbol,
            timeframe=timeframe,
            crash_event=crash_name,
            total_trades=result.total_trades,
            pnl_percent=result.total_return_percent,
            max_drawdown=result.max_drawdown_percent,
            win_rate=result.win_rate,
            sharpe_ratio=result.sharpe_ratio
        )
    except Exception as e:
        logger.error(f"Error backtesting {strategy_name} on {symbol} {timeframe}: {e}")
        return None


def print_analysis_summary(results: List[AnalysisResult]):
    """Print summary of all analysis results."""
    
    print("\n" + "=" * 100)
    print("FLASH CRASH ANALYSIS SUMMARY")
    print("=" * 100)
    
    # Group by crash event
    by_crash = {}
    for r in results:
        if r.crash_event not in by_crash:
            by_crash[r.crash_event] = []
        by_crash[r.crash_event].append(r)
    
    for crash_name, crash_results in by_crash.items():
        print(f"\n{'='*50}")
        print(f"CRASH EVENT: {crash_name}")
        print(f"{'='*50}")
        
        # Group by strategy
        by_strategy = {}
        for r in crash_results:
            if r.strategy_name not in by_strategy:
                by_strategy[r.strategy_name] = []
            by_strategy[r.strategy_name].append(r)
        
        for strategy_name, strat_results in by_strategy.items():
            print(f"\n  Strategy: {strategy_name}")
            print(f"  {'-'*40}")
            
            total_pnl = sum(r.pnl_percent for r in strat_results)
            avg_pnl = total_pnl / len(strat_results) if strat_results else 0
            avg_dd = sum(r.max_drawdown for r in strat_results) / len(strat_results) if strat_results else 0
            total_trades = sum(r.total_trades for r in strat_results)
            avg_winrate = sum(r.win_rate for r in strat_results) / len(strat_results) if strat_results else 0
            
            print(f"    Avg PnL: {avg_pnl:+.2f}%")
            print(f"    Avg Max DD: {avg_dd:.2f}%")
            print(f"    Total Trades: {total_trades}")
            print(f"    Avg Win Rate: {avg_winrate*100:.1f}%")
            
            # Best and worst performing symbols
            sorted_results = sorted(strat_results, key=lambda x: x.pnl_percent, reverse=True)
            
            if sorted_results:
                best = sorted_results[0]
                worst = sorted_results[-1]
                
                print(f"    Best: {best.symbol} ({best.timeframe}): {best.pnl_percent:+.2f}%")
                print(f"    Worst: {worst.symbol} ({worst.timeframe}): {worst.pnl_percent:+.2f}%")
    
    # Overall summary
    print("\n" + "=" * 100)
    print("OVERALL STRATEGY RANKING")
    print("=" * 100)
    
    by_strategy_overall = {}
    for r in results:
        if r.strategy_name not in by_strategy_overall:
            by_strategy_overall[r.strategy_name] = []
        by_strategy_overall[r.strategy_name].append(r)
    
    rankings = []
    for strategy_name, strat_results in by_strategy_overall.items():
        avg_pnl = sum(r.pnl_percent for r in strat_results) / len(strat_results) if strat_results else 0
        avg_dd = sum(r.max_drawdown for r in strat_results) / len(strat_results) if strat_results else 0
        total_trades = sum(r.total_trades for r in strat_results)
        
        rankings.append({
            "name": strategy_name,
            "avg_pnl": avg_pnl,
            "avg_dd": avg_dd,
            "total_trades": total_trades,
            "samples": len(strat_results)
        })
    
    rankings.sort(key=lambda x: x["avg_pnl"], reverse=True)
    
    print(f"\n{'Rank':<5} {'Strategy':<25} {'Avg PnL':<12} {'Avg DD':<12} {'Trades':<10} {'Samples':<8}")
    print("-" * 80)
    
    for i, r in enumerate(rankings, 1):
        print(f"{i:<5} {r['name']:<25} {r['avg_pnl']:+.2f}%{'':<5} {r['avg_dd']:.2f}%{'':<5} {r['total_trades']:<10} {r['samples']:<8}")


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Analyze trading strategy performance during market crashes"
    )
    parser.add_argument(
        "--symbols", "-s",
        type=int,
        default=20,
        help="Number of top symbols to analyze (default: 20)"
    )
    parser.add_argument(
        "--recent-days", "-r",
        type=int,
        default=None,
        help="Analyze last N days instead of predefined crashes"
    )
    parser.add_argument(
        "--timeframes", "-t",
        nargs="+",
        default=["1m", "5m", "15m", "30m", "1h", "4h", "12h", "1d"],
        help="Timeframes to analyze"
    )
    return parser.parse_args()


def main():
    """Main analysis function."""
    
    args = parse_args()
    
    print("\n" + "=" * 100)
    print("TRADING BOT FLASH CRASH ANALYSIS")
    print("Using BingX API for historical data")
    print("=" * 100)
    
    # Initialize data provider
    provider = BingXDataProvider(timeout=60)
    
    # Get top symbols by volume
    print(f"\nFetching top {args.symbols} symbols by volume...")
    symbols = provider.get_top_symbols(limit=args.symbols)
    
    if not symbols:
        print("ERROR: Could not fetch symbols from BingX API")
        print("This may be due to network issues or API rate limits.")
        print("Please try again later.")
        sys.exit(1)
    
    print(f"\nTop {len(symbols)} symbols by 24h volume:")
    for i, s in enumerate(symbols, 1):
        print(f"  {i:2}. {s.symbol:<15} Volume: ${s.volume_24h:,.0f}")
    
    # Define timeframes
    timeframes = args.timeframes
    
    # Get strategies
    strategies = get_strategies()
    print(f"\nStrategies to test: {len(strategies)}")
    for name in strategies.keys():
        print(f"  - {name}")
    
    # Get crash events or recent period
    if args.recent_days:
        crash_events = get_recent_period(args.recent_days)
    else:
        crash_events = get_crash_events()
    
    print(f"\nPeriods to analyze: {len(crash_events)}")
    for event in crash_events:
        print(f"  - {event.name}: {event.start_date.date()} to {event.end_date.date()}")
    
    # Perform analysis
    all_results = []
    
    for event in crash_events:
        print(f"\n{'='*60}")
        print(f"Analyzing: {event.name}")
        print(f"Period: {event.start_date} to {event.end_date}")
        print(f"{'='*60}")
        
        for symbol_info in symbols:
            symbol = symbol_info.symbol
            
            for tf in timeframes:
                print(f"\n  Fetching {symbol} {tf}...", end=" ")
                
                candles = provider.get_klines_range(
                    symbol=symbol,
                    interval=tf,
                    start_date=event.start_date - timedelta(days=7),  # Extra data for indicators
                    end_date=event.end_date
                )
                
                if len(candles) < 100:
                    print(f"Insufficient data ({len(candles)} candles)")
                    continue
                
                print(f"Got {len(candles)} candles")
                
                # Detect crashes in data
                crashes = detect_crash_periods(candles, threshold_percent=-3.0)
                if crashes:
                    print(f"    Detected {len(crashes)} crash candles")
                
                # Test each strategy
                for strategy_name, strategy in strategies.items():
                    result = analyze_strategy_on_crash(
                        candles=candles,
                        strategy=strategy,
                        strategy_name=strategy_name,
                        symbol=symbol,
                        timeframe=tf,
                        crash_name=event.name
                    )
                    
                    if result:
                        all_results.append(result)
    
    # Print summary
    if all_results:
        print_analysis_summary(all_results)
    else:
        print("\nNo results to display. This may be because:")
        print("  - The specified dates are in the future")
        print("  - BingX API rate limits were exceeded")
        print("  - Network connectivity issues")
        print("\nTip: Try using recent historical dates instead.")


if __name__ == "__main__":
    main()
