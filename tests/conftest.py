import pytest

from app.storage import SqliteStore


@pytest.fixture
def store(tmp_path):
    """A fresh file database for every test (TQ-5). A file is used because :memory: ignores WAL."""
    db = SqliteStore(tmp_path / "test.db")
    yield db
    db.close()
