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


class EMAStrategy(TradingStrategy):
    """
    Strategia oparta na przecięciu EMA (Exponential Moving Average).
    
    Bardziej responsywna niż SMA, daje większą wagę niedawnym cenom.
    """
    
    def __init__(self, fast_period: int = 9, slow_period: int = 21):
        if fast_period <= 0 or slow_period <= 0:
            raise ValueError("Okresy muszą być dodatnimi liczbami całkowitymi")
        if fast_period >= slow_period:
            raise ValueError("fast_period musi być mniejszy niż slow_period")
        self.fast_period = fast_period
        self.slow_period = slow_period
    
    @property
    def name(self) -> str:
        return f"EMA_{self.fast_period}_{self.slow_period}"
    
    def _calculate_ema(self, prices: List[float], period: int) -> Optional[float]:
        """Oblicza EMA."""
        if len(prices) < period:
            return None
        
        k = 2 / (period + 1)
        ema = sum(prices[:period]) / period
        
        for price in prices[period:]:
            ema = price * k + ema * (1 - k)
        
        return ema
    
    def analyze(self, candles: List[Candle]) -> Signal:
        if len(candles) < self.slow_period + 1:
            return Signal.HOLD
        
        closes = [c.close for c in candles]
        
        current_fast = self._calculate_ema(closes, self.fast_period)
        current_slow = self._calculate_ema(closes, self.slow_period)
        
        prev_fast = self._calculate_ema(closes[:-1], self.fast_period)
        prev_slow = self._calculate_ema(closes[:-1], self.slow_period)
        
        if None in (current_fast, current_slow, prev_fast, prev_slow):
            return Signal.HOLD
        
        if prev_fast <= prev_slow and current_fast > current_slow:
            return Signal.BUY
        elif prev_fast >= prev_slow and current_fast < current_slow:
            return Signal.SELL
        
        return Signal.HOLD


class BollingerBandsStrategy(TradingStrategy):
    """
    Strategia mean reversion oparta na Bollinger Bands.
    
    BUY gdy cena spadnie poniżej dolnej wstęgi (oversold).
    SELL gdy cena wzrośnie powyżej górnej wstęgi (overbought).
    """
    
    def __init__(self, period: int = 20, num_std: float = 2.0):
        if period <= 0:
            raise ValueError("Period musi być dodatnią liczbą całkowitą")
        if num_std <= 0:
            raise ValueError("num_std musi być dodatni")
        self.period = period
        self.num_std = num_std
    
    @property
    def name(self) -> str:
        return f"BB_{self.period}_{self.num_std}"
    
    def analyze(self, candles: List[Candle]) -> Signal:
        if len(candles) < self.period:
            return Signal.HOLD
        
        closes = [c.close for c in candles[-self.period:]]
        current_price = candles[-1].close
        
        # Oblicz SMA i odchylenie standardowe
        sma = sum(closes) / self.period
        variance = sum((x - sma) ** 2 for x in closes) / self.period
        std = variance ** 0.5
        
        upper_band = sma + (self.num_std * std)
        lower_band = sma - (self.num_std * std)
        
        # Mean reversion signals
        if current_price < lower_band:
            return Signal.BUY
        elif current_price > upper_band:
            return Signal.SELL
        
        return Signal.HOLD


class RSIStrategy(TradingStrategy):
    """
    Strategia oparta na RSI (Relative Strength Index).
    
    BUY gdy RSI < oversold_level (domyślnie 30).
    SELL gdy RSI > overbought_level (domyślnie 70).
    """
    
    def __init__(
        self,
        period: int = 14,
        oversold_level: float = 30.0,
        overbought_level: float = 70.0
    ):
        if period <= 0:
            raise ValueError("Period musi być dodatnią liczbą całkowitą")
        if not (0 < oversold_level < overbought_level < 100):
            raise ValueError("Poziomy RSI muszą być: 0 < oversold < overbought < 100")
        
        self.period = period
        self.oversold_level = oversold_level
        self.overbought_level = overbought_level
    
    @property
    def name(self) -> str:
        return f"RSI_{self.period}_{int(self.oversold_level)}_{int(self.overbought_level)}"
    
    def _calculate_rsi(self, candles: List[Candle]) -> Optional[float]:
        if len(candles) < self.period + 1:
            return None
        
        gains = []
        losses = []
        
        for i in range(1, len(candles)):
            change = candles[i].close - candles[i-1].close
            if change >= 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        avg_gain = sum(gains[-self.period:]) / self.period
        avg_loss = sum(losses[-self.period:]) / self.period
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
    
    def analyze(self, candles: List[Candle]) -> Signal:
        rsi = self._calculate_rsi(candles)
        
        if rsi is None:
            return Signal.HOLD
        
        if rsi < self.oversold_level:
            return Signal.BUY
        elif rsi > self.overbought_level:
            return Signal.SELL
        
        return Signal.HOLD


class DonchianBreakoutStrategy(TradingStrategy):
    """
    Strategia breakout oparta na Donchian Channel.
    
    BUY gdy cena przebije górną granicę kanału.
    SELL gdy cena przebije dolną granicę kanału.
    """
    
    def __init__(self, period: int = 20):
        if period <= 0:
            raise ValueError("Period musi być dodatnią liczbą całkowitą")
        self.period = period
    
    @property
    def name(self) -> str:
        return f"Donchian_{self.period}"
    
    def analyze(self, candles: List[Candle]) -> Signal:
        if len(candles) < self.period + 1:
            return Signal.HOLD
        
        # Kanał z poprzednich świec (bez aktualnej)
        lookback = candles[-(self.period + 1):-1]
        upper = max(c.high for c in lookback)
        lower = min(c.low for c in lookback)
        
        current_price = candles[-1].close
        
        # Breakout
        if current_price > upper:
            return Signal.BUY
        elif current_price < lower:
            return Signal.SELL
        
        return Signal.HOLD


class MACDStrategy(TradingStrategy):
    """
    Strategia oparta na MACD (Moving Average Convergence Divergence).
    
    BUY gdy MACD line przecina signal line od dołu.
    SELL gdy MACD line przecina signal line od góry.
    """
    
    def __init__(
        self,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9
    ):
        if any(p <= 0 for p in [fast_period, slow_period, signal_period]):
            raise ValueError("Wszystkie okresy muszą być dodatnimi liczbami całkowitymi")
        if fast_period >= slow_period:
            raise ValueError("fast_period musi być mniejszy niż slow_period")
        
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period
    
    @property
    def name(self) -> str:
        return f"MACD_{self.fast_period}_{self.slow_period}_{self.signal_period}"
    
    def _calculate_ema(self, prices: List[float], period: int) -> Optional[float]:
        if len(prices) < period:
            return None
        
        k = 2 / (period + 1)
        ema = sum(prices[:period]) / period
        
        for price in prices[period:]:
            ema = price * k + ema * (1 - k)
        
        return ema
    
    def _calculate_macd(self, candles: List[Candle]) -> Optional[tuple]:
        """Zwraca (macd_line, signal_line) lub None."""
        if len(candles) < self.slow_period + self.signal_period:
            return None
        
        closes = [c.close for c in candles]
        
        # Oblicz serię MACD line
        macd_series = []
        for i in range(self.slow_period, len(closes) + 1):
            subset = closes[:i]
            fast_ema = self._calculate_ema(subset, self.fast_period)
            slow_ema = self._calculate_ema(subset, self.slow_period)
            if fast_ema and slow_ema:
                macd_series.append(fast_ema - slow_ema)
        
        if len(macd_series) < self.signal_period:
            return None
        
        signal_line = self._calculate_ema(macd_series, self.signal_period)
        macd_line = macd_series[-1]
        
        return (macd_line, signal_line)
    
    def analyze(self, candles: List[Candle]) -> Signal:
        current = self._calculate_macd(candles)
        prev = self._calculate_macd(candles[:-1])
        
        if current is None or prev is None:
            return Signal.HOLD
        
        macd_now, signal_now = current
        macd_prev, signal_prev = prev
        
        # Crossover detection
        if macd_prev <= signal_prev and macd_now > signal_now:
            return Signal.BUY
        elif macd_prev >= signal_prev and macd_now < signal_now:
            return Signal.SELL
        
        return Signal.HOLD


class ADXTrendStrategy(TradingStrategy):
    """
    EMA + ADX strategy (trend with strength filter).
    
    BUY when EMA fast > EMA slow + ADX > threshold.
    SELL when EMA fast < EMA slow + ADX > threshold.
    HOLD when ADX < threshold (no clear trend).
    """
    
    def __init__(
        self,
        ema_fast: int = 9,
        ema_slow: int = 21,
        adx_period: int = 14,
        adx_threshold: float = 20.0
    ):
        if ema_fast <= 0 or ema_slow <= 0 or adx_period <= 0:
            raise ValueError("All periods must be positive integers")
        if ema_fast >= ema_slow:
            raise ValueError("ema_fast must be less than ema_slow")
        if adx_threshold <= 0:
            raise ValueError("adx_threshold must be positive")
        
        self.ema_fast = ema_fast
        self.ema_slow = ema_slow
        self.adx_period = adx_period
        self.adx_threshold = adx_threshold
    
    @property
    def name(self) -> str:
        return f"ADXTrend_{self.ema_fast}_{self.ema_slow}_{self.adx_period}"
    
    def _calculate_ema(self, prices: List[float], period: int) -> Optional[float]:
        if len(prices) < period:
            return None
        
        k = 2 / (period + 1)
        ema = sum(prices[:period]) / period
        
        for price in prices[period:]:
            ema = price * k + ema * (1 - k)
        
        return ema
    
    def _calculate_adx(self, candles: List[Candle]) -> Optional[float]:
        """Calculates ADX (simplified DX-based approximation)."""
        if len(candles) < self.adx_period * 2:
            return None
        
        plus_dm_list = []
        minus_dm_list = []
        tr_list = []
        
        for i in range(1, len(candles)):
            high = candles[i].high
            low = candles[i].low
            prev_high = candles[i-1].high
            prev_low = candles[i-1].low
            prev_close = candles[i-1].close
            
            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            tr_list.append(tr)
            
            plus_dm = max(high - prev_high, 0) if (high - prev_high) > (prev_low - low) else 0
            minus_dm = max(prev_low - low, 0) if (prev_low - low) > (high - prev_high) else 0
            
            plus_dm_list.append(plus_dm)
            minus_dm_list.append(minus_dm)
        
        if len(tr_list) < self.adx_period:
            return None
        
        # Simple sum over period (simplified calculation)
        smoothed_tr = sum(tr_list[-self.adx_period:])
        smoothed_plus = sum(plus_dm_list[-self.adx_period:])
        smoothed_minus = sum(minus_dm_list[-self.adx_period:])
        
        if smoothed_tr == 0:
            return None
        
        plus_di = (smoothed_plus / smoothed_tr) * 100
        minus_di = (smoothed_minus / smoothed_tr) * 100
        
        di_sum = plus_di + minus_di
        if di_sum == 0:
            return None
        
        # DX (used as simplified ADX indicator)
        dx = abs(plus_di - minus_di) / di_sum * 100
        return dx
    
    def analyze(self, candles: List[Candle]) -> Signal:
        if len(candles) < max(self.ema_slow, self.adx_period * 2) + 1:
            return Signal.HOLD
        
        closes = [c.close for c in candles]
        
        ema_fast_val = self._calculate_ema(closes, self.ema_fast)
        ema_slow_val = self._calculate_ema(closes, self.ema_slow)
        adx = self._calculate_adx(candles)
        
        if None in (ema_fast_val, ema_slow_val, adx):
            return Signal.HOLD
        
        # ADX filter - sygnały tylko przy silnym trendzie
        if adx < self.adx_threshold:
            return Signal.HOLD
        
        if ema_fast_val > ema_slow_val:
            return Signal.BUY
        elif ema_fast_val < ema_slow_val:
            return Signal.SELL
        
        return Signal.HOLD


class VolumeBreakoutStrategy(TradingStrategy):
    """
    Strategia Donchian Breakout z potwierdzeniem wolumenem.
    
    BUY gdy cena przebije górną granicę + Volume spike > p90.
    SELL gdy cena przebije dolną granicę + Volume spike > p90.
    """
    
    def __init__(
        self,
        donchian_period: int = 20,
        volume_lookback: int = 20,
        volume_percentile: float = 90.0
    ):
        if donchian_period <= 0 or volume_lookback <= 0:
            raise ValueError("Okresy muszą być dodatnimi liczbami całkowitymi")
        if not (0 < volume_percentile <= 100):
            raise ValueError("volume_percentile musi być w zakresie (0, 100]")
        
        self.donchian_period = donchian_period
        self.volume_lookback = volume_lookback
        self.volume_percentile = volume_percentile
    
    @property
    def name(self) -> str:
        return f"VolumeBreakout_{self.donchian_period}_{int(self.volume_percentile)}"
    
    def _check_volume_spike(self, candles: List[Candle]) -> bool:
        if len(candles) < self.volume_lookback:
            return False
        
        volumes = [c.volume for c in candles[-self.volume_lookback:]]
        current_volume = candles[-1].volume
        
        count_below = sum(1 for v in volumes[:-1] if v < current_volume)
        percentile = (count_below / (len(volumes) - 1)) * 100
        
        return percentile >= self.volume_percentile
    
    def analyze(self, candles: List[Candle]) -> Signal:
        if len(candles) < max(self.donchian_period + 1, self.volume_lookback):
            return Signal.HOLD
        
        # Donchian channel z poprzednich świec
        lookback = candles[-(self.donchian_period + 1):-1]
        upper = max(c.high for c in lookback)
        lower = min(c.low for c in lookback)
        
        current_price = candles[-1].close
        has_volume_spike = self._check_volume_spike(candles)
        
        # Breakout z potwierdzeniem wolumenem
        if current_price > upper and has_volume_spike:
            return Signal.BUY
        elif current_price < lower and has_volume_spike:
            return Signal.SELL
        
        return Signal.HOLD


class MeanReversionZScoreStrategy(TradingStrategy):
    """
    Strategia mean reversion oparta na Z-score.
    
    BUY gdy z-score < -entry_threshold (oversold).
    SELL gdy z-score > entry_threshold (overbought).
    Opcjonalny filtr spread/vol.
    """
    
    def __init__(
        self,
        period: int = 20,
        entry_threshold: float = 2.0,
        exit_threshold: float = 0.0
    ):
        if period <= 0:
            raise ValueError("Period musi być dodatnią liczbą całkowitą")
        if entry_threshold <= 0:
            raise ValueError("entry_threshold musi być dodatni")
        
        self.period = period
        self.entry_threshold = entry_threshold
        self.exit_threshold = exit_threshold
    
    @property
    def name(self) -> str:
        return f"MRZScore_{self.period}_{self.entry_threshold}"
    
    def _calculate_zscore(self, candles: List[Candle]) -> Optional[float]:
        if len(candles) < self.period:
            return None
        
        closes = [c.close for c in candles[-self.period:]]
        mean = sum(closes) / self.period
        variance = sum((x - mean) ** 2 for x in closes) / self.period
        std = variance ** 0.5
        
        if std == 0:
            return 0.0
        
        current_price = candles[-1].close
        return (current_price - mean) / std
    
    def analyze(self, candles: List[Candle]) -> Signal:
        z_score = self._calculate_zscore(candles)
        
        if z_score is None:
            return Signal.HOLD
        
        if z_score < -self.entry_threshold:
            return Signal.BUY  # Oversold
        elif z_score > self.entry_threshold:
            return Signal.SELL  # Overbought
        
        return Signal.HOLD
