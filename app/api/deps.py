"""Gives each request its own store. Tests swap this with app.dependency_overrides."""

import os

from app.storage import SqliteStore

DB_PATH = os.environ.get("COINFIDENTIAL_DB", "coinfidential.db")


def get_store():
    store = SqliteStore(DB_PATH)
    try:
        yield store
    finally:
        store.close()
