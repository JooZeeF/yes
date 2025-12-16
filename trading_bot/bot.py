"""
Główny moduł bota do tradingu.
"""

import logging
from typing import List, Optional

from .config import TradingConfig
from .strategy import Candle, Signal, TradingStrategy

# Konfiguracja loggera
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TradingBot:
    """
    Bot do tradingu.
    
    Obsługuje analizę rynku przy użyciu strategii tradingowych
    i zarządza pozycjami.
    """
    
    def __init__(self, config: TradingConfig, strategy: TradingStrategy):
        """
        Inicjalizuje bota.
        
        Args:
            config: Konfiguracja bota
            strategy: Strategia tradingowa do użycia
        """
        self.config = config
        self.strategy = strategy
        self.position: Optional[float] = None  # Aktualna pozycja (cena wejścia)
        self.balance: float = 10000.0  # Początkowy kapitał (w trybie dry_run)
        
        logger.info(f"Bot zainicjalizowany ze strategią: {strategy.name}")
        logger.info(f"Symbol: {config.symbol}, Timeframe: {config.timeframe}")
        logger.info(f"Tryb dry_run: {config.dry_run}")
    
    def process_candles(self, candles: List[Candle]) -> Optional[str]:
        """
        Przetwarza dane rynkowe i podejmuje decyzję tradingową.
        
        Args:
            candles: Lista świec OHLCV
            
        Returns:
            Opis wykonanej akcji lub None jeśli brak akcji
        """
        if not candles:
            logger.warning("Brak danych do analizy")
            return None
        
        current_price = candles[-1].close
        signal = self.strategy.analyze(candles)
        
        logger.info(f"Cena: {current_price}, Sygnał: {signal.value}")
        
        if signal == Signal.BUY and self.position is None:
            return self._open_position(current_price)
        elif signal == Signal.SELL and self.position is not None:
            return self._close_position(current_price)
        elif self.position is not None:
            return self._check_stop_loss_take_profit(current_price)
        
        return None
    
    def _open_position(self, price: float) -> str:
        """Otwiera pozycję long."""
        position_value = self.balance * self.config.max_position_size
        
        if self.config.dry_run:
            self.position = price
            logger.info(f"[DRY RUN] Otwarcie pozycji LONG @ {price}")
            return f"Otwarto pozycję LONG @ {price} (wartość: {position_value:.2f})"
        
        # Tu byłaby integracja z API giełdy
        self.position = price
        return f"Otwarto pozycję LONG @ {price}"
    
    def _close_position(self, price: float) -> str:
        """Zamyka pozycję."""
        if self.position is None:
            return "Brak otwartej pozycji"
        
        profit_percent = ((price - self.position) / self.position) * 100
        
        if self.config.dry_run:
            profit = self.balance * self.config.max_position_size * (profit_percent / 100)
            self.balance += profit
            entry_price = self.position
            self.position = None
            logger.info(f"[DRY RUN] Zamknięcie pozycji @ {price}, zysk: {profit_percent:.2f}%")
            return f"Zamknięto pozycję (wejście: {entry_price}, wyjście: {price}, zysk: {profit_percent:.2f}%)"
        
        # Tu byłaby integracja z API giełdy
        entry_price = self.position
        self.position = None
        return f"Zamknięto pozycję (wejście: {entry_price}, wyjście: {price})"
    
    def _check_stop_loss_take_profit(self, current_price: float) -> Optional[str]:
        """Sprawdza warunki stop loss i take profit."""
        if self.position is None:
            return None
        
        price_change_percent = ((current_price - self.position) / self.position) * 100
        
        if price_change_percent <= -self.config.stop_loss_percent:
            logger.info("Stop loss triggered!")
            return self._close_position(current_price)
        elif price_change_percent >= self.config.take_profit_percent:
            logger.info("Take profit triggered!")
            return self._close_position(current_price)
        
        return None
    
    def get_status(self) -> dict:
        """Zwraca aktualny status bota."""
        return {
            "strategy": self.strategy.name,
            "symbol": self.config.symbol,
            "timeframe": self.config.timeframe,
            "position": self.position,
            "balance": self.balance,
            "dry_run": self.config.dry_run,
        }
