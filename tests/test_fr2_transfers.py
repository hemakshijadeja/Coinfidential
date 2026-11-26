"""FR-2 (idempotent transfers) tests, one group per acceptance criterion."""

import threading

import pytest

from app.api.auth import issue_token
from app.ledger.transfers import make_transfer, request_hash
from app.storage import SqliteStore


def auth(token, key=None):
    headers = {"Authorization": f"Bearer {token}"}
    if key is not None:
        headers["Idempotency-Key"] = key
    return headers


def count(store, table):
    return store.conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def balance(store, wallet_id):
    return store.get_wallet(wallet_id)["balance"]


def money_state(store):
    """Everything a transfer could change, so tests can check that nothing moved."""
    balances = [tuple(row) for row in store.conn.execute("SELECT id, balance FROM wallets ORDER BY id")]
    return balances, count(store, "transactions"), count(store, "ledger_entries")


@pytest.fixture
def admin_token(store):
    return issue_token(store, "admin")


def make_account(client, store, admin_token, name, wallets):
    """Create an account and return (user token, {currency: wallet_id})."""
    body = {"name": name, "wallets": wallets}
    created = client.post("/accounts", json=body, headers=auth(admin_token)).json()
    wallet_ids = {wallet["currency"]: wallet["wallet_id"] for wallet in created["wallets"]}
    return issue_token(store, "user", created["account_id"]), wallet_ids


@pytest.fixture
def asha(client, store, admin_token):
    return make_account(client, store, admin_token, "Asha", [{"currency": "INR", "starting_balance": 100000}])


@pytest.fixture
def ravi(client, store, admin_token):
    return make_account(client, store, admin_token, "Ravi", [
        {"currency": "INR", "starting_balance": 0},
        {"currency": "USD", "starting_balance": 0},
    ])


@pytest.fixture
def transfer_body(asha, ravi):
    return {"from_wallet_id": asha[1]["INR"], "to_wallet_id": ravi[1]["INR"], "amount": 2500}


# Acceptance criterion 1: a valid transfer moves the exact amount and creates two matching ledger records.

def test_valid_transfer_moves_exact_amount(client, store, asha, ravi, transfer_body):
    token, _ = asha

    response = client.post("/transfers", json=transfer_body, headers=auth(token, "key-1"))

    assert response.status_code == 201
    body = response.json()
    assert body["from_wallet_id"] == transfer_body["from_wallet_id"]
    assert body["to_wallet_id"] == transfer_body["to_wallet_id"]
    assert body["amount"] == 2500
    assert body["currency"] == "INR"
    assert body["created_at"].endswith("Z")
    assert balance(store, transfer_body["from_wallet_id"]) == 97500
    assert balance(store, transfer_body["to_wallet_id"]) == 2500


def test_valid_transfer_creates_two_matching_ledger_records(client, store, asha, transfer_body):
    token, _ = asha
    before = count(store, "ledger_entries")

    response = client.post("/transfers", json=transfer_body, headers=auth(token, "key-1"))
    transfer_id = response.json()["transfer_id"]

    entries = store.conn.execute(
        "SELECT * FROM ledger_entries WHERE transaction_id = ? ORDER BY id", (transfer_id,)
    ).fetchall()
    assert count(store, "ledger_entries") == before + 2
    debit, credit = entries
    assert (debit["wallet_id"], debit["direction"], debit["amount"]) == (transfer_body["from_wallet_id"], "debit", 2500)
    assert (credit["wallet_id"], credit["direction"], credit["amount"]) == (transfer_body["to_wallet_id"], "credit", 2500)
    kind = store.conn.execute("SELECT kind FROM transactions WHERE id = ?", (transfer_id,)).fetchone()[0]
    assert kind == "transfer"


# Acceptance criterion 2: sending the same request again returns the same result, and no money moves.

def test_retry_with_same_key_returns_same_result(client, store, asha, transfer_body):
    token, _ = asha
    first = client.post("/transfers", json=transfer_body, headers=auth(token, "key-1"))
    after_first = money_state(store)

    second = client.post("/transfers", json=transfer_body, headers=auth(token, "key-1"))

    assert second.status_code == 201
    assert second.json() == first.json()
    assert money_state(store) == after_first
    assert balance(store, transfer_body["from_wallet_id"]) == 97500


def test_new_key_makes_a_new_transfer(client, store, asha, transfer_body):
    token, _ = asha
    first = client.post("/transfers", json=transfer_body, headers=auth(token, "key-1"))

    second = client.post("/transfers", json=transfer_body, headers=auth(token, "key-2"))

    assert second.status_code == 201
    assert second.json()["transfer_id"] != first.json()["transfer_id"]
    assert balance(store, transfer_body["from_wallet_id"]) == 95000


def test_failed_transfer_is_saved_under_its_key(client, store, asha, ravi, admin_token):
    # OD-6 and BR-6: a rejected transfer keeps its answer, even after the wallet gets money.
    asha_token, asha_wallets = asha
    ravi_token, ravi_wallets = ravi
    body = {"from_wallet_id": ravi_wallets["INR"], "to_wallet_id": asha_wallets["INR"], "amount": 500}

    first = client.post("/transfers", json=body, headers=auth(ravi_token, "key-1"))
    assert first.status_code == 409
    assert first.json()["error"]["code"] == "insufficient_funds"

    # Asha gives Ravi enough money, then Ravi retries with the same key.
    gift = {"from_wallet_id": asha_wallets["INR"], "to_wallet_id": ravi_wallets["INR"], "amount": 1000}
    client.post("/transfers", json=gift, headers=auth(asha_token, "gift"))
    before = money_state(store)

    retry = client.post("/transfers", json=body, headers=auth(ravi_token, "key-1"))

    assert retry.status_code == 409
    assert retry.json() == first.json()
    assert money_state(store) == before

    # A new key works now.
    fresh = client.post("/transfers", json=body, headers=auth(ravi_token, "key-2"))
    assert fresh.status_code == 201


def test_keys_are_separate_for_each_account(client, store, asha, ravi):
    # Two users can pick the same key without getting each other's result.
    asha_token, asha_wallets = asha
    ravi_token, ravi_wallets = ravi
    to_ravi = {"from_wallet_id": asha_wallets["INR"], "to_wallet_id": ravi_wallets["INR"], "amount": 2000}
    to_asha = {"from_wallet_id": ravi_wallets["INR"], "to_wallet_id": asha_wallets["INR"], "amount": 500}
    client.post("/transfers", json=to_ravi, headers=auth(asha_token, "same-key"))

    response = client.post("/transfers", json=to_asha, headers=auth(ravi_token, "same-key"))

    assert response.status_code == 201
    assert balance(store, ravi_wallets["INR"]) == 1500


# Acceptance criterion 3: reusing a key with a different amount is rejected.

def test_reused_key_with_different_amount_is_rejected(client, store, asha, transfer_body):
    token, _ = asha
    client.post("/transfers", json=transfer_body, headers=auth(token, "key-1"))
    before = money_state(store)

    changed = dict(transfer_body, amount=9999)
    response = client.post("/transfers", json=changed, headers=auth(token, "key-1"))

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "idempotency_key_reused"
    assert money_state(store) == before


def test_reused_key_with_different_wallet_is_rejected(client, store, asha, ravi, transfer_body):
    token, _ = asha
    client.post("/transfers", json=transfer_body, headers=auth(token, "key-1"))
    before = money_state(store)

    changed = dict(transfer_body, to_wallet_id=ravi[1]["USD"])
    response = client.post("/transfers", json=changed, headers=auth(token, "key-1"))

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "idempotency_key_reused"
    assert money_state(store) == before


def test_request_hash_changes_with_the_request():
    # TQ-1: the fingerprint is the same for the same request and different otherwise.
    assert request_hash(1, 2, 100) == request_hash(1, 2, 100)
    assert request_hash(1, 2, 100) != request_hash(1, 2, 101)
    assert request_hash(1, 2, 100) != request_hash(2, 1, 100)


# Acceptance criterion 4: eight identical requests sent at the same moment give exactly one transfer.

def test_eight_identical_requests_at_once_make_one_transfer(tmp_path, store, asha, transfer_body):
    _, asha_wallets = asha
    account_id = store.get_wallet(asha_wallets["INR"])["account_id"]
    before = count(store, "transactions")
    db_path = tmp_path / "test.db"
    start = threading.Barrier(8)
    results = []

    def send():
        # Each thread has its own connection, like separate requests on a real server.
        own_store = SqliteStore(db_path)
        try:
            start.wait()
            results.append(make_transfer(
                own_store, account_id, "same-key",
                transfer_body["from_wallet_id"], transfer_body["to_wallet_id"], transfer_body["amount"],
            ))
        finally:
            own_store.close()

    threads = [threading.Thread(target=send) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len(results) == 8
    assert all(status == 201 for status, _ in results)
    assert len({body["transfer_id"] for _, body in results}) == 1
    assert count(store, "transactions") == before + 1
    assert balance(store, transfer_body["from_wallet_id"]) == 97500
    assert balance(store, transfer_body["to_wallet_id"]) == 2500


# Acceptance criterion 5: if the system fails before finishing, a retry completes the transfer exactly once.

def test_crash_halfway_then_retry_transfers_once(client, store, asha, transfer_body, monkeypatch):
    token, _ = asha
    before = money_state(store)
    real_add_entry = store.add_entry

    def add_entry_then_crash(transaction_id, wallet_id, direction, amount):
        if direction == "credit":
            raise RuntimeError("crash halfway")
        return real_add_entry(transaction_id, wallet_id, direction, amount)

    monkeypatch.setattr(store, "add_entry", add_entry_then_crash)
    crashed = client.post("/transfers", json=transfer_body, headers=auth(token, "key-1"))

    # FR-2.2: the debit, the transfer and the key were all rolled back.
    assert crashed.status_code == 500
    assert "crash halfway" not in crashed.text
    assert money_state(store) == before
    assert count(store, "idempotency_keys") == 0

    monkeypatch.setattr(store, "add_entry", real_add_entry)
    retry = client.post("/transfers", json=transfer_body, headers=auth(token, "key-1"))
    again = client.post("/transfers", json=transfer_body, headers=auth(token, "key-1"))

    assert retry.status_code == 201
    assert again.json() == retry.json()
    assert balance(store, transfer_body["from_wallet_id"]) == 97500
    assert balance(store, transfer_body["to_wallet_id"]) == 2500
    assert count(store, "ledger_entries") == before[2] + 2


# Acceptance criterion 6: 10^12 is accepted when funds allow, and anything larger is rejected.

def test_largest_amount_is_accepted(client, store, admin_token, ravi):
    rich_token, rich_wallets = make_account(
        client, store, admin_token, "Rich", [{"currency": "INR", "starting_balance": 10**12}]
    )
    body = {"from_wallet_id": rich_wallets["INR"], "to_wallet_id": ravi[1]["INR"], "amount": 10**12}

    response = client.post("/transfers", json=body, headers=auth(rich_token, "big"))

    assert response.status_code == 201
    assert balance(store, rich_wallets["INR"]) == 0
    assert balance(store, ravi[1]["INR"]) == 10**12


def test_amount_over_limit_is_rejected(client, store, asha, transfer_body):
    token, _ = asha
    before = money_state(store)

    body = dict(transfer_body, amount=10**12 + 1)
    response = client.post("/transfers", json=body, headers=auth(token, "too-big"))

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert money_state(store) == before


# FR-2.1: every transfer needs an idempotency key.

@pytest.mark.parametrize("key", [None, "", "   "])
def test_missing_key_is_rejected(client, store, asha, transfer_body, key):
    token, _ = asha
    before = money_state(store)

    response = client.post("/transfers", json=transfer_body, headers=auth(token, key))

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "missing_idempotency_key"
    assert money_state(store) == before


def test_very_long_key_is_rejected(client, store, asha, transfer_body):
    token, _ = asha

    response = client.post("/transfers", json=transfer_body, headers=auth(token, "k" * 256))

    assert response.status_code == 422


# FR-2.4: users can only send money from their own wallets.

def test_cannot_send_from_someone_elses_wallet(client, store, asha, ravi):
    _, asha_wallets = asha
    ravi_token, ravi_wallets = ravi
    before = money_state(store)
    body = {"from_wallet_id": asha_wallets["INR"], "to_wallet_id": ravi_wallets["INR"], "amount": 2500}

    response = client.post("/transfers", json=body, headers=auth(ravi_token, "steal"))

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"
    assert money_state(store) == before


def test_cannot_send_from_system_wallet(client, store, asha):
    token, asha_wallets = asha
    before = money_state(store)
    body = {"from_wallet_id": store.system_wallet_id("INR"), "to_wallet_id": asha_wallets["INR"], "amount": 100}

    response = client.post("/transfers", json=body, headers=auth(token, "free-money"))

    assert response.status_code == 403
    assert money_state(store) == before


def test_admin_cannot_send_money(client, store, admin_token, transfer_body):
    before = money_state(store)

    response = client.post("/transfers", json=transfer_body, headers=auth(admin_token, "key-1"))

    assert response.status_code == 403
    assert money_state(store) == before


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer not-a-real-token"}])
def test_transfer_needs_valid_token(client, store, transfer_body, headers):
    before = money_state(store)

    response = client.post("/transfers", json=transfer_body, headers=dict(headers, **{"Idempotency-Key": "k"}))

    assert response.status_code == 401
    assert money_state(store) == before


# FR-2.5 and other bad requests: rejected, and no money moves.

@pytest.mark.parametrize("bad_amount", [-500, 0, 10.5, "100", True, None])
def test_bad_amount_is_rejected(client, store, asha, transfer_body, bad_amount):
    token, _ = asha
    before = money_state(store)

    body = dict(transfer_body, amount=bad_amount)
    response = client.post("/transfers", json=body, headers=auth(token, "bad"))

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert money_state(store) == before


@pytest.mark.parametrize("change", [
    {"from_wallet_id": "abc"},
    {"to_wallet_id": 0},
    {"to_wallet_id": 2**63},
    {"extra": 1},
])
def test_bad_body_is_rejected(client, store, asha, transfer_body, change):
    token, _ = asha
    before = money_state(store)

    response = client.post("/transfers", json=dict(transfer_body, **change), headers=auth(token, "bad"))

    assert response.status_code == 422
    assert money_state(store) == before


def test_insufficient_funds_is_rejected(client, store, asha, transfer_body):
    token, _ = asha
    before = money_state(store)

    body = dict(transfer_body, amount=100001)
    response = client.post("/transfers", json=body, headers=auth(token, "too-much"))

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "insufficient_funds"
    assert money_state(store) == before


def test_different_currencies_are_rejected(client, store, asha, ravi, transfer_body):
    token, _ = asha
    before = money_state(store)

    body = dict(transfer_body, to_wallet_id=ravi[1]["USD"])
    response = client.post("/transfers", json=body, headers=auth(token, "fx"))

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert money_state(store) == before


def test_cannot_send_to_same_wallet(client, store, asha, transfer_body):
    token, _ = asha
    before = money_state(store)

    body = dict(transfer_body, to_wallet_id=transfer_body["from_wallet_id"])
    response = client.post("/transfers", json=body, headers=auth(token, "self"))

    assert response.status_code == 422
    assert money_state(store) == before


def test_missing_receiver_is_404(client, store, asha, transfer_body):
    token, _ = asha
    before = money_state(store)

    body = dict(transfer_body, to_wallet_id=9999)
    response = client.post("/transfers", json=body, headers=auth(token, "nobody"))

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
    assert money_state(store) == before
