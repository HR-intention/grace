> ## Documentation Index
> Fetch the complete documentation index at: https://www.cashfree.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# Get Payment by ID

> Use this API to view payment details of an order for a payment ID.

<style>
  {`
    .postman-button {
      transition: all 0.2s ease;
      cursor: pointer;
    }
    .postman-button:hover {
      background-color: rgba(255, 248, 240, 0.8) !important;
      border-color: #FF6C37 !important;
      transform: translateY(-1px) !important;
    }
    .postman-button [data-as="p"],
    .postman-button:hover [data-as="p"] {
      background: transparent !important;
      border: 0 !important;
      padding: 0 !important;
    }
    `}
</style>

<a
  href="https://www.postman.com/cashfreedevelopers/workspace/cashfree-apis-v2025-01-01/request/40140981-2796fe72-dc6f-4333-921e-7c42ea5de3b7"
  target="_blank"
  rel="noopener noreferrer"
  className="postman-button"
  style={{ display:'inline-flex', alignItems:'center', gap:'8px', padding:'8px 18px', backgroundColor:'rgba(255,248,240,0.4)', color:'black', border:'1px solid #FF6C37', borderRadius:'6px', textDecoration:'none', fontSize:'14px', fontWeight:'500' }}
  onMouseEnter={(e) => {
const el = e.currentTarget;
el.style.backgroundColor = 'rgba(255, 248, 240, 0.8)';
el.style.transform = 'translateY(-1px)';
}}
  onMouseLeave={(e) => {
const el = e.currentTarget;
el.style.backgroundColor = 'rgba(255, 248, 240, 0.4)';
el.style.transform = 'none';
}}
>
  <span style={{ display:'block', width:'22px', height:'22px', backgroundImage:'url(https://www.cashfree.com/docs/static/social/postman-icon-svgrepo-com.svg)', backgroundSize:'22px 22px', backgroundRepeat:'no-repeat', backgroundPosition:'center', flexShrink:0 }} aria-label="Postman" />

  Run in Postman: You can also try this API in our Postman Collection.
</a>

## Error codes

The following table lists the error codes you may encounter when retrieving payment details for an order using a payment ID:

<Accordion title="Error codes">
  | Code                 | Description                                                                                                                                     | Type                    | Status |
  | :------------------- | :---------------------------------------------------------------------------------------------------------------------------------------------- | :---------------------- | :----- |
  | `order_id_invalid`   | The `order_id` field contains a value in an invalid format. Provide a correctly formatted order ID and try again. Value received: `#INVALID`    | `invalid_request_error` | 400    |
  | `order_id_missing`   | The `order_id` field is required but was not included in the request.                                                                           | `invalid_request_error` | 400    |
  | `version_missing`    | The `version` field is required but was not included in the request header.                                                                     | `invalid_request_error` | 400    |
  | `payment_id_invalid` | The `payment_id` field must be a numeric value. Value received: `INVALID`                                                                       | `invalid_request_error` | 400    |
  | `payment_get_failed` | The `payment_id` value is out of the supported integer range and cannot be processed. Value received: `100000000000000000000000000000000000000` | `invalid_request_error` | 400    |
  | `payment_id_missing` | The `payment_id` field is required but was not included in the request.                                                                         | `invalid_request_error` | 400    |
  | `payment_not_found`  | No transaction was found for the specified payment ID. Verify the payment ID and try again.                                                     | `invalid_request_error` | 404    |
  | `order_not_found`    | No order was found for the specified order reference ID. Verify the order ID and try again.                                                     | `invalid_request_error` | 404    |
</Accordion>

<Note>This API allows you to retrieve payment data for the current and previous financial years. To access data older than this period, log in to the [Merchant Dashboard](https://merchant.cashfree.com/auth/login)</Note>


## OpenAPI

````yaml /openapi/payments/v2025-01-01.yaml get /orders/{order_id}/payments/{cf_payment_id}
openapi: 3.0.0
info:
  version: '2025-01-01'
  title: Cashfree Payment Gateway APIs
  license:
    name: Apache 2.0
    url: https://www.apache.org/licenses/LICENSE-2.0.html
  contact:
    email: developers@cashfree.com
    name: API Support
    url: https://discord.com/invite/QdZkNSxXsB
  description: >-
    Cashfree's Payment Gateway APIs provide developers with a streamlined
    pathway to integrate advanced payment processing capabilities into their
    applications, platforms and websites.
servers:
  - url: https://sandbox.cashfree.com/pg
    description: Sandbox server.
  - url: https://api.cashfree.com/pg
    description: Production server.
security: []
tags:
  - name: Orders
    description: Collection of APIs to handle orders.
  - name: Payments
    description: Collection of APIs to handle payments.
  - name: Refunds
    description: Collection of APIs to handle refunds.
  - name: Settlements
    description: Collection of APIs to handle settlements.
  - name: Payment Links
    description: Collection of APIs to handle payment links.
  - name: Token Vault
    description: >-
      Collection of APIs to use Cashfree's token Vault. This helps you save
      cards and tokenize them in a PCI complaint manner. We support creation of
      network tokens which can be used across acquiring banks.
  - name: softPOS
    description: Collection of APIs to manage softPOS' agent and order.
  - name: Offers
    description: Collection of APIs to handle offers.
  - name: Eligibility
    description: >-
      Collection of APIs to check eligibile entities - payment methods, offer,
      affordibility.
  - name: Settlement Reconciliation
    description: Collection of APIs to handle settlements.
  - name: PG Reconciliation
    description: Collection of APIs to handle reconciliation.
  - name: Customers
    description: Collection of APIs to handle customers.
  - name: Easy-Split
    description: Collection of APIs to handle Easy-Split.
  - name: Simulation
    description: Collection of APIs to handle simulation.
  - name: Disputes
    description: Collection of APIs to handle disputes.
  - name: Utilities
    description: Collection of APIs for utility requirement.
  - name: Downtimes
    description: Collection of APIs for managing downtimes.
externalDocs:
  url: https://api.cashfree.com/pg
  description: This url will have the information of all the APIs.
paths:
  /orders/{order_id}/payments/{cf_payment_id}:
    get:
      tags:
        - Payments
      summary: Get Payment by ID
      description: Use this API to view payment details of an order for a payment ID.
      operationId: PGOrderFetchPayment
      parameters:
        - $ref: '#/components/parameters/apiVersionHeader'
        - $ref: '#/components/parameters/xRequestIDHeader'
        - $ref: '#/components/parameters/orderIDParam'
        - $ref: '#/components/parameters/cfPaymentIDParam'
        - $ref: '#/components/parameters/xIdempotencyKeyHeader'
      responses:
        '200':
          description: >-
            Success response for viewing payment details of an order for a
            payment ID.
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/PaymentEntity'
              examples:
                upi:
                  value:
                    cf_payment_id: '12376123'
                    order_id: order_8123
                    entity: payment
                    payment_currency: INR
                    error_details: null
                    order_amount: 10.01
                    order_currency: INR
                    is_captured: true
                    payment_group: upi
                    authorization:
                      action: CAPTURE
                      status: PENDING
                      captured_amount: 100
                      start_time: '2022-02-09T18:04:34+05:30'
                      end_time: '2022-02-19T18:04:34+05:30'
                      approve_by: '2022-02-09T18:04:34+05:30'
                      action_reference: '6595231908096894505959'
                      action_time: '2022-08-03T16:09:51'
                    payment_method:
                      upi:
                        channel: collect
                        upi_id: rohit@xcxcx
                        upi_payer_ifsc: AXL1234
                        upi_payer_account_number: XXXXXXX6024
                    payment_amount: 10.01
                    payment_time: '2021-07-23T12:15:06+05:30'
                    payment_completion_time: '2021-07-23T12:18:59+05:30'
                    payment_status: SUCCESS
                    payment_message: Transaction successful
                    bank_reference: P78112898712
                    auth_id: A898101
                    international_payment:
                      international: false
                    payment_gateway_details:
                      gateway_name: CASHFREE
                      gateway_order_id: 1234421ABD
                      gateway_payment_id: XABDJ2213
                      gateway_order_reference_id: BDIWO233
                      gateway_settlement: cashfree
                      gateway_reference_name: ''
                card:
                  value:
                    auth_id: '749842'
                    authorization: null
                    bank_reference: '519615460937'
                    cf_payment_id: '4128924251'
                    entity: payment
                    error_details: null
                    international_payment:
                      international: false
                    is_captured: true
                    order_amount: 1
                    order_currency: INR
                    order_id: order_18482zuD6LhQGYO3OOihGjnlDV4OzpD
                    payment_amount: 1
                    payment_completion_time: '2025-07-15T15:02:48+05:30'
                    payment_currency: INR
                    payment_gateway_details:
                      gateway_name: CASHFREE
                      gateway_order_id: null
                      gateway_payment_id: null
                      gateway_order_reference_id: null
                      gateway_status_code: null
                      gateway_settlement: cashfree
                      gateway_reference_name: null
                    payment_group: debit_card
                    payment_message: Transaction Success
                    payment_method:
                      card:
                        card_bank_name: KOTAK MAHINDRA BANK
                        card_country: IN
                        card_network: visa
                        card_network_reference_id: null
                        card_number: XXXXXXXXXXXX4738
                        card_sub_type: R
                        card_type: debit_card
                        channel: link
                    payment_offers: []
                    payment_status: SUCCESS
                    payment_surcharge: null
                    payment_time: '2025-07-15T15:01:53+05:30'
          headers:
            x-api-version:
              $ref: '#/components/headers/x-api-version'
            x-ratelimit-limit:
              $ref: '#/components/headers/x-ratelimit-limit'
            x-ratelimit-remaining:
              $ref: '#/components/headers/x-ratelimit-remaining'
            x-ratelimit-retry:
              $ref: '#/components/headers/x-ratelimit-retry'
            x-ratelimit-type:
              $ref: '#/components/headers/x-ratelimit-type'
            x-request-id:
              $ref: '#/components/headers/x-request-id'
            x-idempotency-key:
              $ref: '#/components/headers/x-idempotency-key'
            x-idempotency-replayed:
              $ref: '#/components/headers/x-idempotency-replayed'
        '400':
          $ref: '#/components/responses/Response400'
        '401':
          $ref: '#/components/responses/Response401'
        '404':
          $ref: '#/components/responses/Response404'
        '409':
          $ref: '#/components/responses/Response409'
        '422':
          $ref: '#/components/responses/Response422'
        '429':
          $ref: '#/components/responses/Response429'
        '500':
          $ref: '#/components/responses/Response500'
        '502':
          $ref: '#/components/responses/Response502'
      deprecated: false
      security:
        - XClientID: []
          XClientSecret: []
        - XClientID: []
          XPartnerAPIKey: []
        - XClientID: []
          XClientSignatureHeader: []
        - XPartnerMerchantID: []
          XPartnerAPIKey: []
components:
  parameters:
    apiVersionHeader:
      in: header
      name: x-api-version
      required: true
      description: API version to be used. Format is in YYYY-MM-DD.
      schema:
        type: string
        description: API version to be used.
        default: '2025-01-01'
      example: '2025-01-01'
      x-ignore: true
    xRequestIDHeader:
      in: header
      name: x-request-id
      description: >-
        Request ID for the API call. Can be used to resolve tech issues.
        Communicate this in your tech related queries to Cashfree.
      required: false
      schema:
        type: string
      example: 4dfb9780-46fe-11ee-be56-0242ac120002
    orderIDParam:
      name: order_id
      in: path
      required: true
      description: The ID which uniquely identifies your order.
      schema:
        type: string
      example: your-order-id
    cfPaymentIDParam:
      name: cf_payment_id
      in: path
      required: true
      description: The Cashfree payment or transaction ID.
      schema:
        type: string
      example: '121224562'
    xIdempotencyKeyHeader:
      in: header
      name: x-idempotency-key
      required: false
      description: >
        An idempotency key is a unique identifier you include with your API
        call.

        If the request fails or times out, you can safely retry it using the
        same key to avoid duplicate actions.
      schema:
        type: string
        format: UUID
      example: 47bf8872-46fe-11ee-be56-0242ac120002
  schemas:
    PaymentEntity:
      title: PaymentEntity
      type: object
      example:
        $ref: '#/components/examples/payments_entity_list_example/value/0'
      properties:
        cf_payment_id:
          type: string
          description: Payment entity full object.
        order_id:
          type: string
        entity:
          type: string
        error_details:
          $ref: '#/components/schemas/ErrorDetailsInPaymentsEntity'
        is_captured:
          type: boolean
        order_amount:
          type: number
          description: >-
            Order amount can be different from payment amount if you collect
            service fee from the customer.
        payment_group:
          type: string
          description: >-
            Type of payment group. One of ['prepaid_card', 'upi_ppi_offline',
            'cash', 'upi_credit_card', 'paypal', 'net_banking', 'cardless_emi',
            'credit_card', 'bank_transfer', 'pay_later', 'debit_card_emi',
            'debit_card', 'wallet', 'upi_ppi', 'upi', 'credit_card_emi'].
        payment_currency:
          type: string
        payment_amount:
          type: number
        payment_time:
          type: string
          description: This is the time when the payment was initiated.
        payment_completion_time:
          type: string
          description: This is the time when the payment reaches its terminal state.
        payment_status:
          type: string
          enum:
            - SUCCESS
            - NOT_ATTEMPTED
            - FAILED
            - USER_DROPPED
            - VOID
            - CANCELLED
            - PENDING
          description: >-
            The transaction status can be one of  ["SUCCESS", "NOT_ATTEMPTED",
            "FAILED", "USER_DROPPED", "VOID", "CANCELLED", "PENDING"].
        payment_message:
          type: string
        bank_reference:
          type: string
          description: Issuing bank’s transaction reference number.
        auth_id:
          type: string
          description: Authorisation ID provided by the issuing bank.
        order_currency:
          type: string
        authorization:
          $ref: '#/components/schemas/AuthorizationInPaymentsEntity'
        payment_method:
          oneOf:
            - $ref: '#/components/schemas/PaymentMethodCardInPaymentsEntity'
            - $ref: '#/components/schemas/PaymentMethodNetBankingInPaymentsEntity'
            - $ref: '#/components/schemas/PaymentMethodUPIInPaymentsEntity'
            - $ref: '#/components/schemas/PaymentMethodAppInPaymentsEntity'
            - $ref: '#/components/schemas/PaymentMethodCardlessEMIInPaymentsEntity'
            - $ref: '#/components/schemas/PaymentMethodPaylaterInPaymentsEntity'
            - $ref: '#/components/schemas/PaymentMethodCardEMIInPaymentsEntity'
            - $ref: '#/components/schemas/PaymentMethodBankTransferInPaymentsEntity'
        international_payment:
          $ref: '#/components/schemas/InternationalPaymentEntity'
        payment_gateway_details:
          $ref: '#/components/schemas/PaymentGatewayDetails'
        payment_surcharge:
          type: object
          properties:
            payment_surcharge_service_charge:
              type: number
              format: float64
            payment_surcharge_service_tax:
              type: number
              format: float64
    ErrorDetailsInPaymentsEntity:
      title: ErrorDetailsInPayments
      description: The error details are present only for failed payments.
      example:
        error_code: TRANSACTION_DECLINED
        error_description: issuer bank or payment service provider declined the transaction
        error_reason: auth_declined
        error_source: customer
        error_code_raw: ZM
        error_description_raw: INVALID / INCORRECT MPIN
        error_subcode_raw: ''
      type: object
      properties:
        error_code:
          type: string
        error_description:
          type: string
        error_reason:
          type: string
        error_source:
          type: string
        error_code_raw:
          type: string
        error_description_raw:
          type: string
        error_subcode_raw:
          type: string
    AuthorizationInPaymentsEntity:
      title: AuthorizationInPayments
      description: If preauth enabled for account you will get this body.
      example:
        action: CAPTURE
        status: PENDING
        captured_amount: 100
        start_time: '2022-02-09T18:04:34+05:30'
        end_time: '2022-02-19T18:04:34+05:30'
        approve_by: '2022-02-09T18:04:34+05:30'
        action_reference: '6595231908096894505959'
        action_time: '2022-08-03T16:09:51'
      type: object
      properties:
        action:
          type: string
          enum:
            - CAPTURE
            - VOID
          description: One of CAPTURE or VOID.
        status:
          type: string
          enum:
            - SUCCESS
            - PENDING
          description: One of SUCCESS or PENDING.
        captured_amount:
          type: number
          description: The captured amount for this authorization request.
        start_time:
          type: string
          description: Start time of this authorization hold (only for UPI).
        end_time:
          type: string
          description: End time of this authorization hold (only for UPI).
        approve_by:
          type: string
          description: >-
            Approve by time as passed in the authorization request (only for
            UPI).
        action_reference:
          type: string
          description: CAPTURE or VOID reference number based on action.
        action_time:
          type: string
          description: Time of action (CAPTURE or VOID).
    PaymentMethodCardInPaymentsEntity:
      title: Card
      description: >-
        The following code samples show the payment method object payload for
        different payment methods.
      example:
        channel: link
        card_number: XXXXXXXXXXXX4738
        card_network: visa
        card_type: credit_card
        card_sub_type: R
        card_country: IN
        card_bank_name: HDFC Bank
        card_network_reference_id: '100212023061229'
        instrument_id: 3fc5814b-e732-4a71-b2ee-94b4f147d9e1
      type: object
      properties:
        card:
          type: object
          properties:
            channel:
              description: The requested channel, can be `link` or `post`.
              type: string
            card_number:
              description: >-
                The last four digits of the customer's card number. For external
                token transactions or external Alt ID transactions, this value
                is passed only when the merchant includes `card_display` in the
                [Order Pay
                API](https://www.cashfree.com/docs/api-reference/payments/latest/payments/pay)
                request.
              type: string
            card_network:
              description: >-
                The card scheme or network of the card. For example, `visa`,
                `mastercard`, `rupay`, `amex`, or `diners`.
              type: string
            card_type:
              description: >-
                The type of card. For example, `credit_card`, `debit_card`, or
                `prepaid_card`.
              type: string
            card_sub_type:
              description: >-
                The sub-type of card. `R` is Retail card, `P` is Premium card,
                `C` is Corporate card.
              type: string
            card_country:
              description: The issuing country of the card. For example, `IN`.
              type: string
            card_bank_name:
              description: >-
                The issuing bank of the card. For example, `HDFC BANK`, `AXIS
                BANK`, or `ICICI BANK`.
              type: string
            card_network_reference_id:
              description: >-
                The authentication reference ID provided by the respective card
                network.
              type: string
            instrument_id:
              description: >-
                The identifier for the card saved at Cashfree. This value is
                sent only for CF token transactions.
              type: string
    PaymentMethodNetBankingInPaymentsEntity:
      title: Net banking
      description: Netbanking payment method object for pay.
      example:
        channel: link
        netbanking_bank_code: 3044
        netbanking_bank_name: State Bank of India
      type: object
      properties:
        netbanking:
          type: object
          properties:
            channel:
              type: string
            netbanking_bank_code:
              type: integer
            netbanking_bank_name:
              type: string
            netbanking_ifsc:
              type: string
            netbanking_account_number:
              type: string
      required:
        - channel
        - netbanking_bank_name
        - netbanking_bank_code
    PaymentMethodUPIInPaymentsEntity:
      title: UPI
      description: UPI payment method for pay api.
      example:
        channel: collect
        upi_id: 980123781@upi
        upi_payer_ifsc: AXL1234
        upi_payer_account_number: XXXXXXX6024
      type: object
      properties:
        upi:
          type: object
          properties:
            channel:
              type: string
            upi_id:
              type: string
            upi_payer_ifsc:
              type: string
            upi_payer_account_number:
              type: string
      required:
        - channel
    PaymentMethodAppInPaymentsEntity:
      title: App
      description: payment method app object in payment entity.
      example:
        channel: link
        provider: paytm
        phone: '1234512345'
      type: object
      properties:
        app:
          type: object
          properties:
            channel:
              type: string
            provider:
              type: string
            phone:
              type: string
    PaymentMethodCardlessEMIInPaymentsEntity:
      title: Cardless EMI
      description: payment method carless object in payment entity.
      example:
        channel: link
        provider: flexmoney
        phone: '9908761211'
      type: object
      properties:
        cardless_emi:
          type: object
          properties:
            channel:
              type: string
            provider:
              type: string
            phone:
              type: string
    PaymentMethodPaylaterInPaymentsEntity:
      title: Pay later
      description: Paylater payment method object for pay API.
      example:
        channel: link
        provider: lazypay
        phone: '9908761211'
      type: object
      properties:
        paylater:
          type: object
          properties:
            channel:
              type: string
            provider:
              type: string
            phone:
              type: string
    PaymentMethodCardEMIInPaymentsEntity:
      title: Card EMI
      description: payment method card emi object in payment entity.
      example:
        channel: link
        card_number: 41111xxxxxx111
        card_network: visa
        card_type: credit_card
        card_country: IN
        card_bank_name: HDFC Bank
        card_network_reference_id: '100212023061229'
      type: object
      properties:
        emi:
          type: object
          properties:
            channel:
              type: string
            card_number:
              type: string
            card_network:
              type: string
            card_type:
              type: string
            card_country:
              type: string
            card_bank_name:
              type: string
            card_network_reference_id:
              type: string
            emi_tenure:
              type: number
            emi_details:
              type: object
              properties:
                emi_amount:
                  type: number
                emi_tenure:
                  type: number
                emi_interest:
                  type: number
    PaymentMethodBankTransferInPaymentsEntity:
      title: Bank transfer
      description: payment method bank transfer object in payment entity.
      example:
        channel: link
        banktransfer_bank_name: BANK_TRANSFER
        banktransfer_ifsc: ''
        banktransfer_account_number: ''
      type: object
      properties:
        banktransfer:
          type: object
          properties:
            channel:
              type: string
            banktransfer_bank_name:
              type: string
            banktransfer_ifsc:
              type: string
            banktransfer_account_number:
              type: string
    InternationalPaymentEntity:
      title: InternationalPayment
      description: International payment details.
      type: object
      properties:
        international:
          type: boolean
    PaymentGatewayDetails:
      title: PaymentGatewayDetails
      type: object
      description: payment gateway details present in the webhook response.
      properties:
        gateway_name:
          type: string
        gateway_order_id:
          type: string
        gateway_payment_id:
          type: string
        gateway_order_reference_id:
          type: string
        gateway_status_code:
          type: string
        gateway_settlement:
          type: string
        gateway_reference_name:
          type: string
    BadRequestError:
      title: BadRequestError
      description: Invalid request received from client.
      example:
        message: bad URL, please check API documentation
        help: >-
          Check latest errors and resolution from Merchant Dashboard API logs:
          https://bit.ly/4glEd0W Help Document: https://bit.ly/4eeZYO9
        code: request_failed
        type: invalid_request_error
      type: object
      properties:
        message:
          type: string
        code:
          type: string
        help:
          type: string
        type:
          type: string
          enum:
            - invalid_request_error
    AuthenticationError:
      title: AuthenticationError
      description: Error if api keys are wrong.
      example:
        message: authentication Failed
        code: request_failed
        type: authentication_error
      type: object
      properties:
        message:
          type: string
        code:
          type: string
        type:
          type: string
          description: authentication_error.
    ApiError404:
      title: ApiError404
      description: Error when resource requested is not found.
      example:
        message: something is not found
        help: >-
          Check latest errors and resolution from Merchant Dashboard API logs:
          https://bit.ly/4glEd0W Help Document: https://bit.ly/4eeZYO9
        code: something_not_found
        type: invalid_request_error
      type: object
      properties:
        message:
          type: string
        code:
          type: string
        help:
          type: string
        type:
          type: string
          enum:
            - invalid_request_error
          description: invalid_request_error.
    ApiError409:
      title: ApiError409
      description: duplicate request.
      example:
        message: order with same id is already present
        help: >-
          Check latest errors and resolution from Merchant Dashboard API logs:
          https://bit.ly/4glEd0W Help Document: https://bit.ly/4eeZYO9
        code: order_already_exists
        type: invalid_request_error
      type: object
      properties:
        message:
          type: string
        help:
          type: string
        code:
          type: string
        type:
          type: string
          enum:
            - invalid_request_error
          description: invalid_request_error.
    IdempotencyError:
      title: IdempotencyError
      description: >-
        Error when idempotency fails. Different request body with the same
        idempotent key.
      example:
        message: something is not found
        help: >-
          Check latest errors and resolution from Merchant Dashboard API logs:
          https://bit.ly/4glEd0W Help Document: https://bit.ly/4eeZYO9
        code: request_invalid
        type: idempotency_error
      type: object
      properties:
        message:
          type: string
        help:
          type: string
        code:
          type: string
        type:
          type: string
          enum:
            - idempotency_error
          description: idempotency_error.
    RateLimitError:
      title: RateLimitError
      description: Error when rate limit is breached for your api.
      example:
        message: Too many requests from IP. Check headers
        code: request_failed
        type: rate_limit_error
      type: object
      properties:
        message:
          type: string
        code:
          type: string
        type:
          type: string
          enum:
            - rate_limit_error
          description: rate_limit_error.
    ApiError:
      title: ApiError
      description: Error at Cashfree's server.
      example:
        message: internal Server Error
        help: >-
          Check latest errors and resolution from Merchant Dashboard API logs:
          https://bit.ly/4glEd0W Help Document: https://bit.ly/4eeZYO9
        code: internal_error
        type: api_error
      type: object
      properties:
        message:
          type: string
        code:
          type: string
        help:
          type: string
        type:
          type: string
          enum:
            - api_error
          description: api_error.
    ApiError502:
      title: ApiError502
      description: Error when there is error at partner bank.
      example:
        message: something is not found
        help: >-
          Check latest errors and resolution from Merchant Dashboard API logs:
          https://bit.ly/4glEd0W Help Document: https://bit.ly/4eeZYO9
        code: bank_processing_failure
        type: api_error
      type: object
      properties:
        message:
          type: string
        help:
          type: string
        code:
          type: string
          description: >
            `bank_processing_failure` will be returned here to denote failure at
            bank.
        type:
          type: string
          enum:
            - api_error
          description: api_error.
  headers:
    x-api-version:
      schema:
        type: string
        format: YYYY-MM-DD
        enum:
          - '2025-01-01'
      description: >-
        This header has the version of the API. The current version is
        `2025-01-01`.
    x-ratelimit-limit:
      schema:
        type: integer
      example: 200
      description: Ratelimit set for your account for this API per minute.
    x-ratelimit-remaining:
      schema:
        type: integer
      example: 2
      description: >-
        Rate limit remaning for your account for this API in the next minute.
        Uses sliding window.
    x-ratelimit-retry:
      schema:
        type: integer
      example: 4
      description: |
        Contains number of seconds to wait if rate limit is breached
        - Is 0 if withing the limit
        - Is between 1 and 59 if breached
    x-ratelimit-type:
      schema:
        type: string
        enum:
          - app_id
          - ip
      example: ip
      description: >
        either ip or app_id

        - `ip` if making a call from the browser. True for api where you don't
        need `x-client-id` and `x-client-secret`

        - `app_id` for authenticated api calls i.e using `x-client-id` and
        `x-client-secret`
    x-request-id:
      schema:
        type: string
      example: some-req-id
      description: >-
        Request id for your api call. Is blank or null if no `x-request-id` is
        sent during the request.
    x-idempotency-key:
      schema:
        type: string
      example: some-idem-id
      description: >-
        An idempotency key is a unique identifier you include with your API
        call. If the request fails or times out, you can safely retry it using
        the same key to avoid duplicate actions.
    x-idempotency-replayed:
      schema:
        type: string
        format: boolean
      example: 'true'
      description: |-
        In conjunction with `x-idempotency-key` this means
        - `true` if the response was replayed
        - `false` if the response has not been replayed.
  responses:
    Response400:
      description: Bad request error.
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/BadRequestError'
      headers:
        x-api-version:
          $ref: '#/components/headers/x-api-version'
        x-ratelimit-limit:
          $ref: '#/components/headers/x-ratelimit-limit'
        x-ratelimit-remaining:
          $ref: '#/components/headers/x-ratelimit-remaining'
        x-ratelimit-retry:
          $ref: '#/components/headers/x-ratelimit-retry'
        x-ratelimit-type:
          $ref: '#/components/headers/x-ratelimit-type'
        x-request-id:
          $ref: '#/components/headers/x-request-id'
        x-idempotency-key:
          $ref: '#/components/headers/x-idempotency-key'
        x-idempotency-replayed:
          $ref: '#/components/headers/x-idempotency-replayed'
    Response401:
      description: Authentication Error.
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/AuthenticationError'
      headers:
        x-api-version:
          $ref: '#/components/headers/x-api-version'
        x-ratelimit-limit:
          $ref: '#/components/headers/x-ratelimit-limit'
        x-ratelimit-remaining:
          $ref: '#/components/headers/x-ratelimit-remaining'
        x-ratelimit-retry:
          $ref: '#/components/headers/x-ratelimit-retry'
        x-ratelimit-type:
          $ref: '#/components/headers/x-ratelimit-type'
        x-request-id:
          $ref: '#/components/headers/x-request-id'
        x-idempotency-key:
          $ref: '#/components/headers/x-idempotency-key'
        x-idempotency-replayed:
          $ref: '#/components/headers/x-idempotency-replayed'
    Response404:
      description: Resource Not found.
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/ApiError404'
      headers:
        x-api-version:
          $ref: '#/components/headers/x-api-version'
        x-ratelimit-limit:
          $ref: '#/components/headers/x-ratelimit-limit'
        x-ratelimit-remaining:
          $ref: '#/components/headers/x-ratelimit-remaining'
        x-ratelimit-retry:
          $ref: '#/components/headers/x-ratelimit-retry'
        x-ratelimit-type:
          $ref: '#/components/headers/x-ratelimit-type'
        x-request-id:
          $ref: '#/components/headers/x-request-id'
        x-idempotency-key:
          $ref: '#/components/headers/x-idempotency-key'
        x-idempotency-replayed:
          $ref: '#/components/headers/x-idempotency-replayed'
    Response409:
      description: Resource already present.
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/ApiError409'
      headers:
        x-api-version:
          $ref: '#/components/headers/x-api-version'
        x-ratelimit-limit:
          $ref: '#/components/headers/x-ratelimit-limit'
        x-ratelimit-remaining:
          $ref: '#/components/headers/x-ratelimit-remaining'
        x-ratelimit-retry:
          $ref: '#/components/headers/x-ratelimit-retry'
        x-ratelimit-type:
          $ref: '#/components/headers/x-ratelimit-type'
        x-request-id:
          $ref: '#/components/headers/x-request-id'
        x-idempotency-key:
          $ref: '#/components/headers/x-idempotency-key'
        x-idempotency-replayed:
          $ref: '#/components/headers/x-idempotency-replayed'
    Response422:
      description: Idempotency error.
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/IdempotencyError'
      headers:
        x-api-version:
          $ref: '#/components/headers/x-api-version'
        x-ratelimit-limit:
          $ref: '#/components/headers/x-ratelimit-limit'
        x-ratelimit-remaining:
          $ref: '#/components/headers/x-ratelimit-remaining'
        x-ratelimit-retry:
          $ref: '#/components/headers/x-ratelimit-retry'
        x-ratelimit-type:
          $ref: '#/components/headers/x-ratelimit-type'
        x-request-id:
          $ref: '#/components/headers/x-request-id'
        x-idempotency-key:
          $ref: '#/components/headers/x-idempotency-key'
        x-idempotency-replayed:
          $ref: '#/components/headers/x-idempotency-replayed'
    Response429:
      description: Rate Limit Error.
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/RateLimitError'
      headers:
        x-api-version:
          $ref: '#/components/headers/x-api-version'
        x-ratelimit-limit:
          $ref: '#/components/headers/x-ratelimit-limit'
        x-ratelimit-remaining:
          $ref: '#/components/headers/x-ratelimit-remaining'
        x-ratelimit-retry:
          $ref: '#/components/headers/x-ratelimit-retry'
        x-ratelimit-type:
          $ref: '#/components/headers/x-ratelimit-type'
        x-request-id:
          $ref: '#/components/headers/x-request-id'
        x-idempotency-key:
          $ref: '#/components/headers/x-idempotency-key'
        x-idempotency-replayed:
          $ref: '#/components/headers/x-idempotency-replayed'
    Response500:
      description: API related Error.
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/ApiError'
      headers:
        x-api-version:
          $ref: '#/components/headers/x-api-version'
        x-ratelimit-limit:
          $ref: '#/components/headers/x-ratelimit-limit'
        x-ratelimit-remaining:
          $ref: '#/components/headers/x-ratelimit-remaining'
        x-ratelimit-retry:
          $ref: '#/components/headers/x-ratelimit-retry'
        x-ratelimit-type:
          $ref: '#/components/headers/x-ratelimit-type'
        x-request-id:
          $ref: '#/components/headers/x-request-id'
        x-idempotency-key:
          $ref: '#/components/headers/x-idempotency-key'
        x-idempotency-replayed:
          $ref: '#/components/headers/x-idempotency-replayed'
    Response502:
      description: Bank related Error.
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/ApiError502'
      headers:
        x-api-version:
          $ref: '#/components/headers/x-api-version'
        x-ratelimit-limit:
          $ref: '#/components/headers/x-ratelimit-limit'
        x-ratelimit-remaining:
          $ref: '#/components/headers/x-ratelimit-remaining'
        x-ratelimit-retry:
          $ref: '#/components/headers/x-ratelimit-retry'
        x-ratelimit-type:
          $ref: '#/components/headers/x-ratelimit-type'
        x-request-id:
          $ref: '#/components/headers/x-request-id'
        x-idempotency-key:
          $ref: '#/components/headers/x-idempotency-key'
        x-idempotency-replayed:
          $ref: '#/components/headers/x-idempotency-replayed'
  securitySchemes:
    XClientID:
      type: apiKey
      in: header
      name: x-client-id
      description: >-
        Client app ID. You can find your app id in the [Merchant
        Dashboard](https://merchant.cashfree.com/auth/login/pg/developers/api-keys?env=prod).
    XClientSecret:
      type: apiKey
      in: header
      name: x-client-secret
      description: >-
        Client secret key. You can find your secret key in the [Merchant
        Dashboard](https://merchant.cashfree.com/auth/login/pg/developers/api-keys?env=prod).
    XPartnerAPIKey:
      type: apiKey
      in: header
      name: x-partner-apikey
      description: >-
        If you are partner and you are making an api call on behalf of a
        merchant.
    XClientSignatureHeader:
      type: apiKey
      in: header
      name: x-client-signature
      description: >-
        Use this if you do not want to pass the secret key and instead want to
        use signature.
    XPartnerMerchantID:
      type: apiKey
      in: header
      name: x-partner-merchantid
      description: >-
        If you are partner use this to specify the merchant ID if you don't have
        the merchant client app ID.

````