#!/bin/bash
# Agent conversation test: pulls lore from the SQLite database
DB="$(cd "$(dirname "$0")/.." && pwd)/db/grimoire.db"
[ -f "$DB" ] || { echo "FAIL: database not found at $DB - bootstrap: ./setup.sh, or python3 db/migrate.py (see README)"; exit 1; }
python3 - "$DB" << 'PYEOF'
import sqlite3, sys
db = sys.argv[1]
conn = sqlite3.connect(db)
conn.row_factory = sqlite3.Row
print("=== DRIFTER CONVERSATION TEST (uses SQLite database) ===")
print()
print("== Scenario: User asks about Gambit ==")
rows = conn.execute(
    "SELECT line FROM transcript_lines WHERE speaker = 'Drifter' AND line LIKE '%Gambit%' LIMIT 3").fetchall()
for i, r in enumerate(rows):
    print(f"  [{i+1}] Drifter: \"{r['line'][:100]}\"")
print()
print("== Scenario: User asks about the Darkness ==")
rows = conn.execute(
    "SELECT text FROM fts WHERE fts MATCH 'darkness' AND speaker = 'Drifter' LIMIT 3").fetchall()
for i, r in enumerate(rows):
    print(f"  [{i+1}] Drifter: \"{r['text'][:100]}\"")
print()
print("== Scenario: User asks about Eris ==")
rows = conn.execute(
    "SELECT line FROM transcript_lines WHERE speaker = 'Drifter' AND line LIKE '%Eris%' LIMIT 3").fetchall()
for i, r in enumerate(rows):
    print(f"  [{i+1}] Drifter: \"{r['line'][:100]}\"")
print()
print("== Scenario: User asks about items (weapon flavor text) ==")
rows = conn.execute(
    "SELECT title, text FROM items WHERE text != '' AND (item_type LIKE '%Hand Cannon%' OR item_type LIKE '%Sniper%') LIMIT 3").fetchall()
for i, r in enumerate(rows):
    print(f"  [{i+1}] {r['title'][:30]}: \"{r['text'][:90]}\"")
print()
print("== Scenario: Grimoire card (Destiny 1 lore) ==")
rows = conn.execute(
    "SELECT title, substr(body,1,200) AS body FROM grimoire_cards WHERE body LIKE '%Moon%' LIMIT 2").fetchall()
for i, r in enumerate(rows):
    body = r['body'] or ''
    print(f"  [{i+1}] {r['title'][:50]}: {body[:150]}")
print()
print("=== CONVERSATION TEST PASSED (all queries hit SQLite database) ===")
conn.close()
PYEOF
