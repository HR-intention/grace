### Connector Information
- **Connector Name:** Cashfree Payment Gateway
- **Base URLs:**
  - Sandbox: `https://sandbox.cashfree.com/pg` or `https://sandbox.cashfree.com/pg/`
  - Production: `https://cashfree.com/pg/` or `https://api.cashfree.com/pg`
- **Additional URLs:**
  - Webhooks: Specified by the merchant in the order creation (`notify_url`)
  - Documentation: `https://www.cashfree.com/docs/llms.txt`

### Authentication Details
- **Authentication Methods:**
  1. `x-client-id` + `x-client-secret`
  2. `x-client-id` + `x-partner-apikey`
  3. `x-client-id` + `x-client-signature`
  4. `x-partner-merchantid` + `x-partner-apikey`
- **Headers:**
  - `x-api-version`: API version (e.g., `2025-01-01`)
  - `x-client-id`: Client app ID
  - `x-client-secret`: Client secret key
  - `Content-Type`: `application/json`
- **Notes:**
  - Separate credentials for each Cashfree product
  - Never expose secret keys to client-side applications
  - Store credentials securely

### Complete Endpoint Inventory
#### 1. Order Pay (S2S) - `POST /orders/sessions`
- **HTTP Method:** POST
- **URL:** `/orders/sessions`
- **Headers:**
  - `x-api-version`
  - `x-request-id` (optional)
  - `x-idempotency-key` (optional)
- **Request Body:**
  - `payment_session_id`
  - `payment_method`
- **Response:**
  - `payment_amount`
  - `cf_payment_id`
  - `payment_method`
  - `channel`
  - `action`
  - `data`
- **Notes:**
  - Does not require credentials
  - May be invoked directly from client-side applications

#### 2. Get Payment by ID - `GET /orders/{order_id}/payments/{cf_payment_id}`
- **HTTP Method:** GET
- **URL:** `/orders/{order_id}/payments/{cf_payment_id}`
- **Headers:**
  - Same as authentication headers
- **Path Parameters:**
  - `order_id`
  - `cf_payment_id`
- **Response:**
  - `cf_payment_id`
  - `order_id`
  - `payment_status`
  - `payment_amount`
  - `payment_currency`
  - `payment_time`
  - `payment_completion_time`
  - `payment_message`
  - `bank_reference`
  - `auth_id`
  - `payment_group`
- **Notes:**
  - Returns payment details by ID

#### 3. Get Payments for Order - `GET /orders/{order_id}/payments`
- **HTTP Method:** GET
- **URL:** `/orders/{order_id}/payments`
- **Headers:**
  - Same as authentication headers
- **Path Parameters:**
  - `order_id`
- **Response:**
  - List of payments for the order
- **Notes:**
  - Returns all payments for an order

#### 4. Preauthorisation - `POST /orders/{order_id}/authorization`
- **HTTP Method:** POST
- **URL:** `/orders/{order_id}/authorization`
- **Headers:**
  - Same as authentication headers
- **Path Parameters:**
  - `order_id`
- **Request Body:**
  - Authorization details
- **Response:**
  - Authorization result
- **Notes:**
  - Preauthorizes a payment

#### 5. Submit or Resend OTP - `POST /orders/pay/authenticate/{cf_payment_id}`
- **HTTP Method:** POST
- **URL:** `/orders/pay/authenticate/{cf_payment_id}`
- **Headers:**
  - Same as authentication headers
- **Path Parameters:**
  - `cf_payment_id`
- **Request Body:**
  - OTP details
- **Response:**
  - Authentication result
- **Notes:**
  - Submits or resends OTP for payment authentication

#### 6. Create Order - `POST /orders`
- **HTTP Method:** POST
- **URL:** `/orders`
- **Headers:**
  - Same as authentication headers
- **Request Body:**
  - `order_amount`
  - `order_currency`
  - `customer_details`
- **Response:**
  - `cf_order_id`
  - `order_id`
  - `entity`
  - `order_amount`
  - `order_currency`
  - `order_status`
  - `payment_session_id`
  - `order_expiry_time`
- **Notes:**
  - Creates a new order

#### 7. Get Order - `GET /orders/{order_id}`
- **HTTP Method:** GET
- **URL:** `/orders/{order_id}`
- **Headers:**
  - Same as authentication headers
- **Path Parameters:**
  - `order_id`
- **Response:**
  - Order details
- **Notes:**
  - Returns order details by ID

#### 8. Terminate Order - `PATCH /orders/{order_id}`
- **HTTP Method:** PATCH
- **URL:** `/orders/{order_id}`
- **Headers:**
  - Same as authentication headers
- **Path Parameters:**
  - `order_id`
- **Request Body:**
  - Termination details
- **Response:**
  - Termination result
- **Notes:**
  - Terminates an order

#### 9. Create Refund - `POST /orders/{order_id}/refunds`
- **HTTP Method:** POST
- **URL:** `/orders/{order_id}/refunds`
- **Headers:**
  - Same as authentication headers
- **Path Parameters:**
  - `order_id`
- **Request Body:**
  - Refund details
- **Response:**
  - Refund result
- **Notes:**
  - Creates a new refund

#### 10. Get Refund - `GET /orders/{order_id}/refunds/{refund_id}`
- **HTTP Method:** GET
- **URL:** `/orders/{order_id}/refunds/{refund_id}`
- **Headers:**
  - Same as authentication headers
- **Path Parameters:**
  - `order_id`
  - `refund_id`
- **Response:**
  - Refund details
- **Notes:**
  - Returns refund details by ID

#### 11. Get All Refunds for Order - `GET /orders/{order_id}/refunds`
- **HTTP Method:** GET
- **URL:** `/orders/{order_id}/refunds`
- **Headers:**
  - Same as authentication headers
- **Path Parameters:**
  - `order_id`
- **Response:**
  - List of refunds for the order
- **Notes:**
  - Returns all refunds for an order

### Flow Categories
- **Payment/Authorization flows:**
  - Order Pay (S2S)
  - Get Payment by ID
  - Preauthorisation
  - Submit or Resend OTP
- **Capture operations:**
  - Not explicitly mentioned
- **Refund processes:**
  - Create Refund
  - Get Refund
  - Get All Refunds for Order
- **Status/sync endpoints:**
  - Get Payment by ID
  - Get Payments for Order
  - Get Order
- **Dispute handling:**
  - Not explicitly mentioned
- **Tokenization/vaulting:**
  - Not explicitly mentioned
- **Webhook endpoints:**
  - Payment webhooks (e.g., `PAYMENT_SUCCESS_WEBHOOK`)
- **Account/configuration endpoints:**
  - Create Order
  - Get Order
  - Terminate Order

### Configuration Parameters
- **Environment variables:**
  - `x-api-version`
  - `x-client-id`
  - `x-client-secret`
- **Settings:**
  - API version
  - Client ID
  - Client secret
- **Supported features:**
  - Payments
  - Refunds
  - Orders
- **Currencies:**
  - INR (Indian Rupee)
- **Regions:**
  - India
- **Integration requirements:**
  - API keys
  - Client ID
  - Client secret