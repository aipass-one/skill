---
name: aipass-app-credit
description: Integrate AI Pass as an app-funded AI credit ledger for a multi-user product. Use when the developer pays for inference and needs app-local user attribution, allowances, daily or monthly limits, OAuth execution tokens, and usage reporting behind the app's existing login or subscriptions. Personal AI Pass wallet connection is a separate integration.
---

# AI Pass app-funded credits

Keep the app's Google, Apple or other verified login. Its backend authenticates the user and uses a server-held app funding key to obtain execution-only OAuth credentials bound to that app, app-local user and allowance. AI Pass reserves and settles actual AI expenses in the owner's wallet and reports each user's usage. The user does not need a personal AI Pass wallet or a second login for this mode.

Read [the developer guide](references/developer-guide.md) for dashboard setup, exact request fields, refresh, reporting, revocation and current availability. Use that contract rather than the general user-funded SDK cookbook.

## Implementation workflow

1. Inspect existing authentication, AI routes, subscriptions, secret storage and request retries. Preserve them unless the requested migration changes them. Choose an existing owned AI Pass client; creating another client must be an intentional setup decision.
2. On the backend, verify the app session and derive a stable subject from it. Use the verified Firebase UID or equivalent app-local ID, never a subject or email accepted directly from the device. Email equality does not grant another person's wallet authority.
3. For Firebase Secret Manager, use [one-approval funding setup](references/funding-setup.md). The bundled helper asks the owner to approve the exact app and destination, then stores the resulting app funding key directly over HTTPS using your authorized Google Cloud login. Keep the credential in the backend secret store. When the helper is unavailable, the owner can generate it from **App funding** and place it in their secret store.
4. Map a verified entitlement to a stable grant key and expiry. For the optional **Welcome campaign**, claim `POST /v1/sponsored/apps/{clientId}/users/{subject}/welcome/claim` from the backend after user verification. Any app identity provider works. Use the returned `welcome` grant. Prepare it with `createOnly:true` so repeated logins/status requests do not reset spending or undo a developer's pause. Read current aggregate user limits; write them only as an intentional policy change. Keep plan prices, grants and per-user limits configurable.
5. Implement a protected token-exchange endpoint in the app backend. Authenticate the caller, check entitlement and any app integrity requirements, derive the subject and grant server-side, call AI Pass's issuance endpoint and return only the ordinary execution token response to that user with `Cache-Control: no-store`. Do not create an arbitrary-subject token broker.
6. Use the issued bearer for nonstreaming chat or transcription. Choose a compatible catalog model in the inference request. Bind local token storage to the host account and funding mode; clear it on logout/account switch. Follow existing client TTLs and refresh rotation, serializing refresh per token family and persisting both returned tokens atomically. Refresh does not renew an allowance or switch its grant.
7. Read usage and remaining permission through the backend, and render them in the app's own terms. AI Pass owns the AI expense ledger; the app still owns purchase verification and entitlements. Do not debit a second AI-cost ledger for the same accepted request. The developer can also manage users and export statements in `/panel/ai-credit`.
8. Revoke grant-bound authorization families on refund or entitlement removal. Check entitlements on future issuance too. For a new subscription period, prepare its grant and obtain credentials bound to that period using the existing host login. Never make token refresh refill credits.

## Billing boundaries

- A public client ID authorizes no spending. The scoped app funding key and AI Pass's stored app/user/grant binding determine the payer. Caller-supplied payer or user headers do not change it.
- Fund the owner wallet and prepare a grant for each user. Admission uses estimated holds and checks the grant and per-user limits. Actual accepted provider cost can exceed the estimate and remains billable.
- Use one stable request ID per logical operation. Do not retry a possibly accepted request with a new ID, alternate provider or personal-wallet payer. On ambiguous results, show pending/recovery behavior instead of claiming success or sending duplicate work.
- Connecting a personal wallet requires a separate explicit AI Pass OAuth consent and app permission. Google/Apple login alone never authorizes it. Do not silently fall back to that wallet.
- Startup promotion approval records shared/per-user, one-time/monthly terms, but actual platform-funded issuance/renewal is not implemented. Do not manufacture platform credits or hand a platform owner key to an applicant.
- App-funded execution is deployed but disabled globally as of 27 November 2026. Build/configure the integration and report the activation dependency; do not treat unavailable endpoints as permission to bypass controls or switch payer. Do not enable production spending or perform paid probes without task authorization for that action.

## Verify and report

Use synthetic identities and mocked provider responses first. Verify that one user cannot choose another subject, that owner keys stay server-side, repeated grant preparation preserves limits/pauses, concurrent refresh is serialized, and a denied/ambiguous request does not trigger another payer or duplicate call. Check refund revocation and per-period renewal behavior against the app's verified entitlement state.

Report the chosen client and subject mapping, payer, grant lifecycle, secret names (never values), tests run and pending activation or paid verification. A build or mocked test is not a verified funded production integration.
