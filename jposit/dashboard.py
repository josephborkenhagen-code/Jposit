"""Web dashboard for monitoring the trading bot."""

import json
import logging
import threading

from flask import Flask, render_template
from flask_socketio import SocketIO

logger = logging.getLogger(__name__)


def create_app(engine):
    """Create the Flask dashboard app."""
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "jposit-dashboard"
    socketio = SocketIO(app, cors_allowed_origins="*")

    # Register engine callback to push updates via WebSocket
    def on_portfolio_update(summary):
        socketio.emit("portfolio_update", summary)

    engine.on_update(on_portfolio_update)

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

    return app, socketio


def run_dashboard(engine, host="0.0.0.0", port=5000):
    """Run the dashboard in a background thread."""
    app, socketio = create_app(engine)

    def start():
        socketio.run(app, host=host, port=port, allow_unsafe_werkzeug=True)

    thread = threading.Thread(target=start, daemon=True)
    thread.start()
    logger.info(f"Dashboard running at http://{host}:{port}")
    return app, socketio
