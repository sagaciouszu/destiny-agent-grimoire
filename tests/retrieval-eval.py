#!/usr/bin/env python3
"""Retrieval evaluation: compares default FTS order with relevance order.

Metrics over a fixed query set:
  recall@5   fraction of queries with a relevant result in the top 5
  MRR        mean reciprocal rank of the first relevant result
  precision@5 mean fraction of the top 5 that are relevant

Run: python3 tests/retrieval-eval.py [--json]
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'db'))
import api  # noqa: E402

QUERIES = [
    ('sword logic', ['sword logic']),
    ('Crota', ['crota']),
    ('Eris Morn', ['eris']),
    ('Gambit', ['gambit']),
    ('Malfeasance', ['malfeasance']),
    ('Savathûn', ['savath']),
    ('the Nine', ['nine']),
    ('Oryx', ['oryx']),
    ('Hellmouth', ['hellmouth']),
    ('Dredgen', ['dredgen']),
    ('Ghost', ['ghost']),
    ('Traveler', ['traveler']),
    ('Iron Lords', ['iron lord']),
    ('Warmind', ['warmind']),
    ('Exo Stranger', ['stranger', 'elsie']),
]


def relevant(row, terms):
    blob = f"{row.get('title', '')} {row.get('snippet', row.get('text', ''))}".lower()
    return any(t in blob for t in terms)


def evaluate(rank):
    hits = 0
    rr = 0.0
    precision = 0.0
    latencies = []
    import time
    for q, terms in QUERIES:
        t = time.perf_counter()
        rows = api.search(q, limit=5, rank=rank)
        latencies.append((time.perf_counter() - t) * 1000)
        flags = [relevant(r, terms) for r in rows]
        if any(flags):
            hits += 1
            rr += 1 / (flags.index(True) + 1)
            precision += sum(flags) / len(flags)
    n = len(QUERIES)
    return {'recall@5': hits / n, 'mrr': rr / n, 'precision@5': precision / n,
            'median_ms': sorted(latencies)[len(latencies) // 2]}


default = evaluate(False)
ranked = evaluate(True)
print('retrieval evaluation (15 queries)')
print(f"  default  recall@5={default['recall@5']:.2f} MRR={default['mrr']:.2f} "
      f"P@5={default['precision@5']:.2f} {default['median_ms']:.1f} ms")
print(f"  ranked   recall@5={ranked['recall@5']:.2f} MRR={ranked['mrr']:.2f} "
      f"P@5={ranked['precision@5']:.2f} {ranked['median_ms']:.1f} ms")
winner = 'ranked' if (ranked['mrr'], ranked['recall@5']) > (default['mrr'], default['recall@5']) else 'default'
print(f"  better: {winner}")

if '--json' in sys.argv:
    print(json.dumps({'default': default, 'ranked': ranked, 'winner': winner}))
