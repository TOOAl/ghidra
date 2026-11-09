"""💡 Stage J — SemanticMemory: a meaning space trained ONLY on our own wiki.

Before this, "remembering" was word matching: a question had to contain the
same words as a note, or the note did not exist as far as the brain was
concerned.  Ask "기억을 작게 줄이는 방법" and the 4-bit quantization note was
invisible — not one word overlaps.

This module gives the brain distributional semantics, the same trick real
language models are built on, but small enough to live on an external drive:

    "You shall know a word by the company it keeps."  — J. R. Firth, 1957

We read our OWN Markdown memories, count which words sit near each other, and
turn those counts into vectors (PPMI + L2, then one round of second-order
smoothing because a personal wiki is a tiny corpus).  Words that never appear
in the same sentence but live in the same neighbourhood — 양자화 / 압축 /
절약 — end up pointing in similar directions, so their notes become findable
by MEANING.

Nothing here is downloaded, no API is called, no external model is loaded:
the vectors are grown from the vault and stored quantized to int8 in
`state/semantic.json`, with the reconstruction fidelity measured and reported
rather than assumed.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

__all__ = [
    "SemanticMemory",
    "tokenize",
    "cosine",
]

_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_.\-]{1,24}|[가-힣]{2,14}")

# Same normalisation `wiki_gardener.extract_keywords` uses, kept local on
# purpose: this module must stay importable from anywhere with zero project
# dependencies (an import cycle here would break `wiki_gardener` itself).
_SUFFIXES = (
    "에서는", "으로서", "이라서", "입니다", "합니다", "하기", "에서", "으로",
    "에게", "까지", "부터", "처럼", "만의", "들이", "들은", "들을", "이다",
    "이고", "이나", "하는", "되는", "이라는", "같은", "위한",
)
_PARTICLES = ("은", "는", "이", "가", "을", "를", "의", "에", "로", "도", "만", "과", "와", "으로")
_STOP = {
    "그리고", "하지만", "그러나", "이것", "저것", "그것", "우리", "위해", "통해", "대한", "대한한",
    "같은", "수", "때", "더", "매우", "정말", "또한", "즉", "등", "및", "또", "the", "and", "for",
    "with", "this", "that", "from", "are", "is", "of", "to",
}

# Verb/adjective endings that a plain particle stripper leaves behind
# ("토론해서" -> "토론").  Only used as a fallback for UNKNOWN words, so a
# known word is never mangled.
_ENDINGS = (
    "해서", "하여", "했던", "었던", "았던", "었다", "았다", "는다", "습니다",
    "세요", "거나", "면서", "는데", "라고", "까지", "보다", "처럼", "만큼",
    "부터", "에게", "께서", "라도", "조차", "나마", "이다", "아닌", "없는",
    "있는", "된다", "한다", "해도", "해서", "려고", "려고", "으면", "면서도",
    "고", "서", "면", "니", "게", "라", "야", "여", "죠", "요", "던", "든",
)

_WINDOW = 4          # words within ±4 of each other are "company"
_MAX_VOCAB = 500     # rare-but-central words (용량, 토론) carry the most meaning
_KEEP_PER_WORD = 18  # ...so instead of shrinking the vocabulary we sparsify the
                     # vectors: keep each word's strongest neighbours only
_MIN_PMI = 0.04
_PMI_CAP = 4.5       # rare-rare pairs otherwise dominate the whole space
_TITLE_REPEAT = 3
_TAG_REPEAT = 2


def tokenize(text: str) -> List[str]:
    """Normalise raw text into meaning-bearing tokens."""
    out: List[str] = []
    for tok in _TOKEN_RE.findall(str(text or "")):
        low = tok.lower()
        if re.match(r"^[가-힣]+$", low) and len(low) >= 3:
            for suf in _SUFFIXES:
                if low.endswith(suf) and len(low) - len(suf) >= 2:
                    low = low[: -len(suf)]
                    break
            if len(low) >= 3 and low[-1] in _PARTICLES:
                low = low[:-1]
        if len(low) >= 2 and low not in _STOP:
            out.append(low)
    return out


def cosine(a: Sequence[float], b: Sequence[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na <= 1e-12 or nb <= 1e-12:
        return 0.0
    return dot / (na * nb)


def _char_grams(word: str, n: int = 3) -> set:
    padded = f"^{word}$"
    return {padded[i:i + n] for i in range(max(0, len(padded) - n + 1))}


def note_text(n: Dict[str, Any]) -> str:
    """The text a note is known by, with title/tags repeated so they weigh more."""
    title = str(n.get("title", ""))
    tags = " ".join(str(t) for t in (n.get("tags") or []))
    summary = str(n.get("summary", ""))
    body = str(n.get("body", ""))
    return " ".join([title] * _TITLE_REPEAT + [tags] * _TAG_REPEAT + [summary, body])


class SemanticMemory:
    """A tiny, self-trained meaning space for the brain's own Markdown vault."""

    def __init__(self, state_dir: Path) -> None:
        self.state_dir = Path(state_dir)
        self.path = self.state_dir / "semantic.json"
        self.vocab: List[str] = []
        self.index: Dict[str, int] = {}
        self.vectors: Dict[str, List[float]] = {}
        self.idf: Dict[str, float] = {}
        self.stats: Dict[str, Any] = {
            "trained": False,
            "vocab_size": 0,
            "dims": 0,
            "notes": 0,
            "quant_bits": 8,
            "cosine_fidelity_pct": None,
            "fingerprint": "",
            "trained_ts": "",
        }
        self._grams: Dict[str, set] = {}
        self._note_cache: Dict[str, List[float]] = {}
        self._q_cache: Dict[str, List[float]] = {}
        self._load()

    # ---------------------------------------------------------------- storage
    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return
        self.vocab = list(raw.get("vocab") or [])
        self.index = {w: i for i, w in enumerate(self.vocab)}
        self.idf = {k: float(v) for k, v in (raw.get("idf") or {}).items()}
        self.stats = dict(self.stats, **(raw.get("stats") or {}))
        self._grams = {w: _char_grams(w) for w in self.vocab}
        # int8 vectors + per-vector scale -> reconstructed fp32 rows
        for word, payload in (raw.get("vectors") or {}).items():
            scale = float(payload.get("s") or 0.0)
            vec = [0.0] * len(self.vocab)
            for pair in str(payload.get("q") or "").split(","):
                if not pair:
                    continue
                try:
                    idx_s, val_s = pair.split(":")
                    idx, val = int(idx_s), int(val_s)
                except Exception:
                    continue
                if 0 <= idx < len(vec):
                    vec[idx] = val * scale
            if word in self.index:
                self.vectors[word] = vec

    def _save(self) -> None:
        try:
            self.state_dir.mkdir(parents=True, exist_ok=True)
            out: Dict[str, Any] = {"vocab": self.vocab, "idf": self.idf, "stats": self.stats, "vectors": {}}
            for word, vec in self.vectors.items():
                peak = max((abs(x) for x in vec), default=0.0)
                if peak <= 1e-12:
                    continue
                scale = peak / 127.0
                out["vectors"][word] = {
                    "s": round(scale, 8),
                    "q": ",".join(
                        f"{i}:{int(round(v / scale))}" for i, v in enumerate(vec) if abs(v) > 1e-9
                    ),
                }
            self.path.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass  # a failed cache must never stop the brain from thinking

    # -------------------------------------------------------------- training
    @staticmethod
    def fingerprint(notes: Sequence[Dict[str, Any]]) -> str:
        h = hashlib.sha1()
        for n in sorted(notes, key=lambda x: str(x.get("slug") or x.get("title"))):
            h.update(f"{n.get('slug')}|{n.get('title')}|{len(str(n.get('body') or ''))}".encode("utf-8"))
        return h.hexdigest()[:16]

    def ensure_trained(self, notes: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
        """Train only when the vault actually changed — the cache is a fingerprint away."""
        fp = self.fingerprint(notes)
        if self.stats.get("trained") and self.stats.get("fingerprint") == fp and self.vectors:
            return dict(self.stats, retrained=False)
        return self.train(notes)

    def train(self, notes: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
        usable = [n for n in notes if str(n.get("title") or "").strip()]
        if len(usable) < 2:
            self.stats = dict(self.stats, trained=False, notes=len(usable), vocab_size=0, dims=0)
            return dict(self.stats, retrained=False)

        docs: List[List[str]] = []
        df: Counter = Counter()
        co: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
        freq: Counter = Counter()
        for n in usable:
            toks = tokenize(note_text(n))
            docs.append(toks)
            df.update(set(toks))
            freq.update(toks)
            for i, a in enumerate(toks):
                lo = max(0, i - _WINDOW)
                for b in toks[lo:i]:
                    co[a][b] += 1.0
                    co[b][a] += 1.0
            # A personal wiki is a TINY corpus, so "lives in the same note" is
            # real evidence too — weighted half as much as sitting side by side.
            for a in set(toks):
                for b in set(toks):
                    if a != b:
                        co[a][b] += 0.25

        # Vocabulary policy, in priority order:
        #   1. words seen at least twice (they have a distribution to learn from)
        #   2. words that appear once but in a TITLE/TAG/SUMMARY — the dense part
        #      of a note, where a single mention is still the note's own concept
        #      ("용량" appears exactly once in the whole vault and is precisely
        #      what the quantization note is about)
        #   3. any remaining word, most frequent first
        # Prose hapax are what the cap drops, never key concepts.
        dense: set = set()
        for n in usable:
            dense.update(tokenize(f"{n.get('title','')} {' '.join(n.get('tags') or [])} {n.get('summary','')}"))
        twice = [w for w, c in freq.most_common() if c >= 2]
        once_dense = [w for w, c in freq.most_common() if c == 1 and w in dense]
        once_rest = [w for w, c in freq.most_common() if c == 1 and w not in dense]
        vocab = list(dict.fromkeys(twice + once_dense + once_rest))[:_MAX_VOCAB]
        if len(vocab) < 4:
            vocab = [w for w, _ in freq.most_common(_MAX_VOCAB)]
        self.vocab = vocab
        self.index = {w: i for i, w in enumerate(vocab)}
        self._grams = {w: _char_grams(w) for w in vocab}
        n_docs = max(1, len(docs))
        self.idf = {w: math.log((n_docs + 1) / (df.get(w, 0) + 1)) + 1.0 for w in vocab}

        # Positive pointwise mutual information: how much MORE often two words
        # meet than chance would predict.  Chance is what makes "그리고" useless
        # and "양자화 ↔ 압축" meaningful.
        total = float(sum(sum(c.values()) for c in co.values())) or 1.0
        co = {w: c for w, c in co.items()}
        row_tot = {w: float(sum(co[w].values())) for w in vocab}
        raw: Dict[str, List[float]] = {}
        for w in vocab:
            vec = [0.0] * len(vocab)
            for other, cnt in co[w].items():
                j = self.index.get(other)
                if j is None or cnt <= 0:
                    continue
                pmi = math.log((cnt * total) / max(1.0, row_tot[w] * row_tot.get(other, 1.0)))
                if pmi > _MIN_PMI:
                    # Capped, then discounted by how often the pair was actually
                    # seen: one sighting in a tiny vault is a rumour, not a fact.
                    vec[j] = min(pmi, _PMI_CAP) * (cnt / (cnt + 1.0))
            norm = math.sqrt(sum(x * x for x in vec))
            raw[w] = [x / norm for x in vec] if norm > 1e-12 else vec

        self.vectors = self._sparsify(raw)

        # One round of second-order smoothing: a personal wiki is a tiny corpus,
        # so a word also inherits a little of its closest neighbours' meaning.
        # Second-order smoothing over each word's OWN strongest partners (not a
        # scan of the whole vocabulary — that would be O(V^3) and too slow to run
        # on the host machine while the brain is awake).
        partners = {
            w: [o for o, _ in sorted(co[w].items(), key=lambda kv: kv[1], reverse=True)
                if o in self.index and o != w][:4]
            for w in vocab
        }
        raw2: Dict[str, List[float]] = {}
        for w in vocab:
            base = raw[w]
            strong = [o for o in partners[w] if any(raw.get(o) or [])]
            if strong and any(base):
                acc = [0.88 * x for x in base]
                share = 0.12 / len(strong)
                for o in strong:
                    acc = [a + share * b for a, b in zip(acc, raw[o])]
                norm = math.sqrt(sum(x * x for x in acc))
                base = [x / norm for x in acc] if norm > 1e-12 else acc
            raw2[w] = base
        self.vectors = raw2

        fidelity = self._measure_fidelity()
        import datetime as _dt

        self._note_cache.clear()
        self._q_cache.clear()
        self.stats = {
            "trained": True,
            "vocab_size": len(vocab),
            "dims": len(vocab),
            "notes": len(usable),
            "pairs_observed": int(sum(len(c) for c in co.values())),
            "quant_bits": 8,
            "cosine_fidelity_pct": fidelity,
            "fingerprint": self.fingerprint(usable),
            "trained_ts": _dt.datetime.now().strftime("%H:%M:%S"),
            "cache_kb": 0,
        }
        self._save()
        try:
            self.stats["cache_kb"] = round(self.path.stat().st_size / 1024.0, 1)
        except Exception:
            pass
        return dict(self.stats, retrained=True)

    @staticmethod
    def _sparsify(raw: Dict[str, List[float]]) -> Dict[str, List[float]]:
        """Keep only each word's strongest neighbours.

        With 420 dimensions a dense capsule would be fat and noisy; a word's
        meaning lives in its top handful of neighbours, so pruning the tail both
        shrinks the file and sharpens the discrimination.
        """
        out: Dict[str, List[float]] = {}
        for w, vec in raw.items():
            nz = [(v, i) for i, v in enumerate(vec) if v > 0.0]
            if len(nz) <= _KEEP_PER_WORD:
                out[w] = vec
                continue
            nz.sort(reverse=True)
            kept = [0.0] * len(vec)
            for v, i in nz[:_KEEP_PER_WORD]:
                kept[i] = v
            norm = math.sqrt(sum(x * x for x in kept))
            out[w] = [x / norm for x in kept] if norm > 1e-12 else kept
        return out

    def _measure_fidelity(self) -> Optional[float]:
        """Cosine similarity between fp32 vectors and their int8 round trip."""
        sims: List[float] = []
        for w, vec in list(self.vectors.items())[:40]:
            peak = max((abs(x) for x in vec), default=0.0)
            if peak <= 1e-12:
                continue
            scale = peak / 127.0
            recon = [round(v / scale) * scale for v in vec]
            sims.append(cosine(vec, recon))
        return round(100.0 * sum(sims) / len(sims), 3) if sims else None

    # --------------------------------------------------------------- meaning
    def _word_vector(self, tok: str) -> Tuple[List[float], float]:
        """Vector for a token; unknown tokens bridge in via character n-grams.

        Korean bends its words (양자화 → 양자화기), so a strict dictionary would
        call the inflected form meaningless.  Character-trigram overlap finds
        the known word it is built from and lends a fraction of its meaning.
        """
        vec = self.vectors.get(tok)
        if vec is not None and any(vec):
            return vec, 1.0
        # Korean keeps its stem as a prefix ("줄여서" -> "줄이"), so before
        # guessing by shape we simply try dropping one or two ending letters.
        if re.match(r"^[가-힣]{3,}$", tok):
            # known ending first ("토론해서" -> "토론"), then a blind 1-2 letter cut
            for end in _ENDINGS:
                if tok.endswith(end) and len(tok) - len(end) >= 2:
                    sv = self.vectors.get(tok[: -len(end)])
                    if sv is not None and any(sv):
                        return sv, 0.9
                    break
            for cut in (1, 2):
                stem = tok[:-cut]
                sv = self.vectors.get(stem)
                if sv is not None and any(sv):
                    return sv, 0.85
        if re.match(r"^[가-힣]{4,}$", tok):
            parts: List[Tuple[str, List[float]]] = []
            for cut in range(2, len(tok) - 1):
                for piece in (tok[:cut], tok[cut:]):
                    pv = self.vectors.get(piece)
                    if pv is not None and any(pv):
                        parts.append((piece, pv))
            if parts:
                # Blend the known pieces; a compound means both of its halves.
                acc = [0.0] * len(self.vocab)
                for _, pv in parts[:2]:
                    acc = [a + b for a, b in zip(acc, pv)]
                norm = math.sqrt(sum(x * x for x in acc))
                if norm > 1e-12:
                    return [x / norm for x in acc], 0.75
        grams = _char_grams(tok)
        if not grams or not self._grams:
            return [], 0.0
        best, best_sim = None, 0.0
        for w, wg in self._grams.items():
            if not wg or not any(self.vectors.get(w) or []):
                continue
            sim = len(grams & wg) / len(grams | wg)
            if sim > best_sim:
                best, best_sim = w, sim
        if best is None or best_sim < 0.30:
            return [], 0.0
        return self.vectors[best], 0.6 * best_sim

    def text_vector(self, text: str) -> List[float]:
        """IDF-weighted mean of token vectors — the meaning of a whole phrase."""
        if not self.vocab:
            return []
        acc = [0.0] * len(self.vocab)
        weight_sum = 0.0
        for tok in tokenize(text):
            vec, conf = self._word_vector(tok)
            if not vec:
                continue
            w = self.idf.get(tok, self.idf.get(tok, 1.2)) * conf
            acc = [a + w * b for a, b in zip(acc, vec)]
            weight_sum += w
        if weight_sum <= 1e-12:
            return []
        acc = [x / weight_sum for x in acc]
        norm = math.sqrt(sum(x * x for x in acc))
        return [x / norm for x in acc] if norm > 1e-12 else []

    def coverage(self, text: str) -> Dict[str, Any]:
        """How many of a sentence's words the meaning space actually knows.

        A similarity computed from 1 of 6 words is not the same kind of claim as
        one computed from 6 of 6, so the number is reported next to the score.
        """
        toks = list(dict.fromkeys(tokenize(text)))
        if not toks:
            return {"known": 0, "total": 0, "pct": 0.0, "unknown": []}
        known, unknown = [], []
        for t in toks:
            vec, _ = self._word_vector(t)
            (known if vec else unknown).append(t)
        return {
            "known": len(known),
            "total": len(toks),
            "pct": round(100.0 * len(known) / len(toks), 1),
            "unknown": unknown[:6],
        }

    def note_vector(self, note: Dict[str, Any]) -> List[float]:
        """Cached meaning vector of one note (the vault changes rarely, chats don't)."""
        key = f"{note.get('slug') or note.get('title')}|{note.get('updated_at','')}|{len(str(note.get('body') or ''))}"
        vec = self._note_cache.get(key)
        if vec is None:
            vec = self.text_vector(note_text(note))
            if len(self._note_cache) > 400:
                self._note_cache.clear()
            self._note_cache[key] = vec
        return vec

    def query_vector(self, query: str) -> List[float]:
        vec = self._q_cache.get(query)
        if vec is None:
            vec = self.text_vector(query)
            if len(self._q_cache) > 120:
                self._q_cache.clear()
            self._q_cache[query] = vec
        return vec

    def similarity(self, query: str, note: Dict[str, Any]) -> float:
        """How close a question and a note are in MEANING (0..1, never negative)."""
        if not self.vectors:
            return 0.0
        qv = self.query_vector(query)
        nv = self.note_vector(note)
        if not qv or not nv:
            return 0.0
        return max(0.0, round(cosine(qv, nv), 4))

    def bridges(self, query: str, note: Dict[str, Any], top_k: int = 3) -> List[Dict[str, Any]]:
        """The word pairs that carry the meaning — so a decision can be explained.

        A score nobody can inspect is a score nobody should trust, so we show
        WHICH words reached across: 「압축 ↔ 양자화」 rather than a bare number.
        """
        if not self.vectors:
            return []
        qv = self.query_vector(query)
        nv = self.note_vector(note)
        if not qv or not nv:
            return []
        pairs: List[Tuple[float, str, str]] = []
        for qt in dict.fromkeys(tokenize(query)):
            qvec, _ = self._word_vector(qt)
            if not qvec or not any(qvec):
                continue
            for nt in dict.fromkeys(tokenize(f"{note.get('title','')} {note.get('summary','')}")):
                nvec, _ = self._word_vector(nt)
                if not nvec or not any(nvec) or nt == qt:
                    continue
                pairs.append((cosine(qvec, nvec), qt, nt))
        pairs.sort(reverse=True)
        # No threshold on purpose: a meaning score the user cannot inspect is a
        # score the user should not have to trust, so we always show the pairs
        # that actually carried it, even when they are weak.
        return [{"similarity": round(s, 3), "query_word": q, "note_word": n} for s, q, n in pairs[:top_k]]

    # ------------------------------------------------------------------
    # Stage K — note ↔ note meaning.  Stage J only ever compared a QUESTION
    # with a note (recall).  The organizing muscle, the synapse weaver and the
    # vault's own blind spots all need to compare a NOTE with a NOTE, so the
    # same self-learned space gets a second door here.  Nothing new is
    # downloaded or invented: it is the very same vectors, squared.
    # ------------------------------------------------------------------
    def pair_similarity(self, a: Dict[str, Any], b: Dict[str, Any]) -> float:
        """How close two NOTES are in meaning (0..1) — what weaving decides on."""
        if not self.vectors:
            return 0.0
        va, vb = self.note_vector(a), self.note_vector(b)
        if not va or not vb:
            return 0.0
        return max(0.0, round(cosine(va, vb), 4))

    def pair_bridges(self, a: Dict[str, Any], b: Dict[str, Any], top_k: int = 3) -> List[Dict[str, Any]]:
        """The words that carry a note↔note link, so weaving stays inspectable."""
        return self.bridges(f"{a.get('title','')} {a.get('summary','')}", b, top_k=top_k)

    def neighbours(self, note: Dict[str, Any], notes: Sequence[Dict[str, Any]], top_k: int = 3) -> List[Dict[str, Any]]:
        """The notes closest in MEANING to this one, with the words that bridge them.

        Sorted strongest first; empty when the space is untrained, because an
        untrained guess dressed up as a neighbour would be a lie.
        """
        if not self.vectors or not notes:
            return []
        v = self.note_vector(note)
        if not v:
            return []
        me = note.get("slug") or note.get("title")
        out: List[Dict[str, Any]] = []
        for m in notes:
            if (m.get("slug") or m.get("title")) == me:
                continue
            mv = self.note_vector(m)
            if not mv:
                continue
            c = cosine(v, mv)
            if c <= 0.02:
                continue
            out.append(
                {
                    "slug": m.get("slug"),
                    "title": m.get("title"),
                    "cos": round(c, 3),
                    "bridges": self.pair_bridges(note, m, top_k=3),
                }
            )
        out.sort(key=lambda r: -r["cos"])
        return out[:top_k]

    def orphans(self, notes: Sequence[Dict[str, Any]], cos_min: float = 0.30, top_k: int = 6) -> List[Dict[str, Any]]:
        """Blind spots: notes whose STRONGEST meaning neighbour is still weak.

        This is the vault asking for help.  A note nobody is close to in meaning
        is either brand new (nothing else covers that idea yet) or written in
        words the rest of the vault never uses — in both cases the honest move
        is to point at it and say "I have no context for this", not to glue it
        to the nearest thing.  Weakest first, and only up to `top_k`.
        """
        if not self.vectors or len(notes) < 2:
            return []
        vecs = {}
        for n in notes:
            v = self.note_vector(n)
            if v:
                vecs[n.get("slug") or n.get("title")] = v
        out: List[Dict[str, Any]] = []
        for n in notes:
            key = n.get("slug") or n.get("title")
            v = vecs.get(key)
            if not v:
                continue
            best, best_key = 0.0, ""
            for k2, v2 in vecs.items():
                if k2 == key:
                    continue
                c = cosine(v, v2)
                if c > best:
                    best, best_key = c, k2
            if best < cos_min:
                nb = next((m for m in notes if (m.get("slug") or m.get("title")) == best_key), None)
                out.append(
                    {
                        "slug": n.get("slug"),
                        "title": n.get("title"),
                        "best_cos": round(best, 3),
                        "nearest": (nb or {}).get("title"),
                        "nearest_slug": best_key,
                        "bridges": self.pair_bridges(n, nb, top_k=2) if nb else [],
                    }
                )
        out.sort(key=lambda r: r["best_cos"])
        return out[:top_k]

    def status(self) -> Dict[str, Any]:
        """Always the same keys, trained or not — callers must not have to guess."""
        st = {
            "trained": False,
            "vocab_size": 0,
            "dims": 0,
            "notes": 0,
            "pairs_observed": 0,
            "quant_bits": 8,
            "cosine_fidelity_pct": None,
            "cache_kb": 0.0,
            "fingerprint": "",
            "trained_ts": "",
        }
        st.update(self.stats)
        st["trained"] = bool(self.stats.get("trained") and self.vectors)
        st["known_words"] = len(self.vectors)
        try:
            st["cache_kb"] = round(self.path.stat().st_size / 1024.0, 1) if self.path.exists() else 0.0
        except OSError:
            pass
        return st
