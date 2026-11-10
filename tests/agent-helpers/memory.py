#!/usr/bin/env python3
"""Per-user memory helper.

Usage:
    python3 memory.py get    --user <platform-id>
    python3 memory.py set    --user <platform-id> [--text "..."]   # or stdin
    python3 memory.py forget --user <platform-id>
    python3 memory.py prefs-get  --user <platform-id>
    python3 memory.py prefs-set  --user <platform-id> --class hunter|titan|warlock

The platform id is hashed with a local salt; the raw id is never used as a
filename. There is deliberately no list command and no free path argument.
"""
import argparse
import fcntl
import hashlib
import json
import os
import secrets
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.environ.get('MEMORY_ROOT') or os.path.join(HERE, 'memory'))
USERS = os.path.join(ROOT, 'users')
PREFS = os.path.join(ROOT, 'prefs')
SALT = os.path.join(ROOT, '.salt')
MAX_BYTES = 8192


def bootstrap():
    """Create directories and the salt under one exclusive lock."""
    os.makedirs(ROOT, mode=0o700, exist_ok=True)
    os.chmod(ROOT, 0o700)
    os.makedirs(USERS, mode=0o700, exist_ok=True)
    os.makedirs(PREFS, mode=0o700, exist_ok=True)
    lock_path = os.path.join(ROOT, '.lock')
    handle = open(lock_path, 'a+')
    os.chmod(lock_path, 0o600)
    fcntl.flock(handle, fcntl.LOCK_EX)
    if not os.path.exists(SALT):
        fd = os.open(SALT, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'wb') as f:
            f.write(secrets.token_bytes(32))
    os.chmod(SALT, 0o600)
    return handle


def key(user):
    user = (user or '').strip()
    if not user or len(user) > 256 or any(ch in user for ch in ('\n', '\r', '\x00')):
        raise SystemExit('invalid user id')
    with open(SALT, 'rb') as f:
        salt = f.read()
    return hashlib.sha256(salt + b'\x00' + user.encode('utf-8')).hexdigest()[:32]


def path_for(user):
    return os.path.join(USERS, key(user) + '.txt')


def read(handle, user):
    path = path_for(user)
    if not os.path.exists(path):
        return ''
    with open(path, encoding='utf-8') as f:
        return f.read(MAX_BYTES + 1)


def prefs_path(user):
    return os.path.join(PREFS, key(user) + '.json')


def prefs_read(user):
    path = prefs_path(user)
    if not os.path.exists(path):
        return {}
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def prefs_write(user, updates):
    current = prefs_read(user)
    current.update(updates)
    fd, tmp = tempfile.mkstemp(dir=PREFS)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(current, f, indent=2, sort_keys=True)
            f.write('\n')
        os.chmod(tmp, 0o600)
        os.replace(tmp, prefs_path(user))
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def write(handle, user, text):
    text = text.replace('\x00', '').strip()
    if len(text.encode('utf-8')) > MAX_BYTES:
        raise SystemExit(f'memory exceeds {MAX_BYTES} bytes')
    path = path_for(user)
    fd, tmp = tempfile.mkstemp(dir=USERS)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(text + ('\n' if text else ''))
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def forget(handle, user):
    for path in (path_for(user), prefs_path(user)):
        if os.path.exists(path):
            os.remove(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['get', 'set', 'forget', 'prefs-get', 'prefs-set'])
    parser.add_argument('--user', required=True)
    parser.add_argument('--text')
    parser.add_argument('--class', dest='player_class', choices=['hunter', 'titan', 'warlock'])
    args = parser.parse_args()
    handle = bootstrap()
    try:
        if args.action == 'get':
            sys.stdout.write(read(handle, args.user))
        elif args.action == 'set':
            write(handle, args.user, args.text if args.text is not None else sys.stdin.read())
        elif args.action == 'forget':
            forget(handle, args.user)
        elif args.action == 'prefs-get':
            json.dump(prefs_read(args.user), sys.stdout, indent=2, sort_keys=True)
            sys.stdout.write('\n')
        else:
            if not args.player_class:
                raise SystemExit('prefs-set requires --class hunter|titan|warlock')
            prefs_write(args.user, {'class': args.player_class})
    finally:
        fcntl.flock(handle, fcntl.LOCK_UN)
        handle.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
