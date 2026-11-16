#!/bin/bash
# Rebuild the full grimoire.db from vault-local extraction corpora.
# Raw corpora are never committed; this script copies them in, builds,
# verifies, and removes the staged copies. The vault is only ever read.
# Usage: scripts/rebuild-from-vault.sh [--vault DIR] [--dry-run]
set -e
HERE="$(cd "$(dirname "$0")/.." && pwd)"
VAULT_DEFAULT="/opt/vault/d2-bl-extract/archive-data-backup/archive/data"
VAULT="$VAULT_DEFAULT"
DRY=""

STAGED=()
cleanup_and_restore() {
    # Remove exactly what this script staged (never operator files), and
    # restore the pre-build database if the chain failed midway.
    if [ "${#STAGED[@]}" -gt 0 ]; then
        rm -f "${STAGED[@]}"
    fi
    rmdir "$DATA/locale-maps" 2>/dev/null || true
    if [ -f "$DB.prevault" ]; then
        mv -f "$DB.prevault" "$DB"
        echo "restored pre-build database" >&2
    fi
}
trap 'cleanup_and_restore; exit 2' ERR

while [ $# -gt 0 ]; do
    case "$1" in
        --vault) VAULT="${2:?--vault needs a directory}"; shift 2 ;;
        --dry-run) DRY="echo"; shift ;;
        *) echo "FATAL: unknown argument $1 (usage: rebuild-from-vault.sh [--vault DIR] [--dry-run])" >&2; exit 2 ;;
    esac
done

MANIFEST="$HERE/scripts/vault-manifest.sha256"
# Manifest paths are relative to the backup root (parent of archive/data).
ROOT="$(dirname "$(dirname "$VAULT")")"
DATA="$HERE/archive/data"
DB="$HERE/db/grimoire.db"

[ -f "$MANIFEST" ] || { echo "FATAL: manifest missing: $MANIFEST" >&2; exit 2; }
[ -d "$VAULT" ] || { echo "FATAL: vault data dir not found: $VAULT" >&2; exit 2; }

echo "verifying vault against manifest..."
if ! (cd "$ROOT" && sha256sum -c "$MANIFEST"); then
    echo "FATAL: vault verification failed (missing or altered files above)" >&2
    exit 2
fi

# Build inputs: the 9 files migrate.py reads plus locale-maps/ for tooling.
INPUTS="captions.jsonl captions-live.jsonl cutscenes.jsonl interactions.jsonl
items.jsonl transcripts_web.jsonl transcripts_overlap.jsonl
transcript-releases.json transcript-missing.txt"

if [ -n "$DRY" ]; then
    echo "dry-run: would stage vault inputs, run migrate + enrich chain, gate, clean up"
    echo "dry-run: vault=$VAULT data=$DATA db=$DB"
    exit 0
fi

echo "staging vault inputs (copy-only)..."
mkdir -p "$DATA/locale-maps"
for f in $INPUTS; do
    cp "$VAULT/$f" "$DATA/$f"
    STAGED+=("$DATA/$f")
done
for f in "$VAULT"/locale-maps/*; do
    cp "$f" "$DATA/locale-maps/"
    STAGED+=("$DATA/locale-maps/$(basename "$f")")
done

echo "rebuilding database..."
[ -f "$DB" ] && cp -f "$DB" "$DB.prevault.tmp" && mv -f "$DB.prevault.tmp" "$DB.prevault"  # restore point; migrate recreates
python3 "$HERE/db/migrate.py"
python3 "$HERE/scripts/apply-queen-fold.py"
python3 "$HERE/db/enrich_lore.py"
python3 "$HERE/db/enrich_seals.py"
python3 "$HERE/db/enrich_itemsets.py" --apply
python3 "$HERE/db/build_entity_web.py" --db "$DB"

echo "gates..."
python3 "$HERE/tests/conformance.py"
bash "$HERE/tests/test-db.sh"
GRIMOIRE_DB="$DB" python3 "$HERE/tests/caption-test.py"

echo "re-verifying vault (untouched proof)..."
(cd "$ROOT" && sha256sum -c "$MANIFEST" > /dev/null) \
    || { cleanup_and_restore; echo "FATAL: vault changed during build" >&2; exit 2; }
echo "vault untouched: OK"

echo "cleaning staged corpora..."
if [ "${#STAGED[@]}" -gt 0 ]; then
    rm -f "${STAGED[@]}"
fi
rmdir "$DATA/locale-maps" 2>/dev/null || true
rm -f "$DB.prevault"

echo "--- rebuilt table counts ---"
sqlite3 "$DB" "SELECT 'interactions', COUNT(*) FROM interactions
UNION ALL SELECT 'items', COUNT(*) FROM items
UNION ALL SELECT 'transcripts', COUNT(*) FROM transcripts
UNION ALL SELECT 'transcript_lines', COUNT(*) FROM transcript_lines
UNION ALL SELECT 'caption_sightings', COUNT(*) FROM caption_sightings
UNION ALL SELECT 'fts', COUNT(*) FROM fts;"
echo "database written: $DB"
