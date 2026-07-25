# AI Pass OAuth and API Contract

Use this reference for wire-level implementation. Use the authorization-server metadata endpoint as the live source of truth:

```http
GET https://aipass.one/.well-known/oauth-authorization-server
```

## Base URLs and Scopes

| Purpose | Base or endpoint |
|---|---|
| OAuth authorization | `https://aipass.one/oauth2/authorize` |
| Token exchange/refresh | `https://aipass.one/oauth2/token` |
| User info | `https://aipass.one/oauth2/userinfo` |
| Revocation | `https://aipass.one/oauth2/revoke` |
| OAuth model proxy | `https://aipass.one/oauth2/v1` |
| Balance | `https://aipass.one/api/v1/usage/me/summary` |
| Checkout | `https://aipass.one/api/v1/payment/create-checkout-session` |
| Dashboard | `https://aipass.one/panel/dashboard` |

Scopes:

- `api:access`: required for `/oauth2/v1/*` model calls.
- `profile:read`: required for `/oauth2/userinfo`.

The token endpoint supports public-client authentication (`none`) with authorization-code + PKCE and refresh-token grants. Do not add HTTP Basic auth or expose a client secret unless current metadata and client configuration explicitly require a different mode.

## Authorization Request

Generate a fresh state and PKCE verifier for every attempt. Use `S256`.

```text
GET /oauth2/authorize
  ?response_type=code
  &client_id=CLIENT_ID
  &redirect_uri=EXACT_CALLBACK
  &scope=api:access%20profile:read
  &state=RANDOM_STATE
  &code_challenge=BASE64URL_SHA256_VERIFIER
  &code_challenge_method=S256
```

Required query parameters:

- `response_type=code`
- `client_id`
- `redirect_uri`
- `code_challenge`
- `code_challenge_method`

Optional query parameters:

- `scope`
- `state` (the consumer must still require it)
- `mode=login` or `mode=signup` to influence the AI Pass authentication UI

### Redirect URI Modes

AI Pass client callback configuration has meaningful nullability:

- non-null list: exact registered allowlist is enforced;
- `null`: validated dynamic callbacks for distributed clients whose installation host is not known when registered;
- empty list: no callbacks are allowed.

Dynamic mode is intentionally broader. It still accepts only syntactically safe callback forms: HTTPS origins, loopback HTTP for development, or private custom schemes for installed applications. It rejects fragments, wildcards, dangerous schemes, and public plain HTTP.

Use an exact allowlist whenever deployment hosts are known. Use null only when installation-specific hosts make preregistration impossible, such as a WordPress plugin.

## Token Exchange

AI Pass expects a JSON body with camelCase field names:

```http
POST /oauth2/token
Content-Type: application/json

{
  "grantType": "authorization_code",
  "clientId": "CLIENT_ID",
  "code": "AUTHORIZATION_CODE",
  "codeVerifier": "ORIGINAL_VERIFIER",
  "redirectUri": "EXACT_CALLBACK"
}
```

The redirect URI must be the same value used for authorization. The token response uses snake_case:

```json
{
  "access_token": "...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "refresh_token": "...",
  "scope": "api:access profile:read"
}
```

Do not hardcode a token lifetime. Compute the expiry using `expires_in` when the response arrives.

## Refresh

```http
POST /oauth2/token
Content-Type: application/json

{
  "grantType": "refresh_token",
  "refreshToken": "CURRENT_REFRESH_TOKEN",
  "clientId": "CLIENT_ID"
}
```

Refresh rotates the access and refresh tokens. Persist the returned pair atomically. AI Pass serializes server-side rotations and may return `503` with `Retry-After: 1` when concurrent refresh requests conflict. Wait and retry once. Consumers must still serialize or coalesce refreshes.

Treat invalid grant, `400`, or `401` as requiring authorization again. Treat network and other `5xx` errors as temporary; do not delete the connection or switch billing sources automatically.

## User Info

```http
GET /oauth2/userinfo
Authorization: Bearer ACCESS_TOKEN
```

Requires `profile:read`. Fields include:

```json
{
  "sub": "stable-aipass-user-id",
  "name": "Example User",
  "email": "user@example.com",
  "email_verified": true,
  "preferred_username": "example",
  "updated_at": "2026-07-15T12:00:00Z",
  "scopes": ["api:access", "profile:read"]
}
```

Use `sub` as the durable external identity. Do not key identity by mutable email. If the host application allows email matching, require `email_verified: true`.

## Models and Generation

Discover the public model catalog:

```http
GET /oauth2/v1/models
GET /oauth2/v1/models?type=text&method=chat_completions
```

The default response is the OpenAI-compatible `{ "object": "list", "data": [{ "id": "..." }] }` envelope. Map `data[].id` when only stable public IDs are needed. The explicit compatibility query `?detailed=false` returns the historical string array. Use `type`, `capability`, and `method` filters rather than provider prefixes or path suffixes.

Chat completion:

```http
POST /oauth2/v1/chat/completions
Authorization: Bearer ACCESS_TOKEN
Content-Type: application/json

{
  "model": "MODEL_FROM_DISCOVERY",
  "messages": [{"role": "user", "content": "Hello"}],
  "stream": false
}
```

The proxy uses OpenAI-compatible bodies. Supported proxy routes include:

- `GET /models` and `GET /models/{id}`
- `POST /chat/completions`
- `POST /embeddings`
- `POST /images/generations`
- `POST /images/edits`
- `POST /images/variations`
- `POST /audio/speech`
- `POST /audio/transcriptions`
- video create, status, content, and remix routes

Use `/oauth2/v1`, not the API-key namespace `/apikey/v1`.

## Balance

```http
GET /api/v1/usage/me/summary
Authorization: Bearer ACCESS_TOKEN
```

Envelope:

```json
{
  "success": true,
  "data": {
    "totalCost": 2.45,
    "maxBudget": 10.00,
    "remainingBudget": 7.55
  }
}
```

The display balance is `data.remainingBudget`. Refresh after a successful call and after checkout. A preflight balance is not a reservation; the model request decides whether spending is accepted.

## Checkout

```http
POST /api/v1/payment/create-checkout-session
Authorization: Bearer ACCESS_TOKEN
Content-Type: application/json

{"amount": 5}
```

The minimum accepted amount is currently `$0.50`. Read `data.checkoutUrl` from the response envelope. Validate it and open it in a new tab from the user's direct click. In production, require HTTPS. Local integrations may explicitly allow loopback or configured private development hosts over HTTP.

Checkout returns to the AI Pass dashboard, not necessarily the consumer app. Keep the consumer tab open and refresh balance on focus/visibility change.

## Revocation

```http
POST /oauth2/revoke
Content-Type: application/x-www-form-urlencoded

token=TOKEN_TO_REVOKE&client_id=CLIENT_ID
```

Revoke refresh token first, then access token. AI Pass uses RFC 7009-style idempotent success for unknown tokens. The current service does not require `client_id` for revocation, but including it is forward-compatible for public clients.

## Retry Boundaries

- Refresh once before expiry or after one `401`; retry the original request once.
- Retry refresh once after an explicit short `503` conflict.
- Retry a different model only after a confirmed model-unavailable response.
- Do not retry or reroute an ambiguous paid request to another funding source automatically.
- Do not loop indefinitely on any status.
