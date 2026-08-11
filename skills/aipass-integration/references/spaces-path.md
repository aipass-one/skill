# AI Pass Spaces fallback

AI Pass Spaces is an optional hosted-app path for a self-contained HTML result. It is not required to integrate AI Pass, and an existing application should remain on its current host unless the user asks to move it.

Read the canonical standalone manual for the Space app format and publication calls:

https://aipass.one/skills/aipass-spaces/SKILL.md

The standard integration grant already contains the displayed Space scopes and one project app slug. If it is still usable, reuse it with the standalone manual's REST calls; never start a second device request. If no grant exists yet, the manual creates the same one-month project-bound authorization. Never ask for a generic API key, password, browser cookie, session token, device code, or setup grant. Never call the human approval endpoint on the user's behalf.

Do not ask the user to look up or paste their Space handle. The signed-in approval page resolves an existing Space automatically. A new user may approve first and claim a Space later; the first preflight then binds the Space owned by that same account without another authorization.

For a new browser prototype, the SDK on localhost is usually the fastest proof. Choose Spaces only when the user requests it or wants a hosted result and the project has no practical deployment path.

Published Space apps can use `AiPass.data` and `AiPass.files` for private per-user state. Use
`AiPass.shared` only for an intentional same-user workflow with another exact OAuth, catalog, or
Space app, and let the SDK display its grant confirmation. Follow [sdk-storage.md](sdk-storage.md)
for permissions, quotas, and verification.
