#!/usr/bin/env python3
"""README quality gate for the Destiny agent series.

Checks every roster README against the onboarding contract:
required sections in order, a per-agent intro, a verified-quote demo,
wiki links that resolve, tier budgets that match AGENTS.md, a current
Last push date, a 200-line cap and an honest Token Estimate.

Read-only. Exit 1 on violations.
"""

import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
WORK = os.path.dirname(ROOT)
WIKI = os.path.join(WORK, "destiny-agent-grimoire.wiki")

REQUIRED_H2 = [
    "## What it sounds like",
    "## Quick start for Guardians",
    "## Requirements",
    "## Connect it",
    "## For agents",
    "## Repository layout",
    "## Verification",
    "## Troubleshooting",
    "## License and attribution",
]

MAX_LINES = 200
INTRO_MIN = 120


def roster():
    with open(os.path.join(ROOT, "series", "agents.json"), encoding="utf-8") as fh:
        return json.load(fh)["agents"]


def headings(text):
    return [line.strip() for line in text.splitlines() if line.startswith("## ")]


def intro(text):
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if "Token Estimate:" in line:
            start = i + 1
            break
    if start is None:
        return ""
    out = []
    for line in lines[start:]:
        if line.startswith("## "):
            break
        if line.strip():
            out.append(line.strip())
    return " ".join(out)


def budget(text, tier):
    m = re.search(r"^\| " + tier + r" \|.*?~([\d.]+)K", text, re.M)
    return m.group(1) if m else None


def last_push(text):
    m = re.search(r"\*\*Last push:\*\* (\d{4}-\d{2}-\d{2})", text)
    return m.group(1) if m else None


def token_estimate(text):
    m = re.search(r"Token Estimate:\*\* ~([\d.]+)K", text)
    return float(m.group(1)) if m else None


def head_date(repo):
    try:
        return subprocess.run(
            ["git", "-C", repo, "log", "-1", "--format=%cs"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def check(agent):
    repo = os.path.join(WORK, agent["source"])
    readme = os.path.join(repo, "README.md")
    if not os.path.exists(readme):
        return [f"missing README.md"]
    text = open(readme, encoding="utf-8").read()
    bad = []

    have = headings(text)
    pos = -1
    for want in REQUIRED_H2:
        if want not in have:
            bad.append(f"missing section: {want}")
            continue
        at = have.index(want)
        if at < pos:
            bad.append(f"section out of order: {want}")
        pos = at

    body = intro(text)
    if len(body) < INTRO_MIN:
        bad.append(f"intro too short ({len(body)} chars)")
    tokens = [t for t in re.split(r"[^A-Za-z0-9]+", agent["name"]) if len(t) >= 4]
    if tokens and not any(t.lower() in body.lower() for t in tokens):
        bad.append("intro does not name the character")

    demo = [
        l
        for l in text.splitlines()
        if re.match(r"^> \*\*.+:\*\* ", l)
        and not re.match(r"^> \*\*(Depends On|Token Estimate):\*\*", l)
    ]
    if len(demo) < 3:
        bad.append(f"demo has {len(demo)} quoted lines, need 3")
    if "sagaciouszu.github.io/destiny-agent-grimoire-site/personas/" not in text:
        bad.append("demo lacks a persona-page link")

    links = re.findall(
        r"github\.com/sagaciouszu/destiny-agent-grimoire/wiki/([A-Za-z0-9._-]+)",
        text,
    )
    if not links:
        bad.append("no grimoire wiki link")
    for page in links:
        if not os.path.exists(os.path.join(WIKI, page + ".md")):
            bad.append(f"wiki link target missing: {page}.md")

    agents_md = os.path.join(repo, "AGENTS.md")
    if os.path.exists(agents_md):
        other = open(agents_md, encoding="utf-8").read()
        for tier in ("Core", "Task-loaded"):
            mine, theirs = budget(text, tier), budget(other, tier)
            if mine != theirs:
                bad.append(f"{tier} budget {mine} != AGENTS.md {theirs}")

    claimed, actual = last_push(text), head_date(repo)
    if not claimed:
        bad.append("no Last push date")
    elif actual and claimed != actual:
        bad.append(f"Last push {claimed} != HEAD {actual}")

    lines = len(text.splitlines())
    if lines > MAX_LINES:
        bad.append(f"{lines} lines, cap {MAX_LINES}")

    est = token_estimate(text)
    if est is None:
        bad.append("no Token Estimate")
    else:
        measured = len(text) / 4 / 1000
        if abs(measured - est) / est > 0.25:
            bad.append(f"Token Estimate ~{est}K vs measured ~{measured:.1f}K")

    return bad


def main():
    problems = []
    intros = {}
    for agent in roster():
        bad = check(agent)
        for item in bad:
            problems.append(f"{agent['source']}: {item}")
        repo = os.path.join(WORK, agent["source"])
        readme = os.path.join(repo, "README.md")
        if os.path.exists(readme):
            key = " ".join(intro(open(readme, encoding="utf-8").read()).lower().split())
            if key:
                intros.setdefault(key, []).append(agent["source"])
    for key, repos in intros.items():
        if len(repos) > 1:
            problems.append(f"duplicate intro: {', '.join(repos)}")

    if problems:
        for item in problems:
            print(f"  FAIL: {item}")
        print(f"\nREADME QUALITY: {len(problems)} violation(s)")
        return 1
    print(f"README QUALITY: PASS ({len(roster())}/{len(roster())} agent READMEs)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
