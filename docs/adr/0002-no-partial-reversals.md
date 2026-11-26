# ADR-0002: No partial reversals

- **Date:** 2026-11-26
- **Author:** Subhadeep
- **Requirements:** FR-4, FR-5, TQ-3, TQ-4

## Status

Proposed

## Context

FR-4 says the ledger can't be edited, so a mistake is fixed by adding a reversal that moves the money back. The SRS leaves open whether a reversal can move back only part of a transfer, for example 40 out of 100 (OD-9, Appendix C). We need to decide before building reversals in Stage 2.

Things we already know:

- FR-4.2 says each transfer can be reversed at most once.
- In testing, a full reversal posts the same entries with debit and credit swapped, and both balances go back to where they started. Debits still equal credits ([[immutable-audit-trail-and-reversals]]).
- A `reverses INTEGER UNIQUE` column stopped a second reversal of the same transfer. The same note points out that this also rules out partial reversals, because you would need more than one reversal per transfer to give all the money back in parts.
- OD-8 already says a reversal is rejected if the recipient has spent the money.

## Decision

We will **not** allow partial reversals. A reversal always moves back the full amount of the original transfer, and a transfer can only be reversed once. If someone needs to give back only part of the money, they make a normal new transfer for that amount. (my suggestion)

## Consequences

Good:

- It matches FR-4.2 and lets us use the `UNIQUE(reverses)` column from the research note, so the database itself blocks a second reversal.
- A reversal is just the original entries flipped, so it is always balanced and easy to check in reconciliation ([[ledger-reconciliation-algorithms]]).
- Fewer cases to test: no tracking of "how much is left to reverse".

Bad:

- A partial refund shows up as a normal transfer, not as a reversal linked to the original, so it is harder to see why it happened.
- If a later stage needs partial reversals, we would have to drop the `UNIQUE` rule and track the remaining amount, which needs a new ADR.

## Brain notes cited

- [[immutable-audit-trail-and-reversals]]: Shows how full reversals work and stay balanced, and notes that `UNIQUE(reverses)` blocks partial reversals.
- [[ledger-reconciliation-algorithms]]: Reversals must keep the ledger check balanced, which full reversals do.
