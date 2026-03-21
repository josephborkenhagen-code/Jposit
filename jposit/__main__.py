"""CLI entry point for Jposit trading bot."""

import argparse
import logging
import sys

from .config import load_config
from .engine import TradingEngine


def main():
    parser = argparse.ArgumentParser(description="Jposit - Real-Time Stock Trading Bot")
    parser.add_argument("--config", default="config.yaml", help="Path to config file")
    parser.add_argument("--symbols", nargs="+", help="Symbols to trade (overrides config)")
    parser.add_argument(
        "--strategy",
        choices=["sma_crossover", "rsi", "macd"],
        help="Strategy to use (overrides config)",
    )
    parser.add_argument("--capital", type=float, help="Initial capital (overrides config)")
    parser.add_argument(
        "--interval", type=int, default=60, help="Trading loop interval in seconds"
    )
    parser.add_argument("--dashboard", action="store_true", help="Enable web dashboard")
    parser.add_argument(
        "--mode", choices=["paper", "live"], help="Trading mode (overrides config)"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    args = parser.parse_args()

    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Load config
    config = load_config(args.config)

    # Apply CLI overrides
    if args.symbols:
        config["symbols"] = args.symbols
    if args.strategy:
        config["strategies"] = [args.strategy]
    if args.capital:
        config["initial_capital"] = args.capital
    if args.mode:
        config["mode"] = args.mode

    # Safety check for live mode
    if config["mode"] == "live":
        logging.warning("LIVE TRADING MODE - Real money will be used!")
        response = input("Type 'YES' to confirm live trading: ")
        if response != "YES":
            print("Aborted. Use --mode paper for paper trading.")
            sys.exit(0)

    # Create engine
    engine = TradingEngine(config)

    # Start dashboard if requested
    if args.dashboard or config["dashboard"].get("enabled"):
        from .dashboard import run_dashboard

        host = config["dashboard"].get("host", "0.0.0.0")
        port = config["dashboard"].get("port", 5000)
        run_dashboard(engine, host, port)

    # Run trading loop
    print(f"\n{'='*50}")
    print(f"  Jposit Trading Bot v1.0")
    print(f"  Mode: {config['mode'].upper()}")
    print(f"  Capital: ${config['initial_capital']:,.2f}")
    print(f"  Symbols: {', '.join(config['symbols'])}")
    print(f"  Strategies: {', '.join(config['strategies'])}")
    print(f"  Interval: {args.interval}s")
    print(f"{'='*50}\n")

    try:
        engine.run(interval_seconds=args.interval)
    except KeyboardInterrupt:
        print("\nShutting down...")
        engine.stop()


if __name__ == "__main__":
    main()
