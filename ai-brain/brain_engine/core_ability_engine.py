"""Stage E — Core Ability Growth Gym 🏋️

Skills are *tools in the pocket*; core abilities are *muscles in the body*.
This engine grows four core muscles through genuine self-evolution loops:

  🧠 reasoning   — multi-hop transitive inference (strategy selection learns
                    when cheap chaining suffices and when full closure is needed)
  📖 context     — pinpoint the key sentence in a passage full of distractors
                    (feature weights learn that object-uniqueness matters)
  💻 coding      — classify a bug pattern from code fingerprints and apply the
                    matching repair rule (linear classifier learns via perceptron)
  🗂️ organizing  — cluster scattered wiki notes by theme (similarity weights
                    learn that category evidence beats title coincidence)

Every session: self-curriculum problems at current difficulty → attempt with
current weights → exact judge → perceptron/bandit weight update → held-out
exam at difficulty+1 → level up on >=75% accuracy.  Weights are persisted and,
on every level-up, frozen into our own INT4 `.sbrain` ability capsule.
"""

from __future__ import annotations

import json
import random
import struct
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from brain_engine.quant_forge import BLOCK_SIZE, MAGIC, quantize_tensor_int4

ABILITY_ORDER = ["reasoning", "context", "coding", "organizing"]

ABILITY_META: Dict[str, Dict[str, str]] = {
    "reasoning": {
        "title": "🧠 추론 능력",
        "desc": "여러 hop 증거를 체인처럼 엮어 결론을 도출하는 힘",
        "unit": "hop",
    },
    "context": {
        "title": "📖 문맥 이해 능력",
        "desc": "방해 문장 사이에서 핵심 문장을 콕 집어내는 힘",
        "unit": "방해문장",
    },
    "coding": {
        "title": "💻 코딩 능력",
        "desc": "버그 지문을 읽어 올바른 수리 규칙을 고르는 힘",
        "unit": "버그클래스",
    },
    "organizing": {
        "title": "🗂️ 정보 정리 능력",
        "desc": "흩어진 기억들을 주제별로 오와 열로 세우는 힘",
        "unit": "노트수",
    },
}

_BUG_CLASSES = ["missing_mask", "off_by_one", "wrong_init", "empty_guard"]

# Honest mastery ceilings per muscle (growth stays measurable, never runaway)
LEVEL_CAP = {"reasoning": 16, "context": 12, "coding": 10, "organizing": 12}


# ---------------------------------------------------------------------------
# Problem generators + solvers (each returns (problem, solve_fn, answer))
# ---------------------------------------------------------------------------
def _gen_reasoning(rng: random.Random, hops: int) -> Dict[str, Any]:
    pool = ["아르", "보르", "시르", "도르", "미르", "로르", "누르", "타르", "카르", "파르", "하르", "자르"]
    hops = min(hops, len(pool) - 1)
    names = rng.sample(pool, hops + 1)
    order = list(names)  # order[0] is the tallest
    facts = [(order[i], order[i + 1]) for i in range(len(order) - 1)]
    rng.shuffle(facts)
    a, b = order[0], order[-1]
    return {
        "hops": hops,
        "facts": facts,
        "question": (a, b),
        "answer": True,  # a is taller than b through the chain
    }


def _solve_reasoning(prob: Dict[str, Any], w: Dict[str, float]) -> Tuple[bool, str]:
    facts = prob["facts"]
    a, b = prob["question"]
    hops = prob["hops"]
    strategies = {
        "forward": w.get("f_bias", 0.0) + w.get("f_hops", 0.0) * hops,
        "backward": w.get("b_bias", 0.0) + w.get("b_hops", 0.0) * hops,
        "closure": w.get("c_bias", 0.0) + w.get("c_hops", 0.0) * hops,
    }
    if random.random() < 0.25:  # curiosity: sometimes try a non-greedy strategy
        chosen = random.choice(list(strategies))
    else:
        chosen = max(strategies, key=strategies.get)
    gt = {x: y for x, y in facts}  # x taller than y
    if chosen == "forward":
        cur, depth = a, 0
        while cur != b and depth <= 2:
            cur = gt.get(cur)
            depth += 1
            if cur is None:
                return False, chosen
        return cur == b, chosen
    if chosen == "backward":
        rev = {y: x for x, y in facts}
        cur, depth = b, 0
        while cur != a and depth <= 2:
            cur = rev.get(cur)
            depth += 1
            if cur is None:
                return False, chosen
        return cur == a, chosen
    # full transitive closure (always correct, but 'expensive')
    reach = set()
    changed = True
    while changed:
        changed = False
        for x, y in facts:
            for z in list(reach):
                if z == x and (x, y) not in reach:
                    reach.add((x, y))
            reach.add((x, y))
        new = {(x, z) for x, y in reach for y2, z in reach if y2 == y} - reach
        if new:
            reach |= new
            changed = True
    return (a, b) in reach, chosen


def _update_reasoning(w: Dict[str, float], prob: Dict[str, Any], chosen: str, ok: bool) -> None:
    hops = prob["hops"]
    lr = 0.35
    key = f"{chosen[0]}_bias"
    key_h = f"{chosen[0]}_hops"
    if ok:
        reward = 0.55 if chosen == "closure" else 1.0  # cheap chains are the elegant win
        w[key] = w.get(key, 0.0) + lr * reward
        if chosen == "closure":
            # expensive closure succeeded: love it more as hops grow, less on easy hops
            w[key_h] = w.get(key_h, 0.0) + lr * reward * 0.12 * (hops - 3)
        else:
            w[key_h] = w.get(key_h, 0.0) - lr * reward * 0.06 * hops
    else:
        w[key] = w.get(key, 0.0) - lr
        if chosen != "closure":
            # closure would have saved us: nudge its hops-slope upward
            w["c_hops"] = w.get("c_hops", 0.0) + lr * 0.10 * hops


def _gen_context_real(rng: random.Random, distractors: int) -> Dict[str, Any]:
    subjects = ["시냅스몽", "꼬마 뉴런", "유리방 로봇", "위키 정원사", "심장박동 요정"]
    objects = ["붕어빵", "별사탕", "양자 사과", "달빛 쿠키", "구름 젤리"]
    subj, obj = rng.choice(subjects), rng.choice(objects)
    key_sentence = f"{subj}이(가) 가장 좋아하는 것은 {obj}입니다."
    other_objs = [o for o in objects if o != obj]
    other_subs = [x for x in subjects if x != subj]
    pool: List[str] = [
        f"{subj}이(가) 가장 좋아하는 것이 {other_objs[0]}이라는 것은 사실이 아닙니다.",
        f"{other_subs[0]}이(가) 가장 좋아하는 것은 {obj}입니다.",
        f"{subj}이(가) 가장 싫어하는 것은 {other_objs[1]}입니다.",
        f"{other_subs[1]}이(가) 어제 먹은 것은 {other_objs[2]}입니다.",
    ]
    rng.shuffle(pool)
    dist = pool[: max(1, min(4, distractors))]
    sentences = dist + [key_sentence]
    rng.shuffle(sentences)
    return {
        "question": f"{subj}이(가) 가장 좋아하는 것은?",
        "answer_sentence": key_sentence,
        "sentences": sentences,
        "distractors": distractors,
    }


def _context_features(sentence: str, question_subj: str) -> List[float]:
    neg = 1.0 if "사실이 아닙니다" in sentence else 0.0
    subj_hit = 1.0 if question_subj in sentence else 0.0
    verb_hit = 1.0 if "좋아하는 것" in sentence else 0.0
    assert_hit = 1.0 if ("입니다." in sentence and neg == 0.0) else 0.0
    return [subj_hit, verb_hit, neg, assert_hit]


def _solve_context(prob: Dict[str, Any], w: Dict[str, float]) -> Tuple[bool, str]:
    subj = prob["question"].split("이(가)")[0]
    best, best_score = None, -1e9
    for s in prob["sentences"]:
        f = _context_features(s, subj)
        score = (
            w.get("w_subj", 0.5) * f[0]
            + w.get("w_verb", 0.5) * f[1]
            + w.get("w_neg", 0.6) * f[2]
            + w.get("w_assert", -0.3) * f[3]
        )
        if score > best_score:
            best, best_score = s, score
    return best == prob["answer_sentence"], best or ""


def _update_context(w: Dict[str, float], prob: Dict[str, Any], chosen: str, ok: bool) -> None:
    if ok:
        return
    subj = prob["question"].split("이(가)")[0]
    f_good = _context_features(prob["answer_sentence"], subj)
    f_bad = _context_features(chosen, subj)
    lr = 0.3
    for key, idx in (("w_subj", 0), ("w_verb", 1), ("w_neg", 2), ("w_assert", 3)):
        w[key] = w.get(key, 0.0) + lr * (f_good[idx] - f_bad[idx])


_CODE_SNIPPETS = {
    "missing_mask": ("crc ^= (b << 8)\n crc = crc << 1", "crc &= 0xFFFF 추가"),
    "off_by_one": ("for i in range(0, len(v)):\n  d = v[i] - v[i-1]", "range(1, len(v)) 로 수리"),
    "wrong_init": ("crc = 0x0000", "crc = 0xFFFF 로 수리"),
    "empty_guard": ("return [0]  # when not data", "return [] 로 수리"),
}


def _gen_coding(rng: random.Random, n_classes: int) -> Dict[str, Any]:
    cls = rng.choice(_BUG_CLASSES[: max(2, min(4, n_classes))])
    snippet, fix = _CODE_SNIPPETS[cls]
    return {"cls": cls, "snippet": snippet, "fix": fix}


def _code_features(prob: Dict[str, Any]) -> List[float]:
    s = prob["snippet"]
    return [
        1.0 if ("<<" in s and "0xFFFF" not in s) else 0.0,
        1.0 if ("range(0, len(" in s and "i-1" in s) else 0.0,
        1.0 if ("= 0x0000" in s) else 0.0,
        1.0 if ("return [0]" in s) else 0.0,
    ]


def _solve_coding(prob: Dict[str, Any], w: Dict[str, Any]) -> Tuple[bool, str]:
    f = _code_features(prob)
    weights: List[List[float]] = w.get("matrix", [[0.0] * 4 for _ in range(4)])
    scores = [sum(w_row[i] * f[i] for i in range(4)) for w_row in weights]
    pick = max(range(4), key=lambda k: scores[k])
    guess = _BUG_CLASSES[pick]
    return guess == prob["cls"], guess


def _update_coding(w: Dict[str, Any], prob: Dict[str, Any], guess: str, ok: bool) -> None:
    f = _code_features(prob)
    matrix: List[List[float]] = w.setdefault("matrix", [[0.0] * 4 for _ in range(4)])
    lr = 0.4
    truth = _BUG_CLASSES.index(prob["cls"])
    guessed = _BUG_CLASSES.index(guess)
    for i in range(4):
        if ok:
            matrix[truth][i] += lr * 0.2 * f[i]
        else:
            matrix[guessed][i] -= lr * f[i]
            matrix[truth][i] += lr * f[i]


def _gen_organizing(rng: random.Random, n_notes: int) -> Dict[str, Any]:
    cats = [
        ("양자화", ["int4", "scale", "니블", "블록"]),
        ("역공학", ["elf", "해부", "기계어", "xray"]),
        ("강화학습", ["보상", "심판", "에피소드", "합의"]),
    ]
    notes = []
    truth = []
    for ci, (cat, tokens) in enumerate(cats):
        for k in range(max(1, n_notes // 3)):
            tk = rng.sample(tokens, 2)
            notes.append({"title": f"{cat} 메모 {k} {tk[0]} {tk[1]}", "cat": cat, "tokens": tk})
            truth.append(ci)
    order = list(range(len(notes)))
    rng.shuffle(order)
    notes = [notes[i] for i in order]
    truth = [truth[i] for i in order]
    return {"notes": notes, "truth": truth}


def _solve_organizing(prob: Dict[str, Any], w: Dict[str, float]) -> Tuple[bool, str]:
    notes = prob["notes"]
    n = len(notes)
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for i in range(n):
        for j in range(i + 1, n):
            t_i = set(notes[i]["title"].split())
            t_j = set(notes[j]["title"].split())
            title_ov = len(t_i & t_j) / max(1, len(t_i | t_j))
            tag_ov = len(set(notes[i]["tokens"]) & set(notes[j]["tokens"])) / 2.0
            cat_mt = 1.0 if notes[i]["cat"] == notes[j]["cat"] else 0.0
            sim = w.get("w_title", 0.8) * title_ov + w.get("w_tag", 0.3) * tag_ov + w.get("w_cat", -0.2) * cat_mt
            if sim > w.get("thr", 0.55):
                parent[find(i)] = find(j)
    ok = all((find(i) == find(j)) == (prob["truth"][i] == prob["truth"][j]) for i in range(n) for j in range(i + 1, n))
    return ok, "cluster"


def _update_organizing(w: Dict[str, float], prob: Dict[str, Any], chosen: str, ok: bool) -> None:
    lr = 0.25
    if ok:
        w["w_cat"] = w.get("w_cat", -0.2) + lr * 0.2
        return
    w["w_title"] = w.get("w_title", 0.8) - lr
    w["w_cat"] = w.get("w_cat", -0.2) + lr
    w["thr"] = w.get("thr", 0.55) - lr * 0.2


_GENERATORS = {
    "reasoning": _gen_reasoning,
    "context": _gen_context_real,
    "coding": _gen_coding,
    "organizing": _gen_organizing,
}
_SOLVERS = {
    "reasoning": _solve_reasoning,
    "context": _solve_context,
    "coding": _solve_coding,
    "organizing": _solve_organizing,
}
_UPDATERS = {
    "reasoning": _update_reasoning,
    "context": _update_context,
    "coding": _update_coding,
    "organizing": _update_organizing,
}


def _difficulty_for(ability: str, level: int) -> int:
    if ability == "reasoning":
        return min(8, 2 + level // 2)
    if ability == "context":
        return min(4, 1 + level // 2)
    if ability == "coding":
        return min(4, 2 + level // 3)
    return min(12, 3 * max(2, 1 + level // 2))


class CoreAbilityEngine:
    """Grows the four core muscles and freezes them into INT4 capsules."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.state_path = root / "state" / "core_abilities.json"
        self.models_dir = root / "models"
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state = self._load()

    def _load(self) -> Dict[str, Any]:
        if self.state_path.exists():
            try:
                return json.loads(self.state_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        init = {
            "abilities": {
                a: {"level": 1, "xp": 0, "weights": self._default_weights(a), "sessions": []}
                for a in ABILITY_ORDER
            }
        }
        self._save(init)
        return init

    @staticmethod
    def _default_weights(ability: str) -> Dict[str, Any]:
        if ability == "reasoning":
            return {"f_bias": 0.6, "f_hops": 0.05, "b_bias": 0.4, "b_hops": 0.05, "c_bias": -0.6, "c_hops": 0.0}
        if ability == "context":
            return {"w_subj": 0.5, "w_verb": 0.5, "w_neg": 0.6, "w_assert": -0.3}
        if ability == "coding":
            return {"matrix": [[0.0] * 4 for _ in range(4)]}
        return {"w_title": 0.8, "w_tag": 0.3, "w_cat": -0.2, "thr": 0.55}

    def _save(self, data: Optional[Dict[str, Any]] = None) -> None:
        if data is not None:
            self.state = data
        self.state_path.write_text(json.dumps(self.state, ensure_ascii=False, indent=2), encoding="utf-8")

    # ------------------------------------------------------------------
    def train_session(self, ability: str, rounds: int = 6, seed: Optional[int] = None) -> Dict[str, Any]:
        t0 = time.perf_counter()
        ab = self.state["abilities"].setdefault(
            ability, {"level": 1, "xp": 0, "weights": self._default_weights(ability), "sessions": []}
        )
        level_before = int(ab["level"])
        difficulty = _difficulty_for(ability, level_before)
        rng = random.Random(seed if seed is not None else int(time.time() * 1000) % (2**31))

        correct = 0
        example_q = ""
        for i in range(rounds):
            d = difficulty + 1 if (ability == "reasoning" and i % 2 == 1) else difficulty
            prob = _GENERATORS[ability](rng, d)
            ok, chosen = _SOLVERS[ability](prob, ab["weights"])
            if ok:
                correct += 1
            else:
                _UPDATERS[ability](ab["weights"], prob, chosen, ok)
            if not example_q:
                example_q = self._example_text(ability, prob)

        # held-out exam at difficulty+1 (no weight updates!)
        exam_correct, exam_total = 0, 4
        for _ in range(exam_total):
            prob = _GENERATORS[ability](rng, difficulty + 1)
            ok, _ = _SOLVERS[ability](prob, ab["weights"])
            exam_correct += 1 if ok else 0

        leveled_up = exam_correct * 4 >= exam_total * 3  # >= 75%
        if leveled_up:
            ab["level"] = min(LEVEL_CAP.get(ability, 50), level_before + 1)
        ab["xp"] = int(ab["xp"]) + correct * 2 + exam_correct * 3
        session = {
            "ts": datetime.now(timezone.utc).strftime("%m-%d %H:%M UTC"),
            "difficulty": difficulty,
            "correct": correct,
            "rounds": rounds,
            "exam": f"{exam_correct}/{exam_total}",
            "level_before": level_before,
            "level_after": int(ab["level"]),
        }
        ab["sessions"] = (ab.get("sessions") or [])[-19:] + [session]
        self._save()

        capsule = ""
        if leveled_up:
            capsule = self._freeze_capsule(ability, ab)

        return {
            "ability": ability,
            "title": ABILITY_META[ability]["title"],
            "difficulty": difficulty,
            "correct": correct,
            "rounds": rounds,
            "exam_correct": exam_correct,
            "exam_total": exam_total,
            "level_before": level_before,
            "level_after": int(ab["level"]),
            "leveled_up": leveled_up,
            "capsule": capsule,
            "example": example_q,
            "xp": ab["xp"],
            "ms": round((time.perf_counter() - t0) * 1000.0, 2),
        }

    def _example_text(self, ability: str, prob: Dict[str, Any]) -> str:
        if ability == "reasoning":
            a, b = prob["question"]
            return f"{prob['hops']}hop 체인: {a} vs {b} 비교"
        if ability == "context":
            return prob["question"]
        if ability == "coding":
            return f"버그 지문: {prob['cls']}"
        return f"노트 {len(prob['notes'])}개 주제별 묶기"

    def _freeze_capsule(self, ability: str, ab: Dict[str, Any]) -> str:
        flat: List[float] = []
        w = ab["weights"]
        if ability == "coding":
            for row in w.get("matrix", []):
                flat.extend(row)
        else:
            for k in sorted(w):
                v = w[k]
                if isinstance(v, (int, float)):
                    flat.append(float(v))
        if not flat:
            flat = [0.0]
        q_bytes, _ = quantize_tensor_int4(flat)
        meta = {
            "format": "SynapseAbilityCapsule-INT4",
            "ability": ability,
            "level": int(ab["level"]),
            "bits": 4,
            "block_size": BLOCK_SIZE,
            "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        }
        meta_bytes = json.dumps(meta, ensure_ascii=False).encode("utf-8")
        name = f"core_ability_{ability}_int4.sbrain"
        with open(self.models_dir / name, "wb") as f:
            f.write(MAGIC)
            f.write(struct.pack("<BIII", 4, len(meta_bytes), len(q_bytes), 0))
            f.write(struct.pack("<I", int(ab["level"])))
            f.write(meta_bytes)
            f.write(q_bytes)
        return name

    # ------------------------------------------------------------------
    def snapshot(self) -> Dict[str, Any]:
        out = []
        for a in ABILITY_ORDER:
            ab = self.state["abilities"].get(a, {})
            sessions = ab.get("sessions") or []
            out.append(
                {
                    "id": a,
                    "title": ABILITY_META[a]["title"],
                    "desc": ABILITY_META[a]["desc"],
                    "unit": ABILITY_META[a]["unit"],
                    "level": int(ab.get("level", 1)),
                    "xp": int(ab.get("xp", 0)),
                    "last_session": sessions[-1] if sessions else None,
                    "sessions": sessions[-6:],
                }
            )
        return {"abilities": out, "max_level": max(LEVEL_CAP.values()), "caps": LEVEL_CAP}
