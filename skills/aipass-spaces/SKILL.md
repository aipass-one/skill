---
name: aipass-spaces
description: Publish self-contained HTML apps to the user's AI Pass Space at aipass.one/spaces/<handle>. Activate when the user asks to "publish an app", "make me an app on AI Pass", "drop this on my space", or hands you an API key together with a handle. You write one HTML file and POST it; AI Pass hosts it, gives it a URL, and the in-app AI Pass SDK handles visitor auth + billing for any AI features inside it.
version: 1.2.0
---

# AI Pass Spaces — App Publishing

A Space is a user's personal app workspace at `https://aipass.one/spaces/<handle>`. Each user has exactly one Space and one OAuth client that is shared by every app inside it. To publish, you write a single self-contained HTML file and POST it. The user's API key is the only credential you need.

> **Companion skills.** This skill handles only the *publishing* API. For AI calls:
> - The HTML you publish runs in visitors' browsers and uses the AI Pass JavaScript SDK with OAuth — see **`aipass-oauth-app`** for the SDK reference.
> - If you need to call AI **for the developer** while you're generating the app (e.g. you want to ask an LLM to write a section of the HTML), use **`aipass-api`** with the same `$AIPASS_API_KEY`.
> - Do not call OpenAI / Anthropic / Google / Fal SDKs directly when an AI Pass key is available. AI Pass IS those providers, billed through one wallet.

## Setup

The user provides:

- **`AIPASS_API_KEY`** — `sk-aikey-*`. Used by you to publish.
- **Space handle** — e.g. `@eiliya`. The owner of the space you're publishing into. Must already be claimed at https://aipass.one/spaces.
- **OAuth client ID** — used by the SDK *inside* the published HTML. Optional input: you can fetch it at runtime via `GET /api/v1/spaces/me`.

```bash
export AIPASS_API_KEY="sk-aikey-..."
```

Base URL for everything in this skill: `https://aipass.one`

## Quick flow

1. `GET /api/v1/spaces/me` — learn `handle` + `oauth2ClientId`. Cache for the session.
2. Write a single HTML file. Use the boilerplate below; leave `PLACEHOLDER_CLIENT_ID` literal — the server substitutes it on publish.
3. `POST /api/v1/spaces/me/apps` with the HTML.
4. Show the user the returned URL: `https://aipass.one/spaces/<handle>/<slug>`.

---

## API

All endpoints below use `Authorization: Bearer $AIPASS_API_KEY`.

### GET /api/v1/spaces/me

Caller's space info. Call once at the start of a publish session.

```bash
curl -s https://aipass.one/api/v1/spaces/me \
  -H "Authorization: Bearer $AIPASS_API_KEY"
```

Response:
```json
{
  "success": true,
  "data": {
    "handle": "eiliya",
    "displayName": "Eiliya",
    "oauth2ClientId": "client_xxxxxxxxxxxxxxxx",
    "url": "/spaces/eiliya"
  }
}
```

Errors:
- `404` — user hasn't claimed a handle yet. Tell them to visit `https://aipass.one/spaces` and pick one.

### POST /api/v1/spaces/me/apps

Publish a new app.

```bash
curl -X POST https://aipass.one/api/v1/spaces/me/apps \
  -H "Authorization: Bearer $AIPASS_API_KEY" \
  -H "Content-Type: application/json" \
  -d @app.json
```

`app.json` body:
```json
{
  "slug": "color-picker",
  "name": "AI Color Picker",
  "shortDescription": "Describe a vibe, get a palette. Save and copy hex codes with one tap.",
  "iconEmoji": "🎨",
  "htmlContent": "<!DOCTYPE html>...<!-- full document, includes PLACEHOLDER_CLIENT_ID -->...",
  "status": "PUBLISHED"
}
```

Field rules:
- `slug` — optional. Lowercase, hyphens only. Generated from `name` if omitted. Must be unique within the space.
- `name` — required, 1–200 chars.
- `shortDescription` — required, 1–300 chars. Shown on the space listing and used as `<meta name="description">`.
- `htmlContent` — required. Must be a complete document (`<html>...</html>`) AND must contain the literal string `PLACEHOLDER_CLIENT_ID` (the server replaces it with the space's OAuth client id).
- `iconEmoji` — optional, up to 16 chars (one emoji).
- `iconUrl` — optional.
- `metaTitle`, `metaDescription` — optional SEO fields. Default to `name` and `shortDescription`.
- `status` — optional. `PUBLISHED` (default, visible on the space listing), `UNLISTED` (works via direct URL only), `DRAFT`, or `ARCHIVED`.

Response `201`:
```json
{
  "success": true,
  "data": {
    "slug": "color-picker",
    "name": "AI Color Picker",
    "shortDescription": "...",
    "iconEmoji": "🎨",
    "status": "PUBLISHED",
    "oauth2ClientId": "client_xxxx",
    "viewCount": 0,
    "createdAt": "2026-05-19T..."
  }
}
```

Errors:
- `400 "Claim a space handle..."` — user hasn't claimed one yet. Direct them to `aipass.one/spaces`.
- `400 "App with slug 'X' already exists..."` — pick a different slug or use PUT to update.
- `400 "htmlContent must include the literal 'PLACEHOLDER_CLIENT_ID'..."` — see boilerplate below.

### PUT /api/v1/spaces/me/apps/{slug}

Update an existing app. All fields optional; only sent fields are applied.

```bash
curl -X PUT https://aipass.one/api/v1/spaces/me/apps/color-picker \
  -H "Authorization: Bearer $AIPASS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"htmlContent":"<!DOCTYPE html>...new version..."}'
```

Same field rules as POST. If `htmlContent` is sent, it must still contain `PLACEHOLDER_CLIENT_ID`. Status values: `PUBLISHED`, `UNLISTED`, `DRAFT`, `ARCHIVED`.

---

## Required HTML boilerplate

Every published app MUST include this scaffolding so AI Pass can mount the auth/balance widget and bill any AI calls to the visitor's wallet:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>My App — AI Pass</title>
  <meta name="description" content="One-line description shown to visitors and in search results.">
  <link rel="stylesheet" href="https://aipass.one/aipass-ui.css">
</head>
<body>
  <header style="display:flex;justify-content:space-between;padding:12px 20px">
    <a href="/">AI Pass</a>
    <div data-aipass-button></div>      <!-- Balance + login widget -->
  </header>
  <main>
    <!-- Your app UI here -->
  </main>
  <script src="https://aipass.one/aipass-sdk.js"></script>
  <script>
    AiPass.initialize({ clientId: 'PLACEHOLDER_CLIENT_ID', requireLogin: false });
    // AiPass.initialize() auto-mounts the auth/balance widget into every
    // <div data-aipass-button> on the page (SDK ≥ 2026-05-20). If you inject
    // more buttons dynamically after init, call AiPassUI.reinit().

    // Helpers — DO NOT skip these. They prevent the two bugs every Spaces app has hit.
    function normalizeModels(raw) {
      const arr = Array.isArray(raw) ? raw : (raw && Array.isArray(raw.data) ? raw.data : []);
      return arr.map(m => (typeof m === 'string' ? m : (m && m.id) || '')).filter(Boolean);
    }

    // Load the model catalog once on page load. getModels() does NOT require auth —
    // it's a public catalog endpoint. Loading it eagerly means the picker is ready
    // before the visitor commits to anything; no "Sign in to load models…" state.
    let editModel = null;
    (async () => {
      const ids = normalizeModels(await AiPass.getModels());
      const falEdit = (s) => ids.find(id => id.startsWith('fal_ai/') && id.endsWith('/edit') && id.includes(s));
      editModel = falEdit('nano-banana-2') || falEdit('gpt-image-2') || falEdit('nano-banana');
      // populate your <select>, enable any model-dependent UI
    })();

    // The SDK pops its own auth modal mid-call if needed (see Rule 9 below).
    // The only listener you need is for surfacing errors.
    document.addEventListener('aipass:error', (e) => console.error(e.detail.error));
  </script>
</body>
</html>
```

**Don't substitute `PLACEHOLDER_CLIENT_ID` yourself.** Leave the literal string — the server replaces it with the space's shared OAuth client id at publish time. (One client per space means a visitor authorizes once and every app in the space works for them.)

### Two bugs every Spaces app ships with if you skip the helpers above

**Bug 1 — In-app auth gating breaks the post-login UI.** Don't read `AiPass.isAuthenticated()` to swap button labels (e.g. "Sign in & generate"), hide the model picker, or wait on `aipass:login` to enable features. The SDK already pops its own auth modal at the moment of a protected call (`editImage`, `generateCompletion`, etc.) and resumes the call after login — building a parallel auth gate in the app HTML desyncs after login (button never re-renders → visitor has to refresh). Trust the SDK; treat your app as if every visitor were already signed in, and let the SDK insert the gate where it actually matters.

**Bug 2 — Hardcoded model IDs return `400 Invalid model name`.** The proxy serves edit models as `fal_ai/fal-ai/nano-banana-2/edit` (note the double `fal_ai/` prefix), not `fal-ai/nano-banana-2/edit`. Names also shift between proxy versions. Always discover via `normalizeModels(await AiPass.getModels())` and pattern-match (e.g. `id.endsWith('/edit')`). Prefer **Fal-routed** IDs (`fal_ai/…`) — they're the canonical billing path and the only ones that support multi-image input.

### Before you write a single line of HTML — read the SDK

The JS SDK is the contract for everything you build. Before you touch the boilerplate, **fetch and skim it**:

```bash
curl -sS https://aipass.one/aipass-sdk.js -o /tmp/aipass-sdk.js
# Then grep for the methods you'll call:
grep -n -E "async (generateCompletion|generateImage|editImage|generateSpeech|transcribeAudio|getModels)" /tmp/aipass-sdk.js
grep -n "_ensureAuthenticated" /tmp/aipass-sdk.js  # see exactly which calls gate auth
```

What you'll find that matters:

- **Auth-gated methods auto-prompt the modal.** Every generation method (`editImage`, `generateImage`, `generateCompletion`, `generateSpeech`, `transcribeAudio`, `generateImageVariations`, `generateVideo`) starts with `await _ensureAuthenticated()`. If the visitor isn't signed in, the SDK opens its dismissible auth-gate modal, *awaits* the OAuth round-trip, then continues the original call. Your `await AiPass.editImage(...)` resolves with the actual result; no re-click required. Dismissed modals throw `AuthRequiredError` (`error.code === 'AUTH_REQUIRED'`) — swallow silently in your `catch`.
- **`getModels()` and `getModel()` are public.** No auth, no balance hit. Call them on page load to build pickers; the visitor sees a real catalog before deciding to sign up.
- **The `<div data-aipass-button>` widget** is the canonical login affordance. The SDK mounts the sign-in button + balance + dropdown menu into it and keeps it in sync with auth state. Put one in your header and you don't need any other login UI — no in-app "Sign in" button, no syncAuth poll.

Then list the available models against your app's needs:

```bash
# Use any AI Pass API key — same catalog is served back.
curl -sS https://aipass.one/apikey/v1/models -H "Authorization: Bearer $AIPASS_API_KEY" \
  | jq -r '.data[].id' | sort
```

Pick the trend/use-case-appropriate default for your picker; mark it as the default in the UI (e.g. a "(native to trend)" badge). Always include 2-3 alternatives so the visitor can compare quality.

### Calling AI from inside a published app

In the browser, **do NOT use `$AIPASS_API_KEY`** — that key is the developer's, not the visitor's. Use the AI Pass JavaScript SDK, which transparently bills the *visitor's* wallet via OAuth:

```javascript
// Use the helpers from the boilerplate section above. getModels() is public,
// so chatModel is ready before the visitor signs in.
let chatModel = null;
(async () => {
  const ids = normalizeModels(await AiPass.getModels());
  chatModel = ids.find(id => id === 'gpt-5-mini')
           || ids.find(id => id.startsWith('gpt-'))
           || ids.find(id => id.startsWith('claude-'));
})();

// In your button handler — no auth check, no login prompt, no re-render dance.
// If the visitor isn't signed in, the SDK shows its auth modal first, awaits
// the OAuth round-trip, then completes the call. Your await resolves with
// the real result.
//
// For ANY visible chat output, use streamText() — tokens render as they arrive.
// Massive perceived-latency win vs waiting 5-30s for a full response.
async function ask(prompt, outEl) {
  if (!chatModel) return;
  try {
    return await AiPass.streamText(
      { model: chatModel, messages: [{ role: 'user', content: prompt }] },
      // DO NOT pass maxTokens — reasoning models eat the cap on reasoning and
      // return content:null. Omit it and the model uses its native max.
      (full /*, delta */) => { outEl.textContent = full; }
    );
  } catch (e) {
    if (e && e.code === 'AUTH_REQUIRED') return;  // visitor dismissed the auth modal
    throw e;
  }
}

// Use generateCompletion ONLY when you need the full response object before
// doing anything (parsing JSON, branching on usage stats, etc.):
//   const r = await AiPass.generateCompletion({ model, messages });
//   const parsed = JSON.parse(r.choices[0].message.content);
```

The SDK ships `generateCompletion`, `generateImage`, `editImage`, `generateSpeech`, `transcribeAudio`, `generateEmbeddings`, and `generateVideo`. All of them call `_ensureAuthenticated()` internally — see the "Before you write a single line of HTML — read the SDK" section above. Full reference and recipe library: load `aipass-oauth-app` and read its Path A section.

---

## Rules — don't break these or the published app won't work

1. **Keep `PLACEHOLDER_CLIENT_ID` literal** in the HTML you POST. Server substitutes it.
2. **Use `requireLogin: false`** in `AiPass.initialize`. The flag controls whether a forced login modal pops on page load — `true` tanks engagement because visitors get gated before they've seen the app. With `false`, the SDK still gates protected calls (`editImage`, `generateCompletion`, etc.) by showing its auth modal *at the moment of the call*, then awaiting the OAuth round-trip and continuing the call automatically. You do not need to call `AiPass.login()` yourself.
3. **Keep `<div data-aipass-button></div>`** somewhere visible (header is conventional) AND **render it in the actual DOM**. The SDK calls `document.querySelectorAll('[data-aipass-button]')` after init and mounts the widget into matched elements. For single-file HTML this is automatic. **For React/Vue/Svelte/Vite-bundled apps** the slot has to be in your JSX/template — putting the string `data-aipass-button` in a comment, in unrendered code, or only inside compiled JS does NOT count. A common failure mode: the agent writes a React PWA, the literal string `data-aipass-button` appears in the bundle (from the skill's boilerplate copied as a comment), but no element is actually rendered, so the widget never mounts and visitors see no login UI. Verify with `document.querySelectorAll('[data-aipass-button]').length > 0` in the live DOM. No mounted element = no login UI.
4. **Don't write a custom login flow.** The SDK provides the overlay; rolling your own breaks billing.
5. **Don't include `$AIPASS_API_KEY` in the HTML.** That's *your* (the agent's) auth for publishing, not the app's runtime auth. Apps authenticate visitors via the SDK + OAuth.
6. **Single-file output preferred.** No external JS/CSS files of your own — inline everything. CDN scripts (Tailwind, Chart.js, etc.) are fine. If you need a bundler (Vite/Webpack) for a complex app, use `vite-plugin-singlefile` to output one self-contained HTML, and double-check rule 3 — the slot must end up in the rendered output.
7. **Sanitize model output before `innerHTML`.** Use DOMPurify when rendering markdown or any AI-generated HTML.
8. **Discover models at runtime — never hardcode IDs.** The proxy serves edit models as `fal_ai/fal-ai/nano-banana-2/edit` (note the prefix); strings like `fal-ai/nano-banana-2/edit` return `400 Invalid model name`. Normalize with the helper above, filter by pattern (`id.endsWith('/edit')`), and prefer `fal_ai/`-prefixed IDs. See `aipass-oauth-app` §A.3 for the full filter table.
9. **Don't gate UI on auth state.** No `AiPass.isAuthenticated()` checks to swap button labels, hide the model picker, or enable features. Don't listen for `aipass:login` / `aipass:logout` to re-render. The SDK already gates protected calls at the API surface — when the visitor clicks "Generate" while signed out, the SDK pops its auth modal, waits for OAuth, then completes the call. In-app gating layered on top of this desyncs after login (buttons stay in their signed-out state until the visitor refreshes). The `<div data-aipass-button>` widget is the only login affordance the app needs.
10. **Do NOT pass `maxTokens` to `generateCompletion` / `streamText`** unless you genuinely need to truncate output. Reasoning models (`gpt-5-mini`, `gpt-5`, o-series) count internal reasoning against the cap and silently return `content: null` when it's too low. Omit the field and the model uses its native max (128K out for gpt-5-mini). The SDK no longer ships a default; passing one yourself reintroduces the bug.
11. **Stream visible chat output via `AiPass.streamText(opts, onToken)`.** It's a one-line wrapper around `generateCompletion({ stream: true })` that renders tokens as they arrive — perceived latency drops from 5–30s of "loading…" to ~50ms per token. Reserve `generateCompletion` for programmatic use only (parsing JSON, branching on usage stats). Example: `await AiPass.streamText({ model, messages }, (full) => { el.textContent = full; });`
12. **For `gpt-image-2/edit`, pass `quality: 'low'`** unless you genuinely need 'high'. It cuts generation time from ~3–5min to ~30–90s. For grainy / retro / VHS / polaroid trends it's also visually on-brand (the aesthetic IS low resolution). The SDK already client-side-shrinks oversized photos before upload.

---

## End-to-end example

```bash
# 1. Get space info
SPACE=$(curl -s https://aipass.one/api/v1/spaces/me \
  -H "Authorization: Bearer $AIPASS_API_KEY")
HANDLE=$(echo "$SPACE" | jq -r '.data.handle')
[ -z "$HANDLE" ] && { echo "Claim a handle first at https://aipass.one/spaces"; exit 1; }

# 2. Write the HTML (substitute PLACEHOLDER_CLIENT_ID NOWHERE — server does it)
cat > /tmp/app.html <<'HTML'
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Color Palette Generator — AI Pass</title>
  <meta name="description" content="Describe a mood. Get a 5-color palette with hex codes.">
  <link rel="stylesheet" href="https://aipass.one/aipass-ui.css">
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen">
  <header class="flex items-center justify-between px-5 py-3 border-b border-white/10">
    <a href="/" class="font-bold">AI Pass</a>
    <div data-aipass-button></div>
  </header>
  <main class="max-w-2xl mx-auto px-4 py-10">
    <h1 class="text-3xl font-extrabold mb-6">Color Palette Generator</h1>
    <input id="mood" class="w-full p-3 rounded bg-white/10 mb-3" placeholder="e.g. 'misty mountain dawn'">
    <button id="go" class="px-5 py-2.5 bg-indigo-600 rounded-full font-semibold">Generate</button>
    <div id="out" class="mt-8 grid grid-cols-5 gap-2"></div>
  </main>
  <script src="https://aipass.one/aipass-sdk.js"></script>
  <script>
    AiPass.initialize({ clientId: 'PLACEHOLDER_CLIENT_ID', requireLogin: false });
    // initialize() auto-mounts the auth widget into <div data-aipass-button>

    function normalizeModels(raw) {
      const arr = Array.isArray(raw) ? raw : (raw && Array.isArray(raw.data) ? raw.data : []);
      return arr.map(m => (typeof m === 'string' ? m : (m && m.id) || '')).filter(Boolean);
    }
    // getModels() is public — load the catalog eagerly so the model is ready
    // before the visitor commits. The SDK will pop its auth modal at click time.
    let chatModel = null;
    (async () => {
      const ids = normalizeModels(await AiPass.getModels());
      chatModel = ids.find(id => id === 'gpt-5-mini') || ids.find(id => id.startsWith('gpt-'));
    })();

    document.getElementById('go').onclick = async () => {
      const mood = document.getElementById('mood').value.trim();
      if (!mood || !chatModel) return;
      const out = document.getElementById('out');
      out.innerHTML = 'Thinking…';
      try {
        const r = await AiPass.generateCompletion({
          model: chatModel,
          messages: [
            { role: 'system', content: 'Return exactly 5 hex color codes for the requested mood, separated by spaces. No prose.' },
            { role: 'user', content: mood },
          ],
        });
        const hexes = r.choices[0].message.content.match(/#[0-9a-fA-F]{6}/g) || [];
        out.innerHTML = hexes.slice(0, 5).map(h =>
          `<div class="aspect-square rounded-lg flex items-end p-1 text-[10px] font-mono" style="background:${h}">${h}</div>`
        ).join('');
      } catch (e) {
        if (e && e.code === 'AUTH_REQUIRED') { out.innerHTML = ''; return; }
        out.innerHTML = `<div class="col-span-5 text-rose-300 text-sm">${e.message || 'Something went wrong'}</div>`;
      }
    };
  </script>
</body>
</html>
HTML

# 3. Publish
jq -n \
  --arg name "Color Palette Generator" \
  --arg desc "Describe a mood. Get a 5-color palette with hex codes." \
  --rawfile html /tmp/app.html \
  '{name:$name, shortDescription:$desc, iconEmoji:"🎨", htmlContent:$html}' \
  | curl -X POST https://aipass.one/api/v1/spaces/me/apps \
      -H "Authorization: Bearer $AIPASS_API_KEY" \
      -H "Content-Type: application/json" \
      -d @-

# 4. Visit https://aipass.one/spaces/$HANDLE/color-palette-generator
```

---

## When NOT to use this skill

- Calling AI from a server, script, or CLI for the developer's own use → use **`aipass-api`** instead.
- Building a standalone product where users sign in to AI Pass on YOUR domain → use **`aipass-oauth-app`** instead. Spaces apps live on `aipass.one`, not your domain.
- Publishing without a handle → not supported; the user must claim one at `aipass.one/spaces` first.
- Catalog apps (curated, in the older `/apps` directory) — different endpoint, different review flow.

---

## Help

- Dashboard / API keys: https://aipass.one/panel/developer.html
- Spaces: https://aipass.one/spaces
- Discord: https://discord.gg/hENftFRMMD
- Full docs: https://aipass.one/docs

Developers earn **50% commission** on every AI call visitors make through apps you publish to a space.
