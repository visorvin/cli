# Visor CLI

## Scope

Go CLI and MCP binary for the read-only Visor Public API. `README.md` is the
user contract. The OpenAPI spec drives endpoint shape, while this repository
owns Visor naming, release configuration, documentation, secure auth, and
hand-maintained compatibility fixes.

## Commands

```bash
make build
make build-mcp
make test
make lint
make build-all
```

Run `go test ./...` after Go changes. Use
`./scripts/update-from-openapi.sh` only when intentionally refreshing generated
API code, then review the entire generated diff and rerun tests/builds.

## Working Rules

- Keep commands non-interactive and parseable when `--agent`, `--json`,
  `--no-input`, or `--yes` is selected.
- Preserve the read-only product boundary. Do not introduce write operations
  without an explicit product decision and matching public API support.
- Never put API keys in arguments, fixtures, logs, or committed config. Agent
  flows should read `VISOR_API_KEY` or use `auth set-token --stdin`.
- Treat output field names, envelopes, exit codes, and error text as public
  compatibility surfaces. Update tests and README examples with behavior.
- Build both `visor` and `visor-mcp` when shared client or generated code
  changes.
- `scripts/release.sh` tags, pushes, and publishes binaries. Do not run it
  without explicit release direction.
