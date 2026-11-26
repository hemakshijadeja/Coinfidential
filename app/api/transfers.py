"""FR-2 route: send money between two wallets (docs/api.md section 3.2)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Header
from fastapi.responses import JSONResponse

from app.api.auth import current_token
from app.api.deps import get_store
from app.api.schemas import NewTransfer, TransferOut
from app.errors import Forbidden, MissingIdempotencyKey, ValidationFailed
from app.ledger import transfers as ledger
from app.storage import WalletStore

router = APIRouter()

MAX_KEY_LENGTH = 255


@router.post("/transfers", status_code=201, response_model=TransferOut)
def create_transfer(
    body: NewTransfer,
    token: Annotated[dict, Depends(current_token)],
    store: Annotated[WalletStore, Depends(get_store)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> JSONResponse:
    # FR-2.1: every transfer needs a key.
    if idempotency_key is None or idempotency_key.strip() == "":
        raise MissingIdempotencyKey()
    key = idempotency_key.strip()
    if len(key) > MAX_KEY_LENGTH:
        raise ValidationFailed("The idempotency key is too long.")

    # Admin tokens have no account, so they own no wallet to send from (BR-4).
    if token["account_id"] is None:
        raise Forbidden("You can only send money from your own wallet.")

    status_code, result = ledger.make_transfer(
        store, token["account_id"], key, body.from_wallet_id, body.to_wallet_id, body.amount
    )
    # The result may be a saved error from an earlier try, so we set the status ourselves.
    return JSONResponse(status_code=status_code, content=result)
