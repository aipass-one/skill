# Provision an app funding key with one approval

Use this flow when an enrolled AI Pass app uses Firebase Secret Manager. The authenticated
Google Cloud CLI account needs permission to add versions to the named secret and to create it
when it is absent. [Add a secret version](https://docs.cloud.google.com/secret-manager/docs/reference/rest/v1/projects.secrets/addVersion) · [Create a secret](https://docs.cloud.google.com/secret-manager/docs/reference/rest/v1/projects.secrets/create)

1. Confirm the existing AI Pass OAuth client ID, Firebase project ID, and backend secret name.
   Read the client ID from app configuration or the app row in AI Credit Management.
2. Run the bundled helper in a terminal session that can remain open while the owner approves.

   ```bash
   python3 scripts/setup_funding_key.py --client-id OWNED_CLIENT_ID \
     --project FIREBASE_PROJECT_ID --secret BACKEND_SECRET_NAME
   ```

   Run from this skill's directory or use the script's absolute path. Use `--account EMAIL`
   when Google Cloud CLI has multiple saved accounts. The helper prints one AI Pass approval link
   and waits up to ten minutes. Share the link with the owner and wait for their decision.

3. The owner signs in to AI Pass and reviews the displayed app, project, and secret. Approval
   lets the helper issue one app funding key and deliver it to Secret Manager. Completion
   output includes the public key ID and destination. Credential values belong in the helper
   and the secret store. New approvals can be requested when an earlier one expires unused.

For active integrations, provision a replacement, deploy the backend with the new secret
version, verify its operation, then revoke the old key in **App funding**. Use
`--retire-key-id KEY_ID` only when the owner approves retiring that exact app funding key
immediately after storage. Find the ID in **App funding**. Existing sessions from the retired
key stop immediately.

If a write or confirmation is ambiguous, inspect the Secret Manager version metadata and
the key list before issuing another key. A successful write may already exist. An unused
issued key can be revoked in **App funding**. Decline or expiry before issuance leaves the
destination untouched.

If the site's funding setup endpoint is unavailable, use **App funding** to create a key
and store it directly through the backend's secret manager. The helper does not activate
paid execution or deploy the app.
