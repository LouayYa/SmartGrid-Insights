import os
import sys

# The app modules (app, config, services) are flat files one directory up,
# imported without a package prefix. Make them importable regardless of
# where pytest is invoked from.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

import app as webui


@pytest.fixture
def client():
    webui.app.config["TESTING"] = True
    webui._jobs.clear()
    with webui.app.test_client() as c:
        yield c
    webui._jobs.clear()
