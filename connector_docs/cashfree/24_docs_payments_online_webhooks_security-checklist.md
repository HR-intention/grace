> ## Documentation Index
> Fetch the complete documentation index at: https://www.cashfree.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# Webhook Security Checklist

> Implement security best practices to protect your webhook integration with Cashfree Payments.

Secure webhook integration requires multiple layers of protection to safeguard your systems from unauthorised access and data tampering. This guide outlines the recommended security measures for your webhook endpoints.

The following table summarises the security controls and their implementation priority:

| Security control                                                                  | Priority           | Description                                             |
| --------------------------------------------------------------------------------- | ------------------ | ------------------------------------------------------- |
| [Public endpoint URL](#public-endpoint-url)                                       | Mandatory          | Ensure your endpoint is publicly accessible over HTTPS. |
| [IP whitelisting](#ip-whitelisting)                                               | Highly recommended | Restrict traffic to Cashfree's IP ranges.               |
| [Signature verification](#signature-verification)                                 | Highly recommended | Verify HMAC signature for each request.                 |
| [Secure Sockets Layer (SSL) whitelisting](#secure-sockets-layer-ssl-whitelisting) | Optional           | Configure mutual TLS for enhanced security.             |
| [Authentication validation](#authentication-validation)                           | Optional           | Add custom authentication for additional protection.    |

## Public endpoint URL

Your webhook endpoint must be publicly accessible over the internet for Cashfree to deliver notifications. Use this as your foundation and apply the security controls described in the following sections to protect the integration.

<Note>
  Ensure your endpoint URL uses HTTPS to encrypt data during transmission.
</Note>

For instructions on adding and configuring webhook endpoints, refer to [Webhook configuration](/payments/online/webhooks/configure).

## IP whitelisting

Restrict inbound traffic to accept requests only from Cashfree's known IP ranges. This control ensures your endpoint receives webhooks exclusively from legitimate Cashfree sources.

To configure IP whitelisting, complete the following steps:

1. Obtain the list of Cashfree's published IP addresses from the [Security features](/security#ip-whitelisting) documentation.
2. Configure your firewall rules to allow requests only from these IP ranges.
3. Block all other inbound traffic to your webhook endpoint.

<Warning>
  Cashfree may update its IP ranges periodically. Monitor the documentation for changes and update your firewall rules accordingly.
</Warning>

## Signature verification

All webhook notifications include a cryptographic signature using HMAC-based validation. Verify this signature to confirm the authenticity and integrity of each request.

To implement signature verification, follow these guidelines:

* Serve your webhook endpoint over **HTTPS** to protect data during transmission.
* Extract the signature from the webhook request headers.
* Verify the signature against the raw request body using your secret key.
* Receive the payload as **raw data** to prevent modifications before verification.

### Required headers

Validate the following mandatory headers in each webhook request:

| Header                | Description                                           |
| --------------------- | ----------------------------------------------------- |
| `x-webhook-signature` | The cryptographic signature for payload verification. |
| `x-webhook-timestamp` | The timestamp when the webhook was generated.         |
| `x-webhook-version`   | The API version of the webhook payload.               |

<Info>
  For detailed implementation examples with SDK and manual verification code samples, refer to [Webhook signature verification](/payments/online/webhooks/signature-verification).
</Info>

## SSL whitelisting

For enhanced transport-level security, configure mutual TLS (mTLS) authentication between your systems and Cashfree.

To enable SSL whitelisting, you can:

* Provide your SSL certificate to Cashfree for addition to their trusted certificate sources.
* Add Cashfree's certificate to your system's trusted certificates.

This configuration ensures only mutually authenticated communication occurs between your systems and Cashfree.

<Note>
  SSL whitelisting is an optional security layer. Contact [Cashfree support](https://merchant.cashfree.com/merchants/landing?env=prod\&raise_issue=1) to configure mutual TLS authentication for your account.
</Note>

## Authentication validation

If your endpoint requires custom authentication, configure Cashfree to include the necessary credentials in webhook requests.

Cashfree supports the following authentication methods:

* **Basic authentication**: Username and password credentials
* **Bearer tokens**: Token-based authentication
* **Custom headers**: Application-specific authentication parameters

To configure authentication for webhooks:

1. Share the required authentication parameters with Cashfree.
2. Implement server-side validation to verify the authentication fields in request headers.
3. Reject requests that fail authentication checks.

For more information on API authentication methods, refer to [Authentication](/api-reference/authentication).

<Warning>
  Implement signature verification at minimum to prevent payload manipulation through man-in-the-middle attacks.
</Warning>

<div class="hidden" data-table-of-contents="bottom">
  <p class="mt-4 font-medium flex items-center gap-2 related-docs-heading">
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" class="w-4 h-4">
      <path d="M3 4h7a2 2 0 0 1 2 2v13a2 2 0 0 0-2-2H3z" />

      <path d="M21 4h-7a2 2 0 0 0-2 2v13a2 2 0 0 1 2-2h7z" />
    </svg>

    <span>Related topics</span>
  </p>

  <ul>
    <li><a href="/docs/payments/online/webhooks/overview">Webhooks overview</a></li>
    <li><a href="/docs/payments/online/webhooks/configure">Webhook configuration</a></li>
    <li><a href="/docs/payments/online/webhooks/signature-verification">Signature verification</a></li>
    <li><a href="/docs/api-reference/authentication">API authentication</a></li>
  </ul>
</div>
