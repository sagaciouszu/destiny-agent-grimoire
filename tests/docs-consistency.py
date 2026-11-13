#!/usr/bin/env python3
"""Cross-repo documentation consistency for the grimoire ecosystem.

Checks the current docs (not historical release notes) against the database,
the MCP manifest and the sibling repos:

  - stale literal counts/sizes anywhere in current user or agent docs;
  - agent-count claims in current docs match series/agents.json;
  - the site stats snapshot matches the DB;
  - agent README metadata matches its tag and HEAD date;
  - MCP tool names in mcp-server/README.md match capabilities.json;
  - relative Markdown links resolve;
  - no timestamped "live build as of <date>" claims in current docs.

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
         "270 MB", "170 MB", "13/13", "21 exposed",
         "Eighteen read-only tools", "Five character agents",
         "five character agents", "180 lines", "12 lines", "1,254",
         "118,944", "73,012", "23/18", "22/17",
         "29 MiB", "56 MiB", "41.9 MiB", "78.6 MiB",
         "seven scripts", "2024+ client", "tar -xJf", "tar -xzf",
         "sha256sum -c SHA256SUMS"]
HISTORICAL = ("RELEASE.md", "CHANGELOG.md", "BeyondLight-Roadmap.md",
              "GRIMOIRE-CHANGES.md", "live-tier", "post-fix",
              "Builds.md", "Captions.md")

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
    paths += glob.glob(os.path.join(ROOT, "docs", "process", "*.md"))
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


# --- positive roster assertion: docs must state the real agent count --------
COUNT_WORDS = ("one two three four five six seven eight nine ten eleven twelve "
               "thirteen fourteen fifteen sixteen seventeen eighteen nineteen "
               "twenty").split()
COUNT_NUM = {w: i for i, w in enumerate(COUNT_WORDS, 1)}
# "<n> character agents", "<n> agents in this series" and "<n> characters"
# are roster-size claims; they must equal len(series/agents.json)["agents"].
# Digits are only trusted next to "agents" (a digit+"characters" claim is
# almost always a string length here: "4000 characters per row"), and
# "N more X" is a relative claim, not a roster size.
COUNT_CLAIM = re.compile(
    r"(?i)\b(?<![\d,])(\d+)\s+(?!more\b)(?:character[\s-]+)?agents\b"
    r"|\b(" + "|".join(COUNT_WORDS) + r")\s+(?!more\b)(?:character[\s-]+)?agents\b"
    r"|\b(" + "|".join(COUNT_WORDS) + r")\s+(?!more\b)characters\b")

# --- frozen build claims: "live build as of <date>" goes stale silently ------
STAMP = (r"(?:20\d\d-\d\d-\d\d|(?:January|February|March|April|May|June|July|"
         r"August|September|October|November|December)\s+20\d\d)")
FROZEN_BUILD = re.compile(
    r"(?i)(?:\b(?:live|current|client) build as of\b"
    rf"|\bas of {STAMP}[^\n]*\b(?:live|current|client) build\b"
    rf"|\b(?:live|current|client) build\b[^\n]*\bas of {STAMP}\b)")


def agent_count_claims():
    manifest = json.load(open(os.path.join(ROOT, "series", "agents.json"),
                              encoding="utf-8"))["agents"]
    roster = len(AGENTS)                       # length via tests/_roster.py
    assert len(manifest) == roster, (
        f"series/agents.json lists {len(manifest)} agents but the "
        f"_roster.py roster exposes {roster} (duplicate id or an entry "
        "missing id/source)")
    hits = []
    for path in current_docs():
        if any(marker in path for marker in HISTORICAL):
            continue                           # release notes record history
        text = open(path, encoding="utf-8", errors="ignore").read()
        for m in COUNT_CLAIM.finditer(text):
            raw = m.group(1) or m.group(2) or m.group(3)
            n = int(raw) if raw.isdigit() else COUNT_NUM[raw.lower()]
            if n != len(manifest):
                line = text.count("\n", 0, m.start()) + 1
                hits.append(f"{os.path.relpath(path, WORK)}:{line}: "
                            f"{raw} agents/characters (roster has {len(manifest)})")
    assert not hits, "agent-count claim drift: " + "; ".join(hits[:8])


def frozen_build_claims():
    hits = []
    for path in current_docs():
        if any(marker in path for marker in HISTORICAL):
            continue
        text = open(path, encoding="utf-8", errors="ignore").read()
        for m in FROZEN_BUILD.finditer(text):
            line = text.count("\n", 0, m.start()) + 1
            hits.append(f"{os.path.relpath(path, WORK)}:{line}: {m.group(0)!r}")
    assert not hits, "timestamped live-build claim: " + "; ".join(hits[:8])


def table_count_claims():
    if not os.path.exists(DB):
        return
    actual = q("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")[0]
    hits = []
    for path in current_docs():
        if any(marker in path for marker in HISTORICAL):
            continue
        text = open(path, encoding="utf-8", errors="ignore").read()
        for m in re.finditer(r"(\d+)\s*(?:tables|tables in the database|database tables)",
                             text, re.I):
            n = int(m.group(1))
            if n != actual:
                line = text.count("\n", 0, m.start()) + 1
                hits.append(f"{os.path.relpath(path, WORK)}:{line}: "
                            f"{m.group(0)} (DB has {actual} tables)")
    assert not hits, "table-count claim drift: " + "; ".join(hits[:8])


def suite_count(command, pattern):
    """Run a suite and parse its reported check count.

    Returns the integer count, or None if the suite could not run (the check
    then skips rather than fails — a missing suite is a CI problem, not a
    documentation problem).
    """
    try:
        out = subprocess.run(command, capture_output=True, text=True,
                             timeout=600).stdout
    except (OSError, subprocess.TimeoutExpired):
        return None
    m = re.search(pattern, out)
    return int(m.group(1)) if m else None


DERIVED = [
    # (label, command, regex, documented literal regex - specific to that label)
    ("Database integrity", ["bash", "tests/test-db.sh"], r"Passed: (\d+)",
     r"Database integrity.*?\|.*?(\d+)\s*checks"),
    ("Query interface", ["bash", "tests/query-interface-test.sh"], r"Passed: (\d+)",
     r"Query interface.*?\|.*?(\d+)\s*CLI and API checks"),
    ("Agent layout", ["bash", "tests/agent-layout-test.sh"], r"Passed: (\d+)",
     r"Agent layout.*?\|.*?(\d+)\s*checks"),
    ("Cutscene captions", ["bash", "tests/cutscene-verify.sh"], r"Passed: (\d+)/(\d+)",
     r"Cutscene captions.*?\|.*?(\d+)/(\d+)\s*checks"),
    ("MCP contract", ["mcp-server/.venv/bin/python", "tests/mcp-test.py"],
     r"Passed: (\d+)", r"MCP contract.*?\|.*?(\d+)/(\d+)\s*checks"),
    ("MCP agent optimisation",
     ["mcp-server/.venv/bin/python", "tests/mcp-agent-optimization-test.py"],
     r"Passed: (\d+)", r"MCP agent optimisation.*?\|.*?(\d+)\s*checks"),
]


def derived_counts():
    """Every suite count in the docs must equal the suite's own reported count.

    Replaces the hand-maintained STALE denylist for check counts. A suite that
    cannot run is skipped; a suite that runs and reports a different number is
    a failure, whether or not anyone remembered to add the old value to the
    denylist.
    """
    actual = {}
    for label, command, pattern, _ in DERIVED:
        actual[label] = suite_count(command, pattern)
    hits = []
    for path in current_docs():
        if any(marker in path for marker in HISTORICAL):
            continue
        text = open(path, encoding="utf-8", errors="ignore").read()
        for label, _command, _pattern, literal_re in DERIVED:
            n = actual[label]
            if n is None:
                continue
            for m in re.finditer(literal_re, text):
                if int(m.group(1)) != n:
                    line = text.count("\n", 0, m.start()) + 1
                    hits.append(f"{os.path.relpath(path, WORK)}:{line}: "
                                f"{m.group(0)} (suite reports {n})")
    assert not hits, "suite-count claim drift: " + "; ".join(hits[:8])


def agent_audit_counts():
    if not os.path.isdir(SITE):
        return
    agents_js = os.path.join(SITE, "_data", "agents.js")
    if not os.path.exists(agents_js):
        return
    text = open(agents_js, encoding="utf-8").read()
    ids = re.findall(r'id:\s*"([^"]+)"', text)
    audits = re.findall(r'audit:\s*\{\s*passed:\s*(\d+)\s*,\s*total:\s*(\d+)\s*\}',
                        text)
    if len(ids) != len(audits):
        raise AssertionError(
            f"agents.js: {len(ids)} ids but {len(audits)} audit blocks")
    repos = _roster.repos()
    hits = []
    for aid, (passed, total) in zip(ids, audits):
        passed = int(passed)
        total = int(total)
        if passed != total:
            hits.append(f"{aid}: audit {passed}/{total} is not green")
        repo = repos.get(aid)
        if repo is None:
            repo = os.path.join(WORK, f"destiny-agent-{aid}")
        suites_path = os.path.join(repo, "tests", "suites.json")
        if not os.path.exists(suites_path):
            continue
        try:
            suite_count = json.load(open(suites_path, encoding="utf-8"))["count"]
        except (KeyError, ValueError, OSError) as exc:
            hits.append(f"{aid}: cannot read suites.json ({exc})")
            continue
        if total != suite_count:
            hits.append(f"{aid}: audit total {total} != suites.json count "
                        f"{suite_count}")
    assert not hits, "agent audit count drift: " + "; ".join(hits)


print("=== DOCS CONSISTENCY ===")
check("no stale counts or sizes in current docs", stale_counts)
check("site stats snapshot matches the DB", site_stats)
check("agent README metadata matches tags and HEAD", agent_metadata)
check("MCP README tools match the manifest", mcp_tools)
check("no internal plans or private paths in public docs", public_surface)
check("relative Markdown links resolve", relative_links)
check("agent-count claims match the series roster", agent_count_claims)
check("no timestamped live-build claims in current docs", frozen_build_claims)
check("table-count claims match the database", table_count_claims)
check("agent audit counts match live manifests", agent_audit_counts)
check("suite-count claims match the live suites", derived_counts)
print(f"\nPassed: {PASS} | Failed: {FAIL}")
sys.exit(1 if FAIL else 0)
