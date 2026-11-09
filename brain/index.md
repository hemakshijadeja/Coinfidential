# Coinfidential Second Brain

The catalog of notes for this project. See `AGENTS.md` for the rules and [[log]] for the history of changes.

## Documents

- [Software Requirements Specification](../docs/SRS.md): The Stage 1 SRS, including the FR, NFR and SK requirements, the TQ-7 skill evaluation, the development plan and the traceability matrix. It sits outside this vault, so it uses a Markdown link. Requirements: [[SE-1]], [[SE-4]], [[SE-5]], [[TQ-7]].

## Projects

No notes yet.

## Areas

- [[stage1-ai-session-setup]]: AI session note on the Stage 1 setup, what worked and what failed. Requirements: [[SB-1]], [[SB-3]], [[SB-4]], [[SB-5]].
- [[stage1-review-retrospective]]: Stage 1 review with what worked, what did not, Stage 2 changes, deliverable status and the 4-member task breakdown. Requirements: [[SB-2]], [[SE-4]], [[SB-5]], [[SB-6]], [[SE-1]], [[TQ-7]].

## Resources

- [[double-entry-bookkeeping-principles]]: Debit == credit math, and why preventing the Vanishing Money Glitch also needs idempotency and concurrency controls. Requirements: [[FR-1]], [[FR-2]], [[FR-3]], [[FR-4]], [[FR-5]], [[SE-3]].
- [[integer-minor-units-money-math]]: Why IEEE 754 floats fail for money, and how to store and enforce cents or paise as integers. Requirements: [[TQ-1]], [[TQ-4]], [[TQ-6]], [[FR-5]].
- [[rest-api-error-handling-and-status-codes]]: Status codes and error formats for the API, compared with measured FastAPI defaults. Requirements: [[FR-2]], [[FR-5]], [[TQ-3]], [[TQ-4]], [[SE-3]], [[SE-7]].

- [[idempotent-api-design-patterns]]: `Idempotency-Key` headers, SHA-256 payload hashing, atomic idempotency records and retry status codes. Requirements: [[FR-2]], [[TQ-1]], [[TQ-2]], [[TQ-4]], [[FR-3]], [[SE-3]].
- [[immutable-audit-trail-and-reversals]]: Append-only triggers, the `REPLACE` gap, compensating reversals and tamper evidence. Requirements: [[FR-4]], [[FR-5]], [[TQ-2]], [[TQ-3]], [[TQ-4]], [[SE-3]].
- [[ledger-reconciliation-algorithms]]: Reconciliation queries, which faults each one catches, and why they need one read transaction. Requirements: [[FR-5]], [[FR-1]], [[FR-2]], [[FR-3]], [[FR-4]], [[TQ-1]], [[TQ-3]], [[TQ-6]], [[SE-3]].

- [[sqlite-acid-and-wal-concurrency]]: SQLite ACID behavior, WAL mode, `BEGIN IMMEDIATE` and busy timeouts for safe simultaneous transfers. Requirements: [[FR-3]], [[TQ-2]], [[FR-5]], [[SE-3]].
- [[race-conditions-and-optimistic-locking]]: Measured ToCToU double-spend races, comparing pessimistic locking with optimistic concurrency control. Requirements: [[FR-3]], [[TQ-4]], [[FR-2]], [[FR-5]], [[SE-3]].
- [[provider-interface-isolation]]: A storage interface for SQLite, and when tests need an in-memory or fresh file database. Requirements: [[SE-6]], [[TQ-5]], [[TQ-1]], [[TQ-2]], [[TQ-3]], [[TQ-4]], [[FR-3]], [[SE-3]].

- [[financial-api-security-and-validation]]: Negative amount inversion, strict amount and ID validation, injection, and the security test plan. Requirements: [[TQ-4]], [[TQ-1]], [[TQ-6]], [[FR-2]], [[FR-5]], [[SE-3]].
- [[agent-skills-and-second-brain-architecture]]: The Agent Skills format, the five project skills and their status, and how to evaluate them. Requirements: [[SK-1]], [[SK-2]], [[SK-3]], [[SK-4]], [[SK-5]], [[SB-1]], [[SB-2]], [[SB-3]], [[SB-5]], [[SE-1]], [[TQ-7]], [[FR-1]], [[FR-5]].


## Archive

No notes yet.

## Requirements

Notes link to requirements by ID. The [SRS](../docs/SRS.md) defines them, using the course PDFs, which are not stored in this repository.

- Functional: [[FR-1]], [[FR-2]], [[FR-3]], [[FR-4]], [[FR-5]]
- Software engineering: [[SE-1]], [[SE-2]], [[SE-3]], [[SE-4]], [[SE-5]], [[SE-6]], [[SE-7]]
- Repository foundation: [[SB-4]] (`AGENTS.md`)
- Other series, linked as they are used: `NFR-<n>`, `SK-<n>`, `TQ-<n>`, `SB-<n>`
