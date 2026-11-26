# ADR-0006: Put SQLite behind a separate storage layer

- **Date:** 2026-11-26
- **Author:** Hemakshi
- **Requirements:** SE-6, TQ-5, TQ-2, FR-3

## Status

Proposed

## Context

SE-6 says we have to "isolate external dependencies behind a provider interface". SQLite is the only external dependency we have, so it is the one this applies to ([[provider-interface-isolation]]).

TQ-5 also says CI has to run tests against an isolated test database on every push. If the service code opens SQLite directly, tests cannot easily give it a different database.

Some other things from the notes:

- Separate `get` and `set` calls with no transaction around them would let the double-spend race happen ([[race-conditions-and-optimistic-locking]]).
- In-memory SQLite quietly ignores WAL (the pragma returns `memory`) and cannot be shared between connections, so race tests for FR-3 need a fresh file database ([[provider-interface-isolation]]).
- The pragmas each connection needs, like WAL and the busy timeout, have to be set in one place ([[sqlite-acid-and-wal-concurrency]]).

## Decision

All database access goes through a small storage interface (a Python `Protocol`, for example `WalletStore`). The service layer only talks to this interface and never contains SQL. A `SqliteStore` class implements it.

The interface has a `write_transaction()` method. In `SqliteStore` this runs `BEGIN IMMEDIATE` when it starts, `COMMIT` when it finishes normally and `ROLLBACK` on an exception. FastAPI gets the store through a dependency, so tests can swap it with `app.dependency_overrides`.

Tests use real SQLite, not a dictionary fake: `:memory:` for fast unit tests, and a fresh file in pytest's `tmp_path` for race and end-to-end tests.

## Consequences

Good:

- We meet SE-6, and the service code is easier to read because it has no SQL in it.
- Each test gets its own database, which covers TQ-5. The real dependency can raise an error if a test ever reaches it, so tests never touch the production file ([[provider-interface-isolation]]).
- Rollback tests (TQ-2) go through the same transaction code as production.
- The prototype in the note passed all 9 tests, including 8 threads spending at once with 1 success and 7 rejections ([[provider-interface-isolation]]).
- SQLite errors can be changed into our own errors, like `StoreBusyError`, at the boundary, and the API can map them to status codes ([[rest-api-error-handling-and-status-codes]]).

Bad:

- It is one more layer to write and explain.
- File databases are slower. 50 of them took about 3.4 s against 0.2 s for in-memory ones on Windows, and we have not measured this on the Linux CI runner yet.
- We have to keep the interface small and only add methods the transfer and reconciliation code really need, or it will grow too big. (my suggestion: review new methods in the PR)
- We still have not decided how FastAPI should manage connections, for example whether `check_same_thread=False` is needed. This is an open question in the note.

## Brain notes cited

- [[provider-interface-isolation]]: The SE-6 and TQ-5 wording, the `WalletStore` prototype and its test results, the in-memory versus file table, and the error translation idea.
- [[race-conditions-and-optimistic-locking]]: Why the transaction has to be part of the interface.
- [[sqlite-acid-and-wal-concurrency]]: The connection pragmas that belong inside the SQLite class.
- [[rest-api-error-handling-and-status-codes]]: Where translated storage errors end up as status codes.
