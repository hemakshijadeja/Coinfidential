# ADR-0005: Access token format and how long tokens last

- **Date:** 2026-11-26
- **Author:** Hardh
- **Requirements:** NFR-5, TQ-4, FR-5, SE-3

## Status

Proposed

## Context

Appendix C item 4 of the SRS leaves the token format and how long tokens last for a Stage 2 decision record. This ADR is that record.

Things we already know:

- The SRS says every REST endpoint needs `Authorization: Bearer <token>`. How tokens are issued is only an adopted default and still needs an ADR ([[financial-api-security-and-validation]]).
- The SRS also says an operator issues tokens (OD-13), tokens must expire, and they must never be stored in readable form, written to logs or put in a URL.
- The ledger check endpoint needs a token with the `admin` role ([[ledger-reconciliation-algorithms]]).
- Every wallet access must be checked against the token's owner, not just the input format (OWASP API1:2023, [[financial-api-security-and-validation]]).

The brain notes do not say anything about which token format to use or how long a token should last, so those parts below are my suggestions.

## Decision

Tokens are random opaque strings, not JWTs. The server makes them with `secrets.token_urlsafe(32)` and only stores their SHA-256 hash, along with the user ID, the role (`user` or `admin`) and an expiry time. (my suggestion)

Wallet holder tokens last 24 hours and admin tokens last 1 hour. After that the API returns `401` and the operator has to issue a new one. There are no refresh tokens. (my suggestion)

## Consequences

Good:

- Simple to build and explain. Checking a token is one lookup by hash in SQLite, and we do not need a JWT library or signing keys. (my suggestion)
- If the database leaks, the stored hashes cannot be used as tokens, which covers "never stored in readable form".
- An operator can revoke a token right away by deleting its row, which a JWT cannot do without extra work.
- The role in the token row gives us the `admin` check that [[FR-5]] needs ([[ledger-reconciliation-algorithms]]).

Bad:

- Every request needs a database read to check the token.
- A stolen token still works until it expires, which is the remaining risk in the SRS. Short admin tokens make this smaller but do not remove it.
- Users have to ask the operator for a new token every day, which is annoying but fine for this project because registration is out of scope.
- We still need tests for missing, wrong, expired and other-user tokens under [[TQ-4]], and we need to make sure the error handler never echoes the token back ([[financial-api-security-and-validation]]).

## Brain notes cited

- [[financial-api-security-and-validation]]: The Bearer token rule, the open question saying token issuing needs an ADR, and the OWASP point about checking every wallet access.
- [[ledger-reconciliation-algorithms]]: The ledger check endpoint needs an `admin` role token.
