---
id: integer-minor-units-money-math
title: Integer Minor Units for Money Math
type: research
author: Member 1
stage: 1
status: active
created: 2026-11-08
source:
  - "Financial_Ledger.pdf, p. 2 (TQ-1, TQ-4, TQ-6)"
  - "Floating-Point Numbers, SQLite: https://sqlite.org/floatingpoint.html"
  - "Datatypes in SQLite: https://sqlite.org/datatype3.html"
  - "Floating-Point Arithmetic: Issues and Limitations, Python Tutorial: https://docs.python.org/3/tutorial/floatingpoint.html"
  - "Local experiments, 2026-11-08: Python 3.12.5, SQLite 3.45.3, Pydantic 2.14.3"
related_requirements: [TQ-1, TQ-4, TQ-6, FR-5]
---

# Integer Minor Units for Money Math

## Summary

IEEE 754 binary floats cannot represent most decimal fractions exactly, so float balances pick up errors that break exact accounting checks. TQ-6 requires the system to prevent these errors by using integer minor units or exact decimal types. Storing amounts as whole cents or paise in SQLite integers avoids the problem and needs no extension.

## Key points

- **Why floats fail:** binary floats store a 53-bit fraction, and most decimal fractions repeat forever in binary. The stored value of `0.1` is really `0.10000000000000000555`.
- **SQLite has the same limit:** `REAL` values use IEEE 754 binary-64. The SQLite documentation says: "If you need an exact answer, you should not use binary-64 floating-point values, in SQLite or in any other product."
- **Integer range:** SQLite integers are signed and up to 8 bytes, so the maximum is 9,223,372,036,854,775,807 minor units. Floats lose whole-number accuracy above 2^53: `9007199254740993` becomes `9007199254740992.0`.

### Measured results

| Operation | Float | Integer minor units |
| --- | --- | --- |
| Add 0.1 ten times in a loop | `0.9999999999999999` | `100` (exact) |
| Add 0.01 a million times in a loop | `10000.000000171856` | `1000000` (exact) |
| SQLite `UPDATE`, adding 0.1 ten times | `0.9999999999999999` | `100` (exact) |
| `0.1 + 0.2` | `0.30000000000000004` | `30` (exact) |
| `round(2.675, 2)` | `2.67` | Not applicable |

### Tests can hide the error

- Python's `sum([0.1] * 10)` returned exactly `1.0`, because `sum()` reduces accumulated error. The Python tutorial documents this behavior.
- SQLite's `SUM()` over ten `REAL` values of `0.1` also returned `1.0` in this run.
- The repeated `UPDATE` above still drifted, so a test built only on `sum()` or `SUM()` can pass while real balance updates are wrong.

### Integers need enforcing

| Input | Plain `INTEGER` column | `STRICT` table | Pydantic `int` | Pydantic `StrictInt` |
| --- | --- | --- | --- | --- |
| `10.5` | Stored as `real` | Rejected | Rejected | Rejected |
| `10.0` | Not tested | Stored as `10` | Accepted as `10` | Rejected |
| `"10"` | Not tested | Not tested | Accepted as `10` | Rejected |
| `-5` | Not tested | Not tested | Accepted | Accepted |

## Relevance to Coinfidential

These are my recommendations, based on the results above:

- **Use integers rather than exact decimals.** TQ-6 allows either. The SQLite decimal extension stores numbers as text, which adds work to every sum, and FR-5 needs to sum ledger entries often.
- **Create ledger tables as `STRICT`.** A plain `INTEGER` column will silently store a fractional value.
- **Use `StrictInt` with a positive constraint for API amounts.** `StrictInt` still accepts `-5`, so it does not meet the negative-amount requirement by itself.
- **Test the update path for TQ-6.** Run repeated balance updates through the real code, and assert that fractional, string and negative amounts are rejected.

## Requirements

- [[TQ-6]]: Monetary amounts must be strictly handled as integer minor units or exact decimals.
- [[TQ-1]]: Accounting unit tests need exact equality, which integers allow.
- [[TQ-4]]: The negative tests should cover the invalid amounts in the table above.
- [[FR-5]]: Reconciliation compares sums for exact equality, which float drift would break.

## Related notes

- [[double-entry-bookkeeping-principles]]: The debit == credit rule depends on exact amounts.
- [[stage1-ai-session-setup]]: Records the session that produced this note, including the first demo that hid the error.

## Open questions

- Which currencies will wallets support? FR-1 requires distinct currency wallets, and minor units differ by currency. The ISO 4217 examples I know of are 0 decimals for JPY and 3 for KWD, but I did not check this against a source in this session.
- Should the API send amounts as integer minor units only? This looks simplest, but it needs a decision in the API design.
- What is the maximum transfer amount? A limit would keep balances well below the SQLite integer maximum.
- Results come from one machine. SQLite `SUM()` behavior may differ in other versions, so the tests should not depend on it.
