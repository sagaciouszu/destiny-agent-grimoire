#!/usr/bin/env python3
"""Verify class-tagged transcript filtering through the API."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'db'))
import api  # noqa: E402


def main():
    hunter = api.transcript('menagerie', class_tag='hunter', limit=300)
    assert hunter, 'no hunter transcript rows'
    assert all(line['class_tag'] in (None, 'hunter') for line in hunter['lines'])
    titan = api.transcript('menagerie', class_tag='titan', limit=300)
    assert all(line['class_tag'] in (None, 'titan') for line in titan['lines'])
    assert hunter['total'] != titan['total'] or hunter['lines'] != titan['lines']
    print('class transcript filter: hunter and titan selected')
    return 0


if __name__ == '__main__':
    sys.exit(main())
