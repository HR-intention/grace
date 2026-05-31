> ## Documentation Index
> Fetch the complete documentation index at: https://www.cashfree.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# Overview

> Explore the Cashfree Payment Gateway API reference covering orders, payments, refunds, settlements, and webhooks, with JSON request and response examples.

Cashfree's RESTful Payment Gateway API provides a robust and flexible interface for integrating payment solutions into your applications. The API uses predictable resource-oriented URLs, accepts JSON request bodies, returns JSON-encoded responses, and supports standard HTTP response codes and authentication. SDKs in popular programming languages help you integrate faster with pre-built handling for authentication, request or response formatting, and error handling.

<Tip>
  We strongly recommend using [SDKs](/api-reference/payments/sdk) to streamline the integration process and ensure optimal performance and security.
</Tip>

## Key features

The key features offered by Cashfree's Payment Gateway APIs are:

* **Orders and payments**: Create orders, collect payments via multiple methods (cards, UPI, netbanking, wallets), and retrieve order and payment status.
* **Payment links and refunds**: Generate shareable payment links, process refunds, and manage refund status.
* **Token Vault**: Save cards and tokenize them in a PCI-compliant manner; generate network tokens for use across acquiring banks.
* **Easy-Split**: Split payments between vendors, configure static or post-payment splits, and manage settlements.
* **Subscriptions**: Create plans and mandates, raise and manage recurring payments with support for UPI, card, and E-Mandate.
* **Eligibility and offers**: Check eligible payment methods, cardless EMI, paylater, and offers for orders; create and manage offers.
* **Settlements and disputes**: Fetch settlements, reconcile, and handle chargebacks and disputes via APIs.

<Tabs>
  <Tab title="Orders and payments">
    <div class="row relative lowmhr">
      <div class="col-md-6">
        <div class="">
          <h4 class="text-gray-800 semibold dark:text-gray-500 pb-4">Orders</h4>

          <div class="">
            <div>
              <a href="/docs/api-reference/payments/latest/orders/create" class="text-cf bold">Create Order</a>

              <p style={{marginBottom: '1rem'}} class="text-gray-500 dark:text-gray-500">
                Create an order to collect payments from your customers.
              </p>
            </div>
          </div>

          <hr />

          <div class="">
            <div>
              <a href="/docs/api-reference/payments/latest/orders/get" class="text-cf bold">Get Order</a>

              <p style={{marginBottom: '1rem'}} class="text-gray-500 dark:text-gray-500">
                Get status and details of an order.
              </p>
            </div>
          </div>

          <hr />

          <div class="">
            <div>
              <a href="/docs/api-reference/payments/latest/orders/terminate" class="text-cf bold">Terminate Order</a>

              <p style={{marginBottom: '1rem'}} class="text-gray-500 dark:text-gray-500">
                Terminate an order that is no longer needed.
              </p>
            </div>
          </div>

          <hr />

          <div class="">
            <div>
              <a href="/docs/api-reference/payments/latest/orders/get-order-extended" class="text-cf bold">Get Order Extended</a>

              <p style={{marginBottom: '1rem'}} class="text-gray-500 dark:text-gray-500">
                Fetch extended data for an order.
              </p>
            </div>
          </div>

          <hr />

          <div class="">
            <div>
              <a href="/docs/api-reference/payments/latest/orders/update-order-extended" class="text-cf bold">Update Order Extended</a>

              <p style={{marginBottom: '1rem'}} class="text-gray-500 dark:text-gray-500">
                Update extended data for an order.
              </p>
            </div>
          </div>

          <hr />

          <h4 class="text-gray-800 semibold dark:text-gray-500 pb-4">Customers</h4>

          <div class="">
            <div>
              <a href="/docs/api-reference/payments/latest/customers/create" class="text-cf bold">Create Customer</a>

              <p style={{marginBottom: '1rem'}} class="text-gray-500 dark:text-gray-500">
                Create a customer for Token Vault and saved instruments.
              </p>
            </div>
          </div>
        </div>
      </div>

      <div class="col-md-6">
        <div class="">
          <h4 class="text-gray-800 semibold dark:text-gray-500 pb-4">Payments</h4>

          <div class="">
            <div>
              <a href="/docs/api-reference/payments/latest/payments/pay" class="text-cf bold">Pay</a>

              <p style={{marginBottom: '1rem'}} class="text-gray-500 dark:text-gray-500">
                Initiate a payment for an order using the chosen payment method.
              </p>
            </div>
          </div>

          <hr />

          <div class="">
            <div>
              <a href="/docs/api-reference/payments/latest/payments/authenticate" class="text-cf bold">Authenticate</a>

              <p style={{marginBottom: '1rem'}} class="text-gray-500 dark:text-gray-500">
                Submit or resend OTP in the native OTP flow for card payments.
              </p>
            </div>
          </div>

          <hr />

          <div class="">
            <div>
              <a href="/docs/api-reference/payments/latest/payments/authorize" class="text-cf bold"> Authorise</a>

              <p style={{marginBottom: '1rem'}} class="text-gray-500 dark:text-gray-500">
                Capture or void a pre-authorised transaction.
              </p>
            </div>
          </div>

          <hr />

          <div class="">
            <div>
              <a href="/docs/api-reference/payments/latest/payments/get" class="text-cf bold">Get Payment</a>

              <p style={{marginBottom: '1rem'}} class="text-gray-500 dark:text-gray-500">
                Get status and details of a single payment.
              </p>
            </div>
          </div>

          <hr />

          <div class="">
            <div>
              <a href="/docs/api-reference/payments/latest/payments/get-payments-for-order" class="text-cf bold">Get Payments for Order</a>

              <p style={{marginBottom: '1rem'}} class="text-gray-500 dark:text-gray-500">
                Get status and details of all payments for an order.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </Tab>

  <Tab title="Links and refunds">
    <div class="row relative lowmhr">
      <div class="col-md-6">
        <div class="">
          <h4 class="text-gray-800 semibold dark:text-gray-500 pb-4">Payment links</h4>

          <div class="">
            <div>
              <a href="/docs/api-reference/payments/latest/payment-links/create" class="text-cf bold">Create Payment Link</a>

              <p style={{marginBottom: '1rem'}} class="text-gray-500 dark:text-gray-500">
                Create a shareable payment link for collecting payments.
              </p>
            </div>
          </div>

          <hr />

          <div class="">
            <div>
              <a href="/docs/api-reference/payments/latest/payment-links/get" class="text-cf bold">Get Payment Link</a>

              <p style={{marginBottom: '1rem'}} class="text-gray-500 dark:text-gray-500">
                Get details of a payment link.
              </p>
            </div>
          </div>

          <hr />

          <div class="">
            <div>
              <a href="/docs/api-reference/payments/latest/payment-links/cancel" class="text-cf bold">Cancel Payment Link</a>

              <p style={{marginBottom: '1rem'}} class="text-gray-500 dark:text-gray-500">
                Cancel an active payment link.
              </p>
            </div>
          </div>

          <hr />

          <div class="">
            <div>
              <a href="/docs/api-reference/payments/latest/payment-links/get-orders-for-link" class="text-cf bold">Get Orders for Link</a>

              <p style={{marginBottom: '1rem'}} class="text-gray-500 dark:text-gray-500">
                Fetch orders associated with a payment link.
              </p>
            </div>
          </div>
        </div>
      </div>

      <div class="col-md-6">
        <div class="">
          <h4 class="text-gray-800 semibold dark:text-gray-500 pb-4">Refunds</h4>

          <div class="">
            <div>
              <a href="/docs/api-reference/payments/latest/refunds/create" class="text-cf bold">Create Refund</a>

              <p style={{marginBottom: '1rem'}} class="text-gray-500 dark:text-gray-500">
                Create a refund for a payment (full or partial).
              </p>
            </div>
          </div>

          <hr />

          <div class="">
            <div>
              <a href="/docs/api-reference/payments/latest/refunds/get" class="text-cf bold">Get Refund</a>

              <p style={{marginBottom: '1rem'}} class="text-gray-500 dark:text-gray-500">
                Get status and details of a refund.
              </p>
            </div>
          </div>

          <hr />

          <div class="">
            <div>
              <a href="/docs/api-reference/payments/latest/refunds/get-refunds-for-order" class="text-cf bold">Get Refunds for Order</a>

              <p style={{marginBottom: '1rem'}} class="text-gray-500 dark:text-gray-500">
                Get all refunds for an order.
              </p>
            </div>
          </div>

          <hr />

          <div class="">
            <div>
              <a href="/docs/api-reference/payments/latest/refunds/update-refund" class="text-cf bold">Update Refund</a>

              <p style={{marginBottom: '1rem'}} class="text-gray-500 dark:text-gray-500">
                Update refund details or speed.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </Tab>

  <Tab title="Vault and offers">
    <div class="row relative lowmhr">
      <div class="col-md-6">
        <div class="">
          <h4 class="text-gray-800 semibold dark:text-gray-500 pb-4">Token Vault</h4>

          <div class="">
            <div>
              <a href="/docs/api-reference/payments/latest/token-vault/generate-cryptogram" class="text-cf bold">Generate Cryptogram</a>

              <p style={{marginBottom: '1rem'}} class="text-gray-500 dark:text-gray-500">
                Generate a cryptogram for a saved card to process a payment.
              </p>
            </div>
          </div>

          <hr />

          <div class="">
            <div>
              <a href="/docs/api-reference/payments/latest/token-vault/get-all" class="text-cf bold">Get All Saved Cards</a>

              <p style={{marginBottom: '1rem'}} class="text-gray-500 dark:text-gray-500">
                Fetch all saved card instruments for a customer.
              </p>
            </div>
          </div>

          <hr />

          <div class="">
            <div>
              <a href="/docs/api-reference/payments/latest/token-vault/get" class="text-cf bold">Get Saved Card</a>

              <p style={{marginBottom: '1rem'}} class="text-gray-500 dark:text-gray-500">
                Get details of a single saved card instrument.
              </p>
            </div>
          </div>

          <hr />

          <div class="">
            <div>
              <a href="/docs/api-reference/payments/latest/token-vault/delete" class="text-cf bold">Delete Saved Card</a>

              <p style={{marginBottom: '1rem'}} class="text-gray-500 dark:text-gray-500">
                Delete a saved card instrument for a customer.
              </p>
            </div>
          </div>
        </div>
      </div>

      <div class="col-md-6">
        <div class="">
          <h4 class="text-gray-800 semibold dark:text-gray-500 pb-4">Eligibility and offers</h4>

          <div class="">
            <div>
              <a href="/docs/api-reference/payments/latest/eligibility/get-eligible-payment-methods" class="text-cf bold">Get Eligible Payment Methods</a>

              <p style={{marginBottom: '1rem'}} class="text-gray-500 dark:text-gray-500">
                Fetch payment methods eligible for an order and account.
              </p>
            </div>
          </div>

          <hr />

          <div class="">
            <div>
              <a href="/docs/api-reference/payments/latest/eligibility/get-eligible-cardless-emi-payment-methods-for-a-customer-on-an-order" class="text-cf bold">Get Eligible Cardless EMI</a>

              <p style={{marginBottom: '1rem'}} class="text-gray-500 dark:text-gray-500">
                Get eligible cardless EMI options for a customer and order.
              </p>
            </div>
          </div>

          <hr />

          <div class="">
            <div>
              <a href="/docs/api-reference/payments/latest/eligibility/get-eligible-paylater-for-a-customer-on-an-order" class="text-cf bold">Get Eligible Paylater</a>

              <p style={{marginBottom: '1rem'}} class="text-gray-500 dark:text-gray-500">
                Get eligible paylater options for a customer and order.
              </p>
            </div>
          </div>

          <hr />

          <div class="">
            <div>
              <a href="/docs/api-reference/payments/latest/eligibility/get-eligible-offers-for-an-order" class="text-cf bold">Get Eligible Offers</a>

              <p style={{marginBottom: '1rem'}} class="text-gray-500 dark:text-gray-500">
                Get offers applicable to an order (e.g. no-cost EMI).
              </p>
            </div>
          </div>

          <hr />

          <div class="">
            <div>
              <a href="/docs/api-reference/payments/latest/offers/create" class="text-cf bold">Create Offer</a>

              <p style={{marginBottom: '1rem'}} class="text-gray-500 dark:text-gray-500">
                Create a new offer (card, netbanking, EMI, etc.).
              </p>
            </div>
          </div>

          <hr />

          <div class="">
            <div>
              <a href="/docs/api-reference/payments/latest/offers/get" class="text-cf bold">Get Offer</a>

              <p style={{marginBottom: '1rem'}} class="text-gray-500 dark:text-gray-500">
                Get details of an offer.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </Tab>

  <Tab title="Split and settlements">
    <div class="row relative lowmhr">
      <div class="col-md-6">
        <div class="">
          <h4 class="text-gray-800 semibold dark:text-gray-500 pb-4">Easy-Split</h4>

          <div class="">
            <div>
              <a href="/docs/api-reference/payments/latest/split/easy-split-overview" class="text-cf bold">Easy-Split Overview</a>

              <p style={{marginBottom: '1rem'}} class="text-gray-500 dark:text-gray-500">
                Overview of split payments and vendor settlements.
              </p>
            </div>
          </div>

          <hr />

          <div class="">
            <div>
              <a href="/docs/api-reference/payments/latest/split/end-points" class="text-cf bold">Easy-Split Endpoints</a>

              <p style={{marginBottom: '1rem'}} class="text-gray-500 dark:text-gray-500">
                API reference for split and vendor operations.
              </p>
            </div>
          </div>

          <hr />

          <div class="">
            <div>
              <a href="/docs/api-reference/payments/latest/split/vendors/create" class="text-cf bold">Create Vendor</a>

              <p style={{marginBottom: '1rem'}} class="text-gray-500 dark:text-gray-500">
                Create a vendor for receiving split payments.
              </p>
            </div>
          </div>

          <hr />

          <div class="">
            <div>
              <a href="/docs/api-reference/payments/latest/split/configuration/static-split" class="text-cf bold">Static Split</a>

              <p style={{marginBottom: '1rem'}} class="text-gray-500 dark:text-gray-500">
                Configure static split rules for orders.
              </p>
            </div>
          </div>

          <hr />

          <div class="">
            <div>
              <a href="/docs/api-reference/payments/latest/split/configuration/split-after-payment" class="text-cf bold">Split After Payment</a>

              <p style={{marginBottom: '1rem'}} class="text-gray-500 dark:text-gray-500">
                Create split for an order after payment is received.
              </p>
            </div>
          </div>

          <hr />

          <div class="">
            <div>
              <a href="/docs/api-reference/payments/latest/split/settlements/on-demand-transfer" class="text-cf bold">On-Demand Transfer</a>

              <p style={{marginBottom: '1rem'}} class="text-gray-500 dark:text-gray-500">
                Transfer vendor share on demand.
              </p>
            </div>
          </div>
        </div>
      </div>

      <div class="col-md-6">
        <div class="">
          <h4 class="text-gray-800 semibold dark:text-gray-500 pb-4">Settlements and more</h4>

          <div class="">
            <div>
              <a href="/docs/api-reference/payments/latest/settlements/get-settlements" class="text-cf bold">Get Settlements</a>

              <p style={{marginBottom: '1rem'}} class="text-gray-500 dark:text-gray-500">
                Fetch settlement details and history.
              </p>
            </div>
          </div>

          <hr />

          <div class="">
            <div>
              <a href="/docs/api-reference/payments/latest/settlements/mark-order-for-settlement" class="text-cf bold">Mark Order for Settlement</a>

              <p style={{marginBottom: '1rem'}} class="text-gray-500 dark:text-gray-500">
                Mark an order for instant settlement.
              </p>
            </div>
          </div>

          <hr />

          <div class="">
            <div>
              <a href="/docs/api-reference/payments/latest/disputes/get-disputes-by-order-id" class="text-cf bold">Get Disputes by Order</a>

              <p style={{marginBottom: '1rem'}} class="text-gray-500 dark:text-gray-500">
                Fetch disputes associated with an order.
              </p>
            </div>
          </div>

          <hr />

          <div class="">
            <div>
              <a href="/docs/api-reference/payments/latest/subscription/overview" class="text-cf bold">Subscription Overview</a>

              <p style={{marginBottom: '1rem'}} class="text-gray-500 dark:text-gray-500">
                Recurring payments: plans, mandates, and payment flows.
              </p>
            </div>
          </div>

          <hr />

          <div class="">
            <div>
              <a href="/docs/api-reference/payments/latest/subscription/mandate/create" class="text-cf bold">Create Subscription</a>

              <p style={{marginBottom: '1rem'}} class="text-gray-500 dark:text-gray-500">
                Create a subscription with mandate (UPI, card, E-Mandate).
              </p>
            </div>
          </div>

          <hr />

          <div class="">
            <div>
              <a href="/docs/api-reference/payments/latest/softpos/create-terminal" class="text-cf bold">softPOS: Create Terminal</a>

              <p style={{marginBottom: '1rem'}} class="text-gray-500 dark:text-gray-500">
                Create a softPOS terminal for in-person card acceptance.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </Tab>
</Tabs>

The videos below walk through testing Payment Gateway APIs in Postman and using this API reference.

<Columns cols={2}>
  <div>
    <Frame>
      <iframe width="100%" height="315" src="https://www.youtube.com/embed/OkzoR7K3yxw?enablejsapi=1" title="Testing in Postman" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen style={{ maxWidth: '560px' }} />
    </Frame>

    <p style={{ textAlign: 'center', fontSize: '14px', marginTop: '8px', color: '#666' }}>
      Testing APIs in Postman
    </p>
  </div>

  <div>
    <Frame>
      <iframe width="100%" height="315" src="https://www.youtube.com/embed/tqcOHCUZgOM?enablejsapi=1" title="Documentation walkthrough" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen style={{ maxWidth: '560px' }} />
    </Frame>

    <p style={{ textAlign: 'center', fontSize: '14px', marginTop: '8px', color: '#666' }}>
      Documentation Walkthrough
    </p>
  </div>
</Columns>

## Getting started

Use the following resources to begin implementing Payment Gateway APIs:

<CardGroup cols={2}>
  <Card title="Payment SDK" href="/api-reference/payments/sdk" icon="puzzle-piece">
    Integrate the Payment Gateway with web, mobile, and server SDKs for orders, checkout, and tokenisation
  </Card>

  <Card title="API rate limits" href="/api-reference/payments/rate-limits" icon="gauge-high">
    View default limits per minute, monitor usage on the dashboard, and request higher limits when needed
  </Card>
</CardGroup>
