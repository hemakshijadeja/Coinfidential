# Second Brain Log

Append-only record of changes to the brain, oldest first. Do not edit past entries. See [[index]] for the catalog of notes.

## [2026-11-08] init | Second Brain created

- Created the PARA folders, [[index]] and this log.
- Notes added: none.

## [2026-11-08] ingest | Member 1 Stage 1 research and AI session notes

- Source: Financial_Ledger.pdf, SDLC_and_Workflow.pdf, SQLite and Python documentation, Countingup and Formance articles, local experiments, and the Stage 1 Claude Code session
- Notes added: [[double-entry-bookkeeping-principles]], [[integer-minor-units-money-math]], [[stage1-ai-session-setup]]
- Notes updated: [[index]]
- Requirements linked: [[FR-1]], [[FR-2]], [[FR-3]], [[FR-4]], [[FR-5]], [[TQ-1]], [[TQ-4]], [[TQ-6]], [[SB-1]], [[SB-2]], [[SB-3]], [[SB-4]], [[SB-5]], [[SE-3]]

## [2026-11-08] ingest | Member 1 REST research note, Stage 1 review draft and schema migration

- Source: RFC 9110, RFC 9457, IETF Idempotency-Key draft-08, FastAPI documentation, Financial_Ledger.pdf, SDLC_and_Workflow.pdf and local experiments
- Notes added: [[rest-api-error-handling-and-status-codes]], [[stage1-review-retrospective]]
- Notes updated: [[index]], [[double-entry-bookkeeping-principles]], [[integer-minor-units-money-math]], [[stage1-ai-session-setup]]
- Requirements linked: [[FR-2]], [[FR-5]], [[TQ-3]], [[TQ-4]], [[TQ-7]], [[SE-1]], [[SE-3]], [[SE-7]], [[SB-2]], [[SB-6]]


## [2026-11-08] ingest | Member 3 idempotency, audit trail and reconciliation research notes

- Source: Financial_Ledger.pdf, IETF Idempotency-Key draft-08, Stripe API documentation, RFC 8785, Python hashlib documentation, SQLite documentation, Countingup article and local experiments
- Notes added: [[idempotent-api-design-patterns]], [[immutable-audit-trail-and-reversals]], [[ledger-reconciliation-algorithms]]
- Notes updated: [[index]]
- Requirements linked: [[FR-1]], [[FR-2]], [[FR-3]], [[FR-4]], [[FR-5]], [[TQ-1]], [[TQ-2]], [[TQ-3]], [[TQ-4]], [[TQ-6]], [[SE-3]]

## [2026-11-08] ingest | Member 2 concurrency and storage research notes

- Source: Financial_Ledger.pdf, SDLC_and_Workflow.pdf, SQLite documentation, Python sqlite3 documentation, CWE-367, Martin Fowler's pattern catalog, FastAPI and pytest documentation, and local experiments
- Notes added: [[sqlite-acid-and-wal-concurrency]], [[race-conditions-and-optimistic-locking]], [[provider-interface-isolation]]
- Notes updated: [[index]]
- Requirements linked: [[FR-3]], [[FR-5]], [[TQ-1]], [[TQ-2]], [[TQ-3]], [[TQ-4]], [[TQ-5]], [[SE-3]], [[SE-6]], [[FR-2]]

## [2026-11-09] ingest | Member 4 security and skills research notes, and Stage 1 review completed

- Source: Financial_Ledger.pdf, SDLC_and_Workflow.pdf, OWASP Input Validation Cheat Sheet, OWASP API Security Top 10 2023, Pydantic documentation, Python sqlite3 documentation, Agent Skills documentation, skills-ref 0.1.1, Git history, GitHub public API and local experiments
- Notes added: [[financial-api-security-and-validation]], [[agent-skills-and-second-brain-architecture]]
- Notes updated: [[index]], [[stage1-review-retrospective]]
- Requirements linked: [[TQ-1]], [[TQ-4]], [[TQ-6]], [[TQ-7]], [[FR-1]], [[FR-2]], [[FR-5]], [[SK-1]], [[SK-2]], [[SK-3]], [[SK-4]], [[SK-5]], [[SB-1]], [[SB-2]], [[SB-3]], [[SB-4]], [[SB-5]], [[SB-6]], [[SE-1]], [[SE-2]], [[SE-3]], [[SE-4]], [[SE-5]]

## [2026-11-09] srs | Stage 1 SRS and brain-ingest skill evaluation

- Source: Financial_Ledger.pdf, SDLC_and_Workflow.pdf, all research notes, Git history, GitHub public API and `scripts/evaluate_brain_ingest.py`
- Document added: [SRS](../docs/SRS.md), which also defines NFR-1 to NFR-8 and SK-1 to SK-5
- Notes added: none
- Notes updated: [[index]], [[stage1-review-retrospective]], [[agent-skills-and-second-brain-architecture]], [[double-entry-bookkeeping-principles]]
- Evaluation: first run 131/132 assertions, with SE-3 missing from the frontmatter of [[double-entry-bookkeeping-principles]]. Second run 132/132 after the fix. Verdict: partial, because no comparison with and without the skill has been run
- Requirements linked: [[SE-1]], [[SE-4]], [[SE-5]], [[TQ-7]], [[SK-1]]

## [2026-11-09] srs | SRS restructured to IEEE format, authentication and amount limit decided

- Source: The team's IEEE outline, the existing [SRS](../docs/SRS.md) and RFC 6750
- Notes added: none
- Notes updated: [[stage1-review-retrospective]], [[agent-skills-and-second-brain-architecture]], [[financial-api-security-and-validation]], [[ledger-reconciliation-algorithms]], [[immutable-audit-trail-and-reversals]]
- Decisions closed: `Authorization: Bearer <token>` required on all REST endpoints, and an amount limit of 10^12 minor units per transaction
- Requirements linked: [[SE-1]], [[NFR-5]], [[FR-5]]

## [2026-11-09] srs | SRS trimmed to requirements, and team names added

- Source: Team review of the [SRS](../docs/SRS.md) for length and restrictiveness
- Notes added: none
- Notes updated: none
- Changes: moved design detail to the research notes and Stage 2, marked extra reconciliation checks as recommended, added Section 2.6 and the repository link
- Requirements linked: [[SE-1]], [[SE-7]], [[FR-4]], [[FR-5]]

