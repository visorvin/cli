#!/bin/sh
set -eu

REPO="${REPO:-visorvin/cli}"
VERSION="${VERSION:-latest}"
BIN_DIR="${BIN_DIR:-/usr/local/bin}"

fail() {
  printf 'error: %s\n' "$1" >&2
  exit 1
}

need() {
  command -v "$1" >/dev/null 2>&1 || fail "$1 is required"
}

print_banner() {
  cat <<'VISOR'
__      ___ ___ ___  ___  ___
\ \    / /_ _/ __|/ _ \| _ \
 \ \  / / | |\__ \ (_) |   /
  \ \/ / |___|___/\___/|_|_\
   \__/   see the whole market

VISOR
  printf 'Visor CLI installer\n\n'
}

os=$(uname -s | tr '[:upper:]' '[:lower:]')
case "$os" in
  darwin|linux) ;;
  *) fail "unsupported OS: $os. Download a binary from https://github.com/$REPO/releases/latest" ;;
esac

arch=$(uname -m)
case "$arch" in
  x86_64|amd64) arch="amd64" ;;
  arm64|aarch64) arch="arm64" ;;
  *) fail "unsupported architecture: $arch" ;;
esac

need curl
need tar

print_banner

if [ "$VERSION" = "latest" ]; then
  release_url="https://api.github.com/repos/$REPO/releases/latest"
else
  release_url="https://api.github.com/repos/$REPO/releases/tags/$VERSION"
fi

json=$(curl -fsSL "$release_url")
asset_url=$(printf '%s\n' "$json" \
  | grep '"browser_download_url"' \
  | sed -E 's/.*"browser_download_url": "([^"]+)".*/\1/' \
  | grep -Ei "visor_.*_${os}_${arch}\\.tar\\.gz$" \
  | head -n 1 || true)

[ -n "$asset_url" ] || fail "could not find a ${os}_${arch} release asset for $REPO $VERSION"

checksums_url=$(printf '%s\n' "$json" \
  | grep '"browser_download_url"' \
  | sed -E 's/.*"browser_download_url": "([^"]+)".*/\1/' \
  | grep -E 'checksums\.txt$' \
  | head -n 1 || true)

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
archive="$tmp/$(basename "$asset_url")"

printf 'Downloading %s\n' "$asset_url"
curl -fL "$asset_url" -o "$archive"

if [ -n "$checksums_url" ]; then
  checksums="$tmp/checksums.txt"
  curl -fsSL "$checksums_url" -o "$checksums"
  expected=$(grep "  $(basename "$archive")$" "$checksums" | awk '{print $1}' || true)
  [ -n "$expected" ] || fail "checksum for $(basename "$archive") not found"

  if command -v sha256sum >/dev/null 2>&1; then
    actual=$(sha256sum "$archive" | awk '{print $1}')
  elif command -v shasum >/dev/null 2>&1; then
    actual=$(shasum -a 256 "$archive" | awk '{print $1}')
  else
    fail "sha256sum or shasum is required to verify the download"
  fi

  [ "$actual" = "$expected" ] || fail "checksum mismatch"
fi

tar -xzf "$archive" -C "$tmp"
visor_bin=$(find "$tmp" -type f -name visor -perm -u+x | head -n 1 || true)
[ -n "$visor_bin" ] || visor_bin=$(find "$tmp" -type f -name visor | head -n 1 || true)
[ -n "$visor_bin" ] || fail "visor binary not found in archive"

install_one() {
  src="$1"
  name="$2"
  if [ -w "$BIN_DIR" ]; then
    install -m 0755 "$src" "$BIN_DIR/$name"
  elif command -v sudo >/dev/null 2>&1; then
    sudo install -m 0755 "$src" "$BIN_DIR/$name"
  else
    fail "$BIN_DIR is not writable and sudo is unavailable. Try: BIN_DIR=\$HOME/.local/bin sh install.sh"
  fi
}

mkdir -p "$BIN_DIR" 2>/dev/null || true
install_one "$visor_bin" visor

mcp_bin=$(find "$tmp" -type f -name visor-mcp | head -n 1 || true)
if [ -n "$mcp_bin" ]; then
  install_one "$mcp_bin" visor-mcp
fi

printf 'Installed visor to %s/visor\n' "$BIN_DIR"
if [ -n "$mcp_bin" ]; then
  printf 'Installed visor-mcp to %s/visor-mcp\n' "$BIN_DIR"
fi
