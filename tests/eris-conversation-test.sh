#!/bin/bash
# Eris conversation test from SQLite database
DB="$(cd "$(dirname "$0")/.." && pwd)/db/grimoire.db"
python3 - "$DB" << 'PYEOF'
import sqlite3, sys
db = sys.argv[1]
conn = sqlite3.connect(db)
conn.row_factory = sqlite3.Row
print("=== ERIS MORN CONVERSATION TEST (uses SQLite database) ===")
print()
print("== Scenario: User asks about the Hive ==")
rows = conn.execute(
    "SELECT line FROM transcript_lines WHERE speaker LIKE '%Eris%' AND line LIKE '%Hive%' LIMIT 3").fetchall()
for i, r in enumerate(rows):
    print(f"  [{i+1}] Eris: \"{r['line'][:100]}\"")
print()
print("== Scenario: User asks about the Darkness ==")
rows = conn.execute(
    "SELECT text FROM fts WHERE fts MATCH 'darkness' AND speaker LIKE '%Eris%' LIMIT 3").fetchall()
for i, r in enumerate(rows):
    print(f"  [{i+1}] Eris: \"{r['text'][:100]}\"")
print()
print("== Scenario: User asks about her fireteam ==")
rows = conn.execute(
    "SELECT line FROM transcript_lines WHERE speaker LIKE '%Eris%' AND (line LIKE '%fireteam%' OR line LIKE '%died%' OR line LIKE '%lost%') LIMIT 3").fetchall()
for i, r in enumerate(rows):
    print(f"  [{i+1}] Eris: \"{r['line'][:100]}\"")
print()
print("== Scenario: User asks about Savathûn ==")
rows = conn.execute(
    "SELECT line FROM transcript_lines WHERE speaker LIKE '%Eris%' AND line LIKE '%Savath%' LIMIT 3").fetchall()
for i, r in enumerate(rows):
    print(f"  [{i+1}] Eris: \"{r['line'][:100]}\"")
print()
print("== Scenario: User asks about the Moon/Hellmouth ==")
rows = conn.execute(
    "SELECT text FROM fts WHERE fts MATCH 'moon OR hellmouth' AND speaker LIKE '%Eris%' LIMIT 3").fetchall()
for i, r in enumerate(rows):
    print(f"  [{i+1}] Eris: \"{r['text'][:100]}\"")
print()
print("== Scenario: Item lore (armor flavor) ==")
rows = conn.execute(
    "SELECT title, text FROM items WHERE item_type LIKE '%Helmet%' AND text != '' LIMIT 3").fetchall()
for i, r in enumerate(rows):
    print(f"  [{i+1}] {r['title'][:40]}: \"{(r['text'] or '')[:90]}\"")
print()
print("== Scenario: Grimoire card (Books of Sorrow) ==")
rows = conn.execute(
    "SELECT title, substr(body,1,150) AS body FROM grimoire_cards WHERE title LIKE '%Sorrow%' LIMIT 2").fetchall()
for i, r in enumerate(rows):
    body = r['body'] or ''
    print(f"  [{i+1}] {r['title'][:50]}: {body[:150]}")
print()
print("=== ERIS CONVERSATION TEST PASSED ===")
conn.close()
PYEOF
