---
name: integrate-aipass
description: Add AI Pass to an existing multi-user product using OAuth2 + PKCE, secure token storage and refresh, OpenAI-compatible model calls, balance and top-up UI, and safe coexistence with the product's own credits or subscriptions. Use when retrofitting AI Pass login/account linking or pay-as-you-go AI into an established web, mobile, desktop, backend, Edge Function, or WordPress architecture; when replacing direct provider keys with per-user AI Pass billing; or when reviewing and repairing an incomplete AI Pass OAuth integration.
---

# Integrate AI Pass

Implement AI Pass as a per-user AI provider and funding source without weakening the host application's authentication or billing guarantees.

## Read the Contract First

Read these references before editing:

- [oauth-contract.md](references/oauth-contract.md) for exact endpoints, request fields, scopes, redirect policy, refresh rotation, balance, and checkout.
- [integration-blueprint.md](references/integration-blueprint.md) for architecture, storage, identity linking, funding fallback, error behavior, and deployment order.
- [examples.md](references/examples.md) for framework-neutral TypeScript and SQL patterns.

Treat `GET https://aipass.one/.well-known/oauth-authorization-server` and runtime model discovery as canonical when live behavior differs from a hardcoded assumption.

## Workflow

### 1. Inspect the Host Application

Map before changing code:

- local authentication and session creation;
- user and external-identity tables;
- secret management and server-only execution boundaries;
- AI request entry points, streaming, retries, and model selection;
- existing free credits, subscriptions, and when they are charged;
- plan, settings, account, and error UI;
- database migrations, local stack, tests, deployment, and rollback.

Search for every direct AI provider call. Do not integrate only the most visible feature and leave secondary generation paths on a different billing route accidentally.

### 2. Choose the Integration Shape

Use the browser SDK only for a small client-only application that accepts browser token storage. Use a backend OAuth broker by default when the product already owns users, sessions, a database, or credits.

For a brokered integration:

```text
client -> host /aipass/start -> AI Pass authorize -> host /aipass/callback
       -> encrypted identity/token row -> host session

AI action -> host backend -> fresh AI Pass access token -> /v1/*
```

Keep AI Pass credentials out of the client. The client should receive connection state, balance, and host-specific errors—not tokens.

### 3. Register and Configure the Client

Use a public client ID with PKCE. Request `api:access`; add `profile:read` when linking identities or offering “Continue with AI Pass.”

- For known hosts, configure exact callback URIs.
- For distributed installs with unknown hosts, a `null` callback list uses AI Pass validated dynamic mode.
- Do not confuse `null` with an empty list.
- Never embed or commit a client secret in a public app, plugin, mobile binary, or frontend environment.

Add base URL, client ID, callback URI, and token-encryption key to the host's documented environment configuration. Use the real AI Pass production service only after local callback and token-flow tests pass.

### 4. Add Persistence and OAuth Broker Endpoints

Add:

- an AI Pass identity row keyed by local user and unique AI Pass `sub`;
- encrypted access and refresh tokens, expiry, scopes, connection state, and selected funding source;
- a short-lived OAuth-state row containing hashed state, encrypted verifier, exact callback, mode, bound local user, creation, and consumption timestamps;
- start, callback, connection-status, source-selection, and disconnect endpoints.

State must be random, single-use, consumed atomically, and expire after about 10 minutes. Bind connect-mode state to the authenticated user. Clean abandoned states and cap growth.

### 5. Link Identities Deliberately

After code exchange, call `/oauth2/userinfo` and key the relationship by `sub`.

- Connect mode attaches only to the user bound into state.
- Login mode matches `sub` first.
- If the product intentionally matches or creates local users by email, require `email_verified: true`, normalize the email, and enforce uniqueness transactionally.
- Reject an AI Pass identity already attached to another local user.
- Mint the host application's normal session; never expose the AI Pass access token as the host session.

### 6. Implement a Shared Token Manager

Centralize token decryption, expiry checks, refresh, rotation, and persistence. Every AI Pass call must use it.

- Refresh about 60 seconds before expiry.
- Retry one model request after one successful refresh on `401`.
- Coalesce refreshes in-process and serialize or compare-and-swap across workers.
- Save the rotated access token, refresh token, expiry, and scope atomically.
- On refresh `503` with `Retry-After`, wait and retry once.
- On invalid grant, `400`, or `401`, mark reauthorization required.
- On persistence failure, fail closed; do not continue with an unrecorded rotated pair.

Never log tokens, authorization codes, PKCE verifiers, or raw secret-bearing responses.

### 7. Add the Provider Adapter

Route AI calls through the shared canonical `https://aipass.one/v1/*` resource API with the user's bearer token. Include `X-AIPass-OAuth-Client-Id` with the configured client ID when practical so the token is bound to the expected client. The legacy `/oauth2/v1/*` and `/apikey/v1/*` resource paths remain compatibility aliases, each with its previous credential contract; OAuth protocol endpoints remain under `/oauth2/*`. Preserve the host application's request and response contract so the integration does not break existing features.

Discover models at runtime. If the product configures a primary and fallback, use the fallback only for a confirmed model-unavailable response. Do not classify auth, balance, validation, timeout, network, or unknown provider errors as model-unavailable.

Audit streaming and non-streaming paths separately. Avoid duplicate requests caused by UI regeneration, retries, analysis helpers, or provider adapters layered on top of one another.

### 8. Add Balance, Top-Up, and Funding Choice

Expose `remainingBudget` from `/api/v1/usage/me/summary` through the host backend. Refresh it at connection load, after each successful AI Pass call, after checkout/window focus, and modestly while visible.

Create checkout through the authenticated AI Pass payment endpoint. Open the validated checkout URL in a new tab directly from the click handler so the host app remains open.

When the host also has credits:

- keep “connected” separate from the selected funding source;
- persist the user's AI Pass/app-credit selection;
- fall back to available host credits only on a definite AI Pass insufficient-balance rejection;
- if both are empty, block and show top-up/plan choices;
- charge host credits only after a host-funded generation succeeds;
- never fall back after an AI Pass request succeeded or after an ambiguous failure;
- do not auto-switch back to AI Pass after a top-up.

### 9. Add UI Without Duplicating Product Logic

Use shared components for:

- canonical AI Pass identity/branding;
- connect, reauthorize, and disconnect;
- selected funding source;
- live AI Pass balance;
- add funds and dashboard link;
- empty-wallet and both-balances-empty states.

Reuse the host application's plan modal and generation error surface. Test desktop and narrow mobile layouts. Do not fork separate landing and in-app plan data if the product already supports shared plan definitions.

### 10. Revoke, Test, and Deploy

On disconnect, revoke refresh then access token and delete local credentials even if remote revocation is unavailable.

Run tests covering:

- state mismatch, replay, expiry, and user binding;
- identity conflict and verified-email policy;
- token expiry, rotation, concurrent refresh, retry, and reauthorization;
- model discovery, primary success, permitted fallback, and forbidden fallback;
- balance refresh after successful usage;
- AI Pass empty, host credits empty, both empty, and successful top-up;
- no double charge on success, timeout, network failure, or retry;
- responsive UI and the existing non-AI-Pass generation path;
- local callback, production callback, and disconnect.

Deploy provider/client callback policy before relying on it in the consumer. Then apply migrations, set secrets, deploy backend endpoints, deploy frontend, and run a disposable-user end-to-end check. Keep rollback able to disable AI Pass routing without deleting identity data.

## Completion Standard

Do not call the integration complete until:

- all AI entry points use an intentional funding/provider route;
- tokens never cross into client-visible state or logs;
- refresh rotation is durable and concurrency-safe;
- balance visibly updates after a paid call;
- an empty wallet has a deterministic, non-double-billing outcome;
- existing app-funded behavior still passes its tests;
- local and production configuration are documented without secrets;
- migrations, backend, frontend, and deployment order are verified.

Report exact files changed, tests run, remaining deployment steps, and any provider-side prerequisite. Never print credentials in the handoff.
