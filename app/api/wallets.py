"""FR-1 routes: create an account with wallets, and view a wallet (docs/api.md section 3.1)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path

from app.api.auth import current_token, require_admin
from app.api.deps import get_store
from app.api.schemas import MAX_ID, AccountOut, NewAccount, WalletDetails
from app.errors import Forbidden, NotFound, ValidationFailed
from app.ledger import wallets as ledger
from app.storage import WalletStore

router = APIRouter()


@router.post("/accounts", status_code=201, response_model=AccountOut)
def create_account(
    body: NewAccount,
    token: Annotated[dict, Depends(require_admin)],
    store: Annotated[WalletStore, Depends(get_store)],
) -> dict:
    name = body.name.strip()
    if name == "":
        raise ValidationFailed("The name must not be empty.")
    wallets = [wallet.model_dump() for wallet in body.wallets]
    return ledger.create_account(store, name, wallets)


@router.get("/wallets/{wallet_id}", response_model=WalletDetails)
def get_wallet(
    wallet_id: Annotated[int, Path(ge=1, le=MAX_ID)],
    token: Annotated[dict, Depends(current_token)],
    store: Annotated[WalletStore, Depends(get_store)],
) -> dict:
    wallet = store.get_wallet(wallet_id)
    if wallet is None:
        raise NotFound("The wallet does not exist.")
    if token["role"] != "admin" and token["account_id"] != wallet["account_id"]:
        raise Forbidden("This wallet belongs to someone else.")
    return {
        "wallet_id": wallet["id"],
        "account_id": wallet["account_id"],
        "currency": wallet["currency"],
        "balance": wallet["balance"],
    }
