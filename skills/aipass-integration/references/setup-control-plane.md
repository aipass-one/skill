# Delegated setup control plane

Use this flow to provision AI Pass without receiving a user's session credential. Base URL: `https://aipass.one`.

## Scope selection

Request the minimum set:

- SDK or backend OAuth for model access: `setup:read`, `oauth-clients:read`, `oauth-clients:create`.
- AI Pass host login: the same setup scopes; request runtime `profile:read` only when ensuring its public client.
- Ask Nova read-only integration questions: add `nova:query` only when needed.

These grants do not authorize billing, payments, wallet access, account security, model spending, generic API keys, or administrator operations.

Always send `requestedScopes`. Omitting it grants only `setup:read`; it does not infer broad setup access.

## Stable public project identity

Before the first request, read `.aipass/config.json`. Reuse its `projectFingerprint` when present. Otherwise generate a random UUID v4, write it there, and reuse it exactly for every later setup grant for this project. The fingerprint is a public correlation identifier, not a credential. Do not derive it from the repository path, Git remote, account, hostname, or other machine identity.

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

Do not invent a production hostname. Ask the user only when the repository and deployment configuration do not establish the destination. The user sees these exact destinations on the approval screen. The resulting client is bound to them; a later change requires a new setup request and approval.

## 1. Start device authorization

No authentication is required for this request:

```http
POST /api/v1/agent-auth/device
Content-Type: application/json

{
  "agentName": "Actual executing agent name",
  "projectName": "Inferred app name",
  "projectFingerprint": "4f23c8c2-75ee-4c7f-8762-cdb8225d7a31",
  "setupVersion": 4,
  "requestedScopes": [
    "setup:read",
    "oauth-clients:read",
    "oauth-clients:create"
  ],
  "proposedRedirectUris": [
    "http://localhost:3000/"
  ]
}
```

Always send `setupVersion: 4` when following this version of the skill. Version 4 fails closed when `oauth-clients:create` lacks exact proposed callbacks. Omitting the field is reserved for compatibility with the already-published v3 instructions and must not be used to create a callback-less client from this skill.

Use the true executing tool name; do not copy an example agent identity. The HTTP 201 response uses the standard AI Pass envelope. Its `data` contains `deviceCode`, `userCode`, `verificationUri`, `verificationUriComplete`, `expiresIn`, and `interval`.

Show the user the app name, requested capability, and `verificationUriComplete`. Ask them to approve in their browser. Never ask them to paste a session token or setup grant, and never call the approval endpoint on their behalf.

## 2. Poll for approval

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
  "expiresIn": 1200,
  "scopes": ["setup:read"]
}
```

Honor the returned polling interval and all pending, denied, and expired outcomes. Do not restart automatically after denial. Keep both `deviceCode` and `accessToken` in process memory only and redact them from logs and output.

If the executing agent supports ephemeral authenticated remote MCP, continue with [remote-mcp.md](remote-mcp.md). If its MCP configuration would persist the bearer value, use the REST calls below instead. Never trade away the in-memory-only boundary merely to use MCP.

## 3. Read before mutating

All REST control-plane calls use:

```http
Authorization: Bearer asg_REDACTED
```

Read owned resources first:

```http
GET /api/v1/agent-control/context
```

Unwrap the standard response envelope's `data`. It is intentionally minimal: owned public OAuth clients with client type, runtime scopes, and exact redirect URIs; read-only Space context; and grant bounds. It contains no client secret, wallet balance, session token, or private profile.

Reuse only an exact public client ID already stored in this project's configuration and confirmed by context as active, `PUBLIC`, correctly scoped, and bound to the same ordered callback list the user approved. Never reuse by display-name similarity.

## 4. Ensure a public OAuth client

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

The ensure request intentionally does not accept redirect URIs. It reads the immutable `proposedRedirectUris` from the approved setup grant, creates the client with exactly those values, and returns them as `redirectUris`. If the callbacks differ from a prior idempotent client, setup fails and requires a new approval and versioned idempotency key; never work around this by choosing another unapproved callback.

The idempotency key is scoped by signed-in user, project fingerprint, and operation. Use the stable literal `oauth-client:v1` for the first client for this project and persist it as `oauthClientIdempotencyKey` in `.aipass/config.json`. If a response is lost or a grant expires, read context and retry with the same project fingerprint, approved project name, runtime scopes, and key; the control plane returns the original usable client rather than creating a duplicate.

If AI Pass explicitly reports that the prior client for that key was deleted, deactivated, or no longer matches a secretless public PKCE client, never reactivate or modify it. Ask for a fresh setup approval, advance the persisted key once to the next version such as `oauth-client:v2`, and ensure a replacement. Do not rotate the key for transient network failures or to bypass a scope/name mismatch.

## 5. Spaces use a separate approval

This integration setup grant must not be reused for Space publishing. If Spaces is the selected optional host, revoke this grant and follow [spaces-path.md](spaces-path.md). The standalone manual requests its own exact publishing scopes and binds approval to the Space handle, app slug, project fingerprint, and HTML hash.

## 6. Optional read-only A2A support

Discover Nova at `/.well-known/agent-card.json`. Calls require the same short-lived grant with `nova:query`:

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

## 7. Revoke every setup session

After provisioning, save the returned public configuration and revoke each setup grant immediately, before runtime application edits or any wallet-funded verification:

```http
DELETE /api/v1/agent-control/session
Authorization: Bearer asg_REDACTED
```

The response is HTTP 200 and the grant becomes unusable immediately. Revoke only after the final control-plane or optional A2A call, and always before wallet-funded runtime verification. If implementation later requires another setup mutation, start a fresh user-approved device flow. On a terminal failure, revoke the current grant when the token is still available and cleanup is safe. Do not persist it for a later run.
