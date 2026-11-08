# AGENTS.md

Instructions for every AI agent and human contributor working in this repository. This file satisfies requirement SB-4.

## Project overview

Coinfidential is a Financial Ledger & Digital Wallet RESTful API built with Python, FastAPI and SQLite.

**Current stage:** Stage 1 (Requirements). The repository holds the project foundation and a `/health` endpoint. Ledger and wallet features are not implemented yet.

These rules apply to all ledger and wallet code:

| Concern | Rule |
| --- | --- |
| Storage | SQLite with WAL mode enabled (`PRAGMA journal_mode=WAL`). |
| Money | Store and calculate amounts as integers in minor units, such as cents or paise. Never use floats for money. |
| Transactions | Every multi-row money movement runs in a single ACID transaction. It either commits completely or leaves no trace. |
| Idempotency | Retrying a money-moving request with the same idempotency key must not apply it a second time. |
| Double-entry | Every ledger transaction has balanced entries: total debits equal total credits. |

## Git workflow

### Branching

- `main` must always be in a passing state. Do not commit feature work directly to it.
- Create one short-lived branch per change, named `<type>/<short-description>`. Include the requirement ID when there is one, for example `feature/fr-1-create-wallet`.
- Use one of these branch types: `feature`, `fix`, `docs`, `test`, `chore`.

### Pull requests

- Every change reaches `main` through a pull request, including code, skills and brain notes.
- **Every pull request requires at least one human review before merging.** A human must review every AI-generated change, and an AI review does not count.
- CI (`.github/workflows/ci.yml`) must pass before merging.
- Every member must be able to explain any merged code, skill or document.
- The PR description states what changed and lists the requirement IDs it addresses.

### Commit rules for AI agents

- **Agents must not run `git commit` or `git push`.** The human developer runs all commits and pushes manually. Agents may edit files and run read-only git commands, then report what is ready to commit.
- **AI `Co-Authored-By` trailers are strictly prohibited** in commit messages. Do not add any other AI attribution to commits or PR descriptions either. `.claude/settings.json` and `.claude/settings.local.json` are ignored by Git, so each contributor sets `includeCoAuthoredBy` to `false` in their own `.claude/settings.json`. Only `.claude/skills/` is tracked.

## Second Brain (PARA)

Project knowledge lives in `brain/`, organized with the PARA method:

| Path | Contents |
| --- | --- |
| `brain/inbox/` | Unprocessed captures waiting to be sorted. |
| `brain/projects/` | Notes for work with a defined outcome and end, such as a project stage. |
| `brain/areas/` | Ongoing responsibilities with no end date, such as security or code quality. |
| `brain/resources/` | Reference material and research on topics of interest. |
| `brain/archive/` | Inactive notes from the other categories. |
| `brain/index.md` | The catalog of notes. Every note outside `inbox/` is listed here. |
| `brain/log.md` | An append-only, chronological record of changes to the brain. |

### Wikilinks are mandatory

Link notes to each other and to requirements with `[[wikilinks]]`, not Markdown links:

- A note, by filename without `.md`: `[[wal-mode-research]]`
- A note, by path relative to `brain/`: `[[resources/wal-mode-research]]`
- A note with display text or a heading: `[[wal-mode-research|WAL notes]]`, `[[wal-mode-research#Trade-offs]]`
- A requirement ID: `[[FR-1]]`

Recognized requirement IDs are `FR-1` to `FR-5`, `SE-1` to `SE-7`, and `NFR-<n>`, `SK-<n>`, `TQ-<n>` and `SB-<n>`, where `<n>` is a number.

Every link must resolve to a real note or a requirement ID. Links inside code spans and code blocks are not checked.

### Note frontmatter

Every note in a PARA folder starts with YAML frontmatter containing these required fields. `brain/index.md` and `brain/log.md` are exempt.

| Field | Rule |
| --- | --- |
| `id` | Must match the filename without `.md`, and be unique. |
| `title` | Non-empty text. |
| `type` | One of `research`, `ai-session`, `review` or `capture`. |
| `author` | The team member responsible for the note, such as `Member 1`. |
| `stage` | The project stage, a number from 1 to 4. |
| `related_requirements` | A list of requirement IDs. Use `[]` if there are none. |

To validate links and frontmatter, run:

```
python scripts/validate_brain.py
```

To add research notes, use the `brain-ingest` skill. Record significant AI sessions as `ai-session` notes covering the goal and what worked or failed, and write a `review` note at the end of each stage.

## Agent Skills

Skills follow the [Agent Skills specification](https://agentskills.io/specification). Each skill lives in its own folder and has this entry point:

```
.claude/skills/<skill-name>/SKILL.md
```

`SKILL.md` starts with YAML frontmatter, followed by Markdown instructions:

```markdown
---
name: skill-name
description: What the skill does and when to use it.
---

# Instructions go here
```

- `name` is required and must match the folder name. It has 1-64 characters: lowercase letters, numbers and single hyphens, with no hyphen at the start or end.
- `description` is required and has 1-1024 characters.
- The body cites at least one distilled brain note with a `[[wikilink]]` (SB-3).

To validate all skills, run:

```
python scripts/validate_skills.py
```

## Before you finish a change

Run these checks, which CI also runs:

```
python -m compileall -q app scripts tests
ruff check .
pytest
python scripts/scan_secrets.py
python scripts/validate_skills.py
python scripts/validate_brain.py
```

Never paste secrets, tokens or credentials into an AI tool or a tracked file.
