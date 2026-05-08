#!/bin/sh
set -eu

usage() {
  cat >&2 <<'USAGE'
Usage: scripts/release.sh vX.Y.Z

Runs local preflight checks, creates an annotated release tag, pushes main and
the tag, waits for the GitHub Actions release workflow, verifies release assets,
and smoke-tests install.sh against the published release.
USAGE
  exit 2
}

fail() {
  printf 'error: %s\n' "$1" >&2
  exit 1
}

need() {
  command -v "$1" >/dev/null 2>&1 || fail "$1 is required"
}

[ "$#" -eq 1 ] || usage
version="$1"

case "$version" in
  v[0-9]*.[0-9]*.[0-9]*) ;;
  *) fail "version must look like v1.2.3" ;;
esac

root=$(git rev-parse --show-toplevel)
cd "$root"

need git
need gh
need go
need sh

[ "$(git rev-parse --abbrev-ref HEAD)" = "main" ] || fail "release must be run from main"
if [ -n "$(git status --porcelain --untracked-files=normal)" ]; then
  fail "working tree must be clean before release"
fi

git fetch origin main --tags
local_head=$(git rev-parse HEAD)
remote_head=$(git rev-parse origin/main)
[ "$local_head" = "$remote_head" ] || fail "local main must match origin/main"

if git rev-parse "$version" >/dev/null 2>&1; then
  fail "tag $version already exists locally"
fi
if git ls-remote --exit-code --tags origin "refs/tags/$version" >/dev/null 2>&1; then
  fail "tag $version already exists on origin"
fi

printf 'Running release preflight for %s\n' "$version"
sh -n install.sh
go test ./...
go run github.com/goreleaser/goreleaser/v2@latest check

git tag -a "$version" -m "$version"

cleanup_tag() {
  git tag -d "$version" >/dev/null 2>&1 || true
}
trap cleanup_tag INT TERM HUP

git push origin main "$version"
trap - INT TERM HUP

printf 'Waiting for release workflow for %s\n' "$version"
run_id=""
for _ in 1 2 3 4 5 6 7 8 9 10; do
  run_id=$(gh run list \
    --repo visorvin/cli \
    --workflow release \
    --limit 10 \
    --json databaseId,headBranch,event \
    --jq ".[] | select(.headBranch == \"$version\" and .event == \"push\") | .databaseId" \
    | head -n 1)
  [ -n "$run_id" ] && break
  sleep 3
done

[ -n "$run_id" ] || fail "could not find release workflow run for $version"
gh run watch "$run_id" --repo visorvin/cli --exit-status

gh release view "$version" --repo visorvin/cli >/dev/null

tmpbin=$(mktemp -d)
trap 'rm -rf "$tmpbin"' EXIT
VERSION="$version" BIN_DIR="$tmpbin" sh install.sh
"$tmpbin/visor" --version

printf 'Release %s published and installer smoke test passed.\n' "$version"
