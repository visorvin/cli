#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SPEC_URL="${SPEC_URL:-https://api.visor.vin/v1/openapi.json}"
PRESS="${PRINTING_PRESS_BIN:-printing-press}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

if ! command -v "$PRESS" >/dev/null 2>&1; then
  if [ -x "$HOME/go/bin/printing-press" ]; then
    PRESS="$HOME/go/bin/printing-press"
  else
    echo "error: printing-press not found" >&2
    exit 1
  fi
fi

curl -fsSL "$SPEC_URL" -o "$TMP/openapi.raw.json"
jq '
  .info += {"x-cli-description":"Query Visor vehicle listings, facets, VIN detail, and dealer inventory from a scriptable CLI."} |
  .components.securitySchemes.bearerAuth += {
    "x-auth-env-vars":["VISOR_API_KEY"],
    "x-auth-vars":[{"name":"VISOR_API_KEY","kind":"per_call","required":true,"sensitive":true,"description":"Visor API bearer key."}]
  } |
  .paths["/v1/listings"].get.operationId = "listings.list" |
  .paths["/v1/listings/{listing_id}"].get.operationId = "listings.get" |
  .paths["/v1/facets"].get.operationId = "facets.list" |
  .paths["/v1/vins/{vin}"].get.operationId = "vins.get" |
  .paths["/v1/dealers"].get.operationId = "dealers.list" |
  .paths["/v1/dealers/{dealer_id}"].get.operationId = "dealers.get" |
  .paths["/v1/dealers/{dealer_id}/listings"].get.operationId = "dealers.listings"
' "$TMP/openapi.raw.json" > "$TMP/openapi.json"

mkdir -p "$TMP/research"
cat > "$TMP/research.json" <<'JSON'
{
  "api_name": "visor",
  "novelty_score": 0,
  "alternatives": [],
  "novel_features": [],
  "narrative": {
    "display_name": "Visor",
    "headline": "Query Visor vehicle listings, facets, VIN detail, and dealer inventory from a scriptable CLI.",
    "value_prop": "The Visor CLI mirrors the public API with agent-friendly output controls for listing search, VIN lookup, facets, and dealer inventory.",
    "trigger_phrases": ["search Visor listings", "look up a VIN in Visor", "get Visor facets", "find Visor dealers", "use Visor", "run Visor"]
  },
  "gaps": [],
  "patterns": [],
  "recommendation": "proceed"
}
JSON

"$PRESS" generate \
  --spec "$TMP/openapi.json" \
  --name visor \
  --output "$TMP/visor-generated" \
  --research-dir "$TMP" \
  --spec-source official \
  --transport standard \
  --force --lenient --validate

rsync -a --delete \
  --exclude='.git/' \
  --exclude='bin/' \
  --exclude='build/' \
  --exclude='.gitignore' \
  --exclude='scripts/' \
  --exclude='.github/' \
  --exclude='README.md' \
  --exclude='SKILL.md' \
  --exclude='install.sh' \
  --exclude='internal/client/*_test.go' \
  --exclude='internal/cli/*_test.go' \
  "$TMP/visor-generated/" "$ROOT/"

"$ROOT/scripts/productize-generated.sh"

cd "$ROOT"
go mod tidy
go test ./...
go build -o bin/visor ./cmd/visor
go build -o bin/visor-mcp ./cmd/visor-mcp

echo "Updated visor CLI from $SPEC_URL. Review git diff before committing."
