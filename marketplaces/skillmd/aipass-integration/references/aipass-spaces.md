---
name: aipass-spaces
description: Build and publish a self-contained hosted app to the signed-in user's AI Pass Space through one reusable browser-approved project authorization. Use when the user asks to publish on AI Pass Spaces or a hosted Space is the fastest deployment path. Discover or later bind the user's handle automatically; never ask them to look it up or paste it into chat.
---

# Publish to AI Pass Spaces

Use this path when a self-contained hosted app reaches a real result faster than deploying or changing the user's existing project. A Space lives at `https://aipass.one/spaces/{handle}`.

## Security boundary

Publishing uses a browser-approved `asg_` setup grant. Never ask the user to paste a Space handle, API key, OAuth token, browser cookie, password, device code, or setup grant. Never call generic API-key create, rotate, regenerate, or delete endpoints.

The grant:

- gives reusable project setup access for up to one month so integration, correction, and publication do not require repeated approval;
- is bound to the signed-in account, that account's approved Space, and one app slug; the project fingerprint identifies the grant for recovery and audit but is not the app ownership key;
- can create or replace content, update metadata and visibility, publish or unlist, and explicitly delete that one owned app, including an app created under an older unavailable fingerprint;
- cannot call models, spend wallet funds, access payments, read account secrets, or act as a normal user credential.

Keep each returned `asg_` value only in process memory. Never print, persist, commit, or include it in tool output. To reuse the approved grant across agent turns, retain its raw `deviceCode` in the agent host's secure credential store when one exists. Otherwise use the portable `.aipass/project-grant.json` fallback described below. The recovery file is secret, must be gitignored and owner-readable only, and must never be served, bundled, committed, or copied into application code. Send either credential only to `https://aipass.one` over HTTPS.

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

Use `AiPass.streamText`, `generateCompletion`, `AiPass.decide`, image/audio/video helpers, `AiPass.data`, `AiPass.files`, and user-approved `AiPass.shared` only as documented by the browser SDK. The publishing grant must never appear in app HTML.

Before the first request, reuse `.aipass/config.json`'s public `projectFingerprint`, or generate and persist a random UUID v4. It is a public project identifier, not a credential. Never derive it from a path, user, hostname, or Git remote.

## Decisions

Decision models return typed answers and probabilities for routing, triage, moderation, scoring, yes/no checks, or picking a tool. Use chat for generated text or explanations. Discover `type: "decision"`, capability `decision`, method `decisions` at runtime and call `AiPass.decide({ model, state, questions, signal, timeout })`. State accepts text, objects, or arrays. Choice uses a criteria object, score an ordered criteria array (never `levels`), and noul gives the probability of yes. Batch questions against one state; use low choice/score confidence for LLM or human fallback. Decisions never stream.

See [SDK examples](https://aipass.one/docs/sdk#decisions) and [REST curl examples](https://aipass.one/docs/rest/openai-compatible#decisions). REST uses `/apikey/v1/decisions` or `/oauth2/v1/decisions` with its runtime credential, never a setup grant. OAuth also needs `api:access` and the client ID header. Jev 1.13 is a live example with input-only pricing ($0.042 per 1M tokens), free output, text-only input, a 64k request limit, and 32k for state plus the longest question. Do not hardcode model IDs.

## 2. Recover the grant or start device authorization

Before creating a device request, look for a recovery record in the agent host's secure credential store or `.aipass/project-grant.json`. Read it without printing it. Reuse it only when its `baseUrl`, `projectFingerprint`, `proposedSpaceAppSlug`, and exact `requestedScopes` match this project and it is before `grantExpiresAt` when approved or before its initial device expiry while pending. Exchange its `deviceCode` once at the token endpoint. An `approved` response returns the same existing `asg_` grant without browser interaction; keep that token in memory and continue at preflight.

Delete an incompatible or terminally failed recovery record. A terminal failure is `access_denied`, `expired_token`, `invalid_device_code`, or `setup_token_secret_changed`. Only then start a new device authorization. Do not replace a matching record merely because a new agent turn began.

When no compatible recovery record exists, no authentication is required to start the device flow:

```http
POST /api/v1/agent-auth/device
Content-Type: application/json

{
  "agentName": "Actual executing agent name",
  "projectName": "My AI app",
  "projectFingerprint": "4f23c8c2-75ee-4c7f-8762-cdb8225d7a31",
  "setupVersion": 5,
  "requestedScopes": [
    "setup:read",
    "space:read",
    "space-apps:write",
    "space-apps:publish",
    "space-apps:delete"
  ],
  "proposedSpaceAppSlug": "my-ai-app"
}
```

Use the real executing tool name. Do not send `proposedSpaceHandle` and do not ask the user for it. Do not send `proposedContentSha256`; setup version 5 lets the agent manage this one approved app without another authorization. The page shows the exact `@handle` when one exists, app slug, editing and publication permissions, and the separately labeled destructive delete capability before approval. Delete only when the user explicitly asks to delete that app. If the account has no Space yet, the user can still approve; after they claim a handle, the first preflight binds the Space owned by that same account to the existing grant.

Immediately store the returned raw `deviceCode` plus `baseUrl`, `projectFingerprint`, `proposedSpaceAppSlug`, exact `requestedScopes`, and the absolute device expiry as the recovery record. Prefer the agent host's secure credential store. For the portable fallback, add `.aipass/project-grant.json` to `.git/info/exclude` when available or otherwise to `.gitignore`, reject a symlink at `.aipass` or the file path, create `.aipass` with owner-only access where supported, and create the file with mode `0600`. Never include `verificationUriComplete`, `userCode`, or an `asg_` token in the recovery record.

Open `verificationUriComplete` once when the environment has a native browser or open-URL capability. Use `open "$verificationUriComplete"` on a local macOS terminal, `xdg-open "$verificationUriComplete"` on a local Linux desktop, `Start-Process $verificationUriComplete` in local Windows PowerShell, or the host's external-link affordance in Replit, Lovable, or another browser IDE. Do not run a desktop opener from a remote or headless server. When opening is unavailable, show the clickable URL.

Opening is only a convenience handoff. Never fetch the page with `curl`, inspect it with browser automation, sign in, click Continue, approve, or otherwise interact with it on the user's behalf. Attempt the automatic open once, not after every pending poll.

Poll no faster than the returned `interval`:

```http
POST /api/v1/agent-auth/token
Content-Type: application/json

{"deviceCode":"in-memory device code"}
```

Continue on `authorization_pending`, slow down on `slow_down`, and stop on denial or expiry. On success, keep the returned `asg_` access token in memory only and replace the recovery record's expiry with the absolute `grantExpiresAt` computed from the response's `expiresIn`. Retain the recovery record until that deadline or explicit revocation. If a turn ends while approval is pending, the next turn must exchange the stored device code instead of creating another request.

## 3. Mandatory preflight

Before every draft write, call:

```http
GET /api/v1/agent-control/space/preflight
Authorization: Bearer asg_REDACTED
```

The returned `handle` is the exact signed-in Space bound during approval or this first preflight. Save it as public metadata in `.aipass/config.json`; do not ask the user to copy it. Inspect `apps` and update the approved matching slug instead of creating a duplicate. The owner-approved grant may manage this slug even when the app was created by a different or lost project fingerprint. It cannot switch to another Space or slug.

Machine-readable failures:

- `MISSING_CREDENTIAL`: no bearer value was sent;
- `INVALID_CREDENTIAL`: malformed, unknown, or wrong credential family;
- `CREDENTIAL_REVOKED`: the owner ended the grant;
- `CREDENTIAL_EXPIRED`: the grant timed out;
- `SPACE_NOT_CLAIMED`: the authenticated owner has no Space; open `/spaces` for them to claim one, then retry with the same grant;
- `SPACE_HANDLE_MISMATCH`: the approved handle is not the owner's current handle.

Keep the same approved grant through SDK/OAuth integration, draft creation, correction, retry, and publication for this exact project app for up to one month. Do not revoke after the first successful call or start a replacement merely because another already-approved operation remains. For an expired, revoked, missing, or invalid grant, start one fresh device authorization for the same target and ask for browser approval. Never rotate or create a generic API key. Do not retry automatically after denial. `404` is not an authentication signal.

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

The server verifies the signed-in owner, approved Space, exact app slug, and session scope. A missing app is created as `DRAFT`; an existing owned app is updated in place and keeps its current `DRAFT`, `PUBLISHED`, or `UNLISTED` visibility. The project fingerprint is recorded for recovery and audit attribution but does not block an owner-authorized update to an older app.

If the response is lost, run preflight again before retrying. Reuse the same slug, fingerprint, content, and idempotency key. Never invent a second slug to bypass an ambiguous response.

## 5. Publish that exact draft

```http
POST /api/v1/agent-control/space/apps/{approved-slug}/publish
Authorization: Bearer asg_REDACTED
```

Only the exact approved app in the owner's Space can be promoted. This also relists an `UNLISTED` app. Confirm the response status is `PUBLISHED`, then open the preflight handle at `/spaces/{handle}/{slug}`. The public Spaces index lists only Spaces with published apps; the owner can still see empty Spaces, drafts, unlisted apps, and failed builder records on their own Space page.

## 6. Manage settings and visibility when requested

Use the write scope for app metadata and visibility changes:

```http
PATCH /api/v1/agent-control/space/apps/{approved-slug}
Authorization: Bearer asg_REDACTED
Content-Type: application/json

{
  "name": "Updated app name",
  "shortDescription": "Updated description.",
  "status": "UNLISTED"
}
```

Send only fields the user asked to change. Supported visibility values are `PUBLISHED` and `UNLISTED`; use the publish endpoint to publish a draft or relist an unlisted app. Settings changes remain confined to the approved owner's Space and exact slug.

Delete only after an explicit user request for this exact app. Deletion is permanent and requires the separately displayed `space-apps:delete` scope:

```http
DELETE /api/v1/agent-control/space/apps/{approved-slug}
Authorization: Bearer asg_REDACTED
```

## 7. Verify and keep the project grant available

Open the real app, exercise its normal AI Pass connection, and make a wallet-funded AI call only with contemporaneous user approval. Confirm one user action makes one model request and renders the real result. Exercise loading, cancellation, one error state, and storage isolation when used.

Do not revoke or delete the recovery record merely because publication completed; a later turn may need to correct or republish the app. Revoke only when the user asks to disconnect, the project identity changes, or the agent must abandon a credential it can no longer protect:

```http
DELETE /api/v1/agent-control/session
Authorization: Bearer asg_REDACTED
```

When revocation is requested, delete the recovery record after the revocation response and confirm a later control-plane request returns `CREDENTIAL_REVOKED`. Delete an expired record as well. Otherwise report that the project grant is recoverable across turns until its one-month expiry or user revocation. Report the public Space URL, slug, and verification performed. Never include credential-bearing responses in the report.
