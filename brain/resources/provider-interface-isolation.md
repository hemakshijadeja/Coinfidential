---
id: provider-interface-isolation
title: Isolating SQLite Behind a Provider Interface
type: research
author: Member 2
stage: 1
status: active
created: 2026-11-08
source:
  - "SDLC_and_Workflow.pdf, p. 1 (SE-6)"
  - "Financial_Ledger.pdf, p. 2 (TQ-2, TQ-5, Database Architecture)"
  - "Repository, Martin Fowler: https://martinfowler.com/eaaCatalog/repository.html"
  - "In-Memory Databases, SQLite: https://sqlite.org/inmemorydb.html"
  - "Testing Dependencies with Overrides, FastAPI: https://fastapi.tiangolo.com/advanced/testing-dependencies/"
  - "How to use temporary directories, pytest: https://docs.pytest.org/en/stable/how-to/tmp_path.html"
  - "Local experiments, 2026-11-08: Python 3.12.5, SQLite 3.45.3, FastAPI 0.139.2, on Windows"
related_requirements: [SE-6, TQ-5, TQ-1, TQ-2, TQ-3, TQ-4, FR-3, SE-3]
---

# Isolating SQLite Behind a Provider Interface

## Summary

SE-6 requires external dependencies to sit behind a provider interface, and TQ-5 requires CI to use an isolated test database on every push. A small storage interface lets the code under test receive any database that the test chooses. In-memory SQLite suits fast single-connection tests, but it silently ignores WAL and cannot host concurrent connections as files can, so FR-3 tests need a fresh file database.

## Key points

- **SE-6:** "Isolate external dependencies behind a provider interface."
- **TQ-5:** CI tests run against "an isolated test database (e.g., an in-memory or fresh local database instance) on every push".
- **Repository pattern:** Fowler describes a layer that mediates between the domain and data mapping layers "using a collection-like interface", with a one-way dependency. His page does not discuss testing or swapping databases, so those benefits below are my inference.
- **FastAPI support:** `app.dependency_overrides` replaces a dependency during tests. The documentation's example is an external authentication provider, not a database, but the mechanism is general.
- **pytest support:** `tmp_path` gives each test function its own temporary directory, and by default keeps the directories from the last 3 runs.

### In-memory versus fresh file

| Behavior | `:memory:` | Shared-cache memory URI | Fresh file in `tmp_path` |
| --- | --- | --- | --- |
| `PRAGMA journal_mode=WAL` returns | `memory` | `memory` | `wal` |
| Second connection sees the data | No, `no such table` | Yes | Yes |
| Reader during an open write | Not applicable | Fails at once, `SQLITE_LOCKED_SHAREDCACHE` | Reads the committed value |
| 50 databases created (this machine) | 0.225 s | Not measured | 3.398 s |

The `PRAGMA` does not raise an error on `:memory:`. It just returns `memory`, so a test can appear to use WAL without doing so. The shared-cache lock error also differs from the `SQLITE_BUSY` that production would see.

### Tested prototype

I built this design in a scratch directory, not in the repository. All 9 tests passed: 3 behavior tests run against both database types, plus concurrent spending, the `:memory:` isolation check and a FastAPI override.

```python
class WalletStore(Protocol):
    def write_transaction(self) -> ContextManager["WalletStore"]: ...
    def get_balance(self, wallet_id: str) -> int: ...
    def set_balance(self, wallet_id: str, balance: int) -> None: ...

def spend(store: WalletStore, wallet_id: str, amount: int) -> bool:
    with store.write_transaction() as tx:
        balance = tx.get_balance(wallet_id)
        if balance < amount:
            return False
        tx.set_balance(wallet_id, balance - amount)
        return True
```

The SQLite implementation runs `BEGIN IMMEDIATE` on entering `write_transaction()`, `COMMIT` on a normal exit and `ROLLBACK` on an exception. The concurrent test confirmed that 8 threads produced 1 success and 7 rejections through this interface.

## Relevance to Coinfidential

These are my recommendations, based on the results above:

- **Put the transaction in the interface.** Separate `get` and `set` calls without one would allow the race in [[race-conditions-and-optimistic-locking]]. Keep `BEGIN IMMEDIATE` inside the SQLite class so the service code never contains SQL.
- **Choose the database by test type:**

  | Test | Database | Why |
  | --- | --- | --- |
  | [[TQ-1]] unit tests | `:memory:` | Fast, single connection |
  | [[TQ-2]] rollback tests | `:memory:` and file | Rollback works on both |
  | [[TQ-4]] and [[FR-3]] race tests | Fresh file | Needs separate connections and WAL |
  | [[TQ-3]] end-to-end tests | Fresh file | Closest to production |

- **Use real SQLite in tests rather than a Python dictionary fake.** A fake would not reproduce locks, rollback or constraints, which are the behaviors most in need of testing here.
- **Run shared behavior tests against both database types,** using a parametrized pytest fixture as the prototype did.
- **Translate database errors at the boundary.** Raising something like `StoreBusyError` keeps `sqlite3` exceptions out of the service layer, and lets the API map them to the codes in [[rest-api-error-handling-and-status-codes]].
- **Keep the interface small.** There is only one database today, so only add methods that the transfer and reconciliation code actually needs.
- **Never let tests open the production path.** In the prototype, the real dependency raises an error if a test ever reaches it.

## Requirements

- [[SE-6]]: The storage interface isolates SQLite from the service layer.
- [[TQ-5]]: Each test gets its own in-memory or fresh file database, on every push.
- [[TQ-2]]: Rollback tests run through the same transaction boundary as production code.
- [[FR-3]]: Race tests need a file database, which the interface can supply.

## Related notes

- [[sqlite-acid-and-wal-concurrency]]: Explains the pragmas each connection needs, which belong in the SQLite class.
- [[race-conditions-and-optimistic-locking]]: Defines the concurrent test this design must support.
- [[double-entry-bookkeeping-principles]]: The store must write balanced entries inside one transaction.

## Open questions

- Does SE-6 apply to SQLite? The wording says "external dependencies", and SQLite is the only one this project has, but the team should confirm that this is what the reviewers expect.
- How should FastAPI manage connections? The prototype's override used `check_same_thread=False` with a connection per request, and I did not test whether that flag is needed.
- CI runs on Linux, so the Windows timings above will not carry over. Is the file database cost acceptable as the test suite grows?
- No storage code exists yet, so this design still needs a decision under [[SE-3]] before implementation.
