> ## Documentation Index
> Fetch the complete documentation index at: https://www.cashfree.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# Refund Webhooks

> Subscribe to Cashfree refund webhook events for successful refunds, cancelled refunds after retries, and automatic auto-refunds triggered for failed orders.

Webhooks are server callbacks to your server from Cashfree Payments. We send refund webhooks for three different events for a payment.

1. Refund is successfully processed
2. Refund is cancelled by Cashfree - we were unable to successfully refund to customer even after multiple attempts.
3. For successful Auto-refunds - Read more about Auto-Refunds [here](/payments/manage/refunds#auto-refunds)

## Refund webhook payload

<Tabs>
  <Tab title="Version (2025-01-01)">
    ```javascript Version 2025-01-01 theme={"dark"}
    {
    "data":{
        "refund":{
             "cf_refund_id":11325632,
             "cf_payment_id":789727431,
             "refund_id":"refund_sampleorder0413",
             "order_id":"sampleorder0413",
             "refund_amount":2.00,
             "refund_currency":"INR",
             "entity":"Refund",
             "refund_type":"MERCHANT_INITIATED",
             "refund_arn":"205907014017",
             "refund_status":"SUCCESS",
             "status_description":"Refund processed successfully",
             "created_at":"2022-02-28T12:54:25+05:30",
             "processed_at":"2022-02-28T13:04:27+05:30",
             "refund_note":"Test",
             "refund_splits":[
                {
                   "merchantVendorId":"sampleID12345",
                   "amount":1,
                   "percentage":null
                },
                {
                   "merchantVendorId":"otherVendor",
                   "amount":1,
                   "percentage":null
                }
             ],
             "metadata":null,
             "requested_speed":"STANDARD",
             "processed_speed":"STANDARD",
             "service_charge":0.00,
             "service_tax":0.00,
             "forex_conversion_handling_charge":null,
             "forex_conversion_handling_tax":null,
             "forex_conversion_rate":null,
             "charges_currency":null
          },
          terminalDetails:{
             "cf_terminal_id":17269,
             "terminal_phone":"8971520311"
          }
       },
       "event_time":"2022-02-28T13:04:28+05:30",
       "type":"REFUND_STATUS_WEBHOOK"
    }
    ```
  </Tab>

  <Tab title="Version (2023-08-01)">
    ```javascript Version 2023-08-01 theme={"dark"}
    {
    "data":{
        "refund":{
             "cf_refund_id":11325632,
             "cf_payment_id":789727431,
             "refund_id":"refund_sampleorder0413",
             "order_id":"sampleorder0413",
             "refund_amount":2.00,
             "refund_currency":"INR",
             "entity":"Refund",
             "refund_type":"MERCHANT_INITIATED",
             "refund_arn":"205907014017",
             "refund_status":"SUCCESS",
             "status_description":"Refund processed successfully",
             "created_at":"2022-02-28T12:54:25+05:30",
             "processed_at":"2022-02-28T13:04:27+05:30",
             "refund_note":"Test",
             "refund_splits":[
                {
                   "merchantVendorId":"sampleID12345",
                   "amount":1,
                   "percentage":null
                },
                {
                   "merchantVendorId":"otherVendor",
                   "amount":1,
                   "percentage":null
                }
             ],
             "metadata":null,
             "requested_speed":"STANDARD",
             "processed_speed":"STANDARD",
             "service_charge":0.00,
             "service_tax":0.00
        }
       },
       "event_time":"2022-02-28T13:04:28+05:30",
       "type":"REFUND_STATUS_WEBHOOK"
    }
    ```
  </Tab>
</Tabs>

## Auto refund webhook payload

Auto-refund webhooks differ from standard refund webhooks because they handle refunds that occur automatically (like failed payment attempts) rather than manual refunds tied to specific orders. Since these automatic refunds may happen before an order is created, they don't contain the usual order-related data fields that are mandatory in standard refund webhooks,

<Tabs>
  <Tab title="Version 2025-01-01">
    ```javascript Version 2025-01-01 theme={"dark"}
    {
      "data": {
        "auto_refund": {
          "event": "AUTO-REFUND",
          "cf_refund_id": 1243460973,
          "cf_payment_id": "2148333968",
          "bank_reference": "234928698581",
          "order_id": "order_1944392Tpba8y2fHcHVx0SwREojp51Jgr",
          "refund_amount": 39,
          "refund_currency": "INR",
          "refund_type": "PAYMENT_AUTO_REFUND",
          "refund_arn": "205907014017",
          "refund_status": "SUCCESS",
          "status_description": "Auto-Refund processed successfully",
          "refund_reason": "Multiple payments were performed against same order.",
          "created_at": "2023-08-11T14:08:28+05:30",
          "processed_at": null,
          "refund_charge": 0,
          "refund_splits": null,
          "metadata": null,
          "forex_conversion_handling_charge": null,
          "forex_conversion_handling_tax": null,
          "forex_conversion_rate": null,
          "charges_currency": null
        },
        terminalDetails:{
          "cf_terminal_id":17269,
          "terminal_phone":"8971520311"
        }
      },
      "event_time": "2023-08-11T14:10:21+05:30",
      "type": "AUTO_REFUND_STATUS_WEBHOOK"
    }
    ```
  </Tab>

  <Tab title="Version 2023-08-01">
    ```javascript Version 2023-08-01 theme={"dark"}
    {
      "data": {
        "auto_refund": {
          "event": "AUTO-REFUND",
          "cf_refund_id": 1243460973,
          "cf_payment_id": "2148333968",
          "bank_reference": "234928698581",
          "order_id": "order_1944392Tpba8y2fHcHVx0SwREojp51Jgr",
          "refund_amount": 39,
          "refund_currency": "INR",
          "refund_type": "PAYMENT_AUTO_REFUND",
          "refund_arn": "205907014017",
          "refund_status": "SUCCESS",
          "status_description": "Auto-Refund processed successfully",
          "refund_reason": "Multiple payments were performed against same order.",
          "created_at": "2023-08-11T14:08:28+05:30",
          "processed_at": null,
          "refund_charge": 0,
          "refund_splits": null,
          "metadata": null
        }
      },
      "event_time": "2023-08-11T14:10:21+05:30",
      "type": "AUTO_REFUND_STATUS_WEBHOOK"
    }
    ```
  </Tab>
</Tabs>
