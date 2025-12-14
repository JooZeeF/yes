#!/usr/bin/env python3
"""
Punkt wejścia dla bota do tradingu.

Przykład użycia:
    python main.py
"""

from trading_bot.bot import TradingBot
from trading_bot.config import TradingConfig
from trading_bot.strategy import Candle, SimpleMovingAverageStrategy


def generate_sample_candles() -> list:
    """Generuje przykładowe dane świecowe do testowania."""
    # Symulacja danych rynkowych (rosnący trend z korektą)
    base_price = 50000
    candles = []
    
    prices = [
        100, 101, 102, 101, 103, 105, 104, 106, 108, 107,  # Wzrost
        109, 111, 110, 112, 114, 113, 115, 117, 116, 118,  # Dalszy wzrost
        117, 115, 113, 111, 109, 108, 106, 105, 104, 103,  # Spadek (korekta)
    ]
    
    for i, price_delta in enumerate(prices):
        price = base_price + price_delta * 10
        candles.append(Candle(
            timestamp=1700000000 + i * 3600,
            open=price - 5,
            high=price + 10,
            low=price - 10,
            close=price,
            volume=1000 + i * 10
        ))
    
    return candles


def main():
    """Uruchamia demo bota do tradingu."""
    print("=" * 60)
    print("Trading Bot - Demo")
    print("=" * 60)
    
    # Konfiguracja
    config = TradingConfig(
        symbol="BTC/USDT",
        timeframe="1h",
        max_position_size=0.1,
        stop_loss_percent=2.0,
        take_profit_percent=4.0,
        dry_run=True
    )
    
    # Strategia SMA
    strategy = SimpleMovingAverageStrategy(short_period=5, long_period=10)
    
    # Inicjalizacja bota
    bot = TradingBot(config=config, strategy=strategy)
    
    # Symulacja tradingu
    candles = generate_sample_candles()
    
    print("\nRozpoczynanie symulacji tradingu...")
    print("-" * 60)
    
    for i in range(10, len(candles)):
        historical_candles = candles[:i+1]
        result = bot.process_candles(historical_candles)
        
        if result:
            current_candle = historical_candles[-1]
            print(f"[Świeca {i}] Cena: {current_candle.close:.2f} - {result}")
    
    print("-" * 60)
    print("\nStatus końcowy:")
    status = bot.get_status()
    for key, value in status.items():
        print(f"  {key}: {value}")
    
    print("\n" + "=" * 60)
    print("Demo zakończone!")
    print("=" * 60)


if __name__ == "__main__":
    main()
