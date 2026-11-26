"""Our own error classes, so the layers above storage never see raw sqlite3 errors."""


class StoreError(Exception):
    """Something went wrong in the storage layer."""


class StoreBusyError(StoreError):
    """The database stayed locked longer than busy_timeout (ADR-0004)."""


class StoreIntegrityError(StoreError):
    """A constraint or trigger rejected the write, for example editing the ledger."""
