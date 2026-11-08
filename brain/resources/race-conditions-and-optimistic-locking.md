---
id: race-conditions-and-optimistic-locking
title: Race Conditions and Optimistic Locking
type: research
author: Member 2
stage: 1
status: active
created: 2026-11-08
source:
  - "Financial_Ledger.pdf, pp. 1-2 (Vanishing Money Glitch, FR-3, TQ-4)"
  - "CWE-367, TOCTOU Race Condition, MITRE: https://cwe.mitre.org/data/definitions/367.html"
  - "Optimistic Offline Lock, Martin Fowler: https://martinfowler.com/eaaCatalog/optimisticOfflineLock.html"
  - "Transaction, SQLite: https://sqlite.org/lang_transaction.html"
  - "Isolation In SQLite: https://sqlite.org/isolation.html"
  - "Local experiments, 2026-11-08: Python 3.12.5, SQLite 3.45.3, on Windows"
related_requirements: [FR-3, TQ-4, FR-2, FR-5, SE-3]
---

# Race Conditions and Optimistic Locking

## Summary

A Time-of-Check to Time-of-Use (ToCToU) race happens when a balance is checked and then spent, but it changes in between. In the experiments, this let 8 concurrent requests all spend the same 100. `BEGIN IMMEDIATE`, optimistic version checks and a guarded `UPDATE` all paid exactly once, and I recommend `BEGIN IMMEDIATE` for Coinfidential because SQLite allows only one writer anyway.

## Key points

- **Definition:** CWE-367 describes a product that checks the state of a resource before using it, where the state can change before the use and so invalidate the check.
- **In a wallet:** two requests both read a balance of 100, both pass the "enough funds" check, and both spend it.
- **Pessimistic locking** takes the lock before reading. In SQLite that is `BEGIN IMMEDIATE`, which holds the only write slot through the check and the writes.
- **Optimistic concurrency control** reads without a lock, then detects conflicts at write time. Fowler defines it as preventing conflicts "by detecting a conflict and rolling back the transaction". Here, that means `UPDATE ... WHERE version = ?`, and an affected row count of 0 means another request got there first.

### Measured results

In each trial, 8 threads tried to spend 100 from a balance of 100, with WAL on and a 10-second busy timeout. I added a 20 ms sleep between the check and the write to widen the race window, so these results show that the bug is possible, not how often it would occur in production. All 5 trials matched for each strategy, apart from the noted variation in `BEGIN` deferred.

| Strategy | Final balance | Ledger entries | Outcome |
| --- | ---: | ---: | --- |
| Separate check, then `bal = bal - 100` | **-700** | 8 | All 8 paid |
| Separate check, then `bal = <value read - 100>` | 0 | **8** | All 8 paid: 800 spent, 100 deducted |
| `BEGIN` deferred | 0 | 1 | 1 paid, the other 7 mostly `database is locked` |
| `BEGIN IMMEDIATE` | 0 | 1 | 1 paid, 7 cleanly rejected |
| Optimistic version check | 0 | 1 | 1 paid, 7 rejected, 35 retries in total |
| Guarded `UPDATE ... WHERE bal >= 100` | 0 | 1 | 1 paid, 7 cleanly rejected |

WAL was on for every row, including the two that failed. WAL alone does not prevent this race.

### Comparison under valid load

Here, 8 threads each spent 10 from a balance of 100, so every request should succeed. All strategies ended correctly at 20.

| | `BEGIN IMMEDIATE` | Optimistic version check |
| --- | --- | --- |
| Conflicts per trial, 3 trials | 0, 0, 0 | 17, 24, 22 |
| Trial duration | 0.44 to 0.55 s | 0.35 to 1.73 s |

The timings include database setup and the artificial 20 ms sleep, so they are not a benchmark. The conflict counts are the more useful result.

### Trade-offs

| | Pessimistic (`BEGIN IMMEDIATE`) | Optimistic (version column) |
| --- | --- | --- |
| Conflict handling | Writers wait | The loser retries, or fails |
| Extra code | Transaction wrapper | Version column and retry loop, with a retry limit |
| Failure mode | `SQLITE_BUSY` after the timeout | Retries used up, or conflicts under load |
| Lock held during checks | Yes, so keep it short | No |

## Relevance to Coinfidential

These are my recommendations and inferences, not statements from the sources:

- **Use `BEGIN IMMEDIATE` for transfers.** Optimistic locking usually pays off when it avoids holding locks in a system with many parallel writers. SQLite has only one writer, so the optimistic write still has to take that slot, and every conflict adds a retry on top.
- **A guarded `UPDATE` is a useful addition,** because it makes the balance rule part of the write. A `CHECK (balance >= 0)` constraint could add a final safeguard, but I did not test one here.
- **Deferred transactions are safe but noisy.** They never overspent in these trials, but valid requests got raw lock errors instead of a clean result.
- **Reconciliation cannot be the only defense.** The `-700` row is internally consistent, with 8 entries and matching deductions, so an [[FR-5]] sum check could pass on an overdrawn wallet. The other failing row, with 8 entries but only 100 deducted, is the lost update that FR-5's balance check should catch. This is the "Vanishing Money Glitch" from the brief.
- **Prove race safety with real threads.** A [[TQ-4]] test should use a barrier to release the requests together, separate connections and a file database. Assert one success, the final balance and the entry count. This test only proves something if it fails against the unprotected code, so check it against that version once.

## Requirements

- [[FR-3]]: This note compares the ways to handle simultaneous requests on one wallet without races.
- [[TQ-4]]: Requires negative tests for simultaneous transfers that prove race safety.
- [[FR-5]]: Reconciliation catches some outcomes of these races, but not all.
- [[SE-3]]: The locking choice belongs in an ADR.

## Related notes

- [[sqlite-acid-and-wal-concurrency]]: Explains the SQLite behavior behind these results.
- [[provider-interface-isolation]]: Explains how to test this with a file database in CI.
- [[double-entry-bookkeeping-principles]]: Covers the other half of the glitch, including duplicate retries.
- [[rest-api-error-handling-and-status-codes]]: Lists the proposed status code for insufficient funds.

## Open questions

- What should the API return when the busy timeout expires? `503` with a retry hint seems reasonable, but I have not checked it against a source, and it needs adding to the error table.
- How does a retry interact with the [[FR-2]] idempotency key after a timeout? The key check needs to be inside the same transaction, and this needs its own test.
- Should the transfer use a guarded `UPDATE`, a `SELECT` check inside the transaction, or both?
- Would the race reproduce without the 20 ms sleep? I did not test this, so the real-world frequency is unknown.
