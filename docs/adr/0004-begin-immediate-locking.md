# ADR-0004: Use BEGIN IMMEDIATE with WAL mode for transfers

- **Date:** 2026-11-26
- **Author:** Aditya
- **Requirements:** FR-3, TQ-2, TQ-4, SE-3

## Status

Proposed

## Context

FR-3 says two transfers on the same wallet at the same time must not break the balance. The risk is a check-then-spend race: two requests both read a balance of 100, both pass the "enough funds" check, and both spend it.

Things we already know:

- WAL mode does not stop this race by itself. With WAL on, 8 threads with no locking all spent the same 100, ending at -700 ([[race-conditions-and-optimistic-locking]]).
- A plain `BEGIN` is deferred, so the balance `SELECT` runs in a read transaction. Upgrading it to a write later can fail with `SQLITE_BUSY_SNAPSHOT`, and a busy timeout does not help with that ([[sqlite-acid-and-wal-concurrency]]).
- SQLite only allows one writer at a time anyway ([[sqlite-acid-and-wal-concurrency]]).

## Decision

Every transfer runs inside one `BEGIN IMMEDIATE` transaction that covers the idempotency check, the balance check, the ledger entries and the balance updates. Each request opens its own connection with `isolation_level=None` and sets `busy_timeout`, `foreign_keys=ON` and `synchronous=FULL`.

We will also write the debit as a guarded `UPDATE ... WHERE balance >= amount` as a second safety check. (my suggestion, also suggested in [[race-conditions-and-optimistic-locking]])

## Consequences

Good:

- In testing, `BEGIN IMMEDIATE` paid exactly once out of 8 racing requests, and the other 7 were rejected cleanly ([[race-conditions-and-optimistic-locking]]).
- No conflicts and no retry loop under normal load, unlike optimistic locking, which had 17 to 24 conflicts per trial ([[race-conditions-and-optimistic-locking]]).
- It also serializes ledger writes, which the hash chain in ADR-0003 needs.

Bad:

- Writers wait for each other, so transactions must stay short.
- If the busy timeout runs out we get `SQLITE_BUSY`. We still need to pick the timeout value and the API error for it (maybe `503`, not decided yet).
- Tests for TQ-2 and TQ-4 need a real file database and separate connections, not an in-memory one ([[provider-interface-isolation]]).

## Brain notes cited

- [[sqlite-acid-and-wal-concurrency]]: How WAL, `BEGIN IMMEDIATE`, busy timeouts and the Python driver behave.
- [[race-conditions-and-optimistic-locking]]: The race test results and the comparison with optimistic locking.
- [[provider-interface-isolation]]: Why concurrency tests need a file database.
