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
- ADX (Average Directional Index)
- SuperTrend
- OBV (On Balance Volume)
- Keltner Channel
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


@dataclass
class ADXResult:
    """Wynik ADX (Average Directional Index)."""
    adx: float
    plus_di: float  # +DI
    minus_di: float  # -DI


@dataclass
class SuperTrendResult:
    """Wynik SuperTrend."""
    value: float
    direction: int  # 1 = uptrend, -1 = downtrend


@dataclass
class KeltnerChannel:
    """Wynik Keltner Channel."""
    upper: float
    middle: float
    lower: float


@dataclass
class PriceAction:
    """Wynik analizy price action."""
    pattern: str  # "HH", "HL", "LH", "LL", "NONE"
    is_uptrend: bool
    is_downtrend: bool


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


def calculate_adx(candles: List[Candle], period: int = 14) -> Optional[ADXResult]:
    """
    Calculates ADX (Average Directional Index) - trend strength.
    
    ADX > 20-25 indicates a strong trend.
    +DI > -DI indicates an uptrend.
    -DI > +DI indicates a downtrend.
    
    Note: Uses simplified Wilder's smoothing approximation.
    """
    if len(candles) < period * 2:
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
        
        # True Range
        tr = max(
            high - low,
            abs(high - prev_close),
            abs(low - prev_close)
        )
        tr_list.append(tr)
        
        # Directional Movement
        plus_dm = max(high - prev_high, 0) if (high - prev_high) > (prev_low - low) else 0
        minus_dm = max(prev_low - low, 0) if (prev_low - low) > (high - prev_high) else 0
        
        plus_dm_list.append(plus_dm)
        minus_dm_list.append(minus_dm)
    
    if len(tr_list) < period:
        return None
    
    # Wilder's smoothing: First value is sum, subsequent use exponential decay
    def wilder_smooth(data: List[float], period: int) -> List[float]:
        if len(data) < period:
            return []
        # First smoothed value is sum of first 'period' values
        smoothed = [sum(data[:period])]
        # Subsequent values: prev - prev/period + current
        for i in range(period, len(data)):
            smoothed.append(smoothed[-1] - smoothed[-1]/period + data[i])
        return smoothed
    
    smoothed_tr = wilder_smooth(tr_list, period)
    smoothed_plus_dm = wilder_smooth(plus_dm_list, period)
    smoothed_minus_dm = wilder_smooth(minus_dm_list, period)
    
    if not smoothed_tr or smoothed_tr[-1] == 0:
        return None
    
    # +DI and -DI
    plus_di = (smoothed_plus_dm[-1] / smoothed_tr[-1]) * 100
    minus_di = (smoothed_minus_dm[-1] / smoothed_tr[-1]) * 100
    
    # DX values for ADX calculation
    di_sum = plus_di + minus_di
    if di_sum == 0:
        return None
    
    dx_list = []
    min_len = min(len(smoothed_plus_dm), len(smoothed_minus_dm), len(smoothed_tr))
    for i in range(min_len):
        if smoothed_tr[i] == 0:
            continue
        pdi = (smoothed_plus_dm[i] / smoothed_tr[i]) * 100
        mdi = (smoothed_minus_dm[i] / smoothed_tr[i]) * 100
        di_sum_i = pdi + mdi
        if di_sum_i > 0:
            dx_list.append(abs(pdi - mdi) / di_sum_i * 100)
    
    if len(dx_list) < period:
        return None
    
    # ADX is smoothed DX using Wilder's method
    adx_smoothed = wilder_smooth(dx_list, period)
    if not adx_smoothed:
        return None
    
    # Normalize ADX (divide by period since wilder_smooth accumulates)
    adx = adx_smoothed[-1] / period
    
    return ADXResult(adx=adx, plus_di=plus_di, minus_di=minus_di)


def calculate_supertrend(
    candles: List[Candle],
    period: int = 10,
    multiplier: float = 3.0
) -> Optional[SuperTrendResult]:
    """
    Oblicza SuperTrend - trailing stop indicator.
    
    direction = 1 oznacza uptrend
    direction = -1 oznacza downtrend
    """
    atr = calculate_atr(candles, period)
    if atr is None:
        return None
    
    current = candles[-1]
    hl2 = (current.high + current.low) / 2
    
    upper_band = hl2 + (multiplier * atr)
    lower_band = hl2 - (multiplier * atr)
    
    # Determine trend direction
    close = current.close
    
    if close > upper_band:
        direction = 1
        value = lower_band
    elif close < lower_band:
        direction = -1
        value = upper_band
    else:
        # Maintain previous direction (simplified)
        direction = 1 if close > hl2 else -1
        value = lower_band if direction == 1 else upper_band
    
    return SuperTrendResult(value=value, direction=direction)


def calculate_obv(candles: List[Candle]) -> Optional[float]:
    """
    Oblicza OBV (On Balance Volume).
    
    OBV rośnie gdy cena rośnie, maleje gdy cena maleje.
    Użyteczny do potwierdzania trendów.
    """
    if len(candles) < 2:
        return None
    
    obv = 0.0
    
    for i in range(1, len(candles)):
        if candles[i].close > candles[i-1].close:
            obv += candles[i].volume
        elif candles[i].close < candles[i-1].close:
            obv -= candles[i].volume
        # Jeśli ceny równe, OBV bez zmian
    
    return obv


def calculate_obv_slope(candles: List[Candle], period: int = 10) -> Optional[float]:
    """
    Oblicza nachylenie OBV (trend wolumenu).
    
    Dodatnie nachylenie = rosnący OBV = akumulacja
    Ujemne nachylenie = malejący OBV = dystrybucja
    """
    if len(candles) < period + 1:
        return None
    
    # Oblicz OBV dla każdego punktu w okresie
    obv_values = []
    for i in range(period):
        end_idx = len(candles) - period + i + 1
        obv = calculate_obv(candles[:end_idx])
        if obv is not None:
            obv_values.append(obv)
    
    if len(obv_values) < 2:
        return None
    
    # Prosta regresja liniowa dla nachylenia
    n = len(obv_values)
    x_mean = (n - 1) / 2
    y_mean = sum(obv_values) / n
    
    numerator = sum((i - x_mean) * (obv_values[i] - y_mean) for i in range(n))
    denominator = sum((i - x_mean) ** 2 for i in range(n))
    
    if denominator == 0:
        return 0.0
    
    return numerator / denominator


def calculate_keltner_channel(
    candles: List[Candle],
    ema_period: int = 20,
    atr_period: int = 10,
    multiplier: float = 2.0
) -> Optional[KeltnerChannel]:
    """
    Oblicza Keltner Channel.
    
    Podobny do Bollinger Bands, ale używa ATR zamiast odchylenia standardowego.
    """
    if len(candles) < max(ema_period, atr_period + 1):
        return None
    
    closes = [c.close for c in candles]
    middle = calculate_ema(closes, ema_period)
    atr = calculate_atr(candles, atr_period)
    
    if middle is None or atr is None:
        return None
    
    upper = middle + (multiplier * atr)
    lower = middle - (multiplier * atr)
    
    return KeltnerChannel(upper=upper, middle=middle, lower=lower)


def analyze_price_action(candles: List[Candle], lookback: int = 4) -> Optional[PriceAction]:
    """
    Analizuje price action patterns (HH/HL/LH/LL).
    
    HH = Higher High, HL = Higher Low (uptrend)
    LH = Lower High, LL = Lower Low (downtrend)
    """
    if len(candles) < lookback:
        return None
    
    recent = candles[-lookback:]
    
    # Znajdź lokalne high/low
    highs = [c.high for c in recent]
    lows = [c.low for c in recent]
    
    current_high = highs[-1]
    prev_high = max(highs[:-1])
    current_low = lows[-1]
    prev_low = min(lows[:-1])
    
    # Określ pattern
    higher_high = current_high > prev_high
    higher_low = current_low > prev_low
    lower_high = current_high < prev_high
    lower_low = current_low < prev_low
    
    if higher_high and higher_low:
        pattern = "HH_HL"
        is_uptrend = True
        is_downtrend = False
    elif lower_high and lower_low:
        pattern = "LH_LL"
        is_uptrend = False
        is_downtrend = True
    elif higher_high:
        pattern = "HH"
        is_uptrend = True
        is_downtrend = False
    elif lower_low:
        pattern = "LL"
        is_uptrend = False
        is_downtrend = True
    elif higher_low:
        pattern = "HL"
        is_uptrend = True
        is_downtrend = False
    elif lower_high:
        pattern = "LH"
        is_uptrend = False
        is_downtrend = True
    else:
        pattern = "NONE"
        is_uptrend = False
        is_downtrend = False
    
    return PriceAction(pattern=pattern, is_uptrend=is_uptrend, is_downtrend=is_downtrend)


def calculate_realized_volatility(
    candles: List[Candle],
    period: int = 50,
    annualize: bool = False
) -> Optional[float]:
    """
    Oblicza realized volatility (historyczna zmienność).
    
    Używa logarytmicznych zwrotów.
    """
    if len(candles) < period + 1:
        return None
    
    # Logarytmiczne zwroty
    returns = []
    for i in range(len(candles) - period, len(candles)):
        if candles[i-1].close > 0:
            log_return = math.log(candles[i].close / candles[i-1].close)
            returns.append(log_return)
    
    if len(returns) < 2:
        return None
    
    # Odchylenie standardowe zwrotów
    mean_return = sum(returns) / len(returns)
    variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
    volatility = math.sqrt(variance)
    
    if annualize:
        # Zakładając dzienne dane, annualizacja * sqrt(252)
        volatility *= math.sqrt(252)
    
    return volatility


def calculate_vwap_deviation(candles: List[Candle]) -> Optional[float]:
    """
    Oblicza odchylenie ceny od VWAP w punktach bazowych (bps).
    
    Dodatnia wartość = cena powyżej VWAP
    Ujemna wartość = cena poniżej VWAP
    """
    vwap = calculate_vwap(candles)
    if vwap is None or vwap == 0:
        return None
    
    current_price = candles[-1].close
    deviation_bps = ((current_price - vwap) / vwap) * 10000
    
    return deviation_bps


def calculate_rvol(candles: List[Candle], lookback: int = 20) -> Optional[float]:
    """
    Oblicza RVOL (Relative Volume).
    
    RVOL = Current Volume / Average Volume
    RVOL > 1 indicates higher than average volume.
    """
    if len(candles) < lookback + 1:
        return None
    
    # Use lookback period excluding current candle for average
    historical_candles = candles[-(lookback + 1):-1]
    volumes = [c.volume for c in historical_candles]
    avg_volume = sum(volumes) / len(volumes)
    
    if avg_volume == 0:
        return None
    
    current_volume = candles[-1].volume
    return current_volume / avg_volume
