# Changelog

All the main changes to Coinfidential are listed here.

## v0.1.0 - Stage 1

Stage 1 was about requirements and setting up the project.

### Added

- Set up the repo with `.gitignore` and a README.
- Added a basic FastAPI app with a `/health` endpoint.
- Added the CI pipeline (compile check, ruff, pytest, secret scan, skill and brain validation).
- Added `AGENTS.md` with our rules for Git, the Second Brain and Agent Skills.
- Added the `brain-ingest` skill.
- Added research notes to the Second Brain (`brain/`) on:
  - SQLite WAL mode, concurrency and race safety
  - Idempotency, immutable audit trail and reconciliation
  - Security validation and the agent skills setup
- Wrote the Stage 1 review note.
- Wrote the SRS in IEEE format, with diagrams and links to our GitHub issues.

### Changed

- Did a formal GitHub review of the Stage 1 work and fixed the gaps it found.
- Simplified the SRS to make it easier to read.
