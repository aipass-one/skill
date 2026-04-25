---
name: aipass-oauth-app
description: Build apps where YOUR users sign in via AI Pass and you call AI on their behalf (OAuth2 + PKCE). Use this when you're shipping a product to other people. If you're calling AI for yourself, use `aipass-api` instead.
version: 1.0.0
---

# AI Pass OAuth — Build Apps for Other Users

You are building an app/site/CLI where end users sign in with their own AI Pass account. AI calls are billed to **their** budget, not yours. Auth uses OAuth2 + PKCE.

> **Wrong skill?** If you're calling AI **for yourself** with your own API key, stop and use `aipass-api` instead — it's much simpler. This skill is only for app builders.

## Quick decision tree

| You want to... | Use |
|---|---|
| Call `gpt-5-mini` to summarize text in your own script | `aipass-api` (one env var, done) |
| Build a website where 10,000 users log in and chat with AI | **this skill** |
| Build a Flutter/iOS app where users sign in with AI Pass | **this skill** |
| Build a CLI tool with `--login` that runs in your users' terminals | **this skill** |

---

## Setup (one-time)

1. Register an OAuth2 client: https://aipass.one/panel/developer.html → **OAuth2 Clients** → **Create Client**
2. Save:
   - `client_id` — public, looks like `client_xxxxxxxxx`
   - `redirect_uri` — where the auth server sends users back (e.g. `https://yourapp.com/callback`, `myapp://auth/callback`, or `http://localhost:3000/callback` for dev)
   - `client_secret` — only needed for **confidential** (server-side) clients. For mobile/web/SPAs, skip secret and rely on PKCE.

## Auth flow (5 steps)

```
1. Generate PKCE pair                      [your code]
2. Send user to /oauth2/authorize          [browser]
3. User signs in + clicks Authorize        [browser]
4. AI Pass redirects back with ?code=...   [browser → your callback]
5. Exchange code for tokens                [your code]
   → got access_token + refresh_token
6. Call /oauth2/v1/* with Bearer header    [your code]
```

CORS is open on `/oauth2/token`, so browser-only apps can exchange codes without a backend.

---

## Step 1 — Generate PKCE + state (per login)

```bash
# Bash one-liner
code_verifier=$(openssl rand -base64 64 | tr -d "=+/" | cut -c1-64)
code_challenge=$(echo -n "$code_verifier" | openssl dgst -sha256 -binary | base64 | tr -d "=+/" | tr "+/" "-_")
state=$(openssl rand -hex 16)
```

```python
# Python
import secrets, hashlib, base64
code_verifier = secrets.token_urlsafe(64)[:64]
code_challenge = base64.urlsafe_b64encode(
    hashlib.sha256(code_verifier.encode()).digest()
).rstrip(b"=").decode()
state = secrets.token_urlsafe(16)
```

```javascript
// JS (browser/Node)
function rand(n){return [...crypto.getRandomValues(new Uint8Array(n))].map(b=>b.toString(36)).join('').slice(0,n)}
const code_verifier = rand(64);
const code_challenge = btoa(String.fromCharCode(...new Uint8Array(
  await crypto.subtle.digest('SHA-256', new TextEncoder().encode(code_verifier))
))).replace(/=/g,'').replace(/\+/g,'-').replace(/\//g,'_');
const state = rand(24);
```

```dart
// Dart (Flutter)
import 'package:crypto/crypto.dart';
import 'dart:convert';
import 'dart:math';
final r = Random.secure();
final code_verifier = List.generate(64, (_) => 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'[r.nextInt(62)]).join();
final code_challenge = base64Url.encode(sha256.convert(utf8.encode(code_verifier)).bytes).replaceAll('=','');
final state = List.generate(24, (_) => 'abcdefghijklmnopqrstuvwxyz0123456789'[r.nextInt(36)]).join();
```

**Keep `code_verifier` and `state` in session storage / memory until the redirect comes back.**

---

## Step 2 — Send user to authorize

```
GET https://aipass.one/oauth2/authorize
  ?response_type=code
  &client_id=YOUR_CLIENT_ID
  &redirect_uri=YOUR_REDIRECT_URI
  &scope=api:access profile:read
  &state=STATE_VALUE
  &code_challenge=PKCE_CHALLENGE
  &code_challenge_method=S256
```

Open this URL in the user's browser (web: full page redirect; mobile: in-app browser / `url_launcher`; CLI: `xdg-open` / `open`).

After they click Authorize, AI Pass redirects to:
```
YOUR_REDIRECT_URI?code=AUTH_CODE&state=STATE_VALUE
```

**Validate `state` matches what you sent before continuing.** If not, abort.

---

## Step 3 — Exchange code for access token

```bash
curl -X POST https://aipass.one/oauth2/token \
  -H "Content-Type: application/json" \
  -d '{
    "grantType": "authorization_code",
    "code": "AUTH_CODE_FROM_REDIRECT",
    "codeVerifier": "ORIGINAL_CODE_VERIFIER",
    "clientId": "YOUR_CLIENT_ID",
    "redirectUri": "YOUR_REDIRECT_URI"
  }'
```

**Response:**
```json
{
  "access_token": "vBgEoUfL3KC_OCXj-YBxayxIJkKzLHKXG06gXqum1tU",
  "refresh_token": "...",
  "expires_in": 6048000,
  "token_type": "Bearer",
  "scope": "api:access profile:read"
}
```

Store both tokens securely (encrypted at rest, never in localStorage/cookies on the auth domain).

---

## Step 4 — 🎯 Make your first API call

**This is the step most newcomers get wrong.** The token goes in the `Authorization` header, NOT in the URL.

```bash
# ✅ CORRECT
curl -X POST https://aipass.one/oauth2/v1/chat/completions \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-5-mini",
    "messages": [
      {"role": "user", "content": "Hello!"}
    ]
  }'
```

```python
# ✅ CORRECT
import requests
r = requests.post(
    "https://aipass.one/oauth2/v1/chat/completions",
    headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
    json={"model": "gpt-5-mini", "messages": [{"role": "user", "content": "Hello!"}]},
)
print(r.json()["choices"][0]["message"]["content"])
```

```javascript
// ✅ CORRECT
const r = await fetch("https://aipass.one/oauth2/v1/chat/completions", {
  method: "POST",
  headers: {
    "Authorization": `Bearer ${access_token}`,
    "Content-Type": "application/json",
  },
  body: JSON.stringify({
    model: "gpt-5-mini",
    messages: [{role: "user", content: "Hello!"}],
  }),
});
console.log((await r.json()).choices[0].message.content);
```

---

## Step 5 — Refresh tokens (when you get a 401)

Access tokens expire (default ~70 days). When an API call returns 401:

```bash
curl -X POST https://aipass.one/oauth2/token \
  -H "Content-Type: application/json" \
  -d '{
    "grantType": "refresh_token",
    "refreshToken": "YOUR_REFRESH_TOKEN",
    "clientId": "YOUR_CLIENT_ID"
  }'
```

If the refresh also fails (e.g. user revoked your app), restart the OAuth flow from Step 1.

---

## ❌ Common mistakes (don't do these)

These are real mistakes real builders have made — listed so you can avoid them:

```bash
# ❌ Token in the URL path (NOT how Bearer auth works)
curl -X POST https://aipass.one/oauth2/$ACCESS_TOKEN
curl https://aipass.one/oauth2/v1/chat/completions/$ACCESS_TOKEN

# ❌ Calling /apikey/v1/* with an OAuth access token
# /apikey/v1/* is for API-key auth (the `aipass-api` skill).
# /oauth2/v1/* is for OAuth access tokens. Use the right namespace.
curl -H "Authorization: Bearer $ACCESS_TOKEN" \
  https://aipass.one/apikey/v1/chat/completions   # WRONG namespace
curl -H "Authorization: Bearer $ACCESS_TOKEN" \
  https://aipass.one/oauth2/v1/chat/completions   # CORRECT

# ❌ Using a placeholder/dummy code_challenge
# The /oauth2/token call will succeed, but PKCE is not actually verifying anything.
# The challenge MUST be SHA256(code_verifier) base64url-encoded.
# Don't ship `code_challenge=AAAAAAAAAAAAAA...` to production.

# ❌ Forgetting to validate `state` on the redirect
# An attacker can fixate auth codes if you skip this. Always check state.

# ❌ Storing tokens in localStorage on the same origin as your auth UI
# XSS = full account takeover. Use httpOnly cookies (server-side) or
# encrypted secure storage (mobile keychain).
```

---

## All allowed endpoints

All require `Authorization: Bearer ACCESS_TOKEN` and `api:access` scope. Base URL: `https://aipass.one/oauth2/v1`

| Category | Endpoint | Notes |
|---|---|---|
| Models | `GET /models` | List all available models |
| Models | `GET /models/{id}` | Single model info |
| Chat | `POST /chat/completions` | Chat + multimodal (vision) — see below |
| Embeddings | `POST /embeddings` | Vector embeddings |
| Images | `POST /images/generations` | Text-to-image |
| Images | `POST /images/edits` | Edit/inpaint with mask |
| Images | `POST /images/variations` | Variations of an image |
| Audio | `POST /audio/speech` | TTS — returns audio bytes |
| Audio | `POST /audio/transcriptions` | STT — multipart/form-data |
| Video | `POST /videos` | Video generation |
| Video | `POST /videos/{id}/remix` | Remix existing video |
| Video | `GET /videos/{id}` | Video metadata |
| Video | `GET /videos/{id}/content` | Download video bytes |
| User | `GET /oauth2/userinfo` | User profile (needs `profile:read` scope) |
| Usage | `GET /api/v1/usage/me/summary` | User's spend + remaining budget |
| Token | `POST /oauth2/revoke?token=ACCESS_TOKEN` | Revoke a token |

> Only allowlisted endpoints are proxied. Anything outside this list returns 403/404.

---

## Available models

Same model catalog as `aipass-api`. List at runtime:
```bash
curl https://aipass.one/oauth2/v1/models -H "Authorization: Bearer $ACCESS_TOKEN"
```

Frequently used:
- **Text:** `gpt-5-mini` (default), `gpt-5-nano` (cheapest), `gpt-5.1`, `claude-sonnet-4-5`, `claude-haiku-4-5`, `gemini/gemini-2.5-flash-lite`, `gemini/gemini-3-pro-preview`
- **Image gen:** `flux-pro/v1.1`, `gpt-image-1`, `gpt-image-1-mini`, `dall-e-3`, `imagen4/preview/ultra`
- **Image edit:** `gemini/gemini-3-pro-image-preview` (via `/chat/completions` with multimodal content)
- **Audio:** `tts-1`, `tts-1-hd`, `whisper-1`, `gpt-4o-mini-tts`
- **Video:** `gemini/veo-3.1-fast-generate-preview`, `openai/sora-2`
- **Embeddings:** `text-embedding-3-small`, `text-embedding-3-large`

---

## Vision (multimodal chat)

Same `/oauth2/v1/chat/completions` endpoint, but `content` is an array:

```json
{
  "model": "gpt-5-mini",
  "messages": [{
    "role": "user",
    "content": [
      {"type": "text", "text": "What's in this image?"},
      {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,/9j/4AAQ..."}}
    ]
  }]
}
```

Compress images to ~800KB before base64-encoding.

---

## Streaming

Set `"stream": true` in the chat completions body. Response is Server-Sent Events:

```
data: {"choices":[{"delta":{"content":"Hello"}}]}
data: {"choices":[{"delta":{"content":" world"}}]}
data: [DONE]
```

```javascript
// JS streaming consumer
const r = await fetch("https://aipass.one/oauth2/v1/chat/completions", {
  method: "POST",
  headers: {"Authorization": `Bearer ${token}`, "Content-Type": "application/json"},
  body: JSON.stringify({model: "gpt-5-mini", messages: [...], stream: true}),
});
const reader = r.body.getReader();
const dec = new TextDecoder();
while (true) {
  const {value, done} = await reader.read();
  if (done) break;
  for (const line of dec.decode(value).split("\n")) {
    if (line.startsWith("data: ")) {
      const j = line.slice(6);
      if (j === "[DONE]") return;
      const delta = JSON.parse(j).choices?.[0]?.delta?.content;
      if (delta) process.stdout.write(delta);
    }
  }
}
```

---

## Usage & balance tracking

Show users their remaining budget:

```bash
curl https://aipass.one/api/v1/usage/me/summary \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

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

Cache for 5–10 minutes — no need to poll on every call.

---

## Revoke

When a user logs out, revoke the token:
```bash
curl -X POST "https://aipass.one/oauth2/revoke?token=$ACCESS_TOKEN" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

---

## Help

- Stuck? Join Discord: https://discord.gg/hENftFRMMD
- Full human docs: https://aipass.one/docs/rest/integration
- Dashboard: https://aipass.one/panel/developer

Developers earn **50% commission** on every API call their users make through your app.
