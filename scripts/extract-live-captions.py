#!/usr/bin/env python3
"""Extract English game captions from a live-build `w64_sr_globals` package.

Input: an extracted package directory (one `.bin` per package entry, produced
by `tiger-pkg` unpack with `-v d2_ren`) plus a locale map naming the English
entry indices. Output: `archive/data/captions-live.jsonl` in the same record
shape as `archive/data/captions.jsonl`, tagged with the build it came from.

Why a separate file: the live build is a different provenance tier from the
2020 `sunrise-pre-bl` client. Keeping the two files apart means the loader
can never silently merge one build's text into another's, and a rebuild can
be audited per build.

Provenance rules (STANDARDS.md):
  * `source_build` is always set.
  * A speaker is recorded only when the string itself carries one (`"..." —Name`).
    No external speaker evidence exists for this build, so nothing is inferred.
  * No season, act or expansion is inferred from text.

Layout reference: /opt/vault/d2-bl-extract/reports/globals-decode.md

Reproduce the shipped package 0294 tier with:

    python3 scripts/extract-live-captions.py \
      --dir /opt/vault/d2-bl-extract/temp/out-w64_sr_globals_0294_0 \
      --locale-map archive/data/locale-maps/w64_sr_globals_0294.json \
      --stats archive/data/locale-maps/w64_sr_globals_0294.stats.json

Item-fragment exclusion is on by default (owner decision 2026-11-10); pass
`--keep-item-fragments` only for a diagnostic run.
"""
import argparse
import collections
import json
import os
import re
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FNV1 = 0x811C9DC5

# ---------------------------------------------------------------- parser ----


def parse_string_bank(path):
    """Decode one v53 StringBank entry. Every structural invariant is asserted."""
    b = open(path, "rb").read()
    u64 = lambda o: struct.unpack_from("<Q", b, o)[0]
    u32 = lambda o: struct.unpack_from("<I", b, o)[0]
    u16 = lambda o: struct.unpack_from("<H", b, o)[0]

    file_size = u64(0x00)
    nrec = u64(0x08)
    nparam = u64(0x18)
    blob_len = u64(0x28)
    pair_count = u64(0x38)

    assert file_size == len(b), f"{path}: file_size {file_size} != {len(b)}"
    assert u64(0x10) == 0x40, f"{path}: header size"
    assert u64(0x50) == nrec, f"{path}: record count repeat"

    recs = []
    for i in range(nrec):
        o = 0x68 + i * 0x20
        recs.append({
            "idx": i,
            "marker": u32(o + 0x08),
            "a": u16(o + 0x0C),
            "cp": u16(o + 0x0E),
        })

    off = 0x68 + nrec * 0x20
    if nparam >= 1:
        assert u32(off + 4) == 0x80809FB8, f"{path}: param header"
        assert u64(off + 8) == nparam, f"{path}: param count"
        assert u32(off + 0x10) == 0x80809A17, f"{path}: param magic"
        off += 24 + nparam * 0xC0 + 8

    desc = off
    assert u32(desc + 4) == 0x80809FB8, f"{path}: blob descriptor"
    assert u64(desc + 8) == blob_len, f"{path}: blob length"
    assert u32(desc + 0x10) == 0x80800005, f"{path}: blob magic"
    blob_start = desc + 24
    assert u64(0x30) == blob_start - 0x40, f"{path}: blob offset"
    blob = b[blob_start:blob_start + blob_len]
    assert blob and blob[-1] == 0, f"{path}: blob terminator"

    cur = 0
    strings = []
    for r in recs:
        if r["marker"] == FNV1:
            raw = blob[cur:cur + r["a"]]
            cur += r["a"]
            strings.append(raw.decode("utf-8", "replace"))
            r["text"] = strings[-1]
        else:
            strings.append(None)      # runtime parameter placeholder
            r["text"] = None
    assert cur == blob_len - 1, f"{path}: blob consumed {cur} of {blob_len - 1}"

    pairs_off = len(b) - pair_count * 16
    assert u64(0x40) == pairs_off - 0x50, f"{path}: pair table offset"
    total = 0
    for i in range(pair_count):
        total += struct.unpack_from("<Q", b, pairs_off + i * 16 + 8)[0]
    assert total == nrec, f"{path}: pair runs {total} != {nrec}"

    return {"file_size": file_size, "records": recs}


# -------------------------------------------------------------- shaping ----

# An attribution is a *spaced* em/en dash. Edition and location labels are
# glued to the dash ("The Witch Queen—Legendary", "Vex Gate Network—Sub
# Transit") and must not be mistaken for speakers.
ATTRIBUTION = re.compile(r"\s[—–]\s*([^\n—–]{1,60})\s*$")
IMPERATIVE = re.compile(
    r"^(Requires|Press|Select|Hold|Equip|Open|Visit|Speak to|Talk to|Return to|"
    r"Go to|Defeat|Eliminate|Collect|Find|Explore|Complete|Reach|Enter|Destroy|"
    r"Investigate|Locate|Recover|Deliver|Escape|Survive|Protect|Escort|Scan|Deploy|"
    r"Place|Use|Kill|Clear|Rescue|Follow|Meet|Report|Summon|Disable|Secure|Breach|"
    r"Infiltrate|Search|Retrieve|Bring|Take|Help|Assist|Attune|Commune|Bake|"
    r"Board|Adjust|Await|Listen|Travel|Board)\b")

# Mechanical text: perk/modifier/stat copy. Not lore, excluded by owner decision
# (2026-11-10). Two shapes: a modifier verb leading the line, or a percentage
# attached to a stat noun.
MECH_VERB = re.compile(
    r"^(Increases?|Decreases?|Reduces?|Grants?|Improves?|Refills?|Restores?|"
    r"Boosts?|Adds?|Extends?)\b")
MECH_STAT = re.compile(
    r"\b(damage|recharge|cooldown|energy|ammo|abilities?|ability|resistance|"
    r"rate|speed|capacity|range|handling|reload|stability|impact|health|"
    r"shield|super|melee|grenade)\b", re.I)
PERCENT = re.compile(r"\d+\s*%")


def is_mechanics(s):
    return bool(MECH_VERB.match(s)) or bool(PERCENT.search(s) and MECH_STAT.search(s))


def has_alnum(s):
    return any(c.isalnum() for c in s)


NOISE = re.compile(
    r"^(Requires\b|Seals:|Rewards?:|Objectives?:|Quest Steps?:|"
    r"\[.*\]$|.{0,2}$)")


def looks_like_speaker(cand):
    """A speaker label is short, capitalised and free of sentence punctuation."""
    words = cand.split()
    if not words or len(words) > 5:
        return False
    if not words[0][:1].isupper():
        return False
    if re.search(r"[.,;:!?()\"]", cand):
        return False
    # Reject descriptive phrases: every word must be capitalised, a particle
    # ("the", "of", "and"), or an acronym / designation such as AI or LAI-701.
    for w in words[1:]:
        if w[:1].isupper():
            continue
        if w.lower() in ("the", "of", "and", "von", "de", "van"):
            continue
        return False
    return True


def split_line(raw):
    """Return (text, speaker) for one string, or None to drop it."""
    text = raw.replace("\r", "\n").strip()
    if not text or not has_alnum(text):
        return None

    speaker = None
    m = ATTRIBUTION.search(text)
    if m:
        cand = m.group(1).strip().rstrip(".,;:")
        if looks_like_speaker(cand):
            speaker = cand
            text = text[:m.start()].strip()

    # Multi-paragraph strings become separate lines; keep the raw paragraph
    # index so (entry, record, part) is a stable line identity.
    raw_parts = re.split(r"\n+", text)
    parts = [(i, p.strip()) for i, p in enumerate(raw_parts)
             if p.strip() and has_alnum(p)]
    if not parts:
        return None
    return parts, speaker


def classify(text, speaker=None):
    """dialogue | objective | narration | mechanics | label.

    A line carrying an explicit speaker attribution is dialogue, whatever its
    punctuation looks like -- the attribution is the evidence, not the quotes.

    Prose must read as prose: a sentence-terminated, capitalised run of at
    least eight words. Everything shorter or unterminated is treated as a
    label and dropped, which keeps proper-noun strings (enemy names, modifier
    names, UI headings) out of the caption corpus.
    """
    s = text.strip()
    if speaker:
        return "dialogue"
    if is_mechanics(s):
        return "mechanics"
    if len(s) >= 2 and s[0] in "\"'\u201c" and s[-1] in "\"'\u201d":
        return "dialogue"
    if IMPERATIVE.match(s):
        # A one- or two-word imperative is a perk/ability name ("Kill Clip",
        # "Take That"), not a mission objective. Objectives read as instructions.
        if len(s.split()) >= 4 or re.search(r"[.!?]$", s):
            return "objective"
        return "label"
    words = s.split()
    if (len(words) >= 8 and re.search(r"[.!?]$", s)
            and s[:1].isupper() and not NOISE.match(s)):
        return "narration"
    return "label"


def strip_quotes(s):
    if len(s) >= 2 and s[0] in "\"'\u201c" and s[-1] in "\"'\u201d":
        return s[1:-1].strip()
    return s


def norm(s):
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return " ".join(s.split())


# ----------------------------------------------------------------- main ----

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True, help="extracted package dir")
    ap.add_argument("--locale-map", required=True, help="JSON with en_entries")
    ap.add_argument("--out", default=os.path.join(ROOT, "archive", "data",
                                                 "captions-live.jsonl"))
    ap.add_argument("--keep-labels", action="store_true",
                    help="include short labels (default: dialogue/prose/objective only)")
    ap.add_argument("--keep-mechanics", action="store_true",
                    help="include perk/modifier stat copy (excluded by default)")
    ap.add_argument("--keep-item-fragments", action="store_true",
                    help="keep lines that are fragments of an existing item text "
                         "(default: drop; owner decision 2026-11-10)")
    ap.add_argument("--items-jsonl",
                    default=os.path.join(ROOT, "archive", "data", "items.jsonl"))
    ap.add_argument("--stats", help="write a JSON stats sidecar here")
    args = ap.parse_args()

    lm = json.load(open(args.locale_map, encoding="utf-8"))
    en = set(lm["en_entries"])
    build = lm["build_id"]
    pkg = lm["package"]
    pkg_id = lm.get("package_id")
    pkg_base = pkg

    index = None
    if not args.keep_item_fragments:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from containment import ContainmentIndex   # noqa: E402
        index = ContainmentIndex.from_jsonl(args.items_jsonl)
        print(f"containment: {index.size} item texts indexed")

    stats = collections.Counter()
    seen = set()
    records = []
    per_entry = {}

    for name in sorted(os.listdir(args.dir)):
        if not name.endswith(".bin"):
            continue
        entry = int(name.split("_", 1)[0])
        if entry not in en:
            continue
        parsed = parse_string_bank(os.path.join(args.dir, name))
        stats["entries"] += 1
        e = per_entry.setdefault(entry, collections.Counter())

        groups = collections.defaultdict(list)
        for rec in parsed["records"]:
            raw = rec["text"]
            if not raw:
                continue
            stats["strings"] += 1
            shaped = split_line(raw)
            if not shaped:
                stats["dropped_noise"] += 1
                e["noise"] += 1
                continue
            parts, speaker = shaped
            for part_idx, part in parts:
                body = strip_quotes(part) if speaker else part
                if NOISE.match(body.strip()):
                    stats["dropped_noise"] += 1
                    e["noise"] += 1
                    continue
                kind = classify(body, speaker)
                if kind == "label" and not args.keep_labels:
                    stats["dropped_label"] += 1
                    e["label"] += 1
                    continue
                if kind == "mechanics" and not args.keep_mechanics:
                    stats["dropped_mechanics"] += 1
                    e["mechanics"] += 1
                    continue
                key = norm(body)
                if len(key) < 8 or key in seen:
                    stats["dropped_dup"] += 1
                    e["dup"] += 1
                    continue
                if index is not None and index.is_fragment(body):
                    stats["dropped_item_fragment"] += 1
                    e["item_fragment"] += 1
                    continue
                seen.add(key)
                groups[kind].append({
                    "text": body,
                    "speaker": speaker,
                    "speaker_source": build if speaker else None,
                    "is_stage_dir": 0,
                    "record_index": rec["idx"],
                    "record_part": part_idx,
                })
                stats["kept_" + kind] += 1
                e["kept"] += 1

        for kind, lines in groups.items():
            records.append({
                "kind": "caption",
                "slug": f"caption-live-{pkg_id:04x}-{entry}-{kind}",
                "title": None,
                "speaker": None,
                "activity": None,
                "confidence": "unknown",
                "lang": "en",
                "source_tier": "game_caption",
                "source_url": f"pkg:{pkg_base}#{entry}",
                "source_build": build,
                "package_id": pkg_id,
                "bank_entry": entry,
                "kind_class": kind,
                "lines": lines,
            })

    records.sort(key=lambda r: (r["bank_entry"], r["kind_class"]))
    with open(args.out, "w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    empty = {str(k): dict(v) for k, v in per_entry.items() if v["kept"] == 0}
    print(f"build      : {build}")
    print(f"package    : {pkg} (id {pkg_id})")
    print(f"entries    : {stats['entries']}")
    print(f"strings    : {stats['strings']}")
    print(f"records    : {len(records)}")
    print(f"lines      : {sum(len(r['lines']) for r in records)}")
    for k in ("kept_dialogue", "kept_narration", "kept_objective",
              "dropped_label", "dropped_dup", "dropped_noise",
              "dropped_mechanics", "dropped_item_fragment"):
        print(f"  {k:22s}: {stats[k]}")
    print(f"  entries with 0 kept  : {len(empty)}")
    print(f"wrote      : {args.out}")

    if args.stats:
        payload = {
            "build_id": build,
            "package": pkg,
            "package_id": pkg_id,
            "entries_read": stats["entries"],
            "strings": stats["strings"],
            "records": len(records),
            "lines": sum(len(r["lines"]) for r in records),
            "counts": {k: stats[k] for k in sorted(stats)},
            "empty_entries": empty,
        }
        with open(args.stats, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=1, sort_keys=True)
        print(f"stats      : {args.stats}")


if __name__ == "__main__":
    main()
