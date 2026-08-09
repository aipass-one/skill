---
name: aipass-oauth-app
description: Build browser, mobile, desktop, CLI, or server apps where end users connect AI Pass through OAuth2 + PKCE, pay for their own AI calls, and optionally use private app storage or user-approved shared JSON/file vaults. Use when shipping a product to other people; use `aipass-api` instead for personal API-key calls.
---

# AI Pass OAuth — Build Apps for Other Users

You are building an app/site/CLI where end users sign in with their own AI Pass account. AI calls are billed to **their** budget, not yours. Auth uses OAuth2 + PKCE.

> **Wrong skill?** If you're calling AI **for yourself** with your own API key, stop and use `aipass-api` instead — it's much simpler. This skill is only for app builders.

## Quick decision tree

| You want to... | Use |
|---|---|
| Call `gpt-5-mini` to summarize text in your own script | `aipass-api` (one env var, done) |
| Build a website where users log in and use AI | **this skill** |
| Build a Flutter/iOS app where users sign in with AI Pass | **this skill** |
| Build a CLI tool with `--login` that runs in your users' terminals | **this skill** |

---

## Two paths

| Path | When to use | Effort |
|---|---|---|
| **A. Browser SDK** | Web app, single-page app, anything in a browser | Trivial — 5 lines, SDK handles PKCE for you |
| **B. Raw REST** | Mobile, CLI, native desktop, server-side | Medium — implement PKCE yourself |

If you're building a website and don't have a strong reason to do otherwise, **use Path A**. The SDK handles login, token refresh, and balance display widget for you.

---

# Path A — Browser SDK (the easy one)

For any app that runs in a browser. Drop in two `<script>` tags, call `AiPass.initialize()`, done.

## A.1 Setup

The user does this once before they ask you to build anything:

1. Sign up at [aipass.one](https://aipass.one) and add a few cents of credit (free $1 on signup).
2. Go to [aipass.one/panel/developer](https://aipass.one/panel/developer.html) → **OAuth2 Clients** → **Create Client**.
3. Copy the `client_id` (looks like `client_xxxxxxxxx`).
4. Hand it to you.

Now in your HTML:

```html
<!DOCTYPE html>
<html>
<head>
  <link rel="stylesheet" href="https://aipass.one/aipass-ui.css">
</head>
<body>
  <!-- Zero-config auth widget: shows "CONNECT" when logged out, balance when logged in -->
  <div data-aipass-button></div>

  <!-- Your app UI here -->

  <script src="https://aipass.one/aipass-sdk.js"></script>
  <script>
    AiPass.initialize({
      clientId: 'client_xxxxxxxxx',  // from step 3
      requireLogin: false             // default. true forces a login modal on page load — bad UX.
                                      // Protected SDK calls show the login modal when needed.
    });
  </script>
</body>
</html>
```

That's the entire auth setup. The SDK handles the OAuth2 + PKCE popup, token storage, refresh, and balance display. You write zero lines of auth code.

## A.2 Authentication — let protected calls open the SDK modal

Initialize with `requireLogin: false` and call the protected SDK method directly from the user's action. Generation, private storage, and shared-vault methods call the SDK authentication gate internally. When signed out, the SDK shows its branded login modal, waits for OAuth, and resumes the original operation without a second click.

```javascript
document.querySelector('#generate').addEventListener('click', async () => {
  try {
    const result = await AiPass.generateCompletion({
      model: 'gpt-5-mini',
      prompt: document.querySelector('#prompt').value
    });
    renderResult(result);
  } catch (error) {
    if (error?.code === 'AUTH_REQUIRED') return; // user dismissed the modal
    showError(error);
  }
});
```

Do not disable the action because `AiPass.isAuthenticated()` is false, replace the button with a custom sign-in flow, or wait for `aipass:login` before making the call. Those patterns bypass the automatic gate and commonly leave the UI stale after popup login.

**Direct API.**
- `AiPass.isAuthenticated()` — optional state for account/status UI, not a prerequisite for protected calls.
- `AiPass.getAccessToken()` — for raw fetch calls if you bypass the SDK.
- `await AiPass.login()` / `await AiPass.logout()` — programmatic triggers.

**Event semantics — read carefully.**
- `aipass:login` — *transition* event (user just signed in). NOT a state signal. Does not fire on storage-restore.
- `aipass:logout` — transition (user signed out, or refresh failed).
- `aipass:balance` — fires periodically and after successful AI calls. `event.detail.balance` is a number.
- `aipass:insufficient-balance` — the SDK detected an AI request that needs more credit and started wallet recovery.
- `aipass:error` — auth/OAuth errors only. Does NOT fire for `/v1/*` API errors — those throw from the SDK method call.

**Anti-pattern to avoid:**

```javascript
// ❌ Prevents the protected call from reaching the SDK's automatic auth gate.
if (!AiPass.isAuthenticated()) {
  showCustomLoginScreen();
  return;
}
```

## A.3 Discover models at runtime

Model availability evolves and can differ between environments. Discover the public catalog at runtime and select from the stable IDs it returns. Provider-qualified routes are private implementation details.

### A.3.1 Use the SDK's two explicit return shapes

`AiPass.getModels()` returns a plain array of stable public ID strings. `AiPass.getModelCatalog()` returns the OpenAI-compatible `{ object: 'list', data: [...] }` envelope with safe metadata.

```javascript
const ids = await AiPass.getModels();
console.log(`${ids.length} models available`);

const { data: editModels } = await AiPass.getModelCatalog({
  type: 'image',
  method: 'image_edit'
});
// Each entry includes id, type, capabilities, and methods.
```

`AiPass.getModels({ detailed: true })` remains a compatibility alias for the catalog envelope, but new code should call `getModelCatalog()` directly.

### A.3.2 Filter with catalog metadata

| Task | Catalog filters | Example stable public IDs |
|---|---|---|
| **Image edit** | `{ type: 'image', method: 'image_edit' }` | `nano-banana-2-edit`, `gpt-image-2-edit`, `nano-banana-pro-edit` |
| **Image generation** | `{ type: 'image', method: 'image_generation' }` | `nano-banana-2`, `flux-pro-v1.1-ultra`, `imagen-4-ultra` |
| **Image upscale** | `{ type: 'image', method: 'image_edit' }` | `aura-sr`, `topaz-upscale-image` |
| **Background removal** | `{ type: 'image', method: 'image_edit' }` | `birefnet-v2`, `ben-v2-image` |
| **Chat / text** | `{ type: 'text', method: 'chat_completions' }` | `gpt-5-mini`, `claude-haiku-4-5`, `gemini-2.5-flash-lite` |
| **Vision (multimodal)** | `{ capability: 'vision', method: 'chat_completions' }` | `gemini-2.5-flash`, `gemini-2.5-pro` |
| **TTS** | `{ type: 'audio', method: 'audio_speech' }` | `tts-1`, `gpt-4o-mini-tts` |
| **Transcription** | `{ type: 'audio', method: 'audio_transcription' }` | `whisper-1` |
| **Embeddings** | `{ type: 'embedding', method: 'embeddings' }` | `text-embedding-3-small` |
| **Video** | `{ type: 'video', method: 'video_generation' }` | `veo-3.1-fast-generate-preview`, `sora-2` |

Do not infer behavior from an ID's shape. The catalog's `type`, `capabilities`, and `methods` fields are the contract.

### A.3.3 Recommended picker

```javascript
function pickModel(models, task) {
  const available = new Set(models.map(model => model.id));
  const preferences = {
    'face-preserving-edit': ['nano-banana-2-edit', 'gpt-image-2-edit', 'nano-banana-pro-edit'],
    'image-edit': ['nano-banana-2-edit', 'gpt-image-2-edit'],
    'image-gen': ['imagen-4-ultra', 'flux-pro-v1.1-ultra', 'nano-banana-2'],
    'cheap-chat': ['gpt-5-nano', 'gemini-2.5-flash-lite'],
    'quality-chat': ['claude-sonnet-4-5', 'gpt-5.1', 'gpt-5-mini'],
    'tts': ['tts-1'],
    'transcribe': ['whisper-1']
  };
  return (preferences[task] || []).find(id => available.has(id)) || null;
}

const { data } = await AiPass.getModelCatalog({ type: 'image', method: 'image_edit' });
const editModel = pickModel(data, 'face-preserving-edit');
if (!editModel) {
  showError("This feature isn't available on your account.");
  return;
}
```

Discover first, then pass the selected stable public ID unchanged to the generation method.

## A.4 Generate text

```javascript
// Programmatic (parse the full response):
const result = await AiPass.generateCompletion({
  prompt: 'Explain async/await in two sentences.',
  model: 'gpt-5-mini',  // OR pickModel(data, 'cheap-chat')
  temperature: 0.7
  // DO NOT pass maxTokens. Reasoning models (gpt-5-mini, gpt-5, o-series)
  // count internal reasoning against the cap and silently return content:null
  // when it's too low. Omit it and the model uses its native max (128K out
  // for gpt-5-mini). Only set it when you genuinely need to truncate output.
});
console.log(result.choices[0].message.content);

// Messages format (recommended for multi-turn):
const chat = await AiPass.generateCompletion({
  messages: [
    { role: 'system', content: 'You are a haiku poet.' },
    { role: 'user', content: 'Write one about debugging.' }
  ],
  model: 'gpt-5-mini'
});

// VISIBLE chat output → use streamText, not generateCompletion.
// Tokens render as they arrive (~50ms each) instead of waiting 5-30s.
const final = await AiPass.streamText(
  { model: 'gpt-5-mini', messages: [{ role: 'user', content: 'tell a joke' }] },
  (full) => { document.getElementById('chat-output').textContent = full; }
);
```

## A.5 Vision (analyze images)

Same `generateCompletion` call, with `content` as an array including an image:

```javascript
const fileToDataUrl = (file) => new Promise((resolve, reject) => {
  const r = new FileReader();
  r.onload = () => resolve(r.result);
  r.onerror = reject;
  r.readAsDataURL(file);
});

const dataUrl = await fileToDataUrl(fileInput.files[0]);

const result = await AiPass.generateCompletion({
  messages: [{
    role: 'user',
    content: [
      { type: 'text', text: 'What hairstyle is this person wearing?' },
      { type: 'image_url', image_url: { url: dataUrl } }
    ]
  }],
  model: 'gpt-5-mini'
});
```

Compress images to ~800KB before encoding to keep latency down.

## A.6 Generate images (text-to-image)

```javascript
const { data } = await AiPass.getModelCatalog({ type: 'image', method: 'image_generation' });
const model = pickModel(data, 'image-gen');

const result = await AiPass.generateImage({
  prompt: 'A futuristic city at sunset, photorealistic',
  model,                     // e.g. 'imagen-4-ultra'
  n: 1,
  size: '1024x1024',
  responseFormat: 'url'      // or 'b64_json'
});

// Always handle BOTH response shapes:
const payload = result.data[0];
const imageUrl = payload.url || `data:image/png;base64,${payload.b64_json}`;
document.getElementById('output').src = imageUrl;
```

## A.7 Edit images — single image

This is the bread-and-butter call for any "transform a photo" app (hair styles, fashion try-on, restyle, etc.).

```javascript
const file = document.getElementById('photo').files[0];

const { data } = await AiPass.getModelCatalog({ type: 'image', method: 'image_edit' });
const model = pickModel(data, 'face-preserving-edit');
// Resolves to a stable public ID such as 'nano-banana-2-edit'.

const result = await AiPass.editImage({
  image: file,                        // single File object
  prompt: 'Change the hairstyle to a sleek bob cut. Preserve the face, lighting, and clothing exactly.',
  model,
  n: 1,
  size: '1024x1024',
  responseFormat: 'url'
});

const payload = result.data[0];
const url = payload.url || `data:image/png;base64,${payload.b64_json}`;
```

**Prompt tips for "swap one attribute":**
- Lead with what to change (`"Change the hairstyle to ..."`).
- Explicitly call out what to preserve (`"Preserve the face, lighting, and clothing exactly."`). Without this, models drift.
- Avoid "make it look like X celebrity" — frequently rejected by content filters.

## A.8 Edit images — multi-image (reference + target)

`editImage` accepts an **array of files** for models that support multi-image input. Useful for "use this as reference":

```javascript
const target    = document.getElementById('your-photo').files[0];
const reference = document.getElementById('reference').files[0];

const { data } = await AiPass.getModelCatalog({ type: 'image', method: 'image_edit' });
// Confirm multi-image support for the selected model's input contract.
const model = pickModel(data, 'image-edit');

const result = await AiPass.editImage({
  image: [target, reference],         // <-- array, not a single file
  prompt: 'Apply the hairstyle from the second image to the person in the first image. Preserve the first person\'s face, lighting, and clothing.',
  model,
  size: '1024x1024'
});
```

**Preferred multi-image edit models** (verify the current catalog and input contract at runtime):
- `nano-banana-2-edit`
- `nano-banana-pro-edit`
- `gpt-image-2-edit`

## A.9 Audio + embeddings (one-liners)

```javascript
// Text → speech (returns audio Blob)
const audioBlob = await AiPass.generateSpeech({
  text: 'Hello world',
  model: 'tts-1',
  voice: 'nova',                       // alloy | echo | fable | onyx | nova | shimmer
  responseFormat: 'mp3',
  speed: 1.0
});
new Audio(URL.createObjectURL(audioBlob)).play();

// Speech → text
const transcription = await AiPass.transcribeAudio({
  audioFile: fileInput.files[0],
  model: 'whisper-1',
  language: 'en'
});
console.log(transcription.text);

// Embeddings
const embeds = await AiPass.generateEmbeddings({
  input: ['First text', 'Second text'],
  model: 'text-embedding-3-small'
});
console.log(embeds.data[0].embedding);   // Float32Array
```

## A.10 Show user balance

The `<div data-aipass-button>` widget already shows balance automatically. If you want it elsewhere:

```javascript
const summary = await AiPass.getUserBalance();
console.log(`$${summary.data.remainingBudget} remaining of $${summary.data.maxBudget}`);
console.log(`Spent: $${summary.data.totalCost}`);
```

Cache for 5–10 minutes — no need to poll on every call.

Do not preflight balance before generation. The server is authoritative and concurrent requests may change available funds. If an AI request is rejected with HTTP 402 or an insufficient-balance response, the SDK automatically opens the same account wallet used by the header widget. The thrown error is marked with `code: 'INSUFFICIENT_BALANCE'`, `insufficientBalanceHandled: true`, and the legacy `budgetExceededHandled: true` flag.

Preserve the user's work and show a retry action. If the user dismisses the automatic wallet and asks to reopen it, call:

```javascript
await AiPass.openWallet();
```

## A.11 Persistent data, files, and cross-app collaboration

The SDK includes three free, authenticated storage surfaces:

- `AiPass.data`: one private 1 MB JSON document per `(user, app)`.
- `AiPass.files`: private files for the current app, up to 10 MB/file and 50 MB total.
- `AiPass.shared`: user-owned named vaults with keyed, revisioned JSON records and private files that the user can grant to other apps as `READ`, `CONTRIBUTE`, or `READ_WRITE`.

Use private storage by default. Use a shared vault only when the product intentionally collaborates with another AI Pass app. `AiPass.shared.grant(...)` shows the user an AI Pass confirmation dialog before changing access.

Read [references/storage.md](references/storage.md) before implementing persistence or app-to-app exchange. It contains the complete method map, quotas, app-reference formats, permission semantics, concurrency pattern, and a Draft/Bupple-style handoff example.

## A.12 Result handling — always check both URL and b64_json

Different models return image responses in different shapes. **Always handle both** or your app will silently break when a model is swapped:

```javascript
function extractImageUrl(payload) {
  if (payload.url) return payload.url;
  if (payload.b64_json) return `data:image/png;base64,${payload.b64_json}`;
  throw new Error('No image in response');
}

const result = await AiPass.editImage({ /* ... */ });
const url = extractImageUrl(result.data[0]);
```

## A.13 Error handling

```javascript
try {
  const result = await AiPass.editImage({ /* ... */ });
} catch (e) {
  if (e.insufficientBalanceHandled || e.budgetExceededHandled) {
    // The SDK already opened the wallet. Preserve input and show Retry/Open wallet.
    showInlineMessage('Add AI Pass credit, then try again.');
    openWalletButton.onclick = () => AiPass.openWallet();
    return;
  }
  if (e?.code === 'AUTH_REQUIRED') return; // user dismissed the SDK login modal
  if (/model.*not found/i.test(e.message)) {
    // Refresh the metadata-filtered catalog before selecting another stable ID.
    console.error('Model not available; refresh with getModelCatalog()');
  }
  alert('Something went wrong: ' + e.message);
}
```

## A.14 Worked example — full hair-style try-on app

Drop this in a `.html` file, replace `client_id`, open in a browser. Fully functional ~150-line app: discovers models, accepts a selfie, applies a chosen hair style via image-edit, renders the result.

```html
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Hair Studio — AI Pass demo</title>
  <link rel="stylesheet" href="https://aipass.one/aipass-ui.css">
  <style>
    body { font-family: system-ui; max-width: 900px; margin: 2rem auto; padding: 0 1rem; }
    .row { display: flex; gap: 1rem; flex-wrap: wrap; align-items: flex-start; }
    .col { flex: 1; min-width: 280px; }
    .styles { display: grid; grid-template-columns: repeat(3, 1fr); gap: .5rem; margin-top: 1rem; }
    .style { padding: .75rem; border: 2px solid #ddd; border-radius: 8px; cursor: pointer; text-align: center; font-size: .9rem; }
    .style.selected { border-color: #6366f1; background: #eef2ff; }
    button { padding: .75rem 1.5rem; background: #6366f1; color: white; border: none; border-radius: 8px; cursor: pointer; font-size: 1rem; }
    button:disabled { opacity: .5; cursor: not-allowed; }
    img { max-width: 100%; border-radius: 8px; }
    #status { color: #666; font-size: .9rem; margin-top: .5rem; }
  </style>
</head>
<body>
  <header style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1rem">
    <h1>💇 Hair Studio</h1>
    <div data-aipass-button></div>
  </header>

  <div class="row">
    <div class="col">
      <h3>1. Upload your photo</h3>
      <input id="photo" type="file" accept="image/*">
      <img id="preview" style="margin-top:.5rem;display:none">

      <h3>2. Pick a style</h3>
      <div class="styles" id="styles"></div>

      <button id="go" disabled style="margin-top:1rem">Try this style</button>
      <div id="status"></div>
    </div>

    <div class="col">
      <h3>Result</h3>
      <img id="result" style="display:none">
    </div>
  </div>

  <script src="https://aipass.one/aipass-sdk.js"></script>
  <script>
    // ─── 1. Configure ──────────────────────────────────────────────────────
    AiPass.initialize({
      clientId: 'YOUR_CLIENT_ID_HERE',   // ← replace
      requireLogin: false
    });

    const STYLES = [
      'sleek bob cut', 'long flowing waves', 'short buzz cut',
      'curly afro', 'straight bangs', 'high ponytail',
      'man bun', 'pixie cut', 'mullet',
      'mohawk', 'dreadlocks', 'shoulder-length wavy'
    ];

    let editModel = null;
    let selectedStyle = null;

    // ─── 2. Render style gallery ──────────────────────────────────────────
    const stylesEl = document.getElementById('styles');
    STYLES.forEach((style, i) => {
      const div = document.createElement('div');
      div.className = 'style';
      div.textContent = style;
      div.onclick = () => {
        document.querySelectorAll('.style').forEach(s => s.classList.remove('selected'));
        div.classList.add('selected');
        selectedStyle = style;
        updateButton();
      };
      stylesEl.appendChild(div);
    });

    // ─── 3. Photo preview ─────────────────────────────────────────────────
    const photoInput = document.getElementById('photo');
    const previewImg = document.getElementById('preview');
    photoInput.onchange = () => {
      if (!photoInput.files[0]) return;
      previewImg.src = URL.createObjectURL(photoInput.files[0]);
      previewImg.style.display = 'block';
      updateButton();
    };

    function updateButton() {
      document.getElementById('go').disabled =
        !photoInput.files[0] || !selectedStyle || !editModel;
    }

    // ─── 4. Discover the right model (catalog discovery is public) ──────
    async function discoverModel() {
      const { data } = await AiPass.getModelCatalog({ type: 'image', method: 'image_edit' });
      editModel = pickModel(data, 'face-preserving-edit');
      document.getElementById('status').textContent = editModel
        ? `Ready: using ${editModel}`
        : 'No image-edit model is available in your account.';
      updateButton();
    }

    discoverModel();

    // ─── 5. Run the edit ──────────────────────────────────────────────────
    document.getElementById('go').onclick = async () => {
      const status = document.getElementById('status');
      const goBtn = document.getElementById('go');
      goBtn.disabled = true;
      status.textContent = 'Generating…';

      try {
        const result = await AiPass.editImage({
          image: photoInput.files[0],
          prompt: `Change the hairstyle to ${selectedStyle}. Preserve the face, lighting, skin tone, and clothing exactly. Keep all other features identical.`,
          model: editModel,
          n: 1,
          size: '1024x1024',
          responseFormat: 'url'
        });

        const payload = result.data[0];
        const url = payload.url || `data:image/png;base64,${payload.b64_json}`;

        const resultImg = document.getElementById('result');
        resultImg.src = url;
        resultImg.style.display = 'block';
        status.textContent = '✅ Done';
      } catch (e) {
        if (e?.code === 'AUTH_REQUIRED') { status.textContent = ''; return; }
        if (e.insufficientBalanceHandled || e.budgetExceededHandled) {
          status.textContent = 'Add AI Pass credit, then try this style again.';
          return;
        }
        status.textContent = '❌ ' + (e.message || 'Edit failed');
      } finally {
        goBtn.disabled = false;
      }
    };
  </script>
</body>
</html>
```

**This is a complete app.** Drop in a `client_id`, open in a browser, sign in, upload a selfie, pick a style, get a result. Adapt the prompt and gallery for any "swap an attribute on a photo" use case (fashion, makeup, eye color, age, room redecoration, etc.).

---

# Path B — Raw REST (mobile, CLI, server)

For native mobile apps, server-side calls, or anywhere you can't load the browser SDK. You implement PKCE yourself.

The canonical resource base is `https://aipass.one/v1` for both OAuth access tokens and API keys. The legacy `/oauth2/v1` and `/apikey/v1` resource paths remain supported as compatibility aliases, each with its previous credential contract. OAuth protocol endpoints such as `/oauth2/authorize`, `/oauth2/token`, and `/oauth2/userinfo` do not move.

For raw OAuth resource calls, also send `X-AIPass-OAuth-Client-Id: YOUR_CLIENT_ID` when practical. This binds the access token to the expected OAuth client; it is not an authentication-type selector.

## B.1 Auth flow (5 steps)

```
1. Generate PKCE pair                      [your code]
2. Send user to /oauth2/authorize          [browser]
3. User signs in + clicks Authorize        [browser]
4. AI Pass redirects back with ?code=...   [browser → your callback]
5. Exchange code for tokens                [your code]
   → got access_token + refresh_token
6. Call /v1/* with Bearer header           [your code]
```

CORS is open on `/oauth2/token`, so browser-only apps can exchange codes without a backend.

## B.2 Step 1 — Generate PKCE + state (per login)

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

## B.3 Step 2 — Send user to authorize

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

## B.4 Step 3 — Exchange code for access token

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

## B.5 Step 4 — 🎯 Make your first API call

**This is the step most newcomers get wrong.** The token goes in the `Authorization` header, NOT in the URL.

```bash
# ✅ CORRECT
curl -X POST https://aipass.one/v1/chat/completions \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-5-mini",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

```python
import requests
r = requests.post(
    "https://aipass.one/v1/chat/completions",
    headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
    json={"model": "gpt-5-mini", "messages": [{"role": "user", "content": "Hello!"}]},
)
print(r.json()["choices"][0]["message"]["content"])
```

## B.6 Step 5 — Refresh tokens (when you get a 401)

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

## B.7 Discover models at runtime

Same rule as Path A: discover the catalog and filter by metadata instead of provider-name patterns:

```bash
curl "https://aipass.one/v1/models?type=image&method=image_edit" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  | jq -r '.data[].id'
# Returns the available stable public image-edit IDs.
```

The default response is the OpenAI-compatible envelope. Use `?detailed=false` only when an older client explicitly needs the historical string array. See the [filter table in Path A.3](#a3-discover-models-at-runtime) for more catalog filters.

## B.8 Image generation (REST)

```bash
curl -X POST https://aipass.one/v1/images/generations \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "imagen-4-ultra",
    "prompt": "A futuristic city at sunset",
    "size": "1024x1024",
    "n": 1,
    "response_format": "url"
  }'

# Response: { "data": [ { "url": "https://..." } ] }
# Always check both `url` and `b64_json` — different models return different shapes.
```

## B.9 Image editing (REST) — single image

```bash
curl -X POST https://aipass.one/v1/images/edits \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -F "image=@selfie.jpg" \
  -F "prompt=Change the hairstyle to a sleek bob cut. Preserve the face and lighting." \
  -F "model=nano-banana-2-edit" \
  -F "size=1024x1024" \
  -F "response_format=url"
```

```python
import requests
with open("selfie.jpg", "rb") as f:
    r = requests.post(
        "https://aipass.one/v1/images/edits",
        headers={"Authorization": f"Bearer {access_token}"},
        files={"image": f},
        data={
            "model": "nano-banana-2-edit",
            "prompt": "Change the hairstyle to a sleek bob cut. Preserve the face and lighting.",
            "size": "1024x1024",
            "response_format": "url",
        },
    )
url = r.json()["data"][0].get("url") or f"data:image/png;base64,{r.json()['data'][0]['b64_json']}"
```

## B.10 Image editing (REST) — multi-image

Pass multiple `-F image=@…` for models that support multi-image input (`nano-banana-2-edit`, `gpt-image-2-edit`, `nano-banana-pro-edit`):

```bash
curl -X POST https://aipass.one/v1/images/edits \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -F "image=@target.jpg" \
  -F "image=@reference.jpg" \
  -F "prompt=Apply the hairstyle from the second image to the person in the first." \
  -F "model=nano-banana-2-edit"
```

The server treats repeated `image` form fields as an array.

## B.11 Vision (multimodal chat)

Same `/v1/chat/completions` endpoint, but `content` is an array:

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

## B.12 Streaming chat

Set `"stream": true` in the chat completions body. Response is Server-Sent Events:

```
data: {"choices":[{"delta":{"content":"Hello"}}]}
data: {"choices":[{"delta":{"content":" world"}}]}
data: [DONE]
```

```javascript
const r = await fetch("https://aipass.one/v1/chat/completions", {
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

## B.13 Audio + embeddings (REST)

```bash
# TTS
curl -X POST https://aipass.one/v1/audio/speech \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"model":"tts-1","input":"Hello world","voice":"nova","response_format":"mp3"}' \
  --output speech.mp3

# Transcribe
curl -X POST https://aipass.one/v1/audio/transcriptions \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -F "file=@audio.mp3" \
  -F "model=whisper-1" \
  -F "language=en"

# Embeddings
curl -X POST https://aipass.one/v1/embeddings \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"model":"text-embedding-3-small","input":["First text","Second text"]}'
```

## B.14 Usage & balance tracking

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

Raw REST clients must handle HTTP 402 themselves. Preserve pending input, show an add-credit route, and retry only after the user asks. The automatic account-wallet modal and `AiPass.openWallet()` belong to the browser SDK path.

## B.15 Revoke

When a user logs out, revoke the token:

```bash
curl -X POST "https://aipass.one/oauth2/revoke?token=$ACCESS_TOKEN" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

---

# Common mistakes (don't do these)

These are real mistakes real builders have made — listed so you can avoid them:

```bash
# Wrong: selecting by an assumed provider prefix or name suffix.
# Query /v1/models with type/capability/method filters instead.
# Use a stable public ID only after it appears in data[].id.
{ "model": "nano-banana-2-edit" }

# ❌ Token in the URL path (NOT how Bearer auth works)
curl -X POST https://aipass.one/oauth2/$ACCESS_TOKEN
curl https://aipass.one/v1/chat/completions/$ACCESS_TOKEN

# ✅ Use the shared canonical resource path with an OAuth access token.
# The server identifies the credential from the Bearer token. The two older
# resource prefixes remain credential-specific aliases, but new code should use /v1/*.
curl -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "X-AIPass-OAuth-Client-Id: $CLIENT_ID" \
  https://aipass.one/v1/chat/completions

# ❌ Only handling `url` in image responses, ignoring `b64_json`
#    Different models return different shapes. ALWAYS handle both:
const url = payload.url || `data:image/png;base64,${payload.b64_json}`;

# ❌ Assuming editImage only takes a single file
#    It accepts an ARRAY for multi-image-capable models.
AiPass.editImage({ image: [file1, file2], ... })   // works on supported models such as nano-banana-2-edit

# ❌ Using a placeholder/dummy code_challenge
# The /oauth2/token call will succeed, but PKCE is not actually verifying anything.
# The challenge MUST be SHA256(code_verifier) base64url-encoded.

# ❌ Forgetting to validate `state` on the redirect
# An attacker can fixate auth codes if you skip this. Always check state.

# ❌ Storing tokens in localStorage on the same origin as your auth UI
# XSS = full account takeover. Use httpOnly cookies (server-side) or
# encrypted secure storage (mobile keychain).
# (The browser SDK handles this for you — only worry about it on REST path.)

# ❌ Refusing to call a protected method while signed out
#    This prevents the SDK from showing its automatic login modal. Call the
#    generation/storage method from the user's action and handle AUTH_REQUIRED
#    only when the user dismisses the modal.

# ❌ Building a second budget modal or treating HTTP 402 as a generic failure
#    The browser SDK opens its account wallet automatically. Preserve the user's
#    work, handle insufficientBalanceHandled, and use AiPass.openWallet() only
#    for an explicit recovery button after dismissal.
```

---

# All allowed endpoints

All require `Authorization: Bearer ACCESS_TOKEN` and `api:access` scope. Base URL: `https://aipass.one/v1`

| Category | Endpoint | Notes |
|---|---|---|
| Models | `GET /models` | List all available models — use this to pick |
| Models | `GET /models/{id}` | Single model info |
| Chat | `POST /chat/completions` | Chat + multimodal (vision) — see Path A.5 / B.11 |
| Embeddings | `POST /embeddings` | Vector embeddings |
| Images | `POST /images/generations` | Text-to-image |
| Images | `POST /images/edits` | Image editing — accepts single OR multiple `image` fields |
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

`AiPass.data`, `AiPass.files`, and `AiPass.shared` are authenticated SDK storage namespaces, not
model-proxy `/v1/*` methods. Use the SDK surface documented in
[references/storage.md](references/storage.md) so app namespaces and user-approved grants are
resolved correctly.

---

# Help

- Stuck? Join Discord: https://discord.gg/hENftFRMMD
- Full human docs: https://aipass.one/docs/rest/integration
- SDK reference: https://aipass.one/docs/sdk/reference
- Dashboard: https://aipass.one/panel/developer

Developers earn **50% commission** on every API call their users make through your app.
