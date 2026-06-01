> ## Documentation Index
> Fetch the complete documentation index at: https://www.cashfree.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# Get Order

> Use this API to fetch the order that was created at Cashfree's using the `order_id`. 
## When to use this API
- To check the status of your order


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
  href="https://www.postman.com/cashfreedevelopers/workspace/cashfree-apis-v2025-01-01/request/40140981-7717c469-8960-451c-aa16-0bdbdb4c3a88"
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

<Note>This API allows you to retrieve order data for the current and previous financial years. To access data older than this period, log in to the [Merchant Dashboard](https://merchant.cashfree.com/auth/login)</Note>


## OpenAPI

````yaml /openapi/payments/v2025-01-01.yaml get /orders/{order_id}
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
  /orders/{order_id}:
    get:
      tags:
        - Orders
      summary: Get Order
      description: >
        Use this API to fetch the order that was created at Cashfree's using the
        `order_id`. 

        ## When to use this API

        - To check the status of your order
      operationId: PGFetchOrder
      parameters:
        - $ref: '#/components/parameters/apiVersionHeader'
        - $ref: '#/components/parameters/xRequestIDHeader'
        - $ref: '#/components/parameters/orderIDParam'
        - $ref: '#/components/parameters/xIdempotencyKeyHeader'
      responses:
        '200':
          description: >-
            Success response for fetching the order that was created at
            Cashfree's using the `order_id`.
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/OrderEntity'
              examples:
                get_order_active:
                  summary: Active Order
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
                get_order_paid:
                  summary: Paid Order
                  value:
                    cf_order_id: '2149460582'
                    created_at: '2023-08-10T14:30:20+05:30'
                    customer_details:
                      customer_id: '409128495'
                      customer_name: Jane Smith
                      customer_email: jane.smith@example.com
                      customer_phone: '9876543211'
                      customer_uid: 64deabb4-ca45-4b60-9e6a-9c016fe7ab11
                    entity: order
                    order_amount: 150.5
                    payment_session_id: >-
                      session_b2VXIPJo8kh7IBigVXX8LgTMupQW_cu25FS8KwLwQLOmiHqbBxq5UhEilrhbDSKKHA6UAuOj9506aaHNlFAHEqYrHSEl9AVtYQN9LIIc4vkH
                    order_currency: INR
                    order_expiry_time: '2023-09-08T14:30:20+05:30'
                    order_id: order_4353Ur5Fgk0DD6SEfNfpcnKPXPCKjk
                    order_meta:
                      return_url: https://www.cashfree.com/devstudio/thankyou
                      payment_methods: upi,card,netbanking
                      notify_url: https://example.com/cf_notify
                    order_note: Payment completed successfully
                    order_splits: []
                    order_status: PAID
                    order_tags:
                      product: Premium Plan
                      category: subscription
                    terminal_data: null
                    cart_details:
                      cart_id: '2'
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