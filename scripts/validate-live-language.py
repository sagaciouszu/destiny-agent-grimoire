#!/usr/bin/env python3
"""Validate the language of an extracted live-caption package.

The locale resolver assigns English entry indices by position, anchored on
script evidence. A whole table can still land on the wrong slot in a partially
translated block, which shows up as a table whose aggregate text is another
language (observed: six German tables in `w64_sr_globals_029e`).

This gate scores each record's aggregated tokens against stopword lists and
drops a record when a non-English language dominates. It is deliberately
table-level: single short lines false-positive constantly ("Return to Ana
Bray" scores Polish because `to` is a Polish stopword), but an English table
with a few short lines still scores English overall.

Usage:
    python3 scripts/validate-live-language.py --in cap.jsonl \
        --out cap.validated.jsonl --report cap.language.json

Exit 1 if any record is dropped, so a widening run cannot silently ignore it.
"""
import argparse
import json
import re
import sys

STOPWORDS = {
    "ES": set("el la los las un una de del que y o en es son fue ser por para con "
              "su sus al lo como más pero se le les este esta cuando muy sin sobre "
              "también hay ha han está están".split()),
    "IT": set("il lo la i gli le un uno una di del della che e o in è sono per con "
              "il suo sua al alla come più ma se questo questa quando molto senza "
              "sopra anche".split()),
    "DE": set("der die das den dem des ein eine einer und oder in ist sind für mit "
              "zu von auf nicht sich sie er es ich du wir ihr werden wurde wird hat "
              "haben als auch aber wenn bei aus nach über vor durch".split()),
    "FR": set("le la les un une des de du et ou en est sont pour avec sur dans pas "
              "que qui ce cette ces il elle ils elles nous vous je tu son sa ses au "
              "aux plus mais si comme quand très sans aussi".split()),
    "PT": set("o a os as um uma de do da dos das e ou em é são para com por no na "
              "nos nas seu sua ao aos como mais mas se este esta quando muito sem "
              "sobre também há tem estão".split()),
    "PL": set("i w na z do nie to że się jest są jak co po za od dla ale lub oraz "
              "tak ten ta te tego tej tym przez przed pod nad przy być mieć ma "
              "mają".split()),
}
STRONG_CHARS = {
    "DE": "äöüß",
    "ES": "¿¡ñ",
    "FR": "àâçéèêëîïôùûüÿœ",
    "PT": "ãõç",
    "PL": "ąęłńóśźż",
}
CYRILLIC = re.compile(r"[\u0400-\u04FF]")
CJK = re.compile(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uac00-\ud7af]")
WORD = re.compile(r"[^\W\d_]+", re.UNICODE)


def language_scores(texts):
    tokens = []
    for text in texts:
        tokens.extend(w.lower() for w in WORD.findall(text))
    if not tokens:
        return None
    return {lang: sum(1 for t in tokens if t in words) / len(tokens)
            for lang, words in STOPWORDS.items()}


def judge(record):
    """Return (keep, reason) for one caption record (one bank table slice)."""
    texts = [line.get("text", "") for line in record.get("lines", [])]
    if not texts:
        return False, "no text"
    joined = " ".join(texts)
    if CYRILLIC.search(joined):
        return False, "cyrillic"
    if CJK.search(joined):
        return False, "cjk"
    scores = language_scores(texts)
    if not scores:
        return True, "no words"
    english = scores.get("EN", 0.0)
    best = max((k for k in scores if k != "EN"), key=lambda k: scores[k])
    ratio = scores[best]
    tokens = len(WORD.findall(joined))
    strong = any(c in joined.lower() for c in STRONG_CHARS.get(best, ""))

    # Short English strings ("Return to Eva") constantly score against Latin
    # stopword lists, so a stopword ratio alone is not evidence. Drop a table
    # only when the wrong language has a script signal, or when there is enough
    # text for the aggregate vocabulary to be decisive.
    if strong and ratio >= 0.15 and ratio > english:
        return False, f"{best}:{ratio:.2f} (script) vs EN:{english:.2f}"
    if tokens >= 20 and ratio >= 0.45 and ratio > english + 0.20:
        return False, f"{best}:{ratio:.2f} vs EN:{english:.2f}"
    return True, "ok"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="src", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--report", required=True)
    args = ap.parse_args()

    kept, dropped = 0, []
    with open(args.src, encoding="utf-8") as src, \
            open(args.out, "w", encoding="utf-8") as dst:
        for raw in src:
            rec = json.loads(raw)
            ok, reason = judge(rec)
            if ok:
                dst.write(json.dumps(rec, ensure_ascii=False) + "\n")
                kept += 1
            else:
                dropped.append({"bank_entry": rec.get("bank_entry"),
                                "package_id": rec.get("package_id"),
                                "reason": reason,
                                "sample": (rec.get("lines") or [{}])[0].get("text", "")[:120]})
    report = {"kept_records": kept, "dropped_records": len(dropped),
              "dropped": dropped}
    with open(args.report, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1, sort_keys=True)
    print(json.dumps({k: report[k] for k in ("kept_records", "dropped_records")},
                     sort_keys=True))
    for d in dropped:
        print(f"  drop entry {d['bank_entry']}: {d['reason']} | {d['sample']}")
    return 1 if dropped else 0


if __name__ == "__main__":
    sys.exit(main())
