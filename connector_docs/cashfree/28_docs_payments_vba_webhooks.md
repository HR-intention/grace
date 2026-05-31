> ## Documentation Index
> Fetch the complete documentation index at: https://www.cashfree.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# Webhooks Configuration and Usage

Configure webhooks and use them to receive real-time updates on transaction events.

<Warning>The VBA\_TRANSFER\_SUCCESS\_PAYMENT webhook has been deprecated and will no longer be triggered for new integrations. Please ensure that your integration relies on the currently supported webhook - PAYMENT\_SUCCESS\_WEBHOOK for transfer status updates.</Warning>

For newer integrations , rely on PAYMENT\_SUCCESS\_WEBHOOK. Refer to the sample below:

```json JSON theme={"dark"}
{
  "data": {
    "order": {
      "order_id": "n585ctivoh6g",
      "order_amount": 1500,
      "order_currency": "INR",
      "order_tags": null
    },
    "payment": {
      "cf_payment_id": "5114925103565",
      "payment_status": "SUCCESS",
      "payment_amount": 1500,
      "payment_currency": "INR",
      "payment_message": "NA",
      "payment_time": "2026-02-05T15:19:36+05:30",
      "bank_reference": "MerchantID_TESTUTR12362",
      "auth_id": null,
      "payment_method": {
        "vba_transfer": {
          "utr": "MerchantID_TESTUTR12362",
          "credit_ref_no": "NA",
          "remitter_account": "123456789012",
          "remitter_name": "John Doe",
          "remitter_ifsc": "NOOB0CMSNOC",
          "email": "user@cashfree.com",
          "phone": "9999999999",
          "vaccount_id": "USER09",
          "vaccount_number": "98912574JSER10"
        }
      },
      "payment_group": "vba_transfer",
      "international_payment": null,
      "payment_surcharge": {
        "payment_surcharge_service_charge": 0,
        "payment_surcharge_service_tax": 0
      }
    },
    "customer_details": {
      "customer_name": "John Doe",
      "customer_id": null,
      "customer_email": "user@cashfree.com",
      "customer_phone": "9999999999"
    },
    "payment_gateway_details": {
      "gateway_name": "CASHFREE",
      "gateway_order_id": null,
      "gateway_payment_id": null,
      "gateway_status_code": null,
      "gateway_order_reference_id": null,
      "gateway_settlement": "CASHFREE",
      "gateway_reference_name": null
    },
    "payment_offers": null,
    "terminal_details": null
  },
  "event_time": "2026-02-05T15:19:35+05:30",
  "type": "PAYMENT_SUCCESS_WEBHOOK"

}
```

The following is the webhook payload for payments collected through the Virtual Bank Account (VBA) (deprecated):

```json JSON theme={"dark"}
{
    "event":"AMOUNT_COLLECTED",
    "amount":"400",
    "vAccountId":"87654321",
    "virtualVpaId":"8080808087654321",
    "isVpa":"0",
    "email":"xyz@example.com",
    "phone":"9876543210",
    "referenceId":87654,
    "utr":"N123456789",
    "creditRefNo":"0976541123",
    "remitterAccount":"123455666778",
    "remitterName":"CASHFREE PAYMENTS",
    "paymentTime":"2019-07-20 15:27:37",
    "signature":"8uV792gBZaasJHBFSsfaMHLuqnZKkossjw9gEJ8Sx85V+jgbpg4ME="
}
```

<Warning>For settlement webhook, PG settlement payload will be sent to you on your endpoints from day 0 of migration. This might break consumption of settlement webhooks at your end if you are relying on settlement webhooks in AC payload format.</Warning>

PG payload for settlement webhook:

```json JSON theme={"dark"}
{
    "data": {
        "settlement": {
            "adjustment": 0,
            "amount_settled": 97.94,
            "payment_amount": 100,
            "payment_from": "2022-02-14 12:00:00",
            "payment_till": "2022-02-14 12:15:00",
            "reason": null,
            "service_charge": 1.75,
            "service_tax": 0.31,
            "settled_on": "2022-02-14T12:35:19+05:30",
            "settlement_type": "STANDARD",   //settlement type //
            "settlement_amount": 97.94,
            "settlement_id": 738,
            "settlement_initiated_on": "2022-02-14T12:35:17+05:30",
            "status": "SUCCESS",
            "utr": 1644822317781212,
            "settlement_charge": 0,    // applicable for instant settlement //
            "settlement_tax": 0,       // applicable for instant settlement //
            "remarks": null.           // applicable for instant settlement //
        }
    },
    "event_time": "2022-02-08T13:37:34+05:30",
    "type": "SETTLEMENT_SUCCESS"
}
```

For detailed information on PG settlement webhooks, refer to [PG Settlement Webhooks](https://www.cashfree.com/docs/api-reference/payments/latest/settlements/settlement-webhooks).
