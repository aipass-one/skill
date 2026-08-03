# Production Integration Blueprint

Use this blueprint to fit AI Pass into an established product instead of bolting OAuth calls directly into UI components.

## Component Map

```text
Host frontend
  account/settings -> connect, reauthorize, disconnect
  AI feature       -> host AI endpoint
  plans/funding    -> source choice, balance, add funds

Host backend
  OAuth broker     -> start + callback + local session
  identity service -> connection status + source selection
  token manager    -> decrypt + refresh + rotate + persist
  AI provider      -> /v1 adapter
  funding router   -> AI Pass versus host credits
  balance service  -> summary + checkout

Host database
  AI Pass identity/token row
  short-lived OAuth state row
  optional funding-source field and host credit ledger
```

Keep the token manager and funding router below every AI feature. UI-specific integrations tend to miss background analysis, regeneration, streaming, or secondary model calls.

## Architecture Decision

### Browser SDK

Choose the browser SDK when all are true:

- the product is intentionally client-only;
- browser token storage is within the threat model;
- AI Pass login does not need to create or link a host account;
- there is no server-side credit router or secret-bearing provider layer.

### Backend Broker

Choose a backend broker when any are true:

- the product has local users/sessions;
- AI Pass is an additional login or connected identity;
- tokens must be encrypted at rest;
- multiple backend/Edge Functions call AI;
- the product has its own free/subscription credits;
- one action must not be charged twice;
- connection and reauthorization state must be centrally managed.

## Suggested Data Model

Adapt names and types to the host schema:

```sql
create table aipass_identities (
  id uuid primary key,
  user_id uuid not null unique references users(id) on delete cascade,
  aipass_sub text not null unique,
  access_token_ciphertext text not null,
  refresh_token_ciphertext text,
  access_token_expires_at timestamptz,
  scopes text,
  reauthorization_required boolean not null default false,
  generation_source text not null default 'aipass'
    check (generation_source in ('aipass', 'app')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table aipass_oauth_states (
  state_hash text primary key,
  code_verifier_ciphertext text not null,
  redirect_uri text not null,
  mode text not null check (mode in ('login', 'connect')),
  bound_user_id uuid references users(id) on delete cascade,
  created_at timestamptz not null default now(),
  consumed_at timestamptz
);
```

Security properties matter more than column names:

- only service code can read token columns;
- access and refresh tokens use authenticated encryption;
- state consumption is atomic;
- `connect` state identifies the initiating local user;
- `aipass_sub` and `user_id` are unique;
- stale state cleanup is indexed and bounded;
- migrations can be rolled back without exposing or silently reassigning identities.

Use a KMS envelope or a vetted AEAD construction such as AES-GCM. Keep the master key outside the database and repository. Include a key version if rotation will be needed.

## Broker Endpoints

### Start

`POST /auth/aipass/start`

Input may include `mode=login|connect` and a safe post-auth return path. Do not accept an arbitrary callback URL when the app has one configured callback.

Start responsibilities:

1. Require a local session for connect mode.
2. Generate 32 random bytes for state.
3. Generate a PKCE verifier and S256 challenge.
4. Save hashed state, encrypted verifier, exact redirect, mode, bound user, and timestamp.
5. Return or redirect to the AI Pass authorization URL.

Use a relative, allowlisted return path to prevent open redirects after the callback.

### Callback

`GET /auth/aipass/callback?code=...&state=...`

Callback responsibilities:

1. Validate required parameters and provider errors.
2. Hash state and atomically change an unconsumed, unexpired row to consumed.
3. Decrypt the verifier.
4. Exchange the code using the saved callback URI.
5. Validate the token response.
6. Fetch user info.
7. Resolve the local identity under the selected mode.
8. Encrypt and save token pair, expiry, and scopes in one transaction.
9. Mint/resume the host session and redirect to an allowlisted host route.

Never continue when state lookup, consumption, verifier decryption, token validation, identity conflict, or token persistence fails.

### Connection Status

Return a client-safe shape such as:

```json
{
  "connected": true,
  "reauthRequired": false,
  "generationSource": "aipass",
  "balance": 7.55,
  "profile": {"name": "Example User"}
}
```

Do not include token values, ciphertext, upstream raw errors, or internal identifiers that the UI does not need.

### Source Selection

Require a local session and accept only a closed enum such as `aipass|app`. Selecting AI Pass should require a connected, authorized identity. Selecting app credits should not disconnect AI Pass.

### Disconnect

Load and decrypt tokens server-side. Revoke refresh token, then access token. Delete the identity/token row regardless of transient revocation failure. Preserve unrelated host account data.

## Identity Rules

Treat connect and login as different operations.

### Connect

- local session is mandatory at start and callback completion;
- saved state is bound to the initiating local user;
- AI Pass `sub` cannot already belong to another local user;
- never choose the target user by callback email.

### Continue with AI Pass

- match an existing AI Pass `sub` first;
- if an existing local user is matched by email, require verified AI Pass email;
- if a new local user is created from user info, require verified email;
- normalize email and handle concurrent account creation transactionally;
- mint the host's normal session only after identity/token persistence succeeds.

Do not auto-merge two established host accounts based only on equal email.

## Token Manager State Machine

```text
load encrypted pair
  -> decrypt failed: internal connection error
  -> no access token: reauthorize
  -> expiry > now + skew: use token
  -> near expiry: enter serialized refresh

refresh
  -> success: encrypt and atomically replace pair -> return new access
  -> 503 conflict: wait Retry-After, retry once
  -> invalid grant / 400 / 401: mark reauthorization required
  -> network / other 5xx: temporary failure, keep connection
  -> encryption or persistence failure: fail closed
```

Concurrency requires two layers when the backend has multiple instances:

- an in-process promise/mutex prevents duplicate refresh in one worker;
- a row lock, version column, or compare-and-swap prevents different workers from overwriting rotated tokens.

After refreshing due to a model `401`, retry the model request once. Do not recursively retry through the entire adapter stack.

## Provider Adapter

Create one adapter that accepts the host application's internal generation request and returns its existing result shape.

Responsibilities:

- obtain a fresh token from the token manager;
- call the matching shared `/v1/*` endpoint;
- support abort signals and streaming without issuing a second request;
- parse OpenAI-compatible success responses;
- return a typed internal error without leaking token-bearing data;
- classify only confirmed model-unavailable errors for model fallback;
- emit a successful-usage event so balance UI invalidates/refetches.

Do not make a speculative “balance check” mandatory before every call. It creates a race and latency without reserving funds.

## Funding Router

Represent the routing result explicitly:

```text
selected source = app
  -> require available host credit
  -> call existing provider path
  -> debit host credit only after success

selected source = aipass
  -> require connected and authorized identity
  -> call AI Pass
  -> success: refresh balance, no host debit
  -> definite insufficient balance:
       host credit available -> persist source=app, call host path, debit after success
       no host credit        -> block and open funding UI
  -> any other error: surface it, no host debit, no source change
```

If the AI Pass request timed out or the connection broke after sending the request, its billing outcome is ambiguous. Do not automatically make another paid request through host credits.

If a fallback model is used within AI Pass, it is still AI Pass-funded. If any AI Pass model call already succeeded, stop; never also execute the host-funded route.

## Balance and Checkout UI

Balance refresh triggers:

- initial connection query;
- successful AI Pass generation;
- checkout initiation followed by visibility/focus return;
- manual refresh;
- low-frequency polling only while relevant UI is visible.

The plan/funding UI should communicate:

- connected versus disconnected;
- selected source;
- exact current AI Pass balance or loading/unavailable state;
- add funds action;
- AI Pass dashboard link;
- host plan and host-credit choices;
- why a source changed after a definite empty-wallet response.

Open checkout in a new tab because its success return may land on AI Pass. Create the tab synchronously in the click handler if checkout URL generation is async, then navigate or close it based on the response to avoid popup blocking.

## Error Taxonomy

Define internal codes instead of string matching in the UI:

| Class | Examples | Reauthorize | Change source | Retry |
|---|---|---:|---:|---:|
| Auth expired | invalid refresh, token rejected after refresh | yes | no | OAuth flow |
| Insufficient AI Pass balance | confirmed budget rejection | no | optional, if host credits exist | after funding |
| Model unavailable | missing/disabled configured model | no | no | one model fallback |
| Invalid request | validation or unsupported payload | no | no | no |
| Temporary provider | upstream 5xx | no | no | user/manual policy |
| Ambiguous transport | timeout, connection reset after send | no | no | no automatic paid retry |
| Internal persistence | encryption/database write failed | no | no | fail closed |

Keep provider error classification close to the adapter and cover it with fixtures from actual provider responses.

## Implementation and Deployment Order

1. Add database migrations and encryption configuration.
2. Add pure OAuth, state, identity, and token-manager tests.
3. Add broker and connection endpoints.
4. Add provider adapter and model discovery/configuration.
5. Add funding router while preserving the existing provider path.
6. Add client hooks, settings, plan UI, and balance invalidation.
7. Run existing AI and billing test suites before new end-to-end tests.
8. Test callback and token flow against local host services.
9. Verify AI Pass client callback policy and production callback registration.
10. Deploy provider/client prerequisites, migrations, backend, then frontend.
11. Run a disposable-user OAuth, generation, balance, source-switch, and disconnect test.
12. Remove the disposable identity and inspect logs for token leakage.

Feature-flag the routing layer when possible. Rollback should disable new routing while retaining encrypted identity data for a later safe resume.

## Review Checklist

- Every AI entry point reaches one intentional provider/funding router.
- One UI action produces one model request unless a documented model-unavailable fallback occurs.
- No token is returned in connection-status or logged.
- State is one-time and connect is bound to the local user.
- Identity uses `sub`; email linking requires verification.
- Refresh rotates both tokens atomically under concurrency.
- Balance refresh does not block every request.
- Definite empty wallet and ambiguous failures have different behavior.
- Host credits are debited only after host-funded success.
- Checkout does not navigate the host app away.
- Disconnect deletes local credentials.
- Existing provider behavior remains tested and reversible.
