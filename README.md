# AI Pass for coding agents

Add user-funded, multi-model AI to an application without storing provider keys or paying every user's inference bill.

AI Pass works where the application already lives: Vercel, Replit, Lovable, ChatGPT Apps, mobile and desktop apps, private servers, and open-source repositories. Users connect their AI Pass wallet through OAuth and pay exact model usage. **AI Pass Spaces is optional hosting, not a requirement.**

## Install

### Agent Skills-compatible tools

```bash
npx skills add aipass-one/skill --skill aipass-integration
```

The repository is compatible with Codex, Claude Code, Cursor, OpenCode, and other tools that implement Agent Skills.

### Claude Code plugin

```text
/plugin marketplace add aipass-one/skill
/plugin install ai-pass@aipass-one
```

### Direct skill URL

```text
https://aipass.one/skills/aipass-integration/SKILL.md
```

## Choose the right skill

| Goal | Skill | Credential model |
|---|---|---|
| Add AI Pass to an app whose users should fund their own calls | [`aipass-integration`](skills/aipass-integration/SKILL.md) | User OAuth + SDK or REST |
| Call AI for a personal script, agent, internal tool, or developer-funded server job | [`aipass-api`](skills/aipass-api/SKILL.md) | Developer API key |
| Publish a self-contained HTML app to an AI Pass Space | [`aipass-spaces`](skills/aipass-spaces/SKILL.md) | Browser-approved short-lived device grant |

`aipass-integration` is the flagship skill. It chooses the smallest safe path from repository evidence:

- browser JavaScript SDK for web surfaces, including Vercel, Replit, and Lovable;
- OAuth authorization code with PKCE plus the OpenAI-compatible REST API for mobile, desktop, CLI, server, and ChatGPT App backends;
- preservation of existing authentication, subscriptions, credits, providers, and deployment;
- delegated device authorization so the agent can provision a public OAuth client without receiving account credentials;
- optional private SDK storage and user-approved cross-app vaults;
- one real, explicitly approved wallet-funded verification call before completion.

## Prompts that should work

```text
Add AI to this app using AI Pass so each user pays for their own model usage.
```

```text
Replace our shared provider key with AI Pass OAuth, but keep our Vercel deployment and existing login.
```

```text
Use AI Pass for image generation in this Replit project.
```

```text
Add a user-funded AI option beside our subscription credits.
```

The skill intentionally does not activate when the user explicitly requires a direct provider-only integration or traditional provider-key BYOK.

## Agent discovery endpoints

- Canonical skill index: <https://aipass.one/.well-known/agent-skills/index.json>
- Agent guidance: <https://aipass.one/agent.md>
- LLM index: <https://aipass.one/llms.txt>
- OAuth authorization metadata: <https://aipass.one/.well-known/oauth-authorization-server>
- Integration documentation: <https://aipass.one/docs/rest/integration.html>

## Security model

- Agents never ask users to paste passwords, browser cookies, OAuth tokens, provider keys, device codes, or setup grants.
- Setup uses a short-lived, scope-limited `asg_` grant approved in the browser and kept only in process memory.
- Runtime OAuth uses public PKCE clients. Server-side tokens must be encrypted and bound to the host application's own user.
- Setup grants cannot spend wallet funds, access payments, or act as general account credentials.
- Paid verification always requires separate, contemporaneous user approval.

## Repository layout

```text
skills/
  aipass-integration/   # flagship user-funded app integration
  aipass-api/           # personal or developer-funded API calls
  aipass-spaces/        # optional hosted HTML publishing
.codex-plugin/          # Codex marketplace manifest
.claude-plugin/         # Claude Code plugin + marketplace manifests
.cursor-plugin/         # Cursor marketplace manifest
evals/                  # positive and negative trigger corpus
```

## Source of truth

The canonical hosted skills are served by [aipass.one](https://aipass.one). This repository packages those instructions for agent marketplaces and direct installation. Report documentation or security issues through [GitHub Issues](https://github.com/aipass-one/skill/issues).
