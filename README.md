# Trading Bot

Bot do tradingu w Pythonie z obsługą strategii opartych na analizie technicznej.

## Funkcje

- 📈 Strategie oparte na średnich kroczących (SMA)
- ⚙️ Konfigurowalne parametry zarządzania ryzykiem (stop loss, take profit)
- 🔄 Tryb dry-run do testowania bez prawdziwych transakcji
- 📊 Obsługa danych OHLCV (Open, High, Low, Close, Volume)
- 🧪 Testy jednostkowe

## Instalacja

```bash
git clone <repo-url>
cd trading-bot
pip install -r requirements.txt
```

## Użycie

```bash
python main.py
```

### Konfiguracja

Bot można skonfigurować przez zmienne środowiskowe:

```bash
export TRADING_API_KEY="twój_klucz_api"
export TRADING_API_SECRET="twój_sekret_api"
export TRADING_SYMBOL="BTC/USDT"
export TRADING_TIMEFRAME="1h"
export TRADING_DRY_RUN="true"
```

### Programowe użycie

```python
from trading_bot.bot import TradingBot
from trading_bot.config import TradingConfig
from trading_bot.strategy import SimpleMovingAverageStrategy

# Konfiguracja
config = TradingConfig(
    symbol="BTC/USDT",
    timeframe="1h",
    stop_loss_percent=2.0,
    take_profit_percent=4.0,
    dry_run=True
)

# Strategia SMA
strategy = SimpleMovingAverageStrategy(short_period=10, long_period=20)

# Inicjalizacja bota
bot = TradingBot(config=config, strategy=strategy)

# Przetwarzanie danych
result = bot.process_candles(candles)
```

## Struktura projektu

```
trading_bot/
├── __init__.py    # Pakiet główny
├── bot.py         # Logika bota
├── config.py      # Konfiguracja
└── strategy.py    # Strategie tradingowe
tests/
├── test_bot.py      # Testy bota
└── test_strategy.py # Testy strategii
main.py            # Punkt wejścia
requirements.txt   # Zależności
```

## Testy

```bash
python -m unittest discover tests/ -v
```

## Ostrzeżenie

⚠️ **Ten bot jest przeznaczony wyłącznie do celów edukacyjnych.** Handel kryptowalutami wiąże się z wysokim ryzykiem. Nie używaj tego bota z prawdziwymi środkami bez dokładnego zrozumienia jego działania i związanego z tym ryzyka.

## Developer

This project is developed for demo and educational purposes.
