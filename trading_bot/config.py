"""
Moduł konfiguracji bota do tradingu.
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class TradingConfig:
    """Konfiguracja bota do tradingu."""
    
    # Ustawienia API giełdy
    api_key: str = ""
    api_secret: str = ""
    
    # Ustawienia tradingowe
    symbol: str = "BTC/USDT"
    timeframe: str = "1h"
    
    # Parametry zarządzania ryzykiem
    max_position_size: float = 0.1  # Maksymalny rozmiar pozycji jako % kapitału
    stop_loss_percent: float = 2.0  # Stop loss w procentach
    take_profit_percent: float = 4.0  # Take profit w procentach
    
    # Tryb testowy
    dry_run: bool = True  # Gdy True, nie wykonuje prawdziwych transakcji
    
    @classmethod
    def from_env(cls) -> "TradingConfig":
        """Tworzy konfigurację z zmiennych środowiskowych."""
        try:
            max_position = float(os.getenv("TRADING_MAX_POSITION", "0.1"))
            stop_loss = float(os.getenv("TRADING_STOP_LOSS", "2.0"))
            take_profit = float(os.getenv("TRADING_TAKE_PROFIT", "4.0"))
        except ValueError:
            # Użyj wartości domyślnych jeśli zmienne środowiskowe są nieprawidłowe
            max_position = 0.1
            stop_loss = 2.0
            take_profit = 4.0
        
        return cls(
            api_key=os.getenv("TRADING_API_KEY", ""),
            api_secret=os.getenv("TRADING_API_SECRET", ""),
            symbol=os.getenv("TRADING_SYMBOL", "BTC/USDT"),
            timeframe=os.getenv("TRADING_TIMEFRAME", "1h"),
            max_position_size=max_position,
            stop_loss_percent=stop_loss,
            take_profit_percent=take_profit,
            dry_run=os.getenv("TRADING_DRY_RUN", "true").lower() == "true",
        )
