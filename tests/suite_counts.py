#!/usr/bin/env python3
"""Report the current check counts printed by the shared verification suites.

The count comes from each suite's own scorecard, not a hand-maintained constant.
Missing optional environments (such as the MCP virtualenv) return None and are
skipped by documentation sync.

Usage: python3 tests/suite_counts.py [--json]
"""
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# (label, command, scorecard regex). Count-valued suites capture the total from
# "Passed: N | Failed: M". Fraction-valued suites capture both values.
SUITES = [
    ("Database integrity", ["bash", os.path.join(HERE, "test-db.sh")],
     r"Passed: (\d+) \| Failed: (\d+)"),
    ("Query interface", ["bash", os.path.join(HERE, "query-interface-test.sh")],
     r"Passed: (\d+) \| Failed: (\d+)"),
    ("Agent layout", ["bash", os.path.join(HERE, "agent-layout-test.sh")],
     r"Passed: (\d+) \| Failed: (\d+)"),
    ("Cutscene captions", ["bash", os.path.join(HERE, "cutscene-verify.sh")],
     r"Passed: (\d+)/(\d+)"),
    ("MCP contract", [os.path.join(ROOT, "mcp-server", ".venv", "bin", "python"),
                       os.path.join(HERE, "mcp-test.py")],
     r"Passed: (\d+) \| Failed: (\d+)"),
    ("MCP agent optimisation", [os.path.join(ROOT, "mcp-server", ".venv", "bin", "python"),
                                os.path.join(HERE, "mcp-agent-optimization-test.py")],
     r"Passed: (\d+) \| Failed: (\d+)"),
]

# In single-repository CI the layout test uses a dummy 2-agent registry and
# reports 24 checks. The full workspace has 108; do not sync the dummy count.
CI_DUMMY_LAYOUT = 24


def run_suite(label, command, pattern):
    try:
        result = subprocess.run(command, capture_output=True, text=True,
                                timeout=900, cwd=ROOT)
    except (OSError, subprocess.TimeoutExpired):
        return None
    match = re.search(pattern, result.stdout)
    if not match:
        return None
    passed, second = map(int, match.groups())
    if label == "Agent layout" and os.environ.get("CI") and passed == CI_DUMMY_LAYOUT:
        return None
    if label in ("Cutscene captions", "MCP contract"):
        return (passed, second if label == "Cutscene captions" else passed + second)
    # For ordinary suites the total is passed + failed; it remains useful even
    # if a specific assertion fails while the documentation count is refreshed.
    return passed + second


def suite_counts():
    return {label: run_suite(label, command, pattern)
            for label, command, pattern in SUITES}


def main():
    counts = suite_counts()
    if "--json" in sys.argv:
        print(json.dumps(counts, indent=2, sort_keys=True))
        return 0
    for label, count in sorted(counts.items()):
        print(f"  {'-' if count is None else '✓'} {label}: {count if count is not None else 'skipped'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
