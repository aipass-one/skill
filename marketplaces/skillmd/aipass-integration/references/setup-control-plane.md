# Delegated setup control plane

Use this flow to provision AI Pass without receiving a user's session credential. Base URL: `https://aipass.one`.

## Scope selection

Request the standard project setup set once: `setup:read`, `oauth-clients:read`, `oauth-clients:create`, `space:read`, `space-apps:write`, `space-apps:publish`, `space-apps:delete`, and `nova:query`. The OAuth callbacks remain exact, and Space mutations remain bound to one inferred project app slug. The delete capability is shown separately to the owner and must be exercised only when the user explicitly requests deletion. Request runtime `profile:read` only when ensuring a public client that intentionally uses AI Pass as host login.

These grants do not authorize billing, payments, wallet access, account security, model spending, generic API keys, or administrator operations.

Always send `requestedScopes`. Omitting it grants only `setup:read`; it does not infer broad setup access.

## Stable public project identity

Before the first request, read `.aipass/config.json`. Reuse its `projectFingerprint` when present. Otherwise generate a random UUID v4, write it there, and reuse it exactly for every later setup grant for this project. The fingerprint is a public correlation identifier for grant recovery, idempotency, and audit attribution, not a credential or an app ownership key. Losing an older fingerprint does not prevent a newly owner-approved grant from managing an app in that owner's approved Space. Do not derive a new fingerprint from the repository path, Git remote, account, hostname, or other machine identity.

For example:

```json
{
  "schemaVersion": 1,
  "projectFingerprint": "4f23c8c2-75ee-4c7f-8762-cdb8225d7a31"
}
```

## Determine callbacks before approval

When requesting `oauth-clients:create`, inspect the application and determine one to eight exact callback destinations before starting the device flow:

- Browser SDK: propose a stable URL on each exact browser origin where the SDK proof will run, for example `http://localhost:3000/` and later `https://app.example/`. The SDK uses AI Pass's signed central handoff, but the target origin must still be represented by an approved callback. The app does not need to implement that URL as an OAuth handler for the SDK path.
- Backend OAuth or AI Pass host login: propose the real callback route the host will implement, for example `https://app.example/auth/aipass/callback`.
- Mobile/deep-link clients: propose the exact private custom-scheme callback.

Public web callbacks must use HTTPS. Plain HTTP is allowed only on `localhost` or `127.0.0.1`. Userinfo, fragments, wildcards, dangerous schemes, and values longer than 2048 characters are rejected. Path, query, case, encoding, port, and trailing slash are significant for direct OAuth callbacks.

Do not invent a production hostname. Ask the user only when the repository and deployment configuration do not establish the destination. The user sees these exact destinations on the approval screen. The client only accepts approved callbacks. A later callback requires a new setup request and approval, and the owner can add it to the existing client from the approval page.

## 1. Recover an existing project grant first

Before creating a device request, look for this project's recovery record in the agent host's secure credential store or the portable `.aipass/project-grant.json` fallback. Read it without printing it. Reuse it only when all recorded bindings exactly match the current request: `baseUrl`, `projectFingerprint`, ordered `proposedRedirectUris`, `proposedSpaceAppSlug`, and `requestedScopes`. It must also be before `grantExpiresAt` when that value exists, or before its initial device expiry while approval remains pending.

Call the token endpoint once with the stored `deviceCode`. An `approved` response recovers the same already-approved `asg_` grant; no browser interaction is needed. Continue at section 3. On `authorization_pending`, preserve the record and continue the existing approval handoff. On `access_denied`, `expired_token`, `invalid_device_code`, or `setup_token_secret_changed`, delete the terminally unusable record. Start a new authorization only after no compatible grant can be recovered.

Do not treat a new agent turn, an empty process environment, or the absence of an in-memory bearer as a reason to replace a compatible recovery record.

## 2. Start device authorization when recovery is unavailable

No authentication is required for this request:

```http
POST /api/v1/agent-auth/device
Content-Type: application/json

{
  "agentName": "Actual executing agent name",
  "projectName": "Inferred app name",
  "projectFingerprint": "4f23c8c2-75ee-4c7f-8762-cdb8225d7a31",
  "setupVersion": 5,
  "requestedScopes": [
    "setup:read",
    "oauth-clients:read",
    "oauth-clients:create",
    "space:read",
    "space-apps:write",
    "space-apps:publish",
    "space-apps:delete",
    "nova:query"
  ],
  "proposedRedirectUris": [
    "http://localhost:3000/"
  ],
  "proposedSpaceAppSlug": "example-app"
}
```

Always send `setupVersion: 5` when following this version of the skill. It fails closed when `oauth-clients:create` lacks exact proposed callbacks, binds an existing Space from the approved account when available, and otherwise reserves the one app slug until that same account claims a Space. Omitting the field is reserved for compatibility with older published instructions.

Use the true executing tool name; do not copy an example agent identity. The HTTP 201 response uses the standard AI Pass envelope. Its `data` contains `deviceCode`, `userCode`, `verificationUri`, `verificationUriComplete`, `expiresIn`, and `interval`.

Before handing control to the browser, store the returned `deviceCode` with `schemaVersion`, `baseUrl`, `projectFingerprint`, ordered `proposedRedirectUris`, `proposedSpaceAppSlug`, exact `requestedScopes`, and the absolute device expiry. Prefer the agent host's secure credential store. For the portable fallback:

1. Add `.aipass/project-grant.json` to `.git/info/exclude` when available, or otherwise to `.gitignore`, before creating the file.
2. Reject a symlink at `.aipass` or the file path. Create `.aipass` with owner-only access where supported, and create the recovery file with mode `0600`.
3. Never store `verificationUriComplete`, `userCode`, an `asg_` token, OAuth token, cookie, password, client secret, provider key, or wallet credential in it.
4. Never serve, bundle, commit, upload, or copy the recovery record into runtime application code.

Show the user the app name, requested capability, and `verificationUriComplete`. When the environment has a browser or open-URL capability, open that user-facing URL once, then say that the approval page is open and ask the user to review it. Use the native capability instead of fetching the URL:

- Local macOS terminal: `open "$verificationUriComplete"`
- Local Linux desktop: `xdg-open "$verificationUriComplete"`
- Local Windows PowerShell: `Start-Process $verificationUriComplete`
- Replit, Lovable, or another browser IDE: use its native external-link or preview-opening affordance when available.

Do not run a local desktop opener from a remote or headless shell where it would open on the server rather than the user's device. In that case, or when opening fails, present `verificationUriComplete` as a clickable link. Attempt the automatic open only once; do not reopen it on every pending poll.

Opening the page is only a convenience handoff. Never use `curl`, an HTTP client, browser automation, or computer-use tools to inspect, sign in, click Continue, approve, or otherwise interact with the authorization page on the user's behalf. Never ask them to paste a session token or setup grant, and never call the approval endpoint yourself.

## 3. Exchange for the in-memory grant

Wait at least the returned interval between requests:

```http
POST /api/v1/agent-auth/token
Content-Type: application/json

{"deviceCode":"returned device code"}
```

While approval is pending, the API returns HTTP 400 with a standard envelope whose `.error` is `authorization_pending`. Poll no faster than `interval`. On `slow_down`, increase the wait before the next poll. Stop on `access_denied` or `expired_token`. Continue only when the standard response envelope has this `data`:

```json
{
  "status": "approved",
  "accessToken": "asg_...",
  "tokenType": "Bearer",
  "expiresIn": 2592000,
  "scopes": ["setup:read", "oauth-clients:read", "oauth-clients:create", "space:read", "space-apps:write", "space-apps:publish", "space-apps:delete", "nova:query"]
}
```

Honor the returned polling interval and all pending, denied, and expired outcomes. Do not restart automatically after denial. Keep the `accessToken` in process memory only. On approval, update the recovery record's `grantExpiresAt` from `expiresIn` and retain the record until that deadline or explicit revocation. Redact both credentials from logs and output.

### Continue across turns without another approval

Not every runtime can hold a process open while the user approves in a browser. A server-side or turn-based agent ends execution when it hands control back to the user, so a polling loop started before the approval never survives to see it. Hosts in this category include Replit, Lovable, v0, and Bolt.

When the runtime cannot poll continuously, resume instead of looping:

1. Open `verificationUriComplete` once with a native user-facing browser capability when available. Otherwise show it as a clickable link. End the turn asking the user to review, approve, and return.
2. On a later turn, read the protected recovery record without printing it and call the token endpoint once. On `authorization_pending`, ask the user to finish approving and end the turn again. Do not busy-loop and do not start a new device request.
3. On approval, retain the same record with its computed `grantExpiresAt`. On every later compatible project turn, exchange it once to recover the same grant without showing the browser page.
4. Delete the record only after denial, expiry, revocation, an incompatible project binding, or a failure to protect the secret.

Never start a second device request while a stored one is pending or while its approved grant remains recoverable. A user who approved one code and is then handed another cannot tell which is live, and the approved one is silently abandoned.

The stored `deviceCode` is scoped to this project and can recover the same issued token while the grant remains valid. Treat it as a secret for its full retained lifetime: never commit it, print it, or place it in application code.

If the executing agent supports ephemeral authenticated remote MCP, continue with [remote-mcp.md](remote-mcp.md). If its MCP configuration would persist the bearer value, use the REST calls below instead. Never trade away the setup grant's in-memory-only boundary merely to use MCP. The device-code recovery record above is the only secret this flow may write to disk, and it never holds an `asg_` grant.

## 4. Read before mutating

All REST control-plane calls use:

```http
Authorization: Bearer asg_REDACTED
```

Read owned resources first:

```http
GET /api/v1/agent-control/context
```

Unwrap the standard response envelope's `data`. It is intentionally minimal: owned public OAuth clients with client type, runtime scopes, and exact redirect URIs; read-only Space context; and grant bounds. It contains no client secret, wallet balance, session token, or private profile.

Reuse only an exact public client ID already stored in this project's configuration and confirmed by context as active, `PUBLIC`, correctly scoped, and holding every callback the user approved. Never pick a client by display-name similarity yourself. When the owner already has a matching app, AI Pass shows it on the approval page and the owner decides.

## 5. Ensure a public OAuth client

For the SDK, backend OAuth, or login path:

```http
POST /api/v1/agent-control/oauth-clients/ensure
Content-Type: application/json
Authorization: Bearer asg_REDACTED

{
  "name": "Inferred app name",
  "idempotencyKey": "oauth-client:v1",
  "runtimeScopes": ["api:access"]
}
```

Use runtime scope `api:access` for SDK and model calls. Add `profile:read` only when AI Pass is intentionally serving as host login. Reuse the returned public `clientId`. This endpoint creates a public, secretless PKCE client only.

The ensure request intentionally does not accept redirect URIs. It reads the immutable `proposedRedirectUris` from the approved setup grant and returns the client's callbacks as `redirectUris`. Never work around a missing callback by choosing another unapproved one.

When the owner already has an app client that matches this project (the same project fingerprint, the same name, or a shared deployed callback), the approval page asks the owner to pick that app or create a separate one:

- The owner picked the existing app: ensure adds the approved callbacks and runtime scopes to that client and returns it with `created: false` and `updated: true`. Nothing already on the client is removed. Keep the same `clientId`.
- The owner chose a separate app: ensure creates it.
- No match existed at approval time but one exists now: ensure creates nothing. REST returns HTTP 409 with `error` set to `existing_oauth_client_found` and the matching clients in `data.existingOAuthClients`. The MCP tool returns `isError: true` with the same fields in `structuredContent`. If one of those client IDs is already in `.aipass/config.json`, keep using it. Otherwise start a new setup request so the owner can choose on the approval page. Never retry with a new idempotency key to get past this response.

The idempotency key is scoped by signed-in user, project fingerprint, and operation. Use the stable literal `oauth-client:v1` for the first client for this project and persist it as `oauthClientIdempotencyKey` in `.aipass/config.json`. If a response is lost or a grant expires, read context and retry with the same project fingerprint, approved project name, runtime scopes, and key; the control plane returns the original usable client rather than creating a duplicate.

If AI Pass explicitly reports that the prior client for that key was deleted, deactivated, or no longer matches a secretless public PKCE client, never reactivate or modify it yourself. Advance the persisted key once to the next version such as `oauth-client:v2` and ensure again. AI Pass creates a replacement only when the owner has no matching app client or approved a separate one; otherwise it returns `existing_oauth_client_found` and the owner decides through a new setup request. Do not rotate the key for transient network failures, a new callback, or to bypass a scope or name mismatch.

## 6. Reuse this grant for the project's Space app

The standard project grant already includes the app-management scopes displayed on the approval page and one exact `proposedSpaceAppSlug`. If the user asks for Spaces after the SDK or OAuth setup, read [spaces-path.md](spaces-path.md) and continue with this same bearer value. Do not start another device request. If the account had no Space during approval, the first preflight after the user claims one binds that same-account Space to the existing grant. A matching app already owned by that Space may be adopted by this grant even if another or lost project fingerprint created it. Ownership comes from the signed-in user's approved Space; the current fingerprint is retained for recovery and audit attribution.

## 7. Optional read-only A2A support

Discover Nova at `/.well-known/agent-card.json`. Calls use the same project grant with `nova:query`:

```http
POST /a2a/v1/message:send
Content-Type: application/a2a+json
A2A-Version: 1.0
Authorization: Bearer asg_REDACTED

{
  "message": {
    "messageId": "new-uuid",
    "role": "ROLE_USER",
    "parts": [{"text":"Which documented path should I read for a localhost React app?"}]
  }
}
```

The first release supports synchronous read-only messages that route questions to documentation, path guidance, and error checklists. It does not inspect the project, analyze a supplied plan or error, stream, manage tasks, provision, publish, or mutate anything.

## 8. Keep one grant across project setup work

Keep each returned bearer in process memory through the current work. Across later turns, exchange the protected recovery device code to recover the same grant for integration, correction, retry, Nova guidance, and optional publication of the approved Space app. Do not revoke after provisioning the OAuth client or after the first Space call. Never persist the bearer or use the grant outside the project resources shown on the approval page. Device approval does not authorize paid model calls.

Revoke when the user asks to disconnect or the agent must abandon a credential it can no longer protect:

```http
DELETE /api/v1/agent-control/session
Authorization: Bearer asg_REDACTED
```

The response is HTTP 200 and the grant becomes unusable immediately. Delete its recovery record after revocation. Normal task completion, client provisioning, a passing build, or the first model call is not itself a reason to revoke; server-side expiry ends the grant after one month, and the recovery record prevents repeated approval during that window. Report a healthy grant as "recoverable for this project until [time], or the user can revoke it." If the user requests a different project, callback destination, or Space app slug, revoke or discard the incompatible record and start a fresh user-approved device flow. For a new callback on the same project, propose the full callback list; the owner can add it to the existing client from the approval page.
