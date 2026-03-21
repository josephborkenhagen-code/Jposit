"""Real-time and historical market data fetcher."""

import logging
from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)


class DataFeed:
    """Fetches market data using yfinance."""

    def __init__(self, config):
        self.interval = config["data"].get("interval", "1d")
        self.lookback_days = config["data"].get("lookback_days", 30)
        self._cache = {}

    def get_historical(self, symbol, period=None, interval=None):
        """Fetch historical OHLCV data for a symbol."""
        interval = interval or self.interval
        period = period or f"{self.lookback_days}d"

        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period, interval=interval)
            if df.empty:
                logger.warning(f"No data returned for {symbol}")
                return pd.DataFrame()
            self._cache[symbol] = df
            return df
        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {e}")
            return pd.DataFrame()

    def get_latest_price(self, symbol):
        """Get the latest price for a symbol."""
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period="1d", interval="1m")
            if not data.empty:
                return float(data["Close"].iloc[-1])
            # Fallback to cached data
            if symbol in self._cache and not self._cache[symbol].empty:
                return float(self._cache[symbol]["Close"].iloc[-1])
            return 0.0
        except Exception as e:
            logger.error(f"Error fetching price for {symbol}: {e}")
            return 0.0

    def get_batch_prices(self, symbols):
        """Get latest prices for multiple symbols."""
        prices = {}
        for symbol in symbols:
            prices[symbol] = self.get_latest_price(symbol)
        return prices
