#!/usr/bin/env python3
"""Mirror a source tree into a destination, cross-platform.

Replacement for the `rsync -a --delete --exclude ...` calls in
`scripts/sync-live-agents.sh`, so agent sync works on Windows (no rsync) as
well as Unix.

Usage:
    python3 scripts/mirror-tree.py [--delete] [--dry-run] \
        [--exclude PATTERN]... SRC/ DST/

Exclude patterns follow rsync's simple semantics used by the sync script:
a bare name (`.git`, `USER.md`) matches that path component anywhere, a
pattern ending in `/` (`memory/`) matches a directory of that name anywhere,
and a path (`core/journal.md`) matches from the destination root.
Excluded destination files are never deleted by `--delete`.
"""
import argparse
import os
import shutil
import stat
import sys


def normalize(pattern):
    p = pattern.strip()
    while p.startswith('./'):
        p = p[2:]
    return p


def is_excluded(rel, patterns):
    parts = rel.split(os.sep)
    for raw in patterns:
        pat = normalize(raw)
        if not pat:
            continue
        if pat.endswith('/'):
            name = pat.rstrip('/')
            if name in parts:
                return True
        elif '/' in pat:
            if rel == pat or rel.startswith(pat + os.sep):
                return True
        else:
            if pat in parts:
                return True
    return False


def on_rm_error(func, path, _exc):
    """Windows marks some files read-only; clear and retry."""
    os.chmod(path, stat.S_IWRITE | stat.S_IREAD)
    func(path)


def mirror(src, dst, patterns, delete, dry):
    src = os.path.abspath(src)
    dst = os.path.abspath(dst)
    if not os.path.isdir(src):
        raise SystemExit(f'source missing: {src}')
    actions = {'copied': 0, 'removed': 0, 'skipped': 0}
    for root, dirs, files in os.walk(src):
        rel_root = os.path.relpath(root, src)
        # Prune excluded directories in place so os.walk does not descend.
        keep = []
        for d in dirs:
            rel = os.path.normpath(os.path.join(rel_root, d)) if rel_root != '.' else d
            if is_excluded(rel, patterns):
                actions['skipped'] += 1
            else:
                keep.append(d)
        dirs[:] = keep
        target_root = dst if rel_root == '.' else os.path.join(dst, rel_root)
        if not dry:
            os.makedirs(target_root, exist_ok=True)
        for name in files:
            rel = os.path.normpath(os.path.join(rel_root, name)) if rel_root != '.' else name
            if is_excluded(rel, patterns):
                actions['skipped'] += 1
                continue
            s = os.path.join(root, name)
            d = os.path.join(target_root, name)
            if not os.path.exists(d) or os.path.getmtime(s) != os.path.getmtime(d):
                if not dry:
                    try:
                        shutil.copy2(s, d)
                    except PermissionError:
                        on_rm_error(os.remove, d, None)
                        shutil.copy2(s, d)
                actions['copied'] += 1

    if delete and os.path.isdir(dst):
        for root, dirs, files in os.walk(dst, topdown=False):
            rel_root = os.path.relpath(root, dst)
            for name in files + dirs:
                rel = os.path.normpath(os.path.join(rel_root, name)) if rel_root != '.' else name
                if is_excluded(rel, patterns):
                    actions['skipped'] += 1
                    continue
                path = os.path.join(root, name)
                src_path = os.path.join(src, rel)
                if os.path.exists(src_path):
                    continue
                if not dry:
                    if os.path.isdir(path) and not os.path.islink(path):
                        shutil.rmtree(path, onerror=on_rm_error)
                    else:
                        try:
                            os.remove(path)
                        except PermissionError:
                            on_rm_error(os.remove, path, None)
                actions['removed'] += 1

    return actions


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('src')
    parser.add_argument('dst')
    parser.add_argument('--delete', action='store_true',
                        help='remove destination files absent from the source')
    parser.add_argument('--dry-run', action='store_true', help='print actions only')
    parser.add_argument('--exclude', action='append', default=[],
                        help='rsync-style exclude pattern; repeat as needed')
    args = parser.parse_args()

    actions = mirror(args.src, args.dst, args.exclude, args.delete, args.dry_run)
    prefix = 'dry-run: ' if args.dry_run else ''
    print(f"{prefix}mirror {actions['copied']} files, "
          f"removed {actions['removed']}, excluded {actions['skipped']}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
