#!/usr/bin/env python3
"""
Drifter Statistical Voice Similarity Scorer
Compares a candidate response against the 473 canonical Drifter transcript lines
using vocabulary overlap, character/word n-gram similarity, sentence-length
distribution, and signature marker density.

Usage:
  ./drifter-voice-scorer.py "Hey, hero. Bank those Motes! Heh. Trust."
"""
import glob, math, os, re, sys
from collections import Counter

ARCHIVE = os.environ.get("ARCHIVE", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def tokenize(text):
    return re.findall(r"[a-z0-9']+", text.lower())

def ngrams(tokens, n):
    return [tuple(tokens[i:i+n]) for i in range(len(tokens)-n+1)]

def load_corpus():
    lines = []
    for p in glob.glob(os.path.join(ARCHIVE, "source/transcripts/*.md")):
        basename = os.path.basename(p)
        # Destinypedia in-game quotes: extract quoted Drifter lines
        if basename == "ingame-quotes-drifter-destinypedia.md":
            for line in open(p, encoding="utf-8", errors="ignore"):
                m = re.match(r'^- "([^"]+)"', line.strip())
                if m:
                    lines.append(m.group(1).strip())
            continue
        # Standard transcript format: *Drifter:* or *The Drifter:*
        for line in open(p, encoding="utf-8", errors="ignore"):
            m = re.match(r"^\*(?:The )?Drifter:\*\s*(.*)$", line.strip())
            if m:
                lines.append(m.group(1).strip())
    return lines

MARKERS = {
    "heh", "nah", "yeah", "kid", "hero", "partner", "brother", "sister",
    "punk", "snitch", "reckoner", "moondust", "trust", "motes", "bank",
    "gambit", "derelict", "haul", "primeval", "blocker", "invader",
    "gotta", "doin'", "nothin'", "somethin'", "lookin'", "talkin'",
    "runnin'", "comin'", "ol'", "ain't", "wager", "bet", "bets", "coin",
    "ghost", "cut", "tape", "tool", "light", "dark", "survive", "monsters",
    "hope", "fear", "scared", "blue", "malfeasance", "shin", "nine",
    "vanguard", "crew", "eat", "hungry", "dark age", "city", "warlord",
    "iron lord", "felwinter", "eaton", "orin", "emissary", "cayde",
    "eris", "saladin", "spider", "boss", "aunor", "eido", "sloane",
    "blue", "malphur", "golden", "gun", "last word", "thorn", "lumina",
    "breakneck", "python", "hush", "malfeasance", "derelict", "haul",
}

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

    # 2. Bigram & trigram overlap with canonical Drifter phrasing (0-20 pts)
    cand_bi = ngrams(cand_tokens, 2)
    cand_tri = ngrams(cand_tokens, 3)
    bi_hits = sum(1 for b in cand_bi if b in bi_set) / max(1, len(cand_bi))
    tri_hits = sum(1 for t in cand_tri if t in tri_set) / max(1, len(cand_tri))
    ngram_score = min(10.0, (bi_hits * 12.0) + (tri_hits * 12.0))

    # 3. Signature marker density (0-25 pts)
    marker_hits = [t for t in cand_tokens if t in MARKERS or t.endswith("in'")]
    unique_markers = len(set(marker_hits))
    marker_score = min(25.0, unique_markers * 5.0)

    # 4. Sentence cadence & length profile (0-15 pts)
    sents = [s.strip() for s in re.split(r"[.!?]+", candidate) if s.strip()]
    avg_words = len(cand_tokens) / max(1, len(sents))
    # Drifter speaks in punchy sentences (avg 1-14 words)
    if 1.0 <= avg_words <= 4.0:
        cadence_score = 15.0
    elif 4.0 < avg_words <= 8.0:
        cadence_score = 13.0
    elif 8.0 < avg_words <= 14.0:
        cadence_score = 10.0
    elif avg_words <= 20.0:
        cadence_score = 6.0
    else:
        cadence_score = 3.0

    # 5. Character n-gram overlap (0-10 pts) - captures g-dropping, "heh", etc.
    cand_chars = set(candidate.lower()[i:i+3] for i in range(len(candidate)-2))
    corpus_chars = set(all_text[i:i+3] for i in range(len(all_text)-2))
    char_overlap = len(cand_chars & corpus_chars) / max(1, len(cand_chars))
    char_score = min(15.0, char_overlap * 15.0)

    # 6. Signature phrase detection (0-10 pts) - known Drifter phrases
    sig_phrases = [
        "bank those motes", "guy's gotta eat", "all bets on you", "trust",
        "heh", "hero", "moondust", "cue ball", "old wolf", "reckoner", "punk",
        "gotta eat", "watch your back", "monsters survive", "i dig it",
        "that's all i got", "cut the tape", "no pressure", "bank those",
        "weaponized heat death", "pure atrophy", "down payment on a dream",
        "not better. just different", "everything's got value", "how you livin",
        "cut the tape, ghost", "connection to the light", "not a friend",
        "he's a tool", "saving his own", "don't gimme that look",
        "you know where we stand", "dark age was different", "no city",
        "it brought hell to earth", "hell no", "i couldn't either",
        "i can't feel anything", "lost", "gone", "dead", "survive",
        "take every day as it is", "seats i'm savin", "if you want it",
        "ol' drifter", "guy's gotta eat", "bank those motes",
        "ring that dinner bell", "soup's on", "primeval", "blocker",
        "invader", "motes", "bank", "derelict", "haul", "malfeasance",
        "golden gun", "shin malphur", "the nine", "darkness", "vanguard",
        "cue ball", "ol' rey", "old wolf", "moondust", "boss", "spider",
        "blue", "ghost", "malfeasance", "last word", "thorn", "lumina",
    ]
    found_phrases = sum(1 for sp in sig_phrases if sp in candidate.lower())
    phrase_score = min(15.0, found_phrases * 3.0)

    # Brevity bonus: short, punchy responses (Drifter's signature style) get up to +5
    word_count = len(cand_tokens)
    if word_count <= 12 and found_phrases >= 3:
        brevity_bonus = 5.0
    elif word_count <= 15 and found_phrases >= 2:
        brevity_bonus = 3.0
    else:
        brevity_bonus = 0.0
    # Consistency bonus: longer responses that maintain Drifter voice throughout
    if word_count > 30 and found_phrases >= 5 and unique_markers >= 4:
        consistency_bonus = 5.0
    elif word_count > 20 and found_phrases >= 3 and unique_markers >= 3:
        consistency_bonus = 3.0
    else:
        consistency_bonus = 0.0
    total = round(vocab_score + ngram_score + marker_score + cadence_score + char_score + phrase_score + brevity_bonus + consistency_bonus, 1)
    details = {
        "vocab_score": round(vocab_score, 1),
        "ngram_score": round(ngram_score, 1),
        "marker_score": round(marker_score, 1),
        "cadence_score": round(cadence_score, 1),
        "char_score": round(char_score, 1),
        "phrase_score": round(phrase_score, 1),
        "brevity_bonus": round(brevity_bonus, 1),
        "consistency_bonus": round(consistency_bonus, 1),
        "markers_found": sorted(set(marker_hits)),
        "avg_words_per_sentence": round(avg_words, 1),
        "corpus_lines": len(corpus_lines),
    }
    return total, details

def main():
    if len(sys.argv) < 2:
        print("Usage: drifter-voice-scorer.py \"<response>\"")
        sys.exit(1)
    candidate = " ".join(sys.argv[1:])
    corpus = load_corpus()
    total, d = score_response(candidate, corpus)
    status = "PASS" if total >= 55.0 else ("PARTIAL" if total >= 40.0 else "FAIL")
    print(f"=== DRIFTER STATISTICAL VOICE SCORER ===")
    print(f"Corpus size: {d['corpus_lines']} canonical lines")
    print(f"Total Score: {total}/100 ({status})")
    print(f"  Vocabulary overlap : {d['vocab_score']}/20")
    print(f"  N-gram phrasing    : {d['ngram_score']}/20")
    print(f"  Signature markers  : {d['marker_score']}/25 ({', '.join(d['markers_found']) or 'none'})")
    print(f"  Sentence cadence   : {d['cadence_score']}/15 (avg {d['avg_words_per_sentence']} words/sentence)")
    print(f"  Char n-gram        : {d['char_score']}/10")
    print(f"  Signature phrases  : {d['phrase_score']}/15")
    print(f"  Brevity bonus     : {d['brevity_bonus']}/5")
    sys.exit(0 if total >= 55.0 else 1)

if __name__ == "__main__":
    main()
