"""
Moduł walidacji danych.

Implementuje:
- Wykrywanie luk w danych (sequence gaps)
- Wykrywanie anomalii cen/wolumenu (Z-score)
- Walidacja crossed/locked book
- Sprawdzanie ciągłości timestampów
"""

import logging
import math
import time
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple

from .strategy import Candle
from .guards import MarketData

logger = logging.getLogger(__name__)


class DataQuality(Enum):
    """Jakość danych."""
    GOOD = "good"
    WARNING = "warning"
    BAD = "bad"


@dataclass
class ValidationResult:
    """Wynik walidacji."""
    quality: DataQuality
    issues: List[str]
    details: dict


@dataclass
class AnomalyConfig:
    """Konfiguracja wykrywania anomalii."""
    # Z-score thresholds
    price_zscore_threshold: float = 3.0  # Próg Z-score dla ceny
    volume_zscore_threshold: float = 4.0  # Próg Z-score dla wolumenu
    
    # Okno dla Z-score
    zscore_window: int = 20
    
    # Maksymalny gap czasowy między świecami (sekundy)
    max_timestamp_gap_seconds: int = 3600 * 2  # 2 godziny dla 1h candles
    
    # Minimalna liczba świec do analizy
    min_candles_for_analysis: int = 20


class DataValidator:
    """Walidator danych rynkowych."""
    
    def __init__(self, config: Optional[AnomalyConfig] = None):
        self.config = config or AnomalyConfig()
    
    def validate_candles(self, candles: List[Candle]) -> ValidationResult:
        """Waliduje listę świec."""
        issues = []
        details = {}
        
        if len(candles) < self.config.min_candles_for_analysis:
            return ValidationResult(
                quality=DataQuality.WARNING,
                issues=[f"Insufficient data: {len(candles)} candles"],
                details={"candle_count": len(candles)}
            )
        
        # Sprawdź luki czasowe
        gaps = self._check_timestamp_gaps(candles)
        if gaps:
            issues.append(f"Found {len(gaps)} timestamp gap(s)")
            details["timestamp_gaps"] = gaps
        
        # Sprawdź anomalie cen
        price_anomalies = self._detect_price_anomalies(candles)
        if price_anomalies:
            issues.append(f"Found {len(price_anomalies)} price anomaly(ies)")
            details["price_anomalies"] = price_anomalies
        
        # Sprawdź anomalie wolumenu
        volume_anomalies = self._detect_volume_anomalies(candles)
        if volume_anomalies:
            issues.append(f"Found {len(volume_anomalies)} volume anomaly(ies)")
            details["volume_anomalies"] = volume_anomalies
        
        # Sprawdź spójność OHLC
        ohlc_issues = self._validate_ohlc_consistency(candles)
        if ohlc_issues:
            issues.extend(ohlc_issues)
            details["ohlc_issues"] = ohlc_issues
        
        # Określ jakość danych
        if price_anomalies or len(gaps) > 2:
            quality = DataQuality.BAD
        elif volume_anomalies or gaps or ohlc_issues:
            quality = DataQuality.WARNING
        else:
            quality = DataQuality.GOOD
        
        return ValidationResult(quality=quality, issues=issues, details=details)
    
    def _check_timestamp_gaps(self, candles: List[Candle]) -> List[dict]:
        """Sprawdza luki w timestampach."""
        if len(candles) < 2:
            return []
        
        gaps = []
        
        # Oblicz typowy interwał
        intervals = []
        for i in range(1, min(10, len(candles))):
            intervals.append(candles[i].timestamp - candles[i-1].timestamp)
        
        if not intervals:
            return []
        
        typical_interval = sum(intervals) / len(intervals)
        
        for i in range(1, len(candles)):
            gap = candles[i].timestamp - candles[i-1].timestamp
            
            # Jeśli gap jest > 2x typowy interwał
            if gap > typical_interval * 2:
                gaps.append({
                    "index": i,
                    "gap_seconds": gap,
                    "expected_seconds": typical_interval,
                    "timestamp_before": candles[i-1].timestamp,
                    "timestamp_after": candles[i].timestamp
                })
        
        return gaps
    
    def _detect_price_anomalies(self, candles: List[Candle]) -> List[dict]:
        """Wykrywa anomalie cen używając Z-score."""
        if len(candles) < self.config.zscore_window:
            return []
        
        anomalies = []
        closes = [c.close for c in candles]
        
        # Oblicz rolling Z-score
        for i in range(self.config.zscore_window, len(candles)):
            window = closes[i - self.config.zscore_window:i]
            current_price = closes[i]
            
            mean = sum(window) / len(window)
            variance = sum((x - mean) ** 2 for x in window) / len(window)
            std = math.sqrt(variance) if variance > 0 else 0
            
            if std > 0:
                z_score = abs((current_price - mean) / std)
                
                if z_score > self.config.price_zscore_threshold:
                    anomalies.append({
                        "index": i,
                        "timestamp": candles[i].timestamp,
                        "price": current_price,
                        "z_score": z_score,
                        "mean": mean,
                        "std": std
                    })
        
        return anomalies
    
    def _detect_volume_anomalies(self, candles: List[Candle]) -> List[dict]:
        """Wykrywa anomalie wolumenu używając Z-score."""
        if len(candles) < self.config.zscore_window:
            return []
        
        anomalies = []
        volumes = [c.volume for c in candles]
        
        for i in range(self.config.zscore_window, len(candles)):
            window = volumes[i - self.config.zscore_window:i]
            current_volume = volumes[i]
            
            mean = sum(window) / len(window)
            variance = sum((x - mean) ** 2 for x in window) / len(window)
            std = math.sqrt(variance) if variance > 0 else 0
            
            if std > 0:
                z_score = abs((current_volume - mean) / std)
                
                if z_score > self.config.volume_zscore_threshold:
                    anomalies.append({
                        "index": i,
                        "timestamp": candles[i].timestamp,
                        "volume": current_volume,
                        "z_score": z_score,
                        "mean": mean,
                        "std": std
                    })
        
        return anomalies
    
    def _validate_ohlc_consistency(self, candles: List[Candle]) -> List[str]:
        """Sprawdza spójność danych OHLC."""
        issues = []
        
        for i, candle in enumerate(candles):
            # High powinno być >= wszystkich innych cen
            if candle.high < candle.open or candle.high < candle.close or candle.high < candle.low:
                issues.append(f"Candle {i}: High ({candle.high}) < other prices")
            
            # Low powinno być <= wszystkich innych cen
            if candle.low > candle.open or candle.low > candle.close or candle.low > candle.high:
                issues.append(f"Candle {i}: Low ({candle.low}) > other prices")
            
            # Ceny nie powinny być ujemne
            if candle.open < 0 or candle.high < 0 or candle.low < 0 or candle.close < 0:
                issues.append(f"Candle {i}: Negative price detected")
            
            # Wolumen nie powinien być ujemny
            if candle.volume < 0:
                issues.append(f"Candle {i}: Negative volume")
        
        return issues
    
    def validate_order_book(self, market_data: MarketData) -> ValidationResult:
        """Waliduje dane order book."""
        issues = []
        details = {}
        
        # Sprawdź crossed book (bid > ask)
        if market_data.bid >= market_data.ask:
            issues.append(f"Crossed book: bid ({market_data.bid}) >= ask ({market_data.ask})")
            details["crossed_book"] = True
        
        # Sprawdź locked book (bid == ask)
        if market_data.bid == market_data.ask:
            issues.append(f"Locked book: bid == ask ({market_data.bid})")
            details["locked_book"] = True
        
        # Sprawdź zerowe/ujemne ceny
        if market_data.bid <= 0:
            issues.append(f"Invalid bid: {market_data.bid}")
        
        if market_data.ask <= 0:
            issues.append(f"Invalid ask: {market_data.ask}")
        
        # Sprawdź zerową głębokość
        if market_data.bid_depth <= 0:
            issues.append(f"Zero bid depth")
        
        if market_data.ask_depth <= 0:
            issues.append(f"Zero ask depth")
        
        # Określ jakość
        if "crossed_book" in details or market_data.bid <= 0 or market_data.ask <= 0:
            quality = DataQuality.BAD
        elif issues:
            quality = DataQuality.WARNING
        else:
            quality = DataQuality.GOOD
        
        return ValidationResult(quality=quality, issues=issues, details=details)
    
    def filter_anomalous_candles(
        self,
        candles: List[Candle],
        remove_anomalies: bool = True
    ) -> Tuple[List[Candle], List[int]]:
        """
        Filtruje anomalne świece.
        
        Args:
            candles: Lista świec
            remove_anomalies: Czy usuwać anomalie (True) czy tylko zwrócić indeksy (False)
        
        Returns:
            Tuple z przefiltrowaną listą świec i listą indeksów anomalii
        """
        if len(candles) < self.config.zscore_window:
            return candles, []
        
        # Znajdź anomalie
        price_anomalies = self._detect_price_anomalies(candles)
        volume_anomalies = self._detect_volume_anomalies(candles)
        
        anomaly_indices = set()
        for anomaly in price_anomalies + volume_anomalies:
            anomaly_indices.add(anomaly["index"])
        
        if not remove_anomalies:
            return candles, list(anomaly_indices)
        
        # Usuń anomalne świece
        filtered = [c for i, c in enumerate(candles) if i not in anomaly_indices]
        
        return filtered, list(anomaly_indices)


class FeedHealthMonitor:
    """Monitor zdrowia feeda danych."""
    
    def __init__(self):
        self.last_update_time: Optional[int] = None
        self.update_count: int = 0
        self.lag_samples: List[int] = []
        self.max_lag_samples: int = 100
    
    def record_update(self, timestamp_exchange: int, timestamp_received: int):
        """Zapisuje aktualizację feeda."""
        self.last_update_time = timestamp_received
        self.update_count += 1
        
        lag = timestamp_received - timestamp_exchange
        self.lag_samples.append(lag)
        
        # Ogranicz liczbę próbek
        if len(self.lag_samples) > self.max_lag_samples:
            self.lag_samples = self.lag_samples[-self.max_lag_samples:]
    
    def get_average_lag(self) -> Optional[float]:
        """Zwraca średnie opóźnienie w ms."""
        if not self.lag_samples:
            return None
        return sum(self.lag_samples) / len(self.lag_samples)
    
    def get_max_lag(self) -> Optional[int]:
        """Zwraca maksymalne opóźnienie w ms."""
        if not self.lag_samples:
            return None
        return max(self.lag_samples)
    
    def is_feed_healthy(self, max_lag_ms: int = 1000, stale_threshold_ms: int = 5000) -> bool:
        """
        Sprawdza czy feed jest zdrowy.
        
        Args:
            max_lag_ms: Maksymalne akceptowalne opóźnienie
            stale_threshold_ms: Próg po którym feed jest uznawany za stale
        """
        if self.last_update_time is None:
            return False
        
        current_time = int(time.time() * 1000)
        time_since_update = current_time - self.last_update_time
        
        if time_since_update > stale_threshold_ms:
            logger.warning(f"Feed stale: {time_since_update}ms since last update")
            return False
        
        avg_lag = self.get_average_lag()
        if avg_lag is not None and avg_lag > max_lag_ms:
            logger.warning(f"Feed lag too high: {avg_lag:.0f}ms avg")
            return False
        
        return True
    
    def get_health_report(self) -> dict:
        """Zwraca raport o zdrowiu feeda."""
        return {
            "update_count": self.update_count,
            "last_update_time": self.last_update_time,
            "average_lag_ms": self.get_average_lag(),
            "max_lag_ms": self.get_max_lag(),
            "sample_count": len(self.lag_samples)
        }
