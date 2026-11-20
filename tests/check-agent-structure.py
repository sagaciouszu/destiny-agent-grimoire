#!/usr/bin/env python3
"""Structural checks shared by both agent workspaces.

Usage: check-agent-structure.py <deps|tokens|dashes|index|paths|required> <workspace>  # tokens gates the Core tier only
Exit 1 on violations; prints the offending files.
"""

import glob
import os
import re
import sys

RUNTIME = (
    "USER.md",
    "user-memory.md",
    "journal.md",
    "session-state.md",
    "cross-session-memory.md",
    "DREAMS.md",
)
SKIP_MODULES = ("README.md", "RELEASE.md", "CHANGELOG.md") + RUNTIME


def modules(ws):
    files = [
        f
        for d in ("", "voice", "core", "world", "reference")
        for f in glob.glob(os.path.join(ws, d, "*.md"))
    ]
    return [f for f in files if os.path.basename(f) not in RUNTIME]


def resolve(ws, from_file, dep):
    dep = dep.strip().strip("`")
    if not dep or dep.lower().startswith("none"):
        return True
    for cand in (dep, dep[:-3] + ".template.md" if dep.endswith(".md") else dep):
        if os.path.exists(os.path.join(ws, cand)):
            return True
        if os.path.exists(os.path.join(os.path.dirname(from_file), cand)):
            return True
    return False


def main():
    cmd, ws = sys.argv[1], sys.argv[2]
    files = modules(ws)
    bad = []

    if cmd == "deps":
        for f in files:
            text = open(f, encoding="utf-8").read()
            m = re.search(r"\*\*Depends On:\*\*\s*(.+)", text)
            if not m:
                bad.append((f, "no Depends On header"))
                continue
            for dep in m.group(1).split(","):
                if not resolve(ws, f, dep):
                    bad.append((f, f"unresolved dependency {dep.strip()}"))
    elif cmd == "tokens":
        for f in files:
            if "Token Estimate:" not in open(f, encoding="utf-8").read():
                bad.append((f, "no Token Estimate header"))
        # load-tier claims in INDEX.md and AGENTS.md must match measured
        # sizes (25% tolerance). Each table is checked against the files its
        # own rows name; 'this file' resolves to the table's own file.
        core = os.path.basename(glob.glob(os.path.join(ws, "*-core.md"))[0])

        def size(rel):
            p = os.path.join(ws, rel)
            return (
                len(open(p, encoding="utf-8").read()) / 4 / 1000
                if os.path.exists(p)
                else None
            )

        def tier_files(table_file, row):
            refs = re.findall(r"`([^`]+\.md)`", row)
            if "this file" in row:
                refs = [table_file] + refs
            return refs

        for table_file in ("INDEX.md", "AGENTS.md"):
            table_path = os.path.join(ws, table_file)
            if not os.path.exists(table_path):
                continue
            table_text = open(table_path, encoding="utf-8").read()
            # Two-tier budgets (cut #3): each table carries one gated Core row
            # naming its always-loaded files; legacy Minimal / Standard / Deep
            # rows are rejected so the old tables cannot drift back.
            if re.search(r"\| (Minimal|Standard|Deep) \|", table_text):
                bad.append(
                    (
                        table_path,
                        "legacy three-tier row present; migrate to Core/Task-loaded",
                    )
                )
                continue
            m_core = re.search(rf"\| Core \|[^\n]*", table_text)
            if not m_core:
                bad.append((table_path, "Core tier claim missing"))
                continue
            actual = sum(size(r) or 0 for r in tier_files(table_file, m_core.group(0)))
            m = re.search(rf"\| Core \|[^\n]*?~([\d.]+)K", table_text)
            if not m:
                bad.append((table_path, "Core tier claim missing"))
                continue
            claimed = float(m.group(1))
            if actual and abs(actual - claimed) / claimed > 0.25:
                bad.append(
                    (table_path, f"Core tier ~{claimed}K vs measured ~{actual:.1f}K")
                )
    elif cmd == "dashes":
        for f in files:
            text = open(f, encoding="utf-8").read()
            if "\u2014" in text or "\u2013" in text:
                bad.append((f, "em/en dash"))
    elif cmd == "index":
        idx = open(os.path.join(ws, "INDEX.md"), encoding="utf-8").read()
        for ref in set(re.findall(r"`([A-Za-z0-9_./-]+\.md)`", idx)):
            if os.path.basename(ref) in RUNTIME or resolve(ws, "INDEX.md", ref):
                continue
            bad.append(("INDEX.md", f"broken ref {ref}"))
        for f in files:
            rel = os.path.relpath(f, ws)
            if os.path.basename(rel) in SKIP_MODULES:
                continue
            if os.path.basename(rel) not in idx:
                bad.append((rel, "not listed in INDEX.md"))
    elif cmd == "paths":
        pat = re.compile(r"/home/[a-z0-9._-]+/|/Users/[a-z0-9._-]+/", re.I)
        for f in glob.glob(os.path.join(ws, "**", "*.*"), recursive=True):
            if not f.endswith((".md", ".sh", ".py")) or "/lore/" in f or "/.git/" in f:
                continue
            if pat.search(open(f, encoding="utf-8", errors="ignore").read()):
                bad.append((os.path.relpath(f, ws), "personal path"))
    elif cmd == "required":
        # Fail-closed required-file manifest: exactly one registry of what
        # belongs at the top level of an agent repo. Images are allowed by
        # extension (README decoration); everything else unlisted fails.
        core = glob.glob(os.path.join(ws, "*-core.md"))
        if not core:
            print("required files: ok (skeleton layout, skipped)")
            return 0
        stem = os.path.basename(core[0])[: -len("-core.md")]
        allowed_files = {
            "AGENTS.md",
            "CHANGELOG.md",
            "IDENTITY.md",
            "INDEX.md",
            "LICENSE",
            "NOTICE",
            "README.md",
            "RELEASE.md",
            "SOUL.md",
            "TOOLS.md",
            "USER.template.md",
            "memory.py",
            "persona.json",
            "setup.sh",
            ".gitignore",
            f"{stem}.md",
            f"{stem}-core.md",
            f"{stem}-voice.md",
        }
        allowed_dirs = {
            ".git",
            ".github",
            "core",
            "voice",
            "world",
            "reference",
            "tests",
            "lore",
            "__pycache__",
            ".venv",
            "node_modules",
        }
        allowed_ext = {".png", ".svg", ".jpg", ".jpeg", ".gif"}
        n = 0
        for name in sorted(os.listdir(ws)):
            # Runtime-seeded state is gitignored by design, not shipped content.
            if name in RUNTIME:
                continue
            pth = os.path.join(ws, name)
            if os.path.isdir(pth):
                if name not in allowed_dirs:
                    bad.append((pth, "unlisted top-level directory"))
                continue
            n += 1
            if name in allowed_files:
                continue
            if os.path.splitext(name)[1].lower() in allowed_ext:
                continue
            bad.append((pth, "unlisted top-level file"))
        if not bad:
            print(f"required files: ok ({n} top-level entries checked)")
    else:
        print(f"unknown check: {cmd}", file=sys.stderr)
        return 2

    if bad:
        print(f"{cmd}: {len(bad)} issue(s)")
        for f, why in bad[:20]:
            print(f"  {os.path.relpath(f, ws) if f.startswith(ws) else f}: {why}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
