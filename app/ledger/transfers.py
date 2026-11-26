"""FR-2: idempotent transfers between two wallets."""

import hashlib
import json
from datetime import UTC, datetime

from app.errors import (
    AppError,
    Forbidden,
    IdempotencyKeyReused,
    InsufficientFunds,
    NotFound,
    ValidationFailed,
    error_body,
)
from app.storage import WalletStore


def request_hash(from_wallet_id: int, to_wallet_id: int, amount: int) -> str:
    """A fingerprint of the request, so we can tell if a key is reused for a different one (OD-10)."""
    text = json.dumps(
        {"from_wallet_id": from_wallet_id, "to_wallet_id": to_wallet_id, "amount": amount},
        sort_keys=True,
    )
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def make_transfer(
    store: WalletStore,
    account_id: int,
    idem_key: str,
    from_wallet_id: int,
    to_wallet_id: int,
    amount: int,
) -> tuple[int, dict]:
    """Run a transfer once per idempotency key. Returns (status code, response body).

    The key lookup, the checks, the ledger entries, both balances and the saved key
    all happen in one BEGIN IMMEDIATE transaction (FR-2.2, ADR-0004). So two
    requests with the same key wait in line, and the second one sees the first
    one's saved result (FR-2.3).
    """
    fingerprint = request_hash(from_wallet_id, to_wallet_id, amount)

    with store.write_transaction():
        saved = store.get_idempotency(account_id, idem_key)
        if saved is not None:
            if saved["request_hash"] != fingerprint:
                raise IdempotencyKeyReused()
            # Same key, same request: give back the first answer and move no money.
            return saved["status_code"], json.loads(saved["response_body"])

        try:
            body = transfer(store, account_id, from_wallet_id, to_wallet_id, amount)
            status_code = 201
            transaction_id = body["transfer_id"]
        except AppError as error:
            # A rejected transfer is saved under its key too, so a retry gets the
            # same rejection (BR-6, OD-6). transfer() only raises AppError before
            # it writes anything, so there is nothing to undo here.
            status_code = error.status_code
            body = error_body(error.code, error.message)
            transaction_id = None

        store.save_idempotency(account_id, idem_key, fingerprint, transaction_id, status_code, json.dumps(body))

    return status_code, body


def transfer(store: WalletStore, account_id: int, from_wallet_id: int, to_wallet_id: int, amount: int) -> dict:
    """Check the transfer, then move the money. Must be called inside write_transaction().

    All the checks come first. The first write is the guarded debit, so if any
    check fails nothing has been written yet.
    """
    if from_wallet_id == to_wallet_id:
        raise ValidationFailed("A wallet cannot send money to itself.")

    sender = store.get_wallet(from_wallet_id)
    if sender is None:
        raise NotFound("The sending wallet does not exist.")
    if sender["account_id"] != account_id:
        raise Forbidden("You can only send money from your own wallet.")  # FR-2.4, BR-4

    receiver = store.get_wallet(to_wallet_id)
    if receiver is None:
        raise NotFound("The receiving wallet does not exist.")
    if receiver["currency"] != sender["currency"]:
        raise ValidationFailed("Both wallets must use the same currency.")  # BR-3

    # Guarded UPDATE: it only takes the money if the balance is big enough (FR-3.1, FR-3.2).
    if not store.debit(from_wallet_id, amount):
        raise InsufficientFunds()

    # From here on nothing raises AppError. Any other error rolls back the debit too.
    transaction_id = store.add_transaction("transfer")
    store.credit(to_wallet_id, amount)
    store.add_entry(transaction_id, from_wallet_id, "debit", amount)
    store.add_entry(transaction_id, to_wallet_id, "credit", amount)

    return {
        "transfer_id": transaction_id,
        "from_wallet_id": from_wallet_id,
        "to_wallet_id": to_wallet_id,
        "amount": amount,
        "currency": sender["currency"],
        "created_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
