> ## Documentation Index
> Fetch the complete documentation index at: https://www.cashfree.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# Troubleshooting

## Webhook did not trigger

If a webhook does not trigger for the specified endpoint:

1. Log in to the [Merchant Dashboard](https://merchant.cashfree.com/auth/login).

2. Navigate to **Developer > Webhooks** under **Payment Gateway**, and select the **Logs** tab to check for failures and take necessary action.
   Common reasons for webhook failure are:
   * The endpoint returns a **500 error** or does not respond.
   * The required event is not configured in the webhook settings.

3. Select **Batch Resend** to resend missed webhook events.

4. Select the **Batch Source** and enter **Entity IDs** in the **Batch Resend** modal.

5. Select **Resend**. Refer to the screenshot below:

<img height="200" noZoom src="https://mintcdn.com/cashfreepayments-d00050e9/tSdE45xBW33wuhXy/static/payments/webhook/pg-webhook-1.png?fit=max&auto=format&n=tSdE45xBW33wuhXy&q=85&s=724360f8544793aa6dc3098006b5f17b" data-path="static/payments/webhook/pg-webhook-1.png" />

## Cannot add a payment gateway webhook

To add a webhook endpoint URL:

1. Log in to the [Merchant Dashboard](https://merchant.cashfree.com/auth/login).

2. Navigate to **Developer > Webhooks** under **Payment Gateway**, and select **Add Webhook Endpoint** in the **Configuration** tab.

3. Add the following details in the **Add Webhook Endpoint** modal:

   * **Endpoint Details**: Enter the endpoint URL for the webhook and select the latest webhook version from the drop-down list.

   <Note>
     **Note**:
     When you add the endpoint URL, Cashfree sends a test `POST` request to check if it is valid and responsive. If the endpoint does not respond, select **Continue** and manually select the required events.
   </Note>

   * **Add Policy**: Customise the retry policy and select the webhook events you want to subscribe to.
   * **Summary**: Review and confirm your selections.

4. Select **Save** to complete the setup.  Refer to the screenshot below:

<img height="200" noZoom src="https://mintcdn.com/cashfreepayments-d00050e9/tSdE45xBW33wuhXy/static/payments/webhook/pg-webhook-2.png?fit=max&auto=format&n=tSdE45xBW33wuhXy&q=85&s=df033f00f3c74af7e4aa0e5433b4db2a" data-path="static/payments/webhook/pg-webhook-2.png" />

## Receiving duplicate webhook events

If you receive duplicate webhook events, check for the following issues:

* **Multiple subscriptions to the same event**
  * You may have subscribed to the same event multiple times across different webhook versions or for different URLs.
  * Check each **URL Configuration** and remove duplicate subscriptions.

* **Retries due to downtime**
  * If **Cashfree Payments** or your server experiences downtime, Cashfree retries webhook deliveries to ensure event completion.

* **Prevent duplicate processing**
  * Validate the **x-idempotency-header** in the webhook header.
    * This header contains a unique hashed value for each webhook payload.
    * Webhook versions from **2025-01-01** support this feature.
    * To upgrade, see the [Webhook Migration](/payments/online/webhooks/overview#webhook-migration) section.

## Configure webhooks for non-payment gateway products

To configure webhooks for products such as **Payouts**, **Subscriptions**, **Payments**, **Payment Links**, or **Secure ID**, go to the respective product webhook section on the Merchant Dashboard and add the required webhook endpoint URL.

<img height="200" noZoom src="https://mintcdn.com/cashfreepayments-d00050e9/tSdE45xBW33wuhXy/static/payments/webhook/pg-webhook-3.png?fit=max&auto=format&n=tSdE45xBW33wuhXy&q=85&s=5a12363d0d5a876e0395243fff7b54ea" data-path="static/payments/webhook/pg-webhook-3.png" />

<div class="hidden" data-table-of-contents="bottom">
  <p class="mt-4 font-medium flex items-center gap-2 related-docs-heading">
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" class="w-4 h-4">
      <path d="M3 4h7a2 2 0 0 1 2 2v13a2 2 0 0 0-2-2H3z" />

      <path d="M21 4h-7a2 2 0 0 0-2 2v13a2 2 0 0 1 2-2h7z" />
    </svg>

    <span>Related topics</span>
  </p>

  <ul>
    <li><a href="/docs/payments/online/webhooks/security-checklist">Webhook Security Checklist</a></li>
    <li><a href="/docs/payments/online/webhooks/overview">Webhooks Overview</a></li>
    <li><a href="/docs/payments/online/webhooks/configure">Webhook Configuration</a></li>
  </ul>
</div>
