---
id: stage1-review-retrospective
title: Stage 1 Review and Retrospective
type: review
author: Member 4
stage: 1
status: active
created: 2026-11-08
updated: 2026-11-09
source:
  - "SDLC_and_Workflow.pdf, pp. 1-3 (SB-2, SE-4, GitHub rules, stage deliverables)"
  - "Git history of this repository, to c560a8e"
  - "GitHub public API, 2026-11-09: pull requests, reviews, Actions runs and issues for hemakshijadeja/Coinfidential"
  - "Team research notes and the Stage 1 Claude Code sessions"
related_requirements: [SB-1, SB-2, SB-3, SB-4, SB-5, SB-6, SE-1, SE-2, SE-3, SE-4, SE-5, SK-1, SK-2, SK-3, SK-4, SK-5, TQ-7, FR-1, FR-5]
---

# Stage 1 Review and Retrospective

## Summary

This is the review note required by [[SB-2]], and it holds the task breakdown for [[SE-4]]. Member 1 drafted it and Member 4 completed it. Stage 1 has produced 11 research notes across all 4 members and a working CI pipeline, but it is **not yet ready to submit**: the SRS, skill evaluations, pull request reviews and GitHub Issues are all still missing.

This review is based on repository evidence. The team should add its own views before submission.

## Key points

### What was produced

| Member | Git user | Research notes | Other work |
| --- | --- | --- | --- |
| Member 1 | `hemakshijadeja` | [[double-entry-bookkeeping-principles]], [[integer-minor-units-money-math]], [[rest-api-error-handling-and-status-codes]] | Repository, CI, validators, `AGENTS.md`, `brain-ingest`, [[stage1-ai-session-setup]] |
| Member 2 | `AdityaBhat2` | [[sqlite-acid-and-wal-concurrency]], [[race-conditions-and-optimistic-locking]], [[provider-interface-isolation]] | |
| Member 3 | `Subhadeep-7597` | [[idempotent-api-design-patterns]], [[immutable-audit-trail-and-reversals]], [[ledger-reconciliation-algorithms]] | |
| Member 4 | `hardhkava` | [[financial-api-security-and-validation]], [[agent-skills-and-second-brain-architecture]] | Completed this review |

That is 11 research notes against a minimum of 10, plus 1 `ai-session` note and this review. Nine are on `main`, and Member 4's two arrive with this branch.

### What worked

- **Research included real experiments.** Testing changed the team's conclusions: WAL alone allowed a balance of `-700`, `INSERT OR REPLACE` got past the append-only triggers, and a `-500` transfer passed reconciliation.
- **The shared note format held up.** All four members followed the same `brain-ingest` process and schema, and the validators kept the links and frontmatter consistent.
- **CI ran on GitHub.** The 8 most recent of 10 Actions runs all succeeded. The older 2 were not read.
- **All work reached `main` through pull requests,** which meets [[SB-5]] for the 3 merged so far.
- **Commits stayed manual.** Git history contains no AI `Co-Authored-By` trailers.
- **Validators were tested against bad input,** so a passing result is meaningful.

### What did not work

| Problem | Evidence | Effect |
| --- | --- | --- |
| No recorded reviews | PRs #1, #2 and #3 each show 0 reviews on GitHub | Breaks the rule of at least one review per change, and human review of AI work is unproven |
| No GitHub Issues | 0 issues exist | Work is not tracked as the rubric requires, and [[SE-5]] has nothing to trace |
| SRS not started | No SRS in the repository | The main Stage 1 deliverable is missing, and `SK-1` to `SK-5` are undefined |
| Skills not evaluated | No `evals` folder | [[TQ-7]] is unmet |
| Few, large commits | Members 2 and 3 have 1 commit each, and Member 1's main commit combines CI, skills and notes | Falls short of "meaningful incremental commits" |
| Shared files caused conflicts | `index.md` and `log.md` conflicted between member branches, needing a merge fix in `fdc009e` | Extra work, with stray blank lines left in both files |
| Parallel branches blocked links | Member 3 could not link Member 2's unmerged notes | 3 plain-text mentions still need converting under [[SB-1]] |
| Branch names differ from the rules | `brain/*` and `feat/*` are in use, but `AGENTS.md` lists `feature`, `fix`, `docs`, `test`, `chore` | The documentation and practice disagree |
| Only one `ai-session` note | Only Member 1's session is recorded | Falls short of the AI policy for significant sessions |
| Foundation built before reading the requirements | Recorded in [[stage1-ai-session-setup]] | Needed extra passes, and the first gap review missed the SRS |
| Experiment code is not in the repository | `tests/` holds only one `/health` test | Findings are recorded, but nothing protects them from regressions yet |

### What to change in Stage 2

1. **Turn the rules on.** Enable branch protection on `main`, with a required review and passing CI. A person other than the author reviews each PR.
2. **Start from Issues.** Create an issue before each task, and reference it in the branch, PR and traceability matrix.
3. **Read the requirements first.** Turn the stage's deliverables into a checklist of issues before generating anything.
4. **Commit in smaller steps,** with one logical change in each commit.
5. **Reduce conflicts.** Merge note PRs promptly, and rebase on `main` just before opening a PR.
6. **Update `AGENTS.md`** to match the agreed branch names, or rename future branches to match it.
7. **Record each significant AI session** as an `ai-session` note, covering the goal and what worked or failed.
8. **Evaluate each skill as it is built,** rather than at the end of the stage.
9. **Turn experiment findings into tests** once the code they describe exists.

### Task breakdown

Stage 1 ownership above is taken from Git history. **The owners below are proposals based on each member's research area, for the team to confirm.** Each task should become a GitHub Issue.

**Remaining before Stage 1 submission**

| Task | Requirement | Proposed owner |
| --- | --- | --- |
| Write the SRS: FR and NFR sections | [[SE-1]] | Member 1 |
| Write the SRS: define SK requirements | [[SE-1]], [[SK-1]] | Member 4 |
| Review the SRS, covering concurrency and ledger rules | [[SE-1]] | Members 2 and 3 |
| Evaluate `brain-ingest` and record the results | [[TQ-7]] | Member 4 |
| Create Issues, and enable branch protection | [[SE-5]] | Member 1 |
| Retroactively review merged PRs, or record why this was not done | [[SB-5]] | All members |
| Add `ai-session` notes for Members 2, 3 and 4 | [[SB-6]] | Each member |
| Convert plain-text links to wikilinks | [[SB-1]] | Member 3 |
| Open the vault in Obsidian and confirm it works | [[SB-1]] | Member 4 |
| Add the team's own views to this review | [[SB-2]] | All members |

**Stage 2: Design**

| Task | Requirement | Proposed owner |
| --- | --- | --- |
| Architecture document and system diagrams | [[SE-2]] | Member 1 |
| ER diagram, schema and transaction design | [[SE-2]] | Member 2 |
| ADRs for locking, idempotency, immutability and reconciliation | [[SE-3]], [[SB-3]] | Members 2 and 3 |
| ADRs for validation, error format and authentication | [[SE-3]], [[SB-3]] | Members 1 and 4 |
| `brain-refine` skill | [[SK-2]] | Member 3 |
| `brain-query` skill | [[SK-3]] | Member 4 |
| First version of `local-check` | [[SK-4]] | Member 2 |
| Traceability matrix | [[SE-5]] | Member 1 |
| Stage 2 review note | [[SB-2]] | All members |

**Later stages**

| Stage | Main work, from the course document | Proposed lead |
| --- | --- | --- |
| Stage 3: Testing and CI | Testing and CI plan and results, `simulate-transfer` with results ([[SK-5]]), defect log with regression tests, review note | Members 3 and 4 |
| Stage 4: Review | Live demo of [[FR-1]] to [[FR-5]], skills run live, one requirement traced from brain note to ADR, code and test, final release tag | All members |

The course document does not set a separate implementation stage, but Stage 3 and Stage 4 both need working [[FR-1]] to [[FR-5]]. The team should plan when this code gets built.

## Relevance to Coinfidential

Stage 1 status on 2026-11-09, checked against `SDLC_and_Workflow.pdf`:

| Deliverable | Status |
| --- | --- |
| SRS with FR, NFR and SK ([[SE-1]]) | **Not started** |
| Brain with PARA folders, index and log | Folders, index and log are done. Use in Obsidian is unconfirmed |
| `brain-ingest` used for at least 10 research notes | **Met** once this branch merges: 11 |
| `AGENTS.md` ([[SB-4]]) | Done |
| Repository and CI skeleton | Done, and running on GitHub |
| Every member authors notes ([[SB-6]]) | 3 members in `main`, and Member 4 once this branch merges |
| Skill evaluations ([[TQ-7]]) | **Not started** |
| Every skill cites a distilled note ([[SB-3]]) | Done for `brain-ingest`, but not enforced |
| Pull requests with reviews | **Not met**: 0 reviews on 3 PRs |
| GitHub Issues for all work | **Not met**: 0 issues |

The research also left design decisions open, which should become ADRs: how wallets receive their first funds, authentication, the treatment of insufficient funds under idempotency, and how to handle a reversal after the recipient has spent the money.

## Requirements

- [[SB-2]]: This is the Stage 1 review note.
- [[SE-4]]: This note holds the task breakdown and an outline plan by stage.
- [[SE-1]], [[SE-2]], [[SE-3]], [[SE-5]]: Engineering documents in the plan.
- [[SB-1]], [[SB-3]], [[SB-4]], [[SB-5]], [[SB-6]]: Second Brain rules assessed in this review.
- [[SK-1]], [[SK-2]], [[SK-3]], [[SK-4]], [[SK-5]]: The skills in the plan, using the proposed mapping in [[agent-skills-and-second-brain-architecture]].
- [[TQ-7]]: Skill evaluations are outstanding.
- [[FR-1]], [[FR-5]]: The range of functional requirements that later stages must demonstrate.

## Related notes

- [[stage1-ai-session-setup]]: The detailed record of the setup session.
- [[agent-skills-and-second-brain-architecture]]: Describes the skills in this plan.
- [[financial-api-security-and-validation]]: Raises the open authentication question.

The research notes from all four members are linked in the table under **What was produced**.

## Open questions

- Do the other members agree with this assessment and the proposed owners? This review comes from repository evidence, not from a team discussion.
- Were PRs reviewed outside GitHub's review feature? The API shows none recorded, so any informal reviews should be noted here.
- What is the Stage 1 deadline? It decides whether the SRS and evaluations come before anything else.
- Does a note satisfy [[SE-4]], or do reviewers expect a separate development plan with dates? No dates are set here because none are in the course documents.
- Is branch protection already on? The public API does not show it without authentication, but the merges with no reviews suggest that a required review is not enforced.
