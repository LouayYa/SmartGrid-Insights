import logging
import os
import time

from dotenv import load_dotenv

# Load .env before importing Config
load_dotenv()

from flask import Flask, g, request
from config import Config
from models import db
from routes import meter_bp

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("meter-registration")


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    app.register_blueprint(meter_bp)

    @app.before_request
    def start_timer():
        g.request_start = time.perf_counter()

    @app.after_request
    def log_request(response):
        elapsed_ms = (time.perf_counter() - g.get("request_start", time.perf_counter())) * 1000
        logger.info(
            "%s %s -> %d (%.1f ms)",
            request.method, request.path, response.status_code, elapsed_ms,
        )
        return response

    with app.app_context():
        # SQLite (dev/test fallback) gets its schema from the models directly;
        # Postgres schema is managed by Alembic migrations (alembic upgrade head).
        if db.engine.url.get_backend_name() == "sqlite":
            db.create_all()

    return app


app = create_app()


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    # Debug mode is opt-in via FLASK_DEBUG=1 — never enable it by default.
    app.run(host="0.0.0.0", port=port, debug=os.getenv("FLASK_DEBUG") == "1")
