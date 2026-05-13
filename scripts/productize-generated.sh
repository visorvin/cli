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

# Keep product-specific root/client behavior that Printing Press regeneration
# currently resets.
if [ -f internal/cli/root.go ]; then
  perl -0pi -e 's/var version = "1\.0\.0"/var version = "1.0.17"/' internal/cli/root.go
  perl -0pi -e 's/(\tcsv\s+bool\n)(\tplain\s+bool)/$1\tmarkdown      bool\n$2/' internal/cli/root.go
  perl -0pi -e 's/(\tc\.NoCache = f\.noCache\n)(\treturn c, nil)/$1\tc.UserAgent = "visor-cli\/" + version\n\tc.Telemetry = f.telemetryHeaders()\n$2/' internal/cli/root.go
  if ! rg -q 'func \(f \*rootFlags\) telemetryHeaders' internal/cli/root.go; then
    perl -0pi -e 's/(func \(f \*rootFlags\) printJSON)/func (f *rootFlags) telemetryHeaders() map[string]string {\n\tcontext := []string{}\n\tif f.agent {\n\t\tcontext = append(context, "agent")\n\t}\n\tif f.compact {\n\t\tcontext = append(context, "compact")\n\t}\n\tif f.asJSON {\n\t\tcontext = append(context, "json")\n\t}\n\tif f.markdown {\n\t\tcontext = append(context, "markdown")\n\t}\n\tif f.csv {\n\t\tcontext = append(context, "csv")\n\t}\n\tif f.plain {\n\t\tcontext = append(context, "plain")\n\t}\n\tif f.quiet {\n\t\tcontext = append(context, "quiet")\n\t}\n\tif f.noCache {\n\t\tcontext = append(context, "no-cache")\n\t}\n\n\theaders := map[string]string{\n\t\t"X-Visor-Client":      "cli",\n\t\t"X-Visor-CLI-Version": version,\n\t}\n\tif len(context) > 0 {\n\t\theaders["X-Visor-CLI-Context"] = strings.Join(context, ",")\n\t}\n\treturn headers\n}\n\n$1/' internal/cli/root.go
  fi
fi

if [ -f internal/client/client.go ]; then
  perl -0pi -e 's/(\tNoCache\s+bool\n)(\tcacheDir)/$1\tUserAgent  string\n\tTelemetry  map[string]string\n$2/' internal/client/client.go
  perl -0pi -e 's/(\t\tHTTPClient: httpClient,\n)(\t\tcacheDir:)/$1\t\tUserAgent:  "visor-cli",\n$2/' internal/client/client.go
  perl -0pi -e 's/\t\tif bodyBytes != nil \{\n\t\t\treq\.Header\.Set\("Content-Type", "application\/json"\)\n\t\t\}\n\n//g' internal/client/client.go
  perl -0pi -e 's/\t\t\/\/ Per-endpoint header overrides \(e\.g\., different API version per resource\)\n\t\tfor k, v := range headerOverrides \{\n\t\t\treq\.Header\.Set\(k, v\)\n\t\t\}\n\t\treq\.Header\.Set\("User-Agent", "visor\/1\.0\.0-beta"\)/\t\tc.applyRequestHeaders(req.Header, bodyBytes != nil, headerOverrides)/' internal/client/client.go
  if ! rg -q 'func \(c \*Client\) applyRequestHeaders' internal/client/client.go; then
    perl -0pi -e 's/(func \(c \*Client\) ConfiguredTimeout)/func (c *Client) applyRequestHeaders(h http.Header, hasBody bool, headerOverrides map[string]string) {\n\tif hasBody {\n\t\th.Set("Content-Type", "application\/json")\n\t}\n\t\/\/ Per-endpoint header overrides (e.g., different API version per resource).\n\tfor k, v := range headerOverrides {\n\t\th.Set(k, v)\n\t}\n\tif c.UserAgent != "" {\n\t\th.Set("User-Agent", c.UserAgent)\n\t}\n\tkeys := make([]string, 0, len(c.Telemetry))\n\tfor k := range c.Telemetry {\n\t\tkeys = append(keys, k)\n\t}\n\tsort.Strings(keys)\n\tfor _, k := range keys {\n\t\tif c.Telemetry[k] != "" {\n\t\t\th.Set(k, c.Telemetry[k])\n\t\t}\n\t}\n}\n\n$1/' internal/client/client.go
  fi
  if ! rg -Fq 'headers := http.Header{}' internal/client/client.go; then
    perl -0pi -e 's/(\tif authHeader != "" \{\n\t\tfmt\.Fprintf\(os\.Stderr, "  %s: %s\\n", "Authorization", maskToken\(authHeader\)\)\n\t\}\n)(\tfmt\.Fprintf\(os\.Stderr, "\\n\(dry run - no request sent\)\\n"\))/$1\theaders := http.Header{}\n\tc.applyRequestHeaders(headers, body != nil, headerOverrides)\n\theaderKeys := make([]string, 0, len(headers))\n\tfor k := range headers {\n\t\tif strings.EqualFold(k, "Authorization") {\n\t\t\tcontinue\n\t\t}\n\t\theaderKeys = append(headerKeys, k)\n\t}\n\tsort.Strings(headerKeys)\n\tfor _, k := range headerKeys {\n\t\tfmt.Fprintf(os.Stderr, "  %s: %s\\n", k, headers.Get(k))\n\t}\n$2/' internal/client/client.go
  fi
fi

if [ -f cmd/visor-mcp/main.go ]; then
  perl -0pi -e 's/"1\.0\.0"/"1.0.17"/' cmd/visor-mcp/main.go
fi

if [ -f internal/mcp/tools.go ]; then
  if ! rg -q 'c.UserAgent = "visor-mcp"' internal/mcp/tools.go; then
    perl -0pi -e 's/(\tc := client\.New\(cfg, 30\*time\.Second, 0\)\n)/$1\tc.UserAgent = "visor-mcp"\n\tc.Telemetry = map[string]string{\n\t\t"X-Visor-Client":      "mcp",\n\t\t"X-Visor-CLI-Context": "agent,mcp,json,compact",\n\t}\n/' internal/mcp/tools.go
  fi
  perl -0pi -e 's/"name":\s+"usage",\s+"description":\s+"Manage usage",\s+"endpoints":\s+\[\]string\{"public"\},\s+"syncable":\s+true,\s+"searchable":\s+true,/"name":        "usage",\n\t\t\t\t"description": "Manage usage",\n\t\t\t\t"endpoints":   []string{"public"},\n\t\t\t\t"syncable":    false,\n\t\t\t\t"searchable":  false,/s' internal/mcp/tools.go
fi

if [ -f internal/cli/which.go ]; then
  perl -0pi -e 's/Command: "usage public"/Command: "usage"/' internal/cli/which.go
fi
if [ -f internal/cli/promoted_usage.go ]; then
  perl -0pi -e 's/Shortcut for '\''usage public'\''. //' internal/cli/promoted_usage.go
fi

for promoted in internal/cli/promoted_facets.go internal/cli/promoted_usage.go internal/cli/promoted_vins.go; do
  if [ -f "$promoted" ]; then
    perl -0pi -e 's#\t\t\t// For JSON output, wrap with provenance envelope\. --select wins over\n\t\t\t// --compact when both are set; --compact only runs when no explicit\n\t\t\t// fields were requested\.\n\t\t\tif flags\.asJSON \|\| flags\.markdown \|\| !isTerminal\(cmd\.OutOrStdout\(\)\) \{\n\t\t\t\tfiltered := data\n\t\t\t\tif flags\.selectFields != "" \{\n\t\t\t\t\tfiltered = filterFields\(filtered, flags\.selectFields\)\n\t\t\t\t\} else if flags\.compact \{\n\t\t\t\t\tfiltered = compactFields\(filtered\)\n\t\t\t\t\}\n\t\t\t\twrapped, wrapErr := wrapWithProvenance\(filtered, prov\)#\t\t\t// For structured output, wrap with provenance first so --select paths\n\t\t\t// match the documented envelope shape, e.g. results.data.vin.\n\t\t\tif flags.asJSON || flags.markdown || !isTerminal(cmd.OutOrStdout()) {\n\t\t\t\twrapped, wrapErr := wrapWithProvenance(data, prov)#g' "$promoted"
  fi
done

# Keep the dealer inventory endpoint at a direct endpoint-equivalent path:
#   visor dealers listings list <dealer_id>
if [ -f internal/cli/dealers_listings_dealers.go ]; then
  perl -0pi -e 's/Use:\s+"dealers <dealer_id>",\n\s+Aliases: \[\]string\{"get"\},/Use:   "list <dealer_id>",\n\t\tAliases: []string{"dealers", "get"},/' internal/cli/dealers_listings_dealers.go
  perl -0pi -e 's/visor dealers listings dealers 550e8400-e29b-41d4-a716-446655440000/visor dealers listings list 550e8400-e29b-41d4-a716-446655440000/' internal/cli/dealers_listings_dealers.go
  perl -0pi -e 's/\n\tvar flagDealerId string//' internal/cli/dealers_listings_dealers.go
  perl -0pi -e 's/\n\t\t\t\t"dealer_id":\s+fmt\.Sprintf\("%v", flagDealerId\),//' internal/cli/dealers_listings_dealers.go
  perl -0pi -e 's/\n\tcmd\.Flags\(\)\.StringVar\(&flagDealerId, "dealer-id", "", "Comma-separated dealer UUIDs\. Accepts up to 50 dealer IDs and uses dealer-filtered listing metering\."\)//' internal/cli/dealers_listings_dealers.go
fi

# The dealer inventory endpoint has a path dealer_id. The upstream shared
# listing filter also includes query dealer_id, which collides in generated
# MCP tool names. Keep the path argument for this endpoint and leave query
# dealer_id available on the top-level listings/facets commands.
if [ -f internal/mcp/tools.go ]; then
  perl -0pi -e 's/Required: dealer_id\. Optional: limit, offset, sort \(plus 64 more\)\./Required: dealer_id. Optional: limit, offset, sort (plus 63 more)./' internal/mcp/tools.go
  perl -0pi -e 's/\n\t\t\tmcplib\.WithString\("dealer_id", mcplib\.Description\("Comma-separated dealer UUIDs\. Accepts up to 50 dealer IDs and uses dealer-filtered listing metering\."\)\),//' internal/mcp/tools.go
  perl -0pi -e 's/, \{PublicName: "dealer_id", WireName: "dealer_id", Location: "path"\}, \{PublicName: "dealer_type"/, {PublicName: "dealer_type"/' internal/mcp/tools.go
fi

# Current Visor compatibility patch: generated sync otherwise sends generic params
# that the strict public API rejects, and dry-run tries to store placeholder output.
if [ -f internal/cli/sync.go ]; then
  perl -0pi -e 's/\treturn \[\]string\{\n\t\t"dealers",\n\t\t"facets",\n\t\t"listings",\n\t\}/\treturn []string{\n\t\t"dealers",\n\t\t"listings",\n\t}/' internal/cli/sync.go
  perl -0pi -e 's/\treturn \[\]string\{\n\t\t"dealers",\n\t\t"listings",\n\t\t"usage",\n\t\}/\treturn []string{\n\t\t"dealers",\n\t\t"listings",\n\t}/' internal/cli/sync.go
  perl -0pi -e 's/\n\tcase "usage":\n\t\treturn db\.UpsertUsage\(data\)//' internal/cli/sync.go
  perl -0pi -e 's/\n\t\t"usage":\s+"\/v1\/usage",//' internal/cli/sync.go
  perl -0pi -e 's/\n\t"usage":\s+"date",//' internal/cli/sync.go
  perl -0pi -e 's/\t\tif effectiveSince != "" \{\n\t\t\tparams\[sinceParam\] = effectiveSince\n\t\t\}/\t\tif effectiveSince != "" \&\& sinceParam != "" {\n\t\t\tparams[sinceParam] = effectiveSince\n\t\t}/' internal/cli/sync.go
  perl -0pi -e 's/func determineSinceParam\(\) string \{\n\treturn "since"\n\}/func determineSinceParam() string {\n\treturn ""\n}/' internal/cli/sync.go
  perl -0pi -e 's/\treturn \[\]dependentResourceDef\{\n\t\t\{Name: "dealers_listings", ParentTable: "dealers", ParentIDParam: "dealer_id", PathTemplate: "\/v1\/dealers\/\{dealer_id\}\/listings"\},\n\t\}/\treturn nil/' internal/cli/sync.go

  if ! rg -q 'func syncDryRun' internal/cli/sync.go; then
    perl -0pi -e 's/(\t\t\tif len\(resources\) == 0 \{\n\t\t\t\tresources = defaultSyncResources\(\)\n\t\t\t\}\n)/$1\n\t\t\tif flags.dryRun {\n\t\t\t\treturn syncDryRun(c, resources)\n\t\t\t}\n/' internal/cli/sync.go
    perl -0pi -e 's/(\/\/ syncResource handles the full paginated sync of a single resource\.)/func syncDryRun(c interface {\n\tGet(string, map[string]string) (json.RawMessage, error)\n}, resources []string) error {\n\tpageSize := determinePaginationDefaults()\n\tfor _, resource := range resources {\n\t\tpath, err := syncResourcePath(resource)\n\t\tif err != nil {\n\t\t\treturn err\n\t\t}\n\t\tparams := map[string]string{}\n\t\tif pageSize.limitParam != "" {\n\t\t\tparams[pageSize.limitParam] = strconv.Itoa(pageSize.limit)\n\t\t}\n\t\t_, _ = c.Get(path, params)\n\t}\n\treturn nil\n}\n\n$1/' internal/cli/sync.go
  fi
fi

if [ -f internal/cli/channel_workflow.go ]; then
  perl -0pi -e 's/\[\]string\{\s*"dealers",\s*"listings",\s*"usage"\s*\}/[]string{"dealers", "listings"}/s' internal/cli/channel_workflow.go
fi

gofmt -w $(find cmd internal -type f -name '*.go')
