# Visor CLI

A scriptable command-line client for the [Visor Public API](https://api.visor.vin/v1/openapi.json): vehicle listings, facets, VIN detail, dealers, and dealer inventory.

The CLI is read-only. It is built for customer workflows, shell scripts, and AI agents that need compact JSON, field selection, CSV export, dry-run previews, and repeatable checks against Visor data.

## Install

### macOS and Linux

Install the latest prebuilt binary without Go:

```bash
curl -fsSL https://raw.githubusercontent.com/visorvin/cli/main/install.sh | sh
```

To install somewhere other than `/usr/local/bin`:

```bash
curl -fsSL https://raw.githubusercontent.com/visorvin/cli/main/install.sh | BIN_DIR="$HOME/.local/bin" sh
```

### Windows

Download the latest Windows zip from GitHub Releases, extract `visor.exe`, and add it to your `PATH`:

```text
https://github.com/visorvin/cli/releases/latest
```

### From source

Developers who already have Go installed can build from source:

```bash
go install github.com/visorvin/cli/cmd/visor@latest
go install github.com/visorvin/cli/cmd/visor-mcp@latest
```

## Authentication

Set a Visor API key:

```bash
export VISOR_API_KEY="your-key-here"
visor doctor
```

You can also store a token locally. For humans, use the secure prompt:

```bash
visor auth set-token
visor auth status
```

For agents and scripts, pipe the token over stdin so it does not appear in process arguments:

```bash
printf '%s' "$VISOR_API_KEY" | visor auth set-token --stdin
visor auth status
```

Config is stored at `~/.config/visor/config.toml`. Local cache/data lives under `~/.cache/visor`, `~/.local/share/visor`, and `~/.visor` depending on feature.

## Quick Start

```bash
# Verify credentials and connectivity.
visor doctor

# Search listings.
visor listings list --make toyota --model camry --state CA --limit 5 --json \
  --select results.data.vin,results.data.year,results.data.make,results.data.model,results.data.price,results.data.dealer_name

# Inspect available segment buckets.
visor facets --make toyota --model camry --state CA --facets year,trim,inventory_type --json

# Look up a VIN.
visor vins 3TMAZ5CN0PM207381 --json \
  --select results.data.vin,results.data.status,results.data.latest_listing.price,results.data.build

# Search dealers.
visor dealers list --state CA --make toyota --limit 5 --json \
  --select results.data.dealer_id,results.data.name,results.data.city,results.data.state
```

## Commands

| Command | Endpoint |
| --- | --- |
| `visor listings list` | `GET /v1/listings` |
| `visor listings get <listing_id>` | `GET /v1/listings/{listing_id}` |
| `visor facets` | `GET /v1/facets` |
| `visor vins <vin>` | `GET /v1/vins/{vin}` |
| `visor dealers list` | `GET /v1/dealers` |
| `visor dealers get <dealer_id>` | `GET /v1/dealers/{dealer_id}` |
| `visor dealers listings list <dealer_id>` | `GET /v1/dealers/{dealer_id}/listings` |

Run `visor --help` or `visor <command> --help` for complete flags.

## Agent Usage

All endpoint commands support common output controls:

```bash
visor listings list --json
visor listings list --json --select results.data.vin,results.data.price
visor listings list --csv
visor listings list --dry-run
visor listings list --agent
```

`--agent` expands to JSON, compact output, no prompts, no color, and yes-to-confirmations. Responses are wrapped with provenance:

```json
{
  "meta": {"source": "live"},
  "results": {"data": []}
}
```

Use `results.data...` paths with `--select`.

## MCP

The optional MCP server exposes the same read-only API surface for agent hosts:

```bash
visor-mcp --help
```

For Claude Desktop-style JSON config:

```json
{
  "mcpServers": {
    "visor": {
      "command": "visor-mcp",
      "env": {
        "VISOR_API_KEY": "<your-key>"
      }
    }
  }
}
```

## Updating From the OpenAPI Spec

This repo is generated-but-owned code. The Visor OpenAPI spec remains the source of truth for endpoint shape, but this repo owns product naming, release config, docs, and any hand-applied compatibility fixes.

To refresh after the API spec changes:

```bash
./scripts/update-from-openapi.sh
```

The script:

1. Runs Printing Press against `https://api.visor.vin/v1/openapi.json`.
2. Copies the fresh generated CLI into a temporary directory.
3. Reapplies Visor productization: binary name `visor`, module `github.com/visorvin/cli`, MCP binary `visor-mcp`, customer-facing docs, and the current sync compatibility patch.
4. Replaces this repo's generated code and spec files.
5. Runs `go test ./...` and builds `visor` and `visor-mcp`.

Review the resulting diff before committing.

## Development

```bash
make build
make test
make build-mcp
```

Live smoke test with a read-only key:

```bash
VISOR_API_KEY="$VISOR_API_KEY" visor listings list --limit 1 --json
```

## Release

This repo includes a GoReleaser config for `visor` and `visor-mcp` binaries across macOS, Linux, and Windows.

```bash
goreleaser release --clean
```

Set up repository secrets/tokens for GitHub Releases and the Homebrew tap before enabling automated releases.
