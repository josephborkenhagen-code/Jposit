"""Configuration loader for Jposit trading bot."""

import os
import yaml

DEFAULT_CONFIG = {
    "mode": "paper",
    "initial_capital": 100000,
    "symbols": ["AAPL", "MSFT", "GOOGL"],
    "strategies": ["sma_crossover"],
    "strategy_params": {
        "sma_crossover": {"short_window": 20, "long_window": 50},
        "rsi": {"period": 14, "oversold": 30, "overbought": 70},
        "macd": {"fast_period": 12, "slow_period": 26, "signal_period": 9},
    },
    "risk": {
        "max_position_pct": 0.10,
        "stop_loss_pct": 0.02,
        "take_profit_pct": 0.05,
        "max_drawdown_pct": 0.15,
    },
    "data": {"interval": "1d", "lookback_days": 30},
    "dashboard": {"enabled": True, "host": "0.0.0.0", "port": 5000},
}


def load_config(path="config.yaml"):
    """Load config from YAML file, falling back to defaults."""
    config = DEFAULT_CONFIG.copy()
    if os.path.exists(path):
        with open(path) as f:
            user_config = yaml.safe_load(f) or {}
        _deep_merge(config, user_config)
    return config


def _deep_merge(base, override):
    """Recursively merge override into base dict."""
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
