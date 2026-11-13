#!/usr/bin/env python3
"""Fail if agent test fixtures embed long verbatim transcript lines.

The source text is read from the local DB and compared in memory only. Output
contains file/field locations, never matched canon text.
"""
import ast
import json
import os
import re
import shlex
import sqlite3
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
WORK = os.path.dirname(ROOT)
DB = os.environ.get("GRIMOIRE_DB") or os.path.join(ROOT, "db", "grimoire.db")
MIN_CHARS = 40
MIN_WORDS = 6
GRAM_WORDS = 6

sys.path.insert(0, os.path.join(ROOT, "db"))
import api  # noqa: E402
sys.path.insert(0, HERE)
import _roster  # noqa: E402


def _strings(path):
    """Yield (location, string) pairs from test-source formats."""
    text = open(path, encoding="utf-8", errors="ignore").read()
    suffix = os.path.splitext(path)[1].lower()
    if suffix == ".json":
        try:
            root = json.loads(text)
        except json.JSONDecodeError:
            return

        def walk(value, location="$"):
            if isinstance(value, str):
                yield location, value
            elif isinstance(value, dict):
                for key, child in value.items():
                    yield from walk(child, location + "." + str(key))
            elif isinstance(value, list):
                for index, child in enumerate(value):
                    yield from walk(child, f"{location}[{index}]")

        yield from walk(root)
        return
    if suffix == ".py":
        for number, line in enumerate(text.splitlines(), 1):
            yield str(number), line
        try:
            tree = ast.parse(text, filename=path)
        except SyntaxError:
            return
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                yield str(getattr(node, "lineno", 0)), node.value
        return
    if suffix == ".sh":
        for number, line in enumerate(text.splitlines(), 1):
            yield str(number), line
            if line.lstrip().startswith("#"):
                continue
            try:
                for value in shlex.split(line, comments=True):
                    yield str(number), value
            except ValueError:
                continue
        return
    if suffix in (".md", ".txt", ".yml", ".yaml"):
        for number, line in enumerate(text.splitlines(), 1):
            yield str(number), line


def _fixture_roots():
    roots = [(name, path) for name, path in _roster.repos(WORK).items()]
    template = os.path.join(WORK, "destiny-agent-template")
    if os.path.isdir(template):
        roots.append(("template", template))
    return roots


def _source_index(conn):
    index = defaultdict(set)
    count = 0
    for (line,) in conn.execute(
            "SELECT line FROM transcript_lines WHERE line IS NOT NULL"):
        normalized = api.norm(line)
        words = normalized.split()
        if len(normalized) < MIN_CHARS or len(words) < MIN_WORDS:
            continue
        index[tuple(words[:GRAM_WORDS])].add(normalized)
        count += 1
    return index, count


def _has_canon_substring(value, index):
    normalized = api.norm(value)
    words = normalized.split()
    if len(normalized) < MIN_CHARS or len(words) < MIN_WORDS:
        return False
    for start in range(len(words) - GRAM_WORDS + 1):
        prefix = tuple(words[start:start + GRAM_WORDS])
        if any(canon_line in normalized for canon_line in index.get(prefix, ())):
            return True
    return False


def scan():
    """Return (files, strings, source_lines, hits) without exposing text."""
    if not os.path.isfile(DB):
        return 0, 0, 0, []
    conn = sqlite3.connect("file:{}?mode=ro".format(
        os.path.abspath(DB)), uri=True)
    try:
        index, source_lines = _source_index(conn)
    finally:
        conn.close()

    files_scanned = strings_scanned = 0
    hits = set()
    for agent, repo in _fixture_roots():
        if agent == "grimoire":
            continue
        test_roots = [os.path.join(repo, "tests")]
        if agent == "template":
            test_roots.append(os.path.join(repo, "template", "tests"))
        for test_root in test_roots:
            if not os.path.isdir(test_root):
                continue
            for directory, dirs, names in os.walk(test_root):
                dirs[:] = [d for d in dirs if d not in
                           (".git", "__pycache__", ".venv", "node_modules", "lore")]
                for name in names:
                    if not name.endswith((".json", ".py", ".sh", ".md", ".txt",
                                          ".yml", ".yaml")):
                        continue
                    path = os.path.join(directory, name)
                    files_scanned += 1
                    rel = os.path.relpath(path, WORK).replace(os.sep, "/")
                    for location, value in _strings(path):
                        strings_scanned += 1
                        if _has_canon_substring(value, index):
                            hits.add((rel, location))
    return files_scanned, strings_scanned, source_lines, sorted(hits)


def main():
    if not os.path.isfile(DB):
        print(f"fixture canon guard: SKIP (database not present at {DB})")
        return 0
    files, strings, source_lines, hits = scan()
    if hits:
        print(f"FIXTURE CANON GUARD FAIL: {len(hits)} possible long verbatim match(es)")
        for path, location in hits[:40]:
            print(f"  {path}:{location}")
        return 1
    print(f"fixture canon guard: PASS ({files} files, {strings} strings, "
          f"{source_lines} long source lines; no matches)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
