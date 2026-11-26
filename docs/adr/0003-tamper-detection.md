# ADR-0003: Tamper detection with a hash chain

- **Date:** 2026-11-26
- **Author:** Hardh
- **Requirements:** FR-4, FR-5, NFR-4, TQ-3, TQ-4

## Status

Proposed

## Context

FR-4.3 says the ledger must be tamper-evident, so any change to a past record has to be detectable. FR-5.4 says the reconciliation check should also confirm that no record has been tampered with. The SRS leaves open how this will work (OD-11, Appendix C).

Things we already know:

- Triggers can block `UPDATE` and `DELETE`, but in testing `INSERT OR REPLACE` still rewrote a row unless `PRAGMA recursive_triggers=ON` was set on that connection. Anyone with database access can also just drop the triggers ([[immutable-audit-trail-and-reversals]]).
- Reconciliation proves the books balance, not that they are correct. An edit that changes both legs of a transfer by the same amount passes every reconciliation query ([[ledger-reconciliation-algorithms]]).
- In testing, a hash chain (each entry stores the SHA-256 of the previous entry's hash plus its own fields) caught exactly that balanced edit. It did not catch someone who rewrote the whole chain afterwards ([[immutable-audit-trail-and-reversals]]).

## Decision

We will add a hash chain to the ledger. Each new entry stores `hash = SHA-256(previous hash + its own fields)`, and the first entry uses a fixed starting value. The reconciliation check (FR-5) will recompute the chain and report the first entry where it breaks. It will also check that the append-only triggers still exist.

We will keep the triggers and `PRAGMA recursive_triggers=ON` as the first line of defence, and treat the hash chain as the way to detect anything that gets past them.

We will not store the latest hash outside the database in Stage 2. (my suggestion)

## Consequences

Good:

- It catches balanced edits, which reconciliation alone misses ([[ledger-reconciliation-algorithms]]).
- It fits into the reconciliation check we already have to build, so there is no new endpoint.
- It is easy to test: change a row with the triggers dropped, then check that reconciliation reports it.

Bad:

- Each entry needs the previous entry's hash, so ledger writes must be serialized. We already plan to use `BEGIN IMMEDIATE` for transfers, so this should not cost much ([[sqlite-acid-and-wal-concurrency]]).
- It adds a column and makes the check slower, because it has to read every entry in order.
- Someone who can rewrite the whole table can also recompute the chain. Catching that would mean saving the latest hash somewhere outside the database, which would need a new ADR.

## Brain notes cited

- [[immutable-audit-trail-and-reversals]]: Shows the limits of triggers, the `REPLACE` gap, and the hash chain test results.
- [[ledger-reconciliation-algorithms]]: Shows that a balanced edit passes every reconciliation query, so we need something extra.
- [[sqlite-acid-and-wal-concurrency]]: `BEGIN IMMEDIATE` serializes writers, which the chain needs.
