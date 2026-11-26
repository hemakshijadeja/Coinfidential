"""SqliteStore: the only file that runs SQL (ADR-0006)."""

import hashlib
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from app.errors import StoreBusyError, StoreError, StoreIntegrityError

SCHEMA_FILE = Path(__file__).with_name("schema.sql")
BUSY_TIMEOUT_MS = 5000
# prev_hash used by the very first ledger entry (ADR-0003).
GENESIS_HASH = "0" * 64


def connect(path: str | Path) -> sqlite3.Connection:
    """Open a connection with all the pragmas every connection needs."""
    # isolation_level=None means Python never starts transactions on its own; we do it ourselves.
    # check_same_thread=False because FastAPI may run a request's dependency and route in
    # different threads. It is still safe: each request opens its own connection and uses it
    # one step at a time.
    conn = sqlite3.connect(path, isolation_level=None, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    # Needed so INSERT OR REPLACE fires the ledger_no_delete trigger.
    conn.execute("PRAGMA recursive_triggers=ON")
    conn.execute("PRAGMA synchronous=FULL")
    conn.execute(f"PRAGMA busy_timeout={BUSY_TIMEOUT_MS}")
    return conn


def check_amount(amount: int) -> None:
    """Money is a positive whole number of minor units. bool counts as int in Python, so reject it."""
    if type(amount) is not int or amount <= 0:
        raise ValueError("amount must be a positive integer in minor units")


def entry_hash(prev_hash: str, transaction_id: int, wallet_id: int, direction: str, amount: int, created_at: str) -> str:
    """SHA-256 of the previous hash plus this entry's own fields."""
    text = f"{prev_hash}|{transaction_id}|{wallet_id}|{direction}|{amount}|{created_at}"
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def to_store_error(error: sqlite3.Error) -> StoreError:
    """Turn a raw sqlite3 error into one of our own errors."""
    if isinstance(error, sqlite3.IntegrityError):
        return StoreIntegrityError(str(error))
    if "locked" in str(error) or "busy" in str(error):
        return StoreBusyError("the database is busy, try again")
    return StoreError(str(error))


class SqliteStore:
    def __init__(self, path: str | Path) -> None:
        self.conn = connect(path)
        # The schema only uses IF NOT EXISTS / OR IGNORE, so this is safe on an existing database.
        self.conn.executescript(SCHEMA_FILE.read_text(encoding="utf-8"))

    def close(self) -> None:
        self.conn.close()

    @contextmanager
    def write_transaction(self):
        """BEGIN IMMEDIATE, then COMMIT on success or ROLLBACK on any error (ADR-0004)."""
        try:
            self.conn.execute("BEGIN IMMEDIATE")
        except sqlite3.Error as error:
            raise to_store_error(error) from error
        try:
            yield self
            self.conn.execute("COMMIT")
        except sqlite3.Error as error:
            self._rollback()
            raise to_store_error(error) from error
        except BaseException:
            self._rollback()
            raise

    def _rollback(self) -> None:
        # Some errors make SQLite roll back by itself, so only roll back if still open.
        if self.conn.in_transaction:
            self.conn.execute("ROLLBACK")

    # The methods below are meant to be called inside write_transaction().

    def create_account(self, name: str) -> int:
        cursor = self.conn.execute("INSERT INTO accounts (name) VALUES (?)", (name,))
        return cursor.lastrowid

    def create_wallet(self, account_id: int, currency: str) -> int:
        cursor = self.conn.execute(
            "INSERT INTO wallets (account_id, currency) VALUES (?, ?)", (account_id, currency)
        )
        return cursor.lastrowid

    def get_wallet(self, wallet_id: int) -> dict | None:
        row = self.conn.execute("SELECT * FROM wallets WHERE id = ?", (wallet_id,)).fetchone()
        return dict(row) if row else None

    def system_wallet_id(self, currency: str) -> int:
        row = self.conn.execute(
            "SELECT wallets.id FROM wallets JOIN accounts ON accounts.id = wallets.account_id "
            "WHERE accounts.is_system = 1 AND wallets.currency = ?",
            (currency,),
        ).fetchone()
        if row is None:
            raise StoreError(f"no system wallet for {currency}")
        return row["id"]

    def credit(self, wallet_id: int, amount: int) -> None:
        check_amount(amount)
        self.conn.execute("UPDATE wallets SET balance = balance + ? WHERE id = ?", (amount, wallet_id))

    def debit(self, wallet_id: int, amount: int) -> bool:
        """Guarded debit. Returns False if a normal wallet does not have enough money.

        Only system wallets may go negative (BR-2). A CHECK cannot look at another
        table, so the rule lives in the WHERE clause.
        """
        check_amount(amount)
        cursor = self.conn.execute(
            "UPDATE wallets SET balance = balance - :amount "
            "WHERE id = :wallet_id "
            "AND (balance >= :amount "
            "     OR account_id IN (SELECT id FROM accounts WHERE is_system = 1))",
            {"amount": amount, "wallet_id": wallet_id},
        )
        return cursor.rowcount == 1

    def add_transaction(self, kind: str, reverses: int | None = None) -> int:
        cursor = self.conn.execute(
            "INSERT INTO transactions (kind, reverses) VALUES (?, ?)", (kind, reverses)
        )
        return cursor.lastrowid

    def add_entry(self, transaction_id: int, wallet_id: int, direction: str, amount: int) -> int:
        """Append one ledger entry and link it to the previous entry's hash."""
        check_amount(amount)
        last = self.conn.execute("SELECT hash FROM ledger_entries ORDER BY id DESC LIMIT 1").fetchone()
        prev_hash = last["hash"] if last else GENESIS_HASH
        created_at = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
        new_hash = entry_hash(prev_hash, transaction_id, wallet_id, direction, amount, created_at)
        cursor = self.conn.execute(
            "INSERT INTO ledger_entries "
            "(transaction_id, wallet_id, direction, amount, prev_hash, hash, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (transaction_id, wallet_id, direction, amount, prev_hash, new_hash, created_at),
        )
        return cursor.lastrowid

    def get_idempotency(self, account_id: int, idem_key: str) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM idempotency_keys WHERE account_id = ? AND idem_key = ?",
            (account_id, idem_key),
        ).fetchone()
        return dict(row) if row else None

    def save_idempotency(
        self,
        account_id: int,
        idem_key: str,
        request_hash: str,
        transaction_id: int | None,
        status_code: int,
        response_body: str,
    ) -> None:
        self.conn.execute(
            "INSERT INTO idempotency_keys "
            "(account_id, idem_key, request_hash, transaction_id, status_code, response_body) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (account_id, idem_key, request_hash, transaction_id, status_code, response_body),
        )

    def save_token(self, token_hash: str, account_id: int | None, role: str, expires_at: str) -> None:
        """Save a token's hash, never the token itself (ADR-0005)."""
        self.conn.execute(
            "INSERT INTO tokens (token_hash, account_id, role, expires_at) VALUES (?, ?, ?, ?)",
            (token_hash, account_id, role, expires_at),
        )

    def get_token(self, token_hash: str) -> dict | None:
        row = self.conn.execute("SELECT * FROM tokens WHERE token_hash = ?", (token_hash,)).fetchone()
        return dict(row) if row else None
