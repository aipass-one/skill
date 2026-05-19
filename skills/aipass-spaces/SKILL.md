---
name: aipass-spaces
description: Publish self-contained HTML apps to the user's AI Pass Space at aipass.one/spaces/<handle>. Activate when the user asks to "publish an app", "make me an app on AI Pass", "drop this on my space", or hands you an API key together with a handle. You write one HTML file and POST it; AI Pass hosts it, gives it a URL, and the in-app AI Pass SDK handles visitor auth + billing for any AI features inside it.
version: 1.1.0
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
    AiPass.initialize({ clientId: 'PLACEHOLDER_CLIENT_ID', requireLogin: true });

    // Helpers — DO NOT skip these. They prevent two bugs every shipped Spaces app has hit.
    function normalizeModels(raw) {
      const arr = Array.isArray(raw) ? raw : (raw && Array.isArray(raw.data) ? raw.data : []);
      return arr.map(m => (typeof m === 'string' ? m : (m && m.id) || '')).filter(Boolean);
    }

    let editModel = null;   // discovered at runtime
    async function discoverModels() {
      if (!AiPass.isAuthenticated()) return;
      const ids = normalizeModels(await AiPass.getModels());
      // Prefer Fal-routed face-preserving edit models; never hardcode literal IDs.
      const falEdit = (s) => ids.find(id => id.startsWith('fal_ai/') && id.endsWith('/edit') && id.includes(s));
      editModel = falEdit('nano-banana-2') || falEdit('gpt-image-2') || falEdit('nano-banana');
      // Now enable UI that depends on the model.
    }

    function syncAuthUi() {
      const isAuth = AiPass.isAuthenticated();
      // toggle every auth-gated piece of UI; call discoverModels() once signed in
      if (isAuth) discoverModels();
    }

    // Run once for restored sessions, then poll briefly for async OAuth-callback exchange.
    syncAuthUi();
    let _polls = 0;
    const _tick = setInterval(() => {
      syncAuthUi();
      if (++_polls > 25 || AiPass.isAuthenticated()) clearInterval(_tick);
    }, 200);
    document.addEventListener('aipass:login',  syncAuthUi);
    document.addEventListener('aipass:logout', () => { editModel = null; });
    document.addEventListener('aipass:error',  (e) => console.error(e.detail.error));
  </script>
</body>
</html>
```

**Don't substitute `PLACEHOLDER_CLIENT_ID` yourself.** Leave the literal string — the server replaces it with the space's shared OAuth client id at publish time. (One client per space means a visitor authorizes once and every app in the space works for them.)

### Two bugs every Spaces app ships with if you skip the helpers above

**Bug 1 — `aipass:login` event ≠ "is signed in".** It fires only on the actual click. It does NOT re-fire when the visitor comes back with a valid stored session. If you wrap your "enable features" code inside `addEventListener('aipass:login', …)` and nothing else, every returning user sees your app permanently disabled. Use `AiPass.isAuthenticated()` as the source of truth + sync on init.

**Bug 2 — Hardcoded model IDs return `400 Invalid model name`.** The proxy serves edit models as `fal_ai/fal-ai/nano-banana-2/edit` (note the double `fal_ai/` prefix), not `fal-ai/nano-banana-2/edit`. Names also shift between proxy versions. Always discover via `normalizeModels(await AiPass.getModels())` and pattern-match (e.g. `id.endsWith('/edit')`). Prefer **Fal-routed** IDs (`fal_ai/…`) — they're the canonical billing path and the only ones that support multi-image input.

### Calling AI from inside a published app

In the browser, **do NOT use `$AIPASS_API_KEY`** — that key is the developer's, not the visitor's. Use the AI Pass JavaScript SDK, which transparently bills the *visitor's* wallet via OAuth:

```javascript
// Use the helpers from the boilerplate section above.
let chatModel = null;

async function readyChat() {
  if (!AiPass.isAuthenticated()) return;
  const ids = normalizeModels(await AiPass.getModels());
  chatModel = ids.find(id => id === 'gpt-5-mini')
           || ids.find(id => id.startsWith('gpt-'))
           || ids.find(id => id.startsWith('claude-'));
}

// Run on init AND on login transition (the auth pattern from the boilerplate).
readyChat();
document.addEventListener('aipass:login', readyChat);

// Later, in your button handler:
async function ask(prompt) {
  if (!chatModel) return;
  const r = await AiPass.generateCompletion({
    messages: [{ role: 'user', content: prompt }],
    model: chatModel,
  });
  return r.choices[0].message.content;
}
```

The SDK ships `generateCompletion`, `generateImage`, `editImage`, `generateSpeech`, `transcribeAudio`, `generateEmbeddings`, and `generateVideo`. Full reference and recipe library: load `aipass-oauth-app` and read its Path A section.

---

## Rules — don't break these or the published app won't work

1. **Keep `PLACEHOLDER_CLIENT_ID` literal** in the HTML you POST. Server substitutes it.
2. **Keep `requireLogin: true`** in `AiPass.initialize`. Otherwise the visitor can't be billed and AI calls 401.
3. **Keep `<div data-aipass-button></div>`** somewhere visible (header is conventional). The SDK mounts the auth/balance widget into it. No button = no login UI.
4. **Don't write a custom login flow.** The SDK provides the overlay; rolling your own breaks billing.
5. **Don't include `$AIPASS_API_KEY` in the HTML.** That's *your* (the agent's) auth for publishing, not the app's runtime auth. Apps authenticate visitors via the SDK + OAuth.
6. **Single-file output.** No external JS/CSS files of your own — inline everything. CDN scripts (Tailwind, Chart.js, etc.) are fine.
7. **Sanitize model output before `innerHTML`.** Use DOMPurify when rendering markdown or any AI-generated HTML.
8. **Discover models at runtime — never hardcode IDs.** The proxy serves edit models as `fal_ai/fal-ai/nano-banana-2/edit` (note the prefix); strings like `fal-ai/nano-banana-2/edit` return `400 Invalid model name`. Normalize with the helper above, filter by pattern (`id.endsWith('/edit')`), and prefer `fal_ai/`-prefixed IDs. See `aipass-oauth-app` §A.3 for the full filter table.
9. **Use `AiPass.isAuthenticated()` as the source of truth, not the `aipass:login` event.** That event only fires on the actual click; it does NOT re-fire when a returning visitor's session is restored from storage. Apps that gate features inside `addEventListener('aipass:login', …)` are broken for every returning user. Sync on init + poll briefly + re-sync on transition events (boilerplate pattern above).

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
    AiPass.initialize({ clientId: 'PLACEHOLDER_CLIENT_ID', requireLogin: true });

    function normalizeModels(raw) {
      const arr = Array.isArray(raw) ? raw : (raw && Array.isArray(raw.data) ? raw.data : []);
      return arr.map(m => (typeof m === 'string' ? m : (m && m.id) || '')).filter(Boolean);
    }
    let chatModel = null;
    async function readyChat() {
      if (!AiPass.isAuthenticated()) return;
      const ids = normalizeModels(await AiPass.getModels());
      chatModel = ids.find(id => id === 'gpt-5-mini') || ids.find(id => id.startsWith('gpt-'));
    }
    readyChat();
    let _p = 0;
    const _i = setInterval(() => { readyChat(); if (++_p > 25 || chatModel) clearInterval(_i); }, 200);
    document.addEventListener('aipass:login', readyChat);

    document.getElementById('go').onclick = async () => {
      const mood = document.getElementById('mood').value.trim();
      if (!mood || !chatModel) return;
      const out = document.getElementById('out');
      out.innerHTML = 'Thinking…';
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
