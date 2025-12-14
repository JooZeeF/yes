"""
Trading Bot - Profesjonalny bot do tradingu w Pythonie.

Moduły:
- bot: Główna logika bota
- config: Konfiguracja
- strategy: Strategie tradingowe (SMA, EMA, BB, RSI, MACD, Donchian, ADX, Volume)
- indicators: Wskaźniki analizy technicznej (ADX, SuperTrend, OBV, Keltner)
- guards: Guardy i filtry bezpieczeństwa
- validation: Walidacja danych
- backtest: Backtesting z kosztami
"""

__version__ = "0.3.0"

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
    ADXTrendStrategy,
    VolumeBreakoutStrategy,
    MeanReversionZScoreStrategy,
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
    "ADXTrendStrategy",
    "VolumeBreakoutStrategy",
    "MeanReversionZScoreStrategy",
    "TradingConfig",
    "TradingBot",
]