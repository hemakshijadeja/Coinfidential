"""Tests for the SQLite storage layer. Each test gets a fresh database from conftest.py."""

import pytest

from app.errors import StoreBusyError, StoreIntegrityError
from app.storage import SqliteStore
from app.storage.sqlite_store import GENESIS_HASH, entry_hash


def pragma(store, name):
    return store.conn.execute(f"PRAGMA {name}").fetchone()[0]


def make_wallet(store, currency="INR", funding=0):
    """Create an account and wallet, funded from the system wallet like FR-1.2."""
    with store.write_transaction():
        account_id = store.create_account("Asha")
        wallet_id = store.create_wallet(account_id, currency)
        if funding:
            system_id = store.system_wallet_id(currency)
            tx = store.add_transaction("funding")
            assert store.debit(system_id, funding)
            store.credit(wallet_id, funding)
            store.add_entry(tx, system_id, "debit", funding)
            store.add_entry(tx, wallet_id, "credit", funding)
    return account_id, wallet_id


def test_connection_pragmas(store):
    assert pragma(store, "journal_mode") == "wal"
    assert pragma(store, "foreign_keys") == 1
    assert pragma(store, "recursive_triggers") == 1
    assert pragma(store, "synchronous") == 2  # 2 means FULL
    assert pragma(store, "busy_timeout") == 5000


def test_schema_can_be_applied_twice(tmp_path):
    SqliteStore(tmp_path / "again.db").close()
    store = SqliteStore(tmp_path / "again.db")
    count = store.conn.execute("SELECT COUNT(*) FROM accounts WHERE is_system = 1").fetchone()[0]
    store.close()

    assert count == 2


def test_system_wallets_exist_with_zero_balance(store):
    for currency in ("INR", "USD"):
        wallet = store.get_wallet(store.system_wallet_id(currency))
        assert wallet["currency"] == currency
        assert wallet["balance"] == 0


def test_only_inr_and_usd_wallets(store):
    with pytest.raises(StoreIntegrityError):
        make_wallet(store, currency="EUR")


def test_one_wallet_per_currency(store):
    account_id, _ = make_wallet(store)

    with pytest.raises(StoreIntegrityError), store.write_transaction():
        store.create_wallet(account_id, "INR")


def test_funding_is_balanced(store):
    _, wallet_id = make_wallet(store, funding=10_000)

    assert store.get_wallet(wallet_id)["balance"] == 10_000
    assert store.get_wallet(store.system_wallet_id("INR"))["balance"] == -10_000
    totals = dict(store.conn.execute(
        "SELECT direction, SUM(amount) FROM ledger_entries GROUP BY direction"
    ).fetchall())
    assert totals == {"debit": 10_000, "credit": 10_000}


@pytest.mark.parametrize("amount", [0, -5, 10.5, "100", True])
def test_amount_must_be_positive_integer(store, amount):
    _, wallet_id = make_wallet(store)

    with pytest.raises(ValueError), store.write_transaction():
        store.credit(wallet_id, amount)


def test_database_rejects_float_amount(store):
    # Even raw SQL that skips check_amount() cannot store a float in the ledger.
    _, wallet_id = make_wallet(store)

    with pytest.raises(StoreIntegrityError), store.write_transaction():
        tx = store.add_transaction("funding")
        store.conn.execute(
            "INSERT INTO ledger_entries "
            "(transaction_id, wallet_id, direction, amount, prev_hash, hash, created_at) "
            "VALUES (?, ?, 'credit', 10.5, 'x', 'y', 'now')",
            (tx, wallet_id),
        )


def test_debit_fails_without_enough_money(store):
    _, wallet_id = make_wallet(store, funding=100)

    with store.write_transaction():
        assert store.debit(wallet_id, 101) is False

    assert store.get_wallet(wallet_id)["balance"] == 100


def test_error_rolls_back_everything(store):
    _, wallet_id = make_wallet(store, funding=100)

    with pytest.raises(RuntimeError), store.write_transaction():
        store.debit(wallet_id, 50)
        store.add_transaction("transfer")
        raise RuntimeError("crash halfway")

    assert store.get_wallet(wallet_id)["balance"] == 100
    assert store.conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0] == 1


@pytest.mark.parametrize("sql", [
    "UPDATE ledger_entries SET amount = 1",
    "DELETE FROM ledger_entries",
    # Without recursive_triggers=ON this REPLACE would quietly rewrite entry 1.
    (
        "INSERT OR REPLACE INTO ledger_entries "
        "(id, transaction_id, wallet_id, direction, amount, prev_hash, hash, created_at) "
        "VALUES (1, 1, 1, 'debit', 1, 'x', 'y', 'now')"
    ),
    "UPDATE transactions SET kind = 'transfer'",
    "DELETE FROM transactions",
])
def test_ledger_and_transactions_are_append_only(store, sql):
    make_wallet(store, funding=100)

    with pytest.raises(StoreIntegrityError, match="append-only"), store.write_transaction():
        store.conn.execute(sql)

    assert store.conn.execute("SELECT COUNT(*) FROM ledger_entries").fetchone()[0] == 2


def test_transfer_can_only_be_reversed_once(store):
    with store.write_transaction():
        transfer_id = store.add_transaction("transfer")
        store.add_transaction("reversal", reverses=transfer_id)

    with pytest.raises(StoreIntegrityError), store.write_transaction():
        store.add_transaction("reversal", reverses=transfer_id)


def test_reversal_must_point_to_a_transaction(store):
    with pytest.raises(StoreIntegrityError), store.write_transaction():
        store.add_transaction("reversal")


def test_entries_form_a_hash_chain(store):
    make_wallet(store, funding=100)

    rows = store.conn.execute("SELECT * FROM ledger_entries ORDER BY id").fetchall()
    assert rows[0]["prev_hash"] == GENESIS_HASH
    assert rows[1]["prev_hash"] == rows[0]["hash"]
    for row in rows:
        expected = entry_hash(
            row["prev_hash"], row["transaction_id"], row["wallet_id"],
            row["direction"], row["amount"], row["created_at"],
        )
        assert row["hash"] == expected


def test_idempotency_key_saved_once(store):
    account_id, _ = make_wallet(store)

    with store.write_transaction():
        store.save_idempotency(account_id, "key-1", "abc", None, 201, '{"ok": true}')

    saved = store.get_idempotency(account_id, "key-1")
    assert saved["status_code"] == 201
    assert saved["response_body"] == '{"ok": true}'
    assert store.get_idempotency(account_id, "key-2") is None

    with pytest.raises(StoreIntegrityError), store.write_transaction():
        store.save_idempotency(account_id, "key-1", "abc", None, 201, "{}")


def test_second_writer_gets_busy_error(tmp_path):
    first = SqliteStore(tmp_path / "busy.db")
    second = SqliteStore(tmp_path / "busy.db")
    second.conn.execute("PRAGMA busy_timeout=0")  # fail at once instead of waiting 5 s

    # first holds the write lock, so second cannot start its own write.
    with first.write_transaction(), pytest.raises(StoreBusyError), second.write_transaction():
        pass

    first.close()
    second.close()
