"""MACD (Moving Average Convergence Divergence) Strategy."""

import pandas as pd

from ..models import Side, Signal
from .base import Strategy


class MACDStrategy(Strategy):
    """Trade on MACD signal line crossovers."""

    def __init__(self, params):
        super().__init__(params)
        self.fast_period = params.get("fast_period", 12)
        self.slow_period = params.get("slow_period", 26)
        self.signal_period = params.get("signal_period", 9)

    def analyze(self, symbol, data: pd.DataFrame) -> Signal | None:
        if len(data) < self.slow_period + self.signal_period + 1:
            return None

        close = data["Close"]

        # Calculate MACD
        fast_ema = close.ewm(span=self.fast_period, adjust=False).mean()
        slow_ema = close.ewm(span=self.slow_period, adjust=False).mean()
        macd_line = fast_ema - slow_ema
        signal_line = macd_line.ewm(span=self.signal_period, adjust=False).mean()
        histogram = macd_line - signal_line

        current_hist = histogram.iloc[-1]
        prev_hist = histogram.iloc[-2]

        if pd.isna(current_hist) or pd.isna(prev_hist):
            return None

        # MACD crosses above signal line (bullish)
        if current_hist > 0 and prev_hist <= 0:
            strength = min(abs(current_hist) / close.iloc[-1] * 100, 1.0)
            return Signal(
                symbol=symbol,
                side=Side.BUY,
                strength=strength,
                strategy="macd",
                metadata={
                    "macd": round(macd_line.iloc[-1], 4),
                    "signal": round(signal_line.iloc[-1], 4),
                    "histogram": round(current_hist, 4),
                },
            )

        # MACD crosses below signal line (bearish)
        if current_hist < 0 and prev_hist >= 0:
            strength = min(abs(current_hist) / close.iloc[-1] * 100, 1.0)
            return Signal(
                symbol=symbol,
                side=Side.SELL,
                strength=strength,
                strategy="macd",
                metadata={
                    "macd": round(macd_line.iloc[-1], 4),
                    "signal": round(signal_line.iloc[-1], 4),
                    "histogram": round(current_hist, 4),
                },
            )

        return None

    def required_data_points(self) -> int:
        return self.slow_period + self.signal_period + 5
