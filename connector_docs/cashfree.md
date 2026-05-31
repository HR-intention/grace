## Connector Information

- **Connector Name:** Cashfree Payment Gateway
- **Base URLs:**
  - Sandbox: `https://sandbox.cashfree.com/pg`
  - Production: `https://api.cashfree.com/pg`
- **Subscriptions Base URLs:**
  - Sandbox: `https://sandbox.cashfree.com/pg/subscriptions`
  - Production: `https://api.cashfree.com/pg/subscriptions`
- **Authentication Headers:**
  - `x-client-id`: Client app ID
  - `x-client-secret`: Client secret key
  - `x-api-version`: API version (e.g. `2025-01-01`)
  - `Content-Type`: `application/json`
- **Idempotency:** Forward `idempotency_key` as the `x-idempotency-key` request header on all state-changing calls.

---

## Shared — failure free-text → (PaymentFailureCode, FailureClass)

Cashfree `failure_details.failure_reason` is free text. Map on **substring match** (case-insensitive,
first match wins). Default: `UNKNOWN` (preserve raw text in `failure_reason`).

`FAILURE_CLASS` is **published data only** — lens never branches on it. The connector sets
`MandateDebitOutcome.failure_code`; orbit reads `FAILURE_CLASS[code]`. Never redeclare `FailureClass`
or `FAILURE_CLASS` in the generated connector.

| Signal (substring in `failure_reason`) | `PaymentFailureCode` | `FailureClass` |
|---|---|---|
| `insufficient funds` | `INSUFFICIENT_FUNDS` | `RETRIABLE` |
| `network` / `timeout` | `NETWORK_ERROR` | `RETRIABLE` |
| `psp` / `system error` | `PSP_ERROR` | `RETRIABLE` |
| `card declined` | `CARD_DECLINED` | `TERMINAL` |
| `invalid instrument` | `INVALID_INSTRUMENT` | `TERMINAL` |
| `mandate revoked` | `MANDATE_REVOKED` | `TERMINAL` |
| `mandate paused` | `MANDATE_PAUSED` | `TERMINAL` |
| `mandate expired` | `MANDATE_EXPIRED` | `TERMINAL` |
| `mandate not found` / `subscription not found` | `MANDATE_NOT_FOUND` | `TERMINAL` |
| `amount exceeds cap` | `DEBIT_LIMIT_EXCEEDED` | `TERMINAL` |
| (unmatched) | `UNKNOWN` (raw in `failure_reason`) | — |

---

## Subscriptions — `subscription_status` → `MandateStatus`

| Cashfree `subscription_status` | `MandateStatus` |
|---|---|
| `INITIALIZED`, `BANK_APPROVAL_PENDING` | `PENDING_AUTHORIZATION` |
| `ACTIVE` | `ACTIVE` |
| `PAUSED` (merchant), `CUSTOMER_PAUSED` (customer) | `PAUSED` |
| `ON_HOLD` | `SUSPENDED` |
| `COMPLETED` | `COMPLETED` |
| `CANCELLED`, `CUSTOMER_CANCELLED` | `CANCELLED` |
| `EXPIRED` | `EXPIRED` |
| `CARD_EXPIRED` | `SUSPENDED` (instrument dead; needs re-auth) |
| `LINK_EXPIRED` | `FAILED` (auth link lapsed pre-approval) |
| auth `FAILED` (on `SUBSCRIPTION_AUTH_STATUS`) | `FAILED` |

---

## Subscriptions — event → `WebhookEventType`

| Cashfree event (condition) | `WebhookEventType` | Notes |
|---|---|---|
| `SUBSCRIPTION_AUTH_STATUS` (authorization_status=`ACTIVE`) | `MANDATE_AUTHORIZED` | |
| `SUBSCRIPTION_AUTH_STATUS` (`FAILED`) | `MANDATE_REJECTED` | |
| `SUBSCRIPTION_PAYMENT_SUCCESS` | `MANDATE_DEBIT_SUCCESS` | |
| `SUBSCRIPTION_PAYMENT_FAILED` | `MANDATE_DEBIT_FAILED` | `psp_attempt = retry_attempts` from payload |
| `SUBSCRIPTION_PAYMENT_CANCELLED` | `MANDATE_DEBIT_FAILED` | `failure_code = USER_CANCELLED` |
| `SUBSCRIPTION_PAYMENT_NOTIFICATION_INITIATED` | `MANDATE_DEBIT_NOTIFIED` | orbit accepted — emit |
| `SUBSCRIPTION_STATUS_CHANGED` → `ACTIVE` (from paused) | `MANDATE_RESUMED` | |
| `SUBSCRIPTION_STATUS_CHANGED` → `CUSTOMER_PAUSED` | `MANDATE_PAUSED` | |
| `SUBSCRIPTION_STATUS_CHANGED` → `ON_HOLD` | `MANDATE_SUSPENDED` | |
| `SUBSCRIPTION_STATUS_CHANGED` → `CANCELLED` | `MANDATE_CANCELLED` | |
| `SUBSCRIPTION_STATUS_CHANGED` → `CUSTOMER_CANCELLED` | `MANDATE_REVOKED` | |
| `SUBSCRIPTION_STATUS_CHANGED` → `EXPIRED` / `CARD_EXPIRED` | `MANDATE_EXPIRED` | |
| `SUBSCRIPTION_STATUS_CHANGED` → `COMPLETED` | `MANDATE_COMPLETED` | |
| `SUBSCRIPTION_CARD_EXPIRY_REMINDER` | `MANDATE_EXPIRING_SOON` | orbit accepted — emit |
| `SUBSCRIPTION_REFUND_STATUS` | reuse refund handling | out of core mandate scope |

> **No `*_FAILED_FINAL` event.** There is no Cashfree "retries-exhausted / final-failure" event.
> Finality is derived by the consumer from `MANDATE_SUSPENDED` (← `ON_HOLD`) + `psp_attempt`.
> Do **not** synthesize a `*_FAILED_FINAL` event.
>
> `ON_HOLD` is **payment-failure-only** (merchant/customer pauses are `PAUSED`/`CUSTOMER_PAUSED`),
> so `MANDATE_SUSPENDED` unambiguously means a payment-failure suspension — no reason field exists
> or is needed. Documented for NACH + Card SI; **normalize UPI_AUTOPAY debit failure to
> `MANDATE_SUSPENDED` too** (confirm the exact UPI path in sandbox — open L9 item).

---

## Subscriptions — rail → `payment_methods`

| `MandateRail` | Cashfree `authorization_details.payment_methods` |
|---|---|
| `UPI_AUTOPAY` | `[upi]` |
| `CARD_EMANDATE` | `[card]` |

eNACH/pNACH bank rails are out of scope this phase.

---

## Subscriptions — create-request field map

Maps `CreateSubscriptionRequest` lens fields to Cashfree Subscriptions API fields.

| lens field | Cashfree field | Notes |
|---|---|---|
| `amount` (`Amount`) | `plan_details.plan_recurring_amount` | |
| `max_amount` (`Amount`) | `plan_details.plan_max_amount` | |
| `interval_type` | `plan_interval_type` | |
| `interval_count` | `plan_intervals` | |
| `max_cycles` | `plan_max_cycles` | |
| `first_charge_at` | `subscription_first_charge_time` | PERIODIC mode only |
| `expires_at` | `subscription_expiry_time` | |
| `customer_contact.email` | `customer_details.customer_email` | required |
| `customer_contact.phone` | `customer_details.customer_phone` | required |
| `return_url` | `subscription_meta.return_url` | |
| (notification) | `subscription_meta.notification_channel = [SMS, EMAIL]` | always set both |
| `rail` | `authorization_details.payment_methods` | via rail → payment_methods table above |
| `idempotency_key` | Cashfree idempotency token header (`x-idempotency-key`) | |
| `ManageMandateRequest.effective_at` (resume) | `action_details.next_scheduled_time` | resume = ACTIVATE verb |
