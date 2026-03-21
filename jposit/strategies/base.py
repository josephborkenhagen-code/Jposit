"""Base strategy interface."""

from abc import ABC, abstractmethod

import pandas as pd

from ..models import Signal


class Strategy(ABC):
    """Abstract base class for trading strategies."""

    def __init__(self, params):
        self.params = params
        self.name = self.__class__.__name__

    @abstractmethod
    def analyze(self, symbol, data: pd.DataFrame) -> Signal | None:
        """Analyze market data and return a trading signal, or None."""
        pass

    def required_data_points(self) -> int:
        """Minimum number of data points needed for this strategy."""
        return 50
