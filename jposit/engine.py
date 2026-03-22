"""Core trading engine - orchestrates strategies, data, and execution."""

import logging
import time
from datetime import datetime

from .data_feed import DataFeed
from .models import Order, OrderStatus, Side
from .portfolio import Portfolio
from .strategies import get_strategy

logger = logging.getLogger(__name__)


class TradingEngine:
    """Main trading engine that runs the bot loop."""

    def __init__(self, config):
        self.config = config
        self.symbols = config["symbols"]
        self.data_feed = DataFeed(config)
        self.portfolio = Portfolio(config["initial_capital"], config["risk"])
        self.strategies = []
        self.running = False
        self._callbacks = []
        self.pending_orders = {}  # order_id -> Order

        # Initialize strategies
        for strategy_name in config["strategies"]:
            params = config["strategy_params"].get(strategy_name, {})
            strategy = get_strategy(strategy_name, params)
            self.strategies.append(strategy)
            logger.info(f"Loaded strategy: {strategy_name}")

    def on_update(self, callback):
        """Register a callback for portfolio updates."""
        self._callbacks.append(callback)

    def _notify(self):
        """Notify all registered callbacks."""
        summary = self.portfolio.get_summary()
        for cb in self._callbacks:
            try:
                cb(summary)
            except Exception as e:
                logger.error(f"Callback error: {e}")

    def run_once(self):
        """Run a single iteration of the trading loop."""
        # Update prices
        prices = self.data_feed.get_batch_prices(self.symbols)
        self.portfolio.update_prices(prices)

        # Check stop-loss / take-profit
        sl_tp_signals = self.portfolio.check_stop_loss_take_profit()
        for symbol, side, quantity, reason in sl_tp_signals:
            price = prices.get(symbol, 0)
            if price > 0:
                order = Order(
                    symbol=symbol,
                    side=side,
                    quantity=quantity,
                    price=price,
                    strategy=reason,
                )
                self.portfolio.execute_order(order)

        # Run strategies
        for strategy in self.strategies:
            for symbol in self.symbols:
                data = self.data_feed.get_historical(symbol)
                if data.empty:
                    continue

                signal = strategy.analyze(symbol, data)
                if signal is None:
                    continue

                logger.info(
                    f"Signal: {signal.side.value} {symbol} "
                    f"(strategy={signal.strategy}, strength={signal.strength:.2f})"
                )

                price = prices.get(symbol, 0)
                if price <= 0:
                    continue

                # Calculate position size based on signal strength
                order = None
                if signal.side == Side.BUY:
                    max_spend = (
                        self.portfolio.cash
                        * self.config["risk"]["max_position_pct"]
                        * signal.strength
                    )
                    quantity = int(max_spend / price)
                    if quantity > 0:
                        order = Order(
                            symbol=symbol,
                            side=Side.BUY,
                            quantity=quantity,
                            price=price,
                            strategy=signal.strategy,
                            reason=self._build_reason(signal, price),
                        )

                elif signal.side == Side.SELL:
                    if symbol in self.portfolio.positions:
                        pos = self.portfolio.positions[symbol]
                        sell_qty = int(pos.quantity * signal.strength)
                        if sell_qty > 0:
                            order = Order(
                                symbol=symbol,
                                side=Side.SELL,
                                quantity=sell_qty,
                                price=price,
                                strategy=signal.strategy,
                                reason=self._build_reason(signal, price),
                            )

                if order:
                    self.pending_orders[order.order_id] = order
                    logger.info(
                        f"Pending approval: {order.side.value} {order.quantity} "
                        f"{order.symbol} @ ${order.price:.2f} ({order.reason})"
                    )

        self._notify()

    def run(self, interval_seconds=60):
        """Run the trading loop continuously."""
        self.running = True
        logger.info(
            f"Trading engine started | Mode: {self.config['mode']} | "
            f"Capital: ${self.config['initial_capital']:,.2f} | "
            f"Symbols: {', '.join(self.symbols)}"
        )

        while self.running:
            try:
                self.run_once()
                summary = self.portfolio.get_summary()
                logger.info(
                    f"Portfolio: ${summary['total_value']:,.2f} | "
                    f"P&L: {summary['pnl_pct']:+.2f}% | "
                    f"Positions: {summary['num_positions']} | "
                    f"Trades: {summary['num_trades']}"
                )
            except KeyboardInterrupt:
                logger.info("Shutting down trading engine...")
                self.running = False
                break
            except Exception as e:
                logger.error(f"Engine error: {e}")

            time.sleep(interval_seconds)

    def _build_reason(self, signal, price):
        """Build a human-readable reason for the trade."""
        meta = signal.metadata
        if signal.strategy == "sma_crossover":
            short = meta.get("short_sma", 0)
            long = meta.get("long_sma", 0)
            if signal.side == Side.BUY:
                return (
                    f"Golden Cross detected: 20-day SMA (${short}) crossed above "
                    f"50-day SMA (${long}). This bullish pattern suggests upward "
                    f"momentum. Current price: ${price:.2f}. "
                    f"Signal strength: {signal.strength:.0%}."
                )
            else:
                return (
                    f"Death Cross detected: 20-day SMA (${short}) crossed below "
                    f"50-day SMA (${long}). This bearish pattern suggests downward "
                    f"momentum. Current price: ${price:.2f}. "
                    f"Signal strength: {signal.strength:.0%}."
                )
        elif signal.strategy == "rsi":
            rsi = meta.get("rsi", 0)
            if signal.side == Side.BUY:
                return (
                    f"RSI oversold at {rsi:.1f} (below 30). Stock may be undervalued. "
                    f"Current price: ${price:.2f}. Signal strength: {signal.strength:.0%}."
                )
            else:
                return (
                    f"RSI overbought at {rsi:.1f} (above 70). Stock may be overvalued. "
                    f"Current price: ${price:.2f}. Signal strength: {signal.strength:.0%}."
                )
        elif signal.strategy == "macd":
            macd_val = meta.get("macd", 0)
            macd_signal = meta.get("signal", 0)
            if signal.side == Side.BUY:
                return (
                    f"MACD bullish crossover: MACD ({macd_val:.2f}) crossed above "
                    f"signal line ({macd_signal:.2f}). Current price: ${price:.2f}. "
                    f"Signal strength: {signal.strength:.0%}."
                )
            else:
                return (
                    f"MACD bearish crossover: MACD ({macd_val:.2f}) crossed below "
                    f"signal line ({macd_signal:.2f}). Current price: ${price:.2f}. "
                    f"Signal strength: {signal.strength:.0%}."
                )
        return f"{signal.strategy} signal: {signal.side.value} at ${price:.2f}"

    def approve_order(self, order_id):
        """Approve a pending order for execution."""
        if order_id not in self.pending_orders:
            return False, "Order not found"
        order = self.pending_orders.pop(order_id)
        # Refresh price before executing
        current_price = self.data_feed.get_latest_price(order.symbol)
        if current_price > 0:
            order.price = current_price
        self.portfolio.execute_order(order)
        logger.info(f"Approved: {order.side.value} {order.quantity} {order.symbol} @ ${order.price:.2f}")
        self._notify()
        return True, order

    def reject_order(self, order_id):
        """Reject a pending order."""
        if order_id not in self.pending_orders:
            return False, "Order not found"
        order = self.pending_orders.pop(order_id)
        order.status = OrderStatus.CANCELLED
        logger.info(f"Rejected: {order.side.value} {order.quantity} {order.symbol}")
        self._notify()
        return True, order

    def stop(self):
        """Stop the trading loop."""
        self.running = False
