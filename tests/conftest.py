import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_store
from app.main import app
from app.storage import SqliteStore


@pytest.fixture
def store(tmp_path):
    """A fresh file database for every test (TQ-5). A file is used because :memory: ignores WAL."""
    db = SqliteStore(tmp_path / "test.db")
    yield db
    db.close()


@pytest.fixture
def client(store):
    """A test client whose requests all use this test's fresh database."""
    app.dependency_overrides[get_store] = lambda: store
    # raise_server_exceptions=False so a crash gives a 500 reply, like a real server.
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()
