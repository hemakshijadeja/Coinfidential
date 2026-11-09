---
id: immutable-audit-trail-and-reversals
title: Immutable Audit Trail and Reversals
type: research
author: Member 3
stage: 1
status: active
created: 2026-11-08
source:
  - "Financial_Ledger.pdf, pp. 1-2 (tamper-evident ledger, FR-4, TQ-4)"
  - "CREATE TRIGGER, SQLite: https://sqlite.org/lang_createtrigger.html"
  - "ON CONFLICT clause, SQLite: https://sqlite.org/lang_conflict.html"
  - "Local experiments, 2026-11-08: Python 3.12.5, SQLite 3.45.3, on Windows"
related_requirements: [FR-4, FR-5, TQ-2, TQ-3, TQ-4, SE-3]
---

# Immutable Audit Trail and Reversals

## Summary

[[FR-4]] says ledger records cannot be updated or deleted, and that corrections must be explicit reversal transactions. SQLite triggers can enforce this, but in testing the obvious triggers did not stop `INSERT OR REPLACE`, which rewrote a ledger row without any error. Triggers also do not make the ledger tamper-evident, as the brief requires, because anyone with database access can drop them.

## Key points

### Blocking changes with triggers

```sql
CREATE TRIGGER ledger_no_update BEFORE UPDATE ON ledger
BEGIN SELECT RAISE(ABORT, 'ledger is append-only'); END;

CREATE TRIGGER ledger_no_delete BEFORE DELETE ON ledger
BEGIN SELECT RAISE(ABORT, 'ledger is append-only'); END;
```

SQLite's documentation warns that a `BEFORE` trigger which changes the row being updated gives undefined results, and generally prefers `AFTER` triggers. These triggers only raise an error and change nothing.

| Statement against the ledger | Result with both triggers |
| --- | --- |
| `UPDATE`, `DELETE` of one row, `DELETE` of all rows | Blocked |
| `UPDATE OR REPLACE`, upsert with `DO UPDATE` | Blocked |
| Parent row deleted with `ON DELETE CASCADE` | Blocked |
| `INSERT OR IGNORE` on an existing row | Accepted, row unchanged |
| **`INSERT OR REPLACE`, `REPLACE INTO`** | **Accepted, row rewritten** |
| **Plain `INSERT` on a column with `ON CONFLICT REPLACE`** | **Accepted, row rewritten** |
| **`DROP TRIGGER`, `DROP TABLE`** | **Accepted** |

### The `REPLACE` gap

SQLite's documentation says `REPLACE` fires delete triggers "if and only if recursive triggers are enabled". That setting was `0` by default in this build.

| Defense | `REPLACE` through `id` | `REPLACE` through another `UNIQUE` column |
| --- | --- | --- |
| Update and delete triggers only | Rewritten | Rewritten |
| Add a `BEFORE INSERT` trigger that checks `id` | Blocked | **Rewritten** |
| `PRAGMA recursive_triggers=ON` | Blocked | Blocked |

`PRAGMA recursive_triggers=ON` also blocked the `ON CONFLICT REPLACE` case, and normal inserts still worked. It is **per connection**: a new connection to the same file reported `0`, so one connection opened without it can still rewrite history.

### How a blocked statement behaves

The error was `sqlite3.IntegrityError`, with the name `SQLITE_CONSTRAINT_TRIGGER`. `RAISE(ABORT, ...)` cancels only that statement and leaves the transaction open. In testing, an earlier insert in the same transaction survived the error until an explicit `ROLLBACK`, so the error handler must roll back.

### Reversals

A reversal posts new entries with debit and credit swapped, and references the original. Original rows stay in place.

| Step | Wallet A | Wallet B | Entries | Debits == credits |
| --- | ---: | ---: | ---: | --- |
| Start | 1000 | 0 | 0 | Not applicable |
| Transfer 100 from A to B | 900 | 100 | 2 | Yes |
| Reverse it | 1000 | 0 | 4 | Yes |

A `reverses INTEGER UNIQUE REFERENCES ledger(id)` column blocked a second reversal of the same entries, with no change to the balances. Two problems remained:

| Case | Result |
| --- | --- |
| B already spent the money, then the transfer is reversed | Accepted, and **B's balance became -100** |
| Reversing the reversal entries | Accepted, and the original transfer took effect again |

### Tamper evidence

The brief describes a "tamper-evident" ledger, but [[FR-4]] itself only requires that records cannot be changed. I prototyped a hash chain, where each entry stores the SHA-256 of the previous entry's hash plus its own fields.

| Tampering | Debits == credits check | Hash chain check |
| --- | --- | --- |
| Trigger dropped, then both legs of a transfer edited to 900 | Passes | **Broken at entry 1** |
| Same edit, then the whole chain recomputed | Passes | **Passes** |

A chain detects edits, but not someone who can rewrite the whole table. Catching that requires storing the latest hash somewhere outside the database.

## Relevance to Coinfidential

These are my recommendations and inferences, based on the results above:

- **Enable `PRAGMA recursive_triggers=ON` on every connection,** alongside the other per-connection settings, and add a test that checks it on a connection from the application's own connection code.
- **Never use `REPLACE` on the ledger,** and do not declare `ON CONFLICT REPLACE` on its columns.
- **Avoid `ON DELETE CASCADE` from wallets to ledger entries.** The trigger blocked it in testing, but the schema should not suggest that deleting a wallet is a valid action.
- **Use a shared posting function for reversals,** so they get the same transaction, balance checks and idempotency as transfers. See [[idempotent-api-design-patterns]].
- **Treat triggers as protection against bugs, not attackers.** A database administrator can drop them, so reconciliation should confirm that they still exist.
- **Add a hash chain if the team wants to claim "tamper-evident".** It adds a column and a verification step, and needs serialized writes so that each entry knows its predecessor.

## Requirements

- [[FR-4]]: This note covers how to enforce an append-only ledger and explicit reversals.
- [[FR-5]]: Reversals must keep reconciliation balanced, which they did in testing.
- [[TQ-2]]: Tests should confirm the rollback after a blocked statement.
- [[TQ-3]]: End-to-end tests must cover a reversal for [[FR-4]].
- [[TQ-4]]: Negative tests should include every statement in the first table, including `REPLACE`.
- [[SE-3]]: The trigger and tamper-evidence choices belong in an ADR.

## Related notes

- [[double-entry-bookkeeping-principles]]: A reversal is a balanced transaction like any other.
- [[idempotent-api-design-patterns]]: A retried reversal must not apply twice.
- [[ledger-reconciliation-algorithms]]: Shows which tampering reconciliation can and cannot detect.
- [[rest-api-error-handling-and-status-codes]]: Needs a defined response for reversal errors.

Member 2's `provider-interface-isolation` note covers the connection code where these settings belong, but it is on an unmerged branch and is not linked here because the link would fail validation.

## Open questions

- Should a reversal be rejected if the recipient has already spent the money, or be allowed to overdraw? [[TQ-4]] requires tests for negative balance attempts, so I would reject it, but support cases may need another route.
- Should reversals of reversals be blocked? Blocking needs a check that the target entry has no `reverses` value.
- Are partial reversals needed? `UNIQUE(reverses)` allows only one reversal per entry, so it would prevent them.
- Does the rubric expect a hash chain? The brief says "tamper-evident", but no FR or TQ mentions one, so the team should confirm.
- Adopted in the SRS: the owner of the original source wallet, or an admin, may request a reversal. The brief does not say, so this needs an ADR.
