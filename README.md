# Jposit - Real-Time Stock Trading Bot

A Python-based automated stock trading bot with multiple strategy support, paper trading, and a real-time web dashboard.

## Features

- **Multiple Strategies**: SMA Crossover, RSI, MACD - or build your own
- **Paper Trading**: Test strategies risk-free with simulated trades
- **Live Trading**: Connect to Alpaca API for real market execution
- **Web Dashboard**: Real-time portfolio monitoring at `http://localhost:5000`
- **Risk Management**: Position sizing, stop-losses, and max drawdown limits
- **Real-Time Data**: Live market data via yfinance

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run with paper trading (default)
python -m jposit

# Run with web dashboard
python -m jposit --dashboard

# Run a specific strategy
python -m jposit --strategy sma_crossover --symbols AAPL MSFT GOOGL
```

## Configuration

Copy `config.example.yaml` to `config.yaml` and customize:

```yaml
mode: paper          # paper or live
initial_capital: 100000
symbols:
  - AAPL
  - MSFT
  - GOOGL
strategies:
  - sma_crossover
risk:
  max_position_pct: 0.1
  stop_loss_pct: 0.02
```

## Strategies

| Strategy | Description |
|----------|-------------|
| `sma_crossover` | Buy when short SMA crosses above long SMA, sell on cross below |
| `rsi` | Buy when RSI < 30 (oversold), sell when RSI > 70 (overbought) |
| `macd` | Trade on MACD signal line crossovers |

## Disclaimer

This software is for educational purposes only. Trading stocks involves risk. Past performance does not guarantee future results. Always do your own research before trading with real money.
