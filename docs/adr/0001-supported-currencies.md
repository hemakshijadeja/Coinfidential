# ADR-0001: Supported currencies

- **Date:** 2026-11-26
- **Author:** Hemakshi
- **Requirements:** FR-1, FR-5, TQ-6

## Status

Proposed

## Context

FR-1 says each account can have wallets in different currencies, but the SRS leaves open which currencies we actually support (OD-4, Appendix C). We have to pick before we build wallets in Stage 2.

Things we already know:

- All money is stored as whole numbers of the smallest unit, like paise or cents ([[integer-minor-units-money-math]]).
- Not every currency has 2 decimal places. The same note says JPY has 0 and KWD has 3, but this was not checked against a source. If we allow currencies like these, we have to track decimals per currency.
- Currency conversion is out of scope, and a transfer stays in one currency (BR-3).
- Each currency needs its own system account to fund new wallets (OD-3, FR-1.2).
- The ledger check adds up credits and debits for each currency separately. In testing, a USD debit against an INR credit of the same size was only caught by the per-currency and per-transaction checks, not the global one ([[ledger-reconciliation-algorithms]]).

## Decision

We will support two currencies, **INR and USD**, both stored in minor units with 2 decimal places (paise and cents). The list is fixed in the code, and any other currency code is rejected. (my suggestion)

## Consequences

Good:

- Both currencies use 2 decimal places, so we do not need per-currency decimal handling yet.
- INR and USD are already used in the SRS examples (FR-1 acceptance criterion 1), so the tests match the SRS.
- Only two system accounts, so the per-currency ledger check is easy to test.

Bad:

- Users cannot open wallets in other currencies.
- Adding a currency with 0 or 3 decimals later means changing how amounts are validated and shown, so it would need a new ADR.

## Brain notes cited

- [[integer-minor-units-money-math]]: Money is stored as integer minor units, and its open question says minor units differ by currency.
- [[ledger-reconciliation-algorithms]]: The ledger check groups by currency, and testing showed this catches mixed-currency entries.
