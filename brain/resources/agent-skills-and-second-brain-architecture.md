---
id: agent-skills-and-second-brain-architecture
title: Agent Skills and Second Brain Architecture
type: research
author: Member 4
stage: 1
status: active
created: 2026-11-09
source:
  - "SDLC_and_Workflow.pdf, pp. 1-3 (Second Brain, SB-1 to SB-6, Common Agent Skills, TQ-7, Stage deliverables)"
  - "Financial_Ledger.pdf, p. 2 (simulate-transfer)"
  - "Agent Skills Overview: https://agentskills.io/home"
  - "Agent Skills Specification: https://agentskills.io/specification"
  - "Evaluating skill output quality, Agent Skills: https://agentskills.io/skill-creation/evaluating-skills"
  - "Local checks, 2026-11-09: skills-ref 0.1.1 and this repository"
related_requirements: [SK-1, SK-2, SK-3, SK-4, SK-5, SB-1, SB-2, SB-3, SB-5, SE-1, TQ-7, FR-1, FR-5]
---

# Agent Skills and Second Brain Architecture

## Summary

Agent Skills are folders with a `SKILL.md` file that agents load on demand, and the course requires five of them across the project. Three maintain the Second Brain and two exercise the running product. Only `brain-ingest` exists so far, so this note separates what is built from what is planned.

## Key points

### The Agent Skills format

The format was originally developed by Anthropic and released as an open standard. A skill is a folder containing at least a `SKILL.md`, and may include `scripts/`, `references/` and `assets/` folders.

| Field | Required | Rule |
| --- | --- | --- |
| `name` | Yes | 1-64 lowercase letters, digits and hyphens. No hyphen at the start or end, no `--`. Must match the folder name |
| `description` | Yes | 1-1024 characters, stating what the skill does and when to use it |
| `license` | No | License name or bundled file |
| `compatibility` | No | Up to 500 characters on environment requirements |
| `metadata` | No | Map of string keys to string values |
| `allowed-tools` | No | Pre-approved tools. Experimental |

Agents use **progressive disclosure**, which keeps many skills available at a small context cost:

| Stage | What loads | Recommended size |
| --- | --- | --- |
| Discovery | `name` and `description` of all skills | About 100 tokens |
| Activation | The full `SKILL.md` | Under 5000 tokens and 500 lines |
| Execution | Bundled files, as needed | Keep references one level deep |

### Our skills

The course PDFs do not define `SK-1` to `SK-5`. The team's SRS (`docs/SRS.md`, under [[SE-1]]) now defines them with the mapping below, which the team still needs to confirm in its review.

| Proposed ID | Skill | Purpose, from the course documents | Due | Status |
| --- | --- | --- | --- | --- |
| [[SK-1]] | `brain-ingest` | Add new material and summaries to the brain | Stage 1 | **Built** |
| [[SK-2]] | `brain-refine` | Move notes to PARA folders, merge duplicates, fix links | Stage 2 | Not started |
| [[SK-3]] | `brain-query` | Answer questions, and draft documents such as the SRS and ADRs | Stage 2 | Not started |
| [[SK-4]] | `local-check` | Build, run the tests, start the server, call one read-only fetch endpoint, report each step | Stage 2 (first version) | Not started |
| [[SK-5]] | `simulate-transfer` | Create wallets, transfer with an idempotency key, fire two concurrent transfers, reconcile, summarize | Stage 3 | Not started |

### The Second Brain

```
source material
      |
brain-ingest  --> brain/inbox, projects, areas, resources, archive
      |                 linked with [[wikilinks]] and frontmatter
      |--> brain/index.md (the entry point)
      |--> brain/log.md (records all runs)

brain-refine  --> reorganizes notes and repairs links
brain-query   --> reads notes to answer questions and draft the SRS and ADRs
```

The rules that apply to the brain and skills:

| Rule | Current state |
| --- | --- |
| [[SB-1]]: wikilinks between notes and to requirement IDs, issues and PRs | Note and requirement links are validated. There are no issue or PR links yet |
| [[SB-2]]: review note at the end of each stage | [[stage1-review-retrospective]] |
| [[SB-3]]: every skill and ADR cites a distilled note | `brain-ingest` cites two notes, but no check enforces this |
| [[SB-5]]: brain changes go through pull requests | Done for all 3 merged PRs |
| [[TQ-7]]: skill evaluations before each stage submission | **Partial**: SRS Section 6.3 records an audit, with no comparison run yet |

### Validation

- `scripts/validate_skills.py` applies the name and description rules, and CI runs it.
- The specification points to its reference validator, `skills-ref`. I installed version 0.1.1 and ran `agentskills validate .claude/skills/brain-ingest`, which reported `Valid skill`. The installed command is `agentskills`, not `skills-ref` as the documentation shows.
- `brain-ingest` is 155 lines, well under the 500-line recommendation.
- `scripts/validate_brain.py` checks only `brain/`, so the wikilinks in a `SKILL.md` are not checked.

### Evaluating skills

The format's guidance on evaluation fits [[TQ-7]]:

1. Write 2-3 realistic test prompts with expected outputs in `evals/evals.json`, including one edge case.
2. Run each one in a clean context, both with and without the skill.
3. Add checkable assertions after seeing the first outputs, and grade each with concrete evidence.
4. Compare the two runs, have a human review the outputs, and improve the skill.

## Relevance to Coinfidential

These are my recommendations and inferences:

- **Evaluate `brain-ingest` before submitting Stage 1.** [[TQ-7]] applies before each stage submission, and it is the only skill that can be evaluated now. A useful edge case is a source that mentions an undefined requirement ID.
- **Do not depend on `brain-query` for the SRS.** The SRS is due in Stage 1, but `brain-query` is not due until Stage 2, so the SRS has to be written without it.
- **Build the skills in dependency order.** `local-check` can use the existing `/health` endpoint at first, although the team should confirm that it counts as a "read-only fetch endpoint". `simulate-transfer` cannot work until [[FR-1]] to [[FR-5]] exist.
- **Check `brain-refine` against the validators.** Moving a note keeps filename links working, but links by path would break, and the note's `id` must keep matching its filename.
- **Keep `brain-query` limited to what the notes say.** Its drafts should cite the notes they use, which also supports [[SB-3]] for ADRs.
- **Enforce [[SB-3]] in CI.** A small addition to `validate_skills.py` could require at least one resolving wikilink in each `SKILL.md`.
- **Have `simulate-transfer` compare final balances with expected values.** [[ledger-reconciliation-algorithms]] shows that a passing reconciliation alone does not prove the transfers were correct.

## Requirements

- [[SK-1]], [[SK-2]], [[SK-3]], [[SK-4]], [[SK-5]]: The five skills, using the mapping above.
- [[SB-1]], [[SB-2]], [[SB-3]], [[SB-5]]: The rules that the brain and skills must follow.
- [[SE-1]]: The SRS defines the SK requirements.
- [[TQ-7]]: Skill evaluations must run before each stage submission.
- [[FR-1]], [[FR-5]]: The range of functional requirements that `simulate-transfer` depends on.

## Related notes

- [[stage1-ai-session-setup]]: Records how `brain-ingest` and the validators were created.
- [[stage1-review-retrospective]]: Includes the plan and owners for building these skills.
- [[ledger-reconciliation-algorithms]]: Defines the endpoint that `simulate-transfer` calls.
- [[race-conditions-and-optimistic-locking]]: Defines the concurrency test that `simulate-transfer` runs.
- [[idempotent-api-design-patterns]]: Covers the idempotency key that `simulate-transfer` uses.
- [[financial-api-security-and-validation]]: Lists negative cases that a skill or test could exercise.

## Open questions

- Does the team agree with this `SK-1` to `SK-5` mapping in the SRS? The validator accepts any numbered `SK` ID, so it cannot confirm their meaning.
- The source named "How I Built My Second Brain with Obsidian + Claude Code" is listed in the course PDF as the basis for these skills, but it returned `403 Forbidden` when fetched, so I have not read it. A member should read it before building `brain-refine` and `brain-query`.
- Should CI also run `skills-ref`? It would track the official rules, but the version would need pinning, and it is at an early version.
- Where should evaluation results go? [[TQ-7]] says the test documentation, which does not exist yet.
- Has the vault been opened in Obsidian? No `.obsidian` folder is present, so this is unconfirmed. If that folder appears, the team must decide whether to track it.
