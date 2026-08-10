---
name: aipass-spaces
description: Build and publish a self-contained hosted app to an authenticated user's AI Pass Space through browser-approved, short-lived device authorization. Use when a hosted Space is the fastest deployment path and the user has already claimed a handle.
---

# Publish to AI Pass Spaces

Use this path when a self-contained hosted app reaches a real result faster than deploying or changing the user's existing project. A Space lives at `https://aipass.one/spaces/{handle}`.

## Security boundary

Publishing uses a browser-approved `asg_` setup grant. Never ask the user to paste an API key, OAuth token, browser cookie, password, device code, or setup grant. Never call generic API-key create, rotate, regenerate, or delete endpoints.

The grant:

- expires after 20 minutes;
- is bound to the approved user, Space handle, app slug, project fingerprint, and exact SHA-256 of the HTML;
- can read the owner's Space, create or update one draft, and publish that draft;
- cannot call models, spend wallet funds, access payments, read account secrets, or act as a normal user credential.

Keep `deviceCode` and `asg_` values only in process memory. Never print, persist, commit, or include them in tool output. Send them only to `https://aipass.one` over HTTPS.

## 1. Prepare the exact app before authorization

Choose a stable lowercase slug using letters, numbers, and hyphens. Build one complete HTML document with inline app CSS and JavaScript. Include the SDK and keep `PLACEHOLDER_CLIENT_ID` exactly as written; AI Pass replaces it during the draft write.

```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>My AI app</title>
  <link rel="stylesheet" href="https://aipass.one/aipass-ui.css">
</head>
<body>
  <div data-aipass-button></div>
  <button id="generate" type="button">Generate</button>
  <output id="result"></output>
  <script src="https://aipass.one/aipass-sdk.js"></script>
  <script>
    AiPass.initialize({ clientId: 'PLACEHOLDER_CLIENT_ID', requireLogin: false });
  </script>
</body>
</html>
```

Use `AiPass.streamText`, `generateCompletion`, image/audio/video helpers, `AiPass.data`, `AiPass.files`, and user-approved `AiPass.shared` only as documented by the browser SDK. The publishing grant must never appear in app HTML.

Compute lowercase SHA-256 over the exact UTF-8 `htmlContent` string that will be sent. Do not normalize whitespace or replace `PLACEHOLDER_CLIENT_ID` after hashing.

Before the first request, reuse `.aipass/config.json`'s public `projectFingerprint`, or generate and persist a random UUID v4. It is a public project identifier, not a credential. Never derive it from a path, user, hostname, or Git remote.

## 2. Start device authorization

No authentication is required:

```http
POST /api/v1/agent-auth/device
Content-Type: application/json

{
  "agentName": "Actual executing agent name",
  "projectName": "My AI app",
  "projectFingerprint": "4f23c8c2-75ee-4c7f-8762-cdb8225d7a31",
  "setupVersion": 4,
  "requestedScopes": [
    "setup:read",
    "space:read",
    "space-apps:write",
    "space-apps:publish"
  ],
  "proposedSpaceHandle": "expected-handle",
  "proposedSpaceAppSlug": "my-ai-app",
  "proposedContentSha256": "64-lowercase-hex-characters"
}
```

Use the real executing tool name. Show the user `verificationUriComplete` and ask them to approve the displayed agent, exact Space, slug, content hash, and permissions. Never call the approval endpoint yourself.

Poll no faster than the returned `interval`:

```http
POST /api/v1/agent-auth/token
Content-Type: application/json

{"deviceCode":"in-memory device code"}
```

Continue on `authorization_pending`, slow down on `slow_down`, and stop on denial or expiry. On success, keep the returned `asg_` access token in memory only.

## 3. Mandatory preflight

Before every draft write, call:

```http
GET /api/v1/agent-control/space/preflight
Authorization: Bearer asg_REDACTED
```

Require the returned `handle` to equal `proposedSpaceHandle` byte for byte. Inspect `apps` and update the approved matching slug instead of creating a duplicate.

Machine-readable failures:

- `MISSING_CREDENTIAL`: no bearer value was sent;
- `INVALID_CREDENTIAL`: malformed, unknown, or wrong credential family;
- `CREDENTIAL_REVOKED`: the owner ended the grant;
- `CREDENTIAL_EXPIRED`: the grant timed out;
- `SPACE_NOT_CLAIMED`: the authenticated owner has no Space;
- `SPACE_HANDLE_MISMATCH`: the approved handle is not the owner's current handle.

For an expired, revoked, missing, or invalid grant, start one fresh device authorization for the same target and ask for browser approval. Never rotate or create a generic API key. Do not retry automatically after denial. `404` is not an authentication signal.

## 4. Create or update the draft first

```http
PUT /api/v1/agent-control/space/apps/{approved-slug}
Authorization: Bearer asg_REDACTED
Content-Type: application/json

{
  "name": "My AI app",
  "shortDescription": "A clear description of what the app does.",
  "htmlContent": "<!doctype html>...PLACEHOLDER_CLIENT_ID...</html>",
  "idempotencyKey": "space-draft:v1"
}
```

The server verifies the approved content hash and writes `DRAFT`; it never publishes in the same call. A fresh project may create the approved slug. A returning project may update only an agent-managed app previously created with the same stable project fingerprint. It cannot take over another app.

If the response is lost, run preflight again before retrying. Reuse the same slug, fingerprint, content, and idempotency key. Never invent a second slug to bypass an ambiguous response.

## 5. Publish that exact draft

```http
POST /api/v1/agent-control/space/apps/{approved-slug}/publish
Authorization: Bearer asg_REDACTED
```

Only the draft bound to this grant can be promoted. Confirm the response status is `PUBLISHED`, then open `/spaces/{handle}/{slug}`. The public Spaces index lists only Spaces with published apps; the owner can still see empty Spaces, drafts, and failed builder records on their own Space page.

## 6. Verify and revoke

Open the real app, exercise its normal AI Pass connection, and make a wallet-funded AI call only with contemporaneous user approval. Confirm one user action makes one model request and renders the real result. Exercise loading, cancellation, one error state, and storage isolation when used.

After the final control-plane call, revoke immediately:

```http
DELETE /api/v1/agent-control/session
Authorization: Bearer asg_REDACTED
```

Confirm a later control-plane request returns `CREDENTIAL_REVOKED`. Report the public Space URL, slug, verification performed, and revocation result. Never include credential-bearing responses in the report.
