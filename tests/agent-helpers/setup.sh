#!/bin/bash
# Seed this agent workspace: link or clone the grimoire and get the database.
# Usage: ./setup.sh [grimoire-repo-path] [--mcp|--no-mcp] [--dry-run]
# GRIMOIRE_DB=/path/to/grimoire.db copies a local database instead of downloading.

set -e

WORKSPACE="$(cd "$(dirname "$0")" && pwd)"
# Empty LORE_URL skips the clone and uses degraded mode (no canon queries).
LORE_URL="${LORE_URL-https://github.com/sagaciouszu/destiny-agent-grimoire.git}"
RELEASE_DB_URL="${RELEASE_DB_URL:-https://github.com/sagaciouszu/destiny-agent-grimoire/releases/latest/download/grimoire.db}"
RELEASE_SUMS_URL="${RELEASE_SUMS_URL:-https://github.com/sagaciouszu/destiny-agent-grimoire/releases/latest/download/SHA256SUMS}"
LORE_PATH=""
MCP_CHOICE=""
DRY_RUN=0
for arg in "$@"; do
    case "$arg" in
        --dry-run) DRY_RUN=1 ;;
        --mcp) MCP_CHOICE=1 ;;
        --no-mcp) MCP_CHOICE=0 ;;
        --help|-h)
            echo "usage: $0 [lore-path] [--mcp|--no-mcp] [--dry-run]"
            echo "  lore-path   use an existing grimoire checkout instead of cloning"
            echo "  --mcp       install the optional MCP adapter (ships with the archive)"
            echo "  --dry-run   print the plan and change nothing"
            exit 0 ;;
        -*)
            echo "unknown option: $arg" >&2
            exit 2 ;;
        *)
            if [ -n "$LORE_PATH" ]; then
                echo "only one lore path may be given" >&2
                exit 2
            fi
            LORE_PATH="$arg" ;;
    esac
done
WITH_MCP="${WITH_MCP:-$MCP_CHOICE}"

if [ "$DRY_RUN" = "1" ]; then
    if [ -L "$WORKSPACE/lore" ] && [ ! -e "$WORKSPACE/lore" ]; then
        echo "[dry-run] remove dangling lore symlink -> $(readlink "$WORKSPACE/lore")"
    elif [ -e "$WORKSPACE/lore" ]; then
        echo "[dry-run] use existing lore at $WORKSPACE/lore"
    elif [ -n "$LORE_PATH" ]; then
        echo "[dry-run] link lore -> $LORE_PATH"
    else
        echo "[dry-run] clone lore from $LORE_URL"
    fi
    if [ -f "$WORKSPACE/lore/db/grimoire.db" ]; then
        echo "[dry-run] use existing database"
    elif [ -n "$LORE_PATH" ] && [ -f "$LORE_PATH/db/grimoire.db" ]; then
        echo "[dry-run] use database from $LORE_PATH"
    elif [ -n "${GRIMOIRE_DB:-}" ] && [ -f "$GRIMOIRE_DB" ]; then
        echo "[dry-run] copy database from $GRIMOIRE_DB"
    else
        echo "[dry-run] download or build the database"
    fi
    echo "[dry-run] seed runtime memory and update OpenClaw MCP"
    echo "dry-run: nothing was changed"
    exit 0
fi

echo "=== Agent Setup ==="
echo "Workspace: $WORKSPACE"

# Seed runtime memory files from templates (memory is gitignored: never committed)
for t in USER.template.md core/user-memory.template.md core/journal.template.md core/session-state.template.md core/cross-session-memory.template.md; do
    live="${t%.template.md}.md"
    if [ -f "$WORKSPACE/$t" ] && [ ! -f "$WORKSPACE/$live" ]; then
        cp "$WORKSPACE/$t" "$WORKSPACE/$live"
        echo "Seeded $live"
    fi
done

# Runtime memory is personal: readable by the owner only
for f in "$WORKSPACE/USER.md" "$WORKSPACE"/core/*memory*.md \
         "$WORKSPACE/core/journal.md" "$WORKSPACE/core/session-state.md"; do
    [ -f "$f" ] && chmod 600 "$f" 2>/dev/null || true
done

# Lore archive
# A committed/stale symlink can arrive dangling on another machine
if [ -L "$WORKSPACE/lore" ] && [ ! -e "$WORKSPACE/lore" ]; then
    echo "Removing dangling lore symlink -> $(readlink "$WORKSPACE/lore")"
    rm -f "$WORKSPACE/lore"
fi

if [ -L "$WORKSPACE/lore" ]; then
    echo "lore symlink already exists -> $(readlink "$WORKSPACE/lore")"
elif [ -d "$WORKSPACE/lore" ]; then
    echo "lore/ directory already exists (not a symlink). Skipping."
else
    # Prefer an explicit local path over cloning
    if [ -n "$LORE_PATH" ] && [ -d "$LORE_PATH" ]; then
        LORE_ABS="$(cd "$LORE_PATH" && pwd)"
        ln -s "$LORE_ABS" "$WORKSPACE/lore" 2>/dev/null || true
        if [ -L "$WORKSPACE/lore" ]; then
            echo "Created lore symlink -> $LORE_ABS"
        else
            # Windows (Git Bash): ln may copy or fail; use a junction, then clone.
            if [ -e "$WORKSPACE/lore" ]; then
                chmod -R u+w "$WORKSPACE/lore" 2>/dev/null || true
                rm -rf "$WORKSPACE/lore"
            fi
            if (command -v cmd >/dev/null 2>&1 || command -v cmd.exe >/dev/null 2>&1) && \
               MSYS_NO_PATHCONV=1 cmd /c mklink /J "$(cygpath -w "$WORKSPACE/lore" 2>/dev/null || echo "$WORKSPACE/lore")" \
                                  "$(cygpath -w "$LORE_ABS" 2>/dev/null || echo "$LORE_ABS")" >/dev/null 2>&1; then
                echo "Created lore junction -> $LORE_ABS"
            else
                git clone "$LORE_ABS" "$WORKSPACE/lore"
                echo "Cloned lore archive from $LORE_ABS"
            fi
        fi
    elif [ -n "$LORE_URL" ]; then
        echo "Cloning lore archive from $LORE_URL ..."
        if git clone "$LORE_URL" "$WORKSPACE/lore"; then
            echo "Lore archive cloned."
        else
            echo "WARNING: clone failed; continuing in degraded mode (no canon queries)."
            echo "Retry when online, or link a local checkout: ./setup.sh /path/to/destiny-agent-grimoire"
        fi
    else
        echo ""
        echo "The lore archive is required for full functionality."
        echo ""
        echo "Option 1: Clone from a remote repository:"
        echo "  LORE_URL=https://github.com/sagaciouszu/destiny-agent-grimoire.git ./setup.sh"
        echo ""
        echo "Option 2: Symlink to a local copy:"
        echo "  ./setup.sh /path/to/destiny-agent-grimoire"
        echo ""
        echo "Option 3: Create the link manually:"
        echo "  Unix:      ln -s /path/to/destiny-agent-grimoire $WORKSPACE/lore"
        echo "  Windows:   mklink /J lore C:\\path\\to\\destiny-agent-grimoire"
        echo ""
        echo "Without the lore archive, the agent still functions in degraded mode"
        echo "(core voice, personality, and behavioral rules are self-contained)."
        exit 0
    fi
fi

# A local database can replace the download/build path (offline and CI).
if [ -d "$WORKSPACE/lore" ] && [ ! -f "$WORKSPACE/lore/db/grimoire.db" ] \
   && [ -n "${GRIMOIRE_DB:-}" ] && [ -f "$GRIMOIRE_DB" ]; then
    if [ -L "$WORKSPACE/lore" ]; then
        echo "NOTE: lore/ is a symlink; the database will live inside the linked checkout."
    fi
    mkdir -p "$WORKSPACE/lore/db"
    cp "$GRIMOIRE_DB" "$WORKSPACE/lore/db/grimoire.db"
    echo "Copied local database from $GRIMOIRE_DB"
fi

# Verify
if [ -L "$WORKSPACE/lore" ] || [ -d "$WORKSPACE/lore" ]; then
    if [ -f "$WORKSPACE/lore/db/grimoire.db" ]; then
        if STATS=$(python3 "$WORKSPACE/lore/db/query.py" stats 2>/dev/null); then
            echo "Lore archive: OK (database present)"
            echo "$STATS" | head -12
        else
            echo "WARNING: database file present but unreadable (query failed); check the file."
        fi
    elif [ -f "$WORKSPACE/lore/db/migrate.py" ]; then
        # Database is a build artifact (not shipped in git): bootstrap it now.
        # Agent-safe: BOOTSTRAP=1|2 env preselects (no prompt); interactive
        # terminals get a choice but auto-continue to build after 15s; EOF or
        # timeout falls through to a build (never blocks, never aborts).
        if [ -z "${BOOTSTRAP:-}" ] && [ -t 0 ]; then
            echo ""
            echo "Database not built. Bootstrap options:"
            echo "  [1] Download prebuilt (release asset, ~seconds)"
            echo "  [2] Build from your checkout (~2 minutes, matches this commit)"
            read -t 15 -rp "Choice [1/2] (default 2, auto-continues): " BOOTSTRAP || BOOTSTRAP=""
        fi
        BOOTSTRAP="${BOOTSTRAP:-2}"
        if [ "$BOOTSTRAP" = "1" ] && ! command -v curl >/dev/null 2>&1; then
            echo "curl unavailable; building instead."
            BOOTSTRAP=2
        fi
        echo "Database bootstrap: choice ${BOOTSTRAP}."
        if [ "$BOOTSTRAP" = "1" ] && command -v curl >/dev/null 2>&1; then
            echo "Downloading prebuilt database..."
            TMP_DB="$WORKSPACE/lore/db/grimoire.db.part"
            if curl -fsSL "$RELEASE_DB_URL" -o "$TMP_DB"; then
                VERIFIED=0
                if command -v sha256sum >/dev/null 2>&1; then
                    SHA256="sha256sum"
                elif command -v shasum >/dev/null 2>&1; then
                    SHA256="shasum -a 256"
                else
                    SHA256=""
                fi
                if [ -n "$SHA256" ] && \
                   curl -fsSL "$RELEASE_SUMS_URL" -o "$TMP_DB.sums" 2>/dev/null; then
                    EXPECTED=$(awk '$2=="grimoire.db"{print $1}' "$TMP_DB.sums" | head -1)
                    ACTUAL=$($SHA256 "$TMP_DB" | awk '{print $1}')
                    rm -f "$TMP_DB.sums"
                    [ -n "$EXPECTED" ] && [ "$EXPECTED" = "$ACTUAL" ] && VERIFIED=1
                else
                    echo "WARNING: release checksum unavailable; the download cannot be verified."
                    VERIFIED=2
                fi
                if [ "$VERIFIED" = "0" ]; then
                    echo "Checksum mismatch; discarding the download and building from checkout."
                    rm -f "$TMP_DB"
                    python3 "$WORKSPACE/lore/db/migrate.py"
                    echo "Database built."
                else
                    mv "$TMP_DB" "$WORKSPACE/lore/db/grimoire.db"
                    [ "$VERIFIED" = "1" ] && echo "Database downloaded and verified." \
                        || echo "Database downloaded (unverified)."
                fi
            else
                echo "Download failed; building from checkout instead."
                rm -f "$TMP_DB"
                python3 "$WORKSPACE/lore/db/migrate.py"
                echo "Database built."
            fi
        else
            python3 "$WORKSPACE/lore/db/migrate.py"
            echo "Database built."
        fi
    else
        echo "WARNING: Lore archive found but database missing. Check the path."
    fi
else
    echo "WARNING: Lore archive not available. Agent will work in degraded mode."
fi

# Optional MCP adapter. It lives in the grimoire archive, so one install serves
# every agent that mounts this checkout.
if [ -x "$WORKSPACE/lore/mcp-server/install.sh" ]; then
    if [ -z "${WITH_MCP:-}" ] && [ -t 0 ]; then
        echo ""
        echo "MCP adapter (ships with the grimoire archive; one install serves every agent)"
        read -t 15 -rp "Install for MCP clients without a shell? [y/N] " ans || ans=""
        case "$ans" in y|Y|yes|YES) WITH_MCP=1 ;; *) WITH_MCP=0 ;; esac
    fi
    if [ "${WITH_MCP:-0}" = "1" ]; then
        bash "$WORKSPACE/lore/mcp-server/install.sh"
    else
        echo "Optional: typed MCP tools -> ./setup.sh --mcp (or WITH_MCP=1 ./setup.sh)"
    fi
fi

# OpenClaw: give the global config an absolute grimoire MCP path (idempotent).
# This runs even with --no-mcp (entry/pointer only); the venv install is separate.
if [ -f "$WORKSPACE/lore/scripts/ensure-openclaw-mcp.sh" ]; then
    if [ "${WITH_MCP:-0}" != "1" ]; then
        echo "Note: OpenClaw MCP entry will still reference this checkout; run ./setup.sh --mcp to install the adapter it launches."
    fi
    bash "$WORKSPACE/lore/scripts/ensure-openclaw-mcp.sh" "$WORKSPACE/lore" \
        || echo "warning: OpenClaw MCP config was not updated"
fi

echo ""
echo "First session: ask Hunter, Titan or Warlock; store it with python3 memory.py prefs-set --user <id> --class <class> (USER.md is the human summary)."
echo "Setup complete. Load INDEX.md first; it lists your load order."
