"""Single roster source for shared tools.

`series/agents.json` is the only list of agents and repositories. Shared
scripts import this module instead of hardcoding a repository name or a
default agent. Read-only; no imports outside the standard library.
"""
import json
import os

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
WORK = os.path.dirname(ROOT)
MANIFEST = os.path.join(ROOT, "series", "agents.json")


def entries():
    """Registry rows, or an empty list when the manifest is absent."""
    if not os.path.isfile(MANIFEST):
        return []
    with open(MANIFEST, encoding="utf-8") as fh:
        return json.load(fh).get("agents", [])


def repos(work=None):
    """Map agent id to its sibling repository path (present or not)."""
    base = work or WORK
    return {a["id"]: os.path.join(base, a["source"])
            for a in entries() if a.get("id") and a.get("source")}


def present(work=None):
    return {k: v for k, v in repos(work).items() if os.path.isdir(v)}


def entry(ident):
    for row in entries():
        if row.get("id") == ident:
            return row
    return None
