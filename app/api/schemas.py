"""Pydantic request and response models.

StrictInt rejects 10.5, "100" and true, so only real whole numbers get through (TQ-6).
extra="forbid" rejects unknown fields with 422 (docs/api.md section 1).
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr

MAX_AMOUNT = 10**12  # BR-5
# The largest ID SQLite can store. Bigger numbers get 422 instead of crashing.
MAX_ID = 2**63 - 1

Currency = Literal["INR", "USD"]  # ADR-0001


class NewWallet(BaseModel):
    model_config = ConfigDict(extra="forbid")

    currency: Currency
    # 0 is allowed here because a wallet can start empty. No funding is recorded then.
    starting_balance: StrictInt = Field(ge=0, le=MAX_AMOUNT)


class NewAccount(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: StrictStr = Field(min_length=1, max_length=100)
    wallets: list[NewWallet] = Field(min_length=1)


class WalletOut(BaseModel):
    wallet_id: int
    currency: Currency
    balance: int


class AccountOut(BaseModel):
    account_id: int
    wallets: list[WalletOut]


class WalletDetails(BaseModel):
    wallet_id: int
    account_id: int
    currency: Currency
    balance: int


class NewTransfer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    from_wallet_id: StrictInt = Field(ge=1, le=MAX_ID)
    to_wallet_id: StrictInt = Field(ge=1, le=MAX_ID)
    # 1 to 10^12, so negative amounts are rejected (FR-2.5, BR-5).
    amount: StrictInt = Field(ge=1, le=MAX_AMOUNT)


class TransferOut(BaseModel):
    transfer_id: int
    from_wallet_id: int
    to_wallet_id: int
    amount: int
    currency: Currency
    created_at: str
