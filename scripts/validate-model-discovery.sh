#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
files=(
  "$repo_root/README.md"
  "$repo_root/skills/aipass-api/SKILL.md"
  "$repo_root/skills/aipass-spaces/SKILL.md"
  "$repo_root/skills/aipass-integration/SKILL.md"
  "$repo_root/skills/aipass-integration/references/backend-oauth.md"
  "$repo_root/skills/aipass-integration/references/sdk-path.md"
)

forbidden='(fal_ai|fal-ai|openai|gemini|imagen4|flux-pro|recraft|seedream|dreamina|standard|cerebras)/|normalizeModels\(|endsWith\([^)]*/edit|endswith\([^)]*/edit|/proxy/v1/models|nano-banana-2/edit|gpt-image-2/edit|nano-banana-pro/edit'

if grep -En -- "$forbidden" "${files[@]}"; then
  printf 'Active skills contain a private model route alias or obsolete discovery pattern.\n' >&2
  exit 1
fi

require_text() {
  local file="$1"
  local text="$2"
  if ! grep -Fq -- "$text" "$file"; then
    printf 'Missing required model-discovery text in %s: %s\n' "$file" "$text" >&2
    exit 1
  fi
}

require_text "$repo_root/README.md" 'OpenAI-compatible REST API'
require_text "$repo_root/skills/aipass-api/SKILL.md" '.data[].id'
require_text "$repo_root/skills/aipass-integration/references/backend-oauth.md" 'GET https://aipass.one/v1/models'
require_text "$repo_root/skills/aipass-integration/references/sdk-path.md" 'https://aipass.one/aipass-sdk.js'
require_text "$repo_root/skills/aipass-spaces/SKILL.md" 'PLACEHOLDER_CLIENT_ID'

printf 'Skill model-discovery validation passed.\n'
