---
id: stage1-ai-session-setup
title: Stage 1 AI Session - Project Setup
type: ai-session
author: Member 1
stage: 1
status: active
created: 2026-11-08
source:
  - "Claude Code session in the VS Code extension, model Claude Opus 5.5, 2026-11-08"
  - "SDLC_and_Workflow.pdf, pp. 1-2 (SB-1 to SB-6, AI-Assisted Development Policy, Stage 1 deliverables)"
  - "Financial_Ledger.pdf, pp. 1-2"
related_requirements: [SB-1, SB-3, SB-4, SB-5]
---

# Stage 1 AI Session - Project Setup

## Summary

Member 1 used Claude Code to set up the Stage 1 repository foundation, then used the new `brain-ingest` skill to write the first notes. The foundation passes its local checks, and a later pass closed most of the gaps found against the course documents. A human still has to review this work, and nothing has been committed by the AI.

## Key points

**Goal:** create the repository skeleton, `AGENTS.md`, the PARA brain, the `brain-ingest` skill, validation scripts and CI, then ingest the first research notes.

**Produced:**

- `AGENTS.md`, `README.md`, `.gitignore`, `requirements.txt` and `pytest.ini`
- A FastAPI app with a `/health` endpoint and one test
- `scripts/validate_skills.py`, `scripts/validate_brain.py`, `scripts/scan_secrets.py` and `.github/workflows/ci.yml`
- The `brain-ingest` skill, [[index]], [[log]], three research notes and a draft of [[stage1-review-retrospective]]

**Rules given to the AI:** it must not run `git commit` or `git push`, and commits must have no AI `Co-Authored-By` trailers.

### What worked

- **Breaking things on purpose:** running the validators on a scratch copy with bad links and bad frontmatter showed that they really fail, not just pass.
- **Clean environment:** installing the pinned requirements in a new virtual environment confirmed that they install and that the test and both validators pass.
- **Reading the course PDFs:** this corrected the definition of the Vanishing Money Glitch and confirmed the `SE-1` to `SE-7` IDs.
- **Running the experiments:** real output replaced assumptions in [[integer-minor-units-money-math]].

### What failed

- **Requirements were not read first.** The foundation was built from the prompt alone, and the AI searched only the repository for the requirements. The PDFs were in a sibling folder, so the validator missed the `SE` series until the human asked for it.
- **The first float demo proved nothing.** `sum([0.1] * 10)` returned exactly `1.0`, because `sum()` reduces accumulated error. A plain loop showed the real drift.
- **`.gitignore` alone did not keep out `.claude/settings.json`.** The file was already staged, so it also needed `git rm --cached`. It was not ignored originally, because the first prompt asked to create it as a project file.
- **`pytest` was not on the shell's PATH.** The global command failed with exit code 127, so the tests were run from the virtual environment instead.
- **PDFs could not be read directly.** The Read tool needs `pdftoppm`, which is not installed. Extracting the text with `pypdf` in a scratch environment worked, but any content in images would have been missed.
- **The first gap review was incomplete.** It missed the SRS, the skill evaluations under [[TQ-7]] and the CI build step, which were found only when the documents were checked again.

## Relevance to Coinfidential

Comparing the foundation with `SDLC_and_Workflow.pdf` found these gaps. The current state is below, and [[stage1-review-retrospective]] tracks the wider Stage 1 deliverables:

| Requirement in the document | Current state |
| --- | --- |
| CI runs build and lint | Added to `ci.yml` |
| CI runs secret scanning | Added with `scripts/scan_secrets.py` |
| CI validates brain note schema | Added to `scripts/validate_brain.py` |
| [[SB-3]]: every skill cites a distilled note | `brain-ingest` now cites two notes |
| PRs have at least one review | Stated in `AGENTS.md`, but not yet enforced on GitHub |
| `brain-ingest` adds at least 10 research notes | Still open: 3 research notes so far, and the other members add the rest |

**What to change next time** (my recommendation): read the requirement documents before generating anything, then check the output against them.

## Requirements

- [[SB-4]]: This session created `AGENTS.md` at the repository root.
- [[SB-1]]: The notes link to each other and to requirement IDs with wikilinks.
- [[SB-3]]: `brain-ingest` cites this note as one of its distilled notes.
- [[SB-5]]: This session's brain changes still need to go through a pull request.

## Related notes

- [[double-entry-bookkeeping-principles]]: Research note written in this session.
- [[integer-minor-units-money-math]]: Research note written in this session.
- [[rest-api-error-handling-and-status-codes]]: Research note written in this session.
- [[stage1-review-retrospective]]: The Stage 1 review note.

## Open questions

- Has `ci.yml` run on GitHub? It has only been checked as valid YAML, so its first real run comes after the first push.
- `.claude/settings.json` is now untracked, so `includeCoAuthoredBy` no longer applies to a fresh clone. Each member must set it locally.
- Does the first commit need to go through a pull request? [[SB-5]] covers brain changes, but `main` has no commits yet for a branch to target.
- The review note required by [[SB-2]] is still a draft, which the team completes at the end of the stage.
