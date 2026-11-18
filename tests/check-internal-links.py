#!/usr/bin/env python3
"""Check relative Markdown links in grimoire and agent repos.

Usage: python3 tests/check-internal-links.py
Exit 1 if any broken relative links are found.
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
WORK = os.path.dirname(ROOT)

LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")


def check_file(path, base_dir):
    """Check relative links in a single markdown file. Return list of (line, link, reason)."""
    broken = []
    try:
        text = open(path, encoding="utf-8", errors="ignore").read()
    except Exception:
        return broken
    for lineno, line in enumerate(text.splitlines(), 1):
        for m in LINK_RE.finditer(line):
            link = m.group(2).strip()
            # Skip absolute URLs, anchors-only, and mailto
            if link.startswith(("http://", "https://", "mailto:", "#")):
                continue
            # Strip anchor
            link_path = link.split("#")[0]
            if not link_path:
                continue
            # Resolve relative to file's directory
            target = os.path.normpath(os.path.join(os.path.dirname(path), link_path))
            if not os.path.exists(target):
                broken.append((lineno, link, f"target not found: {target}"))
    return broken


def main():
    # Scan grimoire repo + all agent repos
    scan_dirs = [ROOT]
    # Add agent repos from series/agents.json
    agents_json = os.path.join(ROOT, "series", "agents.json")
    if os.path.exists(agents_json):
        import json

        with open(agents_json) as f:
            for agent in json.load(f)["agents"]:
                repo = os.path.join(WORK, agent["source"])
                if os.path.isdir(repo):
                    scan_dirs.append(repo)
    # Add wiki
    wiki = os.path.join(WORK, "destiny-agent-grimoire.wiki")
    if os.path.isdir(wiki):
        scan_dirs.append(wiki)

    all_broken = []
    for scan_dir in scan_dirs:
        for dirpath, _, filenames in os.walk(scan_dir):
            # Skip .git, node_modules, .venv
            if any(
                skip in dirpath
                for skip in (".git", "node_modules", ".venv", "__pycache__")
            ):
                continue
            for fn in filenames:
                if not fn.endswith(".md"):
                    continue
                path = os.path.join(dirpath, fn)
                broken = check_file(path, scan_dir)
                for lineno, link, reason in broken:
                    rel = os.path.relpath(path, WORK)
                    all_broken.append(f"{rel}:{lineno}: {link} -> {reason}")

    if all_broken:
        print(f"Broken internal links ({len(all_broken)}):")
        for b in all_broken[:50]:
            print(f"  {b}")
        if len(all_broken) > 50:
            print(f"  ... and {len(all_broken) - 50} more")
        return 1
    print("Internal links: all resolve")
    return 0


if __name__ == "__main__":
    sys.exit(main())
