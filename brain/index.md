# Coinfidential Second Brain

The catalog of notes for this project. See `AGENTS.md` for the rules and [[log]] for the history of changes.

## Projects

No notes yet.

## Areas

- [[stage1-ai-session-setup]]: AI session note on the Stage 1 setup, what worked and what failed. Requirements: [[SB-1]], [[SB-3]], [[SB-4]], [[SB-5]].
- [[stage1-review-retrospective]]: Draft Stage 1 review note, with deliverable status. Requirements: [[SB-2]], [[SB-6]], [[SE-1]], [[TQ-7]].

## Resources

- [[double-entry-bookkeeping-principles]]: Debit == credit math, and why preventing the Vanishing Money Glitch also needs idempotency and concurrency controls. Requirements: [[FR-1]], [[FR-2]], [[FR-3]], [[FR-4]], [[FR-5]].
- [[integer-minor-units-money-math]]: Why IEEE 754 floats fail for money, and how to store and enforce cents or paise as integers. Requirements: [[TQ-1]], [[TQ-4]], [[TQ-6]], [[FR-5]].
- [[rest-api-error-handling-and-status-codes]]: Status codes and error formats for the API, compared with measured FastAPI defaults. Requirements: [[FR-2]], [[FR-5]], [[TQ-3]], [[TQ-4]], [[SE-3]], [[SE-7]].
- [[sqlite-acid-and-wal-concurrency]]: SQLite ACID behavior, WAL mode, `BEGIN IMMEDIATE` and busy timeouts for safe simultaneous transfers. Requirements: [[FR-3]], [[TQ-2]], [[FR-5]], [[SE-3]].
- [[race-conditions-and-optimistic-locking]]: Measured ToCToU double-spend races, comparing pessimistic locking with optimistic concurrency control. Requirements: [[FR-3]], [[TQ-4]], [[FR-2]], [[FR-5]], [[SE-3]].
- [[provider-interface-isolation]]: A storage interface for SQLite, and when tests need an in-memory or fresh file database. Requirements: [[SE-6]], [[TQ-5]], [[TQ-1]], [[TQ-2]], [[TQ-3]], [[TQ-4]], [[FR-3]], [[SE-3]].

## Archive

No notes yet.

## Requirements

Notes link to requirements by ID. The requirements document is not stored in this repository, so its definitions are not repeated here.

- Functional: [[FR-1]], [[FR-2]], [[FR-3]], [[FR-4]], [[FR-5]]
- Software engineering: [[SE-1]], [[SE-2]], [[SE-3]], [[SE-4]], [[SE-5]], [[SE-6]], [[SE-7]]
- Repository foundation: [[SB-4]] (`AGENTS.md`)
- Other series, linked as they are used: `NFR-<n>`, `SK-<n>`, `TQ-<n>`, `SB-<n>`
