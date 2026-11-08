---
id: sqlite-acid-and-wal-concurrency
title: SQLite ACID Properties and WAL Concurrency
type: research
author: Member 2
stage: 1
status: active
created: 2026-11-08
source:
  - "Financial_Ledger.pdf, p. 2 (FR-3 context, TQ-2, Database Architecture)"
  - "SQLite Is Transactional: https://sqlite.org/transactional.html"
  - "Write-Ahead Logging, SQLite: https://sqlite.org/wal.html"
  - "Transaction, SQLite: https://sqlite.org/lang_transaction.html"
  - "Isolation In SQLite: https://sqlite.org/isolation.html"
  - "sqlite3_busy_timeout, SQLite: https://sqlite.org/c3ref/busy_timeout.html"
  - "sqlite3 module, Python documentation: https://docs.python.org/3/library/sqlite3.html"
  - "Local experiments, 2026-11-08: Python 3.12.5, SQLite 3.45.3, on Windows"
related_requirements: [FR-3, TQ-2, FR-5, SE-3]
---

# SQLite ACID Properties and WAL Concurrency

## Summary

SQLite transactions are ACID and serializable, and only one writer can run at a time. WAL mode changes how readers and writers interact, but it does not stop race conditions by itself: with WAL on, an unprotected check-then-write let 8 threads spend the same balance. Safe transfers need the check and the writes inside a `BEGIN IMMEDIATE` transaction, with a busy timeout so waiting writers queue instead of failing at once.

## Key points

### ACID in SQLite

| Property | What SQLite provides | Local check |
| --- | --- | --- |
| Atomic | Changes "either occur completely or not at all", even through a crash or power failure | `ROLLBACK` after a simulated failure, and closing a connection without `COMMIT`, both left the balance at 100 |
| Consistent | Declared constraints only. Business rules such as debit == credit are the application's job (my inference) | Not tested |
| Isolated | "Serializable" isolation. Readers see only committed transactions, and WAL readers keep a fixed snapshot | A reader saw 100 during another connection's uncommitted write of 7 |
| Durable | Depends on `PRAGMA synchronous`, see below | Real power loss was not tested |

### WAL mode

- `PRAGMA journal_mode=WAL;` persists in the database file. A new connection reported `wal` without setting it.
- SQLite's documentation says "writers do not block readers and readers do not block writers", but adds that this is "mostly true".
- There can still be only one writer at a time, because there is only one WAL file.
- All processes must be on the same host. WAL does not work over a network filesystem.
- **Durability trade-off:** with `synchronous=FULL`, writers sync the WAL on every commit. With `NORMAL`, transactions "might rollback following a power failure or hard reset". This build defaulted to `2` (FULL).
- **Limit of my test:** the reader also saw the old value in rollback-journal mode, during an open uncommitted write. That test therefore does not demonstrate WAL's reader advantage, which needs a test during the commit itself.

### Transaction types

- `BEGIN` is `DEFERRED` by default: it starts no transaction until the first database access, and a leading `SELECT` starts only a read transaction.
- `BEGIN IMMEDIATE` starts a write transaction straight away, so it takes the single write slot before any check runs.
- A write inside a read transaction must upgrade. If another connection has already changed the database, the upgrade fails with `SQLITE_BUSY`.

### Busy timeouts

- A busy timeout makes a blocked connection sleep and retry until "at least" the given time has passed, then return `SQLITE_BUSY`.
- Python's `sqlite3.connect()` defaults to `timeout=5.0`. Setting `timeout=2.5` gave `PRAGMA busy_timeout` of `2500`, while another new connection stayed at `5000`, so the value is per connection.

| Test | Result |
| --- | --- |
| Second `BEGIN IMMEDIATE`, timeout 0 | `SQLITE_BUSY` after 0.001 s |
| Second `BEGIN IMMEDIATE`, timeout 0.5 s | `SQLITE_BUSY` after 0.974 s |
| Upgrade from a stale read, timeout 5 s | `SQLITE_BUSY_SNAPSHOT` after 0.000 s |

**A busy timeout does not rescue a stale read.** The last row failed immediately despite the 5-second timeout, because waiting cannot make an old snapshot current. `BEGIN IMMEDIATE` avoids this case.

### Python driver traps

- By default, the driver opens a transaction only before `INSERT`, `UPDATE`, `DELETE` or `REPLACE`. In the test, `in_transaction` was `False` after a `SELECT` and `True` after an `UPDATE`, so a balance check by `SELECT` runs outside the transaction.
- Sharing a connection across threads raises `ProgrammingError` by default.
- `foreign_keys` was `0` on a new connection, so it needs enabling.

## Relevance to Coinfidential

These are my recommendations, based on the results above:

- **Run every transfer in `BEGIN IMMEDIATE`,** covering the idempotency check, the balance check, the ledger entries and the balance updates. [[race-conditions-and-optimistic-locking]] compares the alternatives.
- **Open one connection per request** with `isolation_level=None`, so the code controls `BEGIN` explicitly.
- **Set per-connection options every time:** `busy_timeout` and `foreign_keys=ON`. Set `synchronous=FULL` explicitly as well, because losing a committed transfer in a power failure is not acceptable for a ledger.
- **Keep write transactions short,** because every other writer waits for them.
- **Test rollback for [[TQ-2]]** by failing between the debit and the credit entry, then asserting that balances and entries are unchanged. The test database must be a real file for concurrency, as explained in [[provider-interface-isolation]].
- **The `.gitignore` already covers WAL sidecar files,** so `-wal` and `-shm` files will not be committed.

## Requirements

- [[FR-3]]: `BEGIN IMMEDIATE` and a busy timeout provide the safe handling of simultaneous transfers on a wallet.
- [[TQ-2]]: Atomic rollback is the behavior these integration tests must verify.
- [[FR-5]]: Atomic commits keep balances and ledger entries in step, which reconciliation verifies.
- [[SE-3]]: The journal mode and transaction strategy belong in an ADR.

## Related notes

- [[race-conditions-and-optimistic-locking]]: Measures what happens with and without these controls.
- [[provider-interface-isolation]]: Explains where the transaction boundary lives in the code.
- [[double-entry-bookkeeping-principles]]: The debit and credit entries are what must commit together.
- [[integer-minor-units-money-math]]: Covers `STRICT` tables and integer amounts for the same schema.
- [[rest-api-error-handling-and-status-codes]]: Defines the API errors, but not yet a response for a busy timeout.

## Open questions

- What busy timeout should production use? 5 seconds is Python's default, not a tested value for this project.
- Python's documentation recommends the 3.12 `autocommit` attribute over `isolation_level`, and says its default will change in a future release. I tested only `isolation_level=None`, so `autocommit=True` still needs checking.
- These results come from one Windows machine. Timings will differ on the CI runner.
