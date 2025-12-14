"""
Moduł strategii tradingowych.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional


class Signal(Enum):
    """Sygnał tradingowy."""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


@dataclass
class Candle:
    """Reprezentacja świecy (OHLCV)."""
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float


class TradingStrategy(ABC):
    """Abstrakcyjna klasa bazowa dla strategii tradingowych."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Nazwa strategii."""
        pass
    
    @abstractmethod
    def analyze(self, candles: List[Candle]) -> Signal:
        """
        Analizuje dane rynkowe i zwraca sygnał tradingowy.
        
        Args:
            candles: Lista świec OHLCV
            
        Returns:
            Sygnał tradingowy (BUY, SELL lub HOLD)
        """
        pass


class SimpleMovingAverageStrategy(TradingStrategy):
    """
    Prosta strategia oparta na przecięciu średnich kroczących (SMA).
    
    Generuje sygnał BUY gdy krótka SMA przecina długą SMA od dołu.
    Generuje sygnał SELL gdy krótka SMA przecina długą SMA od góry.
    """
    
    def __init__(self, short_period: int = 10, long_period: int = 20):
        """
        Inicjalizuje strategię SMA.
        
        Args:
            short_period: Okres krótkiej średniej kroczącej
            long_period: Okres długiej średniej kroczącej
        """
        if short_period <= 0 or long_period <= 0:
            raise ValueError("Okresy muszą być dodatnimi liczbami całkowitymi")
        if short_period >= long_period:
            raise ValueError("short_period musi być mniejszy niż long_period")
        self.short_period = short_period
        self.long_period = long_period
    
    @property
    def name(self) -> str:
        return f"SMA_{self.short_period}_{self.long_period}"
    
    def _calculate_sma(self, candles: List[Candle], period: int) -> Optional[float]:
        """Oblicza prostą średnią kroczącą."""
        if len(candles) < period:
            return None
        closes = [c.close for c in candles[-period:]]
        return sum(closes) / period
    
    def analyze(self, candles: List[Candle]) -> Signal:
        """Analizuje dane i zwraca sygnał na podstawie przecięcia SMA."""
        if len(candles) < self.long_period + 1:
            return Signal.HOLD
        
        # Bieżące wartości SMA
        current_short_sma = self._calculate_sma(candles, self.short_period)
        current_long_sma = self._calculate_sma(candles, self.long_period)
        
        # Poprzednie wartości SMA (bez ostatniej świecy)
        prev_short_sma = self._calculate_sma(candles[:-1], self.short_period)
        prev_long_sma = self._calculate_sma(candles[:-1], self.long_period)
        
        if None in (current_short_sma, current_long_sma, prev_short_sma, prev_long_sma):
            return Signal.HOLD
        
        # Sprawdzenie przecięcia
        if prev_short_sma <= prev_long_sma and current_short_sma > current_long_sma:
            return Signal.BUY
        elif prev_short_sma >= prev_long_sma and current_short_sma < current_long_sma:
            return Signal.SELL
        
        return Signal.HOLD
