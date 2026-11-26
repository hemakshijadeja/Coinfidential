"""Pydantic request and response models.

StrictInt rejects 10.5, "100" and true, so only real whole numbers get through (TQ-6).
extra="forbid" rejects unknown fields with 422 (docs/api.md section 1).
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr

MAX_AMOUNT = 10**12  # BR-5

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
