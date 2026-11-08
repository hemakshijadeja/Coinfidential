---
id: financial-api-security-and-validation
title: Financial API Security and Validation
type: research
author: Member 4
stage: 1
status: active
created: 2026-11-09
source:
  - "Financial_Ledger.pdf, p. 2 (TQ-4, Security Testing)"
  - "Input Validation Cheat Sheet, OWASP: https://cheatsheetseries.owasp.org/cheatsheets/Input_Validation_Cheat_Sheet.html"
  - "API Security Top 10 2023, OWASP: https://api-security.owasp.org/editions/2023/en/0x11-t10"
  - "Strict Mode, Pydantic: https://pydantic.dev/docs/validation/latest/concepts/strict_mode/"
  - "sqlite3 module, Python documentation: https://docs.python.org/3/library/sqlite3.html"
  - "Local experiments, 2026-11-09: Python 3.12.5, SQLite 3.45.3, FastAPI 0.139.2, Pydantic 2.14.3, on Windows"
related_requirements: [TQ-4, TQ-1, TQ-6, FR-2, FR-5, SE-3]
---

# Financial API Security and Validation

## Summary

A negative transfer amount reverses the direction of a transfer: in testing, sending `-500` moved money from the victim to the attacker, passed the funds check, and still passed reconciliation. The brief's Security Testing section requires input validation on all API parameters and negative amount prevention, and [[TQ-4]] requires negative tests. FastAPI's defaults are not strict enough, and also return a `500` for `NaN` and echo rejected input back to the client.

## Key points

### Negative amounts invert transfers

Starting balances were attacker 0 and victim 1000, on a ledger funded by balanced entries. The transfer code had a normal `if balance < amount` check, but no amount validation.

| Step | Attacker | Victim | Credits | Debits | Reconciliation |
| --- | ---: | ---: | ---: | ---: | --- |
| Start | 0 | 1000 | 1000 | 1000 | Passes |
| Attacker "sends" `-500` to victim | **500** | **500** | 500 | 500 | **Still passes** |

- `0 < -500` is false, so the funds check passes.
- The debit and credit entries stay equal, so [[FR-5]] cannot see the problem.
- A `CHECK (amount > 0)` column constraint rejected both `-500` and `0`, with no change to the balances.

### Amount validation

These are the status codes for each JSON input. "Strict and bounded" means `StrictInt` with `gt=0` and `le=10**12`, plus `extra="forbid"` on the model. The upper limit is only a test value.

| Input | Plain `int` | `StrictInt`, `gt=0` | Strict and bounded |
| --- | --- | --- | --- |
| `500` | `200` | `200` | `200` |
| `0` | **`200`** | `422` | `422` |
| `-500` | **`200`** | `422` | `422` |
| `10.5` | `422` | `422` | `422` |
| `500.0`, `5e2` | **`200`, as 500** | `422` | `422` |
| `"500"` | **`200`, as 500** | `422` | `422` |
| `true` | **`200`, as 1** | `422` | `422` |
| `null`, `[500]`, missing | `422` | `422` | `422` |
| `2^63` or `10^30` | **`200`** | **`500` on database insert** | `422` |
| `NaN`, `Infinity` | **`500`** | **`500`** | **`500`** |
| Duplicate keys, `-5` then `5` | **`200`, as 5** | **`200`, as 5** | **`200`, as 5** |
| Extra field `is_admin` | **`200`, ignored** | **`200`, ignored** | `422` |

Pydantic's documentation confirms the first column's behavior: it coerces values by default, and strict mode raises errors instead. Duplicate JSON keys resolve to the last value in all three models.

### The `NaN` and echo problems

Python's JSON parser accepts `NaN`. Validation rejected it, but the default error response includes the rejected input, and that response could not be serialized: `ValueError: Out of range float values are not JSON compliant`.

| Input | Default handler | Custom handler without `input` |
| --- | --- | --- |
| `NaN`, `Infinity` | `500` | `422` |
| `-5` with an extra field holding `my-password` | `422`, **password echoed back** | `422`, not echoed |
| 5 MB rejected field | `422`, **5,000,108 byte response** | `422`, 58 byte response |

OWASP API4:2023 covers unrestricted resource consumption. The custom handler removes the large response, but the server still receives and parses the body.

### Malformed IDs

| Wallet ID in the path | `UUID` type | `UUID4` type | Plain `str` |
| --- | --- | --- | --- |
| Canonical v4 | `200` | `200` | `200` |
| Uppercase, no hyphens, braces, `urn:uuid:` | `200`, normalized | Not tested | `200`, unchanged |
| Version 1 | `200` | `422` | `200` |
| Nil UUID (all zeros) | `200` | `422` | `200` |
| Too short, SQL text, 5000 characters, non-ASCII digits | `422` | Not tested | **`200`** |

A plain string lets every malformed ID reach the database. As a `UUID`, different spellings of an ID normalize to one value, so a same-wallet check still caught `A` against `A.upper()`.

### SQL injection

Validation does not replace parameterized queries. OWASP says injection is prevented by query parameterization, and Python's documentation says to always use placeholders. With the ID `x' OR '1'='1`:

| Query style | Rows returned |
| --- | ---: |
| f-string | **2, every wallet** |
| `?` placeholder | 0 |

### Syntax and meaning

OWASP says to validate both syntax and semantics, and to define what is accepted rather than try to recognize attacks. In a model validator, rejecting a transfer from a wallet to itself returned `422`. The idempotency header with `min_length=1`, `max_length=255` and an allowlist pattern rejected empty, spaces-only, 256-character and injection-style keys, and accepted 255 characters.

## Relevance to Coinfidential

These are my recommendations and inferences, based on the results above:

- **Validate in two layers.** Use strict API models, and also `CHECK (amount > 0)` in the database, because the database is the last defense if a code path skips validation.
- **Use this tested request model,** adjusting the upper limit as the team decides:

  ```python
  class TransferRequest(BaseModel):
      model_config = ConfigDict(extra="forbid")
      from_wallet: UUID4
      to_wallet: UUID4
      amount: Annotated[StrictInt, Field(gt=0, le=MAX_AMOUNT)]
  ```

  I tested `UUID4` in a path parameter and `UUID` in this model. The same-wallet check needs adding as a model validator.
- **Add a custom `RequestValidationError` handler** that returns only `loc` and `type`. This fixes the `NaN` response and the echo, and fits the single error format proposed in [[rest-api-error-handling-and-status-codes]].
- **Set a request size limit** at the server or proxy, and test it. My test client did not run through a production server, so I do not know what limit one would apply.
- **Authorize every wallet access.** OWASP's API1:2023 warns that endpoints accepting object IDs need access checks on every use. Valid input does not show that the caller owns the source wallet, and API5:2023 applies to the administrative [[FR-5]] endpoint.
- **Reject unknown fields,** which covers the mass assignment part of OWASP API3:2023.

### Test plan

| Brief's requirement | Tests to write |
| --- | --- |
| [[TQ-4]]: negative balance attempts | Transfer more than the balance. Confirm the database rejects a direct negative amount |
| [[TQ-4]]: insufficient funds | Assert the status, and that balances and entries are unchanged |
| [[TQ-4]]: invalid idempotency payloads | Empty, oversized and invalid keys, plus a reused key with a different payload |
| [[TQ-4]]: malformed IDs | Each row of the ID table, on every endpoint with a wallet ID |
| [[TQ-4]]: simultaneous transfers | Covered by Member 2's race test design |
| Security Testing: all API parameters | Each row of the amount table, including `NaN` and oversized values |
| Security Testing: negative amounts | `-500` and `0` through the API, then assert no balance moved |
| [[TQ-6]]: integer amounts | `10.5`, `500.0` and `"500"` are rejected |

## Requirements

- [[TQ-4]]: This note provides the negative test cases.
- [[TQ-1]]: The validation rules need unit tests.
- [[TQ-6]]: Strict integers keep amounts in minor units.
- [[FR-2]]: The idempotency key needs its own validation.
- [[FR-5]]: Reconciliation cannot detect an inverted transfer, and its endpoint needs access control.
- [[SE-3]]: The validation limits and error format belong in an ADR.

The brief's Security Testing requirement has no ID, so this note refers to it by name.

## Related notes

- [[integer-minor-units-money-math]]: First identified `StrictInt` and `STRICT` tables, and this note adds positive and upper limits.
- [[rest-api-error-handling-and-status-codes]]: Measured the same input echo, and proposes the error format.
- [[idempotent-api-design-patterns]]: Validation should run before the payload is hashed.
- [[ledger-reconciliation-algorithms]]: Lists other faults that reconciliation cannot detect, and this note adds inverted transfers.
- [[double-entry-bookkeeping-principles]]: Shows that balanced entries alone do not prove a transfer was legitimate.
- [[race-conditions-and-optimistic-locking]]: Covers the simultaneous transfer tests that [[TQ-4]] requires.
- [[agent-skills-and-second-brain-architecture]]: The `simulate-transfer` skill could exercise these checks.

## Open questions

- Who may call each endpoint? The brief defines no authentication, so [[TQ-4]] does not currently cover authorization. This is the largest open security question.
- What is the maximum transfer amount? `10**12` was only a test value.
- Should duplicate JSON keys be rejected? Standard parsing silently uses the last value, and a stricter parser would be needed to detect them.
- Should IDs be restricted to `UUID4`? This assumes that the server generates them.
- These are the behaviors of one set of pinned versions, so the tests need to confirm them after any upgrade.
