---
id: ledger-reconciliation-algorithms
title: Ledger Reconciliation Algorithms
type: research
author: Member 3
stage: 1
status: active
created: 2026-11-08
source:
  - "Financial_Ledger.pdf, pp. 1-2 (FR-1, FR-5, TQ-3, simulate-transfer)"
  - "Accounting for Developers, Countingup Engineering: https://engineering.countingup.com/accounting-for-developers/"
  - "Local experiments, 2026-11-08: Python 3.12.5, SQLite 3.45.3, on Windows"
related_requirements: [FR-5, FR-1, FR-2, FR-3, FR-4, TQ-1, TQ-3, TQ-6, SE-3]
---

# Ledger Reconciliation Algorithms

## Summary

[[FR-5]] requires an administrative endpoint that verifies total credits equal total debits, and that each wallet's balance matches its ledger entries. Those two checks are necessary, but in testing they missed offsetting errors, mixed currencies and entries for unknown wallets. The queries must also run in a single read transaction: scanning with separate statements during live transfers raised false alarms on 254 of 300 scans.

## Key points

### Required and added checks

Wallet balance is calculated here as credits minus debits, following the liability convention proposed in [[double-entry-bookkeeping-principles]]. The test schema has `ledger(txn, wallet, currency, direction, amount)` and `wallet(id, currency, bal)`.

```sql
-- 1. Required: credits equal debits. Grouped by currency, as sums of different currencies mean nothing.
SELECT currency,
       COALESCE(SUM(CASE WHEN direction = 'credit' THEN amount END), 0) AS c,
       COALESCE(SUM(CASE WHEN direction = 'debit'  THEN amount END), 0) AS d
FROM ledger GROUP BY currency HAVING c <> d;

-- 2. Required: every wallet matches its entries. LEFT JOIN also covers wallets with no entries.
SELECT w.id, w.bal,
       COALESCE(SUM(CASE WHEN l.direction = 'credit' THEN l.amount
                         WHEN l.direction = 'debit'  THEN -l.amount END), 0) AS calc
FROM wallet w LEFT JOIN ledger l ON l.wallet = w.id
GROUP BY w.id, w.bal HAVING w.bal <> calc;

-- 3. Added: every transaction balances by itself.
SELECT txn, currency,
       COALESCE(SUM(CASE WHEN direction = 'credit' THEN amount END), 0) AS c,
       COALESCE(SUM(CASE WHEN direction = 'debit'  THEN amount END), 0) AS d
FROM ledger GROUP BY txn, currency HAVING c <> d;

-- 4. Added: no entry points to an unknown wallet.
SELECT l.id FROM ledger l LEFT JOIN wallet w ON w.id = l.wallet WHERE w.id IS NULL;
```

Each query returns rows only when something is wrong, so an empty result means that check passed.

### What each check catches

I injected each fault into a clean, balanced test ledger. "Global" is the plain `SUM(credits) = SUM(debits)` across the whole table.

| Injected fault | Global | Per currency | Per wallet | Per transaction | Unknown wallet |
| --- | --- | --- | --- | --- | --- |
| Balance overwritten (lost update) | Missed | Missed | **Caught** | Missed | Missed |
| Credit leg missing | **Caught** | **Caught** | **Caught** | **Caught** | Missed |
| Wallet has a balance but no entries | Missed | Missed | **Caught** | Missed | Missed |
| One-sided entries that offset across transactions | Missed | Missed | Missed | **Caught** | Missed |
| Debit in USD against credit in INR, same size | Missed | **Caught** | Missed | **Caught** | Missed |
| Entry for an unknown wallet, otherwise balanced | Missed | Missed | Missed | Missed | **Caught** |
| **Duplicate transfer, balances updated** | Missed | Missed | Missed | Missed | Missed |
| **Overdraft, balances consistent** | Missed | Missed | Missed | Missed | Missed |
| **Balanced edit of amounts and balances** | Missed | Missed | Missed | Missed | Missed |

The last three rows pass every check, because the books still balance. Reconciliation proves consistency, not correctness, so they need their own protection:

- Duplicate transfers: [[idempotent-api-design-patterns]].
- Overdrafts: a separate negative-balance scan caught this one, but also flagged the system funding wallets in the test data, so it must exempt them.
- Balanced edits: the hash chain in [[immutable-audit-trail-and-reversals]].

### Query traps

| Query | Result | Problem |
| --- | --- | --- |
| `SUM(credits) = SUM(debits)` on an empty ledger | `NULL` | A check of `if result:` would report a new system as failing |
| `SUM(amount)` on empty | `NULL` | Needs `COALESCE(SUM(amount), 0)` |
| `TOTAL(amount)` on empty | `0.0` | Returns a float, which [[TQ-6]] rules out for money |
| `SUM` exceeding the 64-bit integer limit | `OperationalError: integer overflow` | The endpoint must handle this rather than crash |

### Consistent snapshots

A writer committed transfers while the reader scanned wallets and then entries, with a 1 ms sleep added between the two queries.

| Reader | False mismatches | Transfers committed during the test |
| --- | ---: | --- |
| Separate statements | **254 of 300** | 881 across both runs |
| One `BEGIN` read transaction in WAL mode | **0 of 300** | |

The sleep makes the failure more frequent than it would otherwise be, but the mismatch is real: the two queries saw different points in time. A real alert from this endpoint is only meaningful if false ones cannot occur.

### Scale

Scanning 500,000 entries and 1,000 wallets on this machine, with indexes on `wallet` and `txn`:

| Check | Time |
| --- | ---: |
| Per currency | 0.98 s |
| Per transaction | 1.68 s |
| Per wallet | 4.06 s |

## Relevance to Coinfidential

These are my recommendations and inferences, based on the results above:

- **Run all four queries in one read transaction,** and never inside `BEGIN IMMEDIATE`, so reconciliation does not hold up transfers.
- **Report rather than repair.** Return the failing rows for each check, so an administrator can investigate. An automatic correction would itself need a reversal under [[FR-4]].
- **Return `200` with a result such as `"balanced": false`,** because the scan itself succeeded, as [[rest-api-error-handling-and-status-codes]] proposes.
- **Test both directions.** Each check needs a [[TQ-1]] test with a clean ledger and one with the matching fault injected, because a check that never fails proves nothing. Injecting a fault means dropping the triggers in that test's database.
- **Check the triggers exist.** A scan of `sqlite_master` can confirm that the append-only triggers are still in place.
- **Use it in the skill.** The `simulate-transfer` skill ends by calling this endpoint, so it benefits directly from these checks.

## Requirements

- [[FR-5]]: This note defines the reconciliation algorithm.
- [[FR-1]]: Distinct currency wallets are the reason to group by currency.
- [[FR-2]]: Reconciliation cannot catch duplicates, so idempotency must prevent them.
- [[FR-3]]: A lost balance update is the fault the per-wallet check catches.
- [[FR-4]]: Reconciliation relies on entries that cannot be changed.
- [[TQ-1]]: Unit tests cover these ledger balance assertions.
- [[TQ-3]]: End-to-end tests must cover [[FR-5]].
- [[TQ-6]]: Reconciliation sums must stay integers, which rules out `TOTAL()`.
- [[SE-3]]: The checks beyond the two that FR-5 requires belong in an ADR.

## Related notes

- [[double-entry-bookkeeping-principles]]: Introduces the rule these queries verify, and the Countingup query that the global check is based on.
- [[idempotent-api-design-patterns]]: Prevents the duplicate transfers this algorithm cannot detect.
- [[immutable-audit-trail-and-reversals]]: Protects the entries this algorithm trusts, and covers tampering it cannot detect.
- [[integer-minor-units-money-math]]: Explains why exact integer sums are required.
- [[rest-api-error-handling-and-status-codes]]: Proposes the response for a mismatch.

Member 2's `race-conditions-and-optimistic-locking` note covers the same lost-update and overdraft faults, but it is on an unmerged branch and is not linked here because the link would fail validation.

## Open questions

- Who may call this endpoint? [[FR-5]] says "administrative", but the brief defines no authentication, so the team needs a decision.
- Should the per-transaction and unknown-wallet checks be part of the [[FR-5]] response? They go beyond its wording, but they caught faults that its two checks missed.
- Should it scan the entire ledger every time? A full scan is simple and took seconds here, but stored checkpoints may be needed at a much larger scale.
- These timings are from one Windows machine with simple test data, so they are not a benchmark.
