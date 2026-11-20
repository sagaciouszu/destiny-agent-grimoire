#!/usr/bin/env python3
"""README quality gate for the Destiny agent series.

Checks every roster README against the onboarding contract:
required sections in order, a per-agent intro (unique at sentence level),
a demo whose speaker labels are canonical and whose lines verify against
the archive, wiki links that resolve, tier budgets that match AGENTS.md,
a current Last push date, a 200-line cap, an honest Token Estimate,
repository-layout counts that match the tree, and suite counts that match
tests/suites.json.

Read-only. Exit 1 on violations. `--self-test` runs a good and a bad
fixture through the same checks without touching a repo.
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
DEMO_RE = re.compile(r'^> \*\*(?P<who>[^*]+):\*\* "(?P<line>.+)"\s*$')


def roster():
    with open(os.path.join(ROOT, "series", "agents.json"), encoding="utf-8") as fh:
        return json.load(fh)["agents"]


def strip_fences(text):
    out = []
    fenced = False
    for line in text.splitlines():
        if line.strip().startswith("```"):
            fenced = not fenced
            continue
        if not fenced:
            out.append(line)
    return "\n".join(out)


def headings(text):
    return [
        line.strip()
        for line in strip_fences(text).splitlines()
        if line.startswith("## ")
    ]


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


def sentences(text):
    return [s for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def normalize(text):
    return " ".join(re.findall(r"[a-z0-9']+", text.lower()))


def budget(text, tier):
    m = re.search(r"^\| " + tier + r" \|.*?~([\d.]+)K", text, re.M)
    return m.group(1) if m else None


def last_push(text):
    m = re.search(r"\*\*Last push:\*\* (\d{4}-\d{2}-\d{2})", text)
    return m.group(1) if m else None


def token_estimate(text):
    m = re.search(r"Token Estimate:\*\* ~([\d.]+)(K?)", text)
    if not m:
        return None
    value = float(m.group(1))
    return value if m.group(2) == "K" else value / 1000.0


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


def layout_claims(text):
    claims = {}
    for m in re.finditer(r"^(core|voice|world|reference)/\s+#\s+(\d+)", text, re.M):
        claims[m.group(1)] = int(m.group(2))
    return claims


def actual_counts(repo):
    def count(sub, suffix, exclude_template=False):
        path = os.path.join(repo, sub)
        if not os.path.isdir(path):
            return None
        total = 0
        for name in os.listdir(path):
            if not os.path.isfile(os.path.join(path, name)):
                continue
            if suffix and not name.endswith(suffix):
                continue
            if exclude_template and name.endswith(".template.md"):
                continue
            total += 1
        return total

    return {
        "core": count("core", ".md", exclude_template=True),
        "voice": count("voice", ".md"),
        "world": count("world", ".md"),
        "reference": count("reference", None),
    }


def suite_drift(repo):
    readme = os.path.join(repo, "tests", "README.md")
    manifest = os.path.join(repo, "tests", "suites.json")
    if not (os.path.exists(readme) and os.path.exists(manifest)):
        return []
    try:
        want = json.load(open(manifest, encoding="utf-8")).get("count")
    except ValueError:
        return [f"{os.path.relpath(manifest, WORK)} is not valid JSON"]
    if want is None:
        return []
    text = open(readme, encoding="utf-8").read()
    bad = []
    for m in re.finditer(r"(?:records the|full gate:)\s*(\d+)\s+suites", text):
        if int(m.group(1)) != want:
            bad.append(
                f"tests/README.md says {m.group(1)} suites, suites.json says {want}"
            )
    return bad


def verify_quote(line, speaker):
    result = subprocess.run(
        [
            sys.executable,
            os.path.join(ROOT, "db", "query.py"),
            "verify",
            line,
            "--speaker",
            speaker,
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def check_text(text, agent, repo=None, verify_quotes=True):
    """Return a list of violations for one README body."""
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

    demo = []
    for line in text.splitlines():
        m = DEMO_RE.match(line)
        if m:
            demo.append((m.group("who").strip(), m.group("line").strip()))
    if len(demo) < 3:
        bad.append(f"demo has {len(demo)} quoted lines, need 3")
    speaker = agent.get("speaker")
    for who, line in demo:
        if who.lower() == "you":
            bad.append(f"demo line attributed to You: {line[:40]}")
            continue
        if speaker and who != speaker:
            bad.append(f"demo speaker {who!r} != canonical {speaker!r}")
        elif verify_quotes and not verify_quote(line, who):
            bad.append(f"demo quote not canon: {line[:60]}")

    if f"personas/{agent['id']}/" not in text:
        bad.append(f"no persona link for id {agent['id']!r}")
    if f"try/{agent['id']}/" not in text:
        bad.append(f"no try link for id {agent['id']!r}")

    links = re.findall(
        r"github\.com/sagaciouszu/destiny-agent-grimoire/wiki/([A-Za-z0-9._-]+)",
        text,
    )
    if not links:
        bad.append("no grimoire wiki link")
    for page in links:
        if not os.path.exists(os.path.join(WIKI, page + ".md")):
            bad.append(f"wiki link target missing: {page}.md")

    if repo:
        agents_md = os.path.join(repo, "AGENTS.md")
        if os.path.exists(agents_md):
            other = open(agents_md, encoding="utf-8").read()
            for tier in ("Core", "Task-loaded"):
                mine, theirs = budget(text, tier), budget(other, tier)
                if mine is None or theirs is None:
                    bad.append(
                        f"{tier} budget missing (README {mine}, AGENTS.md {theirs})"
                    )
                elif mine != theirs:
                    bad.append(f"{tier} budget {mine} != AGENTS.md {theirs}")

        claimed, actual = last_push(text), head_date(repo)
        if not claimed:
            bad.append("no Last push date")
        elif actual is None:
            bad.append("cannot read HEAD date (is this a git repo?)")
        elif claimed != actual:
            bad.append(f"Last push {claimed} != HEAD {actual}")

        claims = layout_claims(text)
        counts = actual_counts(repo)
        for name, claimed_count in claims.items():
            actual_count = counts.get(name)
            if actual_count is not None and claimed_count != actual_count:
                bad.append(
                    f"layout {name}/ claims {claimed_count}, tree has {actual_count}"
                )

        bad.extend(suite_drift(repo))

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


def check(agent):
    repo = os.path.join(WORK, agent["source"])
    readme = os.path.join(repo, "README.md")
    if not os.path.exists(readme):
        return ["missing README.md"]
    return check_text(open(readme, encoding="utf-8").read(), agent, repo=repo)


def shared_sentences(entries):
    """Intro sentences of 8+ words that appear in more than one repo."""
    seen = {}
    for agent, text in entries:
        for sentence in sentences(intro(text)):
            words = normalize(sentence).split()
            if len(words) < 8:
                continue
            seen.setdefault(" ".join(words), set()).add(agent["source"])
    return [(key, sorted(repos)) for key, repos in seen.items() if len(repos) > 1]


def self_test():
    agent = {
        "id": "selftest",
        "name": "Selftest",
        "source": "selftest",
        "speaker": "Selftest",
    }
    good = """# Selftest - Agent

> **Depends On:** AGENTS.md
> **Token Estimate:** ~9.9K tokens

Selftest is a synthetic character used only to prove the README gate.
This fixture carries every required section, a three-line demo and links
that resolve against the real wiki directory.

## What it sounds like

> **You:** Say something.
> **Selftest:** "A first line."
> **Selftest:** "A second line."
> **Selftest:** "A third line."

Play the full scene: [persona page](https://sagaciouszu.github.io/destiny-agent-grimoire-site/personas/selftest/)
and [interactive demo](https://sagaciouszu.github.io/destiny-agent-grimoire-site/try/selftest/).

## Quick start for Guardians

Run the setup script.

## Requirements

Python 3 and git.

## Connect it

See [Troubleshooting](https://github.com/sagaciouszu/destiny-agent-grimoire/wiki/Troubleshooting).

## For agents

Load the core tier first.

## Repository layout

Plain markdown.

## Verification

Run the suites.

## Troubleshooting

Ask the archive.

## License and attribution

MIT.
"""
    est = round(len(good) / 4 / 1000, 1)
    good = good.replace("~9.9K", f"~{est}K")
    good_bad = check_text(good, agent, verify_quotes=False)
    if good_bad:
        print("SELF-TEST FAIL: good fixture was rejected:")
        for item in good_bad:
            print(f"  {item}")
        return 1

    bad = good.replace("## What it sounds like", "## Sounds")
    bad = bad.replace('> **Selftest:** "A first line."', '> **You:** "A first line."')
    bad = bad.replace("personas/selftest/", "personas/other/")
    bad = bad.replace(
        "https://github.com/sagaciouszu/destiny-agent-grimoire/wiki/Troubleshooting",
        "https://github.com/sagaciouszu/destiny-agent-grimoire/wiki/No-Such-Page",
    )
    bad_bad = check_text(bad, agent, verify_quotes=False)
    if len(bad_bad) < 3:
        print("SELF-TEST FAIL: bad fixture passed or was under-reported:")
        for item in bad_bad:
            print(f"  {item}")
        return 1
    print(f"SELF-TEST: PASS (good 0 violations, bad {len(bad_bad)} violations)")
    return 0


def main(argv):
    if "--self-test" in argv:
        return self_test()

    problems = []
    entries = []
    for agent in roster():
        bad = check(agent)
        for item in bad:
            problems.append(f"{agent['source']}: {item}")
        repo = os.path.join(WORK, agent["source"])
        readme = os.path.join(repo, "README.md")
        if os.path.exists(readme):
            entries.append((agent, open(readme, encoding="utf-8").read()))

    for key, repos in shared_sentences(entries):
        problems.append(
            f"shared intro sentence across {', '.join(repos)}: {key[:70]}..."
        )

    if problems:
        for item in problems:
            print(f"  FAIL: {item}")
        print(f"\nREADME QUALITY: {len(problems)} violation(s)")
        return 1
    print(f"README QUALITY: PASS ({len(roster())}/{len(roster())} agent READMEs)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
