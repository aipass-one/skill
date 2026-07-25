#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
files=(
  "$repo_root/README.md"
  "$repo_root/skills/aipass-api/SKILL.md"
  "$repo_root/skills/aipass-oauth-app/SKILL.md"
  "$repo_root/skills/aipass-spaces/SKILL.md"
  "$repo_root/skills/integrate-aipass/SKILL.md"
  "$repo_root/skills/integrate-aipass/references/oauth-contract.md"
  "$repo_root/skills/integrate-aipass/references/integration-blueprint.md"
  "$repo_root/skills/integrate-aipass/references/examples.md"
)

forbidden='(fal_ai|fal-ai|openai|gemini|imagen4|flux-pro|recraft|seedream|dreamina|standard|cerebras)/|normalizeModels\(|endsWith\([^)]*/edit|endswith\([^)]*/edit|https://aipass\.one/v1/models|GET /v1/models|/proxy/v1/models|nano-banana-2/edit|gpt-image-2/edit|nano-banana-pro/edit'

if rg -n "$forbidden" "${files[@]}"; then
  printf 'Active skills contain a private model route alias or obsolete discovery pattern.\n' >&2
  exit 1
fi

require_text() {
  local file="$1"
  local text="$2"
  if ! rg -Fq "$text" "$file"; then
    printf 'Missing required model-discovery text in %s: %s\n' "$file" "$text" >&2
    exit 1
  fi
}

require_text "$repo_root/README.md" 'the OpenAI-compatible `{ "object": "list", "data": [...] }` envelope by default'
require_text "$repo_root/skills/aipass-api/SKILL.md" '.data[].id'
require_text "$repo_root/skills/aipass-oauth-app/SKILL.md" 'AiPass.getModels()` returns a plain array of stable public ID strings'
require_text "$repo_root/skills/aipass-oauth-app/SKILL.md" 'AiPass.getModelCatalog()` returns the OpenAI-compatible'
require_text "$repo_root/skills/integrate-aipass/references/oauth-contract.md" 'The default response is the OpenAI-compatible'
require_text "$repo_root/skills/aipass-spaces/SKILL.md" "AiPass.getModelCatalog({ type: 'image', method: 'image_edit' })"

printf 'Skill model-discovery validation passed.\n'
