#!/usr/bin/env python3
"""Combine validated per-package live-caption files into one tier.

Two filters run at this level, because they cannot be decided per package:

  * cross-package duplicate text: a table can appear in more than one globals
    package; the first package in id order keeps the line and later copies are
    dropped (caption_provenance is one row per line).
  * item-text fragments: the per-package extractor already drops containment
    matches, but a line can normalise onto a corpus item only after merge.

Input: a directory of `<package>.validated.jsonl` files.
Output: one sorted JSONL plus a JSON report.
"""
import argparse
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from containment import ContainmentIndex  # noqa: E402


def norm(text):
    text = text.lower()
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--report", required=True)
    ap.add_argument("--items-jsonl", default=None)
    args = ap.parse_args()

    index = ContainmentIndex.from_jsonl(args.items_jsonl) if args.items_jsonl else None
    files = sorted(glob.glob(os.path.join(args.dir, "*.validated.jsonl")))
    if not files:
        print("no validated files", file=sys.stderr)
        return 2

    seen = {}
    records = []
    dup, frag = {}, {}
    for path in files:
        pkg = os.path.basename(path)[:-len(".validated.jsonl")]
        for raw in open(path, encoding="utf-8"):
            rec = json.loads(raw)
            kept = []
            for line in rec.get("lines", []):
                key = norm(line.get("text", ""))
                if key in seen:
                    dup[pkg] = dup.get(pkg, 0) + 1
                    continue
                if index is not None and index.is_fragment(line.get("text", "")):
                    frag[pkg] = frag.get(pkg, 0) + 1
                    continue
                seen[key] = pkg
                kept.append(line)
            if kept:
                rec["lines"] = kept
                records.append(rec)

    records.sort(key=lambda r: (r.get("package_id", 0), r.get("bank_entry", 0),
                                r.get("kind_class") or ""))
    with open(args.out, "w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    report = {
        "packages": len(files),
        "records": len(records),
        "lines": sum(len(r["lines"]) for r in records),
        "cross_package_duplicates": dict(sorted(dup.items())),
        "item_fragments_dropped": dict(sorted(frag.items())),
    }
    with open(args.report, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1, sort_keys=True)
    print(json.dumps({k: report[k] for k in ("packages", "records", "lines")}))
    print("duplicates:", sum(dup.values()), " fragments:", sum(frag.values()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
