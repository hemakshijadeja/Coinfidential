---
id: stage1-review-retrospective
title: Stage 1 Review and Retrospective
type: review
author: Member 1
stage: 1
status: draft
created: 2026-11-08
source:
  - "SDLC_and_Workflow.pdf, pp. 1-2 (SB-2, Stage 1 deliverables)"
  - "The Stage 1 Claude Code session"
related_requirements: [SB-2, SB-6, SE-1, TQ-7]
---

# Stage 1 Review and Retrospective

## Summary

This is the review note [[SB-2]] requires, covering what worked, what did not, and what to change. It is a draft from Member 1's setup work only, because Stage 1 is not finished. The team should complete it before submitting Stage 1.

## Key points

### What worked

- Running validators against deliberately broken input showed that the checks really fail.
- Testing behavior directly found problems that reading alone would have missed, such as float drift hidden by `sum()`.
- Keeping commits manual gave a human a checkpoint before anything entered Git history.

### What did not work

- The foundation was built before the requirement documents were read, so it needed a second and third pass to meet them.
- `.gitignore` could not remove a file that was already staged.
- The first gap review missed the SRS and the skill evaluations listed below.

### What to change

- Read the requirement documents first, and turn them into a checklist before generating anything.
- Keep the course PDFs somewhere every member can find them. They are ignored by Git and were in a folder named `Garbage`.
- Have a second member review each AI-generated change in a pull request.

## Relevance to Coinfidential

Stage 1 status on 2026-11-08, checked against `SDLC_and_Workflow.pdf`:

| Deliverable | Status |
| --- | --- |
| SRS with FR, NFR and SK ([[SE-1]]) | Not started in this repository |
| Brain with PARA folders, index and log | Done, but not yet opened as an Obsidian vault |
| At least 10 research notes through `brain-ingest` | 3 of 10 |
| `AGENTS.md` ([[SB-4]]) | Done |
| Repository and CI skeleton | Passes locally, but has not run on GitHub |
| Every member authors notes ([[SB-6]]) | Member 1 only so far |
| Skill evaluations before submission ([[TQ-7]]) | Not started |
| Pull requests with review, GitHub Issues | Rule documented, but not yet in use or enforced on GitHub |

## Requirements

- [[SB-2]]: This is the Stage 1 review note.
- [[SB-6]]: The other members' contributions are still needed.
- [[SE-1]]: The SRS is still outstanding.
- [[TQ-7]]: Skill evaluations still have to run and be recorded.

## Related notes

- [[stage1-ai-session-setup]]: The detailed record of the setup session.
- [[double-entry-bookkeeping-principles]]: Member 1 research note.
- [[integer-minor-units-money-math]]: Member 1 research note.
- [[rest-api-error-handling-and-status-codes]]: Member 1 research note.

## Open questions

- What are the other members' views on what worked? This draft reflects only Member 1's work.
- How does the team want to run the skill evaluations for [[TQ-7]], and where will the results be recorded?
