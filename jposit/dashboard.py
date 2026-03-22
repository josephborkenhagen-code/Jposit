"""Web dashboard for monitoring the trading bot."""

import json
import logging
import threading

from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO

logger = logging.getLogger(__name__)


def create_app(engine):
    """Create the Flask dashboard app."""
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "jposit-dashboard"
    socketio = SocketIO(app, cors_allowed_origins="*")

    # Register engine callback to push updates via WebSocket
    def on_portfolio_update(summary):
        # Include pending orders in the update
        summary["pending_orders"] = _serialize_pending(engine)
        socketio.emit("portfolio_update", summary)

    engine.on_update(on_portfolio_update)

    # Push pending orders when they arrive
    original_run_once = engine.run_once

    def patched_run_once():
        original_run_once()
        if engine.pending_orders:
            socketio.emit("pending_orders", _serialize_pending(engine))

    engine.run_once = patched_run_once

    @app.route("/")
    def index():
        return render_template("dashboard.html")

    @app.route("/api/portfolio")
    def api_portfolio():
        return json.dumps(engine.portfolio.get_summary())

    @app.route("/api/config")
    def api_config():
        safe_config = {
            k: v for k, v in engine.config.items() if k != "alpaca"
        }
        return json.dumps(safe_config)

    @app.route("/api/pending")
    def api_pending():
        return jsonify(_serialize_pending(engine))

    @app.route("/api/approve/<order_id>", methods=["POST"])
    def api_approve(order_id):
        success, result = engine.approve_order(order_id)
        if success:
            return jsonify({"status": "approved", "order_id": order_id})
        return jsonify({"status": "error", "message": result}), 404

    @app.route("/api/reject/<order_id>", methods=["POST"])
    def api_reject(order_id):
        success, result = engine.reject_order(order_id)
        if success:
            return jsonify({"status": "rejected", "order_id": order_id})
        return jsonify({"status": "error", "message": result}), 404

    @app.route("/api/test-signal", methods=["POST"])
    def api_test_signal():
        """Create a fake pending order to test the notification UI."""
        from .models import Order, Side
        import random
        symbol = random.choice(engine.symbols)
        price = round(random.uniform(150, 220), 2)
        qty = random.randint(10, 100)
        side = random.choice([Side.BUY, Side.SELL])
        if side == Side.BUY:
            reason = (
                f"Golden Cross detected: 20-day SMA (${price + 2:.2f}) crossed above "
                f"50-day SMA (${price - 3:.2f}). This bullish pattern suggests upward "
                f"momentum. Current price: ${price:.2f}. Signal strength: 85%."
            )
        else:
            reason = (
                f"Death Cross detected: 20-day SMA (${price - 2:.2f}) crossed below "
                f"50-day SMA (${price + 3:.2f}). This bearish pattern suggests downward "
                f"momentum. Current price: ${price:.2f}. Signal strength: 72%."
            )
        order = Order(
            symbol=symbol, side=side, quantity=qty, price=price,
            strategy="sma_crossover", reason=reason,
        )
        engine.pending_orders[order.order_id] = order
        socketio.emit("pending_orders", _serialize_pending(engine))
        return jsonify({"status": "ok", "order_id": order.order_id})

    return app, socketio


def _serialize_pending(engine):
    """Serialize pending orders for the API/websocket."""
    orders = []
    for oid, order in engine.pending_orders.items():
        orders.append({
            "order_id": order.order_id,
            "symbol": order.symbol,
            "side": order.side.value,
            "quantity": order.quantity,
            "price": order.price,
            "total": round(order.quantity * order.price, 2),
            "strategy": order.strategy,
            "reason": order.reason,
            "timestamp": order.timestamp.isoformat(),
        })
    return orders


def run_dashboard(engine, host="0.0.0.0", port=5000):
    """Run the dashboard in a background thread."""
    app, socketio = create_app(engine)

    def start():
        socketio.run(app, host=host, port=port, allow_unsafe_werkzeug=True)

    thread = threading.Thread(target=start, daemon=True)
    thread.start()
    logger.info(f"Dashboard running at http://{host}:{port}")
    return app, socketio
