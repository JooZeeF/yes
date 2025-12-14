"""
Moduł wskaźników analizy technicznej.

Zawiera implementacje popularnych wskaźników:
- EMA (Exponential Moving Average)
- Bollinger Bands
- ATR (Average True Range)
- RSI (Relative Strength Index)
- MACD
- Donchian Channel
- VWAP
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple
import math

from .strategy import Candle


@dataclass
class BollingerBands:
    """Wynik Bollinger Bands."""
    upper: float
    middle: float
    lower: float
    bandwidth: float  # (upper - lower) / middle
    percent_b: float  # (price - lower) / (upper - lower)


@dataclass
class MACDResult:
    """Wynik MACD."""
    macd_line: float
    signal_line: float
    histogram: float


@dataclass
class DonchianChannel:
    """Wynik Donchian Channel."""
    upper: float
    middle: float
    lower: float


def calculate_sma(prices: List[float], period: int) -> Optional[float]:
    """Oblicza prostą średnią kroczącą (SMA)."""
    if len(prices) < period:
        return None
    return sum(prices[-period:]) / period


def calculate_ema(prices: List[float], period: int) -> Optional[float]:
    """
    Oblicza wykładniczą średnią kroczącą (EMA).
    
    EMA = price * k + EMA_prev * (1 - k)
    gdzie k = 2 / (period + 1)
    """
    if len(prices) < period:
        return None
    
    k = 2 / (period + 1)
    
    # Inicjalizacja EMA jako SMA pierwszych 'period' wartości
    ema = sum(prices[:period]) / period
    
    # Obliczenie EMA dla pozostałych wartości
    for price in prices[period:]:
        ema = price * k + ema * (1 - k)
    
    return ema


def calculate_ema_series(prices: List[float], period: int) -> List[float]:
    """Oblicza serię EMA dla wszystkich możliwych punktów."""
    if len(prices) < period:
        return []
    
    k = 2 / (period + 1)
    ema_series = []
    
    # Pierwsza wartość EMA = SMA
    ema = sum(prices[:period]) / period
    ema_series.append(ema)
    
    for price in prices[period:]:
        ema = price * k + ema * (1 - k)
        ema_series.append(ema)
    
    return ema_series


def calculate_bollinger_bands(
    candles: List[Candle],
    period: int = 20,
    num_std: float = 2.0
) -> Optional[BollingerBands]:
    """
    Oblicza Bollinger Bands.
    
    Args:
        candles: Lista świec
        period: Okres SMA (domyślnie 20)
        num_std: Liczba odchyleń standardowych (domyślnie 2)
    """
    if len(candles) < period:
        return None
    
    closes = [c.close for c in candles[-period:]]
    middle = sum(closes) / period
    
    # Odchylenie standardowe
    variance = sum((x - middle) ** 2 for x in closes) / period
    std = math.sqrt(variance)
    
    upper = middle + (num_std * std)
    lower = middle - (num_std * std)
    
    current_price = candles[-1].close
    bandwidth = (upper - lower) / middle if middle > 0 else 0
    percent_b = (current_price - lower) / (upper - lower) if (upper - lower) > 0 else 0.5
    
    return BollingerBands(
        upper=upper,
        middle=middle,
        lower=lower,
        bandwidth=bandwidth,
        percent_b=percent_b
    )


def calculate_atr(candles: List[Candle], period: int = 14) -> Optional[float]:
    """
    Oblicza Average True Range (ATR).
    
    True Range = max(high - low, |high - prev_close|, |low - prev_close|)
    ATR = SMA(True Range, period)
    """
    if len(candles) < period + 1:
        return None
    
    true_ranges = []
    
    for i in range(1, len(candles)):
        high = candles[i].high
        low = candles[i].low
        prev_close = candles[i - 1].close
        
        tr = max(
            high - low,
            abs(high - prev_close),
            abs(low - prev_close)
        )
        true_ranges.append(tr)
    
    # Użyj ostatnich 'period' wartości TR
    return sum(true_ranges[-period:]) / period


def calculate_rsi(candles: List[Candle], period: int = 14) -> Optional[float]:
    """
    Oblicza Relative Strength Index (RSI).
    
    RSI = 100 - (100 / (1 + RS))
    RS = Average Gain / Average Loss
    """
    if len(candles) < period + 1:
        return None
    
    gains = []
    losses = []
    
    for i in range(1, len(candles)):
        change = candles[i].close - candles[i - 1].close
        if change >= 0:
            gains.append(change)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(change))
    
    # Użyj ostatnich 'period' wartości
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    
    if avg_loss == 0:
        return 100.0
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi


def calculate_macd(
    candles: List[Candle],
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9
) -> Optional[MACDResult]:
    """
    Oblicza MACD (Moving Average Convergence Divergence).
    
    MACD Line = EMA(fast) - EMA(slow)
    Signal Line = EMA(MACD Line, signal_period)
    Histogram = MACD Line - Signal Line
    """
    if len(candles) < slow_period + signal_period:
        return None
    
    closes = [c.close for c in candles]
    
    # Oblicz serię EMA fast i slow
    ema_fast_series = calculate_ema_series(closes, fast_period)
    ema_slow_series = calculate_ema_series(closes, slow_period)
    
    if not ema_fast_series or not ema_slow_series:
        return None
    
    # MACD line - potrzebujemy wyrównać serie
    # EMA slow zaczyna się później
    offset = slow_period - fast_period
    macd_line_series = []
    
    for i in range(len(ema_slow_series)):
        fast_idx = i + offset
        if fast_idx < len(ema_fast_series):
            macd_line_series.append(ema_fast_series[fast_idx] - ema_slow_series[i])
    
    if len(macd_line_series) < signal_period:
        return None
    
    # Signal line = EMA of MACD line
    signal_line = calculate_ema(macd_line_series, signal_period)
    
    if signal_line is None:
        return None
    
    macd_line = macd_line_series[-1]
    histogram = macd_line - signal_line
    
    return MACDResult(
        macd_line=macd_line,
        signal_line=signal_line,
        histogram=histogram
    )


def calculate_donchian_channel(
    candles: List[Candle],
    period: int = 20
) -> Optional[DonchianChannel]:
    """
    Oblicza Donchian Channel.
    
    Upper = Highest High over period
    Lower = Lowest Low over period
    Middle = (Upper + Lower) / 2
    """
    if len(candles) < period:
        return None
    
    recent_candles = candles[-period:]
    upper = max(c.high for c in recent_candles)
    lower = min(c.low for c in recent_candles)
    middle = (upper + lower) / 2
    
    return DonchianChannel(upper=upper, middle=middle, lower=lower)


def calculate_vwap(candles: List[Candle]) -> Optional[float]:
    """
    Oblicza VWAP (Volume Weighted Average Price).
    
    VWAP = Sum(Typical Price * Volume) / Sum(Volume)
    Typical Price = (High + Low + Close) / 3
    """
    if not candles:
        return None
    
    total_pv = 0.0
    total_volume = 0.0
    
    for candle in candles:
        typical_price = (candle.high + candle.low + candle.close) / 3
        total_pv += typical_price * candle.volume
        total_volume += candle.volume
    
    if total_volume == 0:
        return None
    
    return total_pv / total_volume


def calculate_volatility_percentile(
    candles: List[Candle],
    atr_period: int = 14,
    lookback: int = 50
) -> Optional[float]:
    """
    Oblicza percentyl zmienności na podstawie ATR.
    
    Zwraca wartość 0-100 oznaczającą gdzie obecna zmienność
    znajduje się w kontekście historycznym.
    """
    if len(candles) < lookback + atr_period:
        return None
    
    # Oblicz ATR dla każdego punktu w lookback
    atr_values = []
    for i in range(lookback):
        end_idx = len(candles) - lookback + i + 1
        if end_idx > atr_period:
            subset = candles[:end_idx]
            atr = calculate_atr(subset, atr_period)
            if atr is not None:
                atr_values.append(atr)
    
    if not atr_values:
        return None
    
    current_atr = calculate_atr(candles, atr_period)
    if current_atr is None:
        return None
    
    # Oblicz percentyl
    count_below = sum(1 for v in atr_values if v < current_atr)
    percentile = (count_below / len(atr_values)) * 100
    
    return percentile


def calculate_z_score(
    candles: List[Candle],
    period: int = 20
) -> Optional[float]:
    """
    Oblicza Z-score ceny względem SMA.
    
    Z-score = (Price - SMA) / StdDev
    """
    if len(candles) < period:
        return None
    
    closes = [c.close for c in candles[-period:]]
    mean = sum(closes) / period
    
    variance = sum((x - mean) ** 2 for x in closes) / period
    std = math.sqrt(variance)
    
    if std == 0:
        return 0.0
    
    current_price = candles[-1].close
    z_score = (current_price - mean) / std
    
    return z_score


def detect_volume_spike(
    candles: List[Candle],
    lookback: int = 20,
    threshold_percentile: float = 90
) -> bool:
    """
    Wykrywa spike wolumenu.
    
    Zwraca True jeśli obecny wolumen jest powyżej threshold_percentile.
    """
    if len(candles) < lookback:
        return False
    
    volumes = [c.volume for c in candles[-lookback:]]
    current_volume = candles[-1].volume
    
    # Oblicz percentyl
    count_below = sum(1 for v in volumes[:-1] if v < current_volume)
    percentile = (count_below / (len(volumes) - 1)) * 100
    
    return percentile >= threshold_percentile
