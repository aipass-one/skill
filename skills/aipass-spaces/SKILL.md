---
name: aipass-spaces
description: Publish self-contained HTML apps to a user's AI Pass Space, using the browser SDK for automatic visitor login, wallet-funded AI, private per-app JSON/files, and user-approved shared vaults between apps. Use when asked to publish or build an app on an AI Pass Space.
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

    // Load the public catalog once on page load. Discovery does not require auth,
    // so the picker is ready before the visitor commits to anything.
    const pickPreferred = (models, ids) => {
      const available = new Set(models.map(model => model.id));
      return ids.find(id => available.has(id)) || null;
    };

    let editModel = null;
    (async () => {
      const { data } = await AiPass.getModelCatalog({ type: 'image', method: 'image_edit' });
      editModel = pickPreferred(data, [
        'nano-banana-2-edit',
        'gpt-image-2-edit',
        'nano-banana-pro-edit'
      ]);
      // populate your <select>, enable any model-dependent UI
    })();

    // The SDK pops its own auth modal mid-call if needed (see Rule 9 below).
    // Request errors still throw from the method call; balance recovery also
    // emits aipass:insufficient-balance after the SDK opens the account wallet.
    document.addEventListener('aipass:error', (e) => console.error(e.detail.error));
  </script>
</body>
</html>
```

**Don't substitute `PLACEHOLDER_CLIENT_ID` yourself.** Leave the literal string — the server replaces it with the space's shared OAuth client id at publish time. (One client per space means a visitor authorizes once and every app in the space works for them.)

### Two bugs every Spaces app ships with if you skip the helpers above

**Bug 1 — In-app auth gating breaks the post-login UI.** Don't read `AiPass.isAuthenticated()` to swap button labels (e.g. "Sign in & generate"), hide the model picker, or wait on `aipass:login` to enable features. The SDK already pops its own auth modal at the moment of a protected call (`editImage`, `generateCompletion`, etc.) and resumes the call after login — building a parallel auth gate in the app HTML desyncs after login (button never re-renders → visitor has to refresh). Trust the SDK; treat your app as if every visitor were already signed in, and let the SDK insert the gate where it actually matters.

**Bug 2 - Private route aliases return `400 Invalid model name`.** Discovery exposes stable public IDs such as `nano-banana-2-edit`; provider-qualified upstream routes never belong in app code. Use `AiPass.getModelCatalog({ type: 'image', method: 'image_edit' })` and select from `data[].id`.

### Before you write a single line of HTML — read the SDK

The JS SDK is the contract for everything you build. Before you touch the boilerplate, **fetch and skim it**:

```bash
curl -sS https://aipass.one/aipass-sdk.js -o /tmp/aipass-sdk.js
# Then grep for the methods you'll call:
grep -n -E "async (generateCompletion|generateImage|editImage|generateSpeech|transcribeAudio|getModels|getModelCatalog)" /tmp/aipass-sdk.js
grep -n -E "AiPass\.(data|files|shared)|_createSharedNamespace" /tmp/aipass-sdk.js
grep -n "_ensureAuthenticated" /tmp/aipass-sdk.js  # see exactly which calls gate auth
```

What you'll find that matters:

- **Auth-gated methods auto-prompt the modal.** Every generation method (`editImage`, `generateImage`, `generateCompletion`, `generateSpeech`, `transcribeAudio`, `generateImageVariations`, `generateVideo`) starts with `await _ensureAuthenticated()`. If the visitor isn't signed in, the SDK opens its dismissible auth-gate modal, *awaits* the OAuth round-trip, then continues the original call. Your `await AiPass.editImage(...)` resolves with the actual result; no re-click required. Dismissed modals throw `AuthRequiredError` (`error.code === 'AUTH_REQUIRED'`) — swallow silently in your `catch`.
- **Insufficient balance auto-prompts the wallet.** HTTP 402 and standard insufficient-balance responses open the SDK account/balance window automatically. The thrown error has `code === 'INSUFFICIENT_BALANCE'` and `insufficientBalanceHandled === true` (plus `budgetExceededHandled` for compatibility). Preserve the visitor's work, show a retry action, and use `AiPass.openWallet()` only for an explicit “Open wallet” recovery button after dismissal.
- **`getModels()`, `getModelCatalog()`, and `getModel()` are public.** No auth, no balance hit. `getModels()` returns stable ID strings; `getModelCatalog()` returns the metadata envelope for filtered pickers.
- **The `<div data-aipass-button>` widget** is the canonical login affordance. The SDK mounts the sign-in button + balance + dropdown menu into it and keeps it in sync with auth state. Put one in your header and you don't need any other login UI — no in-app "Sign in" button, no syncAuth poll.

Then list the available models against your app's needs:

```bash
# Use any AI Pass API key — same catalog is served back.
curl -sS https://aipass.one/v1/models -H "Authorization: Bearer $AIPASS_API_KEY" \
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
  const ids = await AiPass.getModels();
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
    if (e?.insufficientBalanceHandled || e?.budgetExceededHandled) {
      outEl.textContent = 'Add AI Pass credit, then try again.';
      return;
    }
    throw e;
  }
}

// Use generateCompletion ONLY when you need the full response object before
// doing anything (parsing JSON, branching on usage stats, etc.):
//   const r = await AiPass.generateCompletion({ model, messages });
//   const parsed = JSON.parse(r.choices[0].message.content);
```

The SDK ships `generateCompletion`, `generateImage`, `editImage`, `generateSpeech`, `transcribeAudio`, `generateEmbeddings`, and `generateVideo`, plus the `AiPass.data`, `AiPass.files`, and `AiPass.shared` storage namespaces. Protected calls authenticate at the API surface — see the "Before you write a single line of HTML — read the SDK" section above. Full reference and recipe library: load `aipass-oauth-app` and read its Path A section.

### Per-user data storage (AiPass.data)

Every published app gets **one JSON document per signed-in visitor** — server-side storage with identity, no backend needed. Use it for anything the app should remember across visits: settings, history, favorites, scores, journal entries. Whole-document semantics: load once, mutate in memory, write the whole object back.

```javascript
// Load — returns {} on the visitor's first ever use of this app.
let store = await AiPass.data.get();

store.history = store.history || [];
store.history.push({ prompt, at: Date.now() });

// Whole-document write (last-write-wins).
await AiPass.data.set(store);
```

The contract:

- **Auth-gates at call time, like generation methods.** `get()`/`set()` run `_ensureAuthenticated()` — a signed-out visitor gets the SDK auth modal and your `await` resumes after login. Works exactly right with `requireLogin: false`; do NOT wrap data calls in `isAuthenticated()` checks (rule 9 applies). Dismissed modal throws `AuthRequiredError` (`error.code === 'AUTH_REQUIRED'`) — swallow it in your `catch`.
- **Scope is automatic:** (signed-in visitor, this app), derived from the `/spaces/{handle}/{slug}` page URL. One app cannot read another space's data.
- **Limits:** 1 MB per document, ~30 writes/minute per visitor. **Free** — data calls never spend the visitor's wallet. Save on explicit user action or debounce; never per keystroke.
- **Namespaced API only.** `AiPass.data.get()` / `AiPass.data.set(obj)`. There is no `AiPass.getData()`, `AiPass.saveData()`, or `AiPass.data(...)` — those are hallucinations and will throw.
- **Optional optimistic concurrency:** `AiPass.data.set(obj, { ifRevision: AiPass.data.revision })` rejects with a revision-conflict error if another tab wrote in between; reload with `get()` and retry. Omit `ifRevision` for last-write-wins (the right default for almost every app).

### Private per-user files (`AiPass.files`)

Keep binary data out of the JSON document:

```javascript
const saved = await AiPass.files.upload(file, { name: 'reference-photo.jpg' });
const files = await AiPass.files.list();
const blob = await AiPass.files.download(saved.id);
const url = await AiPass.files.getUrl(saved.id); // revoke with URL.revokeObjectURL(url)
await AiPass.files.remove(saved.id);
```

Files are scoped automatically to `(signed-in visitor, this Space app)`, are private authenticated
downloads, and never receive public URLs. Limits are 10 MB/file, 50 MB total, and 100 files per
visitor/app. Executable web formats are rejected. Storage is free.

### Shared databases and files across apps (`AiPass.shared`)

Use shared vaults only for intentional app-to-app workflows. A vault belongs to the signed-in user
and contains keyed, revisioned JSON records plus private files. The creator app grants an exact app
reference; the SDK shows a contextual AI Pass confirmation before the grant is written.

```javascript
const project = await AiPass.shared.create('Campaign autumn');
await AiPass.shared.records.set(project.id, 'request:hero', { prompt });

await AiPass.shared.grant(project.id, {
  appRef: 'space:designer/image-maker',
  access: 'CONTRIBUTE'
});

// The granted app, signed in as the same user:
const projects = await AiPass.shared.list();
const request = await AiPass.shared.records.get(project.id, 'request:hero');
const image = await AiPass.shared.files.upload(project.id, generatedBlob, { name: 'hero.png' });
await AiPass.shared.records.set(project.id, 'result:hero', { fileId: image.id });
```

- `READ`: list/read records and list/download files.
- `CONTRIBUTE`: read and add new record keys/files, without overwrite or delete.
- `READ_WRITE`: read, add, replace, and delete records/files.
- App references: `oauth:{clientId}`, `app:{catalog-slug}`, or `space:{handle}/{slug}`.
- Only the creator app can grant/revoke access or delete the vault. Every request remains constrained
  to the same signed-in user.
- Limits: 20 vaults/user, 500 records and 1 MB JSON/vault, 20 grants/vault, 10 MB/file, 50 MB files,
  and 100 files/vault.

Management methods are `list`, `create`, `get`, `remove`, `resolveApp`, `listGrants`, `grant`, and
`revoke`. Record methods are `records.list/get/set/remove`; file methods are
`files.list/upload/download/getUrl/remove`. Prefer private `AiPass.data`/`AiPass.files` unless
cross-app access is a real product feature.

---

## Rules — don't break these or the published app won't work

1. **Keep `PLACEHOLDER_CLIENT_ID` literal** in the HTML you POST. Server substitutes it.
2. **Use `requireLogin: false`** in `AiPass.initialize`. The flag controls whether a forced login modal pops on page load — `true` tanks engagement because visitors get gated before they've seen the app. With `false`, the SDK still gates protected calls (`editImage`, `generateCompletion`, etc.) by showing its auth modal *at the moment of the call*, then awaiting the OAuth round-trip and continuing the call automatically. You do not need to call `AiPass.login()` yourself.
3. **Keep `<div data-aipass-button></div>`** somewhere visible (header is conventional) AND **render it in the actual DOM**. The SDK calls `document.querySelectorAll('[data-aipass-button]')` after init and mounts the widget into matched elements. For single-file HTML this is automatic. **For React/Vue/Svelte/Vite-bundled apps** the slot has to be in your JSX/template — putting the string `data-aipass-button` in a comment, in unrendered code, or only inside compiled JS does NOT count. A common failure mode: the agent writes a React PWA, the literal string `data-aipass-button` appears in the bundle (from the skill's boilerplate copied as a comment), but no element is actually rendered, so the widget never mounts and visitors see no login UI. Verify with `document.querySelectorAll('[data-aipass-button]').length > 0` in the live DOM. No mounted element = no login UI.
4. **Don't write a custom login flow.** The SDK provides the overlay; rolling your own breaks billing.
5. **Don't include `$AIPASS_API_KEY` in the HTML.** That's *your* (the agent's) auth for publishing, not the app's runtime auth. Apps authenticate visitors via the SDK + OAuth.
6. **Single-file output preferred.** No external JS/CSS files of your own — inline everything. CDN scripts (Tailwind, Chart.js, etc.) are fine. If you need a bundler (Vite/Webpack) for a complex app, use `vite-plugin-singlefile` to output one self-contained HTML, and double-check rule 3 — the slot must end up in the rendered output.
7. **Sanitize model output before `innerHTML`.** Use DOMPurify when rendering markdown or any AI-generated HTML.
8. **Discover models at runtime.** `AiPass.getModels()` returns stable public ID strings. Use `AiPass.getModelCatalog({ type, capability, method })` when selecting by behavior, and never copy provider-qualified route aliases into app code.
9. **Don't gate UI on auth state.** No `AiPass.isAuthenticated()` checks to swap button labels, hide the model picker, or enable features. Don't listen for `aipass:login` / `aipass:logout` to re-render. The SDK already gates protected calls at the API surface — when the visitor clicks "Generate" while signed out, the SDK pops its auth modal, waits for OAuth, then completes the call. In-app gating layered on top of this desyncs after login (buttons stay in their signed-out state until the visitor refreshes). The `<div data-aipass-button>` widget is the only login affordance the app needs.
10. **Do NOT pass `maxTokens` to `generateCompletion` / `streamText`** unless you genuinely need to truncate output. Reasoning models (`gpt-5-mini`, `gpt-5`, o-series) count internal reasoning against the cap and silently return `content: null` when it's too low. Omit the field and the model uses its native max (128K out for gpt-5-mini). The SDK no longer ships a default; passing one yourself reintroduces the bug.
11. **Stream visible chat output via `AiPass.streamText(opts, onToken)`.** It's a one-line wrapper around `generateCompletion({ stream: true })` that renders tokens as they arrive — perceived latency drops from 5–30s of "loading…" to ~50ms per token. Reserve `generateCompletion` for programmatic use only (parsing JSON, branching on usage stats). Example: `await AiPass.streamText({ model, messages }, (full) => { el.textContent = full; });`
12. **For `gpt-image-2-edit`, pass `quality: 'low'`** unless you genuinely need 'high'. It cuts generation time from ~3–5min to ~30–90s. For grainy / retro / VHS / polaroid trends it's also visually on-brand (the aesthetic IS low resolution). The SDK already client-side-shrinks oversized photos before upload.
13. **Keep persistence private by default.** Use `AiPass.data` and `AiPass.files` for ordinary app state. Use `AiPass.shared` only for explicit cross-app collaboration, choose the least-powerful grant, and let the SDK display its confirmation dialog. Never store credentials or secrets.
14. **Let the SDK own insufficient-balance recovery.** Do not build a second payment modal or preflight `getUserBalance()` before a request. The SDK opens the account wallet on 402. Keep the user's input, show a clear retry state near the failed action, and wire any later “Open wallet” button to `AiPass.openWallet()`.

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

    // getModels() is public. Load the stable ID array eagerly so the model is ready
    // before the visitor commits. The SDK will pop its auth modal at click time.
    let chatModel = null;
    (async () => {
      const ids = await AiPass.getModels();
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
        if (e?.insufficientBalanceHandled || e?.budgetExceededHandled) {
          out.textContent = 'Add AI Pass credit, then generate again.';
          return;
        }
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
