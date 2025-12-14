# Trading Bot

Profesjonalny bot do tradingu w Pythonie z obsługą strategii opartych na analizie technicznej, guardami bezpieczeństwa i backtestingiem.

## Funkcje

### Strategie tradingowe
- 📈 **SMA** - Simple Moving Average crossover
- 📊 **EMA** - Exponential Moving Average crossover
- 📉 **Bollinger Bands** - Mean reversion strategy
- 🔄 **RSI** - Relative Strength Index (oversold/overbought)
- 📐 **MACD** - Moving Average Convergence Divergence
- 🚀 **Donchian Breakout** - Channel breakout strategy

### Wskaźniki techniczne
- SMA, EMA (proste i wykładnicze średnie)
- Bollinger Bands (pasma zmienności)
- ATR (Average True Range)
- RSI (Relative Strength Index)
- MACD (Moving Average Convergence Divergence)
- Donchian Channel
- VWAP (Volume Weighted Average Price)
- Z-score, percentyle zmienności

### Guardy i filtry bezpieczeństwa
- 🛡️ **Spread Guard** - Blokuje trading przy zbyt szerokim spreadzie
- 📚 **Depth Guard** - Sprawdza głębokość order book
- ⏰ **Clock Drift Guard** - Monitoruje opóźnienia danych
- 📏 **Price Band Guard** - Limituje zakres cen
- 📉 **Daily Drawdown Guard** - Kontroluje dzienny drawdown
- 💰 **Cost-Aware Filter** - Uwzględnia koszty transakcji
- 🌡️ **Volatility Regime Filter** - Filtruje na podstawie zmienności

### Walidacja danych
- Wykrywanie luk czasowych (gaps)
- Wykrywanie anomalii cen/wolumenu (Z-score)
- Walidacja crossed/locked book
- Monitor zdrowia feeda danych

### Backtesting
- Symulacja z kosztami transakcji (maker/taker fees)
- Modelowanie poślizgu (slippage)
- Walk-forward validation
- Metryki: Sharpe Ratio, Sortino Ratio, Max Drawdown
- Equity curve i drawdown curve

## Instalacja

```bash
git clone <repo-url>
cd trading-bot
pip install -r requirements.txt
```

## Użycie

### Demo
```bash
python main.py
```

### Programowe użycie

```python
from trading_bot import (
    TradingBot,
    TradingConfig,
    SimpleMovingAverageStrategy,
    EMAStrategy,
    BollingerBandsStrategy,
    RSIStrategy,
)

# Konfiguracja
config = TradingConfig(
    symbol="BTC/USDT",
    timeframe="1h",
    stop_loss_percent=2.0,
    take_profit_percent=4.0,
    dry_run=True
)

# Wybierz strategię
strategy = EMAStrategy(fast_period=9, slow_period=21)

# Inicjalizacja bota
bot = TradingBot(config=config, strategy=strategy)

# Przetwarzanie danych
result = bot.process_candles(candles)
```

### Backtesting

```python
from trading_bot.backtest import Backtester, BacktestConfig, print_backtest_report
from trading_bot.strategy import RSIStrategy

# Konfiguracja backtestingu
bt_config = BacktestConfig(
    initial_capital=10000.0,
    maker_fee_percent=0.01,
    taker_fee_percent=0.05,
    slippage_percent=0.02,
    stop_loss_percent=2.0,
    take_profit_percent=4.0,
)

# Uruchom backtest
backtester = Backtester(bt_config)
strategy = RSIStrategy(period=14, oversold_level=30, overbought_level=70)
result = backtester.run(candles, strategy)

# Wyświetl raport
print_backtest_report(result)
```

### Guardy bezpieczeństwa

```python
from trading_bot.guards import GuardManager, GuardConfig, MarketData

# Konfiguracja guardów
guard_config = GuardConfig(
    max_spread_bps=10.0,
    min_bid_depth=1.0,
    max_daily_drawdown_percent=5.0,
)

# Manager guardów
manager = GuardManager(guard_config)

# Sprawdź warunki
market_data = MarketData(bid=100, ask=100.05, ...)
results = manager.check_market_data(market_data)

if manager.is_trading_allowed(results):
    # Wykonaj trade
    pass
```

## Struktura projektu

```
trading_bot/
├── __init__.py    # Pakiet główny
├── bot.py         # Logika bota
├── config.py      # Konfiguracja
├── strategy.py    # Strategie tradingowe (SMA, EMA, BB, RSI, MACD, Donchian)
├── indicators.py  # Wskaźniki analizy technicznej
├── guards.py      # Guardy i filtry bezpieczeństwa
├── validation.py  # Walidacja danych
└── backtest.py    # Backtesting
tests/
├── test_bot.py        # Testy bota
├── test_strategy.py   # Testy strategii
├── test_indicators.py # Testy wskaźników
├── test_guards.py     # Testy guardów
├── test_validation.py # Testy walidacji
└── test_backtest.py   # Testy backtestingu
main.py            # Punkt wejścia
requirements.txt   # Zależności
```

## Testy

```bash
python -m unittest discover tests/ -v
```

## Checklist profesjonalnego tradingu

### A. Dane i higiena
- ✅ Walidacja luk czasowych (sequence gaps)
- ✅ Monitor drift zegara (ts_exch vs ts_recv)
- ✅ Wykrywanie anomalii cen/wolumenu (Z-score)
- ✅ Spread/depth guard

### B. Strategie
- ✅ Trend/momentum: SMA, EMA, MACD
- ✅ Mean reversion: Bollinger Bands, RSI
- ✅ Breakout: Donchian Channel
- ✅ Wskaźniki vol: ATR, percentyle zmienności

### C. Filtry i guardy
- ✅ Volatility regime filter
- ✅ Spread/depth guard w każdym sygnale
- ✅ Cost-aware filter (edge > fees + slip)
- ✅ Lookahead off: sygnały shift(1)

### D. Walidacja
- ✅ Backtest z kosztami
- ✅ Walk-forward validation
- ✅ Metryki: PnL, Sharpe, Sortino, max DD

### E. Risk management
- ✅ Daily drawdown guard
- ✅ Price band guard
- ✅ Position sizing

## Ostrzeżenie

⚠️ **Ten bot jest przeznaczony wyłącznie do celów edukacyjnych.** Handel kryptowalutami wiąże się z wysokim ryzykiem. Nie używaj tego bota z prawdziwymi środkami bez dokładnego zrozumienia jego działania i związanego z tym ryzyka.

## Developer

This project is developed for demo and educational purposes.
