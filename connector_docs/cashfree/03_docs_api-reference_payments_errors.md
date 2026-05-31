> ## Documentation Index
> Fetch the complete documentation index at: https://www.cashfree.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# Errors

> Learn in detail about errors.

## Error structure

The Payment Gateway response in case of an error includes the following:

* **error\_code**: Code associated with every error.
* **error\_description**: Description of the error.
* **error\_source**: Source of the error.
* **error\_reason**: Failure reason.

**Sample error response from API**:

```json theme={"dark"}
{
  "message": "bad URL, please check API documentation",
  "help": "Check latest errors and resolution from Merchant Dashboard API logs: https://bit.ly/4glEd0W Help Document: https://bit.ly/4eeZYO9",
  "code": "request_failed",
  "type": "invalid_request_error"
}
```

**Sample error response from webhook**:

```json theme={"dark"}
{
    "auth_id": null,
    "authorization": null,
    "bank_reference": "306118259130",
    "cf_payment_id": 1636676360,
    "entity": "payment",
    "error_details": {
        "error_code": "TRANSACTION_DECLINED",
        "error_description": "transaction is rejected at the remitter bank end. Please reach out to issuer bank",
        "error_reason": "bank_rejected",
        "error_source": "bank"
    },
    "is_captured": false,
    "order_amount": 1.00,
    "order_id": "order_18482MSWq8prPMOW0jTeGsx0B1JmPC1",
    "payment_amount": 1.00,
    "payment_completion_time": "2023-03-02T18:24:51+05:30",
    "payment_currency": "INR",
    "payment_group": "upi",
    "payment_message": "01::REJECTED",
    "payment_method": {
        "upi": {
            "channel": "collect",
            "upi_id": "8XXXXXXXX2@upi"
        }
    },
    "payment_status": "FAILED",
    "payment_time": "2023-03-02T18:24:18+05:30"
}
```

***

## List of error types and error codes

Below are the error types and error codes with their descriptions.

### Error types

| error\_type             | description                                                 |
| ----------------------- | ----------------------------------------------------------- |
| `api_connection_error`  | Network communication issue with API server.                |
| `api_error`             | General server error during request processing.             |
| `authentication_error`  | Invalid or missing authentication credentials.              |
| `invalid_request_error` | Request is malformed or has invalid parameters.             |
| `feature_not_enabled`   | Requested feature is not enabled for the account.           |
| `rate_limit_error`      | Too many requests sent in a short time.                     |
| `validation_error`      | Request failed validation checks.                           |
| `idempotency_error`     | Repeated request with same idempotency key caused conflict. |
| `bad_gateway_error`     | Received invalid response from upstream server.             |

### Error codes

| error\_code                                     | description                                                     |
| ----------------------------------------------- | --------------------------------------------------------------- |
| `card_unsupported`                              | Card type not supported by payment system.                      |
| `payment_method_unsupported`                    | Payment method not accepted for this transaction.               |
| `surcharge_invalid`                             | Surcharge amount is missing, incorrect, or not allowed.         |
| `payment_gateway_unsupported`                   | Selected payment gateway is not supported.                      |
| `card_submission_disabled`                      | Card submission is currently disabled or blocked.               |
| `order_amount_invalid`                          | Order amount is missing, negative, or exceeds limits.           |
| `order_inactive`                                | Order is no longer active or has expired.                       |
| `customer_email_invalid`                        | Customer email is missing or incorrectly formatted.             |
| `version_invalid`                               | Provided API version is not supported or malformed.             |
| `order_token_invalid`                           | Order token is missing, expired, or incorrect.                  |
| `sub_session_id_invalid`                        | Sub-session ID is missing or invalid.                           |
| `payment_session_id_invalid`                    | Payment session ID is missing or does not exist.                |
| `native_otp_session_id_invalid`                 | Native OTP session ID is invalid or expired.                    |
| `flash_upi_auth_token_invalid`                  | Flash UPI auth token is invalid or expired.                     |
| `cookie_invalid`                                | Session cookie is missing, expired, or malformed.               |
| `order_id_invalid`                              | Order ID is incorrect, missing, or unrecognised.                |
| `order_expiry_time_invalid`                     | Order expiry time is missing, invalid, or in past.              |
| `order_id_not_paid`                             | Order ID exists, but payment was not completed.                 |
| `order_id_voided`                               | Order was voided and cannot be processed further.               |
| `refund_amount_invalid`                         | Refund amount is missing, invalid, or exceeds original payment. |
| `refund_id_invalid`                             | Refund ID is missing, incorrect, or unrecognised.               |
| `netbanking_bank_code_invalid`                  | Invalid or unsupported netbanking bank code provided.           |
| `payment_method_invalid`                        | Specified payment method is invalid or not recognised.          |
| `refund_invalid`                                | Refund cannot be processed due to invalid conditions.           |
| `vendor_id_invalid`                             | Vendor ID is missing, malformed, or not recognised.             |
| `payment_gateway_inactive`                      | Payment gateway is inactive or unavailable.                     |
| `customer_phone_invalid`                        | Customer phone number is missing or incorrectly formatted.      |
| `partner_apikey_invalid`                        | Partner API key is missing, invalid, or unauthorised.           |
| `payment_amount_invalid`                        | Payment amount is missing, negative, or incorrectly formatted.  |
| `refund_unsupported`                            | Refund operation is unsupported for this payment type.          |
| `order_already_paid`                            | Order has already been paid successfully.                       |
| `bank_processing_failure`                       | Bank failed to process the payment request.                     |
| `api_request_timeout`                           | API request timed out before completion.                        |
| `sdk_token_invalid`                             | SDK token is invalid or malformed.                              |
| `sdk_token_unknown`                             | Unknown SDK token provided in the request.                      |
| `simulation_id_invalid`                         | Simulation ID is invalid or does not exist.                     |
| `entity_id_invalid`                             | Entity ID is incorrect, missing, or unrecognised.               |
| `entity_unsupported`                            | Entity type is not supported for this operation.                |
| `simulation_id_missing`                         | Simulation ID is required but missing in request.               |
| `subscription_id_missing`                       | Subscription ID is required but missing.                        |
| `payment_id_missing`                            | Payment ID is missing or not found.                             |
| `plan_id_missing`                               | Plan ID is missing, invalid, or not found.                      |
| `refund_id_missing`                             | Refund ID is required but missing.                              |
| `PaymentForm_form_creation_failed`              | Failed to create payment form due to internal error.            |
| `PaymentForm_link_creation_failed`              | Failed to create payment link due to system issue.              |
| `order_already_exists`                          | Order already exists with the given ID or details.              |
| `orderpay_already_exists`                       | OrderPay object already exists for this order.                  |
| `order_id_already_exists`                       | Order ID already exists and cannot be duplicated.               |
| `domain_name_refererString`                     | Invalid or unapproved domain name in referer header.            |
| `android_package_{xRequestedWith}`              | Invalid or unrecognised Android package name in request.        |
| `refType_not_approved`                          | Referenced entity is not approved for this operation.           |
| `refType_ineligible`                            | Referenced entity is not eligible for this operation.           |
| `payment_gateway_inactive_request_failed`       | Payment gateway inactive; request could not be completed.       |
| `subscription_id_missing_request_failed_failed` | Subscription ID missing; request failed.                        |
| `simulation_id_missing_request_failed_failed`   | Simulation ID missing; request failed.                          |
| `cod_eligibility_failed`                        | COD eligibility check failed for this order.                    |
| `Paymentlink_create_failed`                     | Failed to create payment link due to internal issue.            |
| `headless_otp_submit_request_failed`            | OTP submission failed during headless authentication flow.      |
| `order_creation_faied`                          | Order creation failed due to validation or server error.        |
| `pan_submit_failed`                             | PAN submission failed due to invalid data or server error.      |
| `gstin_submit_failed`                           | GSTIN submission failed due to incorrect or missing data.       |
| `cin_submit_failed`                             | CIN submission failed due to invalid or missing data.           |
| `risk_data_ip_address_request_failed`           | IP address risk check failed during request processing.         |
| `cart_create_failed`                            | Cart creation failed due to invalid input or server issue.      |
| `order_create_failed`                           | Order creation failed; please retry or check input data.        |
| `order_pay_failed`                              | Order payment attempt failed due to processing error.           |
| `refund_post_failed`                            | Refund request failed to post due to system error.              |
| `link_post_failed`                              | Failed to post link request to server.                          |
| `api_request_failed`                            | API request failed due to timeout or internal error.            |
| `form_post_failed`                              | Form submission failed due to validation or processing error.   |
| `aadhar_otp_generation_failed`                  | Aadhaar OTP generation failed during identity verification.     |
| `aadhar_otp_verification_failed`                | Aadhaar OTP verification failed or expired.                     |
| `pan_verification_failed`                       | PAN verification failed due to a mismatch or system error.      |
| `bank_account_verification_failed`              | Bank account verification failed due to invalid input.          |
| `otp_generation_failed`                         | OTP generation failed due to rate limits or server error.       |
| `otp_expired_failed`                            | OTP has expired; please request a new one.                      |
| `otp_invalid_failed`                            | OTP is invalid or does not match.                               |
| `ref_id_invalid_failed`                         | Reference ID is invalid or not found.                           |
| `shipping_fetch_failed`                         | Shipping info fetch failed due to network or service error.     |
| `entity_simulation_payment_error_code_failed`   | Entity simulation failed during payment processing.             |
| `gst_verification_failed`                       | GST verification failed due to incorrect or unverified GSTIN.   |
| `offer_not_found`                               | Offer not found or does not exist.                              |
| `customer_get_not_found`                        | Customer not found with given details.                          |
| `payment_not_found`                             | Payment record not found for provided ID.                       |
| `payment_post_not_found`                        | Payment request failed; resource not found.                     |
| `entityId_not_found`                            | Entity ID not found or unrecognised.                            |
| `order_get_not_found`                           | Order not found for given ID.                                   |
| `cart_get_not_found`                            | Cart not found for current session or ID.                       |
| `orderpay_post_not_found`                       | OrderPay request not found or already processed.                |
| `card_alias_not_found`                          | Card alias not found or invalid.                                |
| `cardbin_details_not_found`                     | Card BIN details not available or missing.                      |
| `card_not_found`                                | Card not found or does not exist.                               |
| `order_id_post_not_found`                       | Order ID not found in post request.                             |
| `modeRates_get_not_found`                       | Mode rate information not available or missing.                 |
| `refund_get_not_found`                          | Refund information not found for provided ID.                   |
| `transaction_get_not_found`                     | Transaction details not found or unavailable.                   |
| `settlement_get_not_found`                      | Settlement not found for provided identifier.                   |
| `link_get_not_found`                            | Payment link not found or deleted.                              |
| `merchant_get_not_found`                        | Merchant account not found or unregistered.                     |
| `terminal_id_post_not_found`                    | Terminal ID not found in post request.                          |
| `resource_post_not_found`                       | Resource not found during post request.                         |
| `terminal_post_not_found`                       | Terminal not found or inactive.                                 |
| `order_request_not_found`                       | Order request not found or expired.                             |
| `payment_request_not_found`                     | Payment request not found or invalid.                           |
| `dispute_request_not_found`                     | Dispute request not found or missing.                           |
| `document_request_not_found`                    | Document request not found or expired.                          |
| `resource_get_not_found`                        | Requested resource not found or unavailable.                    |
| `form_get_not_found`                            | Form not found or has been removed.                             |
| `authentication_error`                          | Authentication failed due to invalid or missing credentials.    |
| `customer_instruments_authentication_error`     | Customer instruments request failed authentication.             |
| `integrity_token_not_found`                     | Integrity token not found or expired.                           |
| `checkout_config_not_found`                     | Checkout configuration not found or misconfigured.              |
| `api_error_not_found`                           | API error: requested resource not found.                        |
| `payment_instrument_not_found`                  | Payment instrument not found or unsupported.                    |
| `order_not_found`                               | Order does not exist or was deleted.                            |
| `instrument_not_found`                          | Instrument not found for current customer or request.           |
| `request_failed`                                | Request failed due to server or network error.                  |
| `cryptogram_request_failed`                     | Cryptogram generation failed or request is invalid.             |
| `authorize_only_invalid`                        | Authorise-only is not allowed for this transaction.             |
| `card_number_invalid`                           | Card number is invalid or incorrectly formatted.                |
| `emi_tenure_invalid`                            | EMI tenure is invalid or unsupported for selection.             |

## List of errors for payments

Download the list of errors along with their explanation.

<a href="https://gocashassets.s3.ap-south-1.amazonaws.com/repostmancollection/Error+List.xlsx" target="_blank" download>Payment Error List</a>

<Note>
  Error details will be shown for every failed transaction in the payload of the following APIs and webhooks:

  * [Get Payments for an Order](/api-reference/payments/latest/payments/get-payments-for-order)
  * [Get Payment by ID](/api-reference/payments/latest/payments/get)
  * [Payment Failed Webhook](/api-reference/payments/latest/payments/webhooks#payment-failed-webhook)
</Note>
