import os
from dotenv import load_dotenv

# Load .env before importing Config
load_dotenv()

from flask import Flask
from config import Config
from models import db
from routes import meter_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    app.register_blueprint(meter_bp)

    with app.app_context():
        db.create_all()

    return app


app = create_app()


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    # Debug mode is opt-in via FLASK_DEBUG=1 — never enable it by default.
    app.run(host="0.0.0.0", port=port, debug=os.getenv("FLASK_DEBUG") == "1")
