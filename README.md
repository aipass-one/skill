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
| Build an **app** where YOUR users sign in to AI Pass and you call AI on their behalf | **`aipass-oauth-app`** | OAuth2 + PKCE per-user |

```bash
# Install just the personal-use skill
npx skills add aipass-one/skill --skill aipass-api

# Install just the app-builder skill
npx skills add aipass-one/skill --skill aipass-oauth-app

# Install both
npx skills add aipass-one/skill --all
```

---

## `aipass-api` — Personal use (API key)

For scripts, tools, agents that call AI models for the developer running them.

### Setup

1. Get your API key: [aipass.one/panel/developer.html](https://aipass.one/panel/developer.html)
2. Set env var: `export AIPASS_API_KEY=your_key_here`
3. Base URL: `https://aipass.one/apikey/v1`

---

## Available Models

### 💬 Text Generation

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
| `gemini/gemini-2.5-flash` | Google fast |
| `gemini/gemini-2.5-flash-lite` | Google cheapest |
| `gemini/gemini-2.5-pro` | Google premium |
| `gemini/gemini-3-pro-preview` | Google latest |
| `gemini/gemini-3-flash-preview` | Google latest fast |
| `gemini/gemma-3-27b-it` | Google open model |
| `cerebras/qwen-3-32b` | Fast inference |
| `cerebras/gpt-oss-120b` | Large open model |

### 🎨 Image Generation

| Model | Notes |
|-------|-------|
| `flux-pro/v1.1` | Fast, good quality (~$0.05) |
| `flux-pro/v1.1-ultra` | High quality |
| `imagen4/preview/ultra` | Google's best |
| `standard/1024-x-1024/dall-e-3` | DALL-E 3 |
| `gpt-image-1` | OpenAI native image gen |
| `gpt-image-1-mini` | OpenAI image gen, cheaper |
| `recraft/v3` | Design-focused |
| `seedream/v3` | ByteDance |
| `dreamina/v3.1` | ByteDance |

### ✏️ Image Editing

| Model | Notes |
|-------|-------|
| `gemini/gemini-3-pro-image-preview` | Best for editing |
| `gemini/gemini-2.5-flash-image-preview` | Faster, cheaper |

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
| `gemini/veo-3.0-fast-generate-preview` | Fast video |
| `gemini/veo-3.0-generate-preview` | Quality video |
| `gemini/veo-3.1-fast-generate-preview` | Latest fast video |
| `openai/sora-2` | OpenAI video |
| `openai/sora-2-pro` | OpenAI premium video |

### 🔢 Embeddings

| Model | Dimensions |
|-------|-----------|
| `text-embedding-3-small` | 1536 |
| `text-embedding-3-large` | 3072 |

---

## Quick Examples

### Text Generation
```bash
curl -X POST https://aipass.one/apikey/v1/chat/completions \
  -H "Authorization: Bearer $AIPASS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model": "gpt-5-mini", "messages": [{"role": "user", "content": "Hello!"}]}'
```

### Image Generation
```bash
curl -X POST https://aipass.one/apikey/v1/images/generations \
  -H "Authorization: Bearer $AIPASS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model": "flux-pro/v1.1", "prompt": "A futuristic city", "size": "1024x1024", "n": 1}'
```

### List All Models
```bash
curl https://aipass.one/apikey/v1/models -H "Authorization: Bearer $AIPASS_API_KEY"
```

---

## `aipass-oauth-app` — Build apps for OTHER users (OAuth2)

For products where end users sign in to **their** AI Pass account and AI calls are billed to their budget. Use this if you're shipping a Flutter/iOS/Android app, a web app, a CLI with `--login`, or any product with multiple users.

### Setup

1. Register an OAuth2 client: [aipass.one/panel/developer.html](https://aipass.one/panel/developer.html) → **OAuth2 Clients** → **Create Client**
2. Save your `client_id` and (for confidential clients) `client_secret`
3. Add a `redirect_uri` — e.g. `https://yourapp.com/callback`, `myapp://auth/callback`, `http://localhost:3000/callback`
4. Base URL: `https://aipass.one/oauth2/v1`

### The flow

```
Generate PKCE → /oauth2/authorize → user signs in → /oauth2/token (exchange code)
                                                  → access_token + refresh_token
                                                  → call /oauth2/v1/* with Bearer token
```

CORS is open on `/oauth2/token`, so browser-only apps can exchange codes without a backend.

### First API call (the part most builders get wrong)

> ⚠️ The token goes in the `Authorization` **header**, NOT in the URL path.

```bash
# ✅ Correct
curl -X POST https://aipass.one/oauth2/v1/chat/completions \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"model": "gpt-5-mini", "messages": [{"role": "user", "content": "Hello!"}]}'

# ❌ Common mistakes
curl -X POST https://aipass.one/oauth2/$ACCESS_TOKEN              # token in URL path
curl /oauth2/v1/chat/completions                                  # missing Authorization header
curl -H "Authorization: Bearer $ACCESS_TOKEN" \
  https://aipass.one/apikey/v1/chat/completions                   # wrong namespace (that's the API-key path)
```

### Allowed endpoints

`/oauth2/v1/{models, chat/completions, embeddings, images/generations, images/edits, images/variations, audio/speech, audio/transcriptions, videos, videos/{id}, videos/{id}/content, videos/{id}/remix}`, plus `/oauth2/userinfo` (with `profile:read` scope) and `/api/v1/usage/me/summary`.

See the full skill (`skills/aipass-oauth-app/SKILL.md`) for code examples in JS/Python/Dart, refresh logic, streaming, and the complete common-mistakes list.

---

## About AI Pass

[AI Pass](https://aipass.one) — your universal AI wallet. One key, all AI models, pay as you go.  
Developers earn **50% commission** on every API call their users make.

→ [Get your API key](https://aipass.one/panel/developer.html)  
→ [Full documentation](https://aipass.one/docs)
