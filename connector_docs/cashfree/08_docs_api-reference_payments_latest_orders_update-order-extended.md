> ## Documentation Index
> Fetch the complete documentation index at: https://www.cashfree.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# Update Order Extended

> Use this api to update the order related data like shipment details,order delivery status etc.
## When to use this API
- To provide/update the shipment details or order delivery status.
- Once the order is PAID.


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
  href="https://www.postman.com/cashfreedevelopers/workspace/cashfree-apis-v2025-01-01/request/40140981-c8ecbfba-de79-43bc-b347-d5854e1a0b43"
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

````yaml /openapi/payments/v2025-01-01.yaml put /orders/{order_id}/extended
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
    put:
      tags:
        - Orders
      summary: Update Order Extended
      description: >
        Use this api to update the order related data like shipment
        details,order delivery status etc.

        ## When to use this API

        - To provide/update the shipment details or order delivery status.

        - Once the order is PAID.
      operationId: PGUpdateOrderExtendedData
      parameters:
        - $ref: '#/components/parameters/apiVersionHeader'
        - $ref: '#/components/parameters/xRequestIDHeader'
        - $ref: '#/components/parameters/orderIDParam'
        - $ref: '#/components/parameters/xIdempotencyKeyHeader'
      requestBody:
        $ref: '#/components/requestBodies/UpdateOrderExtendedRequest'
      responses:
        '200':
          description: >-
            Success response for updating the order related data like shipment
            details,order delivery status etc.
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/UpdateOrderExtendedDataEntity'
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
  requestBodies:
    UpdateOrderExtendedRequest:
      description: >-
        Request parameters to update the order related data like shipment
        details,order delivery status etc.
      required: true
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/UpdateOrderExtendedRequest'
          examples:
            order_extended_minimum:
              $ref: '#/components/examples/order_extended_minimum'
            order_extended_delivery_status:
              $ref: '#/components/examples/order_extended_delivery_status'
            order_extended_all_field:
              $ref: '#/components/examples/order_extended_all_field'
  schemas:
    UpdateOrderExtendedDataEntity:
      title: UpdateOrderExtendedDataEntity
      type: object
      example:
        $ref: >-
          #/components/examples/update_order_extended_data_entity_list_example/value/0
      properties:
        cf_order_id:
          type: string
          description: unique id generated by cashfree for your order.
        order_id:
          type: string
          description: order_id sent during the api request.
        shipment_details:
          type: array
          items:
            $ref: '#/components/schemas/ShipmentDetails'
        order_delivery_status:
          $ref: '#/components/schemas/OrderDeliveryStatus'
    UpdateOrderExtendedRequest:
      title: Update Order Extended
      type: object
      properties:
        shipment_details:
          type: array
          description: >-
            Shipment details, such as the tracking company, tracking number, and
            tracking URLs, associated with the shipping of an order. Either
            `shipment_details` or `order_delivery_status` is required.
          items:
            $ref: '#/components/schemas/ShipmentDetails'
        order_delivery_status:
          allOf:
            - $ref: '#/components/schemas/OrderDeliveryStatus'
          example:
            status: SHIPPED
            reason: shipped
      required:
        - shipment_details
    ShipmentDetails:
      title: ShipmentDetails
      description: >-
        Shipment details associated with shipping of order like tracking
        company, tracking number,tracking urls etc.
      properties:
        tracking_company:
          type: string
          description: Tracking company name associated with order.
          example: DHL
        tracking_urls:
          type: array
          description: Tracking Urls associated with order.
          items:
            type: string
            example: https://dhl.com/track/123456
        tracking_numbers:
          type: array
          description: Tracking Numbers associated wih order.
          items:
            type: string
            example: TRACK654321
      required:
        - tracking_company
        - tracking_urls
        - tracking_numbers
    OrderDeliveryStatus:
      title: OrderDeliveryStatus
      description: Order delivery Status associated with order.
      properties:
        status:
          type: string
          enum:
            - AWAITING_PICKUP
            - CANCELLED
            - SELF_FULFILLED
            - PICKED_UP
            - SHIPPED
            - IN_TRANSIT
            - DELAY_COURIER_COMPANY_ISSUES
            - DELAY_INCORRECT_ADDRESS
            - DELAY_SELLER_ISSUES
            - REACHED_DESTINATION_HUB
            - OUT_FOR_DELIVERY
            - DELIVERED
            - POTENTIAL_RTO_DELIVERY_ATTEMPTED
            - RTO
            - LOST
            - DAMAGED
            - UNTRACKABLE_404
            - MANUAL_INTERVENTION_BROKEN_URL
            - ASSOCIATED_WITH_RETURN_PICKUP
            - UNSERVICEABLE
          description: Delivery status of order.
          example: CANCELLED
        reason:
          type: string
          description: Reason of provided order delivery status. This is optional field.
          example: cancelled due to wrong address
      required:
        - status
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
    order_extended_minimum:
      summary: Minimun required details
      description: Minimum set of parameters needed to update shipment details.
      value:
        shipment_details:
          - tracking_company: DHL
            tracking_urls:
              - https://dhl.com/track/123456
            tracking_numbers:
              - TRACK123456
    order_extended_delivery_status:
      summary: Minimum required deatils for status
      description: Minimum set of parameters needed to update shipment details.
      value:
        order_delivery_status:
          status: CANCELLED
          reason: wrong address
    order_extended_all_field:
      summary: With Shipment detail and delivery status
      description: Request with all fields.
      value:
        shipment_details:
          - tracking_company: DHL
            tracking_urls:
              - https://dhl.com/track/123456
            tracking_numbers:
              - TRACK123456
        order_delivery_status:
          status: CANCELLED
          reason: wrong address
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