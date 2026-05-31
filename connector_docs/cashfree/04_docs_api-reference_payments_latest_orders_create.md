> ## Documentation Index
> Fetch the complete documentation index at: https://www.cashfree.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# Create Order

> 

An order is an entity which has a amount and currency associated with it. It is something for which you want to collect payment for.
Use this API to create orders with Cashfree from your backend to get a `payment_sessions_id`. 
You can use the `payment_sessions_id` to create a transaction for the order.


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
  href="https://www.postman.com/cashfreedevelopers/workspace/cashfree-apis-v2025-01-01/request/40140981-853f8d3b-ad14-4481-a429-5d0972b8bea0"
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


## OpenAPI

````yaml /openapi/payments/v2025-01-01.yaml post /orders
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
  /orders:
    post:
      tags:
        - Orders
      summary: Create Order
      description: >


        An order is an entity which has a amount and currency associated with
        it. It is something for which you want to collect payment for.

        Use this API to create orders with Cashfree from your backend to get a
        `payment_sessions_id`. 

        You can use the `payment_sessions_id` to create a transaction for the
        order.
      operationId: PGCreateOrder
      parameters:
        - $ref: '#/components/parameters/apiVersionHeader'
        - $ref: '#/components/parameters/xRequestIDHeader'
        - $ref: '#/components/parameters/xIdempotencyKeyHeader'
      requestBody:
        $ref: '#/components/requestBodies/CreateOrderRequest'
      responses:
        '200':
          description: >-
            Success response for creating orders with Cashfree from your backend
            to get a `payment_sessions_id`.
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/OrderEntity'
              examples:
                create_order_success:
                  value:
                    cf_order_id: '2149460581'
                    created_at: '2023-08-11T18:02:46+05:30'
                    customer_details:
                      customer_id: '409128494'
                      customer_name: John Doe
                      customer_email: pmlpayme@ntsas.com
                      customer_phone: '9876543210'
                      customer_uid: 54deabb4-ba45-4a60-9e6a-9c016fe7ab10
                    entity: order
                    order_amount: 22
                    payment_session_id: >-
                      session_a1VXIPJo8kh7IBigVXX8LgTMupQW_cu25FS8KwLwQLOmiHqbBxq5UhEilrhbDSKKHA6UAuOj9506aaHNlFAHEqYrHSEl9AVtYQN9LIIc4vkH
                    order_currency: INR
                    order_expiry_time: '2023-09-09T18:02:46+05:30'
                    order_id: order_3242Tq4Edj9CC5RDcMeobmJOWOBJij
                    order_meta:
                      return_url: https://www.cashfree.com/devstudio/thankyou
                      payment_methods: cc
                      notify_url: https://example.com/cf_notify
                    order_note: Order created for payment
                    order_splits: []
                    order_status: ACTIVE
                    order_tags:
                      name: John
                      age: '19'
                    terminal_data: null
                    cart_details:
                      cart_id: '1'
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
      callbacks:
        PaymentWebhook:
          object Object:
            description: payment webhook object.
            post:
              summary: Received payment success webhook
              security: []
              requestBody:
                required: true
                content:
                  application/json:
                    schema:
                      type: object
                      properties:
                        data:
                          type: object
                          description: webhook object.
                          properties:
                            order:
                              type: object
                              description: order entity in webhook.
                              properties:
                                order_id:
                                  type: string
                                order_amount:
                                  type: number
                                  format: double
                                order_currency:
                                  type: string
                                order_tags:
                                  type: object
                                  maxProperties: 15
                                  description: >-
                                    Custom Tags in the form of {"key":"value"}
                                    which can be passed for an order. A maximum
                                    of 10 tags can be added.
                                  additionalProperties:
                                    type: string
                                    minLength: 1
                                    maxLength: 255
                            payment:
                              allOf:
                                - $ref: '#/components/schemas/PaymentEntity'
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
                            payment_offers:
                              type: array
                              items:
                                $ref: '#/components/schemas/OfferEntity'
                            customer_details:
                              type: object
                              description: customer details object in webhook.
                              properties:
                                customer_name:
                                  type: string
                                  example: Yogesh
                                customer_id:
                                  type: string
                                  example: '12121212'
                                customer_email:
                                  type: string
                                  example: yogesh.miglani@gmail.com
                                customer_phone:
                                  type: string
                                  example: '9666699999'
                        event_time:
                          type: string
                          example: '2021-10-07T19:42:44+05:30'
                        type:
                          type: string
                          example: PAYMENT_SUCCESS_WEBHOOK
              responses:
                '200':
                  description: OK
                4XX:
                  description: NOT OK. Webhook will be retried.
                5XX:
                  description: NOT OK. Webhook will be retried.
              method: post
              type: path
            path: object Object
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
  requestBodies:
    CreateOrderRequest:
      required: true
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/CreateOrderRequest'
          examples:
            order_with_minimum_fields:
              $ref: '#/components/examples/order_with_minimum_fields'
            order_with_order_id:
              $ref: '#/components/examples/order_with_order_id'
            order_with_customer_details:
              $ref: '#/components/examples/order_with_customer_details'
            order_with_return_url:
              $ref: '#/components/examples/order_with_return_url'
            order_with_payment_methods:
              $ref: '#/components/examples/order_with_payment_methods'
            order_with_tags:
              $ref: '#/components/examples/order_with_tags'
            order_split_by_amount_tags:
              $ref: '#/components/examples/order_split_by_amount_tags'
            order_split_by_percentage:
              $ref: '#/components/examples/order_split_by_percentage'
            order_with_invoice_details:
              $ref: '#/components/examples/order_with_invoice_details'
            order_tpv:
              $ref: '#/components/examples/order_tpv'
            order_with_payment_methods_filters:
              $ref: '#/components/examples/order_with_payment_methods_filters'
      description: >-
        Request parameters to create orders with Cashfree from your backend to
        get a `payment_sessions_id`.
  schemas:
    OrderEntity:
      title: OrderEntity
      type: object
      example:
        $ref: '#/components/examples/order_entity_list_example/value/0'
      properties:
        cf_order_id:
          type: string
          description: unique id generated by cashfree for your order.
        order_id:
          type: string
          description: order_id sent during the api request.
        entity:
          type: string
          description: Type of the entity.
        order_currency:
          type: string
          description: Currency of the order. Example INR.
        order_amount:
          type: number
        order_status:
          type: string
          description: >-
            Possible values are 

            - `ACTIVE`: Order does not have a sucessful transaction yet

            - `PAID`: Order is PAID with one successful transaction

            - `EXPIRED`: Order was not PAID and not it has expired. No
            transaction can be initiated for an EXPIRED order.

            `TERMINATED`: Order terminated

            `TERMINATION_REQUESTED`: Order termination requested.
        payment_session_id:
          type: string
        order_expiry_time:
          type: string
        order_note:
          type: string
          description: Additional note for order.
        created_at:
          type: string
          description: When the order was created at cashfree's server.
          example: '2022-08-16T14:45:38+05:30'
        order_splits:
          type: array
          items:
            $ref: '#/components/schemas/VendorSplit'
        customer_details:
          $ref: '#/components/schemas/CustomerDetailsResponse'
        order_meta:
          $ref: '#/components/schemas/OrderMeta'
        order_tags:
          $ref: '#/components/schemas/OrderTags'
        cart_details:
          $ref: '#/components/schemas/CartDetailsEntity'
        terminal_data:
          $ref: '#/components/schemas/TerminalData'
        products:
          type: object
          description: >-
            Configurations for the products like One Click Checkout, Verify and
            Pay, if they are enabled for your account.
          properties:
            one_click_checkout:
              $ref: '#/components/schemas/ProductDetailsEntity'
            verify_pay:
              $ref: '#/components/schemas/ProductDetailsEntity'
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
    OfferEntity:
      title: OfferEntity
      type: object
      description: Offer entity object.
      properties:
        offer_id:
          type: string
          example: d2b430fb-1afe-455a-af31-66d00377b29a
        offer_status:
          type: string
          example: active
        order_amount:
          type: number
          format: float64
        payable_amount:
          type: number
          format: float64
        offer_meta:
          allOf:
            - $ref: '#/components/schemas/OfferMetaResponse'
          example:
            $ref: '#/components/schemas/OfferMetaResponse/example'
        offer_tnc:
          allOf:
            - $ref: '#/components/schemas/OfferTncResponse'
          example:
            $ref: '#/components/schemas/OfferTncResponse/example'
        offer_details:
          allOf:
            - $ref: '#/components/schemas/OfferDetailsResponse'
          example:
            $ref: '#/components/schemas/OfferDetailsResponse/example'
        offer_validations:
          allOf:
            - $ref: '#/components/schemas/OfferValidationsResponse'
          example:
            $ref: '#/components/schemas/OfferValidationsResponse/example'
    CreateOrderRequest:
      title: CreateOrderRequest
      type: object
      properties:
        order_id:
          type: string
          description: >-
            Order identifier present in your system. Alphanumeric, '_' and '-'
            only.
          minLength: 3
          maxLength: 45
          example: your-order-id
        order_amount:
          type: number
          description: >-
            Bill amount for the order. Provide upto two decimals. 10.15 means Rs
            10 and 15 paisa. For orders in non-INR currency, please refer to
            [supported
            amounts](https://www.cashfree.com/docs/payments/international-payments/ipg/currencies-supported#decimal-support)
            per currency.
          format: double
          example: 10.15
          minimum: 1
        order_currency:
          type: string
          description: >-
            Currency for the order. INR if left empty. For support currency
            list, refer
            [here](https://www.cashfree.com/docs/payments/international-payments/ipg/currencies-supported#full-currency-list).
            Submit [Support Form](https://merchant.cashfree.com/auth/login) to
            enable new currencies.
          example: INR
        cart_details:
          allOf:
            - $ref: '#/components/schemas/CartDetails'
        customer_details:
          allOf:
            - $ref: '#/components/schemas/CustomerDetails'
          example:
            customer_id: 7112AAA812234
            customer_email: john@cashfree.com
            customer_phone: '9908734801'
        terminal:
          allOf:
            - $ref: '#/components/schemas/TerminalDetails'
          example:
            terminal_phone_no: '6309291183'
            terminal_id: terminal-1212
            terminal_type: SPOS
        order_meta:
          allOf:
            - $ref: '#/components/schemas/OrderMeta'
          example:
            return_url: https://www.cashfree.com/devstudio/thankyou
            payment_methods: cc,dc
        order_expiry_time:
          type: string
          format: ISO8601
          description: >-
            Time after which the order expires. Customers will not be able to
            make the payment beyond the time specified here. We store timestamps
            in IST, but you can provide them in a valid ISO 8601 time format.
            Example 2021-07-02T10:20:12+05:30 for IST, 2021-07-02T10:20:12Z for
            UTC
          example: '2021-07-02T10:20:12+05:30'
        order_note:
          type: string
          description: Order note for reference.
          example: Test order
          minLength: 3
          maxLength: 200
        order_tags:
          allOf:
            - $ref: '#/components/schemas/OrderTags'
          example:
            name: John Doe
            city: Bangalore
        order_splits:
          type: array
          description: >-
            If you have Easy split enabled in your Cashfree account then you can
            use this option to split the order amount.
          items:
            $ref: '#/components/schemas/VendorSplit'
          example:
            - amount: 10
              vendor: john
        products:
          title: products
          type: object
          description: >-
            Use this to set configurations for the products like One Click
            Checkout, Verify and Pay, if they are enabled for your account.
          properties:
            one_click_checkout:
              allOf:
                - $ref: '#/components/schemas/ProductDetails'
            verify_pay:
              allOf:
                - $ref: '#/components/schemas/ProductDetails'
      required:
        - order_amount
        - order_currency
        - customer_details
    VendorSplit:
      title: VendorSplit
      description: >-
        Use to split order when cashfree's Easy Split is enabled for your
        account.
      type: object
      example:
        vendor_id: Vendor01
        amount: 100.12
        description: order amount should be more than equal to 100.12.
      properties:
        vendor_id:
          type: string
          description: Vendor id created in Cashfree system.
        amount:
          type: number
          description: Amount which will be associated with this vendor.
        percentage:
          type: number
          description: Percentage of order amount which shall get added to vendor account.
        tags:
          type: object
          maxProperties: 15
          description: >-
            Custom Tags in the form of {"key":"value"} which can be passed for
            an order. A maximum of 10 tags can be added.
          additionalProperties:
            type: object
      required:
        - vendor_id
    CustomerDetailsResponse:
      title: CustomerDetailsResponse
      description: >-
        The customer details that are necessary. Note that you can pass dummy
        details if your use case does not require the customer details.
      example:
        customer_id: 7112AAA812234
        customer_email: john@cashfree.com
        customer_phone: '9908734801'
        customer_name: John Doe
        customer_bank_account_number: '1518121112'
        customer_bank_ifsc: XITI0000001
        customer_bank_code: 3333
        customer_uid: 54deabb4-ba45-4a60-9e6a-9c016fe7ab10
      type: object
      properties:
        customer_id:
          type: string
          description: A unique identifier for the customer. Use alphanumeric values only.
          minLength: 3
          maxLength: 50
        customer_email:
          type: string
          description: Customer email address.
          minLength: 3
          maxLength: 100
        customer_phone:
          type: string
          description: Customer phone number.
          minLength: 10
          maxLength: 10
        customer_name:
          type: string
          description: Name of the customer.
          minLength: 3
          maxLength: 100
        customer_bank_account_number:
          type: string
          description: >-
            Customer bank account. Required if you want to do a bank account
            check (TPV).
          minLength: 3
          maxLength: 20
        customer_bank_ifsc:
          type: string
          description: >-
            Customer bank IFSC. Required if you want to do a bank account check
            (TPV).
        customer_bank_code:
          type: number
          description: >-
            Customer bank code. Required for net banking payments, if you want
            to do a bank account check (TPV).
        customer_uid:
          type: string
          description: >-
            Customer identifier at Cashfree. You will get this when you
            create/get customer.
    OrderMeta:
      title: OrderMeta
      description: >-
        Optional meta details to control how the customer pays and how payment
        journey completes.
      type: object
      properties:
        return_url:
          type: string
          example: >-
            https://www.cashfree.com/devstudio/thankyou?order_id=devstudio_734905336776434862
          description: >-
            This is the
            [URL](https://www.cashfree.com/devstudio/thankyou?order_id=devstudio_734905336776434862)
            to which the customer will be redirected after the payment reaches a
            terminal state (success, failed or cancelled). We recommend keeping
            context of `order_id` in your `return_url` so that you can identify
            the order when customer lands on your page. Cashfree triggers a
            **GET request** to this URL.

            Maximum URL length: 250 characters.
        notify_url:
          type: string
          example: https://example.com/cf_notify
          description: >-
            Notification URL for server-server communication. Useful when user's
            connection drops while re-directing. NotifyUrl should be an https
            URL. Maximum length: 250.
        payment_methods:
          example: cc,dc,upi
          description: >-
            Specifies the allowed payment modes for this order. To restrict
            payment options,  provide a comma-separated list of values from the
            following options: `cc`, `dc`, `ccc`,  `ppc`, `nb`, `upi`, `paypal`,
            `app`, `paylater`, `cardlessemi`, `dcemi`, `ccemi`,  `banktransfer`,
            `applepay`. Leave this field blank to display all available payment
            methods.
        payment_methods_filters:
          description: >-
            Allowed payment modes for this order. Along with multiple filters
            for cards can be added to this key. And this filtering will be
            honoured during transaction creation.
          type: object
          properties:
            methods:
              description: >-
                Allowed payment modes for this order. credit_card, debit_card,
                netbanking, paylater, etc are the values that can be passed to
                this parameter.
              type: object
              properties:
                action:
                  type: string
                  description: >-
                    It accepts value of "ALLOW" and allows only those modes
                    present in it's neighbouring parameter "values.".
                values:
                  type: array
                  items:
                    type: string
                  description: >-
                    The accepted entries for this paramter are "debit_card,
                    credit_card, prepaid_card, upi, wallet, netbanking,
                    banktransfer, paylater, paypal, debit_card_emi,
                    credit_card_emi, upi_credit_card, upi_ppi, cardless_emi,
                    account_based_payment, corporate_credit_card,
                    sbc_debit_card, sbc_emandate, sbc_upi, sbc_credit_card.".
            filters:
              $ref: '#/components/schemas/OrderPaymentMethodFilters'
    OrderTags:
      type: object
      maxProperties: 15
      description: >-
        Custom Tags in the form of {"key":"value"} which can be passed for an
        order. A maximum of 10 tags can be added.
      additionalProperties:
        type: string
        minLength: 1
        maxLength: 255
      example:
        product: Laptop
        shipping_address: 123 Main St.
    CartDetailsEntity:
      title: CartDetailsEntity
      description: Cart Details in the Order Entity Response.
      type: object
      properties:
        cart_id:
          type: string
          description: ID of the cart that was created.
    TerminalData:
      description: Terminal Data in the create order response.
      example:
        agent_mobile_number: '9876543214'
        cf_terminal_id: 1838
        merchant_terminal_id: ahdsgadjhgfaj7137e
        terminal_type: STOREFRONT
      properties:
        agent_mobile_number:
          type: string
        cf_terminal_id:
          type: integer
        merchant_terminal_id:
          type: string
        terminal_type:
          type: string
      title: TerminalData
      type: object
    ProductDetailsEntity:
      type: object
      description: Configurations for this feature.
      properties:
        enabled:
          type: boolean
          description: Whether the feature has been enabled for this order.
        conditions:
          type: array
          description: Configured condtions for the feature.
          items:
            $ref: '#/components/schemas/ProductConditionsEntity'
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
    OfferMetaResponse:
      description: Offer meta response details object.
      example:
        offer_code: CFTESTOFFER
        offer_description: some offer description
        offer_end_time: '2023-03-29T08:09:51Z'
        offer_start_time: '2023-03-21T08:09:51Z'
        offer_title: some title
      properties:
        offer_code:
          description: Unique identifier for the Offer.
          example: CFTESTOFFER
          maxLength: 45
          minLength: 1
          type: string
        offer_description:
          description: Description for the Offer.
          example: Lorem ipsum dolor sit amet, consectetur adipiscing elit
          maxLength: 100
          minLength: 3
          type: string
        offer_end_time:
          description: Expiry Time for the Offer.
          example: '2023-03-29T08:09:51Z'
          type: string
        offer_start_time:
          description: Start Time for the Offer.
          example: '2023-03-21T08:09:51Z'
          maxLength: 20
          minLength: 3
          type: string
        offer_title:
          description: Title for the Offer.
          example: Test Offer
          maxLength: 50
          minLength: 3
          type: string
      title: OfferMetaResponse
      type: object
    OfferTncResponse:
      description: Offer terms and condition object.
      example:
        offer_tnc_type: text
        offer_tnc_value: TnC for the Offer.
      properties:
        offer_tnc_type:
          description: TnC Type for the Offer. It can be either `text` or `link`.
          enum:
            - text
            - link
          example: text
          maxLength: 50
          minLength: 3
          type: string
        offer_tnc_value:
          description: TnC for the Offer.
          example: Lorem ipsum dolor sit amet, consectetur adipiscing elit
          maxLength: 100
          minLength: 3
          type: string
      title: OfferTncResponse
      type: object
    OfferDetailsResponse:
      description: Offer details response and type.
      example:
        cashback_details:
          cashback_type: percentage
          cashback_value: '20'
          max_cashback_amount: '150'
        discount_details:
          discount_type: flat
          discount_value: '10'
          max_discount_amount: '10'
        offer_type: DISCOUNT_AND_CASHBACK
      properties:
        cashback_details:
          $ref: '#/components/schemas/CashbackDetails'
        discount_details:
          $ref: '#/components/schemas/DiscountDetails'
        offer_type:
          description: Offer Type for the Offer.
          enum:
            - DISCOUNT
            - CASHBACK
            - DISCOUNT_AND_CASHBACK
            - NO_COST_EMI
          example: DISCOUNT_AND_CASHBACK
          maxLength: 50
          minLength: 3
          type: string
      title: OfferDetailsResponse
      type: object
    OfferValidationsResponse:
      description: Offer validation object.
      example:
        max_allowed: 2
        min_amount: 10
        payment_method:
          wallet:
            issuer: paytm
      properties:
        max_allowed:
          description: Maximum Amount for Offer to be Applicable.
          example: 1
          minimum: 1
          type: number
        min_amount:
          description: Minimum Amount for Offer to be Applicable.
          example: 1
          minimum: 1
          type: number
        payment_method:
          example:
            wallet:
              issuer: paytm
          oneOf:
            - $ref: '#/components/schemas/OfferAll'
            - $ref: '#/components/schemas/OfferCard'
            - $ref: '#/components/schemas/OfferNB'
            - $ref: '#/components/schemas/OfferWallet'
            - $ref: '#/components/schemas/OfferUPI'
            - $ref: '#/components/schemas/OfferPaylater'
            - $ref: '#/components/schemas/OfferEMI'
      title: OfferValidationsResponse
      type: object
    CartDetails:
      title: CartDetails
      description: >-
        The cart details that are necessary like shipping address, billing
        address and more.
      type: object
      properties:
        customer_note:
          type: string
        shipping_charge:
          type: number
          format: double
        cart_name:
          type: string
          description: Name of the cart.
        customer_shipping_address:
          $ref: '#/components/schemas/CartAddress'
        customer_billing_address:
          $ref: '#/components/schemas/CartAddress'
        cart_items:
          type: array
          items:
            $ref: '#/components/schemas/CartItem'
    CustomerDetails:
      title: CustomerDetails
      description: >-
        The customer details that are necessary. Note that you can pass dummy
        details if your use case does not require the customer details.
      example:
        customer_id: 7112AAA812234
        customer_email: john@cashfree.com
        customer_phone: '9908734801'
        customer_name: John Doe
        customer_bank_account_number: '1518121112'
        customer_bank_ifsc: XITI0000001
        customer_bank_code: 3333
        customer_uid: 54deabb4-ba45-4a60-9e6a-9c016fe7ab10
      type: object
      properties:
        customer_id:
          type: string
          description: A unique identifier for the customer. Use alphanumeric values only.
          minLength: 3
          maxLength: 50
        customer_email:
          type: string
          description: Customer email address.
          minLength: 3
          maxLength: 100
        customer_phone:
          type: string
          description: >-
            Customer phone number. To accommodate international phone numbers,
            ensure the number is prefixed with a '+' to override the 10-digit
            limitation.
          minLength: 10
          maxLength: 10
        customer_name:
          type: string
          description: Name of the customer.
          minLength: 3
          maxLength: 100
        customer_bank_account_number:
          type: string
          description: >-
            Customer's bank account number. This field is required only if you
            want to perform a bank account check (TPV).
          minLength: 3
          maxLength: 20
        customer_bank_ifsc:
          type: string
          description: >-
            Customer's bank IFSC. Required if you want to do a bank account
            check (TPV).
        customer_bank_code:
          type: number
          description: >-
            Customer's bank code. Required for net banking payments, if you want
            to do a bank account check (TPV).
        customer_uid:
          type: string
          description: >-
            Customer's identifier at Cashfree. You will get this when you
            create/get customer.
      required:
        - customer_id
        - customer_phone
    TerminalDetails:
      description: Use this if you are creating an order for cashfree's softPOS.
      example:
        added_on: '2023-08-04T13:12:58+05:30'
        cf_terminal_id: 31051123
        last_updated_on: '2023-09-06T14:07:00+05:30'
        terminal_address: Banglore
        terminal_id: terminal-123
        terminal_name: test
        terminal_note: POS vertical
        terminal_phone_no: '6309291183'
        terminal_status: ACTIVE
        terminal_type: SPOS
      properties:
        added_on:
          description: date time at which terminal is added.
          type: string
        cf_terminal_id:
          description: >-
            Cashfree terminal ID, this is a required parameter when you do not
            provide the terminal phone number.
          type: integer
          format: int64
        last_updated_on:
          description: last instant when this terminal was updated.
          type: string
        terminal_address:
          description: location of terminal.
          type: string
        terminal_id:
          description: terminal id for merchant reference.
          maxLength: 100
          minLength: 3
          type: string
        terminal_name:
          description: name of terminal/agent/storefront.
          type: string
        terminal_note:
          description: note given by merchant while creating the terminal.
          type: string
        terminal_phone_no:
          description: >-
            mobile num of the terminal/agent/storefront,This is a required
            parameter when you do not provide the cf_terminal_id.
          type: string
        terminal_status:
          description: status of terminal active/inactive.
          type: string
        terminal_type:
          description: >-
            To identify the type of terminal product in use, in this case it is
            SPOS.
          maxLength: 10
          minLength: 4
          type: string
      required:
        - terminal_type
      title: Terminal
      type: object
    ProductDetails:
      type: object
      description: Specify the required configurations for this feature.
      properties:
        enabled:
          type: boolean
          description: Option to enable or disable the feature.
        conditions:
          type: array
          description: >-
            The conditions array allows to configure rules by adding condition
            objects with specific parameters for feature configurations.
          items:
            $ref: '#/components/schemas/ProductConditions'
    OrderPaymentMethodFilters:
      title: OrderPaymentMethodFilters
      description: >-
        Filters for this order. Card bins, card schemes, card issuing bank and
        card suffixes.
      type: object
      properties:
        card_emi_tenure:
          type: integer
          minimum: 3
          maximum: 36
          description: Allowed card EMI tenure for the order.
        card_emi_bins:
          type: array
          items:
            type: integer
            minimum: 100000
            maximum: 999999
          description: Allowed card EMI bins for the order.
        card_emi_schemes:
          type: array
          items:
            type: string
          description: Allowed card EMI schemes for the order.
        card_emi_suffix:
          type: array
          items:
            type: integer
          description: Allowed card EMI suffixes for the order.
        card_emi_issuing_bank:
          type: array
          items:
            type: string
          description: Allowed card EMI issuing bank for the order.
        card_bins:
          type: array
          items:
            type: integer
            minimum: 100000
            maximum: 999999
          description: Allowed card bins for the order.
        card_schemes:
          type: array
          items:
            type: string
          description: Allowed card schemes for the order.
        card_suffix:
          type: array
          items:
            type: integer
          description: Allowed card suffixes for the order.
        card_issuing_bank:
          type: array
          items:
            type: string
          description: Allowed card issuing bank for the order.
    ProductConditionsEntity:
      type: object
      properties:
        action:
          type: string
          description: >-
            The Action key in the conditions array specifies whether a condition
            is allowed or denied for the specified rule or feature.
        key:
          type: string
          description: key of the condition.
          maxLength: 50
        values:
          type: array
          description: Values set for the condition.
          maxItems: 10
          items:
            type: string
    CashbackDetails:
      title: CashbackDetails
      description: Cashback detail boject.
      example:
        cashback_type: percentage
        cashback_value: '20'
        max_cashback_amount: '150'
      type: object
      properties:
        cashback_type:
          type: string
          description: Type of discount.
          enum:
            - flat
            - percentage
          minLength: 1
          maxLength: 50
        cashback_value:
          type: number
          format: float64
          description: Value of Discount.
        max_cashback_amount:
          type: number
          format: float64
          description: Maximum Value of Cashback allowed.
      required:
        - cashback_type
        - cashback_value
        - max_cashback_amount
    DiscountDetails:
      title: DiscountDetails
      description: detils of the discount object of offer.
      example:
        discount_type: flat
        discount_value: '10'
        max_discount_amount: '10'
      type: object
      properties:
        discount_type:
          type: string
          description: Type of discount.
          enum:
            - flat
            - percentage
          minLength: 3
          maxLength: 50
        discount_value:
          type: number
          format: float64
          description: Value of Discount.
        max_discount_amount:
          type: number
          format: float64
          description: Maximum Value of Discount allowed.
      required:
        - discount_type
        - discount_value
        - max_discount_amount
    OfferAll:
      title: All Offers
      description: returns all offers.
      example:
        all: {}
      type: object
      properties:
        all:
          $ref: '#/components/schemas/AllOffers'
      required:
        - all
    OfferCard:
      title: Card Offer
      description: Offers related to cards.
      example:
        card:
          type:
            - cc
          bank_name: hdfc bank
          scheme_name:
            - visa
      type: object
      properties:
        card:
          title: Card Offer
          type: object
          properties:
            type:
              type: array
              items:
                $ref: '#/components/schemas/CardArray'
            bank_name:
              type: string
              description: Bank Name of Card.
              minLength: 3
              maxLength: 100
              example: hdfc bank
            scheme_name:
              type: array
              items:
                $ref: '#/components/schemas/SchemeArray'
          required:
            - type
            - bank_name
            - scheme_name
      required:
        - card
    OfferNB:
      title: Net Banking Offer
      description: Offer object ofr NetBanking.
      example:
        netbanking:
          bank_name: hdfc bank
      type: object
      properties:
        netbanking:
          type: object
          properties:
            bank_name:
              type: string
              example: all
      required:
        - netbanking
    OfferWallet:
      title: Wallet Offer
      description: Offer object for wallet payment method.
      example:
        app:
          issuer: paytm
      type: object
      properties:
        app:
          title: Wallet Offer
          type: object
          properties:
            provider:
              type: string
              example: paytm
      required:
        - app
    OfferUPI:
      title: UPI Offer
      description: Offer object for UPI.
      example:
        upi: {}
      type: object
      properties:
        upi:
          title: UPI Offer
          type: object
      required:
        - upi
    OfferPaylater:
      title: Paylater Offer
      description: Offer object for paylater.
      example:
        paylater:
          issuer: lazypay
      type: object
      properties:
        paylater:
          title: Paylater Offer
          type: object
          properties:
            provider:
              type: string
              example: simpl
      required:
        - paylater
    OfferEMI:
      title: EMI Offer
      description: EMI offer object.
      type: object
      example:
        emi:
          type: cardless_emi
          issuer: hdfc bank
          tenures:
            - 3
            - 6
      properties:
        emi:
          title: EMI Offer
          type: object
          properties:
            type:
              type: string
              description: >-
                Type of emi offer. Possible values are `credit_card_emi`,
                `debit_card_emi`, `cardless_emi`.
              minLength: 3
              maxLength: 100
              example: cardless_emi
            issuer:
              type: string
              description: Bank Name.
              minLength: 3
              maxLength: 100
              example: hdfc bank
            tenures:
              type: array
              items:
                title: Tenure Array
                type: integer
                example: 3
          required:
            - type
            - issuer
            - tenures
      required:
        - emi
    CartAddress:
      title: CartAddress
      description: Address given for cart details.
      properties:
        full_name:
          type: string
        country:
          type: string
        city:
          type: string
        state:
          type: string
        pincode:
          type: string
        address_1:
          type: string
        address_2:
          type: string
    CartItem:
      title: CartItem
      description: Each item in the cart.
      properties:
        item_id:
          type: string
          description: Unique identifier of the item.
        item_name:
          type: string
          description: Name of the item.
        item_description:
          type: string
          description: Description of the item.
        item_tags:
          type: array
          items:
            type: string
          description: Tags attached to that item.
        item_details_url:
          type: string
          description: Item details url.
        item_image_url:
          type: string
          description: Item image url.
        item_original_unit_price:
          type: number
          format: double
          description: Original price.
        item_discounted_unit_price:
          type: number
          format: double
          description: Discounted Price.
        item_currency:
          type: string
          description: Currency of the item.
        item_quantity:
          type: number
          format: int32
          description: Quantity if that item.
    ProductConditions:
      type: object
      properties:
        action:
          type: string
          description: >-
            The Action key in the conditions array specifies whether a condition
            should "ALLOW" or "DENY" the specified rule or feature.
        key:
          type: string
          description: Specify what you're trying to configure, such as "features.".
          maxLength: 50
        values:
          type: array
          description: >-
            Define the values you need to set within the conditions in this
            array, such as "checkoutCollectAddress", "checkoutAuthenticate".
          maxItems: 10
          items:
            type: string
    AllOffers:
      title: All Offers
      type: object
      description: All offers applicable.
    CardArray:
      title: card array
      description: short code for credit card, debit card, prepaid card.
      type: string
      example: dc
    SchemeArray:
      title: Scheme array
      type: string
      example: visa
      description: array of card schemes like visa, master etc.
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
  examples:
    order_with_minimum_fields:
      summary: Minimun required details
      description: Minimum set of parameters needed to create an order at cashfree.
      value:
        order_currency: INR
        order_amount: 10.34
        customer_details:
          customer_id: 7112AAA812234
          customer_phone: '9898989898'
    order_with_order_id:
      summary: Specify your order_id
      description: >-
        You should always send `order_id`. If not sent Cashfree will generate
        one for you. This is useful during other api calls.
      value:
        order_id: playstation_purchase_1
        order_currency: INR
        order_amount: 10.34
        customer_details:
          customer_id: 7112AAA812234
          customer_phone: '9908734801'
    order_with_customer_details:
      summary: Customer Details
      description: Complete customer details.
      value:
        order_id: playstation_purchase_1
        order_currency: INR
        order_amount: 10.34
        customer_details:
          customer_id: 7112AAA812234
          customer_name: John Doe
          customer_phone: 9908734801
          customer_email: john@example.com
          customer_bank_ifsc: XDFC0000045
          customer_bank_account_number: 123124123123123
          customer_bank_code: 3021
    order_with_return_url:
      summary: With return/callback URL
      description: add a return url to your order.
      value:
        order_id: playstation_purchase_2
        order_currency: INR
        order_amount: 10.34
        customer_details:
          customer_id: 7112AAA812234
          customer_phone: '9898989898'
        order_meta:
          return_url: https://www.cashfree.com/devstudio/thankyou
    order_with_payment_methods:
      summary: With Payment Methods URL
      description: >-
        add payment methods, customer can pnly pay using these payment methods
        only.
      value:
        order_id: playstation_purchase_4
        order_currency: INR
        order_amount: 10.34
        customer_details:
          customer_id: 7112AAA812234
          customer_phone: '9898989898'
        order_meta:
          return_url: https://www.cashfree.com/devstudio/thankyou
          payment_methods: cc,dc,upi
    order_with_tags:
      summary: With order tags
      description: Add key value pairs to your order. Can be used later in your workflow.
      value:
        order_id: playstation_purchase_6
        order_currency: INR
        order_amount: 10.34
        customer_details:
          customer_id: 7112AAA812234
          customer_phone: '9898989898'
        order_tags:
          address: Bengaluru, India
          pincode: '560034'
    order_split_by_amount_tags:
      summary: With order split Amount
      description: >-
        Create an order where the amount received will be split between vendor
        and merchant based on absolute amount.
      value:
        order_id: playstation_purchase_8
        order_currency: INR
        order_amount: 10.34
        customer_details:
          customer_id: 7112AAA812234
          customer_phone: '9898989898'
        order_splits:
          - vendor_id: Jane
            amount: 1.45
            tags:
              address: Hyderabad
          - vendor_id: Barbie
            amount: 3.45
            tags:
              address: Bengaluru, India.
    order_split_by_percentage:
      summary: With order split Percentage
      description: >
        Create an order where the amount received will be split between vendors
        and merchant based on percentage.

        In the below example order amount, let us say INR 200 will be divided
        like this

        - 33% to merchant becomes INR 66 

        - 20% to Jane becomes INR 40

        - 47% to Barbie becomes INR 94
      value:
        order_id: playstation_purchase_8
        order_currency: INR
        order_amount: 10.34
        customer_details:
          customer_id: 7112AAA812234
          customer_phone: '9898989898'
        order_splits:
          - vendor_id: Jane
            percentage: 20
          - vendor_id: Barbie
            percentage: 47
    order_with_invoice_details:
      summary: With order invoice
      description: Add invoice details for your order.
      value:
        order_id: playstation_purchase_6
        order_currency: INR
        order_amount: 10.34
        customer_details:
          customer_id: 7112AAA812234
          customer_phone: '9898989898'
        order_tags:
          gst: '1'
          gstin: 27AAFCN5072P1ZV
          invoice_date: '2023-06-20T04:35:16.748Z'
          invoice_number: inv1687149916474
          invoice_link: https://example.com/cf/nextgen.php#section-2
          invoice_name: Walters Invoice
          cgst: '1'
          sgst: '1'
          igst: '1'
          cess: '1'
          gst_incentive: '1'
          gst_percentage: '1'
          pincode: '560034'
          city_tier: TIER1
    order_tpv:
      summary: Customer TPV
      description: >-
        Customer with bank details if provided he or she can pay by only that
        bank account.
      value:
        order_id: playstation_purchase_1
        order_currency: INR
        order_amount: 10.34
        customer_details:
          customer_id: 7112AAA812234
          customer_name: John Doe
          customer_phone: '9908734801'
          customer_email: john@example.com
          customer_bank_ifsc: XDFC0000045
          customer_bank_account_number: '123124123123123'
          customer_bank_code: 3021
    order_with_payment_methods_filters:
      summary: With Payment Methods Filters
      description: add payment methods, customer can pay using these payment methods only.
      value:
        order_id: playstation_purchase_4
        order_currency: INR
        order_amount: 10.34
        customer_details:
          customer_id: 7112AAA812234
          customer_phone: '9898989898'
        order_meta:
          return_url: https://www.cashfree.com/devstudio/thankyou
          payment_methods_filters:
            methods:
              action: ALLOW
              values:
                - debit_card
                - credit_card
                - credit_card_emi
                - debit_card_emi
            filters:
              card_bins:
                - 441144
                - 554455
              card_schemes:
                - VISA
                - MASTERCARD
              card_suffix:
                - 4433
                - 8910
              card_emi_tenure: 6
              card_emi_bins:
                - 441144
                - 554455
              card_emi_schemes:
                - VISA
                - MASTERCARD
              card_emi_suffix:
                - 4433
                - 8910
              card_emi_issuing_bank:
                - HDFC
                - ICICI
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