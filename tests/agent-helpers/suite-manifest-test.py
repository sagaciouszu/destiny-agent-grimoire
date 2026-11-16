#!/usr/bin/env python3
"""Guard this agent's suite manifest (tests/suites.json), the single suite
registry that tests/master-audit.sh loads at runtime.

Checks, for the invoking agent only:
  - tests/master-audit.sh loads tests/suites.json and defines no inline
    SUITES block (exactly one list exists)
  - duplicates are rejected
  - every declared tier is one of core/persona/experimental
  - suite count matches the manifest's own count field
  - suite count is at least the agent's registered baseline in lore
    series/suite-baseline.json (missing entry => template default of 18);
    additions pass

Additional suites are fine; the manifest is an additive registry.
Exit code 0 on pass, 1 on fail.
"""

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
MANIFEST = os.path.join(HERE, "suites.json")
AUDIT = os.path.join(HERE, "master-audit.sh")
TIERS = {"core", "persona", "experimental"}
BASELINE = os.path.join(REPO, "..", "lore", "series", "suite-baseline.json")
if not os.path.isfile(BASELINE):
    BASELINE = os.path.join(REPO, "lore", "series", "suite-baseline.json")


def parse_audit(path):
    text = open(path, encoding="utf-8").read()
    if "suites.json" not in text:
        # One level of indirection is allowed: master-audit.sh may source a
        # helper that loads the registry (e.g. Drifter's suites-lib.sh).
        for helper in re.findall(r'(?:source|\.)\s+"\$HERE/([^"]+)"', text):
            helper_path = os.path.join(HERE, helper)
            if os.path.isfile(helper_path):
                return parse_audit(helper_path)
        raise ValueError("master-audit.sh does not load tests/suites.json")
    if re.search(r'(?m)^\s*"[^"]+\|[^"]*"\s*,?\s*$', text):
        raise ValueError("master-audit.sh defines inline suite entries")
    return []


def main():
    try:
        manifest = json.load(open(MANIFEST, encoding="utf-8"))
    except Exception as exc:
        print(f"FAIL: cannot parse {MANIFEST}: {exc}")
        return 1

    try:
        audit = parse_audit(AUDIT)
    except Exception as exc:
        print(f"FAIL: cannot parse {AUDIT}: {exc}")
        return 1

    suites = manifest.get("suites", [])
    failures = []

    # required agent-specific fields
    if not manifest.get("agent"):
        failures.append("manifest missing agent field")
    if manifest.get("count") != len(suites):
        failures.append(
            f"manifest count {manifest.get('count')} != {len(suites)} suite entries"
        )

    names = [s.get("name") for s in suites]
    if len(set(names)) != len(names):
        failures.append("duplicate suite names in manifest")
    for i, s in enumerate(suites):
        if not s.get("name") or not s.get("command"):
            failures.append(f"suite at index {i} missing name/command")
        if s.get("tier") not in TIERS:
            failures.append(f"bad tier for {s.get('name')}: {s.get('tier')!r}")

    # master-audit.sh must load the manifest instead of duplicating it;
    # parse_audit() enforced that above, so the manifest below is the
    # single registry. Remaining checks: schema, tiers, baseline.

    # baseline coverage (if available): require lore's baseline, else template default
    agent = os.path.basename(REPO)
    minimum = 18
    if os.path.isfile(BASELINE):
        try:
            data = json.load(open(BASELINE, encoding="utf-8"))
            spec = data.get("agents", {}).get(agent)
            if spec:
                minimum = spec.get("count", minimum)
                required = set(spec.get("required", []))
                missing = required - set(names)
                if missing:
                    failures.append(f"baseline suites missing: {sorted(missing)}")
        except Exception as exc:
            print(f"  (warning: cannot read baseline {BASELINE}: {exc})")

    if len(suites) < minimum:
        failures.append(f"suite count {len(suites)} < baseline {minimum}")

    print(f"{agent}: {len(suites)} suites, baseline {minimum}")
    if failures:
        print("FAIL:")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print("manifest valid: single registry in suites.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
