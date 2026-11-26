# Coinfidential API

- **Author:** Hardh
- **Stage:** 2 (Design)
- **Requirements:** FR-1, FR-2, FR-3, FR-4, FR-5, SE-7
- **Based on:** the SRS, [architecture.md](architecture.md), [database-design.md](database-design.md), [ADR-0005](adr/0005-token-format-and-lifetime.md) and the brain note `rest-api-error-handling-and-status-codes`

This is the plan for the API. Only `GET /health` exists right now. Paths and fields can still change while we build Stage 2. FastAPI will also generate an OpenAPI page at `/docs` once the endpoints exist.

## 1. General rules

- Every endpoint needs `Authorization: Bearer <token>`. Tokens are random strings issued by the operator. User tokens last 24 hours and admin tokens last 1 hour ([ADR-0005](adr/0005-token-format-and-lifetime.md)).
- Money is always a whole number in minor units (paise or cents), from 1 to 10^12. `10.5`, `"100"`, `true` and negative numbers are rejected.
- Currencies are `INR` and `USD` only ([ADR-0001](adr/0001-supported-currencies.md)).
- Endpoints that move money (`POST /transfers` and reversals) need an `Idempotency-Key` header. Sending the same key with the same body again returns the saved response and moves no money.
- Unknown fields in a request body are rejected with `422`.

## 2. Error format

Every error uses the same shape (architecture section 5):

```json
{
  "error": {
    "code": "insufficient_funds",
    "message": "The wallet does not have enough money for this transfer."
  }
}
```

The message never contains stack traces, SQL, tokens or the value the user sent.

| Status | `code` | When |
| --- | --- | --- |
| `400` | `missing_idempotency_key` | No `Idempotency-Key` header |
| `401` | `invalid_token` | Token missing, wrong or expired |
| `403` | `forbidden` | Not your wallet, or not an admin |
| `404` | `not_found` | Wallet or transfer does not exist |
| `405` | `method_not_allowed` | For example `PUT` or `DELETE` on a ledger record |
| `409` | `insufficient_funds` | Not enough money in the sending wallet |
| `409` | `already_reversed` | Transfer was already reversed |
| `409` | `reversal_not_possible` | Recipient has already spent the money |
| `422` | `validation_error` | Bad amount, currency, ID or extra field |
| `422` | `idempotency_key_reused` | Same key, different body |
| `503` | `busy` | Database too busy, retry later (not final, see ADR-0004) |
| `500` | `internal_error` | Anything unexpected. Nothing is changed |

## 3. Endpoints

| FR | Method | Path | Who | Success |
| --- | --- | --- | --- | --- |
| FR-1 | `POST` | `/accounts` | Admin (operator) | `201` |
| FR-1 | `GET` | `/wallets/{wallet_id}` | Owner or admin | `200` |
| FR-2, FR-3 | `POST` | `/transfers` | Owner of the sending wallet | `201` |
| FR-4 | `POST` | `/transfers/{transfer_id}/reversal` | Sender or admin | `201` |
| FR-4 | `GET` | `/transfers/{transfer_id}` | Sender, receiver or admin | `200` |
| FR-5 | `GET` | `/admin/reconcile` | Admin | `200` |

### 3.1 FR-1: Create an account with wallets

`POST /accounts`

Creates the account and all its wallets in one transaction. A starting balance is a `funding` transfer from the system account for that currency.

Request:

```json
{
  "name": "Asha",
  "wallets": [
    { "currency": "INR", "starting_balance": 100000 },
    { "currency": "USD", "starting_balance": 0 }
  ]
}
```

Response `201`:

```json
{
  "account_id": 7,
  "wallets": [
    { "wallet_id": 12, "currency": "INR", "balance": 100000 },
    { "wallet_id": 13, "currency": "USD", "balance": 0 }
  ]
}
```

Errors: `401`, `403`, `422` (same currency twice, unknown currency, bad starting balance). Nothing is created on any error.

`GET /wallets/{wallet_id}`

Response `200`:

```json
{ "wallet_id": 12, "account_id": 7, "currency": "INR", "balance": 100000 }
```

Errors: `401`, `403` (someone else's wallet), `404`, `422` (bad ID).

### 3.2 FR-2 and FR-3: Transfer

`POST /transfers`

Header: `Idempotency-Key: 3f1c9a2e-...`

Request:

```json
{ "from_wallet_id": 12, "to_wallet_id": 20, "amount": 2500 }
```

Response `201`:

```json
{
  "transfer_id": 55,
  "from_wallet_id": 12,
  "to_wallet_id": 20,
  "amount": 2500,
  "currency": "INR",
  "created_at": "2026-11-26T10:15:00Z"
}
```

- A retry with the same key and body returns this same response again. No money moves.
- Both wallets must have the same currency (BR-3), otherwise `422`.
- FR-3 has no separate endpoint. Simultaneous transfers on one wallet are run one at a time with `BEGIN IMMEDIATE` ([ADR-0004](adr/0004-begin-immediate-locking.md)), so the balance never goes below zero.
- A failed transfer (for example `409`) is also saved under its key. Retrying with the same key gives the same error, so use a new key (OD-6).

Errors: `400`, `401`, `403` (not your sending wallet), `404`, `409` (`insufficient_funds`), `422`, `503`.

### 3.3 FR-4: Reverse a transfer

`POST /transfers/{transfer_id}/reversal`

Header: `Idempotency-Key: 8b7d...`. No body. Always reverses the full amount ([ADR-0002](adr/0002-no-partial-reversals.md)).

Response `201`:

```json
{
  "reversal_id": 61,
  "reverses": 55,
  "amount": 2500,
  "currency": "INR",
  "created_at": "2026-11-26T11:00:00Z"
}
```

Errors: `400`, `401`, `403` (not the sender or an admin), `404`, `409` (`already_reversed`, `reversal_not_possible`), `422`, `503`.

`GET /transfers/{transfer_id}`

Shows a transfer and whether it was reversed. The original record never changes.

```json
{ "transfer_id": 55, "amount": 2500, "currency": "INR", "reversed_by": 61 }
```

Errors: `401`, `403`, `404`, `422`.

There are no `PUT`, `PATCH` or `DELETE` endpoints for transfers or ledger entries. They return `405`.

### 3.4 FR-5: Reconciliation

`GET /admin/reconcile`

Reads the whole ledger in one snapshot and never changes data. It returns `200` even when it finds problems, because the check itself worked.

Response `200` (all good):

```json
{
  "balanced": true,
  "checked_at": "2026-11-26T12:00:00Z",
  "problems": []
}
```

Response `200` (problem found):

```json
{
  "balanced": false,
  "checked_at": "2026-11-26T12:00:00Z",
  "problems": [
    {
      "check": "wallet_balance",
      "wallet_id": 12,
      "stored_balance": 97500,
      "ledger_balance": 97000
    }
  ]
}
```

Possible `check` values: `currency_totals` (credits equal debits per currency), `wallet_balance`, `transaction_balance` and `hash_chain` (tamper check, [ADR-0003](adr/0003-tamper-detection.md)).

Errors: `401`, `403` (not an admin), `500`.

## 4. Still open

- Whether `POST /accounts` should be admin-only. We picked admin because the operator issues tokens and registration is out of scope (OD-13), but no ADR says so yet.
- `503` for a busy database is not final (ADR-0004).
- Whether to switch to the full RFC 9457 error format later.
