#!/bin/bash
# Stage a release: database copy, SHA256SUMS, notes, publish commands.
# Usage: scripts/release-stage.sh <version> [--dry-run]
set -e
HERE="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="${1:?usage: release-stage.sh <version> [--dry-run]}"
case "$VERSION" in
    *[!0-9.]*|.*|*.) echo "FATAL: version must be numeric semver, e.g. 0.20.0" >&2; exit 2 ;;
esac
DRY=""
[ "${2:-}" = "--dry-run" ] && DRY="echo"
STAGE="${STAGE_DIR:-$HOME/releases}/v$VERSION"
DB="$HERE/db/grimoire.db"

[ -f "$DB" ] || { echo "FATAL: build the database first"; exit 1; }
echo "staging v$VERSION -> $STAGE"
$DRY mkdir -p "$STAGE"
$DRY cp --reflink=auto "$DB" "$STAGE/grimoire.db"
$DRY cp "$HERE/RELEASE.md" "$STAGE/RELEASE.md"
$DRY bash -c 'cd "$1" && sha256sum grimoire.db > SHA256SUMS' _ "$STAGE"
[ -z "$DRY" ] && cat "$STAGE/SHA256SUMS"
cat <<EOF

Publish:
  cd $HERE
  git tag -a v$VERSION -m "v$VERSION"
  git push origin master --follow-tags
  gh release create v$VERSION $STAGE/grimoire.db $STAGE/SHA256SUMS \\
    --title "v$VERSION" --notes-file RELEASE.md
  gh release edit v$VERSION --latest
EOF
