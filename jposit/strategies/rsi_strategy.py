"""RSI (Relative Strength Index) Strategy."""

import pandas as pd

from ..models import Side, Signal
from .base import Strategy


class RSIStrategy(Strategy):
    """Buy when RSI < oversold threshold, sell when RSI > overbought threshold."""

    def __init__(self, params):
        super().__init__(params)
        self.period = params.get("period", 14)
        self.oversold = params.get("oversold", 30)
        self.overbought = params.get("overbought", 70)

    def _calculate_rsi(self, close: pd.Series) -> pd.Series:
        delta = close.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)

        avg_gain = gain.rolling(window=self.period).mean()
        avg_loss = loss.rolling(window=self.period).mean()

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def analyze(self, symbol, data: pd.DataFrame) -> Signal | None:
        if len(data) < self.period + 2:
            return None

        rsi = self._calculate_rsi(data["Close"])
        current_rsi = rsi.iloc[-1]
        prev_rsi = rsi.iloc[-2]

        if pd.isna(current_rsi):
            return None

        # Crossed into oversold territory
        if current_rsi < self.oversold and prev_rsi >= self.oversold:
            strength = (self.oversold - current_rsi) / self.oversold
            return Signal(
                symbol=symbol,
                side=Side.BUY,
                strength=min(strength, 1.0),
                strategy="rsi",
                metadata={"rsi": round(current_rsi, 2)},
            )

        # Crossed into overbought territory
        if current_rsi > self.overbought and prev_rsi <= self.overbought:
            strength = (current_rsi - self.overbought) / (100 - self.overbought)
            return Signal(
                symbol=symbol,
                side=Side.SELL,
                strength=min(strength, 1.0),
                strategy="rsi",
                metadata={"rsi": round(current_rsi, 2)},
            )

        return None

    def required_data_points(self) -> int:
        return self.period + 5
