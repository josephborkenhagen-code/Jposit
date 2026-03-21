"""Portfolio manager with position tracking and risk management."""

import logging
from datetime import datetime

from .models import Order, OrderStatus, Position, Side

logger = logging.getLogger(__name__)


class Portfolio:
    """Manages positions, cash, and trade history."""

    def __init__(self, initial_capital, risk_config):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions: dict[str, Position] = {}
        self.trade_history: list[Order] = []
        self.risk_config = risk_config
        self.peak_value = initial_capital
        self.halted = False

    @property
    def total_value(self):
        position_value = sum(p.market_value for p in self.positions.values())
        return self.cash + position_value

    @property
    def total_pnl(self):
        return self.total_value - self.initial_capital

    @property
    def total_pnl_pct(self):
        return self.total_pnl / self.initial_capital

    @property
    def drawdown(self):
        if self.peak_value == 0:
            return 0.0
        return (self.peak_value - self.total_value) / self.peak_value

    def update_prices(self, prices):
        """Update position prices and check risk limits."""
        for symbol, price in prices.items():
            if symbol in self.positions:
                self.positions[symbol].current_price = price

        # Update peak value
        current_value = self.total_value
        if current_value > self.peak_value:
            self.peak_value = current_value

        # Check max drawdown
        if self.drawdown >= self.risk_config["max_drawdown_pct"]:
            if not self.halted:
                logger.warning(
                    f"Max drawdown reached ({self.drawdown:.1%}). Trading halted."
                )
                self.halted = True

    def can_trade(self, symbol, side, quantity, price):
        """Check if a trade passes risk management rules."""
        if self.halted:
            logger.warning("Trading is halted due to max drawdown.")
            return False

        if side == Side.BUY:
            cost = quantity * price
            if cost > self.cash:
                logger.warning(f"Insufficient cash for {symbol}: need ${cost:.2f}, have ${self.cash:.2f}")
                return False

            # Check max position size
            max_position = self.total_value * self.risk_config["max_position_pct"]
            current_position_value = 0
            if symbol in self.positions:
                current_position_value = self.positions[symbol].market_value
            if current_position_value + cost > max_position:
                logger.warning(f"Position size limit reached for {symbol}")
                return False

        elif side == Side.SELL:
            if symbol not in self.positions or self.positions[symbol].quantity < quantity:
                logger.warning(f"Insufficient shares to sell {symbol}")
                return False

        return True

    def execute_order(self, order):
        """Execute an order and update positions."""
        if not self.can_trade(order.symbol, order.side, order.quantity, order.price):
            order.status = OrderStatus.CANCELLED
            return order

        order.fill_price = order.price
        order.status = OrderStatus.FILLED

        if order.side == Side.BUY:
            self._handle_buy(order)
        else:
            self._handle_sell(order)

        self.trade_history.append(order)
        logger.info(
            f"{order.side.value} {order.quantity} {order.symbol} @ ${order.fill_price:.2f}"
        )
        return order

    def _handle_buy(self, order):
        cost = order.quantity * order.fill_price
        self.cash -= cost

        if order.symbol in self.positions:
            pos = self.positions[order.symbol]
            total_qty = pos.quantity + order.quantity
            pos.avg_price = (
                (pos.avg_price * pos.quantity) + (order.fill_price * order.quantity)
            ) / total_qty
            pos.quantity = total_qty
        else:
            stop_loss = order.fill_price * (1 - self.risk_config["stop_loss_pct"])
            take_profit = order.fill_price * (1 + self.risk_config["take_profit_pct"])
            self.positions[order.symbol] = Position(
                symbol=order.symbol,
                quantity=order.quantity,
                avg_price=order.fill_price,
                current_price=order.fill_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
            )

    def _handle_sell(self, order):
        proceeds = order.quantity * order.fill_price
        self.cash += proceeds

        pos = self.positions[order.symbol]
        pos.quantity -= order.quantity
        if pos.quantity <= 0:
            del self.positions[order.symbol]

    def check_stop_loss_take_profit(self):
        """Check if any positions hit stop-loss or take-profit levels."""
        signals = []
        for symbol, pos in list(self.positions.items()):
            if pos.current_price <= pos.stop_loss:
                logger.info(f"Stop-loss triggered for {symbol} @ ${pos.current_price:.2f}")
                signals.append((symbol, Side.SELL, pos.quantity, "stop_loss"))
            elif pos.current_price >= pos.take_profit:
                logger.info(f"Take-profit triggered for {symbol} @ ${pos.current_price:.2f}")
                signals.append((symbol, Side.SELL, pos.quantity, "take_profit"))
        return signals

    def get_summary(self):
        """Get portfolio summary as a dict."""
        return {
            "total_value": round(self.total_value, 2),
            "cash": round(self.cash, 2),
            "pnl": round(self.total_pnl, 2),
            "pnl_pct": round(self.total_pnl_pct * 100, 2),
            "drawdown": round(self.drawdown * 100, 2),
            "num_positions": len(self.positions),
            "num_trades": len(self.trade_history),
            "halted": self.halted,
            "positions": [
                {
                    "symbol": p.symbol,
                    "quantity": p.quantity,
                    "avg_price": round(p.avg_price, 2),
                    "current_price": round(p.current_price, 2),
                    "market_value": round(p.market_value, 2),
                    "pnl": round(p.unrealized_pnl, 2),
                    "pnl_pct": round(p.unrealized_pnl_pct * 100, 2),
                }
                for p in self.positions.values()
            ],
            "recent_trades": [
                {
                    "symbol": t.symbol,
                    "side": t.side.value,
                    "quantity": t.quantity,
                    "price": round(t.fill_price, 2),
                    "strategy": t.strategy,
                    "timestamp": t.timestamp.isoformat(),
                }
                for t in self.trade_history[-20:]
            ],
        }
