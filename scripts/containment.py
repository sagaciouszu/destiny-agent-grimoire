#!/usr/bin/env python3
"""Containment / dedupe helper for the Destiny lore corpus.

Given a candidate line of game text, decide whether the corpus already holds
that text (or a near-identical fragment of it) so an extractor can drop the
candidate instead of storing a duplicate.

The definition is deliberately conservative:

  * a candidate is a *fragment* of a known text when its normalised form is a
    contiguous substring of a normalised known text, **or**
  * the candidate shares enough tokens with a known text, is no longer than
    that text, and the *fragment ratio*
    ``tokens(candidate) / tokens(known)`` is at least ``threshold`` (0.9 by
    default).

Short candidates are guarded: they need at least ``MIN_TOKENS`` (8) tokens
**or** an exact normalised substring of at least ``MIN_SUBSTRING_CHARS`` (40)
characters. Without that guard, two-word labels ("Kill Clip", "Defeat the
Vex") match ordinary prose all over the corpus.

Normalisation mirrors ``db/migrate.py``'s ``norm_text()`` exactly, including
its punctuation-only fallback. It is copied rather than imported so importing
this module never opens or removes the SQLite database.

Usage (as a library)::

    from containment import ContainmentIndex
    index = ContainmentIndex.from_jsonl('archive/data/items.jsonl')
    if index.is_fragment(line):
        ...

Usage (CLI)::

    python3 scripts/containment.py --jsonl archive/data/items.jsonl \\
        --lines live-lines.txt --dump-matches matches.jsonl

The CLI prints a JSON statistics object to stdout. ``--lines`` accepts plain
text (one candidate per line) or JSONL records carrying ``text``/``line``.
"""
import argparse
import bisect
import json
import os
import re
import sys

MIN_TOKENS = 8
MIN_SUBSTRING_CHARS = 40
DEFAULT_THRESHOLD = 0.9


def normalise(s):
    """Normalise text for substring / token comparison.

    Mirrors ``db/migrate.py`` ``norm_text()``:

    * lowercase;
    * ellipsis -> three dots, curly apostrophe -> straight, en/em dash -> '-';
    * every run of characters outside ``[a-z0-9 ]`` becomes a single space;
    * collapse whitespace;
    * punctuation-only strings fall back to the lowered text with LIKE
      wildcards removed (so ``":)"`` and friends stay searchable).
    """
    if s is None:
        return ''
    if not isinstance(s, str):
        s = str(s)
    s = s.lower()
    s = s.replace('…', '...').replace('’', "'").replace('—', '-').replace('–', '-')
    n = re.sub(r'[^a-z0-9 ]+', ' ', s)
    n = re.sub(r'\s+', ' ', n).strip()
    if n:
        return n
    return re.sub(r'\s+', ' ', s.replace('%', ' ').replace('_', ' ')).strip()


# ``normalize`` is the more common spelling; keep both without a second impl.
normalize = normalise


class Match:
    """A single containment hit.

    ``kind`` is ``exact`` (normalised candidate equals the known text),
    ``substring`` (candidate is a contiguous part of the known text) or
    ``overlap`` (token-level near-fragment).

    ``ratio`` is ``tokens(candidate) / tokens(known)``. ``coverage`` is the
    fraction of the candidate's distinct tokens present in the known text.
    """

    __slots__ = ('kind', 'source', 'ref', 'ratio', 'coverage', 'known')

    def __init__(self, kind, source, ref, ratio, coverage, known):
        self.kind = kind
        self.source = source
        self.ref = ref
        self.ratio = ratio
        self.coverage = coverage
        self.known = known

    def as_dict(self):
        return {
            'kind': self.kind,
            'source': self.source,
            'ref': self.ref,
            'ratio': round(self.ratio, 6),
            'coverage': round(self.coverage, 6),
            'known': self.known,
        }

    def __repr__(self):
        return (f'Match(kind={self.kind!r}, source={self.source!r}, '
                f'ref={self.ref!r}, ratio={self.ratio:.3f}, '
                f'coverage={self.coverage:.3f})')


class ContainmentIndex:
    """An in-memory index of known corpus texts.

    Build it once (``from_jsonl``) and query it many times. Identical
    normalised texts are stored once; the first loaded source/ref wins.
    """

    def __init__(self, threshold=DEFAULT_THRESHOLD, min_tokens=MIN_TOKENS,
                 min_substring_chars=MIN_SUBSTRING_CHARS):
        self.threshold = float(threshold)
        self.min_tokens = int(min_tokens)
        self.min_substring_chars = int(min_substring_chars)

        self._texts = []        # normalised known texts, unique
        self._tokens = []       # set of tokens per text
        self._lengths = []      # token count per text
        self._meta = []         # (source, ref) per text
        self._exact = {}        # normalised text -> index
        self._inv = {}          # token -> list of indices
        self._offsets = []      # start offset of each text in _blob
        self._blob = None       # all texts joined by newline
        self._source_texts = {}  # source -> set of normalised texts

    # ------------------------------------------------------------ building --

    @classmethod
    def from_jsonl(cls, *paths, **kwargs):
        """Build an index from one or more JSONL files.

        Each record may be a flat object with a ``text`` field (the items
        shape) or a transcript/caption record with a ``lines`` list whose
        entries carry ``text``/``line``. A single list/tuple of paths is also
        accepted.
        """
        if len(paths) == 1 and isinstance(paths[0], (list, tuple, set)):
            paths = tuple(paths[0])
        if not paths:
            raise ValueError('from_jsonl() needs at least one path')
        text_key = kwargs.pop('text_key', 'text')
        ref_key = kwargs.pop('ref_key', None)
        index = cls(**kwargs)
        for path in paths:
            index.add_jsonl(path, text_key=text_key, ref_key=ref_key)
        index.finalise()
        return index

    def add_jsonl(self, path, text_key='text', ref_key=None):
        """Load one JSONL file and return the number of records read."""
        read = 0
        source = os.fspath(path)
        with open(source, encoding='utf-8') as fh:
            for raw in fh:
                raw = raw.strip()
                if not raw:
                    continue
                obj = json.loads(raw)
                read += 1
                if isinstance(obj, dict) and isinstance(obj.get('lines'), list):
                    base = obj.get('slug') or obj.get('id') or obj.get('title')
                    for seq, line in enumerate(obj['lines']):
                        if not isinstance(line, dict):
                            continue
                        text = line.get(text_key) or line.get('text') or line.get('line')
                        if not text:
                            continue
                        ref = line.get('hash') or line.get('ref')
                        if ref is None and base is not None:
                            ref = f'{base}:{seq}'
                        self.add_text(text, source=source, ref=ref)
                else:
                    text = obj.get(text_key) if isinstance(obj, dict) else obj
                    if not text:
                        continue
                    ref = None
                    if isinstance(obj, dict):
                        key = ref_key or ('slug' if 'slug' in obj else 'url')
                        ref = obj.get(key) or obj.get('slug') or obj.get('url')
                    self.add_text(text, source=source, ref=ref)
        return read

    def add_text(self, text, source='<memory>', ref=None):
        """Add one known text. Returns True if it was new."""
        norm = normalise(text)
        if not norm:
            return False
        self._source_texts.setdefault(source, set()).add(norm)
        if norm in self._exact:
            return False
        i = len(self._texts)
        tokens = norm.split()
        self._texts.append(norm)
        self._tokens.append(set(tokens))
        self._lengths.append(len(tokens))
        self._meta.append((source, ref))
        self._exact[norm] = i
        for token in set(tokens):
            self._inv.setdefault(token, []).append(i)
        return True

    def finalise(self):
        """Seal the index: build the contiguous blob used for substring hits."""
        self._offsets = []
        pos = 0
        parts = []
        for text in self._texts:
            self._offsets.append(pos)
            parts.append(text)
            pos += len(text) + 1
        self._blob = '\n'.join(parts)
        return self

    # ------------------------------------------------------------- querying --

    @property
    def size(self):
        """Number of unique normalised texts held by the index."""
        return len(self._texts)

    def indexed_by_source(self):
        """Mapping of source path -> number of unique texts it contributed."""
        return {src: len(texts) for src, texts in self._source_texts.items()}

    def is_fragment(self, candidate, threshold=None):
        """True when *candidate* duplicates text the index already holds."""
        return self.match(candidate, threshold=threshold) is not None

    def match(self, candidate, threshold=None):
        """Return the best :class:`Match` for *candidate*, or ``None``."""
        thr = self.threshold if threshold is None else float(threshold)
        if not 0 < thr <= 1:
            raise ValueError(f'threshold must be in (0, 1], got {thr}')
        norm = normalise(candidate)
        if not norm:
            return None
        cand_tokens = norm.split()
        n_cand = len(cand_tokens)

        # Short-line guard: <8 tokens is only allowed as a long substring.
        if n_cand < self.min_tokens and len(norm) < self.min_substring_chars:
            return None

        # 1) exact normalised equality
        i = self._exact.get(norm)
        if i is not None:
            source, ref = self._meta[i]
            return Match('exact', source, ref, 1.0, 1.0, self._texts[i])

        # 2) contiguous substring of a known text
        if self._blob:
            pos = self._blob.find(norm)
            if pos >= 0:
                i = bisect.bisect_right(self._offsets, pos) - 1
                if i >= 0:
                    denom = self._lengths[i] or 1
                    source, ref = self._meta[i]
                    return Match('substring', source, ref,
                                 n_cand / denom, 1.0, self._texts[i])

        # 3) token-level near-fragment (candidate must not be the longer text)
        if n_cand < self.min_tokens:
            return None
        cand_set = set(cand_tokens)
        postings = None
        for token in cand_set:
            posting = self._inv.get(token)
            if posting is not None and (postings is None or len(posting) < len(postings)):
                postings = posting
        if not postings:
            return None

        max_known_tokens = int(n_cand / thr) if thr > 0 else n_cand
        best = None
        best_key = None
        for i in postings:
            known_len = self._lengths[i]
            if known_len < n_cand or known_len > max_known_tokens:
                continue
            coverage = len(cand_set & self._tokens[i]) / len(cand_set)
            if coverage < thr:
                continue
            ratio = n_cand / known_len
            if ratio < thr:
                continue
            key = (coverage, ratio)
            if best_key is None or key > best_key:
                best_key = key
                best = (i, coverage, ratio)
        if best is None:
            return None
        i, coverage, ratio = best
        source, ref = self._meta[i]
        return Match('overlap', source, ref, ratio, coverage, self._texts[i])


# ------------------------------------------------------------------- CLI ----

def _iter_candidate_lines(path):
    """Yield candidates from a plain-text or JSONL line file (``-`` = stdin)."""
    fh = sys.stdin if path == '-' else open(path, encoding='utf-8')
    try:
        for raw in fh:
            raw = raw.rstrip('\n').rstrip('\r')
            if not raw.strip():
                continue
            stripped = raw.lstrip()
            if stripped.startswith('{'):
                try:
                    obj = json.loads(stripped)
                except json.JSONDecodeError:
                    yield raw
                    continue
                text = obj.get('text') or obj.get('line') or obj.get('body')
                if text:
                    yield text
            else:
                yield raw
    finally:
        if fh is not sys.stdin:
            fh.close()


def main(argv=None):
    parser = argparse.ArgumentParser(
        description='Report candidate lines already contained in the corpus.')
    parser.add_argument('--jsonl', action='append', default=None,
                        metavar='PATH',
                        help='known-text JSONL (repeatable; default items.jsonl)')
    parser.add_argument('--lines', action='append', default=[], metavar='FILE',
                        help='candidate lines: plain text or JSONL (repeatable; - = stdin)')
    parser.add_argument('--text', action='append', default=[], metavar='TEXT',
                        help='inline candidate line (repeatable)')
    parser.add_argument('--threshold', type=float, default=DEFAULT_THRESHOLD,
                        help=f'token/fragment ratio threshold (default {DEFAULT_THRESHOLD})')
    parser.add_argument('--dump-matches', metavar='FILE',
                        help='write one JSON object per matched candidate')
    parser.add_argument('--quiet', action='store_true',
                        help='suppress the "indexed" line on stderr')
    args = parser.parse_args(argv)

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    jsonl = args.jsonl or [os.path.join(root, 'archive', 'data', 'items.jsonl')]
    index = ContainmentIndex.from_jsonl(*jsonl, threshold=args.threshold)
    if not args.quiet:
        print(f'containment: {index.size} unique texts indexed', file=sys.stderr)

    candidates = list(args.text)
    for path in args.lines:
        candidates.extend(_iter_candidate_lines(path))

    by_kind = {'exact': 0, 'substring': 0, 'overlap': 0}
    by_source = {path: 0 for path in jsonl}
    matches = []
    matched = 0
    for candidate in candidates:
        hit = index.match(candidate, threshold=args.threshold)
        if hit is None:
            continue
        matched += 1
        by_kind[hit.kind] = by_kind.get(hit.kind, 0) + 1
        by_source[hit.source] = by_source.get(hit.source, 0) + 1
        if args.dump_matches:
            record = {'candidate': candidate}
            record.update(hit.as_dict())
            matches.append(record)

    total = len(candidates)
    indexed = index.indexed_by_source()
    stats = {
        'total': total,
        'matched': matched,
        'unmatched': total - matched,
        'threshold': args.threshold,
        'by_kind': by_kind,
        'by_source': by_source,
        'sources': [{'path': p, 'unique_texts': indexed.get(p, 0)}
                    for p in jsonl],
    }
    if args.dump_matches:
        with open(args.dump_matches, 'w', encoding='utf-8') as fh:
            for record in matches:
                fh.write(json.dumps(record, ensure_ascii=False) + '\n')
        stats['dump_matches'] = args.dump_matches

    json.dump(stats, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write('\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
