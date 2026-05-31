> ## Documentation Index
> Fetch the complete documentation index at: https://www.cashfree.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# Payment Webhooks

> Read about all asynchronous events initiated by Cashfree for this entity

Webhooks are server callbacks from Cashfree Payments to your server. We send webhooks for three different events for a `payment`.

* Payment success webhook
* Payment failed webhook
* Payment user dropped webhook

## Webhook signature

The merchant will receive the Webhook signature in the Webhook Header part. Below is a sample header that merchants can expect in the Webhook request. For best practices on securing your webhook endpoints, refer to the [Webhook Security Checklist](/payments/online/webhooks/security-checklist).

<Tabs>
  <Tab title="Version (2025-01-01)">
    | Header name         |                 Header value                 |
    | ------------------- | :------------------------------------------: |
    | content-length      |                     1099                     |
    | x-webhook-attempt   |                       1                      |
    | content-type        |               application/json               |
    | x-webhook-signature | 07r5C3VMwsGYeldGOCYxe5zoHhIN1zLfa8O0U/yngHI= |
    | x-idempotency-key   | n9rn7079wqXcse3GEDEXCYle9ajXmU0SUQY8zrUNAlc= |
    | x-webhook-timestamp |                 1746427759733                |
    | x-webhook-version   |                  2025-01-01                  |
  </Tab>

  <Tab title="Version (2023-08-01)">
    | Header name         |                 Header value                 |
    | ------------------- | :------------------------------------------: |
    | content-length      |                     1002                     |
    | x-webhook-attempt   |                       1                      |
    | content-type        |               application/json               |
    | x-webhook-signature | 0s9zgYXyUYrQaadF5oTYzpxzHmPBMmGDSjbAKZTleL4= |
    | x-webhook-timestamp |                 1746426425612                |
    | x-webhook-version   |                  2023-08-01                  |
  </Tab>
</Tabs>

<Tip> Ensure that the webhook payload is received in raw text format. Converting the webhook into a JSON object can lead to automatic transformation of decimal values—such as the payment\_amount—into integers. This alteration (e.g., payment\_amount: 170 instead of payment\_amount: 170.00) can cause a webhook signature mismatch.<br /><br />**Correct format: payment\_amount: 170.00** ✅ <br />**Incorrect format: payment\_amount: 170** ❌</Tip>

## Payment success webhook

A payment success webhook is triggered when a payment is successfully completed. You can use this for: Updating order status, triggering fulfilment, and sending confirmation to the customer.

<Tabs>
  <Tab title="Version (2025-01-01)">
    ```javascript Version (2025-01-01) theme={"dark"}
    {
    "data":{
      "order":{
         "order_id":"order_OFR_2",
         "order_amount":2,
         "order_currency":"INR",
         "order_tags":null
      },
      "payment":{
         "cf_payment_id":"1453002795",
         "payment_status":"SUCCESS",
         "payment_amount":1,
         "payment_currency":"INR",
         "payment_message":"00::Transaction success",
         "payment_time":"2025-01-15T12:20:29+05:30",
         "bank_reference":"234928698581",
         "auth_id":null,
         "payment_method":{
            "upi":{
               "channel":"collect",
               "upi_id":"rishab@ybl",
               "upi_instrument":"UPI_CREDIT_CARD",
               "upi_instrument_number":"masked card number",
               "upi_payer_ifsc":"SBI0025434",
               "upi_payer_account_number":"XXXXX0231"
            }
         },
         "payment_group":"upi",
         "international_payment":{
            "international":false
         },
         "payment_surcharge":{
            "payment_surcharge_service_charge":0.36,
            "payment_surcharge_service_tax":0.06
         }
      },
      "customer_details":{
         "customer_name":null,
         "customer_id":"7112AAA812234",
         "customer_email":"test@gmail.com",
         "customer_phone":"9908734801"
      },
      "payment_gateway_details":{
         "gateway_name":"CASHFREE",
         "gateway_order_id":"1634766330",
         "gateway_payment_id":"1504280029",
         "gateway_order_reference_id":"abc_124",
         "gateway_settlement":"CASHFREE",
         "gateway_status_code":null
      },
      "payment_offers":[
         {
            "offer_id":"0f05e1d0-fbf8-4c9c-a1f0-814c7b2abdba",
            "offer_type":"DISCOUNT",
            "offer_meta":{
               "offer_title":"50% off on UPI",
               "offer_description":"50% off for testing",
               "offer_code":"UPI50",
               "offer_start_time":"2022-11-09T06:23:25.972Z",
               "offer_end_time":"2025-02-27T18:30:00Z"
            },
            "offer_redemption":{
               "redemption_status":"SUCCESS",
               "discount_amount":1,
               "cashback_amount":0
            }
         }
      ],
      "terminal_details":{
        "cf_terminal_id":17269,
        "terminal_phone":"8971520311"
      }
    },
    "event_time":"2025-01-15T11:16:10+05:30",
    "type":"PAYMENT_SUCCESS_WEBHOOK"
    }
    ```
  </Tab>

  <Tab title="Version (2023-08-01)">
    ```javascript Version (2023-08-01) theme={"dark"}
    {
    "data":{
      "order":{
         "order_id":"order_OFR_2",
         "order_amount":2,
         "order_currency":"INR",
         "order_tags":null
      },
      "payment":{
         "cf_payment_id":"1453002795",
         "payment_status":"SUCCESS",
         "payment_amount":1,
         "payment_currency":"INR",
         "payment_message":"00::Transaction success",
         "payment_time":"2022-12-15T12:20:29+05:30",
         "bank_reference":"234928698581",
         "auth_id":null,
         "payment_method":{
            "upi":{
               "channel":"collect",
               "upi_id":"suhasg6@ybl",
            }
         },
         "payment_group":"upi"
      },
      "customer_details":{
         "customer_name":null,
         "customer_id":"7112AAA812234",
         "customer_email":"test@gmail.com",
         "customer_phone":"9908734801"
      },
      "payment_gateway_details":{
         "gateway_name":"CASHFREE",
         "gateway_order_id":"1634766330",
         "gateway_payment_id":"1504280029",
         "gateway_order_reference_id":"abc_124",
         "gateway_settlement":"CASHFREE",
         "gateway_status_code":null
      },
      "payment_offers":[
         {
            "offer_id":"0f05e1d0-fbf8-4c9c-a1f0-814c7b2abdba",
            "offer_type":"DISCOUNT",
            "offer_meta":{
               "offer_title":"50% off on UPI",
               "offer_description":"50% off for testing",
               "offer_code":"UPI50",
               "offer_start_time":"2022-11-09T06:23:25.972Z",
               "offer_end_time":"2023-02-27T18:30:00Z"
            },
            "offer_redemption":{
               "redemption_status":"SUCCESS",
               "discount_amount":1,
               "cashback_amount":0
            }
         }
      ]
    },
    "event_time":"2023-08-01T11:16:10+05:30",
    "type":"PAYMENT_SUCCESS_WEBHOOK"
    }
    ```
  </Tab>
</Tabs>

## Payment failed webhook

The payment failed webhook notifies you when a payment attempt fails, and we receive a failed response from the bank. Use case: Update order status, notify customer, initiate retry flow

<Tabs>
  <Tab title="Version 2025-01-01">
    ```javascript Version 2025-01-01 theme={"dark"}
    {  
    "data": {  
        "order": {  
            "order_id": "CFPay_g47u3888d0k0_tblfm766qc",  
            "order_amount": 1.8,  
            "order_currency": "INR",  
            "order_tags": {  
                "cf_link_id": "13746255"  
            }  
        },  
        "payment": {  
            "cf_payment_id": "1504280029",  
            "payment_status": "FAILED",  
            "payment_amount": 1.8,  
            "payment_currency": "INR",  
            "payment_message": "AMOUNT SHOULD BE WITHIN RANGE BETWEEN 20.00 TO 500000.00.",  
            "payment_time": "2023-01-06T20:00:11+05:30",  
            "bank_reference": "NA",  
            "auth_id": "null",  
            "payment_method": {  
                "netbanking": {  
                    "channel": null,  
                    "netbanking_bank_code": "3054",  
                    "netbanking_bank_name": "UCO Bank"  
                }  
            },  
            "payment_group": "net_banking",
            "international_payment":{
                "international":false
            },
            "payment_surcharge":null
        },  
        "customer_details": {  
            "customer_name": null,  
            "customer_id": null,  
            "customer_email": "test@gmail.com",  
            "customer_phone": "9611199227"  
        },  
        "error_details": {  
            "error_code": "GATEWAY_ERROR",  
            "error_description": "AMOUNT SHOULD BE WITHIN RANGE BETWEEN 20.00 TO 500000.00. for this bank",  
            "error_reason": "invalid_amount",  
            "error_source": "cashfree",
            "error_subcode_raw": "U09"
        },  
        "payment_gateway_details": {
            "gateway_name": "CASHFREE",
            "gateway_order_id": "1634766330",
            "gateway_payment_id": "1504280029",
            "gateway_settlement": "CASHFREE",
            "gateway_status_code": null
        }, 
        "payment_offers": null,
        "terminal_details":{
            "cf_terminal_id":17269,
            "terminal_phone":"8971520311"
        }
    },  
    "event_time": "2023-08-01T20:00:12+05:30",  
    "type": "PAYMENT_FAILED_WEBHOOK"  
    }
    ```
  </Tab>

  <Tab title="Version 2023-08-01">
    ```javascript Version 2023-08-01 theme={"dark"}
    {
    "data": {
        "order": {
            "order_id": "CFPay_g47u3888d0k0_tblfm766qc",
            "order_amount": 1.8,
            "order_currency": "INR",
            "order_tags": {
                "cf_link_id": "13746255"
            }
        },
        "payment": {
            "cf_payment_id": "1504280029",
            "payment_status": "FAILED",
            "payment_amount": 1.8,
            "payment_currency": "INR",
            "payment_message": "AMOUNT SHOULD BE WITHIN RANGE BETWEEN 20.00 TO 500000.00.",
            "payment_time": "2023-01-06T20:00:11+05:30",
            "bank_reference": "NA",
            "auth_id": "null",
            "payment_method": {
                "netbanking": {
                    "channel": null,
                    "netbanking_bank_code": "3054",
                    "netbanking_bank_name": "UCO Bank"
                }
            },
            "payment_group": "net_banking"
        },
        "customer_details": {
            "customer_name": null,
            "customer_id": null,
            "customer_email": "test@gmail.com",
            "customer_phone": "9611199227"
        },
        "error_details": {
            "error_code": "GATEWAY_ERROR",
            "error_description": "AMOUNT SHOULD BE WITHIN RANGE BETWEEN 20.00 TO 500000.00. for this bank",
            "error_reason": "invalid_amount",
            "error_source": "cashfree",
            "error_subcode_raw": "U09"
        },
        "payment_gateway_details": {
            "gateway_name": "CASHFREE",
            "gateway_order_id": "1634766330",
            "gateway_payment_id": "1504280029",
            "gateway_settlement": "CASHFREE",
            "gateway_status_code": null
        },
        "payment_offers": null
    },
    "event_time": "2023-08-01T20:00:12+05:30",
    "type": "PAYMENT_FAILED_WEBHOOK"
    }
    ```
  </Tab>
</Tabs>

## Payment user dropped webhook

The User Dropped Webhook notifies you when your customer abandons the payment flow. It will help you understand if customers attempted to pay or not. Some common scenarios where the transaction will be marked as USER\_DROPPED are:

* User was redirected to the bank's OTP page, but never entered the OTP.
* User was redirected to open the UPI app, but never entered the UPI PIN.
* User was shown the 3ds OTP modal, but did not enter the OTP.

<Tabs>
  <Tab title="Version 2025-01-01">
    ```javascript Version 2025-01-01 theme={"dark"}
    {
    "data": {
    "order": {
      "order_id": "order_02",
      "order_amount": 2,
      "order_currency": "INR",
      "order_tags": null
    },
    "payment": {
      "cf_payment_id": "975672265",
      "payment_status": "USER_DROPPED",
      "payment_amount": 2,
      "payment_currency": "INR",
      "payment_message": "User dropped and did not complete the two factor authentication",
      "payment_time": "2022-05-25T14:25:34+05:30",
      "bank_reference": "1803592531",
      "auth_id": "2980",
      "payment_method": {
        "netbanking": {
          "channel": null,
          "netbanking_bank_code": "3044",
          "netbanking_bank_name": "State Bank Of India"
        }
      },
      "payment_group": "net_banking",
      "international_payment":{
        "international":false
      },
      "payment_surcharge":null
    },
    "customer_details": {
      "customer_name": null,
      "customer_id": "7112AAA812234",
      "customer_email": "test@gmail.com",
      "customer_phone": "9611199227"
    },
    "terminal_details":{
      "cf_terminal_id":17269,
      "terminal_phone":"8971520311"
    }
    },
    "event_time": "2022-05-25T14:35:38+05:30",
    "type": "PAYMENT_USER_DROPPED_WEBHOOK"
    }
    ```
  </Tab>

  <Tab title="Version 2023-08-01">
    ```javascript Version 2023-08-01 theme={"dark"}
    {
    "data": {
    "order": {
      "order_id": "order_02",
      "order_amount": 2,
      "order_currency": "INR",
      "order_tags": null
    },
    "payment": {
      "cf_payment_id": "975672265",
      "payment_status": "USER_DROPPED",
      "payment_amount": 2,
      "payment_currency": "INR",
      "payment_message": "User dropped and did not complete the two factor authentication",
      "payment_time": "2022-05-25T14:25:34+05:30",
      "bank_reference": "1803592531",
      "auth_id": "2980",
      "payment_method": {
        "netbanking": {
          "channel": null,
          "netbanking_bank_code": "3044",
          "netbanking_bank_name": "State Bank Of India"
        }
      },
      "payment_group": "net_banking"
    },
    "customer_details": {
      "customer_name": null,
      "customer_id": "7112AAA812234",
      "customer_email": "test@gmail.com",
      "customer_phone": "9611199227"
    }
    },
    "event_time": "2022-05-25T14:35:38+05:30",
    "type": "PAYMENT_USER_DROPPED_WEBHOOK"
    }
    ```
  </Tab>
</Tabs>

## Sample payload by payment method

The instrument used for making a payment will vary by the payment methods used by the customer. Details of the payload by payment method are documented for reference.

<Tabs>
  <Tab title="Card">
    ```javascript theme={"dark"}
    {
      ...,
      "payment_method": {  
        "card": {  
          "channel": "link",  
          "card_number": "XXXXXXXXXXXX4738",  
          "card_network": "visa",  
          "card_type": "credit_card",  
          "card_sub_type": "R",  
          "card_country": "IN",  
          "card_bank_name": "HDFC Bank",
          "card_network_reference_id": "100212023061200000001014824849",
          "instrument_id":"8e9cc167-4fe2-4ece-be8d-c1b224e50a23",
          "par": "V0010014623022637739353641436"
        }  
      },  
      "payment_group": "credit_card",
      ...
    }

    ```
  </Tab>

  <Tab title="Net Banking">
    ```javascript theme={"dark"}
    {
      ...,
      "payment_method": {  
        "netbanking": {  
          "channel":null,  
          "netbanking_bank_code":"3022",  
          "netbanking_bank_name":"ICICI Bank"  
        }  
      },  
      "payment_group":"net_banking",
      ...
    }

    ```
  </Tab>

  <Tab title="UPI">
    ```javascript theme={"dark"}
    {
      ...,
      "payment_method": {  
        "upi": {
                "channel": "collect",
                "upi_id": "rishabtated@ybl",
                "upi_instrument" : "UPI_CREDIT_CARD", 
                "upi_instrument_number" : "masked card number", 
                "upi_payer_ifsc" : "SBI0025434",
                "upi_payer_account_number" : "XXXXX0231"
            }  
      },
      "payment_group":"upi",
      ...
    }

    ```
  </Tab>

  <Tab title="Wallet">
    ```javascript theme={"dark"}
    {
      ...,
      "payment_method": {  
        "app": {  
          "channel":"AmazonPay",  
          "upi_id":null  
        }  
      },  
      "payment_group":"wallet",
      ...
    }

    ```
  </Tab>

  <Tab title="Credit Card EMI">
    ```javascript theme={"dark"}
    {
      ...,
      "payment_method":{  
        "card":{  
          "channel":null,  
          "card_number":"XXXXXXXXXX8952",  
          "card_network":null,  
          "card_type":"credit_card_emi",  
          "card_country":null,  
          "card_bank_name":"HDFC BANK",  
          "emi_details":{  
            "emi_amount":1167,  
            "emi_tenure":3,  
            "emi_interest":16.00  
          },
          "card_network_reference_id":null
        }  
      },  
      "payment_group":"credit_card_emi",
      ...
    }

    ```
  </Tab>

  <Tab title="Debit Card EMI">
    ```javascript theme={"dark"}
    {
      ...,
      "payment_method":{  
        "card":{  
          "channel":null,  
          "card_number":"XXXXXXXXXX8952",  
          "card_network":null,  
          "card_type":"debit_card_emi",  
          "card_country":null,  
          "card_bank_name":"HDFC BANK",  
          "emi_details":{  
            "emi_amount":1167,  
            "emi_tenure":3,  
            "emi_interest":16.00  
          }  
        }  
      },  
      "payment_group":"debit_card_emi",
      ...
    }

    ```
  </Tab>

  <Tab title="Cardless EMI">
    ```javascript theme={"dark"}
    {
      ...,
      "payment_method":{  
        "cardless_emi":{  
          "channel":null,  
          "provider":"flexmoney",  
          "phone":"9731117102",  
          "emi_details":null  
        }  
      },  
      "payment_group":"cardless_emi",
      ...
    }

    ```
  </Tab>

  <Tab title="Pay Later">
    ```javascript theme={"dark"}
    {
      ...,
      "payment_method":{  
        "pay_later":{  
            "channel":null,
            "provider":"olapostpaid",
            "phone":"9731117102"
        }  
      },  
      "payment_group":"pay_later",
      ...
    }

    ```
  </Tab>

  <Tab title="VBA Transfer">
    ```javascript theme={"dark"}
    {
      ...,
     "payment_method":{
         "vba_transfer":{
             "utr":"MerchantID_utr",
             "credit_ref_no":"NA",
             "remitter_account":"808081pxqp242614HW",
             "remitter_name":"Test",
             "remitter_ifsc":"IFSC",
             "email":"rishabtated@gmail.com",
             "phone":"9999999999",
             "vaccount_id":"123499",
             "vaccount_number":"94260000123400"
         }
     },
     "payment_group":"vba_transfer",
      ...
    }

    ```
  </Tab>

  <Tab title="Bank Transfer">
    ```javascript theme={"dark"}
    {
      ...,
     "payment_method":{
         "bank_transfer":{
             "transfer_type":"NEFT",
             "bank":"UNION BANK OF INDIA"
         }
     },
     "payment_group":"bank_transfer",
      ...
    }

    ```
  </Tab>
</Tabs>

## Webhook FAQs

<div style={{justifyContent: "space-between", alignItems: "center" }}>
  <a href="https://www.cashfree.com/docs/payments/online/webhooks/configure" target="_blank" rel="noopener noreferrer" style={{ color: "blue", fontWeight: "bold", textDecoration: "underline" }}>
    Configure webhooks
  </a>
</div>

<AccordionGroup>
  <Accordion title="How do I add or configure webhook URLs for different event types (e.g., success, failed)?">
    You can configure webhook URLs for each notification type in your merchant dashboard. To receive notifications, subscribe to specific events, such as PAYMENT\_SUCCESS or PAYMENT\_FAILED. For step-by-step instructions, go through the [official documentation](https://www.cashfree.com/docs/payments/online/webhooks/overview).

    <iframe src="https://www.cashfree.com/devstudio/preview/pg/embed/faqFeedback?section=webhooks%23how-do-i-add-or-configure-webhook-urls-for-different-event-types" style={{ width: "100%", height: "65px", border: "none" }} title="FAQs feedback component" />
  </Accordion>

  <Accordion title="Why am I not receiving failed webhooks?">
    This may occur if the PAYMENT\_FAILED webhook event is not subscribed. To resolve this, open your dashboard, navigate to the webhook configuration, and ensure that the `PAYMENT_FAILED` event       is selected.

    <Note>
      This applies to all webhook events. Make sure relevant events are enabled as needed.
    </Note>

    <iframe src="https://www.cashfree.com/devstudio/preview/pg/embed/faqFeedback?section=webhooks%23why-am-i-not-receiving-failed-webhooks" style={{ width: "100%", height: "65px", border: "none" }} title="FAQs feedback component" />
  </Accordion>

  <Accordion title="I’m getting an error while adding the webhook endpoint. What could be wrong?">
    Ensure that your endpoint is reachable and returns a 2xx status code. Also, verify that it is properly configured to accept webhook requests.

    <iframe src="https://www.cashfree.com/devstudio/preview/pg/embed/faqFeedback?section=webhooks%23im-getting-an-error-while-adding-the-webhook-endpoint" style={{ width: "100%", height: "65px", border: "none" }} title="FAQs feedback component" />
  </Accordion>

  <Accordion title="Why is my webhook not received?">
    There could be multiple reasons:

    * The webhook URL was not included in the notify\_url parameter during order creation.
    * Make sure you have done the webhook configuration for the notification type as needed.
    * The endpoint URL is returning a 4xx or 5xx error.

    Actions to take:

    * Verify that your webhook is correctly configured. Log in to the [Merchant Dashboard](https://merchant.cashfree.com/auth/login) and go to **Payment Gateway > Developers > Webhook Configuration**.
    * Ensure that the endpoint is accessible and able to accept requests from Cashfree.

    <iframe src="https://www.cashfree.com/devstudio/preview/pg/embed/faqFeedback?section=webhooks%23why-is-my-webhook-not-triggered-or-received" style={{ width: "100%", height: "65px", border: "none" }} title="FAQs feedback component" />
  </Accordion>

  <Accordion title="How do I enable or disable specific webhook types?">
    You can enable or disable specific webhook types directly from the [Merchant Dashboard](https://merchant.cashfree.com/auth/login). For detailed instructions, refer to the
    **Payment Gateway > Developers > Webhook Configuration** section.

    <iframe src="https://www.cashfree.com/devstudio/preview/pg/embed/faqFeedback?section=webhooks%23how-do-i-enable-or-disable-specific-webhook-types" style={{ width: "100%", height: "65px", border: "none" }} title="FAQs feedback component" />
  </Accordion>

  <Accordion title="How to enable the latest webhook version (e.g., 2025-01-01)?">
    Once the feature is rolled out in Production, the new version will appear in the version drop-down under Webhook Configuration.

    <Warning>
      If you do not see the new version, the rollout may still be in progress. Please check back later or contact support for assistance.
    </Warning>

    <iframe src="https://www.cashfree.com/devstudio/preview/pg/embed/faqFeedback?section=webhooks%23how-to-enable-the-latest-webhook-version" style={{ width: "100%", height: "65px", border: "none" }} title="FAQs feedback component" />
  </Accordion>

  <Accordion title="Webhook is configured, but no real-time data is received. Why?">
    This may happen if the webhook URL is configured, but no events are selected. Ensure:

    * Webhook types are enabled.
    * Your endpoint is healthy and accessible to accept the requests from Cashfree.

    <iframe src="https://www.cashfree.com/devstudio/preview/pg/embed/faqFeedback?section=webhooks%23webhook-is-configured-but-no-real-time-data-is-received" style={{ width: "100%", height: "65px", border: "none" }} title="FAQs feedback component" />
  </Accordion>

  <Accordion title="Why did the webhook trigger multiple times?">
    Duplicate webhook triggers may occur due to misconfiguration or retry logic. This can happen if multiple webhook versions are configured using the same or different endpoint URLs.

    ✅ Actions to take:

    * The Merchant can revisit and delete the duplicate configured endpoint URL. Log in to the [Merchant Dashboard](https://merchant.cashfree.com/auth/login) and go to **Payment Gateway > Developers > Webhook Configuration**.

    <iframe src="https://www.cashfree.com/devstudio/preview/pg/embed/faqFeedback?section=webhooks%23why-did-the-webhook-trigger-multiple-times" style={{ width: "100%", height: "65px", border: "none" }} title="FAQs feedback component" />
  </Accordion>

  <Accordion title="What if I don't pass a notify_url and only use return URLs?">
    Notify URLs are necessary for webhook delivery. Return URLs only redirect the user after the transaction. Ensure you pass both as different URLs, especially if you need server-side notifications.

    <iframe src="https://www.cashfree.com/devstudio/preview/pg/embed/faqFeedback?section=webhooks%23what-if-i-dont-pass-a-notified-url-and-only-use-return-urls" style={{ width: "100%", height: "65px", border: "none" }} title="FAQs feedback component" />
  </Accordion>

  <Accordion title="How can I improve webhook issue handling and reduce to raise of support tickets?">
    * Always subscribe to the necessary webhook event types (`SUCCESS`, `FAILED`, `USER_DROPPED`).
    * Test your webhook integration in Sandbox before going live.
    * Use publicly accessible HTTPS URLs that return 200 OK responses.
    * Regularly review and update webhook configurations in the merchant dashboard to avoid outdated or incorrect entries.

    <iframe src="https://www.cashfree.com/devstudio/preview/pg/embed/faqFeedback?section=webhooks%23how-can-i-improve-webhook-issue-handling-and-reduce-to-raise-support-tickets" style={{ width: "100%", height: "65px", border: "none" }} title="FAQs feedback component" />
  </Accordion>
</AccordionGroup>
