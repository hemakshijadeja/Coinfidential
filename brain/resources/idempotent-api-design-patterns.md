---
id: idempotent-api-design-patterns
title: Idempotent API Design Patterns
type: research
author: Member 3
stage: 1
status: active
created: 2026-11-08
source:
  - "Financial_Ledger.pdf, pp. 1-2 (FR-2, TQ-1, TQ-4)"
  - "The Idempotency-Key HTTP Header Field, draft-08: https://datatracker.ietf.org/doc/draft-ietf-httpapi-idempotency-key-header/"
  - "Idempotent requests, Stripe API documentation: https://docs.stripe.com/api/idempotent_requests"
  - "RFC 8785, JSON Canonicalization Scheme: https://www.rfc-editor.org/rfc/rfc8785.html"
  - "hashlib, Python documentation: https://docs.python.org/3/library/hashlib.html"
  - "Local experiments, 2026-11-08: Python 3.12.5, SQLite 3.45.3, on Windows"
related_requirements: [FR-2, TQ-1, TQ-2, TQ-4, FR-3, SE-3]
---

# Idempotent API Design Patterns

## Summary

An `Idempotency-Key` header lets a client retry a transfer safely, because the server recognizes the retry and does not move the money again. The server also stores a SHA-256 hash of the request, so a reused key with different content can be rejected. In testing, this was safe only when the idempotency record and the ledger entries committed in the same transaction.

## Key points

### The header

- [[FR-2]] requires an idempotency key header on the transfer endpoint, so retried requests never double-charge an account.
- The IETF draft says a key "MUST be unique" and must not be reused with a different payload, and recommends a UUID or similar random value. The draft is not yet a finished standard, so it could change.
- Stripe suggests V4 UUIDs, limits keys to 255 characters, and warns against using sensitive data as keys.
- Resources must publish their idempotency rules, including any key expiry policy.

### Status codes

`409` and `422` are easy to confuse here, because both can follow a retry. The IETF draft uses `422` for a mismatched payload and `409` for a request still in progress, and [[rest-api-error-handling-and-status-codes]] already follows it:

| Situation | Draft's status |
| --- | --- |
| Required key is missing | `400` |
| Same key, **different payload** | `422` |
| Same key, original request **still processing** | `409` |
| Same key and payload, original completed | A response "consistent with the request being completed" |

### Hashing the payload

The draft allows a fingerprint of the request, such as a checksum of the payload, but names no algorithm. SHA-256 is therefore a project choice, not a requirement of the draft. Python's `hashlib` needs bytes, and passing a string raised `TypeError: Strings must be encoded before hashing`.

| Comparison with `{"from":"A","to":"B","amount":500}` | Raw bytes | Sorted, compact JSON |
| --- | --- | --- |
| Same fields in a different order | Different hash | **Same hash** |
| Same fields with extra whitespace | Different hash | **Same hash** |
| Amount of `501` | Different hash | Different hash |
| Amount of `500.0` | Different hash | Different hash |

Hashing raw bytes would reject a valid retry from a client that reorders its JSON. RFC 8785 defines a full canonical form for JSON, but it is an Informational document, not a standard. `json.dumps(..., sort_keys=True, separators=(",", ":"))` is simpler, and is not the same thing as RFC 8785.

### Atomic storage

Each of these experiments simulated a crash or a race on a balance of 1000, with a transfer of 100.

| Design | Result | Final balance | Entries |
| --- | --- | ---: | ---: |
| Ledger and idempotency record in **separate** transactions, crash between them, then retry | **Double charge** | **800** | **2** |
| Both in the **same** transaction, crash before commit, then retry | Applied once | 900 | 1 |
| 8 concurrent retries, key checked outside any transaction, `UNIQUE` constraint only | **8 charges**, 7 constraint errors after the money moved | **200** | **8** |
| 8 concurrent retries, everything inside `BEGIN IMMEDIATE`, 5 trials | Applied once, 8 identical `201` responses | 900 | 1 |

A `UNIQUE` constraint alone is not enough, because the error arrives after the money has moved unless the writes share one transaction.

## Relevance to Coinfidential

These are my recommendations and inferences, based on the results above:

- **Use this order inside one `BEGIN IMMEDIATE` transaction:** look up the key, compare the hash, check funds, write the ledger entries, update balances, store the idempotency record, then commit.
- **Hash the validated request, not the raw bytes.** Include the method, the path and the validated fields. Validation should run first, so strict integer checks from [[integer-minor-units-money-math]] reject `500.0` before hashing.
- **Scope keys to the caller,** with a primary key of `(owner, key)`. In testing, two owners could use the same key independently. The draft warns that guessable keys could otherwise expose other clients' entries, and suggests a composite lookup.
- **Expect `409` to be rare.** With the whole request inside `BEGIN IMMEDIATE`, concurrent retries waited and then replayed the result: 0 of 40 requests saw a "still processing" state. The API should still document `409`, and a busy timeout needs its own defined response.
- **Do not store validation failures.** Stripe does not save them either, because execution never began, so the client can correct and retry.

## Requirements

- [[FR-2]]: This note covers the design of the required idempotency key.
- [[TQ-1]]: Unit tests cover the hashing rules in the table above.
- [[TQ-4]]: Negative tests cover invalid idempotency payloads and reused keys.
- [[TQ-2]]: Rollback tests must show that a failed transfer leaves no idempotency record.
- [[FR-3]]: Concurrent retries are one form of simultaneous request.
- [[SE-3]]: The idempotency design belongs in an ADR.

## Related notes

- [[double-entry-bookkeeping-principles]]: Explains why reconciliation cannot catch a duplicate transfer, which is why this check must stop it first.
- [[rest-api-error-handling-and-status-codes]]: Lists the same status codes, and notes that FastAPI returns `422` for a missing header by default.
- [[integer-minor-units-money-math]]: Covers the strict validation that runs before hashing.
- [[immutable-audit-trail-and-reversals]]: A reversal is also a money movement, so it needs its own idempotency key.
- [[ledger-reconciliation-algorithms]]: Shows that reconciliation passes on a duplicate transfer.

Member 2's `sqlite-acid-and-wal-concurrency` and `race-conditions-and-optimistic-locking` notes are closely related, but they are on an unmerged branch. They are not linked here because the links would fail validation on this branch.

## Open questions

- Does "idempotency key hashing" in [[TQ-1]] mean hashing the payload, as this note assumes, or hashing the key itself? The team should confirm this.
- Should insufficient funds be stored? In testing, a stored rejection meant a retry with the same key still failed after funds arrived. I would store it, so one key always gives one outcome and a new attempt needs a new key, but this needs a decision.
- How long should keys be kept? Stripe may prune keys after 24 hours, and then treats a reused key as a new request. [[FR-2]] says retries must "never" double-charge, so I would keep them indefinitely at this project's scale.
- Should the stored response be replayed exactly? The draft only asks for a consistent response, while Stripe v1 replays the saved status and body.
