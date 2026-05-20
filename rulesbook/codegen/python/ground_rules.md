# Ground rules (non-negotiable)

These rules are inherited verbatim from `SUBPROJECT_LENS.md` §3. **Violations fail the quality rubric.** No exceptions.

1. **Stateless library.** No database. No file I/O beyond httpx. No global mutable state except `ConnectorFactory._registry` (write-once at import).

2. **No HTTP server.** Pure Python library; never opens a listening socket.

3. **Async everywhere.** Every public method on `PaymentsFacade` and `Connector` is `async def`. CPU work via `asyncio.to_thread`.

4. **One class per PSP.** Each `Connector` subclass implements all four flow methods + `handle_webhook` + `close`. No per-(PSP × Flow) class splits.

5. **Each Connector owns its httpx client.** Created in `__init__`, closed in `close()`. Configured with timeouts, retries, and a structured-logging event hook. Tests pass `httpx.MockTransport` at construction.

6. **No business logic in Connectors.** A Connector's job is: take a domain request, build the PSP-shaped HTTP request, call the PSP, parse the response into a domain response, return it. Business decisions (state transitions on Orders, idempotency dedup, ledger updates) belong to Orbit.

7. **Hosted-checkout only in v1.** Connectors never receive raw card numbers, UPI VPAs, or wallet IDs. `PaymentMethod` is an allow-list constraint passed to the PSP and a value read back; not a per-method request builder.

8. **Pydantic v2 at every boundary.** Requests are `frozen=True`, responses `frozen=False`. All models use `extra="forbid"`.

9. **`mypy --strict` mandatory.** No `Any`. Every public function annotated.

10. **All money is integer minor units at our boundaries.** No floats in our domain types, no floats in our DB schemas, no floats on our public surface. PSP wire-level transformations (where a specific PSP's API takes a different unit, e.g., rupees-as-string with two decimal places) may use `decimal.Decimal` *inside* the connector method to format the request — but the Decimal value never escapes back into our domain types. Example: `Decimal(amount.minor_units) / 100` is fine when building a Cashfree request body; the response's `paid_amount` field on `PaymentAttempt` is always `int`.

11. **PII through `Maskable[T]`.** Any secret-bearing field is typed `Maskable[str]`. `expose()` is the only way to read.

12. **All errors are `ConnectorError`.** PSP-specific exceptions are caught and translated inside the Connector method.

13. **Idempotency keys pass through, never persist.** Lens forwards the caller-supplied key to the PSP. Dedup is Orbit's job.

14. **Webhook = verify + parse, nothing else.** `Connector.handle_webhook` verifies the signature, parses the body into a `WebhookEvent` (with `attempt` or `refund` populated), returns it.

15. **The `__init__.py` in each `connectors/<psp>/` package self-registers with `ConnectorFactory` on import.**

16. **Map all PSP-specific outcome terms into the locked `PaymentFailureCode` taxonomy.** PSPs use varying vocabulary (`USER_DROPPED`, `NOT_ATTEMPTED`, `cancelled_by_user`, `payment_did_not_complete`, …). Each Connector translates them to our taxonomy. If no value fits, use `UNKNOWN` and capture the PSP-original in `failure_reason`.
