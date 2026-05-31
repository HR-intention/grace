> ## Documentation Index
> Fetch the complete documentation index at: https://www.cashfree.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# Get Order Extended

> Use this API to fetch the order related data like address,cart,offers,customer details etc using the Cashfree's `order_id`.
## When to use this API
- To get the extended data associated with order.


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
  href="https://www.postman.com/cashfreedevelopers/workspace/cashfree-apis-v2025-01-01/request/40140981-30a37636-529a-4056-82dd-ee8d34639885"
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

````yaml /openapi/payments/v2025-01-01.yaml get /orders/{order_id}/extended
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
  /orders/{order_id}/extended:
    get:
      tags:
        - Orders
      summary: Get Order Extended
      description: >
        Use this API to fetch the order related data like
        address,cart,offers,customer details etc using the Cashfree's
        `order_id`.

        ## When to use this API

        - To get the extended data associated with order.
      operationId: PGFetchOrderExtendedData
      parameters:
        - $ref: '#/components/parameters/apiVersionHeader'
        - $ref: '#/components/parameters/xRequestIDHeader'
        - $ref: '#/components/parameters/orderIDParam'
        - $ref: '#/components/parameters/xIdempotencyKeyHeader'
      responses:
        '200':
          description: >-
            Success response for fetching the order related data like
            address,cart,offers,customer details etc using the Cashfree's
            `order_id`.
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/OrderExtendedDataEntity'
              examples:
                get_order_extended_success:
                  value:
                    cf_order_id: '2149460581'
                    order_id: order_3242Tq4Edj9CC5RDcMeobmJOWOBJij
                    order_amount: 22
                    order_currency: INR
                    created_at: '2023-08-11T18:02:46+05:30'
                    charges:
                      shipping_charges: 5
                      cod_handling_charges: 10
                    customer_details:
                      customer_id: '409128494'
                      customer_name: Aditya Keshri
                      customer_email: pmlpayme@ntsas.com
                      customer_phone: '9876543210'
                      customer_uid: 54deabb4-ba45-4a60-9e6a-9c016fe7ab10
                    shipping_address:
                      name: Saurav Singh
                      address_line_one: MK Building
                      address_line_two: Test Address
                      country: India
                      country_code: IN
                      state: Karnataka
                      state_code: KA
                      city: Bangalore
                      pin_code: '560034'
                      phone: +91 1118911189
                      email: test@cashfree.com
                    billing_address:
                      name: Saurav Singh
                      address_line_one: MK Building
                      address_line_two: Test Address
                      country: India
                      country_code: IN
                      state: Karnataka
                      state_code: KA
                      city: Bangalore
                      pin_code: '560034'
                      phone: +91 1118911189
                      email: test@cashfree.com
                    cart:
                      name: test
                      items:
                        - item_id: '26'
                          item_name: Sample Product
                          item_description: item-description
                          item_tags:
                            - '1'
                            - '2'
                          item_details_url: http://cashfree.com
                          item_image_url: http://cashfree.com
                          item_original_unit_price: '1'
                          item_discounted_unit_price: '1'
                          item_quantity: 1
                          item_currency: INR
                    offer:
                      offer_id: d2b430fb-1afe-455a-af31-66d00377b29a
                      offer_status: active
                      offer_meta:
                        offer_title: some title
                        offer_description: some offer description
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
    OrderExtendedDataEntity:
      title: OrderExtendedDataEntity
      type: object
      example:
        $ref: '#/components/examples/order_extended_data_entity_list_example/value/0'
      properties:
        cf_order_id:
          type: string
          description: unique id generated by cashfree for your order.
        order_id:
          type: string
          description: order_id sent during the api request.
        order_amount:
          type: number
        order_currency:
          type: string
          description: Currency of the order. Example INR.
        created_at:
          type: string
          description: When the order was created at cashfree's server.
          example: '2022-08-16T14:45:38+05:30'
        charges:
          $ref: '#/components/schemas/ChargesEntity'
        customer_details:
          $ref: '#/components/schemas/ExtendedCustomerDetails'
        shipping_address:
          $ref: '#/components/schemas/AddressDetails'
        billing_address:
          $ref: '#/components/schemas/AddressDetails'
        cart:
          $ref: '#/components/schemas/ExtendedCartDetails'
        offer:
          $ref: '#/components/schemas/OfferExtendedDetails'
    ChargesEntity:
      title: ChargesEntity
      description: Charges accociated with the order.
      type: object
      example:
        shipping_charges: 5
        cod_handling_charges: 10
      properties:
        shipping_charges:
          type: number
          description: Shipping charge of the order.
        cod_handling_charges:
          type: number
          description: COD handling fee for order.
    ExtendedCustomerDetails:
      title: CustomerDetails
      description: Recent Customer details associated with the order.
      example:
        customer_id: 7112AAA812234
        customer_email: john@cashfree.com
        customer_phone: '9908734801'
        customer_name: John Doe
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
        customer_uid:
          type: string
          description: >-
            Customer identifier at Cashfree. You will get this when you
            create/get customer.
    AddressDetails:
      title: AddressDetails
      description: Address associated with the customer.
      type: object
      example:
        name: Aditya Keshri
        address_line_one: MK Building
        address_line_two: Test Address
        country: India
        country_code: IN
        state: Karnataka
        state_code: KA
        city: Bangalore
        pin_code: '560034'
        phone: +91 1118911189
        email: test@cashfree.com
      properties:
        name:
          type: string
          description: Full Name of the customer associated with the address.
        address_line_one:
          type: string
          description: First line of the address.
        address_line_two:
          type: string
          description: Second line of the address.
        country:
          type: string
          description: Country Name.
        country_code:
          type: string
          description: Country Code.
        state:
          type: string
          description: State Name.
        state_code:
          type: string
          description: State Code.
        city:
          type: string
          description: City Name.
        pin_code:
          type: string
          description: Pin Code/Zip Code.
        phone:
          type: string
          description: Customer Phone Number.
        email:
          type: string
          description: Cutomer Email Address.
    ExtendedCartDetails:
      title: CartDetails
      description: >-
        The cart details that are necessary like shipping address, billing
        address and more.
      type: object
      properties:
        name:
          type: string
          description: Name of the cart.
        items:
          type: array
          items:
            $ref: '#/components/schemas/CartItem'
    OfferExtendedDetails:
      title: OfferEntity
      type: object
      description: Details of the offer which got applied to the paid order.
      properties:
        offer_id:
          type: string
          example: d2b430fb-1afe-455a-af31-66d00377b29a
        offer_status:
          type: string
          example: active
        offer_meta:
          allOf:
            - $ref: '#/components/schemas/OfferMeta'
          example:
            $ref: '#/components/schemas/OfferMeta/example'
        offer_tnc:
          allOf:
            - $ref: '#/components/schemas/OfferTnc'
          example:
            $ref: '#/components/schemas/OfferTnc/example'
        offer_details:
          allOf:
            - $ref: '#/components/schemas/OfferDetails'
          example:
            $ref: '#/components/schemas/OfferDetails/example'
        offer_validations:
          allOf:
            - $ref: '#/components/schemas/OfferValidations'
          example:
            $ref: '#/components/schemas/OfferValidations/example'
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
    OfferMeta:
      title: OfferMeta
      type: object
      description: Offer meta details object.
      example:
        offer_title: some title
        offer_description: some offer description
        offer_code: CFTESTOFFER
        offer_start_time: '2023-03-21T08:09:51Z'
        offer_end_time: '2023-03-29T08:09:51Z'
      properties:
        offer_title:
          description: Title for the Offer.
          example: Test Offer
          maxLength: 50
          minLength: 3
          type: string
        offer_description:
          description: Description for the Offer.
          example: Lorem ipsum dolor sit amet, consectetur adipiscing elit
          maxLength: 100
          minLength: 3
          type: string
        offer_code:
          description: Unique identifier for the Offer.
          example: CFTESTOFFER
          maxLength: 45
          minLength: 1
          type: string
        offer_start_time:
          description: Start Time for the Offer.
          example: '2023-03-21T08:09:51Z'
          maxLength: 20
          minLength: 3
          type: string
        offer_end_time:
          description: Expiry Time for the Offer.
          example: '2023-03-29T08:09:51Z'
          type: string
      required:
        - offer_title
        - offer_description
        - offer_code
        - offer_start_time
        - offer_end_time
    OfferTnc:
      title: OfferMeta
      type: object
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
      required:
        - offer_tnc_type
        - offer_tnc_value
    OfferDetails:
      title: OfferDetails
      description: Offer details and type.
      type: object
      example:
        offer_type: DISCOUNT_AND_CASHBACK
        discount_details:
          discount_type: flat
          discount_value: '10'
          max_discount_amount: '10'
        cashback_details:
          cashback_type: percentage
          cashback_value: '20'
          max_cashback_amount: '150'
      properties:
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
        discount_details:
          $ref: '#/components/schemas/DiscountDetails'
        cashback_details:
          $ref: '#/components/schemas/CashbackDetails'
      required:
        - offer_type
    OfferValidations:
      title: OfferValidations
      description: Offer validation object.
      type: object
      example:
        min_amount: 10
        payment_method:
          wallet:
            issuer: paytm
        max_allowed: 2
      properties:
        min_amount:
          description: Minimum Amount for Offer to be Applicable.
          example: 1
          minimum: 1
          type: number
        max_allowed:
          description: Maximum Amount for Offer to be Applicable.
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
      required:
        - max_allowed
        - payment_method
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