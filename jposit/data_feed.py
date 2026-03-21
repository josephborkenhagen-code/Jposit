"""Real-time and historical market data fetcher using Yahoo Finance API."""

import logging
from datetime import datetime, timedelta

import pandas as pd
import requests

logger = logging.getLogger(__name__)

# Yahoo Finance chart API (no auth required)
YF_BASE_URL = "https://query1.finance.yahoo.com/v8/finance/chart"

INTERVAL_MAP = {
    "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m",
    "1h": "1h", "1d": "1d", "1wk": "1wk",
}


class DataFeed:
    """Fetches market data from Yahoo Finance."""

    def __init__(self, config):
        self.interval = config["data"].get("interval", "1d")
        self.lookback_days = config["data"].get("lookback_days", 30)
        self._cache = {}
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })

    def get_historical(self, symbol, period=None, interval=None):
        """Fetch historical OHLCV data for a symbol."""
        interval = interval or self.interval
        lookback = int((period or "").replace("d", "") or self.lookback_days)

        try:
            end = datetime.now()
            start = end - timedelta(days=lookback)

            params = {
                "period1": int(start.timestamp()),
                "period2": int(end.timestamp()),
                "interval": INTERVAL_MAP.get(interval, "1d"),
            }

            resp = self._session.get(f"{YF_BASE_URL}/{symbol}", params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            result = data.get("chart", {}).get("result", [])
            if not result:
                logger.warning(f"No data returned for {symbol}")
                return pd.DataFrame()

            quote = result[0]
            timestamps = quote.get("timestamp", [])
            ohlcv = quote.get("indicators", {}).get("quote", [{}])[0]

            if not timestamps:
                return pd.DataFrame()

            df = pd.DataFrame({
                "Open": ohlcv.get("open", []),
                "High": ohlcv.get("high", []),
                "Low": ohlcv.get("low", []),
                "Close": ohlcv.get("close", []),
                "Volume": ohlcv.get("volume", []),
            }, index=pd.to_datetime(timestamps, unit="s"))

            df.dropna(subset=["Close"], inplace=True)
            self._cache[symbol] = df
            return df

        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {e}")
            if symbol in self._cache:
                return self._cache[symbol]
            return pd.DataFrame()

    def get_latest_price(self, symbol):
        """Get the latest price for a symbol."""
        try:
            params = {"interval": "1d", "range": "1d"}
            resp = self._session.get(f"{YF_BASE_URL}/{symbol}", params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            result = data.get("chart", {}).get("result", [])
            if result:
                meta = result[0].get("meta", {})
                price = meta.get("regularMarketPrice", 0)
                if price:
                    return float(price)

            # Fallback to cached data
            if symbol in self._cache and not self._cache[symbol].empty:
                return float(self._cache[symbol]["Close"].iloc[-1])
            return 0.0

        except Exception as e:
            logger.error(f"Error fetching price for {symbol}: {e}")
            if symbol in self._cache and not self._cache[symbol].empty:
                return float(self._cache[symbol]["Close"].iloc[-1])
            return 0.0

    def get_batch_prices(self, symbols):
        """Get latest prices for multiple symbols."""
        prices = {}
        for symbol in symbols:
            prices[symbol] = self.get_latest_price(symbol)
        return prices
