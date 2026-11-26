# Architecture Decision Records (ADRs)

An ADR is a short document that records one important decision we made about the project, why we made it, and what happens because of it.

We write ADRs so that anyone in the team (or a marker) can see later why the code is built the way it is, without having to ask around.

## When to write one

Write an ADR when a decision is hard to change later or affects more than one part of the project. For example:

- choosing SQLite with WAL mode
- storing money as integers in minor units
- how we handle idempotency keys

## How to write one

1. Copy `0000-template.md` and name it with the next number and a short title, like `0001-use-sqlite-wal-mode.md`.
2. Fill in every section. Keep it short.
3. In "Brain notes cited", link the brain notes you used with `[[wikilinks]]`.
4. Open a pull request so at least one other member reviews it.

## Status values

- **Proposed** - still being discussed
- **Accepted** - we agreed and are following it
- **Superseded** - replaced by a newer ADR (link to it)

Don't delete old ADRs. If a decision changes, write a new ADR and mark the old one as superseded.
