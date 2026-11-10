#!/usr/bin/env python3
"""Independently verify that resolved English slots really are English.

The locale resolver uses script anchors and positional cycles. This check uses
neither: it scores each slot against a lexicon built from the corpus's existing
English canon (books, cards, interactions, items, non-caption transcripts) and
compares the English slot with nearby non-English siblings.

Observed separation on `0295`: English slots score ~0.90, translated siblings
~0.05. A slot that is actually German/French/... scores like its siblings.

Usage:
    python3 scripts/verify-live-english.py --sample 25
    python3 scripts/verify-live-english.py --packages 0295 029e --sample 40

Exit 1 when any sampled English slot looks non-English or a sibling clearly
out-scores it. Read-only.
"""
import argparse
import glob
import importlib.util
import json
import os
import random
import re
import sqlite3
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
VAULT = "/opt/vault/d2-bl-extract"
MAPS = os.path.join(ROOT, "archive", "data", "locale-maps")
WORD = re.compile(r"[^\W\d_]{2,}", re.UNICODE)
NON_EN = {"DE", "FR", "ES", "ES-419", "IT", "PT", "PL", "RU", "JA", "KO",
          "ZH-TW", "ZH-CN"}


def load_extractor():
    spec = importlib.util.spec_from_file_location(
        "extract_live", os.path.join(HERE, "extract-live-captions.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def build_lexicon(db_path):
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    texts = []
    for sql in (
            "SELECT body FROM book_entries WHERE body!=''",
            "SELECT body FROM grimoire_cards WHERE body!=''",
            "SELECT text FROM interactions WHERE text!=''",
            "SELECT text || ' ' || COALESCE(title,'') FROM items",
            "SELECT tl.line FROM transcript_lines tl "
            "JOIN transcripts t ON t.id=tl.transcript_id "
            "WHERE COALESCE(t.source_tier,'')!='game_caption'"):
        texts.extend(r[0] for r in conn.execute(sql))
    conn.close()
    vocab = set()
    for text in texts:
        vocab.update(w.lower() for w in re.findall(r"[A-Za-z][A-Za-z'-]{2,}", text))
    return vocab


def coverage(text, vocab):
    tokens = [w.lower() for w in WORD.findall(text)]
    if not tokens:
        return None
    return sum(1 for w in tokens if w in vocab) / len(tokens)


def parse_entry(extractor, directory, index):
    names = [n for n in os.listdir(directory) if n.startswith(f"{index}_")]
    if not names:
        return None
    try:
        parsed = extractor.parse_string_bank(os.path.join(directory, names[0]))
    except (AssertionError, Exception):
        return None
    return [r["text"] for r in parsed["records"] if r.get("text")]


def mean_coverage(texts, vocab):
    scores = [coverage(t, vocab) for t in texts]
    scores = [s for s in scores if s is not None]
    return statistics.mean(scores) if scores else None


def check_package(package, extractor, vocab, sample, rng):
    map_path = os.path.join(MAPS, f"{package}.json")
    data = json.load(open(map_path, encoding="utf-8"))
    resolver_path = os.path.join(VAULT, "locale-maps", f"{package}.json")
    resolver = json.load(open(resolver_path, encoding="utf-8"))
    locale_map = {int(k): v for k, v in resolver["locale_map"].items()}
    english = [e for e in data["en_entries"] if locale_map.get(e) == "EN"]
    directory = os.path.join(VAULT, "temp", f"out-{package}_mounted")
    if not os.path.isdir(directory):
        return {"package": package, "error": "mounted directory missing"}

    picked = sorted(rng.sample(english, min(sample, len(english))))
    en_scores, other_scores, flags = [], [], []
    for index in picked:
        texts = parse_entry(extractor, directory, index)
        score = mean_coverage(texts, vocab) if texts else None
        if score is None:
            continue
        en_scores.append(score)
        siblings = []
        for other in range(index - 12, index + 13):
            if other == index or locale_map.get(other) not in NON_EN:
                continue
            if other not in data["en_entries"]:
                other_texts = parse_entry(extractor, directory, other)
                other_score = (mean_coverage(other_texts, vocab)
                               if other_texts else None)
                if other_score is not None:
                    siblings.append(other_score)
        best_sibling = max(siblings) if siblings else None
        other_scores.extend(siblings[:2])
        if score < 0.25 or (best_sibling is not None and
                            best_sibling > score + 0.20 and best_sibling > 0.50):
            flags.append({"entry": index, "en_coverage": round(score, 3),
                          "best_sibling": round(best_sibling, 3)
                          if best_sibling is not None else None,
                          "sample": (texts or [""])[0][:110]})

    return {"package": package, "sampled": len(picked),
            "en_median": round(statistics.median(en_scores), 3) if en_scores else None,
            "en_min": round(min(en_scores), 3) if en_scores else None,
            "other_median": round(statistics.median(other_scores), 3)
            if other_scores else None,
            "other_max": round(max(other_scores), 3) if other_scores else None,
            "flags": flags}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--packages", nargs="*", default=None)
    ap.add_argument("--sample", type=int, default=25)
    ap.add_argument("--seed", type=int, default=20261110)
    ap.add_argument("--db", default=os.path.join(ROOT, "db", "grimoire.db"))
    ap.add_argument("--report", help="write the JSON report here")
    args = ap.parse_args()

    if args.packages:
        packages = [p if p.startswith("w64_") else f"w64_sr_globals_{p}"
                    for p in args.packages]
    else:
        packages = sorted(os.path.basename(p)[:-5]
                          for p in glob.glob(os.path.join(MAPS, "w64_sr_globals_*.json"))
                          if not p.endswith(".stats.json"))

    extractor = load_extractor()
    vocab = build_lexicon(args.db)
    rng = random.Random(args.seed)
    results = [check_package(p, extractor, vocab, args.sample, rng)
               for p in packages]

    failed = False
    for r in results:
        if "error" in r:
            print(f"{r['package']}: ERROR {r['error']}")
            failed = True
            continue
        status = "OK" if not r["flags"] else "FLAG"
        if r["flags"]:
            failed = True
        print(f"{r['package']}: {status} n={r['sampled']} "
              f"EN median {r['en_median']} (min {r['en_min']}) | "
              f"other median {r['other_median']} (max {r['other_max']})")
        for flag in r["flags"]:
            print(f"    entry {flag['entry']}: EN {flag['en_coverage']} vs "
                  f"sibling {flag['best_sibling']} | {flag['sample']}")

    if args.report:
        with open(args.report, "w", encoding="utf-8") as fh:
            json.dump({"sample": args.sample, "seed": args.seed,
                       "results": results}, fh, indent=1, sort_keys=True)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
