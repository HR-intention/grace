> ## Documentation Index
> Fetch the complete documentation index at: https://www.cashfree.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# Enums Reference

> Reference for enum values used in the Cashfree Payments API. Use it to interpret API responses, build conditional payment logic, and pass the correct values in API requests.

An enum (enumeration) is a data type that restricts a field to a specific set of
predefined string values. The Cashfree Payments API uses enums across requests and
responses to ensure that only valid, expected values are accepted or returned for a
given field.

The following are some examples of enum fields in the Cashfree Payments API:

* The `order_status` field returns one of `ACTIVE`, `PAID`, `EXPIRED`, or
  `TERMINATED`, never a free-form string.
* The `payment_status` field returns one of `SUCCESS`, `FAILED`, `PENDING`,
  `CANCELLED`, and others.
* Net banking and wallet codes are fixed numeric identifiers mapped to specific
  providers.

Because enum values are fixed and predictable, you can use them directly in
conditional logic, error handling, and status checks without accounting for
unexpected values.

## Order states

Order states represent the current status of an order throughout its lifecycle,
from creation to a terminal state such as paid or expired. Use these values to
determine whether an order is still open for payment or has reached a final state.

<Accordion title="Order states">
  An order moves through the following states based on payment outcomes and
  merchant actions.

  | Order State            | Description                                                                                                          | Remarks                                                                                                           |
  | :--------------------- | :------------------------------------------------------------------------------------------------------------------- | :---------------------------------------------------------------------------------------------------------------- |
  | ACTIVE                 | Order is created and ready for payment.                                                                              | Initial state for all newly created orders.                                                                       |
  | PAID                   | Payment is verified and successful.                                                                                  | Terminal state indicating the order is fully paid.                                                                |
  | EXPIRED                | Order has exceeded the `order_expiry_time` specified during creation.                                                | Further payment attempts are not allowed.                                                                         |
  | TERMINATED             | Order is ended using the [Order Termination API](/api-reference/payments/latest/orders/terminate).                   | Permanent terminal state; customers can no longer pay.                                                            |
  | TERMINATION\_REQUESTED | Call to the [Order Termination API](/api-reference/payments/latest/orders/terminate) is acknowledged and processing. | If a pending transaction succeeds during this state, the order transitions to **PAID** instead of **TERMINATED**. |
</Accordion>

## Payment states

Payment states indicate the status of an individual payment attempt within an
order. An order can have multiple payment attempts, and each attempt progresses
through its own states before reaching a terminal outcome such as `SUCCESS`
or `FAILED`.

<Accordion title="Payment states">
  Each payment attempt within an order has its own lifecycle. Use these states
  to handle granular payment scenarios.

  | Payment State  | Description                                                                         | Remarks                                                          |
  | :------------- | :---------------------------------------------------------------------------------- | :--------------------------------------------------------------- |
  | SUCCESS        | Transaction is successful and the amount is captured.                               | Terminal state. Once successful, the order moves to **PAID**.    |
  | FAILED         | Transaction failed due to bank, customer, or system issues.                         | Terminal state. Customers can initiate a new attempt.            |
  | NOT\_ATTEMPTED | Transaction is created but acknowledgement from the bank is awaited.                | Initial state for a payment attempt.                             |
  | PENDING        | Request is sent to the bank and a response is awaited.                              | Non-terminal state. Do not fulfil orders in this state.          |
  | FLAGGED        | Transaction is identified as high-risk and requires review.                         | Merchant must manually approve or reject the payment.            |
  | CANCELLED      | Amount is reversed because a success response arrived after the time to live (TTL). | Automatic system reversal for late confirmations.                |
  | VOID           | Transaction amount is not captured by explicit request.                             | Typically used for pre-authorised card payments or UPI mandates. |
  | USER\_DROPPED  | Customer abandoned the payment flow before completion.                              | Includes closing the app or OTP page without attempting payment. |
</Accordion>

## Net banking codes

Net banking codes identify the supported net banking providers. Pass the
**Bank Code** value in the `payment_method` parameter of your API request to
initiate a net banking transaction.

The **TPV Supported** column indicates whether the bank supports Third Party
Validation (TPV). When TPV is enabled, Cashfree Payments verifies that the
customer completes the payment from the specific bank account provided during
order creation.

<Accordion title="Netbanking codes">
  The following table lists the supported banks and their corresponding codes
  for net banking integrations.

  | Bank name                                   | Bank code | TPV supported |
  | ------------------------------------------- | --------- | ------------- |
  | Airtel Payments Bank                        | 3123      | N             |
  | Andhra Pragathi Grameena Bank               | 3094      | N             |
  | AU Small Finance Bank                       | 3087      | Y             |
  | Axis Bank                                   | 3003      | Y             |
  | Axis Bank - Corporate                       | 3071      | N             |
  | Bandhan Bank - Retail Banking               | 3088      | Y             |
  | Bank of Bahrain and Kuwait                  | 3095      | N             |
  | Bank of Baroda - Corporate                  | 3060      | Y             |
  | Bank of Baroda - Retail Banking             | 3005      | Y             |
  | Bank of India                               | 3006      | Y             |
  | Bank of India - Corporate                   | 3061      | N             |
  | Bank of Maharashtra                         | 3007      | N             |
  | Barclays - Corporate                        | 3080      | N             |
  | Canara Bank                                 | 3009      | Y             |
  | Capital Small Finance Bank                  | 3098      | Y             |
  | Central Bank of India                       | 3011      | N             |
  | City Union Bank                             | 3012      | Y             |
  | Cosmos Bank                                 | 3097      | Y             |
  | CSB Bank Limited                            | 3010      | Y             |
  | DBS Bank Ltd                                | 3017      | N             |
  | DCB Bank - Personal                         | 3018      | N             |
  | Deutsche Bank                               | 3016      | Y             |
  | Dhanlakshmi Bank                            | 3019      | Y             |
  | Dhanlaxmi Bank - Corporate                  | 3072      | N             |
  | Equitas Small Finance Bank                  | 3076      | N             |
  | ESAF Small Finance Bank                     | 3100      | N             |
  | Federal Bank                                | 3020      | Y             |
  | Fincare Bank                                | 3101      | N             |
  | Gujarat State Co-operative Bank Limited     | 3091      | Y             |
  | HDFC Bank                                   | 3021      | Y             |
  | HDFC Corporate                              | 3084      | N             |
  | HSBC Retail NetBanking                      | 3092      | Y             |
  | ICICI Bank                                  | 3022      | Y             |
  | ICICI Bank - Corporate                      | 3073      | N             |
  | IDBI Bank                                   | 3023      | Y             |
  | IDBI Bank - Corporate                       | 3124      | N             |
  | IDFC FIRST Bank                             | 3024      | Y             |
  | Indian Bank                                 | 3026      | Y             |
  | Indian Overseas Bank                        | 3027      | Y             |
  | Indian Overseas Bank - Corporate            | 3081      | N             |
  | IndusInd Bank                               | 3028      | Y             |
  | Jammu and Kashmir Bank                      | 3029      | Y             |
  | Jana Small Finance Bank                     | 3102      | Y             |
  | Janata Sahakari Bank Ltd Pune               | 3104      | N             |
  | Kalyan Janata Sahakari Bank                 | 3105      | N             |
  | Karnataka Bank Ltd                          | 3030      | Y             |
  | Karnataka Gramin Bank                       | 3113      | N             |
  | Karnataka Vikas Grameena Bank               | 3107      | N             |
  | Karur Vysya Bank                            | 3031      | Y             |
  | Kotak Mahindra Bank                         | 3032      | Y             |
  | Maharashtra Gramin Bank                     | 3108      | N             |
  | Mehsana urban Co-op Bank                    | 3109      | N             |
  | NKGSB Co-op Bank                            | 3111      | N             |
  | Nutan Nagarik Sahakari Bank Limited         | 3112      | N             |
  | Punjab & Sind Bank                          | 3037      | Y             |
  | Punjab National Bank - Corporate            | 3065      | N             |
  | Punjab National Bank - Retail Banking       | 3038      | Y             |
  | RBL Bank                                    | 3039      | Y             |
  | RBL Bank Limited - Corporate                | 3114      | N             |
  | Saraswat Bank                               | 3040      | Y             |
  | SBM Bank India                              | 3115      | Y             |
  | Shamrao Vithal Bank - Corporate             | 3075      | N             |
  | Shamrao Vitthal Co-operative Bank           | 3041      | N             |
  | Shivalik Small Finance Bank                 | 3086      | Y             |
  | South Indian Bank                           | 3042      | Y             |
  | Standard Chartered Bank                     | 3043      | Y             |
  | State Bank Of India                         | 3044      | Y             |
  | State Bank of India - Corporate             | 3066      | N             |
  | Suryoday Small Finance Bank                 | 3116      | N             |
  | Tamil Nadu State Co-operative Bank          | 3051      | N             |
  | Tamilnad Mercantile Bank Ltd                | 3052      | Y             |
  | Thane Bharat Sahakari Bank Ltd              | 3118      | N             |
  | The Kalupur Commercial Co-Operative Bank    | 3106      | N             |
  | The Surat Peoples Co-operative Bank Limited | 3090      | Y             |
  | The Sutex Co-op Bank Ltd                    | 3117      | Y             |
  | TJSB Bank                                   | 3119      | N             |
  | UCO Bank                                    | 3054      | Y             |
  | UCO Bank Corporate                          | 3122      | N             |
  | Ujjivan Small Finance Bank                  | 3126      | Y             |
  | Union Bank of India                         | 3055      | Y             |
  | Union Bank of India - Corporate             | 3067      | N             |
  | Utkarsh Small Finance Bank                  | 3089      | Y             |
  | Varachha Co-operative Bank Limited          | 3120      | N             |
  | Yes Bank - Corporate                        | 3077      | N             |
  | Yes Bank Ltd                                | 3058      | Y             |
  | Zoroastrian Co-Operative Bank Ltd           | 3121      | N             |
</Accordion>

## Wallet codes

Wallet codes identify the supported digital wallet providers. Pass the
**Payment Code** value in your API request to collect payments via a
specific wallet.

<Accordion title="Wallet codes">
  The following table lists the available wallet providers and their
  corresponding payment codes.

  | S. No | Wallet name           | Payment code |
  | :---- | :-------------------- | :----------- |
  | 1     | FreeCharge            | 4001         |
  | 2     | MobiKwik              | 4002         |
  | 3     | Ola Money             | 4003         |
  | 4     | Airtel Money          | 4006         |
  | 5     | Amazon Pay            | 4008         |
  | 6     | PayTM                 | 4007         |
  | 7     | PhonePe               | 4009         |
  | 8     | Test Wallet (Sandbox) | 4010         |
</Accordion>

## EMI codes

Equated Monthly Instalment (EMI) codes specify the available instalment plans
for supported banks and card types. Use these values to present EMI options to
customers during checkout.

The following attributes apply across all EMI plan tables:

* **card\_bank\_name**: The bank identifier to pass in the API request parameter.
* **Tenure**: The duration of the instalment plan, expressed in months.
* **Annual Interest Rate**: The yearly interest rate applied to the
  transaction amount, expressed as a percentage.

<Tip>
  Verify that the transaction amount falls within the **Minimum Amount** and
  **Maximum Amount** range specified for the selected plan and tenure before
  making the API request.
</Tip>

<Tabs>
  <Tab title="Credit card EMI">
    Credit card EMI lets customers split a large payment into fixed monthly
    instalments charged to their credit card. This is the most widely supported
    EMI type and is available across major Indian banks.

    <Accordion title="Credit card EMI codes">
      The following table lists the supported banks, interest rates, and tenures
      available for credit card EMI.

      | Card type | Type of EMI | Bank               | card\_bank\_name   | Minimum amount | Maximum amount | Annual interest rate | Tenure |
      | --------- | ----------- | ------------------ | ------------------ | -------------- | -------------- | -------------------- | ------ |
      | Credit    | Standard    | HDFC Bank          | hdfc               | 1000           | 500000         | 16                   | 3      |
      | Credit    | Standard    | HDFC Bank          | hdfc               | 3000           | 500000         | 16                   | 6      |
      | Credit    | Standard    | HDFC Bank          | hdfc               | 3000           | 500000         | 16                   | 9      |
      | Credit    | Standard    | HDFC Bank          | hdfc               | 3000           | 500000         | 16                   | 12     |
      | Credit    | Standard    | Axis Bank          | axis               | 2500           | 1000000        | 16                   | 3      |
      | Credit    | Standard    | Axis Bank          | axis               | 2500           | 1000000        | 16                   | 6      |
      | Credit    | Standard    | Axis Bank          | axis               | 2500           | 1000000        | 16                   | 9      |
      | Credit    | Standard    | Axis Bank          | axis               | 2500           | 1000000        | 16                   | 12     |
      | Credit    | Standard    | Axis Bank          | axis               | 2500           | 1000000        | 16                   | 18     |
      | Credit    | Standard    | Axis Bank          | axis               | 2500           | 1000000        | 16                   | 24     |
      | Credit    | Standard    | ICICI Bank         | icici              | 1500           | 500000         | 15.99                | 3      |
      | Credit    | Standard    | ICICI Bank         | icici              | 1500           | 500000         | 15.99                | 6      |
      | Credit    | Standard    | ICICI Bank         | icici              | 1500           | 500000         | 15.99                | 9      |
      | Credit    | Standard    | ICICI Bank         | icici              | 1500           | 500000         | 15.99                | 12     |
      | Credit    | Standard    | ICICI Bank         | icici              | 1500           | 500000         | 15.99                | 18     |
      | Credit    | Standard    | ICICI Bank         | icici              | 1500           | 500000         | 15.99                | 24     |
      | Credit    | Standard    | Kotak Bank         | kotak              | 1000           | 1000000        | 16                   | 3      |
      | Credit    | Standard    | Kotak Bank         | kotak              | 2500           | 1000000        | 16                   | 6      |
      | Credit    | Standard    | Kotak Bank         | kotak              | 2500           | 1000000        | 16                   | 9      |
      | Credit    | Standard    | Kotak Bank         | kotak              | 2500           | 1000000        | 16                   | 12     |
      | Credit    | Standard    | Kotak Bank         | kotak              | 2500           | 1000000        | 16                   | 18     |
      | Credit    | Standard    | Kotak Bank         | kotak              | 2500           | 1000000        | 16                   | 24     |
      | Credit    | Standard    | Bank of Baroda     | bob                | 2500           | 1000000        | 16                   | 3      |
      | Credit    | Standard    | Bank of Baroda     | bob                | 2500           | 1000000        | 16                   | 6      |
      | Credit    | Standard    | Bank of Baroda     | bob                | 2500           | 1000000        | 16                   | 9      |
      | Credit    | Standard    | Bank of Baroda     | bob                | 2500           | 1000000        | 16                   | 12     |
      | Credit    | Standard    | Bank of Baroda     | bob                | 2500           | 1000000        | 16                   | 18     |
      | Credit    | Standard    | Bank of Baroda     | bob                | 2500           | 1000000        | 16                   | 24     |
      | Credit    | Standard    | Bank of Baroda     | bob                | 2500           | 1000000        | 16                   | 36     |
      | Credit    | Standard    | Standard Chartered | standard chartered | 2000           | 500000         | 11.88                | 3      |
      | Credit    | Standard    | Standard Chartered | standard chartered | 2000           | 500000         | 14                   | 6      |
      | Credit    | Standard    | Standard Chartered | standard chartered | 2000           | 500000         | 15                   | 9      |
      | Credit    | Standard    | Standard Chartered | standard chartered | 2000           | 500000         | 15                   | 12     |
      | Credit    | Standard    | Standard Chartered | standard chartered | 2000           | 500000         | 15                   | 18     |
      | Credit    | Standard    | Standard Chartered | standard chartered | 2000           | 500000         | 15                   | 24     |
      | Credit    | Standard    | RBL Bank           | rbl                | 1500           | 1000000        | 13                   | 3      |
      | Credit    | Standard    | RBL Bank           | rbl                | 1500           | 1000000        | 14                   | 6      |
      | Credit    | Standard    | RBL Bank           | rbl                | 1500           | 1000000        | 15                   | 9      |
      | Credit    | Standard    | RBL Bank           | rbl                | 1500           | 1000000        | 15                   | 12     |
      | Credit    | Standard    | RBL Bank           | rbl                | 1500           | 1000000        | 15                   | 18     |
      | Credit    | Standard    | RBL Bank           | rbl                | 1500           | 1000000        | 15                   | 24     |
      | Credit    | Standard    | AU Small Bank      | au                 | 2000           | 1000000        | 16                   | 3      |
      | Credit    | Standard    | AU Small Bank      | au                 | 2000           | 1000000        | 16                   | 6      |
      | Credit    | Standard    | AU Small Bank      | au                 | 2000           | 1000000        | 16                   | 9      |
      | Credit    | Standard    | AU Small Bank      | au                 | 2000           | 1000000        | 16                   | 12     |
      | Credit    | Standard    | AU Small Bank      | au                 | 2000           | 1000000        | 16                   | 18     |
      | Credit    | Standard    | AU Small Bank      | au                 | 2000           | 1000000        | 16                   | 24     |
      | Credit    | Standard    | Yes Bank           | yes                | 1500           | 1000000        | 16                   | 3      |
      | Credit    | Standard    | Yes Bank           | yes                | 1500           | 1000000        | 16                   | 6      |
      | Credit    | Standard    | Yes Bank           | yes                | 1500           | 1000000        | 16                   | 9      |
      | Credit    | Standard    | Yes Bank           | yes                | 1500           | 1000000        | 16                   | 12     |
      | Credit    | Standard    | Yes Bank           | yes                | 1500           | 1000000        | 16                   | 18     |
      | Credit    | Standard    | Yes Bank           | yes                | 1500           | 1000000        | 16                   | 24     |
      | Credit    | Standard    | HSBC               | hsbc               | 2000           | 1000000        | 12.5                 | 3      |
      | Credit    | Standard    | HSBC               | hsbc               | 2000           | 1000000        | 12.5                 | 6      |
      | Credit    | Standard    | HSBC               | hsbc               | 2000           | 1000000        | 13.5                 | 9      |
      | Credit    | Standard    | HSBC               | hsbc               | 2000           | 1000000        | 13.5                 | 12     |
      | Credit    | Standard    | American Express   | amex               | 5000           | 1000000        | 14                   | 3      |
      | Credit    | Standard    | American Express   | amex               | 5000           | 1000000        | 14                   | 6      |
      | Credit    | Standard    | American Express   | amex               | 5000           | 1000000        | 14                   | 9      |
      | Credit    | Standard    | American Express   | amex               | 5000           | 1000000        | 14                   | 12     |
      | Credit    | Standard    | American Express   | amex               | 5000           | 1000000        | 15                   | 18     |
      | Credit    | Standard    | American Express   | amex               | 5000           | 1000000        | 15                   | 24     |
    </Accordion>
  </Tab>

  <Tab title="Debit card EMI">
    Debit card EMI allows customers to pay in monthly instalments without a credit
    card. The bank determines eligibility based on the customer's account history.

    <Accordion title="Debit card EMI codes">
      The following bank and plans are currently supported for debit card EMI.
      The **Native OTP** column indicates whether the bank handles OTP
      verification directly.

      | Bank name | Native OTP |
      | :-------- | :--------- |
      | HDFC Bank | Yes        |

      #### Debit card EMI plans

      | Card type | Type of EMI | Bank      | card\_bank\_name | Minimum amount | Maximum amount | Annual interest rate | Tenure |
      | --------- | ----------- | --------- | ---------------- | -------------- | -------------- | -------------------- | ------ |
      | Debit     | Standard    | HDFC Bank | hdfc             | 3000           | 500000         | 16                   | 3      |
      | Debit     | Standard    | HDFC Bank | hdfc             | 5000           | 500000         | 16                   | 6      |
      | Debit     | Standard    | HDFC Bank | hdfc             | 5000           | 500000         | 16                   | 9      |
      | Debit     | Standard    | HDFC Bank | hdfc             | 5000           | 500000         | 16                   | 12     |
      | Debit     | Standard    | HDFC Bank | hdfc             | 5000           | 500000         | 16                   | 18     |
      | Debit     | Standard    | HDFC Bank | hdfc             | 5000           | 500000         | 16                   | 24     |
    </Accordion>
  </Tab>

  <Tab title="Cardless EMI">
    Cardless EMI allows customers to pay in instalments without a physical card.
    Financing is provided by partner banks or Non-Banking Financial Companies (NBFCs).

    <Accordion title="Cardless EMI codes">
      The following table lists the supported cardless EMI providers, interest
      rates, and available tenures.

      | Card type | Type of EMI | Bank       | provider  | Minimum amount | Maximum amount | Annual interest rate | Tenure |
      | --------- | ----------- | ---------- | --------- | -------------- | -------------- | -------------------- | ------ |
      | Cardless  | Standard    | HDFC Bank  | hdfc      | 3000           | 500000         | 16                   | 3      |
      | Cardless  | Standard    | HDFC Bank  | hdfc      | 5000           | 500000         | 16                   | 6      |
      | Cardless  | Standard    | HDFC Bank  | hdfc      | 5000           | 500000         | 16                   | 9      |
      | Cardless  | Standard    | HDFC Bank  | hdfc      | 5000           | 500000         | 16                   | 12     |
      | Cardless  | Standard    | HDFC Bank  | hdfc      | 5000           | 500000         | 16                   | 18     |
      | Cardless  | Standard    | HDFC Bank  | hdfc      | 5000           | 500000         | 16                   | 24     |
      | Cardless  | Standard    | Kotak Bank | kotak     | 3000           | 200000         | 19                   | 3      |
      | Cardless  | Standard    | Kotak Bank | kotak     | 5000           | 200000         | 19                   | 6      |
      | Cardless  | Standard    | Kotak Bank | kotak     | 5000           | 200000         | 19                   | 9      |
      | Cardless  | Standard    | Kotak Bank | kotak     | 5000           | 200000         | 19                   | 12     |
      | Cardless  | Standard    | ICICI Bank | icici     | 7000           | 500000         | 17                   | 3      |
      | Cardless  | Standard    | ICICI Bank | icici     | 7000           | 500000         | 17                   | 6      |
      | Cardless  | Standard    | ICICI Bank | icici     | 7000           | 500000         | 17                   | 9      |
      | Cardless  | Standard    | ICICI Bank | icici     | 7000           | 500000         | 17                   | 12     |
      | Cardless  | Standard    | IDFC Bank  | idfc      | 5000           | 100000         | 24                   | 3      |
      | Cardless  | Standard    | IDFC Bank  | idfc      | 5000           | 100000         | 24                   | 6      |
      | Cardless  | Standard    | IDFC Bank  | idfc      | 5000           | 100000         | 24                   | 9      |
      | Cardless  | Standard    | IDFC Bank  | idfc      | 5000           | 100000         | 24                   | 12     |
      | Cardless  | Standard    | CASHe      | cashe     | 1000           | 100000         | 23.78                | 3      |
      | Cardless  | Standard    | CASHe      | cashe     | 6000           | 100000         | 25.28                | 6      |
      | Cardless  | Standard    | CASHe      | cashe     | 9000           | 100000         | 25.63                | 9      |
      | Cardless  | Standard    | CASHe      | cashe     | 12000          | 100000         | 25.8                 | 12     |
      | Cardless  | No Cost     | ZestMoney  | zestmoney | 5000           | 150000         | 0                    | 3      |
      | Cardless  | Standard    | ZestMoney  | zestmoney | 5000           | 150000         | 36                   | 6      |
      | Cardless  | Standard    | ZestMoney  | zestmoney | 5000           | 150000         | 36                   | 9      |
      | Cardless  | Standard    | ZestMoney  | zestmoney | 5000           | 150000         | 36                   | 12     |
    </Accordion>
  </Tab>

  <Tab title="Pay later">
    Pay later providers extend a short-term line of credit to customers, allowing
    them to complete a purchase immediately and pay the amount — in full or in
    instalments — at a later date.

    <Accordion title="Pay later codes">
      The following table lists the supported Pay later providers and the
      corresponding parameter values to use in API requests.

      | Provider parameter | Name of the provider |
      | :----------------- | :------------------- |
      | zestmoney          | ZestMoney Paylater   |
      | lazypay            | Lazypay              |
      | simpl              | Simpl                |
      | mobikwik           | MobiKwik             |
    </Accordion>
  </Tab>
</Tabs>

<div class="hidden" data-table-of-contents="bottom">
  <p class="mt-4 font-medium flex items-center gap-2 related-docs-heading">
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" class="w-4 h-4">
      <path d="M3 4h7a2 2 0 0 1 2 2v13a2 2 0 0 0-2-2H3z" />

      <path d="M21 4h-7a2 2 0 0 0-2 2v13a2 2 0 0 1 2-2h7z" />
    </svg>

    <span>Related topics</span>
  </p>

  <ul>
    <li><a href="/docs/api-reference/payments/latest/orders/create">Create Order API</a></li>
    <li><a href="/docs/api-reference/payments/latest/orders/get">Get Order API</a></li>
    <li><a href="/docs/api-reference/payments/latest/payments/get">Get Payment API</a></li>
    <li><a href="/docs/payments/webhooks">Webhooks</a></li>
  </ul>
</div>
