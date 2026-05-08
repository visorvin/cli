#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# Printing Press emits generated package/binary names with a -pp-cli suffix.
# The product repo publishes stable visor / visor-mcp commands instead.
if [ -d cmd/visor-pp-cli ]; then
  rm -rf cmd/visor
  mv cmd/visor-pp-cli cmd/visor
fi
if [ -d cmd/visor-pp-mcp ]; then
  rm -rf cmd/visor-mcp
  mv cmd/visor-pp-mcp cmd/visor-mcp
fi
rm -f visor-pp-cli visor-pp-mcp visor visor-mcp

mapfile -t product_files < <(find . -type f \
  -not -path './.git/*' \
  -not -path './bin/*' \
  -not -path './build/*' \
  -not -path './dist/*' \
  -not -path './scripts/*')

if [ -f go.mod ]; then
  go mod edit -go=1.23.0
  go mod edit -require=golang.org/x/term@v0.31.0
fi

if [ "${#product_files[@]}" -gt 0 ]; then
  perl -0pi -e '
    s#github\.com/visorvin/visor-cli-pp-cli#github.com/visorvin/cli#g;
    s#github\.com/visorvin/cli-pp-cli#github.com/visorvin/cli#g;
    s#module\s+visor-pp-cli#module github.com/visorvin/cli#g;
    s#module\s+visor#module github.com/visorvin/cli#g;
    s#visor-pp-cli/internal#github.com/visorvin/cli/internal#g;
    s#visor/internal#github.com/visorvin/cli/internal#g;
    s#visor-cli-pp-cli#cli#g;
    s#cli-pp-cli#cli#g;
    s#visor-pp-mcp#visor-mcp#g;
    s#visor-pp-cli#visor#g;
    s#\.visor\b#.visor#g;
  ' "${product_files[@]}"
fi

if [ -f .goreleaser.yaml ]; then
  perl -0pi -e 's/owner: cole/owner: visorvin/; s#homepage: "https://github.com/cole/visor"#homepage: "https://github.com/visorvin/cli"#' .goreleaser.yaml
fi

if [ -f "$ROOT/scripts/patch-public-ready.py" ]; then
  python3 "$ROOT/scripts/patch-public-ready.py"
fi

if [ -f "$ROOT/scripts/patch-secure-auth.py" ]; then
  python3 "$ROOT/scripts/patch-secure-auth.py"
fi

if [ -f "$ROOT/scripts/patch-agent-output.py" ]; then
  python3 "$ROOT/scripts/patch-agent-output.py"
fi

if [ -f "$ROOT/scripts/patch-root-help.py" ]; then
  python3 "$ROOT/scripts/patch-root-help.py"
fi

if [ -f .printing-press.json ] && command -v jq >/dev/null 2>&1; then
  tmp_meta="$(mktemp)"
  jq '.owner = "visorvin" | .spec_path = "spec.json" | .cli_name = "visor" | .mcp_binary = "visor-mcp"' .printing-press.json > "$tmp_meta"
  mv "$tmp_meta" .printing-press.json
fi

# Keep the dealer inventory endpoint at a direct endpoint-equivalent path:
#   visor dealers listings list <dealer_id>
if [ -f internal/cli/dealers_listings_dealers.go ]; then
  perl -0pi -e 's/Use:\s+"dealers <dealer_id>",\n\s+Aliases: \[\]string\{"get"\},/Use:   "list <dealer_id>",\n\t\tAliases: []string{"dealers", "get"},/' internal/cli/dealers_listings_dealers.go
  perl -0pi -e 's/visor dealers listings dealers 550e8400-e29b-41d4-a716-446655440000/visor dealers listings list 550e8400-e29b-41d4-a716-446655440000/' internal/cli/dealers_listings_dealers.go
fi

# Current Visor compatibility patch: generated sync otherwise sends generic params
# that the strict public API rejects, and dry-run tries to store placeholder output.
if [ -f internal/cli/sync.go ]; then
  perl -0pi -e 's/\treturn \[\]string\{\n\t\t"dealers",\n\t\t"facets",\n\t\t"listings",\n\t\}/\treturn []string{\n\t\t"dealers",\n\t\t"listings",\n\t}/' internal/cli/sync.go
  perl -0pi -e 's/\t\tif effectiveSince != "" \{\n\t\t\tparams\[sinceParam\] = effectiveSince\n\t\t\}/\t\tif effectiveSince != "" \&\& sinceParam != "" {\n\t\t\tparams[sinceParam] = effectiveSince\n\t\t}/' internal/cli/sync.go
  perl -0pi -e 's/func determineSinceParam\(\) string \{\n\treturn "since"\n\}/func determineSinceParam() string {\n\treturn ""\n}/' internal/cli/sync.go
  perl -0pi -e 's/\treturn \[\]dependentResourceDef\{\n\t\t\{Name: "dealers_listings", ParentTable: "dealers", ParentIDParam: "dealer_id", PathTemplate: "\/v1\/dealers\/\{dealer_id\}\/listings"\},\n\t\}/\treturn nil/' internal/cli/sync.go

  if ! rg -q 'func syncDryRun' internal/cli/sync.go; then
    perl -0pi -e 's/(\t\t\tif len\(resources\) == 0 \{\n\t\t\t\tresources = defaultSyncResources\(\)\n\t\t\t\}\n)/$1\n\t\t\tif flags.dryRun {\n\t\t\t\treturn syncDryRun(c, resources)\n\t\t\t}\n/' internal/cli/sync.go
    perl -0pi -e 's/(\/\/ syncResource handles the full paginated sync of a single resource\.)/func syncDryRun(c interface {\n\tGet(string, map[string]string) (json.RawMessage, error)\n}, resources []string) error {\n\tpageSize := determinePaginationDefaults()\n\tfor _, resource := range resources {\n\t\tpath, err := syncResourcePath(resource)\n\t\tif err != nil {\n\t\t\treturn err\n\t\t}\n\t\tparams := map[string]string{}\n\t\tif pageSize.limitParam != "" {\n\t\t\tparams[pageSize.limitParam] = strconv.Itoa(pageSize.limit)\n\t\t}\n\t\t_, _ = c.Get(path, params)\n\t}\n\treturn nil\n}\n\n$1/' internal/cli/sync.go
  fi
fi

gofmt -w $(find cmd internal -type f -name '*.go')
