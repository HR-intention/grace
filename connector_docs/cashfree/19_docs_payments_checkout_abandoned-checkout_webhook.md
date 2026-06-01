> ## Documentation Index
> Fetch the complete documentation index at: https://www.cashfree.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# Abandoned Checkout Webhook

Cashfree One Click Checkout (OCC) webhooks notify business service providers (BSPs) in real time when customers create abandoned carts. BSPs can add their webhook URLs to receive these events.

If a customer drops off during checkout and provides a phone number or email address, Cashfree OCC creates an abandoned cart record in both Shopify and the Cashfree system. Merchants can use this data to retarget users.

Abandoned cart records include:

* **Customer details:** Phone number, email address, or both

* **Address details:** Pincode, state, and other information. The address is included only if the customer submits the complete address.

* **Cart details:** Always included

* **OCC URL:** Link to the merchant’s Shopify store with the OCC page preloaded

Cashfree OCC triggers webhooks only for abandoned carts, not for completed checkouts. Once a BSP adds a webhook URL, it begins receiving events.
To enable this, merchants must ask the BSP to share the webhook URL where Cashfree should send data.

<Note>
  Cashfree doesn't send abandoned checkouts to Shopify if a login is required in the native checkout settings.
</Note>

## Adding a webhook endpoint

To start receiving abandoned cart webhooks from Cashfree One Click Checkout (OCC), follow these steps:

1. Log in to the **[Merchant Dashboard](https://merchant.cashfree.com/auth/login)**.

2. Go to **Payment Gateway > Developers > Webhooks > Configuration > Payment Gateway** tab.

3. On the **Webhooks** page, click **Add Webhook Endpoints**.

4. In the **Endpoint Details** section:
   * Enter the **endpoint URL** where you want to receive webhook data.
   * Click **Test** to verify the URL.
   * From the drop-down menu, select **Webhook Version: 2025-01-01**.
   * Click **Continue**.

5. In the **Add Policy** section:
   * Choose a **retry policy**. The default policy includes **3 retries**.
   * Select the relevant **events** to subscribe to.
   * Optionally, add another **retry policy** if needed.
   * Click **Continue**.

6. In the **Summary** section:
   * Review the configuration.
   * Click **Update Secret Key**, then click **Update** in the confirmation pop-up.
   * Click **Save**.

<iframe width="560" height="315" src="https://www.youtube.com/embed/mj_ccisbCZI?si=kfLRBnCvUBpBzdnE&enablejsapi=1" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen />

## Sample webhook event payload

Below is a sample webhook event payload for an abandoned cart.

<Note>
  Use the signature to verify that the request has not been tampered with. To verify the signature, use your merchant secret key along with the payload.
</Note>

```json theme={"dark"}
{
  "cartId": 75355,
  "storeUrl": "test-mihir-1.myshopify.com",
  "platform": null,
  "cartToken": "Z2NwLWFzaWEtc291dGhlYXN0MTowMUpXRVgyWlJQSFpRRk42SDBCRkFaME1XMA?key=2fee923b8bebe7ecccfad7afd75e7a34",
  "email": "darpxxxxx[at]xxxx[dot]xom",
  "phone": "+91 6000376569",
  "abandonedCheckoutUrl": "https://sandbox.cashfree.com/pg/view/sessions/checkout/web/g63eHoiIayRccLzTvGPX",
  "originalTotalPrice": 2000.0,
  "totalPrice": 1800.0,
  "totalDiscount": 200.0,
  "utmParameters": {
    "fbclid": "",
    "utm_campaign": "",
    "utm_medium": "",
    "utm_content": "",
    "utm_source": ""
  },
  "lineItems": [
    {
      "reference": 8181897822385,
      "variantId": 45515259445425,
      "skuName": "",
      "name": "Jordans - Black",
      "description": "",
      "detailsUrlStr": "",
      "imageUrlStr": "https://cdn.shopify.com/s/files/1/0628/9037/7393/files/1.webp?v=1732785645",
      "imageS3UrlStr": "https://cashfree-checkoutcartimages-gamma.cashfree.com/2193502202/checkoutcartitem1",
      "originalPrice": 500.0,
      "discountedPrice": 400.0,
      "currency": "INR",
      "quantity": 2,
      "discounts": [
        {
          "title": "SHOE_AUTOMATIC",
          "description": "",
          "type": "FIXED",
          "value": 200
        }
      ]
    },
    {
      "reference": 8352793428145,
      "variantId": 45538243870897,
      "skuName": "",
      "name": "bundle 2 - Black / L / Mock",
      "description": "",
      "detailsUrlStr": "",
      "imageUrlStr": "",
      "imageS3UrlStr": "https://cashfree-checkoutcartimages-gamma.cashfree.com/2193502202/checkoutcartitem2",
      "originalPrice": 1000.0,
      "discountedPrice": 1000.0,
      "currency": "INR",
      "quantity": 1,
      "discounts": []
    }
  ],
  "promotions": [
    {
      "code": "SHOE_AUTOMATIC",
      "value": 200
    }
  ],
  "customer": {
    "email": "darpxxxxx[at]xxxx[dot]xom",
    "firstName": "Darpan",
    "lastName": "Deka",
    "shippingAddress": {
      "customerName": "Darpan Deka",
      "address1": "Rangia, Murara",
      "address2": "",
      "city": "Rangia",
      "province": "Assam",
      "country": "India",
      "zip": "781354",
      "email": "XXXXXXXXXXXXXXXXXXXX",
      "phone": "XXXXXXXXXXXXXXXXXXXX",
      "name": null,
      "provinceCode": "AS",
      "countryCode": "IN"
    }
  }
}
```

## Webhook headers

Each webhook request contains the following headers for validation and tracing:

| **Header key**                | **Description**                                                              |
| ----------------------------- | ---------------------------------------------------------------------------- |
| `x-datadog-sampling-priority` | Indicates trace sampling priority. A value of 1 means the trace is retained. |
| `x-datadog-parent-id`         | ID of the parent span in a distributed trace.                                |
| `x-datadog-trace-id`          | Unique ID for the trace across services.                                     |
| `content-length`              | Size of the request body in bytes.                                           |
| `x-webhook-attempt`           | Number of delivery attempts.                                                 |
| `content-type`                | MIME type of the request body (`application/json`).                          |
| `x-webhook-signature`         | Cryptographic signature for payload integrity.                               |
| `x-idempotency-key`           | Unique key to prevent duplicate processing.                                  |
| `x-webhook-timestamp`         | Unix timestamp (in milliseconds) indicating when the webhook was sent.       |
| `x-webhook-version`           | Version of the webhook payload (e.g., `2025-01-01`).                         |
| `accept`                      | Acceptable media types in the response (`*/*`).                              |
| `host`                        | Receiving server domain (e.g., `webhook.site`).                              |
| `user-agent`                  | Client software sending the request (e.g., `ReactorNetty/1.1.11`).           |
