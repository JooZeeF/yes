"""
Moduł guardów i filtrów bezpieczeństwa.

Implementuje:
- Spread/depth guard
- Volatility/regime filter
- Price band guard
- Daily drawdown guard
- Cost-aware filter
- Feed health monitor
"""

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

from .strategy import Candle
from .indicators import calculate_atr, calculate_volatility_percentile

logger = logging.getLogger(__name__)


class VolatilityRegime(Enum):
    """Reżim zmienności rynku."""
    LOW = "low"           # Niska zmienność (< 30 percentyl)
    NORMAL = "normal"     # Normalna zmienność (30-70 percentyl)
    HIGH = "high"         # Wysoka zmienność (70-90 percentyl)
    EXTREME = "extreme"   # Ekstremalna zmienność (> 90 percentyl)


class GuardStatus(Enum):
    """Status guarda."""
    OK = "ok"
    WARNING = "warning"
    BLOCKED = "blocked"


@dataclass
class MarketData:
    """Dane rynkowe do oceny przez guardy."""
    bid: float
    ask: float
    bid_depth: float  # Głębokość po stronie bid (w jednostkach bazowych)
    ask_depth: float  # Głębokość po stronie ask
    last_price: float
    timestamp_exchange: int  # Timestamp z giełdy (ms)
    timestamp_received: int  # Timestamp otrzymania (ms)


@dataclass
class GuardResult:
    """Wynik sprawdzenia guarda."""
    status: GuardStatus
    guard_name: str
    message: str
    details: Dict = field(default_factory=dict)


@dataclass
class GuardConfig:
    """Konfiguracja guardów."""
    # Spread guard
    max_spread_bps: float = 10.0  # Maksymalny spread w punktach bazowych
    
    # Depth guard
    min_bid_depth: float = 1.0  # Minimalny depth bid
    min_ask_depth: float = 1.0  # Minimalny depth ask
    
    # Clock drift
    max_clock_drift_ms: int = 1000  # Maksymalny drift zegara (ms)
    
    # Price band
    price_band_percent: float = 5.0  # Maksymalna zmiana ceny od otwarcia (%)
    
    # Daily drawdown
    max_daily_drawdown_percent: float = 5.0  # Maksymalny dzienny DD (%)
    
    # Cost awareness
    maker_fee_bps: float = 1.0  # Opłata maker (bps)
    taker_fee_bps: float = 5.0  # Opłata taker (bps)
    min_edge_bps: float = 10.0  # Minimalny edge po kosztach (bps)
    expected_slippage_bps: float = 2.0  # Oczekiwany poślizg (bps)
    
    # Volatility regime
    vol_low_threshold: float = 30.0  # Próg niskiej zmienności (percentyl)
    vol_high_threshold: float = 70.0  # Próg wysokiej zmienności (percentyl)
    vol_extreme_threshold: float = 90.0  # Próg ekstremalnej zmienności (percentyl)


class SpreadGuard:
    """Guard sprawdzający spread bid/ask."""
    
    def __init__(self, max_spread_bps: float):
        self.max_spread_bps = max_spread_bps
    
    def check(self, market_data: MarketData) -> GuardResult:
        """Sprawdza czy spread jest akceptowalny."""
        if market_data.bid <= 0:
            return GuardResult(
                status=GuardStatus.BLOCKED,
                guard_name="SpreadGuard",
                message="Invalid bid price",
                details={"bid": market_data.bid}
            )
        
        spread_bps = ((market_data.ask - market_data.bid) / market_data.bid) * 10000
        
        if spread_bps > self.max_spread_bps:
            return GuardResult(
                status=GuardStatus.BLOCKED,
                guard_name="SpreadGuard",
                message=f"Spread {spread_bps:.2f} bps exceeds max {self.max_spread_bps} bps",
                details={"spread_bps": spread_bps, "max_spread_bps": self.max_spread_bps}
            )
        
        return GuardResult(
            status=GuardStatus.OK,
            guard_name="SpreadGuard",
            message=f"Spread OK: {spread_bps:.2f} bps",
            details={"spread_bps": spread_bps}
        )


class DepthGuard:
    """Guard sprawdzający głębokość księgi zleceń."""
    
    def __init__(self, min_bid_depth: float, min_ask_depth: float):
        self.min_bid_depth = min_bid_depth
        self.min_ask_depth = min_ask_depth
    
    def check(self, market_data: MarketData) -> GuardResult:
        """Sprawdza czy głębokość jest wystarczająca."""
        issues = []
        
        if market_data.bid_depth < self.min_bid_depth:
            issues.append(f"Bid depth {market_data.bid_depth} < min {self.min_bid_depth}")
        
        if market_data.ask_depth < self.min_ask_depth:
            issues.append(f"Ask depth {market_data.ask_depth} < min {self.min_ask_depth}")
        
        if issues:
            return GuardResult(
                status=GuardStatus.BLOCKED,
                guard_name="DepthGuard",
                message="; ".join(issues),
                details={
                    "bid_depth": market_data.bid_depth,
                    "ask_depth": market_data.ask_depth,
                    "min_bid_depth": self.min_bid_depth,
                    "min_ask_depth": self.min_ask_depth
                }
            )
        
        return GuardResult(
            status=GuardStatus.OK,
            guard_name="DepthGuard",
            message="Depth OK",
            details={
                "bid_depth": market_data.bid_depth,
                "ask_depth": market_data.ask_depth
            }
        )


class ClockDriftGuard:
    """Guard sprawdzający drift zegara."""
    
    def __init__(self, max_drift_ms: int):
        self.max_drift_ms = max_drift_ms
    
    def check(self, market_data: MarketData) -> GuardResult:
        """Sprawdza drift między czasem giełdy a lokalnym."""
        drift_ms = abs(market_data.timestamp_received - market_data.timestamp_exchange)
        
        if drift_ms > self.max_drift_ms:
            return GuardResult(
                status=GuardStatus.WARNING,
                guard_name="ClockDriftGuard",
                message=f"Clock drift {drift_ms}ms exceeds max {self.max_drift_ms}ms",
                details={"drift_ms": drift_ms, "max_drift_ms": self.max_drift_ms}
            )
        
        return GuardResult(
            status=GuardStatus.OK,
            guard_name="ClockDriftGuard",
            message=f"Clock drift OK: {drift_ms}ms",
            details={"drift_ms": drift_ms}
        )


class PriceBandGuard:
    """Guard sprawdzający czy cena jest w dozwolonym zakresie."""
    
    def __init__(self, band_percent: float):
        self.band_percent = band_percent
        self.reference_price: Optional[float] = None
    
    def set_reference_price(self, price: float):
        """Ustawia cenę referencyjną (np. cenę otwarcia dnia)."""
        self.reference_price = price
    
    def check(self, current_price: float) -> GuardResult:
        """Sprawdza czy cena jest w dozwolonym przedziale."""
        if self.reference_price is None:
            self.reference_price = current_price
            return GuardResult(
                status=GuardStatus.OK,
                guard_name="PriceBandGuard",
                message="Reference price set",
                details={"reference_price": self.reference_price}
            )
        
        change_percent = ((current_price - self.reference_price) / self.reference_price) * 100
        
        if abs(change_percent) > self.band_percent:
            return GuardResult(
                status=GuardStatus.BLOCKED,
                guard_name="PriceBandGuard",
                message=f"Price change {change_percent:.2f}% exceeds band {self.band_percent}%",
                details={
                    "change_percent": change_percent,
                    "band_percent": self.band_percent,
                    "reference_price": self.reference_price,
                    "current_price": current_price
                }
            )
        
        return GuardResult(
            status=GuardStatus.OK,
            guard_name="PriceBandGuard",
            message=f"Price within band: {change_percent:.2f}%",
            details={"change_percent": change_percent}
        )


class DailyDrawdownGuard:
    """Guard sprawdzający dzienny drawdown."""
    
    def __init__(self, max_drawdown_percent: float):
        self.max_drawdown_percent = max_drawdown_percent
        self.daily_high_balance: float = 0.0
        self.start_of_day_balance: float = 0.0
    
    def reset_daily(self, current_balance: float):
        """Resetuje na początku dnia."""
        self.start_of_day_balance = current_balance
        self.daily_high_balance = current_balance
    
    def update(self, current_balance: float):
        """Aktualizuje najwyższy balans dnia."""
        if current_balance > self.daily_high_balance:
            self.daily_high_balance = current_balance
    
    def check(self, current_balance: float) -> GuardResult:
        """Sprawdza czy drawdown nie przekracza limitu."""
        if self.daily_high_balance <= 0:
            self.daily_high_balance = current_balance
            return GuardResult(
                status=GuardStatus.OK,
                guard_name="DailyDrawdownGuard",
                message="Initial balance set",
                details={"balance": current_balance}
            )
        
        self.update(current_balance)
        
        drawdown_percent = ((self.daily_high_balance - current_balance) / self.daily_high_balance) * 100
        
        if drawdown_percent > self.max_drawdown_percent:
            return GuardResult(
                status=GuardStatus.BLOCKED,
                guard_name="DailyDrawdownGuard",
                message=f"Daily DD {drawdown_percent:.2f}% exceeds max {self.max_drawdown_percent}%",
                details={
                    "drawdown_percent": drawdown_percent,
                    "max_drawdown_percent": self.max_drawdown_percent,
                    "daily_high": self.daily_high_balance,
                    "current_balance": current_balance
                }
            )
        
        return GuardResult(
            status=GuardStatus.OK,
            guard_name="DailyDrawdownGuard",
            message=f"Daily DD OK: {drawdown_percent:.2f}%",
            details={"drawdown_percent": drawdown_percent}
        )


class CostAwareFilter:
    """Filtr uwzględniający koszty transakcji."""
    
    def __init__(
        self,
        maker_fee_bps: float,
        taker_fee_bps: float,
        expected_slippage_bps: float,
        min_edge_bps: float
    ):
        self.maker_fee_bps = maker_fee_bps
        self.taker_fee_bps = taker_fee_bps
        self.expected_slippage_bps = expected_slippage_bps
        self.min_edge_bps = min_edge_bps
    
    def check(self, expected_edge_bps: float, is_maker: bool = False) -> GuardResult:
        """
        Sprawdza czy oczekiwany edge pokrywa koszty.
        
        Args:
            expected_edge_bps: Oczekiwany edge w punktach bazowych
            is_maker: True jeśli zlecenie będzie maker
        """
        fee = self.maker_fee_bps if is_maker else self.taker_fee_bps
        total_cost = fee + self.expected_slippage_bps + self.min_edge_bps
        
        net_edge = expected_edge_bps - total_cost
        
        if net_edge < 0:
            return GuardResult(
                status=GuardStatus.BLOCKED,
                guard_name="CostAwareFilter",
                message=f"Net edge {net_edge:.2f} bps < 0 after costs",
                details={
                    "expected_edge_bps": expected_edge_bps,
                    "fee_bps": fee,
                    "slippage_bps": self.expected_slippage_bps,
                    "min_edge_bps": self.min_edge_bps,
                    "net_edge_bps": net_edge
                }
            )
        
        return GuardResult(
            status=GuardStatus.OK,
            guard_name="CostAwareFilter",
            message=f"Net edge OK: {net_edge:.2f} bps",
            details={"net_edge_bps": net_edge}
        )


class VolatilityRegimeFilter:
    """Filtr reżimu zmienności."""
    
    def __init__(
        self,
        low_threshold: float = 30.0,
        high_threshold: float = 70.0,
        extreme_threshold: float = 90.0
    ):
        self.low_threshold = low_threshold
        self.high_threshold = high_threshold
        self.extreme_threshold = extreme_threshold
    
    def get_regime(self, candles: List[Candle]) -> VolatilityRegime:
        """Określa obecny reżim zmienności."""
        vol_percentile = calculate_volatility_percentile(candles)
        
        if vol_percentile is None:
            return VolatilityRegime.NORMAL
        
        if vol_percentile >= self.extreme_threshold:
            return VolatilityRegime.EXTREME
        elif vol_percentile >= self.high_threshold:
            return VolatilityRegime.HIGH
        elif vol_percentile < self.low_threshold:
            return VolatilityRegime.LOW
        else:
            return VolatilityRegime.NORMAL
    
    def check(
        self,
        candles: List[Candle],
        allowed_regimes: Optional[List[VolatilityRegime]] = None
    ) -> GuardResult:
        """
        Sprawdza czy obecny reżim jest dozwolony.
        
        Args:
            candles: Dane świecowe
            allowed_regimes: Lista dozwolonych reżimów (domyślnie wszystkie oprócz EXTREME)
        """
        if allowed_regimes is None:
            allowed_regimes = [VolatilityRegime.LOW, VolatilityRegime.NORMAL, VolatilityRegime.HIGH]
        
        regime = self.get_regime(candles)
        vol_percentile = calculate_volatility_percentile(candles)
        
        if regime not in allowed_regimes:
            return GuardResult(
                status=GuardStatus.BLOCKED,
                guard_name="VolatilityRegimeFilter",
                message=f"Regime {regime.value} not in allowed regimes",
                details={
                    "regime": regime.value,
                    "vol_percentile": vol_percentile,
                    "allowed_regimes": [r.value for r in allowed_regimes]
                }
            )
        
        return GuardResult(
            status=GuardStatus.OK,
            guard_name="VolatilityRegimeFilter",
            message=f"Regime OK: {regime.value}",
            details={
                "regime": regime.value,
                "vol_percentile": vol_percentile
            }
        )


class GuardManager:
    """Zarządza wszystkimi guardami."""
    
    def __init__(self, config: GuardConfig):
        self.config = config
        
        # Inicjalizacja guardów
        self.spread_guard = SpreadGuard(config.max_spread_bps)
        self.depth_guard = DepthGuard(config.min_bid_depth, config.min_ask_depth)
        self.clock_drift_guard = ClockDriftGuard(config.max_clock_drift_ms)
        self.price_band_guard = PriceBandGuard(config.price_band_percent)
        self.daily_dd_guard = DailyDrawdownGuard(config.max_daily_drawdown_percent)
        self.cost_filter = CostAwareFilter(
            config.maker_fee_bps,
            config.taker_fee_bps,
            config.expected_slippage_bps,
            config.min_edge_bps
        )
        self.vol_regime_filter = VolatilityRegimeFilter(
            config.vol_low_threshold,
            config.vol_high_threshold,
            config.vol_extreme_threshold
        )
    
    def check_market_data(self, market_data: MarketData) -> List[GuardResult]:
        """Sprawdza wszystkie guardy związane z danymi rynkowymi."""
        results = [
            self.spread_guard.check(market_data),
            self.depth_guard.check(market_data),
            self.clock_drift_guard.check(market_data),
        ]
        return results
    
    def check_all(
        self,
        market_data: MarketData,
        current_balance: float,
        candles: List[Candle],
        expected_edge_bps: float = 0.0
    ) -> List[GuardResult]:
        """Sprawdza wszystkie guardy."""
        results = self.check_market_data(market_data)
        
        results.append(self.price_band_guard.check(market_data.last_price))
        results.append(self.daily_dd_guard.check(current_balance))
        results.append(self.vol_regime_filter.check(candles))
        
        if expected_edge_bps > 0:
            results.append(self.cost_filter.check(expected_edge_bps))
        
        return results
    
    def is_trading_allowed(self, results: List[GuardResult]) -> bool:
        """Sprawdza czy trading jest dozwolony na podstawie wyników guardów."""
        for result in results:
            if result.status == GuardStatus.BLOCKED:
                logger.warning(f"Trading blocked by {result.guard_name}: {result.message}")
                return False
        return True
    
    def get_blocked_guards(self, results: List[GuardResult]) -> List[GuardResult]:
        """Zwraca listę guardów blokujących trading."""
        return [r for r in results if r.status == GuardStatus.BLOCKED]
    
    def get_warnings(self, results: List[GuardResult]) -> List[GuardResult]:
        """Zwraca listę ostrzeżeń."""
        return [r for r in results if r.status == GuardStatus.WARNING]
