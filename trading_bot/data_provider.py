"""
Data Provider module for fetching historical market data.

Supports:
- BingX API for fetching OHLCV candlestick data
- CSV file loading for offline analysis
"""

import json
import time
import urllib.request
import urllib.error
import urllib.parse
import csv
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
import logging

from .strategy import Candle

logger = logging.getLogger(__name__)


@dataclass
class MarketInfo:
    """Information about a trading pair."""
    symbol: str
    base_asset: str
    quote_asset: str
    volume_24h: float
    price: float


class CSVDataProvider:
    """
    Data provider for loading candle data from CSV files.
    
    CSV format should have columns:
    timestamp (or time), open, high, low, close, volume
    
    Note: Both 'timestamp' and 'time' column names are supported.
    """
    
    @staticmethod
    def load_candles(filepath: str) -> List[Candle]:
        """
        Load candles from CSV file.
        
        Args:
            filepath: Path to CSV file
            
        Returns:
            List of Candle objects
        """
        candles = []
        
        if not os.path.exists(filepath):
            logger.error(f"File not found: {filepath}")
            return candles
        
        with open(filepath, 'r', newline='') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                try:
                    candles.append(Candle(
                        timestamp=int(row.get('timestamp', row.get('time', 0))),
                        open=float(row.get('open', 0)),
                        high=float(row.get('high', 0)),
                        low=float(row.get('low', 0)),
                        close=float(row.get('close', 0)),
                        volume=float(row.get('volume', 0))
                    ))
                except (ValueError, TypeError) as e:
                    logger.warning(f"Error parsing row: {e}")
                    continue
        
        candles.sort(key=lambda x: x.timestamp)
        return candles
    
    @staticmethod
    def save_candles(candles: List[Candle], filepath: str):
        """
        Save candles to CSV file.
        
        Args:
            candles: List of candles
            filepath: Output file path
        """
        with open(filepath, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            writer.writeheader()
            
            for c in candles:
                writer.writerow({
                    'timestamp': c.timestamp,
                    'open': c.open,
                    'high': c.high,
                    'low': c.low,
                    'close': c.close,
                    'volume': c.volume
                })


class BingXDataProvider:
    """
    Data provider using BingX public API.
    
    BingX API docs: https://bingx-api.github.io/docs/
    """
    
    BASE_URL = "https://open-api.bingx.com"
    
    # Supported timeframes
    TIMEFRAMES = {
        "1m": "1m",
        "5m": "5m", 
        "15m": "15m",
        "30m": "30m",
        "1h": "1h",
        "4h": "4h",
        "12h": "12h",
        "1d": "1d",
    }
    
    # Timeframe to milliseconds
    TIMEFRAME_MS = {
        "1m": 60 * 1000,
        "5m": 5 * 60 * 1000,
        "15m": 15 * 60 * 1000,
        "30m": 30 * 60 * 1000,
        "1h": 60 * 60 * 1000,
        "4h": 4 * 60 * 60 * 1000,
        "12h": 12 * 60 * 60 * 1000,
        "1d": 24 * 60 * 60 * 1000,
    }
    
    def __init__(self, timeout: int = 30):
        """
        Initialize BingX data provider.
        
        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout
    
    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """Make HTTP request to BingX API."""
        url = f"{self.BASE_URL}{endpoint}"
        
        if params:
            query_string = urllib.parse.urlencode(params)
            url = f"{url}?{query_string}"
        
        logger.debug(f"Requesting: {url}")
        
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "TradingBot/1.0"}
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                data = json.loads(response.read().decode())
                return data
        except urllib.error.HTTPError as e:
            logger.error(f"HTTP Error {e.code}: {e.reason}")
            raise
        except urllib.error.URLError as e:
            logger.error(f"URL Error: {e.reason}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            raise
    
    def get_top_symbols(self, limit: int = 20) -> List[MarketInfo]:
        """
        Get top trading pairs by 24h volume.
        
        Args:
            limit: Number of pairs to return
            
        Returns:
            List of MarketInfo objects sorted by volume
        """
        endpoint = "/openApi/swap/v2/quote/ticker"
        
        try:
            response = self._make_request(endpoint)
            
            if response.get("code") != 0:
                logger.error(f"API error: {response}")
                return []
            
            tickers = response.get("data", [])
            
            # Parse and sort by volume
            markets = []
            for ticker in tickers:
                try:
                    symbol = ticker.get("symbol", "")
                    if not symbol.endswith("-USDT"):
                        continue
                    
                    volume = float(ticker.get("quoteVolume", 0))
                    price = float(ticker.get("lastPrice", 0))
                    
                    base = symbol.replace("-USDT", "")
                    
                    markets.append(MarketInfo(
                        symbol=symbol,
                        base_asset=base,
                        quote_asset="USDT",
                        volume_24h=volume,
                        price=price
                    ))
                except (ValueError, TypeError) as e:
                    logger.warning(f"Error parsing ticker {ticker}: {e}")
                    continue
            
            # Sort by volume descending
            markets.sort(key=lambda x: x.volume_24h, reverse=True)
            
            return markets[:limit]
            
        except Exception as e:
            logger.error(f"Error fetching top symbols: {e}")
            return []
    
    def get_klines(
        self,
        symbol: str,
        interval: str,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        limit: int = 1000
    ) -> List[Candle]:
        """
        Fetch historical kline/candlestick data.
        
        Args:
            symbol: Trading pair (e.g., "BTC-USDT")
            interval: Timeframe (1m, 5m, 15m, 30m, 1h, 4h, 12h, 1d)
            start_time: Start timestamp in milliseconds
            end_time: End timestamp in milliseconds
            limit: Number of candles (max 1440)
            
        Returns:
            List of Candle objects
        """
        if interval not in self.TIMEFRAMES:
            raise ValueError(f"Invalid interval: {interval}. Supported: {list(self.TIMEFRAMES.keys())}")
        
        endpoint = "/openApi/swap/v3/quote/klines"
        
        params = {
            "symbol": symbol,
            "interval": self.TIMEFRAMES[interval],
            "limit": min(limit, 1440)
        }
        
        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time
        
        try:
            response = self._make_request(endpoint, params)
            
            if response.get("code") != 0:
                logger.error(f"API error: {response}")
                return []
            
            klines = response.get("data", [])
            
            candles = []
            for kline in klines:
                try:
                    candles.append(Candle(
                        timestamp=int(kline.get("time", 0)),
                        open=float(kline.get("open", 0)),
                        high=float(kline.get("high", 0)),
                        low=float(kline.get("low", 0)),
                        close=float(kline.get("close", 0)),
                        volume=float(kline.get("volume", 0))
                    ))
                except (ValueError, TypeError) as e:
                    logger.warning(f"Error parsing kline: {e}")
                    continue
            
            # Sort by timestamp
            candles.sort(key=lambda x: x.timestamp)
            
            return candles
            
        except Exception as e:
            logger.error(f"Error fetching klines for {symbol}: {e}")
            return []
    
    def get_klines_range(
        self,
        symbol: str,
        interval: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[Candle]:
        """
        Fetch klines for a date range, handling pagination.
        
        Args:
            symbol: Trading pair
            interval: Timeframe
            start_date: Start datetime (UTC)
            end_date: End datetime (UTC)
            
        Returns:
            List of Candle objects for the entire range
        """
        all_candles = []
        
        start_ms = int(start_date.timestamp() * 1000)
        end_ms = int(end_date.timestamp() * 1000)
        
        interval_ms = self.TIMEFRAME_MS.get(interval, 60000)
        max_candles_per_request = 1440
        
        current_start = start_ms
        
        while current_start < end_ms:
            # Calculate end time for this batch
            batch_end = min(
                current_start + (max_candles_per_request * interval_ms),
                end_ms
            )
            
            candles = self.get_klines(
                symbol=symbol,
                interval=interval,
                start_time=current_start,
                end_time=batch_end,
                limit=max_candles_per_request
            )
            
            if not candles:
                break
            
            all_candles.extend(candles)
            
            # Move to next batch
            if candles:
                current_start = candles[-1].timestamp + interval_ms
            else:
                current_start = batch_end
            
            # Rate limiting - 100ms delay between requests
            # BingX API allows up to 10 requests per second
            time.sleep(0.1)
        
        # Remove duplicates and sort
        seen = set()
        unique_candles = []
        for c in all_candles:
            if c.timestamp not in seen:
                seen.add(c.timestamp)
                unique_candles.append(c)
        
        unique_candles.sort(key=lambda x: x.timestamp)
        
        return unique_candles


def timestamp_to_datetime(timestamp_ms: int) -> datetime:
    """Convert millisecond timestamp to datetime."""
    return datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)


def datetime_to_timestamp(dt: datetime) -> int:
    """Convert datetime to millisecond timestamp."""
    return int(dt.timestamp() * 1000)
