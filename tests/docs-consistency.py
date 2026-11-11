#!/usr/bin/env python3
"""Cross-repo documentation consistency for the grimoire ecosystem.

Checks the current docs (not historical release notes) against the database,
the MCP manifest and the sibling repos:

  - stale literal counts/sizes anywhere in current user or agent docs;
  - the site stats snapshot matches the DB;
  - agent README metadata matches its tag and HEAD date;
  - MCP tool names in mcp-server/README.md match capabilities.json;
  - relative Markdown links resolve.

Read-only. Skips cleanly when a sibling repo is absent.
Exit 1 on any drift.
"""
import glob
import json
import os
import re
import sqlite3
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
WORK = os.path.dirname(ROOT)
DB = os.environ.get("GRIMOIRE_DB") or os.path.join(ROOT, "db", "grimoire.db")
SITE = os.path.join(WORK, "destiny-agent-grimoire-site")
sys.path.insert(0, HERE)
import _roster
AGENTS = [os.path.basename(p) for p in _roster.repos().values()]
TEMPLATE = os.path.join(WORK, "destiny-agent-template")

STALE = ["2,422", "78,740", "130,210", "9,607", "12,934", "206 rows",
         "260 MB", "170 MB", "61 checks", "13/13", "21 exposed",
         "Eighteen read-only tools", "Five character agents",
         "five character agents", "180 lines", "12 lines", "1,254",
         "118,944", "73,012", "23/18", "22/17",
         "29 MiB", "56 MiB", "41.9 MiB", "78.6 MiB", "65 checks", "89 checks", "91 checks",
         "seven scripts", "2024+ client", "tar -xJf", "tar -xzf",
         "sha256sum -c SHA256SUMS"]
HISTORICAL = ("RELEASE.md", "CHANGELOG.md", "BeyondLight-Roadmap.md",
              "GRIMOIRE-CHANGES.md", "live-tier", "post-fix")

PASS = FAIL = 0


def check(name, fn):
    global PASS, FAIL
    try:
        fn()
        print(f"  ✓ {name}")
        PASS += 1
    except Exception as exc:
        print(f"  ✗ {name}: {exc}")
        FAIL += 1


def q(sql, *args):
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    try:
        return conn.execute(sql, args).fetchone()
    finally:
        conn.close()


def current_docs():
    paths = [os.path.join(ROOT, "README.md"),
             os.path.join(ROOT, "db", "README.md"),
             os.path.join(ROOT, "scripts", "README.md"),
             os.path.join(ROOT, "mcp-server", "README.md"),
             os.path.join(ROOT, "skills", "destiny-grimoire", "SKILL.md"),
             os.path.join(ROOT, "STANDARDS.md")]
    paths += glob.glob(os.path.join(ROOT, "docs", "*.md"))
    paths += glob.glob(os.path.join(ROOT, "docs", "wiki", "*.md"))
    if os.path.isdir(SITE):
        paths += glob.glob(os.path.join(SITE, "*.md"))
        paths += glob.glob(os.path.join(SITE, "**", "*.md"), recursive=True)
        paths += glob.glob(os.path.join(SITE, "**", "*.njk"), recursive=True)
        paths = [p for p in paths if "_site" not in p and "node_modules" not in p]
    for agent in AGENTS:
        base = os.path.join(WORK, agent)
        if not os.path.isdir(base):
            continue
        paths += glob.glob(os.path.join(base, "*.md"))
        paths += glob.glob(os.path.join(base, "reference", "*.md"))
        paths += glob.glob(os.path.join(base, "core", "*.md"))
    wiki = os.path.join(WORK, "destiny-agent-grimoire.wiki")
    if os.path.isdir(wiki):
        paths += glob.glob(os.path.join(wiki, "*.md"))
    if os.path.isdir(TEMPLATE):
        for name in ("README.md", "PORTING.md", "LIFECYCLE.md", "COVERAGE.md",
                     "GRIMOIRE-CHANGES.md"):
            p = os.path.join(TEMPLATE, name)
            if os.path.exists(p):
                paths.append(p)
    return sorted({p for p in paths if os.path.isfile(p)})


def stale_counts():
    hits = []
    for path in current_docs():
        if any(marker in path for marker in HISTORICAL):
            continue
        text = open(path, encoding="utf-8", errors="ignore").read()
        for literal in STALE:
            if literal in text:
                hits.append(f"{os.path.relpath(path, WORK)}: {literal}")
    assert not hits, "stale count/size: " + "; ".join(hits[:8])


def site_stats():
    if not os.path.isdir(SITE):
        return                      # lone checkout / CI: nothing to compare
    path = os.path.join(SITE, "_data", "grimoire.json")
    if not os.path.exists(path):
        raise AssertionError("site _data/grimoire.json is missing")
    data = json.load(open(path, encoding="utf-8"))
    assert data.get("schema_version") == open(
        os.path.join(ROOT, "db", "SCHEMA_VERSION"), encoding="utf-8").read().strip(), \
        "site schema_version is stale"
    expected = {
        "transcripts": q("SELECT COUNT(*) FROM transcripts")[0],
        "transcript_lines": q("SELECT COUNT(*) FROM transcript_lines")[0],
        "fts": q("SELECT COUNT(*) FROM fts")[0],
        "caption_provenance": q("SELECT COUNT(*) FROM caption_provenance")[0],
        "caption_sightings": q("SELECT COUNT(*) FROM caption_sightings")[0],
        "books": q("SELECT COUNT(*) FROM books")[0],
        "items": q("SELECT COUNT(*) FROM items")[0],
    }
    for key, value in expected.items():
        assert data.get("counts", {}).get(key) == value, \
            f"site {key} {data.get('counts', {}).get(key)} != DB {value}"


def agent_metadata():
    for agent in AGENTS:
        repo = os.path.join(WORK, agent)
        if not os.path.isdir(repo):
            continue
        readme = os.path.join(repo, "README.md")
        if not os.path.exists(readme):
            continue
        text = open(readme, encoding="utf-8").read()
        m = re.search(r"\*\*Version:\*\* (\S+) \| \*\*Last push:\*\* (\d{4}-\d{2}-\d{2})", text)
        if not m:
            continue
        tag = subprocess.run(["git", "-C", repo, "describe", "--tags", "--abbrev=0"],
                             capture_output=True, text=True).stdout.strip().lstrip("v")
        head = subprocess.run(["git", "-C", repo, "log", "-1", "--format=%cs"],
                              capture_output=True, text=True).stdout.strip()
        assert not tag or m.group(1) == tag, f"{agent} version {m.group(1)} != {tag}"
        assert not head or m.group(2) == head, f"{agent} last push {m.group(2)} != {head}"


def mcp_tools():
    manifest = set(json.load(open(os.path.join(ROOT, "db", "capabilities.json"),
                                  encoding="utf-8"))["mcp"]["tools"])
    readme = open(os.path.join(ROOT, "mcp-server", "README.md"), encoding="utf-8").read()
    documented = set(re.findall(r"^\| `(\w+)` \|", readme, re.M))
    assert manifest == documented, \
        f"MCP README drift: missing {sorted(manifest - documented)}, extra {sorted(documented - manifest)}"


PLAN_LEAKS = (
    (r"/opt/vault", "private vault path"),
    (r"/home/[A-Za-z0-9._-]+/", "absolute home path"),
    (r"/Users/[A-Za-z0-9._-]+/", "absolute home path"),
    (r"DeepSeek", "internal model/provider note"),
    (r"token envelope", "internal token budget"),
    (r"workstream", "internal workstream"),
    (r"work queue", "internal work queue"),
    (r"hard checkpoint", "internal checkpoint"),
    (r"billing boundary", "internal billing note"),
    (r"scratch (test )?agent", "scratch-agent note"),
    (r"## Ingestion plan", "plan section"),
    (r"## Decision rules", "plan section"),
    (r"Stop-loss", "plan rule"),
    (r"P[0-9] status", "internal phase status"),
)


def public_surface():
    bad = []
    for path in current_docs():
        if not path.endswith((".md", ".njk", ".txt")):
            continue
        text = open(path, encoding="utf-8", errors="ignore").read()
        for pattern, label in PLAN_LEAKS:
            if re.search(pattern, text, re.I):
                bad.append(f"{os.path.relpath(path, WORK)}: {label}")
    assert not bad, "internal plan/private-path leak: " + "; ".join(bad[:8])


def relative_links():
    bad = []
    for path in current_docs():
        if path.endswith(".njk"):
            continue
        text = open(path, encoding="utf-8", errors="ignore").read()
        for target in re.findall(r"\]\(([^)]+)\)", text):
            if target.startswith(("http://", "https://", "#", "mailto:", "{{", "/")):
                continue
            target = target.split("#", 1)[0].strip()
            if not target:
                continue
            resolved = os.path.normpath(os.path.join(os.path.dirname(path), target))
            if not os.path.exists(resolved):
                # agent checkouts may not have the lore symlink populated
                if "/lore/" in resolved:
                    continue
                bad.append(f"{os.path.relpath(path, WORK)} -> {target}")
    assert not bad, "broken relative links: " + "; ".join(bad[:8])


print("=== DOCS CONSISTENCY ===")
check("no stale counts or sizes in current docs", stale_counts)
check("site stats snapshot matches the DB", site_stats)
check("agent README metadata matches tags and HEAD", agent_metadata)
check("MCP README tools match the manifest", mcp_tools)
check("no internal plans or private paths in public docs", public_surface)
check("relative Markdown links resolve", relative_links)
print(f"\nPassed: {PASS} | Failed: {FAIL}")
sys.exit(1 if FAIL else 0)
