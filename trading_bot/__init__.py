"""
Trading Bot - Profesjonalny bot do tradingu w Pythonie.

Moduły:
- bot: Główna logika bota
- config: Konfiguracja
- strategy: Strategie tradingowe (SMA, EMA, BB, RSI, MACD, Donchian)
- indicators: Wskaźniki analizy technicznej
- guards: Guardy i filtry bezpieczeństwa
- validation: Walidacja danych
- backtest: Backtesting z kosztami
"""

__version__ = "0.2.0"

from .strategy import (
    Signal,
    Candle,
    TradingStrategy,
    SimpleMovingAverageStrategy,
    EMAStrategy,
    BollingerBandsStrategy,
    RSIStrategy,
    DonchianBreakoutStrategy,
    MACDStrategy,
)

from .config import TradingConfig
from .bot import TradingBot

__all__ = [
    "Signal",
    "Candle",
    "TradingStrategy",
    "SimpleMovingAverageStrategy",
    "EMAStrategy",
    "BollingerBandsStrategy",
    "RSIStrategy",
    "DonchianBreakoutStrategy",
    "MACDStrategy",
    "TradingConfig",
    "TradingBot",
]

