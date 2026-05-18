# Payment-method categories and types

Authoritative source of truth for the payment-method taxonomy. Each
language pack defines language-specific pattern files under
`guides/patterns/authorize/<category>/` matching the categories below.

## Categories

| Category | Code (Category:Type) | Per-pack pattern dir | Supported Flows |
|----------|----------------------|----------------------|-----------------|
| **Card** | `Card:Credit`, `Card:Debit` | `authorize/card/` | All flows |
| **Wallet** | `Wallet:Apple Pay`, `Wallet:Google Pay`, `Wallet:PayPal`, etc. | `authorize/wallet/` | Authorize, Refund |
| **Bank Transfer** | `BankTransfer:SEPA`, `BankTransfer:ACH`, etc. | `authorize/bank_transfer/` | Authorize, Refund |
| **Bank Debit** | `BankDebit:SEPA`, `BankDebit:ACH`, etc. | `authorize/bank_debit/` | Authorize, Refund |
| **Bank Redirect** | `BankRedirect:Sofort`, `BankRedirect:iDEAL`, etc. | `authorize/bank_redirect/` | Authorize |
| **UPI** | `UPI:Collect`, `UPI:Intent` | `authorize/upi/` | Authorize, Refund |
| **BNPL** | `BNPL:Klarna`, `BNPL:Afterpay`, etc. | `authorize/bnpl/` | Authorize, Refund |
| **Crypto** | `Crypto:Bitcoin`, etc. | `authorize/crypto/` | Authorize |
| **Gift Card** | `GiftCard:Generic` | `authorize/gift_card/` | Authorize |
| **Mobile Payment** | `MobilePayment:<network>` | `authorize/mobile_payment/` | Authorize, Refund |
| **Reward** | `Reward:<program>` | `authorize/reward/` | Authorize |

## Command syntax

When adding payment methods to a connector, the command form is:

```
add <Category>:<Type1>,<Type2> [and <Category2>:<Type3>] to <Connector> using grace/rulesbook/codegen-<lang>/.gracerules_add_payment_method
```

Examples:
- `add Wallet:Apple Pay,Google Pay to Stripe using grace/rulesbook/codegen-rust/.gracerules_add_payment_method`
- `add UPI:Collect,Intent to Razorpay using grace/rulesbook/codegen-python/.gracerules_add_payment_method`

## Validity rules

When adding a payment method to any language pack:

1. The category must exist in the table above.
2. The pattern file path matches `guides/patterns/authorize/<category>/pattern_authorize_<type_or_category>.md`.
3. The Authorize flow must already exist for the target connector (prerequisite).

The [rulesbook-pattern-auditor](../../.claude/agents/rulesbook-pattern-auditor.md) agent enforces these rules.
