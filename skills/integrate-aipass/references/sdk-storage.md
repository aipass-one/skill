# Browser SDK Storage and Shared Vaults

Use these namespaces only on the browser SDK path. They provide authenticated, free persistence
without adding a host database, but they do not replace the host application's authoritative
database when server-side queries, compliance controls, backups, or non-browser workers need the
data.

## Choose a surface

| Requirement | Use |
|---|---|
| Small state private to one app | `AiPass.data` |
| Files private to one app | `AiPass.files` |
| Same user's workflow across approved apps | `AiPass.shared` |

Do not move existing host data into AI Pass storage unless the user asks. Do not store secrets,
tokens, provider keys, passwords, or session material.

## Private app state

```javascript
const state = await AiPass.data.get();
state.drafts = state.drafts || [];
await AiPass.data.set(state, { ifRevision: AiPass.data.revision });

const saved = await AiPass.files.upload(file, { name: file.name });
const blob = await AiPass.files.download(saved.id);
```

`AiPass.data` is one whole JSON document per `(user, app)`, capped at 1 MB and approximately 30
writes/minute. `AiPass.files` allows 10 MB/file, 50 MB total, and 100 files per user/app. Files are
authenticated `Blob` downloads without public URLs. Both namespaces authenticate at call time and
resume after the official SDK login modal.

## User-owned shared vault

```javascript
const vault = await AiPass.shared.create('Campaign autumn');
await AiPass.shared.records.set(vault.id, 'request:hero', { prompt });

await AiPass.shared.grant(vault.id, {
  appRef: 'oauth:image-app-client-id',
  access: 'CONTRIBUTE'
});
```

`grant()` resolves the target and shows an AI Pass confirmation dialog. Do not replace it with a
custom silent grant. Only the creator app can grant/revoke access or delete the vault.

App references are:

- `oauth:{clientId}` for an external SDK app;
- `app:{slug}` for an AI Pass catalog app;
- `space:{handle}/{slug}` for a Space app.

Permissions:

- `READ`: list/read JSON and list/download files.
- `CONTRIBUTE`: read and add new keys/files; no overwrite/delete.
- `READ_WRITE`: read/add/replace/delete JSON and files.

Prefer `CONTRIBUTE` for request/result handoffs. It lets the target write a new `result:*` record
without modifying the source `request:*` record.

## Method map

```text
AiPass.shared.list()
AiPass.shared.create(name)
AiPass.shared.get(vaultId)
AiPass.shared.remove(vaultId)
AiPass.shared.resolveApp(appRef)
AiPass.shared.listGrants(vaultId)
AiPass.shared.grant(vaultId, { appRef, access })
AiPass.shared.revoke(vaultId, grantId)

AiPass.shared.records.list(vaultId)
AiPass.shared.records.get(vaultId, key)
AiPass.shared.records.set(vaultId, key, data, { ifRevision? })
AiPass.shared.records.remove(vaultId, key)

AiPass.shared.files.list(vaultId)
AiPass.shared.files.upload(vaultId, file, { name? })
AiPass.shared.files.download(vaultId, fileId)
AiPass.shared.files.getUrl(vaultId, fileId)
AiPass.shared.files.remove(vaultId, fileId)
```

Record keys are 1-128 characters using letters, numbers, `.`, `_`, `:`, and `-`. Conditional writes
reject a stale revision. Shared files remain private; put their `fileId` in a JSON record when a
collaborating app must discover them.

## Limits and invariants

- 20 vaults/user, 500 records/vault, 1 MB combined JSON/vault, and 20 grants/vault.
- 10 MB/file, 50 MB files/vault, and 100 files/vault.
- Every request is constrained to the same signed-in AI Pass user.
- A grant never exposes another user's data or the granting app's private `AiPass.data`/`files`.
- Storage does not spend AI balance.

## Verification

Test signed-out action-time login, restored login, dismissed login, and two apps signed in as the
same user. Confirm `READ` cannot write, `CONTRIBUTE` cannot overwrite/delete, revoked access fails,
another user cannot see the vault, stale revisions fail, and file object URLs are revoked after use.
