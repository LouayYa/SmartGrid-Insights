import os
import sys

# The app modules (config, database, main, routes...) are flat files one
# directory up, imported without a package prefix (e.g. `from database import
# get_db`). Make them importable regardless of where pytest is invoked from.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Point the app at a throwaway SQLite DB before database.py (which reads
# DATABASE_URL and connects at import time) ever gets imported. load_dotenv()
# does not override an already-set env var, so this wins over .env.
os.environ["DATABASE_URL"] = "sqlite:///./test.db"

import pytest
from fastapi.testclient import TestClient

from database import Base, SessionLocal, engine, get_db
from main import app


@pytest.fixture(scope="function")
def db():
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
