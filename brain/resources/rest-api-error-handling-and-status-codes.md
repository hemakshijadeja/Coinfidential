---
id: rest-api-error-handling-and-status-codes
title: REST API Error Handling and Status Codes
type: research
author: Member 1
stage: 1
status: active
created: 2026-11-08
source:
  - "RFC 9110, HTTP Semantics, sections 9.2.2 and 15: https://www.rfc-editor.org/rfc/rfc9110.html"
  - "RFC 9457, Problem Details for HTTP APIs: https://www.rfc-editor.org/rfc/rfc9457.html"
  - "The Idempotency-Key HTTP Header Field, draft-08, section 2.7: https://datatracker.ietf.org/doc/draft-ietf-httpapi-idempotency-key-header/"
  - "Handling Errors, FastAPI documentation: https://fastapi.tiangolo.com/tutorial/handling-errors/"
  - "Financial_Ledger.pdf, pp. 1-2"
  - "Local experiments, 2026-11-08: FastAPI 0.139.2"
related_requirements: [FR-2, FR-5, TQ-3, TQ-4, SE-3, SE-7]
---

# REST API Error Handling and Status Codes

## Summary

HTTP status codes say what kind of failure occurred, and RFC 9457 defines a standard JSON body for the details. POST is not idempotent under RFC 9110, so a transfer API needs its own protection against retries, which the brief requires through an idempotency key. FastAPI's default errors differ from the IETF idempotency draft and RFC 9457 in several ways, so Coinfidential has to choose its behavior deliberately.

## Key points

- **Status code meanings (RFC 9110):**
  - `400`: the server will not process the request because of a perceived client error.
  - `404`: the server found no current representation of the target resource.
  - `409`: the request conflicts with the current state of the resource.
  - `422`: the server understood the content but could not process its instructions.
  - `500`: an unexpected condition stopped the server from fulfilling the request.
- **Retries (RFC 9110):** PUT, DELETE and the safe methods are idempotent. POST is not listed, and clients should not automatically retry a non-idempotent request unless they know it is safe to repeat.
- **Error bodies (RFC 9457):** the media type is `application/problem+json`, with the members `type`, `title`, `status`, `detail` and `instance`. The RFC advises against exposing implementation details such as stack dumps.
- **Idempotency errors (IETF draft):** the draft is still an Internet-Draft, so it could change. It recommends `400` for a missing key, `422` for a key reused with a different payload, and `409` for a retry while the original is still processing.

### Measured FastAPI defaults

The test endpoint used a required `Idempotency-Key` header, a positive `StrictInt` amount and a UUID wallet ID.

| Request | Status | Default body |
| --- | --- | --- |
| Valid transfer | `201` | The endpoint's JSON |
| Missing idempotency key | `422` | `detail` list |
| Amount of `-5`, `10.5` or `"10"` | `422` | `detail` list, echoing the rejected `input` |
| Malformed JSON | `422` | `detail` list |
| Malformed wallet ID | `422` | `detail` list, echoing the rejected `input` |
| Unknown wallet, using `HTTPException` | `404` | `{"detail": "Wallet not found"}` |
| Wrong method | `405` | `{"detail": "Method Not Allowed"}` |
| Unhandled exception | `500` | Plain text `Internal Server Error`, with no exception text |

## Relevance to Coinfidential

These are my recommendations. The brief requires the behaviors, but does not set these status codes.

| Scenario | Recommended status | Basis |
| --- | --- | --- |
| Transfer created | `201` | Measured default for the test endpoint |
| Retry with the same key and payload | The original response | Inference from [[FR-2]]: the retry must not move money twice |
| Missing idempotency key | `400` | IETF draft. Needs custom handling, as FastAPI returns `422` |
| Same key, different payload | `422` | IETF draft |
| Original request still processing | `409` | IETF draft |
| Negative, fractional or string amount | `422` | FastAPI default |
| Malformed wallet ID | `422` | FastAPI default |
| Unknown wallet | `404` | RFC 9110 |
| Insufficient funds | `409` | Inference: the request is valid but conflicts with the current balance. Some APIs use `422`, so this needs a decision |
| Reconciliation finds a mismatch | `200` with the result in the body | Inference: the scan itself succeeded |
| Unexpected failure | `500`, rolled back, with no internals | RFC 9457 security guidance and FR-3's accuracy goal |

- **Use one error format everywhere.** FastAPI's `detail` list, `detail` string and plain-text `500` are three different shapes. Custom handlers for `RequestValidationError`, Starlette's `HTTPException` and unhandled exceptions could return RFC 9457 bodies. FastAPI's documentation says to register the handler on Starlette's class so internal errors are covered too.
- **Do not echo input by default.** The measured validation errors return the rejected value, and the FastAPI documentation warns about leaking system details. This is low risk for an amount, but a custom handler avoids it for every field.
- **Test the status codes.** The table gives [[TQ-4]] a concrete list of negative tests, and each code must also leave balances unchanged.

## Requirements

- [[FR-2]]: POST is not idempotent, so the required idempotency key provides the retry protection.
- [[FR-5]]: A reconciliation mismatch needs a defined response.
- [[TQ-3]]: End-to-end tests can assert these status codes for each FR.
- [[TQ-4]]: Covers insufficient funds, invalid idempotency payloads and malformed IDs.
- [[SE-3]]: The error format and status code choices belong in an ADR.
- [[SE-7]]: API documentation (OpenAPI) must describe these error responses.

## Related notes

- [[integer-minor-units-money-math]]: Explains why amounts must be rejected unless they are strict integers.
- [[double-entry-bookkeeping-principles]]: Explains why a duplicated transfer cannot be caught later by reconciliation.
- [[stage1-ai-session-setup]]: Records the session that produced this note.

## Open questions

- Should insufficient funds return `409` or `422`?
- Should Coinfidential adopt RFC 9457 fully, or use a simpler consistent error format? RFC 9457 adds work for a course project, but gives a documented standard.
- How long should idempotency keys be stored? The brief does not say.
- Should malformed JSON return `400`? RFC 9110's definition fits it, but FastAPI returns `422` by default.
