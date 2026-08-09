# AI Pass SDK Storage

Use this reference when an SDK app needs persistence. All storage methods authenticate at call
time: if the visitor is signed out, the official SDK opens its login modal, waits for OAuth, and
resumes the operation. If the visitor dismisses it, the promise rejects with
`error.code === 'AUTH_REQUIRED'`.

## Choose the narrowest surface

| Need | Namespace | Visibility |
|---|---|---|
| Preferences, drafts, chat history, small app state | `AiPass.data` | Current user + current app only |
| User uploads or generated binary output | `AiPass.files` | Current user + current app only |
| Intentional workflow between two or more apps | `AiPass.shared` | Current user + explicitly granted apps |

Keep data private unless cross-app exchange is a real product requirement. Never store passwords,
OAuth tokens, API keys, cookies, wallet credentials, or other secrets in any SDK storage surface.

## Private JSON document: `AiPass.data`

```javascript
const state = await AiPass.data.get(); // {} on first use
state.threads = state.threads || [];
state.threads.push({ id: crypto.randomUUID(), title: 'Saved chat' });

// Last-write-wins:
await AiPass.data.set(state);

// Or reject a stale write from another tab:
await AiPass.data.set(state, { ifRevision: AiPass.data.revision });
```

- One whole JSON document per `(signed-in user, OAuth client/hosted app/Space app)`.
- Maximum 1 MB/document and approximately 30 writes/minute per user/app.
- Free; reads and writes do not spend AI balance.
- Keep images, audio, video, and base64 out of JSON. Use `AiPass.files`.
- On a revision conflict, call `get()`, merge the latest document, and retry deliberately.

## Private files: `AiPass.files`

```javascript
const saved = await AiPass.files.upload(file, { name: 'reference-photo.jpg' });
const vault = await AiPass.files.list();

const blob = await AiPass.files.download(saved.id);
const objectUrl = URL.createObjectURL(blob);
preview.src = objectUrl;

const temporaryUrl = await AiPass.files.getUrl(saved.id);
preview.onload = () => URL.revokeObjectURL(temporaryUrl);
preview.src = temporaryUrl;

await AiPass.files.remove(saved.id);
```

- Maximum 10 MB/file, 50 MB total, and 100 files per user/app.
- Downloads are authenticated `Blob` responses. There are no public storage URLs.
- Revoke object URLs after use.
- Active/executable web formats such as HTML, JavaScript, and SVG are rejected.

## Shared user-owned vaults: `AiPass.shared`

A shared vault is a named database owned by the signed-in user rather than an app. It combines
keyed, revisioned JSON records with private files. An app sees only vaults granted to its exact app
namespace for the same user.

### Vault and grant methods

```javascript
const vaults = await AiPass.shared.list();
const vault = await AiPass.shared.create('Magazine issue 12');
const loaded = await AiPass.shared.get(vault.id);

const target = await AiPass.shared.resolveApp('oauth:bupple-client-id');
const grants = await AiPass.shared.listGrants(vault.id);

// Shows a contextual AI Pass confirmation dialog before the grant is written.
const grant = await AiPass.shared.grant(vault.id, {
  appRef: 'oauth:bupple-client-id',
  access: 'CONTRIBUTE'
});

await AiPass.shared.revoke(vault.id, grant.id);
await AiPass.shared.remove(vault.id);
```

Only the app that created the vault can grant/revoke access or delete it. A cancelled confirmation
throws `SharedAccessCancelledError` with `error.code === 'USER_CANCELLED'`.

App-reference formats:

- `oauth:{clientId}` for an external OAuth SDK app.
- `app:{slug}` for an AI Pass catalog app.
- `space:{handle}/{slug}` for a Space app.

Resolve a target before presenting a sharing choice so the UI can show the app's verified name.

### Permission semantics

| Access | Records | Files |
|---|---|---|
| `READ` | List/read | List/download |
| `CONTRIBUTE` | List/read/add new keys; no replace/delete | List/download/add; no delete |
| `READ_WRITE` | List/read/add/replace/delete | List/download/add/delete |

Use `CONTRIBUTE` for request/result handoffs because a collaborator cannot overwrite the source
app's existing keys. Use `READ_WRITE` only when both apps genuinely edit the same project.

### Record methods

```javascript
const records = await AiPass.shared.records.list(vault.id);
const record = await AiPass.shared.records.get(vault.id, 'article-draft');

const saved = await AiPass.shared.records.set(vault.id, 'article-draft', {
  title: 'A quiet coast',
  body: editor.value
});

await AiPass.shared.records.set(
  vault.id,
  'article-draft',
  { ...saved.data, body: editor.value },
  { ifRevision: saved.revision }
);

await AiPass.shared.records.remove(vault.id, 'article-draft');
```

Record keys are 1-128 characters and may contain letters, numbers, `.`, `_`, `:`, and `-`. Use
stable domain keys such as `draft:article`, `render:hero`, or `job:123`; do not use sequential list
positions as identities. Conditional writes reject stale revisions.

### Shared file methods

```javascript
const saved = await AiPass.shared.files.upload(vault.id, file, {
  name: 'hero-image.png'
});
const files = await AiPass.shared.files.list(vault.id);
const blob = await AiPass.shared.files.download(vault.id, saved.id);
const url = await AiPass.shared.files.getUrl(vault.id, saved.id);
await AiPass.shared.files.remove(vault.id, saved.id);
```

Shared files remain private authenticated downloads. Store a returned `fileId` in a JSON record
when another app needs to discover the file; never expect a permanent public URL.

### Draft/Bupple handoff

```javascript
// Draft owns the project and shares a narrowly-scoped contribution surface.
const project = await AiPass.shared.create('Campaign autumn');
await AiPass.shared.records.set(project.id, 'request:hero', {
  prompt: editor.value,
  status: 'ready'
});
await AiPass.shared.grant(project.id, {
  appRef: 'oauth:bupple-client-id',
  access: 'CONTRIBUTE'
});

// Bupple, signed in as the same user, discovers the granted project.
const projects = await AiPass.shared.list();
const request = await AiPass.shared.records.get(project.id, 'request:hero');
const image = await generateHero(request.data.prompt);
const stored = await AiPass.shared.files.upload(project.id, image, { name: 'hero.png' });
await AiPass.shared.records.set(project.id, 'result:hero', {
  fileId: stored.id,
  createdAt: new Date().toISOString()
});

// Draft reloads result:hero and downloads the private file through the SDK.
```

With `CONTRIBUTE`, Bupple can add `result:hero` but cannot replace `request:hero`. Generate unique
result keys when retries or multiple outputs are possible.

## Shared quotas and invariants

- 20 vaults per user.
- 500 records and 1 MB combined JSON per vault.
- 20 app grants per vault, including the creator grant.
- 10 MB/file, 50 MB of files, and 100 files per vault.
- Storage is free and does not spend AI balance.
- Every operation is constrained to the same signed-in AI Pass user.
- A grant gives an app access to that user's vault only; it never exposes another user's data.
- Keep app-private `AiPass.data` and `AiPass.files` private. Cross-app access exists only through an
  explicit shared-vault grant.
