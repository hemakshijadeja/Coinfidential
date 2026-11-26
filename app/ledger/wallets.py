"""FR-1: create an account with its wallets."""

from app.errors import StoreError, ValidationFailed
from app.storage import WalletStore


def create_account(store: WalletStore, name: str, wallets: list[dict]) -> dict:
    """Create the account and all its wallets in one transaction (FR-1.1).

    Each wallet in `wallets` is {"currency": ..., "starting_balance": ...}. The API
    layer has already checked the amounts and currencies.
    """
    currencies = [wallet["currency"] for wallet in wallets]
    if len(set(currencies)) != len(currencies):
        raise ValidationFailed("Each wallet must use a different currency.")

    created = []
    # If anything fails inside this block, write_transaction() rolls back everything.
    with store.write_transaction():
        account_id = store.create_account(name)
        for wallet in wallets:
            wallet_id = store.create_wallet(account_id, wallet["currency"])
            amount = wallet["starting_balance"]
            if amount > 0:
                fund_wallet(store, wallet_id, wallet["currency"], amount)
            created.append({"wallet_id": wallet_id, "currency": wallet["currency"], "balance": amount})

    return {"account_id": account_id, "wallets": created}


def fund_wallet(store: WalletStore, wallet_id: int, currency: str, amount: int) -> None:
    """Move the starting balance from the system wallet for that currency (FR-1.2).

    One debit and one equal credit, so the ledger stays balanced (BR-1).
    Must be called inside write_transaction().
    """
    system_wallet_id = store.system_wallet_id(currency)
    transaction_id = store.add_transaction("funding")
    # System wallets are allowed to go negative (BR-2), so this should never fail.
    if not store.debit(system_wallet_id, amount):
        raise StoreError("could not debit the system wallet")
    store.credit(wallet_id, amount)
    store.add_entry(transaction_id, system_wallet_id, "debit", amount)
    store.add_entry(transaction_id, wallet_id, "credit", amount)
