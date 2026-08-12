#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
canonical="$repo_root/skills/aipass-integration"
mirrors=(
  "$repo_root/marketplaces/skillmd/aipass-integration"
  "$repo_root/marketplaces/killerskills/aipass-integration"
)

required=(
  SKILL.md
  agents/openai.yaml
  assets/aipass.svg
  references/aipass-spaces.md
  references/backend-oauth.md
  references/existing-auth-and-billing.md
  references/feature-opportunities.md
  references/path-decision.md
  references/remote-mcp.md
  references/sdk-path.md
  references/sdk-storage.md
  references/setup-control-plane.md
  references/spaces-path.md
  references/verification.md
)

for relative in "${required[@]}"; do
  test -f "$canonical/$relative" || {
    printf 'Missing canonical integration file: %s\n' "$relative" >&2
    exit 1
  }

  for mirror in "${mirrors[@]}"; do
    test -f "$mirror/$relative" || {
      printf 'Missing mirrored integration file: %s/%s\n' "$mirror" "$relative" >&2
      exit 1
    }
    cmp -s "$canonical/$relative" "$mirror/$relative" || {
      printf 'Integration mirror drift: %s/%s\n' "$mirror" "$relative" >&2
      exit 1
    }
  done
done

for directory in "$canonical" "${mirrors[@]}"; do
  actual_count="$(find "$directory" -type f | wc -l | tr -d ' ')"
  if [[ "$actual_count" != "${#required[@]}" ]]; then
    printf 'Unexpected integration file count in %s: expected %s, found %s\n' \
      "$directory" "${#required[@]}" "$actual_count" >&2
    exit 1
  fi
done

printf 'Integration skill mirrors are byte-identical.\n'
