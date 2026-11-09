---
id: double-entry-bookkeeping-principles
title: Double-Entry Bookkeeping Principles
type: research
author: Member 1
stage: 1
status: active
created: 2026-11-08
source:
  - "Financial_Ledger.pdf, pp. 1-2 (project statement)"
  - "Accounting for Developers, Countingup Engineering: https://engineering.countingup.com/accounting-for-developers/"
  - "How Not to Build a Ledger, Clément Salaün, Formance: https://dev.to/formance/how-not-to-build-a-ledger-cfg"
related_requirements: [FR-1, FR-2, FR-3, FR-4, FR-5, SE-3]
---

# Double-Entry Bookkeeping Principles

## Summary

Double-entry bookkeeping records every transaction as equal debits and credits, so a single entry cannot create or destroy money. The project brief makes this the basis of every wallet balance and requires an endpoint that proves the books still balance. Double-entry alone does not stop the Vanishing Money Glitch, because the brief's two causes are overwritten balances and retried requests.

## Key points

- **Core rule:** within each transaction, total debits equal total credits. Across the whole ledger, this means `SUM(debits) = SUM(credits)`.
- **Debit and credit are not plus and minus:** their effect depends on the account type. Debits increase assets and decrease liabilities, and credits do the reverse.
- **Worked example:** a transfer of 500 paise from wallet A to wallet B writes two entries in one transaction:

  | Entry | Debit | Credit |
  | --- | ---: | ---: |
  | Wallet A | 500 | |
  | Wallet B | | 500 |
  | **Total** | **500** | **500** |

- **Why a balance column is not enough:** Salaün notes that a mutable balance can be overwritten without a trace, so errors surface only at reconciliation and cannot be traced to a cause.
- **Balances come from entries:** Countingup computes balances by summing entries, and suggests a cached running balance or checkpoints because recalculating everything is slow.
- **Reconciliation query:** Countingup checks the ledger with `SELECT SUM(credits) = SUM(debits) FROM ledger_entries`, both overall and per transaction.

### The Vanishing Money Glitch

The brief names two causes: balance updates overwriting each other during simultaneous requests, and a network retry triggering a duplicate charge.

| Failure | Does balanced double-entry stop it? | Control |
| --- | --- | --- |
| Entry with no matching opposite entry | Yes | Debit == credit check, [[FR-1]] |
| Two requests overwrite the same balance | No | Serialized transactions, [[FR-3]] |
| A retry applies the same transfer twice | No | Idempotency key, [[FR-2]] |
| Past entries are edited or deleted | No | Append-only ledger with reversals, [[FR-4]] |
| Stored balance drifts from the entries | Detects it, does not prevent it | Reconciliation, [[FR-5]] |

## Relevance to Coinfidential

These are my inferences, not statements from the sources:

- **A duplicate transfer passes the debit == credit check.** Each copy is perfectly balanced, so `SUM(debits) = SUM(credits)` still holds. Reconciliation cannot catch this, so the idempotency check has to stop it before it is written.
- **FR-5 needs two separate checks.** One compares credits with debits. The other compares each wallet's stored balance with its ledger sum. A lost balance update fails only the second check.
- **Treat wallets as liabilities.** Wallet funds are money the platform owes its users, so a credit would increase a wallet balance. The brief does not prescribe this convention, so it needs a decision.
- **Write entries and the balance update in one transaction.** Otherwise a crash between them creates the drift that FR-5 is meant to find.

## Requirements

- [[FR-1]]: Every wallet balance is backed by ledger entries, and every credit equals a debit.
- [[FR-5]]: The reconciliation endpoint verifies credits equal debits and that wallet balances match ledger sums.
- [[FR-2]]: Prevents the duplicate-charge half of the glitch, which double-entry cannot detect.
- [[FR-3]]: Prevents the overwritten-balance half of the glitch.
- [[FR-4]]: Keeps the entries trustworthy by making corrections explicit reversal transactions.

## Related notes

- [[integer-minor-units-money-math]]: The debit == credit check needs exact amounts, which integers provide.
- [[stage1-ai-session-setup]]: Records the session that produced this note.

## Open questions

- How does a new wallet get its initial balance? The `simulate-transfer` skill records initial balances, but the brief does not say where that money comes from. A balanced entry needs an opposite account, such as a system funding account.
- Should wallets be recorded as liabilities? This needs an ADR under [[SE-3]].
- Should the ledger store separate debit and credit columns, or one column with a direction? The Countingup query assumes separate columns.
- The two web sources are practitioner articles, not accounting textbooks. Is a stronger citation needed for the SRS?
