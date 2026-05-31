> ## Documentation Index
> Fetch the complete documentation index at: https://www.cashfree.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# Configuration

> Configure Cashfree webhooks for Payment Gateway, Payment Links, Forms, and Subscriptions to receive event notifications, view logs, and set alerts.

Add and define webhooks for Payment Gateway, Payment Links, Payment Forms, and Subscriptions. Get notified for each action on the URLs you configure.

## Add a webhook endpoint

To add a new webhook:

1. Log in to the [Merchant Dashboard](https://merchant.cashfree.com/auth/login).
2. Go to **Payment Gateway** > **Developers** or select **Developers** from the homepage.
3. Select **Add Webhook Endpoint** to create a new webhook. Enter the endpoint URL and select the webhook version from the drop-down menu. The available webhook versions are **2022-09-01**, **2023-08-01**, and **2025-01-01**.
4. Select **Test** to verify if the webhook endpoint returns a response and select **Next**.

<Note>
  In the sandbox environment, both http\:// and https\:// endpoints are supported. In the production environment, only https\:// endpoints are supported.
</Note>

5. Select the events for which you want to configure the webhooks and select **Add Webhook**.

<Accordion title="View available webhook events">
  * Dispute Closed
  * Dispute Created
  * Dispute Updated
  * Failed Payment
  * Incident
  * Instrument Active
  * Instrument Failed
  * Refund
  * Settlement Failed
  * Settlement Initiated
  * Settlement Reversed
  * Success Payment
  * Success Payment TDR
  * User Dropped Payment
  * Vendor Settlement Failed
  * Vendor Settlement Initiated
  * Vendor Settlement Reversed
  * Vendor Settlement Success
</Accordion>

<Frame caption="">
  <img src="https://mintcdn.com/cashfreepayments-d00050e9/nQAlY3LNUrZl-7GM/static/images/pg/adding-webhook.gif?s=898e51c359719a998e3336bdf1373401" width="1913" height="1080" data-path="static/images/pg/adding-webhook.gif" />
</Frame>

You have successfully created a webhook for the required event. You can view all your webhooks from the **Webhook Endpoints** homepage. Details such as **URL**, **Webhook Version**, **Event**, and **Actions** are available.

## Test a webhook endpoint

You can test the URL at any time using the **Test** option.

1. Select **Test** on the webhook you want to verify.
2. In the **Test Webhook Endpoint** pop-up, select **Test**.
3. Select **Done** after you receive a success response.

<Frame caption="Test a webhook endpoint">
  <img src="https://mintcdn.com/cashfreepayments-d00050e9/S5p7bMVVv5fcWVIF/static/images/pg/pgwebhook-4.png?fit=max&auto=format&n=S5p7bMVVv5fcWVIF&q=85&s=d5fb5af3cd8f2016a7776953c3d5f791" width="700" data-path="static/images/pg/pgwebhook-4.png" />
</Frame>

## Edit a webhook endpoint

To edit a webhook:

1. Select **Edit** on the webhook you want to modify.
2. Select the events you want to add or remove.
3. Select **Save**.

<Frame caption="Edit a webhook endpoint">
  <img src="https://mintcdn.com/cashfreepayments-d00050e9/S5p7bMVVv5fcWVIF/static/images/pg/pgwebhook-5.png?fit=max&auto=format&n=S5p7bMVVv5fcWVIF&q=85&s=2bec55cfb58bbf1f61870d07695ecc3d" width="700" data-path="static/images/pg/pgwebhook-5.png" />
</Frame>

## Logs

The **Logs** section displays all webhook logs (successful or failed) on your dashboard.

<Frame caption="">
  <img src="https://mintcdn.com/cashfreepayments-d00050e9/S5p7bMVVv5fcWVIF/static/images/pg/pgwebhook-6.png?fit=max&auto=format&n=S5p7bMVVv5fcWVIF&q=85&s=f0fbfd03a92dbfa1f7d80a24c08bc727" width="2848" height="1612" data-path="static/images/pg/pgwebhook-6.png" />
</Frame>

To view logs:

1. Specify the date range to view logs for a particular period.
2. Use the **Search and Filter** option to view specific logs. Enter the **URL** and select the required webhook type from the drop-down menu.
3. Select a request to view details such as **Message**, **Time**, **Version**, **Header Details**, and **Payload**.
4. To view only **Success** or **Failed** logs, navigate to the respective tabs.

Watch the video below to learn how logs work.

<iframe width="600" height="400" src="https://app.supademo.com/embed/9epYKcBiRpBQxFlniI2Yj\" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen />

***

## Analytics

The webhook analytics feature provides contextual information on webhook metrics that help you track, monitor, and assess the success or failure of your webhooks. Metrics such as success rate and latency are available.

To view analytics:

1. Specify the date range to view metrics for a particular period.
2. Use the **Search and Filter** option to filter results. Enter the URL and select the required webhook type from the drop-down menu.

<Frame caption="Search and Filter">
  <img src="https://mintcdn.com/cashfreepayments-d00050e9/S5p7bMVVv5fcWVIF/static/images/pg/pgwebhook-10.png?fit=max&auto=format&n=S5p7bMVVv5fcWVIF&q=85&s=1b896f22001dba5c951e355bbdd2abcb" width="2862" height="1620" data-path="static/images/pg/pgwebhook-10.png" />
</Frame>

***

### Success rate

The success rate chart displays the webhook delivery status over time. The chart shows the following metrics:

* **Total Attempts**: The total number of webhook delivery attempts.
* **Successful**: The count of webhooks delivered successfully on the first attempt.
* **Retried Successful**: The count of webhooks that succeeded after retry attempts.
* **Failed**: The count of webhooks that failed to deliver.

Hover over individual bars to view the breakdown for a specific date.

### Latency

Latency is the time taken to respond to webhooks. Hover over individual bars to view the latency for a specific date. The average latency value is also displayed.

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
    <li><a href="/docs/payments/online/webhooks/signature-verification">Signature Verification</a></li>
  </ul>
</div>
