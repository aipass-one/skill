# AI Pass Spaces fallback

AI Pass Spaces is an optional hosted-app path for a self-contained HTML result. It is not required to integrate AI Pass, and an existing application should remain on its current host unless the user asks to move it.

Do not reuse the integration setup grant for publishing. Fetch and follow the canonical standalone manual:

https://aipass.one/skills/aipass-spaces/SKILL.md

That manual uses browser-approved device authorization with a short-lived grant bound to the exact user, Space, slug, project, and HTML hash. Never ask for a generic API key, password, browser cookie, session token, device code, or setup grant. Never call the human approval endpoint on the user's behalf.

For a new browser prototype, the SDK on localhost is usually the fastest proof. Choose Spaces only when the user requests it or wants a hosted result and the project has no practical deployment path.

Published Space apps can use `AiPass.data` and `AiPass.files` for private per-user state. Use
`AiPass.shared` only for an intentional same-user workflow with another exact OAuth, catalog, or
Space app, and let the SDK display its grant confirmation. Follow [sdk-storage.md](sdk-storage.md)
for permissions, quotas, and verification.
