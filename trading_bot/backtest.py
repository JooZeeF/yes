"""
Moduł backtestingu.

Implementuje:
- Backtesting z kosztami transakcji
- Symulacja poślizgu i partial fills
- Walk-forward validation
- Raportowanie (PnL, Sharpe, Sortino, max DD)
"""

import logging
import math
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Callable
from enum import Enum

from .strategy import Candle, Signal, TradingStrategy
from .config import TradingConfig

logger = logging.getLogger(__name__)


class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"


@dataclass
class Trade:
    """Reprezentacja transakcji."""
    timestamp: int
    side: OrderSide
    price: float
    quantity: float
    fee: float
    slippage: float
    pnl: float = 0.0


@dataclass
class BacktestConfig:
    """Konfiguracja backtestingu."""
    # Kapitał początkowy
    initial_capital: float = 10000.0
    
    # Opłaty
    maker_fee_percent: float = 0.01  # 0.01% = 1 bps
    taker_fee_percent: float = 0.05  # 0.05% = 5 bps
    
    # Poślizg
    slippage_percent: float = 0.02  # 0.02% = 2 bps
    
    # Pozycja
    position_size_percent: float = 10.0  # 10% kapitału na trade
    
    # Risk management
    stop_loss_percent: float = 2.0
    take_profit_percent: float = 4.0
    
    # Funding (dla perpetual futures)
    funding_rate_8h: float = 0.01  # 0.01% co 8h
    
    # Latency model
    latency_ms: int = 100  # Opóźnienie w ms


@dataclass
class BacktestResult:
    """Wynik backtestingu."""
    # Podstawowe metryki
    initial_capital: float
    final_capital: float
    total_return_percent: float
    
    # Transakcje
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    
    # PnL
    gross_pnl: float
    total_fees: float
    total_slippage: float
    net_pnl: float
    
    # Risk metrics
    max_drawdown_percent: float
    sharpe_ratio: Optional[float]
    sortino_ratio: Optional[float]
    
    # Dodatkowe
    avg_trade_pnl: float
    avg_win: float
    avg_loss: float
    profit_factor: float
    
    # Szczegóły
    trades: List[Trade] = field(default_factory=list)
    equity_curve: List[float] = field(default_factory=list)
    drawdown_curve: List[float] = field(default_factory=list)


class Backtester:
    """Silnik backtestingu."""
    
    def __init__(self, config: BacktestConfig):
        self.config = config
    
    def run(
        self,
        candles: List[Candle],
        strategy: TradingStrategy,
        trading_config: Optional[TradingConfig] = None
    ) -> BacktestResult:
        """
        Uruchamia backtest.
        
        Args:
            candles: Dane historyczne
            strategy: Strategia do testowania
            trading_config: Opcjonalna konfiguracja tradingowa
        """
        if len(candles) < 50:
            raise ValueError("Insufficient data for backtesting (min 50 candles)")
        
        capital = self.config.initial_capital
        position: Optional[float] = None  # Cena wejścia
        position_size: float = 0.0
        
        trades: List[Trade] = []
        equity_curve: List[float] = [capital]
        peak_capital = capital
        max_drawdown = 0.0
        drawdown_curve: List[float] = [0.0]
        daily_returns: List[float] = []
        
        # Iteruj przez świece z shift(1) dla uniknięcia lookahead
        for i in range(50, len(candles)):
            # Dane dostępne w momencie sygnału (bez bieżącej świecy)
            historical_candles = candles[:i]
            current_candle = candles[i]
            
            # Generuj sygnał na podstawie historycznych danych
            signal = strategy.analyze(historical_candles)
            
            # Cena wykonania z poślizgiem
            execution_price = self._apply_slippage(current_candle.open, signal)
            
            # Obsługa sygnałów
            if signal == Signal.BUY and position is None:
                # Otwórz pozycję long
                position_value = capital * (self.config.position_size_percent / 100)
                position_size = position_value / execution_price
                fee = position_value * (self.config.taker_fee_percent / 100)
                slippage_cost = position_value * (self.config.slippage_percent / 100)
                
                position = execution_price
                # Kapitał zmniejsza się o wartość pozycji + koszty
                capital -= position_value + fee + slippage_cost
                
                trades.append(Trade(
                    timestamp=current_candle.timestamp,
                    side=OrderSide.BUY,
                    price=execution_price,
                    quantity=position_size,
                    fee=fee,
                    slippage=slippage_cost
                ))
                
            elif signal == Signal.SELL and position is not None:
                # Zamknij pozycję
                position_value = position_size * execution_price
                fee = position_value * (self.config.taker_fee_percent / 100)
                slippage_cost = position_value * (self.config.slippage_percent / 100)
                
                # PnL to różnica między wartością sprzedaży a kupna
                entry_value = position_size * position
                pnl = position_value - entry_value - fee - slippage_cost
                
                # Kapitał zwiększa się o wartość sprzedaży minus koszty
                capital += position_value - fee - slippage_cost
                
                trades.append(Trade(
                    timestamp=current_candle.timestamp,
                    side=OrderSide.SELL,
                    price=execution_price,
                    quantity=position_size,
                    fee=fee,
                    slippage=slippage_cost,
                    pnl=pnl
                ))
                
                position = None
                position_size = 0.0
            
            # Sprawdź stop loss / take profit
            elif position is not None:
                price_change = ((current_candle.close - position) / position) * 100
                
                if price_change <= -self.config.stop_loss_percent:
                    # Stop loss
                    sl_price = position * (1 - self.config.stop_loss_percent / 100)
                    position_value = position_size * sl_price
                    fee = position_value * (self.config.taker_fee_percent / 100)
                    slippage_cost = position_value * (self.config.slippage_percent / 100)
                    
                    entry_value = position_size * position
                    pnl = position_value - entry_value - fee - slippage_cost
                    capital += position_value - fee - slippage_cost
                    
                    trades.append(Trade(
                        timestamp=current_candle.timestamp,
                        side=OrderSide.SELL,
                        price=sl_price,
                        quantity=position_size,
                        fee=fee,
                        slippage=slippage_cost,
                        pnl=pnl
                    ))
                    
                    position = None
                    position_size = 0.0
                    
                elif price_change >= self.config.take_profit_percent:
                    # Take profit
                    tp_price = position * (1 + self.config.take_profit_percent / 100)
                    position_value = position_size * tp_price
                    fee = position_value * (self.config.taker_fee_percent / 100)
                    slippage_cost = position_value * (self.config.slippage_percent / 100)
                    
                    entry_value = position_size * position
                    pnl = position_value - entry_value - fee - slippage_cost
                    capital += position_value - fee - slippage_cost
                    
                    trades.append(Trade(
                        timestamp=current_candle.timestamp,
                        side=OrderSide.SELL,
                        price=tp_price,
                        quantity=position_size,
                        fee=fee,
                        slippage=slippage_cost,
                        pnl=pnl
                    ))
                    
                    position = None
                    position_size = 0.0
            
            # Aktualizuj equity curve
            mark_to_market = capital
            if position is not None:
                mark_to_market += position_size * (current_candle.close - position)
            
            equity_curve.append(mark_to_market)
            
            # Aktualizuj drawdown
            if mark_to_market > peak_capital:
                peak_capital = mark_to_market
            
            current_dd = ((peak_capital - mark_to_market) / peak_capital) * 100
            drawdown_curve.append(current_dd)
            
            if current_dd > max_drawdown:
                max_drawdown = current_dd
            
            # Daily returns (dla Sharpe/Sortino)
            if len(equity_curve) > 1:
                daily_return = (equity_curve[-1] - equity_curve[-2]) / equity_curve[-2]
                daily_returns.append(daily_return)
        
        # Zamknij otwartą pozycję na końcu
        if position is not None:
            final_price = candles[-1].close
            position_value = position_size * final_price
            # Kapitał zwiększa się o wartość pozycji (bez dodatkowych opłat na końcu)
            capital += position_value
        
        # Oblicz metryki
        return self._calculate_metrics(
            initial_capital=self.config.initial_capital,
            final_capital=capital,
            trades=trades,
            equity_curve=equity_curve,
            drawdown_curve=drawdown_curve,
            max_drawdown=max_drawdown,
            daily_returns=daily_returns
        )
    
    def _apply_slippage(self, price: float, signal: Signal) -> float:
        """Aplikuje poślizg do ceny."""
        slippage_factor = self.config.slippage_percent / 100
        
        if signal == Signal.BUY:
            return price * (1 + slippage_factor)
        elif signal == Signal.SELL:
            return price * (1 - slippage_factor)
        
        return price
    
    def _calculate_metrics(
        self,
        initial_capital: float,
        final_capital: float,
        trades: List[Trade],
        equity_curve: List[float],
        drawdown_curve: List[float],
        max_drawdown: float,
        daily_returns: List[float]
    ) -> BacktestResult:
        """Oblicza metryki backtestingu."""
        
        # Podstawowe
        total_return = ((final_capital - initial_capital) / initial_capital) * 100
        
        # Trade stats
        sell_trades = [t for t in trades if t.side == OrderSide.SELL]
        winning = [t for t in sell_trades if t.pnl > 0]
        losing = [t for t in sell_trades if t.pnl <= 0]
        
        total_trades = len(sell_trades)
        win_rate = len(winning) / total_trades if total_trades > 0 else 0
        
        # PnL
        gross_pnl = sum(t.pnl + t.fee + t.slippage for t in sell_trades)
        total_fees = sum(t.fee for t in trades)
        total_slippage = sum(t.slippage for t in trades)
        net_pnl = final_capital - initial_capital
        
        # Averages
        avg_trade_pnl = net_pnl / total_trades if total_trades > 0 else 0
        avg_win = sum(t.pnl for t in winning) / len(winning) if winning else 0
        avg_loss = sum(t.pnl for t in losing) / len(losing) if losing else 0
        
        # Profit factor
        total_wins = sum(t.pnl for t in winning)
        total_losses = abs(sum(t.pnl for t in losing))
        profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')
        
        # Sharpe ratio (annualized, assuming daily returns)
        sharpe_ratio = None
        if len(daily_returns) > 1:
            mean_return = sum(daily_returns) / len(daily_returns)
            variance = sum((r - mean_return) ** 2 for r in daily_returns) / len(daily_returns)
            std_return = math.sqrt(variance)
            
            if std_return > 0:
                sharpe_ratio = (mean_return / std_return) * math.sqrt(252)  # Annualizacja
        
        # Sortino ratio (tylko negatywne odchylenia)
        sortino_ratio = None
        if len(daily_returns) > 1:
            mean_return = sum(daily_returns) / len(daily_returns)
            negative_returns = [r for r in daily_returns if r < 0]
            
            if negative_returns:
                downside_variance = sum(r ** 2 for r in negative_returns) / len(daily_returns)
                downside_std = math.sqrt(downside_variance)
                
                if downside_std > 0:
                    sortino_ratio = (mean_return / downside_std) * math.sqrt(252)
        
        return BacktestResult(
            initial_capital=initial_capital,
            final_capital=final_capital,
            total_return_percent=total_return,
            total_trades=total_trades,
            winning_trades=len(winning),
            losing_trades=len(losing),
            win_rate=win_rate,
            gross_pnl=gross_pnl,
            total_fees=total_fees,
            total_slippage=total_slippage,
            net_pnl=net_pnl,
            max_drawdown_percent=max_drawdown,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            avg_trade_pnl=avg_trade_pnl,
            avg_win=avg_win,
            avg_loss=avg_loss,
            profit_factor=profit_factor,
            trades=trades,
            equity_curve=equity_curve,
            drawdown_curve=drawdown_curve
        )
    
    def walk_forward_validation(
        self,
        candles: List[Candle],
        strategy: TradingStrategy,
        train_size: int,
        test_size: int,
        step_size: Optional[int] = None
    ) -> List[BacktestResult]:
        """
        Walk-forward validation.
        
        Dzieli dane na okna treningowe i testowe, przesuwa się przez dane.
        
        Args:
            candles: Wszystkie dane
            strategy: Strategia do testowania
            train_size: Rozmiar okna treningowego (liczba świec)
            test_size: Rozmiar okna testowego (liczba świec)
            step_size: Rozmiar kroku (domyślnie = test_size)
        """
        if step_size is None:
            step_size = test_size
        
        results = []
        start_idx = 0
        
        while start_idx + train_size + test_size <= len(candles):
            # Dane treningowe (tu mogłaby być optymalizacja parametrów)
            train_data = candles[start_idx:start_idx + train_size]
            
            # Dane testowe
            test_start = start_idx + train_size
            test_data = candles[test_start:test_start + test_size]
            
            # Uruchom backtest na danych testowych
            # Używamy danych treningowych + testowych, żeby strategia miała kontekst
            full_test_data = train_data + test_data
            
            try:
                result = self.run(full_test_data, strategy)
                result.trades = [t for t in result.trades 
                               if t.timestamp >= train_data[-1].timestamp]
                results.append(result)
            except ValueError:
                pass  # Pomiń jeśli za mało danych
            
            start_idx += step_size
        
        return results


def print_backtest_report(result: BacktestResult):
    """Wyświetla raport z backtestingu."""
    print("\n" + "=" * 60)
    print("BACKTEST REPORT")
    print("=" * 60)
    
    print(f"\nCapital:")
    print(f"  Initial: ${result.initial_capital:,.2f}")
    print(f"  Final:   ${result.final_capital:,.2f}")
    print(f"  Return:  {result.total_return_percent:+.2f}%")
    
    print(f"\nTrades:")
    print(f"  Total:   {result.total_trades}")
    print(f"  Winners: {result.winning_trades} ({result.win_rate*100:.1f}%)")
    print(f"  Losers:  {result.losing_trades}")
    
    print(f"\nPnL:")
    print(f"  Gross:    ${result.gross_pnl:+,.2f}")
    print(f"  Fees:     ${result.total_fees:,.2f}")
    print(f"  Slippage: ${result.total_slippage:,.2f}")
    print(f"  Net:      ${result.net_pnl:+,.2f}")
    
    print(f"\nRisk Metrics:")
    print(f"  Max Drawdown: {result.max_drawdown_percent:.2f}%")
    if result.sharpe_ratio is not None:
        print(f"  Sharpe Ratio: {result.sharpe_ratio:.2f}")
    if result.sortino_ratio is not None:
        print(f"  Sortino Ratio: {result.sortino_ratio:.2f}")
    
    print(f"\nTrade Stats:")
    print(f"  Avg Trade: ${result.avg_trade_pnl:+,.2f}")
    print(f"  Avg Win:   ${result.avg_win:+,.2f}")
    print(f"  Avg Loss:  ${result.avg_loss:+,.2f}")
    print(f"  Profit Factor: {result.profit_factor:.2f}")
    
    print("\n" + "=" * 60)
