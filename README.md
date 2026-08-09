# AI Pass Skills

> Official AI Pass skills for AI agents — one key, all AI models.

## Install

```bash
npx skills add aipass-one/skill
```

You'll be prompted to pick which skill to install. Works with Claude Code, Codex, Cursor, OpenCode, and 38+ other agents.

## Which skill do I want?

| Goal | Skill | Auth |
|---|---|---|
| Call AI for **yourself** with your own API key | **`aipass-api`** | API key (one env var) |
| Build a new **app** where users sign in to AI Pass and you call AI on their behalf | **`aipass-oauth-app`** | OAuth2 + PKCE per-user |
| Add AI Pass to an **existing product** with its own users, sessions, or credits | **`integrate-aipass`** | Backend OAuth broker + PKCE |
| Publish HTML apps to your AI Pass **Space** (aipass.one/spaces/&lt;handle&gt;) from your agent | **`aipass-spaces`** | API key (publishes); SDK + OAuth (inside the published app) |

```bash
# Install just the personal-use skill
npx skills add aipass-one/skill --skill aipass-api

# Install just the app-builder skill
npx skills add aipass-one/skill --skill aipass-oauth-app

# Install the production integration skill
npx skills add aipass-one/skill --skill integrate-aipass

# Install just the space-publish skill (great paired with aipass-api)
npx skills add aipass-one/skill --skill aipass-spaces

# Install everything
npx skills add aipass-one/skill --all
```

---

## `aipass-api` — Personal use (API key)

For scripts, tools, agents that call AI models for the developer running them.

### Setup

1. Get your API key: [aipass.one/panel/developer.html](https://aipass.one/panel/developer.html)
2. Set env var: `export AIPASS_API_KEY=your_key_here`
3. Base URL: `https://aipass.one/v1`

---

## Available Models

Discover the current catalog at runtime. The model-list route returns the OpenAI-compatible `{ "object": "list", "data": [...] }` envelope by default:

```bash
curl -sS "https://aipass.one/v1/models" \
  -H "Authorization: Bearer $AIPASS_API_KEY" \
  | jq -r '.data[] | [.id, .type, (.methods | join(","))] | @tsv'
```

Use `type`, `capability`, and `method` query parameters to narrow the result. The explicit compatibility query `?detailed=false` returns the historical string array. The stable public IDs below are preference examples; confirm availability before use.

### Text Generation

| Model | Notes |
|-------|-------|
| `gpt-5-nano` | Cheapest, simple tasks |
| `gpt-5-mini` | Good balance, recommended default |
| `gpt-5` | Premium OpenAI |
| `gpt-5.1` | Latest OpenAI |
| `gpt-5.1-codex` | Code-optimized |
| `gpt-5.1-codex-mini` | Code-optimized, cheaper |
| `claude-opus-4-6` | Anthropic best (reasoning, code) |
| `claude-sonnet-4-5` | Anthropic premium |
| `claude-haiku-4-5` | Anthropic fast/cheap |
| `gemini-2.5-flash` | Google fast |
| `gemini-2.5-flash-lite` | Google cheapest |
| `gemini-2.5-pro` | Google premium |
| `gemini-3.1-pro-preview` | Google latest |
| `gemini-3-flash-preview` | Google latest fast |
| `gemma-3-27b-it` | Google open model |

### 🎨 Image Generation

| Model | Notes |
|-------|-------|
| `nano-banana-2` | Google's latest (via Fal) — best identity preservation |
| `nano-banana-pro` | Premium tier of Nano Banana |
| `gpt-image-2` | OpenAI's GPT Image 2 (via Fal) |
| `flux-pro-v1.1` | Fast, good quality (~$0.05) |
| `flux-pro-v1.1-ultra` | High quality |
| `imagen-4-ultra` | Google's best |
| `dall-e-3` | DALL-E 3 |
| `gpt-image-1` | OpenAI native image gen |
| `gpt-image-1-mini` | OpenAI image gen, cheaper |
| `recraft-v3` | Design-focused |
| `seedream-v3` | ByteDance |
| `dreamina-v3.1` | ByteDance |

> **Tip:** filter `/v1/models` by catalog metadata. Do not infer behavior from a provider prefix or path suffix.

### ✏️ Image Editing

| Model | Notes |
|-------|-------|
| `nano-banana-2-edit` | Best face preservation, supports multi-image |
| `gpt-image-2-edit` | Strong alternative, supports multi-image |
| `nano-banana-pro-edit` | Premium Nano Banana edit |
| `gemini-3-pro-image-preview` | Gemini-routed (via `/chat/completions` with multimodal) |
| `gemini-2.5-flash-image-preview` | Faster, cheaper Gemini option |

Image-edit models expose `image_edit` in their catalog `methods`. Public IDs are provider-neutral and use stable names such as `nano-banana-2-edit`; private provider routes are never discovery output. Multi-image input uses repeated `image` form fields (REST) or a `File[]` array (SDK).

Discover with `/v1/models?type=image&method=image_edit`, then choose from the returned stable IDs. See the [`aipass-oauth-app` skill](skills/aipass-oauth-app/SKILL.md) for SDK catalog filtering and selection.

### 🔊 Text-to-Speech

| Model | Voices |
|-------|--------|
| `tts-1` | alloy, echo, fable, onyx, nova, shimmer |
| `tts-1-hd` | alloy, echo, fable, onyx, nova, shimmer |
| `gpt-4o-mini-tts` | alloy, echo, fable, onyx, nova, shimmer |

### 🎙️ Transcription (Speech-to-Text)

| Model | Formats |
|-------|---------|
| `whisper-1` | mp3, mp4, mpeg, mpga, m4a, wav, webm, ogg |

### 🎬 Video Generation

| Model | Notes |
|-------|-------|
| `veo-3.0-fast-generate-preview` | Fast video |
| `veo-3.0-generate-preview` | Quality video |
| `veo-3.1-fast-generate-preview` | Latest fast video |
| `sora-2` | OpenAI video |
| `sora-2-pro` | OpenAI premium video |

### 🔢 Embeddings

| Model | Dimensions |
|-------|-----------|
| `text-embedding-3-small` | 1536 |
| `text-embedding-3-large` | 3072 |

---

## Quick Examples

### Text Generation
```bash
curl -X POST https://aipass.one/v1/chat/completions \
  -H "Authorization: Bearer $AIPASS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model": "gpt-5-mini", "messages": [{"role": "user", "content": "Hello!"}]}'
```

### Image Generation
```bash
curl -X POST https://aipass.one/v1/images/generations \
  -H "Authorization: Bearer $AIPASS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model": "flux-pro-v1.1", "prompt": "A futuristic city", "size": "1024x1024", "n": 1}'
```

### List All Models
```bash
curl https://aipass.one/v1/models -H "Authorization: Bearer $AIPASS_API_KEY"
```

---

## `aipass-oauth-app` — Build apps for OTHER users (OAuth2)

For products where end users sign in to **their** AI Pass account and AI calls are billed to their budget. Use this if you're shipping a Flutter/iOS/Android app, a web app, a CLI with `--login`, or any product with multiple users.

### Setup

1. Register an OAuth2 client: [aipass.one/panel/developer.html](https://aipass.one/panel/developer.html) → **OAuth2 Clients** → **Create Client**
2. Save your `client_id` and (for confidential clients) `client_secret`
3. Add a `redirect_uri` — e.g. `https://yourapp.com/callback`, `myapp://auth/callback`, `http://localhost:3000/callback`
4. Resource base URL: `https://aipass.one/v1`

### The flow

```
Generate PKCE → /oauth2/authorize → user signs in → /oauth2/token (exchange code)
                                                  → access_token + refresh_token
                                                  → call /v1/* with Bearer token
```

CORS is open on `/oauth2/token`, so browser-only apps can exchange codes without a backend.

### First API call (the part most builders get wrong)

> ⚠️ The token goes in the `Authorization` **header**, NOT in the URL path.

```bash
# ✅ Correct
curl -X POST https://aipass.one/v1/chat/completions \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "X-AIPass-OAuth-Client-Id: $CLIENT_ID" \
  -H "Content-Type: application/json" \
  -d '{"model": "gpt-5-mini", "messages": [{"role": "user", "content": "Hello!"}]}'

# ❌ Common mistakes
curl -X POST https://aipass.one/oauth2/$ACCESS_TOKEN              # token in URL path
curl /v1/chat/completions                                         # missing Authorization header
curl https://aipass.one/v1/chat/completions/$ACCESS_TOKEN         # token in the resource URL
```

### Allowed endpoints

`/v1/{models, chat/completions, embeddings, images/generations, images/edits, images/variations, audio/speech, audio/transcriptions, videos, videos/{id}, videos/{id}/content, videos/{id}/remix}`, plus `/oauth2/userinfo` (with `profile:read` scope) and `/api/v1/usage/me/summary`.

The canonical `/v1/*` resource API accepts either credential type in the Bearer header. Existing `/apikey/v1/*` and `/oauth2/v1/*` resource URLs remain supported as compatibility aliases, each with its previous credential contract. OAuth protocol endpoints such as authorize, token, revoke, and userinfo remain under `/oauth2/*`.

See the full skill (`skills/aipass-oauth-app/SKILL.md`) for code examples in JS/Python/Dart, refresh logic, streaming, and the complete common-mistakes list.

### SDK storage and app-to-app workflows

Browser SDK apps also receive free authenticated persistence:

- `AiPass.data` — a private 1 MB JSON document per user/app;
- `AiPass.files` — private files up to 10 MB each and 50 MB per user/app;
- `AiPass.shared` — user-owned named vaults containing keyed JSON records and private files, shared with exact apps through user-confirmed `READ`, `CONTRIBUTE`, or `READ_WRITE` grants.

Private namespaces remain private. Cross-app access exists only through an explicit shared-vault grant and is always constrained to the same signed-in user. See [the storage reference](skills/aipass-oauth-app/references/storage.md) for methods, quotas, and a complete handoff pattern.

---

## `integrate-aipass` — Retrofit an existing product

For established products that already own authentication, sessions, a database, AI features, or free/subscription credits. This skill guides an agent through the production architecture used by integrations such as dr.aft:

- backend OAuth broker with one-time state and PKCE;
- encrypted server-side access and refresh tokens;
- verified identity linking and local session minting;
- concurrency-safe refresh-token rotation;
- OpenAI-compatible model routing through each user's AI Pass balance;
- live balance, checkout, and funding-source UI;
- safe fallback to product credits without double billing;
- security, regression, local, and deployment tests.

Use `aipass-oauth-app` for a broad SDK/API cookbook or a new client-only app. Use `integrate-aipass` when AI Pass must fit safely into an architecture that already exists.

The full public developer guide is also available at [aipass.one/docs/rest/integration.html](https://aipass.one/docs/rest/integration.html).

---

## `aipass-spaces` — Publish HTML apps to your Space

Every AI Pass user can claim a handle at [aipass.one/spaces](https://aipass.one/spaces) and gets a personal app workspace at `aipass.one/spaces/<handle>`. With this skill, an agent (Claude Code, Cursor, etc.) can build an HTML app and publish it to your Space using only your API key — no OAuth setup on your side, no hosting to configure.

### Setup

1. Claim a handle at [aipass.one/spaces](https://aipass.one/spaces) — gives you `aipass.one/spaces/<your-handle>`.
2. Get your API key: [aipass.one/panel/developer.html](https://aipass.one/panel/developer.html) → API Keys.
3. `export AIPASS_API_KEY=...`

### Flow

```bash
# Discover your space + the OAuth client id (one per handle, shared by every app you publish)
curl -s https://aipass.one/api/v1/spaces/me -H "Authorization: Bearer $AIPASS_API_KEY"

# Publish an HTML file — leave the literal "PLACEHOLDER_CLIENT_ID" in the HTML; the server replaces it
curl -X POST https://aipass.one/api/v1/spaces/me/apps \
  -H "Authorization: Bearer $AIPASS_API_KEY" -H "Content-Type: application/json" \
  -d '{"name":"My App","shortDescription":"...","htmlContent":"<!DOCTYPE html>...PLACEHOLDER_CLIENT_ID..."}'
```

The published app uses the AI Pass JS SDK inside it (covered by `aipass-oauth-app`) so visitors sign in and AI calls are billed to *their* wallet — not yours. That's how you earn the 50% commission on Spaces.

See the full skill (`skills/aipass-spaces/SKILL.md`) for the HTML boilerplate, field rules, update endpoint, and an end-to-end working example.

---

## About AI Pass

[AI Pass](https://aipass.one) — your universal AI wallet. One key, all AI models, pay as you go.  
Developers earn **50% commission** on every API call their users make.

→ [Get your API key](https://aipass.one/panel/developer.html)  
→ [Full documentation](https://aipass.one/docs)
