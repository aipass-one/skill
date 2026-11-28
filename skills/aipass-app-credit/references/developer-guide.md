# Developer guide: app-funded AI credits

AI Pass can manage your app's AI expense ledger, user allowances and usage reports. Your app authenticates users and verifies subscriptions; AI Pass authenticates your backend, reserves estimated AI cost, settles accepted work at actual cost and attributes it to the correct app-local user.

**Availability — 27 November 2026:** the backend and management panel are deployed. App-funded issuance/execution is globally disabled pending approved funding configuration and funded integration validation. Management can prepare policies while execution is off. Startup application review is available; automatic platform-funded promotional issuance and monthly renewal are not implemented. This guide does not enable spending or promise an automatic signup gift.

## Choose who pays

| Mode | User signs in to | AI Pass credential | Charged account |
|---|---|---|---|
| App-funded (this guide) | Your app | App/user/grant-bound execution token issued to your authenticated backend | Your app's funding-owner wallet |
| Personal wallet | Your app, then explicitly connects AI Pass | User-authorized OAuth token and budget | That user's AI Pass wallet |

Matching Google email addresses does not connect wallets. For app-funded usage, AI Pass trusts your authenticated backend's app-local subject because it spends that funding owner's money. The end user does not need an AI Pass account. One user in two third-party apps has two independent app-local identities unless a separate, consented identity feature links them.

```text
Google/Apple login in your app
  → your backend verifies login + entitlement and derives the user ID
  → backend obtains AI Pass app/user/grant-bound OAuth credentials
  → device calls supported AI routes with that execution bearer
  → AI Pass charges the owner's wallet and records cost/tokens per app user
```

## 1. Open the developer dashboard

1. [Sign in to AI Pass](https://aipass.one/panel/auth) with the account that owns and funds your app. A separate developer account type is not required.
2. Open [AI Credit Management](https://aipass.one/panel/ai-credit) from the Developer Console. The list shows the apps you’ve added.
3. Select **Add app** and choose an existing OAuth client. If you register a new app here, it also appears under **OAuth2 Clients** in the Developer Console.
4. Open the app’s row and go to **App funding → Create app funding key**. Copy the key to your backend secret store. AI Pass reveals it once, and you can revoke it from the same page.
5. Use the detail tabs to view allowances, user spending limits, tokens, statements and CSV exports. App funding also controls whether users can connect and pay from their own wallets.

Add funds to the funding wallet and assign a grant to each user. AI Pass checks the funding wallet, the grant and any per-user caps at request admission.

## 2. Configure the backend boundary

Keep these settings on your server:

- AI Pass origin: `https://aipass.one`.
- The owned app's public `clientId`.
- The app funding key in your backend secret store, referenced below as `AIPASS_FUNDING_KEY`.
- A verified host session → stable app-local subject mapping, such as Firebase UID.
- Verified subscription → grant key, UTC expiry and configurable allowance mapping.

Never ship the funding key or provider keys in a website/mobile bundle. The backend must verify the app's Google/Apple/Firebase session itself. Derive the subject from the authenticated session; do not accept an arbitrary device-supplied ID or email. AI Pass does not need access to your Firebase service-account credentials for this server-to-server mode.

Use `(clientId, subject)` as the user identity. Subjects and grant keys accept ASCII letters, numbers, `.`, `_`, `~`, `-`, up to 128 characters.

After a user opts in, your backend can add a verified email as a label in your developer dashboard. Use the app funding key with `PUT /v1/sponsored/apps/{clientId}/users/{subject}/reporting-email` and a body containing `email` and a positive integer `revision`. Increment the revision on each change. Send `email: null` with a newer revision when the user withdraws consent or deletes their account. Usage, limits and wallet charges use the app user ID.

The app funding key belongs in your backend secret store. General setup grants authorize project setup tools. The funding setup approval authorizes a single delivery operation for one app.

### Let an agent provision the key

Install the `aipass-app-credit` skill with the steps below. The agent runs its helper with the existing OAuth client ID, Firebase project ID, and backend secret name. Open the displayed AI Pass link and approve the app and destination. The helper uses your existing authorized Google Cloud CLI login to write the key into Secret Manager and reports the key ID. Use an explicit Google Cloud account if you have several CLI logins.

For a live backend, provision the new key, switch the backend to its new secret version, then revoke the previous key in **App funding**. The helper also supports immediate retirement after delivery when you explicitly approve a previous key ID and the old key can be safely removed.

## 3. Prepare the app policy and each user's allowance

All paths in this section start with `/v1/sponsored/apps/{clientId}` and require:

```http
Authorization: Bearer <server-held-app-funding-key>
Content-Type: application/json
```

The app funding key binds to one OAuth client. It authorizes allowance and limit updates, usage reads, optional reporting emails, welcome claims, and issuance and revocation of user execution tokens for that client. Browser management uses the owner’s AI Pass session under `/api/sponsored/**`. Use the dashboard to set app policy and campaign amounts.

Use **App funding** in the dashboard to change who can pay. Execution requires global activation and sufficient funds.

After the app backend verifies the subscription/trial entitlement, prepare a stable grant:

```http
PUT /v1/sponsored/apps/{clientId}/users/{subject}/grants/{grantKey}

{"creditLimitUsd":"1.00","expiresAt":"2027-01-01T00:00:00","enabled":true,"createOnly":true}
```

The date is an example; compute the real entitlement expiry on the server. This server endpoint uses a UTC local timestamp without an offset; dashboard grant timestamps require an explicit offset. `createOnly:true` leaves an existing grant unchanged, including a developer's edits or pause. A new grant key cannot erase prior user cap usage. Setting a total limit does not reset settled charges.

Optionally configure aggregate caps across **all** grants for the app user:

```http
PUT /v1/sponsored/apps/{clientId}/users/{subject}/limits

{"dailyLimitUsd":"0.20","monthlyLimitUsd":"1.00","totalLimitUsd":null}
```

Send all three fields when replacing caps. `null` removes that cap; zero blocks new admission. Read current limits on normal status/login calls instead of overwriting owner decisions. Daily/monthly boundaries are UTC calendar boundaries. Use grant expiry and period-specific grants for subscription periods; calendar caps and an App Store renewal date are separate concepts.

### Optional welcome allowance

Open the selected app’s **Welcome campaign**, enter a USD amount, and save. On signup or sign-in, verify the user with your app’s existing identity provider. Derive their stable account ID on your backend, then claim the allowance with the app funding key:

```http
POST /v1/sponsored/apps/{clientId}/users/{subject}/welcome/claim
Authorization: Bearer <server-held-app-funding-key>
```

Use the returned `grantKey` of `welcome` when requesting execution tokens. AI Pass creates at most one welcome allowance per app account. Repeated claims preserve its spending, allowance total, and any pause. **Stop new welcome claims** closes the campaign to new users. Your funding wallet pays as users spend the allowance.

Existing Firebase-verified campaigns keep their configured verification and claim endpoint. To move one to backend-verified claims, stop the existing campaign and then save a new amount. Existing allowances still count toward the one-per-account rule.

## 4. Obtain execution tokens for the signed-in user

Your protected backend endpoint verifies the current app session and entitlement, derives `{subject}` and `{grantKey}` itself, then sends:

```http
POST /v1/sponsored/apps/{clientId}/users/{subject}/oauth
Authorization: Bearer <server-held-app-funding-key>
Content-Type: application/json

{"grantKey":"<server-selected-entitlement-period>"}
```

AI Pass requires the owned client, app policy and existing enabled/unexpired grant. Issuance creates no allowance, balance or charge. The ordinary response includes:

```json
{
  "access_token": "<execution-access-token>",
  "refresh_token": "<execution-refresh-token>",
  "expires_in": 3600,
  "token_type": "Bearer",
  "scope": "sponsored:execute",
  "client_id": "<owned-client-id>"
}
```

The expiry above is illustrative. Honor the returned value and registered client's stored TTLs; this flow does not introduce a separate short token lifetime. Forward only the token response to the authenticated app user, with `Cache-Control: no-store`. Keep tokens out of logs, URLs and analytics. Bind secure local storage to the app account and funding mode, and clear it on account switching/logout. These are restricted execution credentials, not AI Pass profile or personal-wallet credentials.

## 5. Call AI from the app

The execution bearer currently permits only:

- `POST /oauth2/v1/chat/completions` — nonstreaming chat, including supported receipt interpretation.
- `POST /oauth2/v1/audio/transcriptions` — supported audio upload up to 20 MB. Set `model` in the multipart form to choose a compatible transcription model.

Use a stable, unique `Idempotency-Key` for each logical operation. This example uses environment variables only for illustration; do not print tokens or commit them:

```bash
curl --fail-with-body https://aipass.one/oauth2/v1/chat/completions   -H "Authorization: Bearer $AIPASS_EXECUTION_TOKEN"   -H "Idempotency-Key: $AI_OPERATION_ID"   -H 'Content-Type: application/json'   --data '{"model":"gemini-3.1-flash-lite","messages":[{"role":"user","content":"Summarize this receipt."}],"stream":false}'
```

Choose models from [Supported models](/docs/models). Chat accepts a compatible `model` ID and optional `max_tokens`. With no model specified, chat uses Gemini 3.1 Flash Lite and transcription uses Whisper. A chat request without `max_tokens` uses the provider’s response default. The owner-key chat route also accepts `model` and `max_tokens`. Its raw transcription route accepts an optional `model` query parameter.

For JSON output, use `"response_format":{"type":"json_object"}`. Chat accepts at most 64 messages and a 3.5 MB body. Raw supported audio or standard supported multipart upload is accepted for transcription. Do not add payer/user overrides, query parameters or compressed request bodies. Streaming, model listing, decisions, images, video, profile, wallet and management endpoints are not supported by these restricted credentials, even if ordinary personal OAuth supports them.

AI Pass checks current app ownership/activity, issuing key, policy, grant, caps, backing funds and revocation at admission. It creates an estimated hold and later settles accepted work at actual provider cost plus the configured direct AI Pass fee. Developer-funded requests use no developer markup/earnings; no new fee percentage is selected by this guide. Usage appears in the funding account's app reports, not the end user's personal-wallet history.

### Errors and retries

- A typed allowance refusal returns HTTP 402 with `error.code = SPONSORED_ALLOWANCE_EXHAUSTED`.
- A wallet/provider funding refusal returns sanitized HTTP 402 with `SPONSORED_FUNDING_UNAVAILABLE`.
- Conflicting request reuse may return HTTP 409 with `SPONSORED_REQUEST_CONFLICT`.
- Malformed, expired, paused or revoked credentials/policies have their corresponding 4xx denial. The global switch can make server routes unavailable; confirm activation instead of changing authentication or payer.

Treat an ambiguous network result as possibly accepted. Do not resend under a fresh ID or another payer/provider. Do not claim a provider operation finished until its actual result is known. An exhausted allowance is not a reason to silently charge a personal wallet.

## 6. Refresh without another user login

Use the existing token endpoint and JSON field names:

```http
POST /oauth2/token
Content-Type: application/json

{"grantType":"refresh_token","refreshToken":"<execution-refresh-token>","clientId":"<owned-client-id>"}
```

Refresh preserves app, user, grant, funding mode and restricted scope. Use each client's returned TTLs and rotation/grace behavior rather than hardcoding expiry. Serialize refresh per token family and atomically store both returned tokens. A still-live refresh authorization remains usable after access expiry.

Refresh does not refill credit, change grants, renew a subscription or bypass pause/revocation/expiry. For the next verified subscription period, the app backend prepares that period's grant and issues new delegation using the existing host login. Your token-broker response can include grant expiry separately so the app knows when to request period-bound credentials. Revoke old families when appropriate to the entitlement state; do not rely on a client to select a period.

## 7. Display allowance and usage

The backend calls these with its app funding key:

```http
GET /v1/sponsored/apps/{clientId}/users/{subject}/limits
GET /v1/sponsored/apps/{clientId}/usage?subject={subject}&month=2026-12&page=0&size=100
```

Derive the queried subject from the logged-in app session. Omit `month` for lifetime reporting. The server usage endpoint returns a paginated array of per-grant rows, with fields including `subject`, `grant_key`, `credit_limit`, `charged_usd`, `held_usd`, `input_tokens`, `output_tokens`, `total_tokens`, `provider_cost_usd` and `platform_fee_usd`. Pages are zero-based; size is 1–1,000. Continue until a short page when exporting every row. Dashboard API pagination has its own response shape and 250-row maximum.

Limits report the user’s daily, monthly and lifetime charged amounts and holds across grants. Estimated holds reduce the user’s remaining allowance and available wallet funds.

Admission uses estimated costs. Final provider charges may exceed the estimate and reduce the allowance available for later requests. Statements use the request's admission UTC period even if settlement is later. Keep exact money as decimal values; do not use binary floating-point to recreate a competing expense ledger.

## 8. Revoke after entitlement changes

For refunds, entitlement removal or app-account deletion, the authenticated backend can revoke matching app-funded access/refresh families:

```http
POST /v1/sponsored/apps/{clientId}/users/{subject}/oauth/revoke
Authorization: Bearer <server-held-app-funding-key>
Content-Type: application/json

{"grantKey":"<affected-entitlement-period>"}
```

Successful revocation returns idempotent HTTP 204. It does not erase credit or past expenses and does not affect personal-wallet sessions, other users or other grants. Prevent future issuance without a valid entitlement. Notification delivery has latency; revocation cannot undo already admitted provider work. App funding key revocation and grant/policy pause also stop new execution.

Your app remains responsible for StoreKit/Google Play/Stripe purchase verification, renewals, restore, refunds and subscription entitlements. AI Pass manages the AI expense ledger; it is not an in-app purchase replacement. A retail price such as $5/month is distinct from the AI allowance you configure.

## Optional startup promotions and personal wallets

Apply for promotional funding from the panel's **Startup promotion** tab using a working public HTTPS product URL, startup/use-case description and team details. A new client gets no automatic credit. AI Pass reviews the application and chooses configurable app/user and one-time/monthly terms. Approved applications remain `approved_awaiting_funding` with `fundingActivationAvailable:false`; platform-funded issuance/renewal is not implemented. Do not grant a third party access to an unrestricted platform owner's key.

To support personal-wallet payments later, add a separate **Connect AI Pass wallet** flow with the user's explicit OAuth consent and budget, and enable app permission for that funding mode. Host Google/Apple login alone never grants this permission. Keep both credential namespaces and payer choices separate; no automatic fallback is implemented.

## Give this to a coding agent

Install the dedicated skill from the official public repository:

```bash
npx skills add aipass-one/skill --skill aipass-app-credit
```

Then ask:

```text
Use $aipass-app-credit to integrate AI Pass as our app-funded AI ledger.
Keep our existing Google/Apple login and subscription verification.
Add a secure backend token exchange, per-user allowances, normal OAuth refresh,
and usage reporting. Keep the app funding key server-side and allowances configurable.
Do not connect or charge users' personal AI Pass wallets.
```

The skill and this guide are distributed through the public `aipass-one/skill` repository. The existing hosted `aipass-integration` skill is for user-funded wallet access; use this dedicated app-credit skill for the flow above. No domain-hosted app-credit skill URL is advertised until it is published there.
