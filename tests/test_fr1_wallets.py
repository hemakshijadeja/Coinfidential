"""FR-1 (wallet initialization) tests through the API, one group per acceptance criterion."""

import pytest

from app.api.auth import issue_token

GOOD_BODY = {
    "name": "Asha",
    "wallets": [
        {"currency": "INR", "starting_balance": 100000},
        {"currency": "USD", "starting_balance": 0},
    ],
}


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def count(store, table):
    return store.conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def table_counts(store):
    return {table: count(store, table) for table in ("accounts", "wallets", "transactions", "ledger_entries")}


@pytest.fixture
def admin_token(store):
    return issue_token(store, "admin")


# Acceptance criterion 1: two wallets, and exactly two matching ledger records for INR.

def test_create_account_with_two_wallets(client, store, admin_token):
    response = client.post("/accounts", json=GOOD_BODY, headers=auth(admin_token))

    assert response.status_code == 201
    body = response.json()
    inr, usd = body["wallets"]
    assert inr["currency"] == "INR" and inr["balance"] == 100000
    assert usd["currency"] == "USD" and usd["balance"] == 0

    for wallet in body["wallets"]:
        saved = store.get_wallet(wallet["wallet_id"])
        assert saved["account_id"] == body["account_id"]
        assert saved["balance"] == wallet["balance"]


def test_starting_balance_is_two_matching_ledger_records(client, store, admin_token):
    response = client.post("/accounts", json=GOOD_BODY, headers=auth(admin_token))
    inr_wallet_id = response.json()["wallets"][0]["wallet_id"]
    system_inr = store.system_wallet_id("INR")

    entries = store.conn.execute("SELECT * FROM ledger_entries ORDER BY id").fetchall()
    assert len(entries) == 2
    debit, credit = entries
    assert (debit["wallet_id"], debit["direction"], debit["amount"]) == (system_inr, "debit", 100000)
    assert (credit["wallet_id"], credit["direction"], credit["amount"]) == (inr_wallet_id, "credit", 100000)

    # Both lines belong to one funding transaction, so the ledger balances (FR-1.2).
    assert debit["transaction_id"] == credit["transaction_id"]
    kind = store.conn.execute(
        "SELECT kind FROM transactions WHERE id = ?", (debit["transaction_id"],)
    ).fetchone()[0]
    assert kind == "funding"

    # The money came from the system wallet, which is allowed to go negative (BR-2).
    assert store.get_wallet(system_inr)["balance"] == -100000
    assert store.get_wallet(store.system_wallet_id("USD"))["balance"] == 0


# Acceptance criterion 2: bad requests are rejected and nothing is created.

@pytest.mark.parametrize("bad_balance", [-1, 10.5, "100", True])
def test_bad_starting_balance_creates_nothing(client, store, admin_token, bad_balance):
    before = table_counts(store)
    body = {"name": "Asha", "wallets": [{"currency": "INR", "starting_balance": bad_balance}]}

    response = client.post("/accounts", json=body, headers=auth(admin_token))

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert table_counts(store) == before


def test_repeated_currency_creates_nothing(client, store, admin_token):
    before = table_counts(store)
    body = {
        "name": "Asha",
        "wallets": [
            {"currency": "INR", "starting_balance": 100},
            {"currency": "INR", "starting_balance": 200},
        ],
    }

    response = client.post("/accounts", json=body, headers=auth(admin_token))

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert table_counts(store) == before


@pytest.mark.parametrize("body", [
    {"name": "Asha", "wallets": [{"currency": "EUR", "starting_balance": 100}]},
    {"name": "Asha", "wallets": [{"currency": "INR", "starting_balance": 10**12 + 1}]},
    {"name": "Asha", "wallets": [{"currency": "INR", "starting_balance": 100, "extra": 1}]},
    {"name": "Asha", "wallets": []},
    {"name": "   ", "wallets": [{"currency": "INR", "starting_balance": 100}]},
    {"wallets": [{"currency": "INR", "starting_balance": 100}]},
])
def test_other_bad_bodies_create_nothing(client, store, admin_token, body):
    before = table_counts(store)

    response = client.post("/accounts", json=body, headers=auth(admin_token))

    assert response.status_code == 422
    assert table_counts(store) == before


def test_error_does_not_echo_input(client, admin_token):
    body = {"name": "Asha", "wallets": [{"currency": "INR", "starting_balance": "secret-value"}]}

    response = client.post("/accounts", json=body, headers=auth(admin_token))

    assert set(response.json()) == {"error"}
    assert "secret-value" not in response.text


def test_failure_halfway_rolls_back_everything(client, store, admin_token, monkeypatch):
    # FR-1.1: if the second wallet fails, the account and the first wallet's funding vanish too.
    before = table_counts(store)
    real_create_wallet = store.create_wallet

    def create_wallet_then_crash(account_id, currency):
        if currency == "USD":
            raise RuntimeError("crash halfway")
        return real_create_wallet(account_id, currency)

    monkeypatch.setattr(store, "create_wallet", create_wallet_then_crash)

    response = client.post("/accounts", json=GOOD_BODY, headers=auth(admin_token))

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_error"
    assert "crash halfway" not in response.text
    assert table_counts(store) == before
    assert store.get_wallet(store.system_wallet_id("INR"))["balance"] == 0


# Acceptance criterion 3: requests without a valid token are rejected.

@pytest.mark.parametrize("headers", [
    {},
    {"Authorization": "Bearer not-a-real-token"},
    {"Authorization": "Bearer "},
    {"Authorization": "Basic abc"},
])
def test_create_account_needs_valid_token(client, store, headers):
    before = table_counts(store)

    response = client.post("/accounts", json=GOOD_BODY, headers=headers)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_token"
    assert table_counts(store) == before


def test_expired_token_is_rejected(client, store):
    expired = issue_token(store, "admin", hours=-1)

    response = client.post("/accounts", json=GOOD_BODY, headers=auth(expired))

    assert response.status_code == 401
    assert count(store, "accounts") == 2  # only the two system accounts


def test_token_is_not_stored_or_echoed(client, store):
    token = issue_token(store, "admin", hours=-1)

    response = client.post("/accounts", json=GOOD_BODY, headers=auth(token))

    assert token not in response.text
    stored = [row[0] for row in store.conn.execute("SELECT token_hash FROM tokens")]
    assert token not in stored


def test_user_token_cannot_create_account(client, store, admin_token):
    account_id = client.post("/accounts", json=GOOD_BODY, headers=auth(admin_token)).json()["account_id"]
    user_token = issue_token(store, "user", account_id)
    before = table_counts(store)

    response = client.post("/accounts", json=GOOD_BODY, headers=auth(user_token))

    assert response.status_code == 403
    assert table_counts(store) == before


# GET /wallets/{wallet_id}: only the owner or an admin can see a wallet.

@pytest.fixture
def asha(client, store, admin_token):
    """Create Asha's account and return (her token, her INR wallet ID)."""
    body = client.post("/accounts", json=GOOD_BODY, headers=auth(admin_token)).json()
    return issue_token(store, "user", body["account_id"]), body["wallets"][0]["wallet_id"]


def test_owner_can_view_wallet(client, store, asha):
    token, wallet_id = asha

    response = client.get(f"/wallets/{wallet_id}", headers=auth(token))

    assert response.status_code == 200
    assert response.json() == {
        "wallet_id": wallet_id,
        "account_id": store.get_wallet(wallet_id)["account_id"],
        "currency": "INR",
        "balance": 100000,
    }


def test_admin_can_view_any_wallet(client, admin_token, asha):
    _, wallet_id = asha

    response = client.get(f"/wallets/{wallet_id}", headers=auth(admin_token))

    assert response.status_code == 200


def test_other_user_cannot_view_wallet(client, store, admin_token, asha):
    _, asha_wallet_id = asha
    ravi = {"name": "Ravi", "wallets": [{"currency": "USD", "starting_balance": 0}]}
    ravi_account_id = client.post("/accounts", json=ravi, headers=auth(admin_token)).json()["account_id"]
    ravi_token = issue_token(store, "user", ravi_account_id)

    response = client.get(f"/wallets/{asha_wallet_id}", headers=auth(ravi_token))

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"
    assert "100000" not in response.text


def test_user_cannot_view_system_wallet(client, store, asha):
    token, _ = asha

    response = client.get(f"/wallets/{store.system_wallet_id('INR')}", headers=auth(token))

    assert response.status_code == 403


def test_view_wallet_needs_token(client, asha):
    _, wallet_id = asha

    response = client.get(f"/wallets/{wallet_id}")

    assert response.status_code == 401


def test_missing_wallet_is_404(client, admin_token):
    response = client.get("/wallets/9999", headers=auth(admin_token))

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


@pytest.mark.parametrize("bad_id", ["abc", "0", "-1", "1.5", str(2**63)])
def test_bad_wallet_id_is_422(client, admin_token, bad_id):
    response = client.get(f"/wallets/{bad_id}", headers=auth(admin_token))

    assert response.status_code == 422
