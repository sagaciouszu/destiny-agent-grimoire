#!/usr/bin/env python3
"""Merge extracted Tiger package layers into one mounted view.

A Destiny package family ships as a base (`_0`) plus one or more patch layers
(`_1`, `_2`, ...). The game mounts them in order: a patch entry replaces the
base entry with the same entry index. The class suffix is part of the entry
identity, so a patch can also *replace the class* of an entry; the base file
is then stale and must be removed rather than overlaid.

Usage:
    python3 scripts/merge-pkg-layers.py \
        --base  /opt/vault/.../out-w64_sr_globals_0294_0 \
        --patch /opt/vault/.../out-w64_sr_globals_0294_1 \
        --out   /opt/vault/.../out-w64_sr_globals_0294_merged

Output: a directory with the mounted view plus a JSON report on stdout
(`added`, `overlaid`, `class_replaced`, `files`).
"""
import argparse
import json
import os
import shutil


def entry_of(name):
    return name.split("_", 1)[0]


def files_by_entry(directory):
    out = {}
    for name in os.listdir(directory):
        out.setdefault(entry_of(name), []).append(name)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--patch", action="append", default=[],
                    help="patch layer directory, in mount order (repeatable)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--report", help="write the JSON report here")
    args = ap.parse_args()

    if os.path.exists(args.out):
        shutil.rmtree(args.out)
    shutil.copytree(args.base, args.out, copy_function=shutil.copy2)

    report = {"added": 0, "overlaid": 0, "class_replaced": 0, "files": 0}
    for patch in args.patch:
        current = files_by_entry(args.out)
        for name in sorted(os.listdir(patch)):
            entry = entry_of(name)
            existing = current.get(entry, [])
            src = os.path.join(patch, name)
            dst = os.path.join(args.out, name)
            if not existing:
                shutil.copy2(src, dst)
                report["added"] += 1
            elif name in existing:
                shutil.copy2(src, dst)
                report["overlaid"] += 1
            else:
                # The patch changed the entry's class. Remove the stale base
                # entry; the patch file becomes the current truth.
                for old in existing:
                    os.remove(os.path.join(args.out, old))
                shutil.copy2(src, dst)
                report["class_replaced"] += 1
            current[entry] = [name]

    report["files"] = len(os.listdir(args.out))
    text = json.dumps(report, indent=1, sort_keys=True)
    print(text)
    if args.report:
        with open(args.report, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")


if __name__ == "__main__":
    main()
