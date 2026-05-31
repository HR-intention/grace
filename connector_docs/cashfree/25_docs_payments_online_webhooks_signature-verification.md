> ## Documentation Index
> Fetch the complete documentation index at: https://www.cashfree.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# Webhook Signature Verification

> Learn how to verify webhook signatures to ensure the authenticity and integrity of webhook payloads.

Verify webhook signatures to ensure payloads from Cashfree haven't been tampered with. This security measure prevents fraudulent notifications and protects your application from malicious attacks.

**Essential for production environments**: all merchants processing live payments, subscriptions, or marketplace transactions must implement signature verification to maintain security and prevent financial losses.

<Warning>
  Cashfree generates the webhook signature based on the raw payload, not the
  parsed payload. You can refer to how the popular JavaScript framework
  [NestJS](https://docs.nestjs.com/faq/raw-body) provides a hook for accessing
  the raw body.
</Warning>

Use the signature to verify that the request hasn't been tampered with. You need your Cashfree PG secret key and the payload to verify the signature.

* The timestamp is present in the header `x-webhook-timestamp`.
* The actual signature is present in the header `x-webhook-signature`.

```bash signature-verification theme={"dark"}
timestamp := 1617695238078;
signedPayload := $timestamp.$payload;
expectedSignature := Base64Encode(HMACSHA256($signedPayload, $merchantSecretKey));
```

## SDK verification (built-in approach)

<CodeGroup>
  ```javascript Node (express) theme={"dark"}
  var express = require('express')
  const { Cashfree, CFEnvironment } = require "cashfree-pg";

  var app = express()

  const cashfree = new Cashfree(
  CFEnvironment.SANDBOX,
  "{Client ID}",
  "{Client Secret Key}"
  );

  app.post('/webhook', function (req, res) {
  try {
  cashfree.PGVerifyWebhookSignature(req.headers["x-webhook-signature"], req.rawBody, req.headers["x-webhook-timestamp"])
  } catch (err) {
  console.log(err.message)
  }
  })

  ```

  ```go golang theme={"dark"}
  import (
    cashfree "github.com/cashfree/cashfree-pg/v4"
  )

  // Route
  e.POST("/webhook", _this.Webhook)

  // Controller
  func (_this *WebhookRoute) Webhook(c echo.Context) error {
    	clientId := "<x-client-id>"
  		clientSecret := "<x-client-secret>"
  		cashfree.XClientId = &clientId
  		cashfree.XClientSecret = &clientSecret
  		cashfree.XEnvironment = cashfree.SANDBOX

      signature := c.Request().Header.Get("x-webhook-signature")
      timestamp := c.Request().Header.Get("x-webhook-timestamp")

      body, _ := ioutil.ReadAll(c.Request().Body)
      rawBody := string(body)
      webhookEvent, err := cashfree.PGVerifyWebhookSignature(signature, rawBody, timestamp)
      if err != nil {
  		fmt.Println(err.Error())
  	} else {
  		fmt.Println(webhookEvent.Object)
  	}
  }
  ```

  ```php PHP theme={"dark"}
  <?php

  $inputJSON = file_get_contents('php://input');

  $expectedSig = getallheaders()['x-webhook-signature'];
  $ts = getallheaders()['x-webhook-timestamp'];

  if(!isset($expectedSig) || !isset($ts)){
      echo "Bad Request";
      die();
  }

  \Cashfree\Cashfree::$XClientId = "<x-client-id>";
  \Cashfree\Cashfree::$XClientSecret = "<x-client-secret>";
  $cashfree = new \Cashfree\Cashfree();

  try {
   $response =  cashfree->PGVerifyWebhookSignature($expectedSig, $inputJSON, $ts);
  } catch(Exception $e) {
    // Error if signature verification fails
  }
  ?>
  ```

  ```python Python theme={"dark"}
  from cashfree_pg.api_client import Cashfree

  @app.route('/webhook', methods = ['POST'])
  def disp():
  		# Get the raw body from the request
      raw_body = request.data

      # Decode the raw body bytes into a string
      decoded_body = raw_body.decode('utf-8')

      #verify_signature
      timestamp = request.headers['x-webhook-timestamp']
      signature = request.headers['x-webhook-signature']

  		cashfree = Cashfree()
  		cashfree.XClientId = "<app_id>"
  		cashfree.XClientSecret = "<secret_key>"
  		try:
  			cashfreeWebhookResponse = cashfree.PGVerifyWebhookSignature(signature, decoded_body, timestamp)
  		except:
  			# If Signature mis-match
  ```

  ```java Java theme={"dark"}
  import com.cashfree.*;

  @PostMapping("/my-endpoint")
  public String handlePost(HttpServletRequest request) throws IOException {
      Cashfree.XClientId = "<x-client-id>";
  		Cashfree.XClientSecret = "<x-client-secret>";
  		Cashfree.XEnvironment = Cashfree.SANDBOX;

    	StringBuilder stringBuilder = new StringBuilder();
      BufferedReader bufferedReader = null;

      try {
        bufferedReader = request.getReader();
        String line;
        while ((line = bufferedReader.readLine()) != null) {
                stringBuilder.append(line).append('\n');
        }


        String rawBody = stringBuilder.toString();
        String signature = request.getHeader("x-webhook-signature");
        String timestamp = request.getHeader("x-webhook-timestamp");

        Cashfree cashfree = new Cashfree();
        PGWebhookEvent webhook = cashfree.PGVerifyWebhookSignature(signature, rawBody, timestamp);

      } catch (Exception e) {
              // Error if verification fails
      } finally {
           if (bufferedReader != null) {
              bufferedReader.close();
  		}
  	}

  }
  ```

  ```csharp csharp theme={"dark"}
  using cashfree_pg.Client;
  using cashfree_pg.Model;


  		[Route("api/[controller]")]
      [ApiController]
      public class YourController : ControllerBase
      {
          [HttpPost]
          public async Task<IActionResult> Post()
          {
              // Read the raw body of the POST request
              using (StreamReader reader = new StreamReader(Request.Body, Encoding.UTF8))
              {
                  string requestBody = await reader.ReadToEndAsync();
                  var headers = Request.Headers;
                  var signature = headers["x-webhook-signature"];
                  var timestamp = headers["x-webhook-timestamp"];

                  Cashfree.XClientId = "<x-client-id>";
                  Cashfree.XClientSecret = "<x-client-secret>";
                  Cashfree.XEnvironment = Cashfree.SANDBOX;
  								var cashfree = new Cashfree();

                  try {
                  var response = cashfree.PGVerifyWebhookSignature(signature, requestBody, timestamp);
                  } catch(Exception e) {
                  // Error if signature mis matches
                  }
              }
          }
      }
  ```
</CodeGroup>

## Manual verification (custom approach)

<CodeGroup>
  ```javascript Node (Express) theme={"dark"}
  function verify(ts, request){
      const body = request.headers['x-webhook-timestamp'] + request.rawBody
      const secretKey = <client secret>;
      let generatedSignature = crypto.createHmac('sha256', secretKey).update(body).digest("base64");
      const signature = request.headers['x-webhook-signature']
      if(generatedSignature === signature) {
          let jsonObject = JSON.parse(rawBody)
          return jsonObject
      }
      throw new Error("Generated signature and received signature did not match.");
  }
  ```

  ```go golang theme={"dark"}
  func VerifySignature(expectedSig string, ts string, body string) (string, error) {
          clientSecret := "<client-secret>"
  	signatureString := ts + rawBody
  	hmacInstance := hmac.New(sha256.New, []byte(*clientSecret))
  	hmacInstance.Write([]byte(signatureString))
  	bytesData := hmacInstance.Sum(nil)
  	generatedSignature := base64.StdEncoding.EncodeToString(bytesData)
  	if generatedSignature == expectedSig {
  		var object interface{}
  		err := json.Unmarshal([]byte(rawBody), &object)
  		if err != nil {
  			return nil, errors.New("something went wrong when unmarshalling raw body")
  		}
  		if objectAsMapInterface, ok := object.(map[string]interface{}); ok {
  			if webhookType, ok := objectAsMapInterface["type"].(string); ok {
  				return "signatures match", nil
  			}
  		}
  		return "", nil
  	}
  	return nil, errors.New("generated signature and received signature did not match")
  }

  timestamp := c.Request().Header.Get("x-webhook-timestamp")
  body, _ := ioutil.ReadAll(c.Request().Body)
  rawBody := string(body)
  signature := c.Request().Header.Get("x-webhook-signature")

  VerifySignature(signature, timestamp, rawBody)
  ```

  ```php PHP theme={"dark"}
  function computeSignature($ts, $rawBody){
      $rawBody = file_get_contents('php://input');
      $timestamp = getallheaders()['x-webhook-timestamp'];
      $signature = getallheaders()['x-webhook-signature'];

      $body = $timestamp . $rawBody;
      $secretKey = "<client-secret>";
      $genSignature = hash_hmac('sha256', $body, $secretKey, true);
      $genSignatureBase64 = base64_encode($genSignature);
      if($genSignatureBase64 == $signature) {
          $jsonResponse = json_decode($rawBody);
          return $jsonResponse;
      }
      throw new Exception("Generated signature and received signature did not match.");
  }
  ```

  ```java Java theme={"dark"}
  public Object generateSignature() {
    try {
        String data = headers.get("x-webhook-timestamp") + rawBody;
        String secretKey = "<client-secret>";
        Mac sha256_HMAC = Mac.getInstance("HmacSHA256");
        SecretKeySpec secret_key_spec = new SecretKeySpec(secretKey.getBytes(), "HmacSHA256");
        sha256_HMAC.init(secret_key_spec);
        String computed_signature = Base64.getEncoder().encodeToString(sha256_HMAC.doFinal(data.getBytes()));
        String signature = headers.get("x-webhook-signature")
        if(computed_signature.equals(signature)) {
          Gson g = new Gson();
          Object response = g.fromJson(rawBody, Object.class);
          return response;
        }
        throw new Exception("Generated signature and received signature did not match.");
    } catch (Exception e) {
      throw e;
    }
  }
  ```

  ```python Python theme={"dark"}
  import base64
  import hashlib
  import hmac

  def generateSignature():
      raw_body = request.data
      timestamp = request.headers['x-webhook-timestamp']
      signature = request.headers['x-webhook-signature']
      signatureData = timestamp+rawBody
      message = bytes(signatureData, 'utf-8')
      secretkey=bytes("<client-signature>",'utf-8')
      generatedSignature = base64.b64encode(hmac.new(secretkey, message, digestmod=hashlib.sha256).digest())
      computed_signature = str(generatedSignature, encoding='utf8')
      if computed_signature == signature:
          json_response = json.loads(rawBody)
          return json_response
      raise Exception("Generated signature and received signature did not match.")
  ```
</CodeGroup>

<div class="hidden" data-table-of-contents="bottom">
  <p class="mt-4 font-medium flex items-center gap-2 related-docs-heading">
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" class="w-4 h-4">
      <path d="M3 4h7a2 2 0 0 1 2 2v13a2 2 0 0 0-2-2H3z" />

      <path d="M21 4h-7a2 2 0 0 0-2 2v13a2 2 0 0 1 2-2h7z" />
    </svg>

    <span>Related topics</span>
  </p>

  <ul>
    <li><a href="/docs/payments/online/webhooks/security-checklist">Webhook Security Checklist</a></li>
    <li><a href="/docs/payments/online/webhooks/overview">Webhooks Overview</a></li>
    <li><a href="/docs/payments/online/webhooks/configure">Configure Webhooks</a></li>
    <li><a href="/docs/api-reference/payments/latest/payments/webhooks">Payment Webhooks API</a></li>
  </ul>
</div>
