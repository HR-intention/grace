> ## Documentation Index
> Fetch the complete documentation index at: https://www.cashfree.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# Webhook Idempotency

> Learn how to handle duplicate webhook events and terminal payment statuses in a reliable way.

When integrating with Cashfree Payment Gateway, it's crucial to implement webhook idempotency to ensure your application processes only final and unique payment events. Below are the core principles and practices to follow.

## Key concepts

The following are the key concepts:

* **Multiple payment attempts per order\_id**: For a single `order_id`, Cashfree allows multiple payment attempts until one succeeds. Each attempt generates a unique `cf_payment_id`.

* **Unique payment\_id per attempt**: Every retry—whether triggered by the user or automatically—will have a distinct `cf_payment_id` but the same `order_id`.

* **Terminal status**: Only consider webhook events where `payment_status = SUCCESS` as the final confirmation of payment for an order.

<Note> Statuses such as `FAILED`, `NOT_ATTEMPTED`, or `PENDING` are transitional and should not be treated as final.</Note>

<Frame caption="Webhook idempotency flowchart">
  <img src="https://mintcdn.com/cashfreepayments-d00050e9/3p7irhmTjRVwqRH8/static/payments/online/mobile/webhook-idempotency-flow.png?fit=max&auto=format&n=3p7irhmTjRVwqRH8&q=85&s=49fe6cfd137bc140d9c49b4c03693d2e" width="993" height="721" data-path="static/payments/online/mobile/webhook-idempotency-flow.png" />
</Frame>

## Best practices

The following are the recommended best practices:

* **De-duplicate using payment\_id**: Track `cf_payment_id` in your database and ensure it is processed only once, regardless of how many webhook retries you receive.

* **Order-level validation**: Update the order status **only when** you receive a webhook that meets **all** of the following conditions:
  * The `order_id` matches the one you created.
  * The `payment_status` is `SUCCESS`.
  * The order has **not already** been marked as paid.

* **Handle retried payments**: Users may retry failed payments. As a result, you may receive multiple webhook events in the sequence: `FAILED → PENDING → SUCCESS`.\
  Implement logic to update the order status only upon receiving the `SUCCESS` webhook.

* **Ignore duplicate FAILED webhooks**: Webhook events with a `FAILED` status may be sent multiple times. Do not trigger any final actions for these statuses unless you are tracking them for logging or metrics.

* **Store payment attempts**: Keep a log of all `cf_payment_id` for a given `order_id` to support reporting, reconciliation, or dispute management.

<Note>
  Do not mark the order as PAID on receiving `FAILED` or `PENDING` statuses.
  Always wait for a `SUCCESS` webhook before finalising the payment status.
</Note>
