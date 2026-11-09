# Coinfidential: Software Requirements Specification

Version 1.0 approved

Prepared by Aditya Bhat (BT2024035), Subhadeep Das (BT2024219), Hemakshi Jadeja (BT2024002) and Hardh Kava (BT2024041)

## 1. Introduction

### 1.1 Purpose

This document specifies the requirements for Coinfidential, a Financial Ledger and Digital Wallet RESTful API, at version 1.0. It states what the system must do. How it does so is decided in the Stage 2 design documents and ADRs. It is the Stage 1 deliverable required by SE-1.

**Implementation status:** only `GET /health` exists, and it does not yet require the token specified in Section 3.3.1. All other behavior is specified but not yet built.

### 1.2 Document Conventions

- **Requirement IDs.** `FR-n` functional, `NFR-n` non-functional, `SK-n` agent skill, `TQ-n` testing and quality, `SE-n` software engineering, `SB-n` Second Brain. Security Testing is a named requirement in the brief, with no ID.
- **"Shall" and "should".** "Shall" marks a mandatory requirement. "Should" marks a recommended one, which the team may change in Stage 2 with an ADR.
- **Priority.** High, Medium or Low. All five features are High, because the brief requires each and TQ-3 tests each.
- **Wikilinks.** `[[note-name]]` cites a research note in the `brain/` Obsidian vault, starting from [[index]].
- **Decisions.** `OD-n` identifies a decision recorded in Section 2.7.

| ID series | Source | Defined by |
| --- | --- | --- |
| FR-1 to FR-5, TQ-1 to TQ-6, Security Testing, `simulate-transfer` | `Financial_Ledger.pdf` | Course brief |
| SB-1 to SB-6, SE-1 to SE-7, TQ-7, TQ-8, `brain-ingest`, `brain-refine`, `brain-query`, `local-check` | `SDLC_and_Workflow.pdf` | Course document |
| NFR-1 to NFR-8, SK-1 to SK-5 | This SRS, as SE-1 requires | The team |

The course documents require NFR and SK sections but do not list individual NFR or SK IDs.

| Term | Meaning |
| --- | --- |
| ADR | Architecture Decision Record |
| Bearer token | A credential that gives access to whoever holds it (RFC 6750) |
| Credit, debit | The two sides of a ledger transaction. Wallets are treated as liabilities, so a credit increases a wallet balance and a debit decreases it |
| Idempotency key | A client-supplied value that identifies one logical request across retries |
| Minor unit | The smallest unit of a currency, such as a cent or paisa |
| PARA | Projects, Areas, Resources, Archive: the structure of the Second Brain |
| Reversal | A new transaction that offsets an earlier one, leaving the original unchanged |
| System account | An internal, non-user account per currency that funds opening balances. It may have a negative balance |
| ToCToU | Time-of-Check to Time-of-Use, a race where state changes between a check and its use |
| WAL | Write-Ahead Logging, a SQLite journal mode |

### 1.3 Intended Audience

Course reviewers should read all sections. Developers and testers should focus on Sections 2 to 5, API client authors on Sections 3.3 and 3.4, and skill authors on Section 6.1.

### 1.4 Product Scope

**The problem: the Vanishing Money Glitch.** In poorly designed databases, simple balance updates can overwrite each other during simultaneous network requests, and a single network retry can trigger a duplicate charge. Our research reproduced both causes: 8 unprotected concurrent requests spent the same 100 and left a balance of -700 ([[race-conditions-and-optimistic-locking]]), and a separately stored idempotency record allowed a double charge after a simulated crash ([[idempotent-api-design-patterns]]).

**The solution: a mathematically sound double-entry backend.** Coinfidential is the backend of a digital wallet, backed by a strict, tamper-evident, double-entry ledger ([[double-entry-bookkeeping-principles]]). Every credit has an equal and opposite debit, retries never charge twice, concurrent requests cannot corrupt a balance, ledger records are never changed, and an administrator can verify the ledger at any time.

**In scope:** a RESTful API, with token authentication, to create user accounts with currency wallets, transfer between wallets, reverse transfers, read wallets and entries, and reconcile the ledger.

**Out of scope:** currency conversion, payment networks and real money movement, user interfaces, and user registration and login.

### 1.5 References

**Project repository:** [github.com/hemakshijadeja/Coinfidential](https://github.com/hemakshijadeja/Coinfidential)

**Course documents** (not stored in the repository): `Financial_Ledger.pdf` and `SDLC_and_Workflow.pdf`.

**Second Brain research notes:**

| Topic | Notes |
| --- | --- |
| Ledger design | [[double-entry-bookkeeping-principles]], [[immutable-audit-trail-and-reversals]], [[ledger-reconciliation-algorithms]] |
| Money and API behavior | [[integer-minor-units-money-math]], [[rest-api-error-handling-and-status-codes]], [[idempotent-api-design-patterns]], [[financial-api-security-and-validation]] |
| Storage and concurrency | [[sqlite-acid-and-wal-concurrency]], [[race-conditions-and-optimistic-locking]], [[provider-interface-isolation]] |
| Skills and process | [[agent-skills-and-second-brain-architecture]], [[stage1-ai-session-setup]], [[stage1-review-retrospective]] |

**External:** RFC 6750 (Bearer tokens), RFC 9110 (HTTP Semantics), RFC 9457 (Problem Details), the IETF `Idempotency-Key` draft (not yet a finished standard), OWASP API Security Top 10 (2023), SQLite documentation, and the [Agent Skills specification](https://agentskills.io/specification).

## 2. Overall Description

### 2.1 Product Perspective

Coinfidential is a new, self-contained backend service. It does not connect to banks or payment networks.

```
Client (Postman, Bruno, cURL, agent skills)
        |  HTTPS + JSON, Authorization: Bearer <token>
        v
API layer                authentication, validation, error format
        |
        v
Service layer            transfers, reversals, reconciliation rules
        |  storage interface (SE-6)
        v
SQLite provider and database file
```

### 2.2 Product Functions

| Feature | Function |
| --- | --- |
| FR-1 | Create user accounts with distinct currency wallets, each balance backed by ledger entries |
| FR-2 | Transfer funds between wallets, safely retried through an idempotency key |
| FR-3 | Keep balances correct under simultaneous requests |
| FR-4 | Keep ledger records immutable, with corrections made by reversal transactions |
| FR-5 | Let an administrator verify the whole ledger |

### 2.3 User Classes and Characteristics

| User class | Characteristics | Access |
| --- | --- | --- |
| API client (wallet holder) | Software acting for one user, through a user token | Own accounts and wallets |
| Administrator | Trusted operator, through an admin token | Reconciliation, reversals, read access to all wallets |
| Developers and AI agents | The team and its skills, following `AGENTS.md` | Test databases, never real data |

### 2.4 Operating Environment

Python 3.12, FastAPI and SQLite on a single host with a local filesystem. Development is on Windows, and CI runs on Ubuntu through GitHub Actions.

### 2.5 Design and Implementation Constraints

The following shall apply. Research supporting each one, including candidate SQL and settings for Stage 2, is in the cited notes.

- **SQLite in WAL mode.** The database shall use `PRAGMA journal_mode=WAL;`. WAL is not the race protection: tests with WAL on still reached -700 when the check and write were unprotected ([[sqlite-acid-and-wal-concurrency]]).
- **`BEGIN IMMEDIATE` locking.** Every money-moving request shall run its checks and writes in one `BEGIN IMMEDIATE` transaction, which removes the ToCToU window. Optimistic locking produced 17 to 24 conflicts per trial where this produced none ([[race-conditions-and-optimistic-locking]]).
- **64-bit integer minor units (TQ-6).** All money shall be stored and calculated as 64-bit signed integers in minor units. TQ-6 also allows exact decimals, but the team chose integers. Adding `0.1` ten times as a float gave `0.9999999999999999` ([[integer-minor-units-money-math]]).
- **Amount limit.** Every transaction amount shall be between 1 and 10^12 minor units, and opening balances between 0 and 10^12 (OD-5).
- **Course process.** Each change gets a human review in a pull request, secrets are never pasted into AI tools, and significant decisions become ADRs in `docs/adr/` (SE-3).

### 2.6 User Documentation

The team shall provide user documentation and developer API documentation, such as OpenAPI, as SE-7 requires. This shall include the authentication rules, every endpoint, its error codes, and the idempotency key rules. `README.md` covers setup and running the checks.

### 2.7 Assumptions and Dependencies

**Assumptions:** one API server host, because WAL does not work over a network filesystem. All IDs are server-generated UUID version 4 values, and timestamps are UTC.

**Dependencies:** Python, FastAPI, Pydantic, Uvicorn and SQLite, pinned in `requirements.txt`. The IETF idempotency draft could change.

**Decisions.** The brief does not settle these points. Adopted decisions and Stage 2 decisions each need an ADR under SE-3.

| ID | Decision | Outcome | Status |
| --- | --- | --- | --- |
| OD-1 | End-user authentication | `Authorization: Bearer <token>` on all REST endpoints | **Closed** |
| OD-2 | Protecting the "administrative" endpoint | Bearer token with the `admin` role | **Closed** |
| OD-3 | Opening funds | Balanced entry against a per-currency system account | Adopted |
| OD-4 | Supported currencies | At least two, with INR and USD recommended. The final list is for Stage 2 | Stage 2 |
| OD-5 | Maximum amount | 10^12 minor units per transaction | **Closed** |
| OD-6 | Is insufficient funds stored against the key? | Yes: a retry returns the same `409`, and a new attempt needs a new key | Adopted |
| OD-7 | Idempotency record retention | Keep indefinitely, because FR-2 says retries must never double-charge | Adopted |
| OD-8 | Reversal after the recipient spent the money | Reject with `409`, which keeps wallets from going negative | Adopted |
| OD-9 | Partial reversals, and reversing a reversal | At most one full reversal per transfer. Whether to allow more is for Stage 2 | Stage 2 |
| OD-10 | Meaning of "idempotency key hashing" in TQ-1 | Hash the request payload | Adopted |
| OD-11 | How to deliver "tamper-evident" | A SHA-256 hash chain is recommended. The method is for Stage 2 | Stage 2 |
| OD-12 | Does SE-6 apply to SQLite? | Yes, as the project's only external dependency | Adopted |
| OD-13 | How tokens are issued | An operator issues them outside the API. Format and lifetime are for Stage 2 | Adopted |

## 3. External Interface Requirements

### 3.1 User Interfaces

There is no graphical user interface. People and agents use the REST API through tools such as Postman, Bruno or cURL.

### 3.2 Hardware Interfaces

There are no direct hardware interfaces.

### 3.3 Software Interfaces

The REST API uses JSON, under the base path `/api/v1`. `GET /health` stays at the root. These contracts fix the endpoints, key fields and main outcomes. Stage 2 and the OpenAPI document (SE-7) define the full schemas.

#### 3.3.1 Authentication (All Endpoints)

Every REST endpoint, including `GET /health`, shall require `Authorization: Bearer <token>`, following RFC 6750. There are two roles: `user`, which owns the accounts it created, and `admin`. Authentication shall run before any other check.

| Situation | Status | Code |
| --- | --- | --- |
| No credentials | `401`, with `WWW-Authenticate: Bearer` | `AUTH_REQUIRED` |
| Malformed `Authorization` header | `400` | `AUTH_HEADER_INVALID` |
| Unknown, expired or revoked token | `401` | `TOKEN_INVALID` |
| Valid token without the required role or ownership | `403` | `FORBIDDEN` |

These apply to every endpoint, so the contracts below do not repeat them. Research: [[financial-api-security-and-validation]].

#### 3.3.2 Error Format (NFR-8)

All errors shall use `application/problem+json` (RFC 9457), with `type`, `title`, `status`, `detail` and a stable `code`. Validation errors also list each failing location and type, and shall never contain the rejected input. Request bodies reject unknown fields, and amounts must be strict JSON integers. Status code choices follow [[rest-api-error-handling-and-status-codes]].

#### 3.3.3 FR-1: Accounts and Wallets

| Field | Value |
| --- | --- |
| Method and URL | `POST /api/v1/accounts` |
| Request headers | `Authorization: Bearer <token>`, `Content-Type: application/json` |
| Allowed role | `user`, who becomes the owner |
| Request | `owner_name`, and `wallets`: 1 or more, each with a distinct `currency` and an `initial_balance_minor` of 0 to 10^12 |
| Success | `201`, with `account_id` and each wallet's `wallet_id`, `currency` and `balance_minor` |
| Errors | `422` `VALIDATION_FAILED`, `503` `STORE_BUSY` |

| Field | Value |
| --- | --- |
| Method and URL | `GET /api/v1/wallets/{wallet_id}` |
| Request headers | `Authorization: Bearer <token>` |
| Allowed role | `user` who owns the wallet, or `admin` |
| Success | `200`, with `wallet_id`, `account_id`, `currency` and `balance_minor` |
| Errors | `404` `WALLET_NOT_FOUND`, `422` `VALIDATION_FAILED` |

#### 3.3.4 FR-2: Transfer

| Field | Value |
| --- | --- |
| Method and URL | `POST /api/v1/transfers` |
| Request headers | `Authorization: Bearer <token>`, `Content-Type: application/json`, `Idempotency-Key` (1 to 255 characters from `A-Z a-z 0-9 _ -`) |
| Allowed role | `user` who owns the source wallet |
| Request | `from_wallet_id` and `to_wallet_id` (different UUIDs), `currency` (matching both wallets), `amount_minor` (strict integer, 1 to 10^12) |
| Success | `201`, with `transfer_id`, the request's fields and `created_at`. A retry returns the stored status and body, with `Idempotent-Replayed: true` |

| Status | Code | Meaning | Stored against key |
| --- | --- | --- | --- |
| `400` | `IDEMPOTENCY_KEY_INVALID` | Key missing or badly formed | No |
| `404` | `WALLET_NOT_FOUND` | Either wallet does not exist | No |
| `409` | `INSUFFICIENT_FUNDS` | Balance is below the amount | Yes (OD-6) |
| `409` | `IDEMPOTENCY_IN_PROGRESS` | Original request still processing, which is expected to be rare | No |
| `422` | `IDEMPOTENCY_KEY_REUSED` | Same key with a different payload | No |
| `422` | `VALIDATION_FAILED` | Invalid body, same wallet, or wrong currency | No |
| `503` | `STORE_BUSY` | Could not get the write lock in time, sent with `Retry-After` | No |

The stored fingerprint shall be a SHA-256 hash of the method, path and validated body, so a retry with reordered JSON still matches. Keys are scoped to the account that owns the source wallet.

#### 3.3.5 FR-3: Endpoints Under Concurrency

FR-3 adds no endpoint. It applies to the money-moving endpoints above and below, which shall evaluate funds against the latest committed balance. A request that cannot get the write lock in a bounded time shall return `503`, and raw `database is locked` errors shall never reach a client.

#### 3.3.6 FR-4: Reversals and Audit Trail

| Field | Value |
| --- | --- |
| Method and URL | `POST /api/v1/transfers/{transfer_id}/reversals` |
| Request headers | `Authorization: Bearer <token>`, `Content-Type: application/json`, `Idempotency-Key` |
| Allowed role | `user` who owns the original source wallet, or `admin` |
| Request | `reason` (1 to 500 characters) |
| Success | `201`, with `reversal_id`, `reverses_transfer_id`, `currency`, `amount_minor` and `reason` |
| Errors | `404` `TRANSFER_NOT_FOUND`, `409` `ALREADY_REVERSED`, `409` `CANNOT_REVERSE_REVERSAL`, `409` `INSUFFICIENT_FUNDS`, and the idempotency errors of FR-2 |

| Field | Value |
| --- | --- |
| Method and URL | `GET /api/v1/wallets/{wallet_id}/entries` |
| Request headers | `Authorization: Bearer <token>` |
| Allowed role | `user` who owns the wallet, or `admin` |
| Success | `200`, with a page of entries: `entry_id`, `transaction_id`, `direction`, `amount_minor`, `created_at` |
| Errors | `404` `WALLET_NOT_FOUND`, `422` `VALIDATION_FAILED` |

The API shall have no route that changes or removes a ledger entry, so `PUT`, `PATCH` and `DELETE` on these paths return `405`.

#### 3.3.7 FR-5: Reconciliation

| Field | Value |
| --- | --- |
| Method and URL | `GET /api/v1/admin/reconciliation` |
| Request headers | `Authorization: Bearer <token>` |
| Allowed role | `admin` only |
| Success | `200` whether or not the ledger balances, with `balanced`, `scanned_at`, and the result and failing rows of each check |
| Errors | `500` `RECONCILIATION_FAILED`, if the scan could not finish |

#### 3.3.8 Health Check

| Field | Value |
| --- | --- |
| Method and URL | `GET /health` |
| Request headers | `Authorization: Bearer <token>` |
| Allowed role | `user` or `admin` |
| Success | `200`, with `{ "status": "ok" }` |

The current `GET /health` code does not check a token, so it does not yet meet this requirement.

#### 3.3.9 SQLite and Provider Interface Isolation (SE-6)

SQLite shall sit behind a storage interface that includes the transaction boundary, so only the provider contains SQL or imports `sqlite3`. This lets each test receive its own database, as TQ-5 requires. Tests should use real SQLite rather than a fake, and race tests need a file database, because `:memory:` ignores WAL and gives each connection a separate database. A tested prototype is in [[provider-interface-isolation]].

### 3.4 Communications Interfaces

REST over HTTP, with JSON in UTF-8. RFC 6750 makes TLS mandatory for bearer tokens, so deployed traffic shall use HTTPS, and plain HTTP is allowed only on the loopback address for local work. Tokens shall travel only in the `Authorization` header, never in a URL.

## 4. System Features

The contract for each feature is in Section 3.3. These invariants shall hold after every committed transaction. `E(w)` is the set of entries of wallet `w`.

```text
I-1  Each transaction balances, per currency:   SUM(debits) == SUM(credits)
I-2  The whole ledger balances, per currency:   SUM(debits) == SUM(credits)
I-3  Wallet balance:   balance(w) == SUM(credits in E(w)) - SUM(debits in E(w))
I-4  User wallets are never negative:   balance(w) >= 0   (system accounts are exempt)
I-5  Entry amounts are positive integers:   1 <= amount <= 10^12
I-6  Balances fit a signed 64-bit integer:   abs(balance(w)) <= 2^63 - 1
I-7  Entries are append-only:   no committed entry is ever changed or removed
```

### 4.1 FR-1: Wallet Initialization

#### 4.1.1 Description and Priority

From the brief: "Create user accounts with distinct currency wallets. Every balance is backed by double-entry ledger entries (every credit must equal a debit)." Research: [[double-entry-bookkeeping-principles]].

**Priority:** High.

#### 4.1.2 Stimulus/Response Sequences

| Stimulus | Response |
| --- | --- |
| A valid account request with a user token | `201`, with the account and its wallets |
| A repeated or unsupported currency, or an invalid balance | `422`, and nothing is created |
| A client reads its own wallet, or another user's | `200`, or `403` |

#### 4.1.3 Functional Requirements

**FR-1.1** The system shall create an account and its distinct-currency wallets in one transaction, owned by the token's subject.

**FR-1.2** An opening balance `b > 0` shall be recorded by debiting the currency's system account by `b` and crediting the wallet by `b`.

**Invariants:** I-1 to I-6.

**Pre-conditions:** a valid token and body.

**Post-conditions:** the account, wallets and funding entries all commit, or none do.

**Error cases:** invalid input returns `422`, and a failure on any wallet rolls back the whole request.

**Acceptance criteria:**

1. An account with INR 100000 and USD 0 returns `201`, and the ledger holds exactly 2 entries: a system debit and a wallet credit of 100000.
2. A repeated currency, or an opening balance of `-1`, `10.5`, `"100"` or `true`, returns `422` and creates nothing.
3. A request with no token returns `401`, and reading another user's wallet returns `403`.

### 4.2 FR-2: Idempotent Transfers

#### 4.2.1 Description and Priority

From the brief: "Transfer funds between two wallets. The endpoint must require an idempotency key (header) to ensure retried network requests never double-charge an account." Research: [[idempotent-api-design-patterns]].

**Priority:** High.

#### 4.2.2 Stimulus/Response Sequences

| Stimulus | Response |
| --- | --- |
| A valid transfer with a new key, from the caller's wallet | `201`, and the money moves |
| The same key and payload again | The stored response, and no money moves |
| The same key with a different payload | `422`, and no money moves |
| A missing key, insufficient funds, or another user's source wallet | `400`, `409` or `403`, and no money moves |

#### 4.2.3 Functional Requirements

**FR-2.1** The transfer endpoint shall require an `Idempotency-Key` header.

**FR-2.2** The key check, funds check, ledger entries, balance updates and idempotency record shall commit in one transaction.

**FR-2.3** A retry with the same key and payload shall never move money again.

**FR-2.4** A transfer shall be accepted only from a wallet owned by the token's subject.

**Invariants:** I-1 to I-7. For one key and payload, `|transactions(key)| <= 1`. A posted transfer of `a` changes `balance(from)` by `-a` and `balance(to)` by `+a`.

**Pre-conditions:** a valid token that owns the source wallet, a valid key and body, and two different existing wallets in the same currency.

**Post-conditions:** if posted, all writes committed together. If rejected, no ledger entries or balance changes.

**Error cases:**

- A crash before commit rolls back everything, so a retry applies the transfer once.
- A negative amount returns `422`. Otherwise `-500` reverses the transfer's direction and still passes reconciliation ([[financial-api-security-and-validation]]).

**Acceptance criteria:**

1. A valid transfer returns `201`, moves the amount and writes exactly 2 entries.
2. A retry returns the same status and body, with `Idempotent-Replayed: true`, and writes no entries.
3. The same key with a different amount returns `422`, and the same fields in a different JSON order count as a retry.
4. 8 concurrent requests with one key and payload produce 1 transfer and 8 identical responses.
5. A failure injected before commit, followed by a retry, moves the money exactly once.
6. An amount of 10^12 is accepted when funds allow, and 10^12 + 1 returns `422`.

### 4.3 FR-3: Concurrent Balance Mutability and Race Prevention

#### 4.3.1 Description and Priority

From the brief: "Safely handle multiple simultaneous incoming/outgoing transfer requests on the same wallet without data race conditions or balance corruption." Research: [[sqlite-acid-and-wal-concurrency]], [[race-conditions-and-optimistic-locking]].

**Priority:** High.

#### 4.3.2 Stimulus/Response Sequences

| Stimulus | Response |
| --- | --- |
| Several requests spend from one wallet at once | Each is serialized against the latest committed balance |
| More requests than the balance can cover | Those covered get `201`, and the rest get `409` |
| A request cannot get the write lock in time | `503`, and nothing is written |

#### 4.3.3 Functional Requirements

**FR-3.1** All money-moving requests shall run their funds check and writes in one `BEGIN IMMEDIATE` transaction.

**FR-3.2** A lock timeout shall return `503`, roll back, and be safe to retry with the same key.

**Invariants.** For concurrent requests on wallet `w`, where `S` is the set that succeeded:

```text
balance_final(w) == balance_initial(w) + SUM(incoming in S) - SUM(outgoing in S)
For k requests each spending a from balance b:   |S| == min(k, floor(b / a))
```

**Pre-conditions:** WAL mode, and a separate connection per request.

**Post-conditions:** the final state equals some serial order of the successful requests.

**Error cases:** double spends and lost updates are prevented by checking inside the transaction, and lost updates are also detected by FR-5.

**Acceptance criteria:**

1. 8 concurrent spends of 100 from a balance of 100 produce 1 `201` and 7 `409` responses and a final balance of 0, in each of 5 runs.
2. 8 concurrent spends of 10 from a balance of 100 all succeed, with a final balance of 20.
3. No response has status `500` or contains `database is locked`, and FR-5 reports `balanced: true` afterwards.
4. The race test fails against a deliberately unprotected version of the transfer, which proves that it detects the bug.

### 4.4 FR-4: Immutable Audit Trail and Reversal Transactions

#### 4.4.1 Description and Priority

From the brief: "Ledger records cannot be updated or deleted once written. Any corrections or cancellations must be recorded as an explicit reversal transaction." Research: [[immutable-audit-trail-and-reversals]].

**Priority:** High.

#### 4.4.2 Stimulus/Response Sequences

| Stimulus | Response |
| --- | --- |
| The source wallet's owner, or an admin, reverses a posted transfer | `201`, with 2 new offsetting entries, and the originals unchanged |
| A retry with the same key | The stored response, and no money moves |
| A second reversal, or a reversal of a reversal | `409` |
| The recipient no longer holds the funds | `409` `INSUFFICIENT_FUNDS` |
| Any attempt to change a ledger row, through the API or SQL | `405` from the API, and an error from the database, with the row unchanged |

#### 4.4.3 Functional Requirements

**FR-4.1** The database itself shall prevent committed ledger rows from being updated, deleted or replaced, including through `INSERT OR REPLACE`, which research showed can bypass delete triggers.

**FR-4.2** Corrections shall be new reversal transactions that reference the original, with at most one reversal per transfer.

**FR-4.3** The ledger shall be tamper-evident, as the brief requires: a change to a committed entry shall be detectable. A SHA-256 hash chain is the recommended method (OD-11).

**Invariants:** for a reversal of a transfer of `a` from `A` to `B`, `balance(A)` changes by `+a`, `balance(B)` changes by `-a`, and the net effect of both transactions on each wallet is 0. I-1 to I-7 hold.

**Pre-conditions:** the right to reverse, a transfer that is neither a reversal nor already reversed, and a recipient holding at least the amount.

**Post-conditions:** the original entries are unchanged, and 2 new entries reference them.

**Error cases:** blocked database statements raise an error and leave the row unchanged. A reversal after the recipient spent the money returns `409`, because research showed it would otherwise leave the wallet at -100.

**Acceptance criteria:**

1. Reversing a transfer of 100 restores both balances, and the ledger grows from 2 to 4 entries with the originals unchanged.
2. A second reversal returns `409`, and a retry with the same key replays the original response.
3. `UPDATE`, `DELETE`, `INSERT OR REPLACE` and `REPLACE INTO` each fail to alter a row on an application connection.
4. A reversal when the recipient no longer holds the funds returns `409`, and no balance changes.
5. A direct change to a committed entry is detected.

### 4.5 FR-5: Ledger Reconciliation Endpoint

#### 4.5.1 Description and Priority

From the brief: "An administrative endpoint that scans ledger entries and verifies that the sum of credits equals debits, and that current wallet balances match the calculated ledger sums." Research: [[ledger-reconciliation-algorithms]].

**Priority:** High.

#### 4.5.2 Stimulus/Response Sequences

| Stimulus | Response |
| --- | --- |
| An admin scans a clean ledger | `200`, with `balanced: true` |
| An admin scans a faulty ledger | `200`, with `balanced: false` and the failing rows |
| A user token, or no token | `403`, or `401` |

#### 4.5.3 Functional Requirements

**FR-5.1** The endpoint shall verify, per currency, that total credits equal total debits (I-2).

**FR-5.2** The endpoint shall verify that each wallet's balance matches its entries (I-3), including wallets with no entries.

**FR-5.3** All checks shall read one consistent snapshot. Separate statements produced false mismatches on 254 of 300 scans during live transfers.

**FR-5.4** The endpoint should also check that each transaction balances (I-1), that every entry refers to a known wallet, that user wallets are not negative (I-4), and that tampering is detected (FR-4.3). Research showed the two required checks miss offsetting one-sided entries, mixed currencies and unknown wallets.

**Invariants:** `balanced` is true only if every check passed, and a scan changes no data.

**Pre-conditions:** a valid token with the `admin` role.

**Post-conditions:** no data changed. The endpoint reports problems and never repairs them.

**Error cases:**

- An empty ledger returns `balanced: true`. A plain `SUM() = SUM()` returns `NULL`, which must not count as a failure.
- A balanced duplicate transfer cannot be detected here, so FR-2 must prevent it.

**Acceptance criteria:**

1. A clean ledger, and an empty one, each return `balanced: true`.
2. An overwritten balance, and a removed credit leg, are each reported.
3. No false mismatch occurs in 300 scans during live transfers.
4. A missing token returns `401`, a user token returns `403`, and counts are unchanged after a scan.

## 5. Other Nonfunctional Requirements

These targets are the team's verification criteria.

### 5.1 Performance Requirements

**No throughput or latency target is set in this version,** because the only timings available are from one machine and are not benchmarks. Correctness under concurrency is the measured requirement.

| ID | Name | Requirement | Measurable criteria | Verified by | Research |
| --- | --- | --- | --- | --- | --- |
| NFR-2 | Concurrency and Locking | Simultaneous requests cannot corrupt a balance | 8 threads, 5 runs: 0 overspends and 0 lost updates. 100% of write transactions use `BEGIN IMMEDIATE`. 0 raw lock errors reach a client | TQ-3, TQ-4 | [[race-conditions-and-optimistic-locking]] |

### 5.2 Safety Requirements

| ID | Name | Requirement | Measurable criteria | Verified by | Research |
| --- | --- | --- | --- | --- | --- |
| NFR-1 | ACID Atomicity | Every money movement commits completely or leaves no trace | With a failure injected at each write step of a transfer and reversal, 100% of cases leave balances, entries and idempotency records unchanged | TQ-2 | [[sqlite-acid-and-wal-concurrency]] |
| NFR-4 | Audit Immutability | Committed ledger rows never change | 100% of `UPDATE`, `DELETE` and `REPLACE` forms are blocked on application connections, and a direct change is detected | TQ-3, TQ-4 | [[immutable-audit-trail-and-reversals]] |

### 5.3 Security Requirements

| ID | Name | Requirement | Measurable criteria | Verified by | Research |
| --- | --- | --- | --- | --- | --- |
| NFR-5 | Input Security, Authentication and Negative Amount Prevention | Every endpoint authenticates the caller, all parameters are validated, and negative amounts are rejected | See below | TQ-4, Security Testing | [[financial-api-security-and-validation]] |

**Authentication and authorization.** The system shall require `Authorization: Bearer <token>` on all REST endpoints (Section 3.3.1), which closes OD-1 and OD-2.

- 100% of endpoints return `401` for a missing, unknown or expired token.
- 100% of wallet, transfer and reversal endpoints return `403` when the caller does not own the resource (OWASP API1:2023), and reconciliation returns `403` for a `user` token (OWASP API5:2023).
- Tokens are never stored in plain text, logged, placed in URLs or returned in responses, and token lifetime is limited, as RFC 6750 requires.

**Input validation and amounts.** The limit of 10^12 minor units per transaction is formally adopted, which closes OD-5.

- All cases in Section 6.2.2 return the specified status, with 0 `500` responses and 0 balance changes.
- The database rejects amounts that are not positive.
- 100% of SQL uses bound parameters.

A bearer token gives access to whoever holds it, so a stolen token works until it expires.

### 5.4 Software Quality Attributes

| ID | Name | Requirement | Measurable criteria | Verified by | Research |
| --- | --- | --- | --- | --- | --- |
| NFR-3 | Minor-Unit Precision | Money is exact, in integer minor units | 0 float money columns or variables. After 1,000,000 additions of 1, the stored value is exactly 1000000 | TQ-1, TQ-6 | [[integer-minor-units-money-math]] |
| NFR-6 | CI Test Database Isolation | Tests never share state or touch real data | CI runs on every push. Each test gets a new in-memory or temporary file database, and tests pass in any order | TQ-5 | [[provider-interface-isolation]] |
| NFR-7 | Provider Interface Decoupling | SQLite is isolated behind an interface (SE-6) | Exactly 1 package imports `sqlite3` or contains SQL, checked by an automated test | TQ-1, TQ-2 | [[provider-interface-isolation]] |
| NFR-8 | Structured Error Handling | Every error is structured, stable and safe | 100% of 4xx and 5xx responses use `application/problem+json` with a stable `code`. 0 responses echo rejected input or show a stack trace. `NaN` returns `422`, not `500` | TQ-3, TQ-4 | [[rest-api-error-handling-and-status-codes]] |

## 6. Other Requirements (Course Specifics)

### 6.1 Agent Skill Requirements (SK-1 to SK-5)

Skills follow the Agent Skills format: `.claude/skills/<name>/SKILL.md`, with a `name` that matches the folder. Each must cite at least one distilled note (SB-3) and be evaluated before its stage submission (TQ-7). Only SK-1 is built. Research: [[agent-skills-and-second-brain-architecture]].

#### 6.1.1 SK-1: brain-ingest (Stage 1, built)

| Aspect | Specification |
| --- | --- |
| Inputs | Pasted text, a file path, a URL, or `brain/inbox/` |
| Workflow | Read the source as data, choose the PARA folder, write the note from the template, link requirements and related notes, update the index and log, then validate |
| Outputs | A note in the correct folder, an updated `brain/index.md`, and a `brain/log.md` entry |
| Validation rules | `validate_skills.py`, `validate_brain.py` and `evaluate_brain_ingest.py` pass |
| Cited notes (SB-3) | [[double-entry-bookkeeping-principles]], [[stage1-ai-session-setup]] |

#### 6.1.2 SK-2: brain-refine (Stage 2, not started)

| Aspect | Specification |
| --- | --- |
| Inputs | A folder or note, or all of `brain/` by default |
| Workflow | Move notes to PARA folders, merge duplicates and fix links, then update the index and log |
| Outputs | Reorganized notes, and a report of each change |
| Validation rules | `validate_brain.py` passes, and no source or requirement link is lost |
| Cited notes (SB-3) | [[agent-skills-and-second-brain-architecture]], [[stage1-review-retrospective]] |

#### 6.1.3 SK-3: brain-query (Stage 2, not started)

| Aspect | Specification |
| --- | --- |
| Inputs | A question or document request |
| Workflow | Start from `brain/index.md`, read the relevant notes, answer or draft documents such as ADRs, and log the run |
| Outputs | An answer or draft with wikilink citations, and a list of gaps |
| Validation rules | Every claim cites a note that resolves, or is marked as a gap |
| Cited notes (SB-3) | [[agent-skills-and-second-brain-architecture]], [[ledger-reconciliation-algorithms]] |

#### 6.1.4 SK-4: local-check (Stage 2 first version, not started)

From the course document: "Confirm that the project works on a team member's machine."

| Aspect | Specification |
| --- | --- |
| Inputs | A test token from the environment |
| Workflow | Build the project, run the automated test suite, start the local server, invoke one read-only fetch endpoint, and report pass or fail for each step |
| Outputs | A pass or fail result per step |
| Validation rules | Uses a temporary database, stops its server, and never prints the token |
| Cited notes (SB-3) | [[provider-interface-isolation]], [[stage1-ai-session-setup]] |

#### 6.1.5 SK-5: simulate-transfer (Stage 3, not started)

From the brief: "Run a complete product workflow and verify ledger consistency."

| Aspect | Specification |
| --- | --- |
| Inputs | Base URL, and user and admin tokens from the environment |
| Workflow | Create two test wallets, record initial balances, execute a transfer with an idempotency key, fire two concurrent transfer requests, then call the reconciliation endpoint and summarize final balances |
| Outputs | A step-by-step report, final balances, and an overall pass or fail |
| Validation rules | Final balances equal the calculated values, because passing reconciliation alone cannot detect a balanced duplicate |
| Cited notes (SB-3) | [[ledger-reconciliation-algorithms]], [[race-conditions-and-optimistic-locking]], [[idempotent-api-design-patterns]] |

### 6.2 Testing and Quality (TQ-1 to TQ-8)

#### 6.2.1 Verification Matrix

The repository has 1 product test (`GET /health`) and SRS checks in `tests/test_srs.py`. **The product tests below are planned, because the features do not exist yet.** CI already runs build, lint, tests, secret scanning, and skill and brain validation.

| ID | Requirement, from the course documents | Verification method | Status |
| --- | --- | --- | --- |
| TQ-1 | Unit tests for accounting calculations, ledger balance assertions, and idempotency key hashing | Unit tests of amount rules, invariants and the payload hash | Planned |
| TQ-2 | Integration tests verifying database transactions and database rollback behavior on simulated transfer failures | Inject failures at each write step, then assert no change | Planned |
| TQ-3 | System (end-to-end) tests for each of FR-1 to FR-5 | API tests of each feature's acceptance criteria | Planned |
| TQ-4 | Negative tests: negative balance attempts, insufficient funds, invalid idempotency payloads, malformed IDs, and simultaneous concurrent transfers (proving race safety) | Section 6.2.2, plus threaded race tests on a file database | Planned |
| TQ-5 | CI tests shall run against an isolated test database (e.g., an in-memory or fresh local database instance) on every push | A fixture gives each test its own database | CI done, fixture planned |
| TQ-6 | The system shall prevent floating-point rounding errors. Test that monetary amounts are strictly handled using integer minor units (e.g., cents/paise) or exact decimal types | Reject fractional input, and repeat balance updates through real code, because `sum()` and `SUM()` can hide the drift | Planned |
| TQ-7 | Skill evaluations shall run before each stage submission. Record results in the test documentation | Section 6.3 records Stage 1 | Stage 1 partial |
| TQ-8 | Maintain and update tests as the system changes. Each significant defect gets a regression test | Review rule, and a defect log from Stage 3 | Planned |
| Security Testing | Input validation (all API parameters), Negative amount prevention (preventing users from sending negative values to inflate balances) | Section 6.2.2, on every endpoint | Planned |

#### 6.2.2 Security and Negative Test Cases

| Parameter | Input | Expected |
| --- | --- | --- |
| `Authorization` | Missing, unknown or expired | `401` |
| `Authorization` | Malformed | `400` |
| `Authorization` | Another user's wallet, or a user token on reconciliation | `403` |
| `amount_minor` | `-500`, `0`, `10.5`, `500.0`, `"500"`, `true`, `null`, `NaN`, above 10^12 | `422`, with no balance change and no `500` |
| Body | Unknown field, malformed JSON, or a rejected value holding a secret | `422`, with the value not echoed |
| Wallet ID | Malformed, including SQL text such as `' OR 1=1 --` | `422` |
| Wallet ID | Valid but unknown | `404` |
| `from_wallet_id`, `to_wallet_id` | The same wallet | `422` |
| `Idempotency-Key` | Missing, empty, 256 characters, or invalid characters | `400` |

### 6.3 Stage 1 Skill Evaluation (TQ-7)

The evaluation covers `brain-ingest` (SK-1) on 2026-11-09, using Python 3.12.5 on Windows. Reproduce it with `python scripts/evaluate_brain_ingest.py`. It audits the 11 `type: research` notes that the skill's workflow produced, and tests the validators that guard them.

#### 6.3.1 Assertions

Each note is checked against 12 assertions: required frontmatter fields (A1), `id` matches the filename (A2), research type with a named author (A3), source recorded (A4), all 6 template headings in order (A5), frontmatter IDs equal linked IDs (A6), IDs within their series (A7), an existing related note linked (A8), inferences labelled, by keyword check (A9), filed under `brain/resources/` (A10), listed in the index (A11), and recorded in the log (A12).

#### 6.3.2 Results Per Note

**First run: 131 of 132 assertions passed.** One real defect was found: `double-entry-bookkeeping-principles` linked SE-3 in its body but not in its frontmatter, failing A6. The note was corrected. **Second run: 132 of 132 assertions passed.**

| Note | Author | First run | Second run |
| --- | --- | --- | --- |
| [[double-entry-bookkeeping-principles]] | Member 1 | 11/12, failed A6 | 12/12 |
| [[integer-minor-units-money-math]] | Member 1 | 12/12 | 12/12 |
| [[rest-api-error-handling-and-status-codes]] | Member 1 | 12/12 | 12/12 |
| [[sqlite-acid-and-wal-concurrency]] | Member 2 | 12/12 | 12/12 |
| [[race-conditions-and-optimistic-locking]] | Member 2 | 12/12 | 12/12 |
| [[provider-interface-isolation]] | Member 2 | 12/12 | 12/12 |
| [[idempotent-api-design-patterns]] | Member 3 | 12/12 | 12/12 |
| [[immutable-audit-trail-and-reversals]] | Member 3 | 12/12 | 12/12 |
| [[ledger-reconciliation-algorithms]] | Member 3 | 12/12 | 12/12 |
| [[financial-api-security-and-validation]] | Member 4 | 12/12 | 12/12 |
| [[agent-skills-and-second-brain-architecture]] | Member 4 | 12/12 | 12/12 |

#### 6.3.3 Validator Fault Injection

Each of 20 cases copied the brain to a temporary folder, applied one change and ran `validate_brain.py`. All 20 behaved as expected. It rejected all 15 faults, such as a link to a missing note, an out-of-range FR-6 or SE-8, missing or invalid frontmatter, and a deleted index or log. It accepted the 2 controls.

The other 3 cases are **known gaps**, which it accepts: a link to an out-of-range TQ-99, a removed template heading, and a new note missing from the index. The evaluation script covers these for the 11 notes, but CI does not run it, so they remain open for new notes.

The reference validator (`agentskills validate`, from `skills-ref` 0.1.1) reported `Valid skill`.

#### 6.3.4 Limitations and Verdict

- **No baseline comparison.** The Agent Skills guidance recommends running test cases with and without the skill in a clean context. This was not done, so this does not show that the skill improves on no skill.
- **Structure, not accuracy.** The assertions check format and links, not whether a note's claims are correct.
- **No transcripts or stored test prompts.** The assertions were also written after the notes, by the same AI-assisted process.

**Verdict: partial.** The skill's outputs conform to its rules, and the validators catch the faults they claim to. TQ-7 is not fully met until with-skill and without-skill runs are recorded and a human has reviewed the outputs.

### 6.4 Traceability Matrix and Task Breakdown (SE-4, SE-5)

#### 6.4.1 Four-Stage Roadmap (SE-4)

The course documents set no dates, so the team must add them. They also set no separate implementation stage, so **the plan builds FR-1 to FR-5 during Stage 2 and early Stage 3.**

| Stage | Deliverables, from the course document | Status on 2026-11-09 |
| --- | --- | --- |
| Stage 1: Requirements | SRS (FR, NFR, SK). Brain set up as an Obsidian vault (PARA, index, log). `brain-ingest` used to add at least 10 research notes. `AGENTS.md`. Repository and CI skeleton | SRS written, 11 research notes, `AGENTS.md` and CI done. Obsidian use unconfirmed |
| Stage 2: Design | Architecture and design documentation. Diagrams. `brain-refine` and `brain-query` skills. First version of `local-check` | Not started |
| Stage 3: Testing and CI | Continuous testing and CI plan and results. `simulate-transfer` with test results. Defect log with regression tests. Review note for each stage | Not started |
| Stage 4: Review | Live demonstration of FRs in client. Run product skill end-to-end. Run `local-check` live. Run `brain-query` live. Walk through a requirement from brain note to ADR, code and test. Final release tag | Not started |

#### 6.4.2 Four-Member Task Allocation

Completed work comes from Git history. **Future owners are proposals for the team to confirm.**

| Member | Stage 1, completed | Stage 2, proposed | Stage 3, proposed | Stage 4, proposed |
| --- | --- | --- | --- | --- |
| Member 1 (Hemakshi Jadeja) | Repository, CI, validators, `AGENTS.md`, `brain-ingest`, 3 notes (PR #1) | Architecture, diagrams, traceability matrix, FR-1, error format | System tests (TQ-3), CI plan and results | Demonstration of FR-1 and FR-5 |
| Member 2 (Aditya Bhat) | 3 notes (PR #2) | ER diagram, schema, storage provider (SE-6), FR-3, `local-check` | Race tests (TQ-4), integration tests (TQ-2), isolation (TQ-5) | `local-check` live, demonstration of FR-3 |
| Member 3 (Subhadeep Das) | 3 notes (PR #3) | Idempotency and immutability ADRs, FR-2, FR-4, `brain-refine` | Unit tests (TQ-1), `simulate-transfer` | `simulate-transfer` live, demonstration of FR-2 and FR-4 |
| Member 4 (Hardh Kava) | 2 notes, Stage 1 review (PR #4) | Validation and authentication ADRs, token authentication, FR-5, `brain-query` | Security tests, TQ-6, skill evaluations (TQ-7), defect log | `brain-query` live, requirement walkthrough |

#### 6.4.3 Traceability Matrix (SE-5)

This shows the state on 2026-11-09, read from the GitHub API and Git history. The repository has **0 issues**, so every Issue cell shows "None". PR cells list merged PRs with related work, and "Impl. pending" means no implementation PR exists yet. "This SRS" means this document's PR, which is not yet open. Test IDs are planned categories unless stated otherwise.

| Requirement ID | GitHub Issue | PR | Test ID (TQ-*) | Skill (SK-*) | Brain Note |
| --- | --- | --- | --- | --- | --- |
| FR-1 | None | #1 research. Impl. pending | TQ-1, TQ-3, TQ-4, TQ-6 | SK-5 | [[double-entry-bookkeeping-principles]] |
| FR-2 | None | #3 research. Impl. pending | TQ-1, TQ-2, TQ-3, TQ-4 | SK-5 | [[idempotent-api-design-patterns]] |
| FR-3 | None | #2 research. Impl. pending | TQ-2, TQ-3, TQ-4 | SK-5 | [[race-conditions-and-optimistic-locking]] |
| FR-4 | None | #3 research. Impl. pending | TQ-2, TQ-3, TQ-4 | SK-4 | [[immutable-audit-trail-and-reversals]] |
| FR-5 | None | #3 research. Impl. pending | TQ-1, TQ-3 | SK-5 | [[ledger-reconciliation-algorithms]] |
| NFR-1 | None | #2 research. Impl. pending | TQ-2 | SK-4 | [[sqlite-acid-and-wal-concurrency]] |
| NFR-2 | None | #2 research. Impl. pending | TQ-3, TQ-4 | SK-5 | [[race-conditions-and-optimistic-locking]] |
| NFR-3 | None | #1 research. Impl. pending | TQ-1, TQ-6 | SK-4 | [[integer-minor-units-money-math]] |
| NFR-4 | None | #3 research. Impl. pending | TQ-3, TQ-4 | SK-4 | [[immutable-audit-trail-and-reversals]] |
| NFR-5 | None | #4 research. Impl. pending | TQ-4 | SK-4 | [[financial-api-security-and-validation]] |
| NFR-6 | None | #2 research. Impl. pending | TQ-5 | SK-4 | [[provider-interface-isolation]] |
| NFR-7 | None | #2 research. Impl. pending | TQ-1, TQ-2 | SK-4 | [[provider-interface-isolation]] |
| NFR-8 | None | #1 research. Impl. pending | TQ-3, TQ-4 | SK-4 | [[rest-api-error-handling-and-status-codes]] |
| SK-1 | None | #1 built | TQ-7 (Stage 1 partial) | SK-1 | [[agent-skills-and-second-brain-architecture]] |
| SK-2 | None | Impl. pending | TQ-7 | SK-2 | [[agent-skills-and-second-brain-architecture]] |
| SK-3 | None | Impl. pending | TQ-7 | SK-3 | [[agent-skills-and-second-brain-architecture]] |
| SK-4 | None | Impl. pending | TQ-7 | SK-4 | [[agent-skills-and-second-brain-architecture]] |
| SK-5 | None | Impl. pending | TQ-7 | SK-5 | [[ledger-reconciliation-algorithms]] |
| TQ-1 | None | Impl. pending | TQ-1 | SK-4 | [[idempotent-api-design-patterns]] |
| TQ-2 | None | Impl. pending | TQ-2 | SK-4 | [[sqlite-acid-and-wal-concurrency]] |
| TQ-3 | None | Impl. pending | TQ-3 | SK-4, SK-5 | [[rest-api-error-handling-and-status-codes]] |
| TQ-4 | None | Impl. pending | TQ-4 | SK-4, SK-5 | [[financial-api-security-and-validation]] |
| TQ-5 | None | #1 CI. Fixture pending | TQ-5 | SK-4 | [[provider-interface-isolation]] |
| TQ-6 | None | Impl. pending | TQ-6 | SK-4 | [[integer-minor-units-money-math]] |
| TQ-7 | None | This SRS | TQ-7 (Stage 1 partial) | SK-1 | [[agent-skills-and-second-brain-architecture]] |
| TQ-8 | None | Impl. pending | TQ-8 | SK-4 | [[stage1-review-retrospective]] |
| Security Testing | None | #4 research. Impl. pending | TQ-4 | SK-4 | [[financial-api-security-and-validation]] |
| SE-1 | None | This SRS | Not applicable | SK-3 | [[stage1-review-retrospective]] |
| SE-2 | None | Stage 2 pending | Not applicable | SK-3 | [[stage1-review-retrospective]] |
| SE-3 | None | Stage 2 pending | Not applicable | SK-3 | [[stage1-review-retrospective]] |
| SE-4 | None | #4 outline, this SRS | Not applicable | None | [[stage1-review-retrospective]] |
| SE-5 | None | This SRS | Not applicable | None | [[stage1-review-retrospective]] |
| SE-6 | None | #2 research. Impl. pending | TQ-1, TQ-2 | SK-4 | [[provider-interface-isolation]] |
| SE-7 | None | Impl. pending | TQ-3 | None | [[rest-api-error-handling-and-status-codes]] |
| SB-1 | None | #1 validator | TQ-7 (Stage 1 partial) | SK-1, SK-2 | [[agent-skills-and-second-brain-architecture]] |
| SB-2 | None | #1 draft, #4 completed | Not applicable | None | [[stage1-review-retrospective]] |
| SB-3 | None | #1 for `brain-ingest` | TQ-7 (Stage 1 partial) | SK-1 | [[agent-skills-and-second-brain-architecture]] |
| SB-4 | None | #1 | Not applicable | None | [[stage1-ai-session-setup]] |
| SB-5 | None | #1 to #4 | Not applicable | None | [[stage1-review-retrospective]] |
| SB-6 | None | #1 to #4 | Not applicable | None | [[stage1-review-retrospective]] |

#### 6.4.4 Known Gaps Against the Course Documents

| Gap | Next action |
| --- | --- |
| 0 GitHub Issues | Create one issue per requirement, and update the matrix |
| 0 recorded PR reviews on PRs #1 to #4 | Enable a required review, and review this SRS's PR |
| TQ-7 is partial | Run the with-skill and without-skill comparison, with a human review |
| NFR, SK and contract details are team-defined | Record the decisions in Section 2.7 as ADRs |
| Only `/health` is implemented, without a token check | Build the features under the Section 6.4.1 plan |
