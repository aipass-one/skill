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
2. Open [Developer Console](https://aipass.one/panel/developer). Reuse your app's existing **OAuth2 Client**, or choose **OAuth2 Clients → Register New Client** if it has none. A public client ID is an identifier, not a billing secret.
3. Open **AI Credit Management** or [the dedicated panel](https://aipass.one/panel/ai-credit). It lists clients owned by the signed-in account.
4. Choose the app. Configure its model/output policy, shared monthly admission limit and personal-wallet permission. Keep personal-wallet usage off if your product uses only app funding.
5. Inspect user allowances, daily/monthly/total limits, charged amounts, pending holds, tokens, UTC monthly statements and CSV exports. These reports describe existing wallet charges; exporting them does not charge again.

A $10 monthly app cap is shared by all its users. It is not $10 per user and does not fund an empty wallet. A $1 user allowance is separate permission within that shared cap. Amounts here are examples, not configured offers or retail subscription prices.

## 2. Configure the backend boundary

Keep these settings on your server:

- AI Pass origin: `https://aipass.one`.
- The owned app's public `clientId`.
- A funding-owner API key in your backend secret store, referenced below as `AIPASS_FUNDING_KEY`.
- A verified host session → stable app-local subject mapping, such as Firebase UID.
- Verified subscription → grant key, UTC expiry and configurable allowance mapping.

Never ship the funding key or provider keys in a website/mobile bundle. The backend must verify the app's Google/Apple/Firebase session itself. Derive the subject from the authenticated session; do not accept an arbitrary device-supplied ID or email. AI Pass does not need access to your Firebase service-account credentials for this server-to-server mode. Optional welcome-campaign identity checks use a separately configured Firebase project and public certificates.

Use `(clientId, subject)` as the user identity. Subjects and grant keys accept ASCII letters, numbers, `.`, `_`, `~`, `-`, up to 128 characters. Email lookup/metadata is not implemented. Your own backend may map email to its verified UID without making email the wallet authority.

The `asg_` project setup grant and existing setup MCP tools cannot fund wallets, administer allowances or execute AI. Provision the funding-owner key directly into the backend secret store; do not paste it into an agent conversation. No special universal AI Pass billing SDK is required for the REST flow below.

## 3. Prepare the app policy and each user's allowance

All paths in this section start with `/v1/sponsored/apps/{clientId}` and require:

```http
Authorization: Bearer <server-held-funding-owner-key>
Content-Type: application/json
```

The key owner must own the active registered client. Browser management uses the owner's normal AI Pass session under `/api/sponsored/**`; it is a different authentication surface and has some different field names. Do not call dashboard APIs with execution tokens.

Configure the app once or when the owner intentionally changes policy:

```http
PUT /v1/sponsored/apps/{clientId}

{"enabled":true,"monthlyLimitUsd":"10.00","model":"<chosen-supported-chat-model>","maxOutputTokens":1024,"allowPersonalWallet":false}
```

Choose the model from the developer catalog. AI Pass pins the actual chat model and output ceiling to this policy; sending a different device `model` does not change the funded policy. A policy enabled for an app still cannot bypass the global execution switch or insufficient backing funds.

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

## 4. Obtain execution tokens for the signed-in user

Your protected backend endpoint verifies the current app session and entitlement, derives `{subject}` and `{grantKey}` itself, then sends:

```http
POST /v1/sponsored/apps/{clientId}/users/{subject}/oauth
Authorization: Bearer <server-held-funding-owner-key>
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
- `POST /oauth2/v1/audio/transcriptions` — supported audio upload, up to 20 MB; fixed transcription model.

Use a stable, unique `Idempotency-Key` for each logical operation. This example uses environment variables only for illustration; do not print tokens or commit them:

```bash
curl --fail-with-body https://aipass.one/oauth2/v1/chat/completions   -H "Authorization: Bearer $AIPASS_EXECUTION_TOKEN"   -H "Idempotency-Key: $AI_OPERATION_ID"   -H 'Content-Type: application/json'   --data '{"messages":[{"role":"user","content":"Summarize this receipt."}],"stream":false}'
```

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

The backend calls these with its funding-owner key:

```http
GET /v1/sponsored/apps/{clientId}/users/{subject}/limits
GET /v1/sponsored/apps/{clientId}/usage?subject={subject}&month=2026-12&page=0&size=100
```

Derive the queried subject from the logged-in app session. Omit `month` for lifetime reporting. The server usage endpoint returns a paginated array of per-grant rows, with fields including `subject`, `grant_key`, `credit_limit`, `charged_usd`, `held_usd`, `input_tokens`, `output_tokens`, `total_tokens`, `provider_cost_usd` and `platform_fee_usd`. Pages are zero-based; size is 1–1,000. Continue until a short page when exporting every row. Dashboard API pagination has its own response shape and 250-row maximum.

Limits report grant-independent daily/monthly/lifetime charged amounts and holds plus shared app headroom. The user can spend only when every layer allows admission: backing wallet, app monthly policy, selected grant, and aggregate user caps. Outstanding estimated holds reduce remaining permission.

**A quota is an admission control, not an absolute final invoice ceiling.** Actual accepted model work can cost more than its estimate, cross a quota and block later admissions; the full actual cost remains billable. Do not promise a mathematically strict $10 maximum bill. Statements use the request's admission UTC period even if settlement is later. Keep exact money as decimal values; do not use binary floating-point to recreate a competing expense ledger.

## 8. Revoke after entitlement changes

For refunds, entitlement removal or app-account deletion, the authenticated backend can revoke matching app-funded access/refresh families:

```http
POST /v1/sponsored/apps/{clientId}/users/{subject}/oauth/revoke
Authorization: Bearer <server-held-funding-owner-key>
Content-Type: application/json

{"grantKey":"<affected-entitlement-period>"}
```

Successful revocation returns idempotent HTTP 204. It does not erase credit or past expenses and does not affect personal-wallet sessions, other users or other grants. Prevent future issuance without a valid entitlement. Notification delivery has latency; revocation cannot undo already admitted provider work. Owner-key revocation and grant/policy pause also stop new execution.

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
and usage reporting. Keep owner keys server-side and allowances configurable.
Do not connect or charge users' personal AI Pass wallets.
```

The skill and this guide are distributed through the public `aipass-one/skill` repository. The existing hosted `aipass-integration` skill is for user-funded wallet access; use this dedicated app-credit skill for the flow above. No domain-hosted app-credit skill URL is advertised until it is published there.
