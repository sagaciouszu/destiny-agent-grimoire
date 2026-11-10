#!/usr/bin/env python3
"""Refresh the live-build caption tier from a new game build.

The sequence is the one used by hand for build-25932352:

  source build -> unpack every w64_sr_globals layer -> merge layers ->
  resolve locales -> extract English -> validate language -> combine ->
  drift report -> register build -> rebuild -> gates

A new build is written to `archive/data/live-builds/<build>.jsonl` with
build-scoped slugs. The current build stays in `archive/data/captions-live.jsonl`;
a changed line becomes a new `caption_sightings` row, never an inline rewrite.

Safety:
  * running against the registered current build is a no-op;
  * `--dry-run` prints the plan and writes nothing;
  * the source tree is never modified;
  * `--self-test` exercises the drift report without a real build.

Usage:
  python3 scripts/refresh-live-build.py --source /path/to/build-25932352 --dry-run
  python3 scripts/refresh-live-build.py --source /path/to/build-26000001 \
      --version 245114.27.01.01.0000.v500_live.main
  python3 scripts/refresh-live-build.py --self-test
"""
import argparse
import datetime
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BUILDS = os.path.join(ROOT, "archive", "data", "builds.json")
LIVE_DIR = os.path.join(ROOT, "archive", "data", "live-builds")
CURRENT_LIVE = os.path.join(ROOT, "archive", "data", "captions-live.jsonl")
VAULT = "/opt/vault/d2-bl-extract"
UNPACK = "/opt/vault/d2extraction/tiger-pkg/target/release/examples/unpack"
OODLE_CWD = os.path.join(VAULT, "temp", "oodle")
DEFAULT_WORK = os.path.join(VAULT, "temp", "refresh")

GATES = [
    ["python3", "db/migrate.py"],
    ["python3", "db/enrich_lore.py"],
    ["python3", "db/enrich_manifest.py"],
    ["python3", "db/enrich_seals.py"],
    ["python3", "db/enrich_itemsets.py", "--apply"],
    ["python3", "scripts/apply-queen-fold.py"],
    ["python3", "db/build_entity_web.py", "--db", "db/grimoire.db"],
    ["bash", "grimoire-master-audit.sh"],
]


def norm(text):
    text = text.lower()
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def run(cmd, cwd=None, check=True):
    print("+", " ".join(cmd))
    return subprocess.run(cmd, cwd=cwd, check=check)


def registered_builds():
    if not os.path.exists(BUILDS):
        return []
    return json.load(open(BUILDS, encoding="utf-8"))


def latest_live_build(rows):
    live = [r["build_id"] for r in rows if r.get("kind") == "game_build"
            and r["build_id"].startswith("build-")]
    return live[-1] if live else None


def source_build_id(source, explicit):
    if explicit:
        return explicit if explicit.startswith("build-") else f"build-{explicit}"
    match = re.fullmatch(r"build-(\d+)", os.path.basename(source.rstrip("/")))
    if match:
        return f"build-{match.group(1)}"
    raise SystemExit("cannot infer build id from the source path; pass --build-id")


def tier_lines(path):
    lines = {}
    if not os.path.exists(path):
        return lines
    for raw in open(path, encoding="utf-8"):
        rec = json.loads(raw)
        package = rec.get("source_url", "")
        for line in rec.get("lines", []):
            text = (line.get("text") or "").strip()
            if text:
                lines[(package, norm(text))] = text
    return lines


def drift_report(old_path, new_path, old_build, new_build):
    old = tier_lines(old_path)
    new = tier_lines(new_path)
    added = [new[k] for k in new.keys() - old.keys()]
    removed = [old[k] for k in old.keys() - new.keys()]
    return {
        "old_build": old_build,
        "new_build": new_build,
        "old_lines": len(old),
        "new_lines": len(new),
        "added": len(added),
        "removed": len(removed),
        "added_samples": added[:50],
        "removed_samples": removed[:50],
    }


def self_test():
    with tempfile.TemporaryDirectory(prefix="refresh-selftest-") as tmp:
        old = os.path.join(tmp, "old.jsonl")
        new = os.path.join(tmp, "new.jsonl")
        base = {"kind": "caption", "slug": "x", "source_url": "pkg:p#1",
                "source_build": "build-old", "bank_entry": 1, "kind_class": "narration"}
        with open(old, "w", encoding="utf-8") as fh:
            fh.write(json.dumps({**base, "lines": [
                {"text": "The old line.", "speaker": None, "record_index": 0,
                 "record_part": 0}]}) + "\n")
        with open(new, "w", encoding="utf-8") as fh:
            fh.write(json.dumps({**base, "source_build": "build-new", "lines": [
                {"text": "The new line.", "speaker": None, "record_index": 0,
                 "record_part": 0}]}) + "\n")
        report = drift_report(old, new, "build-old", "build-new")
        assert report["added"] == 1 and report["removed"] == 1, report
        assert "The new line." in report["added_samples"], report
        assert "The old line." in report["removed_samples"], report
    print("self-test: drift report names the changed line")
    return 0


def package_layers(source):
    packages_dir = os.path.join(source, "packages")
    if not os.path.isdir(packages_dir):
        packages_dir = source
    files = sorted(glob.glob(os.path.join(packages_dir, "w64_sr_globals_*.pkg")))
    families = {}
    for path in files:
        name = os.path.basename(path)[:-4]
        family = re.sub(r"_\d+$", "", name)
        families.setdefault(family, []).append(path)
    for family in families:
        families[family].sort(key=lambda p: int(p.rsplit("_", 1)[1][:-4]))
    return families


def write_map(work, package, package_id, resolver_path, build_id):
    resolution = json.load(open(resolver_path, encoding="utf-8"))
    map_path = os.path.join(work, "maps", f"{package}.json")
    os.makedirs(os.path.dirname(map_path), exist_ok=True)
    payload = {
        "build_id": build_id,
        "package": package,
        "package_id": package_id,
        "en_entries": resolution.get("en_entries", []),
        "resolution": {
            "confidence": resolution.get("confidence"),
            "tables_detected": resolution.get("tables_detected"),
            "tables_verified": resolution.get("tables_verified"),
            "skipped_blocks": resolution.get("skipped_blocks", []),
            "rejected_non_english": resolution.get("rejected_non_english", []),
        },
    }
    with open(map_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1)
    return map_path, payload


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", help="build tree containing packages/")
    ap.add_argument("--build-id")
    ap.add_argument("--version", default="unknown")
    ap.add_argument("--work", default=DEFAULT_WORK)
    ap.add_argument("--report", help="drift report path")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true",
                    help="re-run even if this build is already registered")
    ap.add_argument("--skip-gates", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if not args.source:
        ap.error("--source is required unless --self-test")

    build = source_build_id(args.source, args.build_id)
    rows = registered_builds()
    current = latest_live_build(rows)
    if build == current and not args.force:
        print(f"current build already registered: {build} (no-op)")
        return 0
    if not os.path.isdir(args.source):
        raise SystemExit(f"source not found: {args.source}")
    families = package_layers(args.source)
    if not families:
        raise SystemExit(f"no w64_sr_globals packages under {args.source}")

    work = os.path.join(args.work, build)
    report_path = args.report or os.path.join(
        VAULT, "reports", f"live-refresh-{build}.json")
    print(f"refresh {current or 'none'} -> {build}")
    print(f"source: {args.source} ({len(families)} families)")

    if args.dry_run:
        for family, layers in sorted(families.items()):
            print(f"  {family}: unpack {len(layers)} layer(s), merge, resolve, extract")
        print(f"  combine -> {os.path.join(LIVE_DIR, build + '.jsonl')}")
        print(f"  drift report -> {report_path}")
        print(f"  register {build} in {BUILDS}")
        print("  rebuild + gates" if not args.skip_gates else "  rebuild (gates skipped)")
        print("dry-run: nothing written")
        return 0

    for path in ("captions", "validated", "maps", "merged"):
        os.makedirs(os.path.join(work, path), exist_ok=True)
    os.makedirs(LIVE_DIR, exist_ok=True)

    validated_dir = os.path.join(work, "validated")
    for family, layers in sorted(families.items()):
        package_id = int(family.rsplit("_", 1)[1], 16)
        unpacked = []
        for layer in layers:
            out = os.path.join(work, "unpacked", os.path.basename(layer)[:-4])
            run([UNPACK, layer, "-v", "d2_ren", "-o", out, "-s"], cwd=OODLE_CWD)
            unpacked.append(out)
        merged = os.path.join(work, "merged", family)
        merge_cmd = ["python3", os.path.join(HERE, "merge-pkg-layers.py"),
                     "--base", unpacked[0], "--out", merged]
        for patch in unpacked[1:]:
            merge_cmd += ["--patch", patch]
        run(merge_cmd, cwd=ROOT)
        resolver = os.path.join(work, "maps", f"{family}.resolver.json")
        run(["python3", os.path.join(HERE, "resolve-locales.py"), merged,
             "--out", resolver], cwd=ROOT)
        map_path, payload = write_map(work, family, package_id, resolver, build)
        if not payload["en_entries"]:
            print(f"  skip {family}: resolver found no English entries")
            continue
        out_jsonl = os.path.join(work, "captions", f"{family}.jsonl")
        stats = os.path.join(work, "captions", f"{family}.stats.json")
        run(["python3", os.path.join(HERE, "extract-live-captions.py"),
             "--dir", merged, "--locale-map", map_path, "--out", out_jsonl,
             "--stats", stats, "--build-scoped-slug"], cwd=ROOT)
        run(["python3", os.path.join(HERE, "validate-live-language.py"),
             "--in", out_jsonl,
             "--out", os.path.join(validated_dir, f"{family}.validated.jsonl"),
             "--report", os.path.join(work, "captions", f"{family}.language.json")],
            cwd=ROOT, check=False)

    combined = os.path.join(LIVE_DIR, f"{build}.jsonl")
    run(["python3", os.path.join(HERE, "combine-live-captions.py"),
         "--dir", validated_dir, "--out", combined,
         "--report", os.path.join(work, "combined.json"),
         "--items-jsonl", os.path.join(ROOT, "archive", "data", "items.jsonl")],
        cwd=ROOT)

    report = drift_report(CURRENT_LIVE, combined, current or "none", build)
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1)
    print(f"drift: +{report['added']} / -{report['removed']} -> {report_path}")

    if build not in [r["build_id"] for r in rows]:
        pkg_files = glob.glob(os.path.join(args.source, "packages", "*.pkg"))
        if not pkg_files:
            pkg_files = glob.glob(os.path.join(args.source, "*.pkg"))
        rows.append({
            "build_id": build,
            "label": f"Destiny 2 live client ({build})",
            "kind": "game_build",
            "version": args.version,
            "source": "private extraction vault (not distributed)",
            "captured_at": datetime.date.today().isoformat(),
            "package_count": len(pkg_files) or None,
            "byte_count": sum(os.path.getsize(p) for p in pkg_files) or None,
            "notes": f"Added by scripts/refresh-live-build.py from {args.source}.",
        })
        with open(BUILDS, "w", encoding="utf-8") as fh:
            json.dump(rows, fh, indent=1)
            fh.write("\n")
        print(f"registered {build} in {BUILDS}")

    if not args.skip_gates:
        for cmd in GATES:
            run(cmd, cwd=ROOT)
    print(f"refresh complete: {build}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
