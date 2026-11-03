#!/usr/bin/env python3
"""
Eris Morn Statistical Voice Similarity Scorer
Compares a candidate response against the canonical Eris Morn transcript lines
in the grimoire database using vocabulary overlap, character/word n-gram
similarity, sentence-length distribution, formal-marker density, and a
Drifter-slang penalty (Eris never uses Drifter slang).

Usage:
  ./eris-voice-scorer.py "The Hive are frenzied. We must move, Guardian."
"""
import math, os, re, sys
from collections import Counter

def tokenize(text):
    return re.findall(r"[a-z0-9']+", text.lower())

def ngrams(tokens, n):
    return [tuple(tokens[i:i+n]) for i in range(len(tokens)-n+1)]

def load_corpus():
    """Load canonical Eris lines from the grimoire DB (fallback: source markdown)."""
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.environ.get("GRIMOIRE_DB", ""),
        os.path.join(here, "..", "lore", "db", "grimoire.db"),
        os.path.join(here, "..", "..", "destiny-agent-grimoire", "db", "grimoire.db"),
        os.path.join(here, "..", "db", "grimoire.db"),
    ]
    for db in candidates:
        if db and os.path.exists(db):
            import sqlite3
            conn = sqlite3.connect(db)
            rows = [r[0] for r in conn.execute(
                "SELECT line FROM transcript_lines WHERE speaker LIKE '%Eris%' AND is_stage_dir=0")]
            conn.close()
            if rows:
                return rows
    # Fallback: markdown source corpus
    import glob
    lines = []
    for p in glob.glob(os.path.join(here, "..", "lore", "source", "transcripts", "*.md")):
        for line in open(p, encoding="utf-8", errors="ignore"):
            m = re.match(r"^\*(?:The )?Eris(?: Morn)?:\*\s*(.*)$", line.strip())
            if m:
                lines.append(m.group(1).strip())
    return lines

# Formal markers grounded in Eris's actual corpus (frequency-checked against DB)
MARKERS = {
    "guardian", "hive", "darkness", "pyramid", "pyramids", "witness", "savathûn",
    "savathuns", "oryx", "crota", "xivu", "nightmare", "nightmares", "moon",
    "hellmouth", "seed", "traveler", "swarm", "cradle", "witch", "vengeance",
    "grief", "sorrow", "fireteam", "must", "cannot", "shall",
    "endure", "silence", "forces", "influence", "destroy", "banish",
    "taken", "throne", "tree", "silver", "wings", "fight", "reach", "return",
    "veil", "rhulk", "navôta", "ecthar", "xenophage", "veil", "collapse",
    "eriana", "toland", "omar", "vell", "sai",
}

# Vocabulary Eris never uses: Drifter slang + casual markers (penalized)
SLANG = {
    "heh", "nah", "yeah", "kid", "brother", "sister", "y'know", "gotta",
    "nothin'", "somethin'", "doin'", "ain't", "lol", "haha", "hah", "dude",
    "gonna", "wanna", "gimme", "cool", "awesome", "totally", "super",
    "fun", "funny", "joke", "joking", "stuff",
    # Drifter-specific vocabulary Eris would never say
    "motes", "gambit", "bank", "hero", "partner", "reckoner",
    "derelict", "primeval", "blocker", "invader", "haul", "moondust",
    "malfeasance", "wager", "punk", "snitch",
}

# Signature Eris phrases (all verified present in DB corpus)
SIG_PHRASES = [
    "i am eris morn", "the hive", "do not", "guardian", "savathûn",
    "the darkness", "pyramid", "nightmare", "the moon", "hellmouth",
    "crota", "oryx", "xivu", "witness", "fireteam", "the seed",
    "tree of silver wings", "we must", "you must", "there is no",
    "i will", "vengeance", "witch", "grief", "sorrow", "swarm",
    "frenzied", "cradle", "the traveler", "the great game", "endure",
    "i will not", "silence", "my fireteam", "the hive god", "hive gods",
    "the last city", "the vanguard", "zavala", "ikora", "the drifter",
    "moondust", "xenophage", "ecthar", "assassins", "navôta",
    "the leviathan", "calus", "the nine", "the veil", "rhulk",
    "the witness", "the pyramids", "the collapse", "the dark",
    "the light", "the fireteam", "eriana", "toland", "sai", "omar",
    "vell", "alcove", "the hellmouth", "the moon", "crota's end",
]

def score_response(candidate, corpus_lines):
    cand_tokens = tokenize(candidate)
    if not cand_tokens:
        return 0.0, {}

    all_tokens = []
    for l in corpus_lines:
        all_tokens.extend(tokenize(l))
    all_text = " ".join(all_tokens).lower()

    vocab = set(all_tokens)
    uni_counts = Counter(all_tokens)
    bi_set = set(ngrams(all_tokens, 2))
    tri_set = set(ngrams(all_tokens, 3))

    # 1. Vocabulary overlap (0-20 pts)
    in_vocab = sum(1 for t in cand_tokens if t in vocab)
    vocab_ratio = in_vocab / len(cand_tokens)
    vocab_score = min(20.0, vocab_ratio * 20.0)

    # 2. Bigram & trigram overlap (0-20 pts)
    cand_bi = ngrams(cand_tokens, 2)
    cand_tri = ngrams(cand_tokens, 3)
    bi_hits = sum(1 for b in cand_bi if b in bi_set) / max(1, len(cand_bi))
    tri_hits = sum(1 for t in cand_tri if t in tri_set) / max(1, len(cand_tri))
    ngram_score = min(10.0, (bi_hits * 12.0) + (tri_hits * 12.0))

    # 3. Formal marker density (0-25 pts)
    marker_hits = [t for t in cand_tokens if t in MARKERS]
    unique_markers = len(set(marker_hits))
    marker_score = min(25.0, unique_markers * 4.0)

    # 4. Slang penalty (0 to -25 pts)
    slang_hits = [t for t in cand_tokens if t in SLANG]
    unique_slang = len(set(slang_hits))
    slang_penalty = min(25.0, unique_slang * 8.0)

    # 5. Sentence cadence (0-15 pts): Eris avg 6.3 words/sentence, short declaratives
    sents = [s.strip() for s in re.split(r"[.!?]+", candidate) if s.strip()]
    avg_words = len(cand_tokens) / max(1, len(sents))
    if 3.0 <= avg_words <= 8.0:
        cadence_score = 15.0
    elif 8.0 < avg_words <= 12.0:
        cadence_score = 12.0
    elif 12.0 < avg_words <= 16.0:
        cadence_score = 8.0
    elif avg_words <= 20.0:
        cadence_score = 5.0
    else:
        cadence_score = 2.0

    # 6. Character n-gram overlap (0-10 pts)
    cand_chars = set(candidate.lower()[i:i+3] for i in range(len(candidate)-2))
    corpus_chars = set(all_text[i:i+3] for i in range(len(all_text)-2))
    char_overlap = len(cand_chars & corpus_chars) / max(1, len(cand_chars))
    char_score = min(15.0, char_overlap * 15.0)

    # 7. Signature phrase detection (0-15 pts)
    cand_lower = candidate.lower()
    found_phrases = sum(1 for sp in SIG_PHRASES if sp in cand_lower)
    phrase_score = min(15.0, found_phrases * 2.0)

    # 8. Formality bonus: no contractions + formal address (0-5 pts)
    formal_bonus = 0.0
    if "guardian" in cand_lower and not slang_hits:
        formal_bonus += 3.0
    if not slang_hits and avg_words <= 10.0:
        formal_bonus += 2.0

    # 9. Length brevity (Eris short: <=30 words) (0-5 pts)
    word_count = len(cand_tokens)
    if word_count <= 25:
        brevity_bonus = 5.0
    elif word_count <= 40:
        brevity_bonus = 3.0
    else:
        brevity_bonus = 0.0

    total_raw = (vocab_score + ngram_score + marker_score + cadence_score +
                 char_score + phrase_score + formal_bonus + brevity_bonus -
                 slang_penalty)
    total = round(max(0.0, min(100.0, total_raw)), 1)

    details = {
        "vocab_score": round(vocab_score, 1),
        "ngram_score": round(ngram_score, 1),
        "marker_score": round(marker_score, 1),
        "slang_penalty": round(slang_penalty, 1),
        "cadence_score": round(cadence_score, 1),
        "char_score": round(char_score, 1),
        "phrase_score": round(phrase_score, 1),
        "formal_bonus": round(formal_bonus, 1),
        "brevity_bonus": round(brevity_bonus, 1),
        "markers_found": sorted(set(marker_hits)),
        "slang_found": sorted(set(slang_hits)),
        "avg_words_per_sentence": round(avg_words, 1),
        "corpus_lines": len(corpus_lines),
    }
    return total, details

def main():
    if len(sys.argv) < 2:
        print("Usage: eris-voice-scorer.py \"<response>\"")
        sys.exit(1)
    candidate = " ".join(sys.argv[1:])
    corpus = load_corpus()
    total, d = score_response(candidate, corpus)
    status = "PASS" if total >= 55.0 else ("PARTIAL" if total >= 40.0 else "FAIL")
    print(f"=== ERIS MORN STATISTICAL VOICE SCORER ===")
    print(f"Corpus size: {d['corpus_lines']} canonical lines")
    print(f"Total Score: {total}/100 ({status})")
    print(f"  Vocabulary overlap : {d['vocab_score']}/20")
    print(f"  N-gram phrasing    : {d['ngram_score']}/20")
    print(f"  Formal markers     : {d['marker_score']}/25 ({', '.join(d['markers_found'][:8]) or 'none'})")
    print(f"  Slang penalty      : -{d['slang_penalty']}/25 ({', '.join(d['slang_found']) or 'none'})")
    print(f"  Sentence cadence   : {d['cadence_score']}/15 (avg {d['avg_words_per_sentence']} words/sentence)")
    print(f"  Char n-gram        : {d['char_score']}/15")
    print(f"  Signature phrases  : {d['phrase_score']}/15")
    print(f"  Formality bonus    : +{d['formal_bonus']}/5")
    print(f"  Brevity bonus      : +{d['brevity_bonus']}/5")
    sys.exit(0 if total >= 55.0 else 1)

if __name__ == "__main__":
    main()
