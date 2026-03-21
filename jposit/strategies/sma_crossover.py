"""Simple Moving Average Crossover Strategy."""

import pandas as pd

from ..models import Side, Signal
from .base import Strategy


class SMACrossoverStrategy(Strategy):
    """Buy when short SMA crosses above long SMA, sell on cross below."""

    def __init__(self, params):
        super().__init__(params)
        self.short_window = params.get("short_window", 20)
        self.long_window = params.get("long_window", 50)

    def analyze(self, symbol, data: pd.DataFrame) -> Signal | None:
        if len(data) < self.long_window + 1:
            return None

        close = data["Close"]
        short_sma = close.rolling(window=self.short_window).mean()
        long_sma = close.rolling(window=self.long_window).mean()

        # Current and previous crossover state
        current_above = short_sma.iloc[-1] > long_sma.iloc[-1]
        prev_above = short_sma.iloc[-2] > long_sma.iloc[-2]

        # Golden cross: short SMA crosses above long SMA
        if current_above and not prev_above:
            strength = (short_sma.iloc[-1] - long_sma.iloc[-1]) / long_sma.iloc[-1]
            return Signal(
                symbol=symbol,
                side=Side.BUY,
                strength=min(abs(strength) * 10, 1.0),
                strategy="sma_crossover",
                metadata={
                    "short_sma": round(short_sma.iloc[-1], 2),
                    "long_sma": round(long_sma.iloc[-1], 2),
                },
            )

        # Death cross: short SMA crosses below long SMA
        if not current_above and prev_above:
            strength = (long_sma.iloc[-1] - short_sma.iloc[-1]) / long_sma.iloc[-1]
            return Signal(
                symbol=symbol,
                side=Side.SELL,
                strength=min(abs(strength) * 10, 1.0),
                strategy="sma_crossover",
                metadata={
                    "short_sma": round(short_sma.iloc[-1], 2),
                    "long_sma": round(long_sma.iloc[-1], 2),
                },
            )

        return None

    def required_data_points(self) -> int:
        return self.long_window + 2
