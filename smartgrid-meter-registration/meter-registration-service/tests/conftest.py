import os
import sys

# The app modules (config, models, routes, app) are flat files one directory
# up, imported without a package prefix (e.g. `from models import db`). Make
# them importable regardless of where pytest is invoked from.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Point the app at a throwaway SQLite DB before config.py (which reads
# DATABASE_URL at import time) ever gets imported. load_dotenv() does not
# override an already-set env var, so this wins over .env.
os.environ["DATABASE_URL"] = "sqlite:///./test.db"

import pytest

from app import app as flask_app
from models import db


@pytest.fixture(scope="function")
def client():
    flask_app.config["TESTING"] = True
    with flask_app.app_context():
        db.create_all()
        yield flask_app.test_client()
        db.session.remove()
        db.drop_all()
