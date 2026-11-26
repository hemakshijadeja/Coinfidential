"""Bearer token checks (NFR-5, ADR-0005).

Tokens are random strings. Only their SHA-256 hash is stored, never the token itself.
"""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import Depends, Header

from app.api.deps import get_store
from app.errors import Forbidden, InvalidToken
from app.storage import WalletStore

TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
# How long tokens last, in hours (ADR-0005).
TOKEN_HOURS = {"user": 24, "admin": 1}


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def now_text() -> str:
    return datetime.now(UTC).strftime(TIME_FORMAT)


def issue_token(store: WalletStore, role: str, account_id: int | None = None, hours: int | None = None) -> str:
    """Make a new token for the operator to hand out (OD-13). Returns the token once."""
    if hours is None:
        hours = TOKEN_HOURS[role]
    token = secrets.token_urlsafe(32)
    expires_at = (datetime.now(UTC) + timedelta(hours=hours)).strftime(TIME_FORMAT)
    with store.write_transaction():
        store.save_token(hash_token(token), account_id, role, expires_at)
    return token


def current_token(
    store: Annotated[WalletStore, Depends(get_store)],
    authorization: Annotated[str | None, Header()] = None,
) -> dict:
    """Read the Authorization header and return the token's row, or raise 401."""
    if authorization is None or not authorization.startswith("Bearer "):
        raise InvalidToken()

    token = authorization[len("Bearer "):].strip()
    if token == "":
        raise InvalidToken()

    row = store.get_token(hash_token(token))
    # Both times use the same format, so comparing the text compares the times.
    if row is None or row["expires_at"] <= now_text():
        raise InvalidToken()
    return row


def require_admin(token: Annotated[dict, Depends(current_token)]) -> dict:
    if token["role"] != "admin":
        raise Forbidden("Only an administrator can do this.")
    return token
