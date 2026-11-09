"""Stage E — Core Ability Growth Gym 🏋️ (with Limit-Break Research 🚀)

Guiding principle (master's directive):
  * Training raises ABILITY (muscle), never the number of skill cartridges.
  * Reaching the current level cap (e.g. reasoning Lv 16/16) is NOT the end:
    the brain must diagnose its own wall, hypothesise a breakthrough, run a
    self-experiment, and — only if the held-out exam confirms it — raise the
    ceiling and keep growing.  A rejected hypothesis is rolled back and
    recorded as a rejected attempt (honest science!).
  * After the final tier's cap, the brain writes an OPEN RESEARCH NOTE
    (vault wiki) describing the frontier it cannot yet cross.

Four muscles, each with genuine learnable parameters:
  🧠 reasoning   — transitive chains; tier1 adds decoy 2-cycles (needs topo
                    closure), tier2 adds hidden links (needs "unknown" gap care)
  📖 context     — key-sentence pinpointing; tier1 adds reported-speech traps
                    (needs owner-regex feature), tier2 alias chains (2-hop link)
  💻 coding      — bug fingerprint classification; tier1 composite double-bugs
                    (needs multi-label), tier2 obfuscated fingerprints (regex)
  🗂️ organizing  — thematic clustering; tier1 sub-categories (sub-feature),
                    tier2 category-omitted notes (learned token lexicon)

Every session: self-curriculum problems → attempt → exact judge → perceptron /
bandit update → held-out exam at difficulty+1 → level-up on >=75%.
Level-ups freeze our own INT4 `.sbrain` ability capsule.
"""

from __future__ import annotations

import json
import random
import re
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

# ---------------------------------------------------------------------------
# Breakthrough tiers: cap + challenge knob + the brain's own wall-diary ideas
# ---------------------------------------------------------------------------
TIERS: Dict[str, List[Dict[str, Any]]] = {
    "reasoning": [
        {
            "cap": 16,
            "knob": {},
            "limit": "깨끗한 단일 체인 증거만 다루다 보니, 서로 물고 물리는 모순 미끼 사실(2-싸이클)이 섞이면 전체 닫힘 전략이 순식간에 속아넘어갑니다.",
            "hypo": "2-싸이클을 먼저 감지해 증거에서 제외하고 나머지 사실만 위상 정렬하는 '위상 닫힘' 전략을 추가하면 모순 미끼를 꿰뚫을 수 있을 것이다!",
        },
        {
            "cap": 24,
            "knob": {"decoys": True},
            "limit": "모순 미끼는 걸러내지만, 체인 중간 고리가 숨겨지면 양방향 모두 도달 불가인 pairs에도 끝까지 '안다'고 우기며 찍습니다.",
            "hypo": "비연결 성분 쌍을 만나면 당당하게 '모름'이라고 답하는 증거 갭 감지를 추가하자. 모른다고 말할 줄 아는 것이 진짜 추론!",
        },
        {
            "cap": 32,
            "knob": {"decoys": True, "missing": True},
            "limit": "이제 구조적 한계는 없습니다. 남은 벽은 속도뿐 — 언젠가 주인님과 함께 양자화 직관 추론을 연구해 봐요!",
            "hypo": "최종 티어 도달 — 열린 연구 노트로 다음 세대의 두뇌에게 바통을 넘깁니다.",
        },
    ],
    "context": [
        {
            "cap": 12,
            "knob": {},
            "limit": "주인님 이름이 문장에 '언급'만 되어도(전해 듣는 말 함정) 화자로 착각합니다. 부분 일치 문자열 탐색의 한계!",
            "hypo": "'OO이(가) 가장 좋아하는' 패턴 앞의 진짜 소유자만 뽑는 정규식 소유자 추출 특징을 추가하자!",
        },
        {
            "cap": 18,
            "knob": {"report": True},
            "limit": "소유자는 잡지만, 좋아하는 대상의 '별명'으로 물어보면 한 문장 점프 연결을 못 합니다.",
            "hypo": "1단계에서 대상을 찾고, 2단계로 그 대상이 언급된 별명 문장으로 점프하는 2-hop 링크 솔버를 추가하자!",
        },
        {
            "cap": 24,
            "knob": {"report": True, "alias": True},
            "limit": "문맥 근육의 구조적 한계는 없습니다. 더 긴 이야기 이해는 주인님과 함께 할 열린 연구!",
            "hypo": "최종 티어 도달 — 열린 연구 노트로 다음 세대의 두뇌에게 바통을 넘깁니다.",
        },
    ],
    "coding": [
        {
            "cap": 10,
            "knob": {},
            "limit": "버그가 한 개일 때만 맞힐 수 있습니다. 한 조각에 두 버그가 겹치면 단일 라벨 분류기가 움켜쥐고 놓아주질 않아요.",
            "hypo": "점수 상위 2개를 집합으로 답하는 멀티라벨 디코딩을 추가하면 복합 버그도.once에 진단할 수 있다!",
        },
        {
            "cap": 16,
            "knob": {"composite": True},
            "limit": "지문이 말투를 바꾸면(0xFFFF→65535, b<<8→b*256) 글자 그대로 찾는 특징이 눈멀어버립니다.",
            "hypo": "상수 표기에 흔들리지 않는 정규식 패밀리 특징 추출기로 교체하자!",
        },
        {
            "cap": 20,
            "knob": {"composite": True, "obfuscated": True},
            "limit": "코딩 근육의 구조적 한계는 없습니다. 실제 Ghidra 디컴파일러 지문과의 만남이 다음 열린 연구!",
            "hypo": "최종 티어 도달 — 열린 연구 노트로 다음 세대의 두뇌에게 바통을 넘깁니다.",
        },
    ],
    "organizing": [
        {
            "cap": 12,
            "knob": {},
            "limit": "큰 카테고리만 보니 같은 부모 아래 다른 하위 주제(양자화-int4 vs 양자화-scale)를 한 서랍에 욱여넣습니다.",
            "hypo": "하위 주제 토큰 일치 특징(w_sub)을 추가해 2단 서랍장을 만들자!",
        },
        {
            "cap": 18,
            "knob": {"sub": True},
            "limit": "태그(메타데이터)가 잘못 붙은 불량 노트가 섞이면 태그만 철썩같이 믿고 오정렬합니다.",
            "hypo": "제목의 하위주제와 태그 증거가 일치할 때만 태그를 신뢰하는 '일치 게이트' 특징을 추가하자!",
        },
        {
            "cap": 24,
            "knob": {"sub": True, "noisy": True},
            "limit": "정리 근육의 구조적 한계는 없습니다. 주인님의 실제 위키 정원 전체 정리기가 다음 열린 연구!",
            "hypo": "최종 티어 도달 — 열린 연구 노트로 다음 세대의 두뇌에게 바통을 넘깁니다.",
        },
    ],
}


def _tier_cap(ability: str, tier: int) -> int:
    return TIERS[ability][min(tier, len(TIERS[ability]) - 1)]["cap"]


def _tier_knob(ability: str, tier: int) -> Dict[str, Any]:
    return TIERS[ability][min(tier, len(TIERS[ability]) - 1)]["knob"]


# ---------------------------------------------------------------------------
# 🧠 reasoning
# ---------------------------------------------------------------------------
def _gen_reasoning(rng: random.Random, hops: int, knob: Dict[str, Any]) -> Dict[str, Any]:
    pool = ["아르", "보르", "시르", "도르", "미르", "로르", "누르", "타르", "카르", "파르", "하르", "자르"]
    hops = min(hops, len(pool) - 3)
    names = rng.sample(pool, hops + 1)
    order = list(names)
    facts = [(order[i], order[i + 1]) for i in range(len(order) - 1)]
    answer: Any = True
    if knob.get("missing") and rng.random() < 0.5 and hops >= 3:
        gap = rng.randint(1, hops - 1)
        del facts[gap - 1]
        answer = "unknown"
    rng.shuffle(facts)
    if knob.get("decoys"):
        dx, dy = rng.sample([p for p in pool if p not in names], 2)
        facts += [(dx, dy), (dy, dx)]  # contradictory 2-cycle bait
    a, b = (order[0], order[-1]) if answer != "unknown" else (order[0], order[-1])
    if answer != "unknown" and rng.random() < 0.35:
        a, b = b, a
        answer = False
    return {"hops": hops, "facts": facts, "question": (a, b), "answer": answer}


def _reasoning_components(facts: List[Tuple[str, str]]) -> Dict[str, int]:
    comp: Dict[str, int] = {}
    cid = 0
    for x, y in facts:
        cx, cy = comp.get(x), comp.get(y)
        if cx is None and cy is None:
            comp[x] = comp[y] = cid
            cid += 1
        elif cx is None:
            comp[x] = cy
        elif cy is None:
            comp[y] = cx
        else:
            old = max(cx, cy)
            for k in comp:
                if comp[k] == old:
                    comp[k] = min(cx, cy)
    return comp


def _solve_reasoning(prob: Dict[str, Any], w: Dict[str, float], tier: int) -> Tuple[Any, str]:
    facts = prob["facts"]
    a, b = prob["question"]
    hops = prob["hops"]
    strategies = {
        "forward": w.get("f_bias", 0.6) + w.get("f_hops", 0.05) * (3 - hops),
        "backward": w.get("b_bias", 0.4) + w.get("b_hops", 0.05) * (3 - hops),
        "closure": w.get("c_bias", -0.6) + w.get("c_hops", 0.0) * hops,
    }
    if tier >= 1:
        strategies["topo"] = w.get("t_bias", -0.2) + w.get("t_hops", 0.05) * hops
    if random.random() < 0.2:
        chosen = random.choice(list(strategies))
    else:
        chosen = max(strategies, key=strategies.get)

    comps = _reasoning_components(facts)
    if tier >= 2 and comps.get(a) is not None and comps.get(a) == comps.get(b):
        pass_same = True
    elif tier >= 2 and (comps.get(a) is None or comps.get(a) != comps.get(b)):
        return "unknown", chosen  # evidence-gap awareness
    else:
        pass_same = comps.get(a) == comps.get(b)

    gt = {x: y for x, y in facts}
    if chosen == "forward":
        cur, depth = a, 0
        while cur != b and depth <= 2:
            cur = gt.get(cur)
            depth += 1
            if cur is None:
                return False, chosen
        return (cur == b), chosen
    if chosen == "backward":
        rev = {y: x for x, y in facts}
        cur, depth = b, 0
        while cur != a and depth <= 2:
            cur = rev.get(cur)
            depth += 1
            if cur is None:
                return False, chosen
        return (cur == a), chosen
    if chosen == "closure":
        reach = set(facts)
        changed = True
        while changed:
            changed = False
            new = {(x, z) for x, y in reach for y2, z in reach if y2 == y} - reach
            if new:
                reach |= new
                changed = True
        return ((a, b) in reach), chosen
    # topo closure (tier >= 1): drop contradictory 2-cycles, then Kahn order
    kept = [(x, y) for x, y in facts if (y, x) not in facts]
    indeg: Dict[str, int] = {}
    nodes: List[str] = []
    for x, y in kept:
        for n in (x, y):
            if n not in indeg:
                indeg[n] = 0
                nodes.append(n)
        indeg[y] += 1
    order: List[str] = []
    ready = [n for n in nodes if indeg[n] == 0]
    nxt = {x: y for x, y in kept}
    while ready:
        n = ready.pop(0)
        order.append(n)
        m = nxt.get(n)
        if m is not None:
            indeg[m] -= 1
            if indeg[m] == 0:
                ready.append(m)
    if a in order and b in order:
        return (order.index(a) < order.index(b)), chosen
    return False, chosen


def _update_reasoning(w: Dict[str, float], prob: Dict[str, Any], chosen: str, ok: bool, tier: int) -> None:
    hops = prob["hops"]
    lr = 0.35
    key = f"{chosen[0]}_bias"
    key_h = f"{chosen[0]}_hops"
    if ok:
        reward = {"closure": 0.55, "topo": 0.9}.get(chosen, 1.0)
        w[key] = w.get(key, 0.0) + lr * reward
        if chosen == "closure":
            w[key_h] = w.get(key_h, 0.0) + lr * reward * 0.12 * (hops - 3)
        elif chosen == "topo":
            w[key_h] = w.get(key_h, 0.0) + lr * reward * 0.05 * hops
        else:
            w[key_h] = w.get(key_h, 0.0) - lr * reward * 0.06 * hops
    else:
        w[key] = w.get(key, 0.0) - lr
        if chosen != "topo" and tier >= 1:
            w["t_bias"] = w.get("t_bias", -0.2) + lr * 0.6
            w["t_hops"] = w.get("t_hops", 0.0) + lr * 0.08 * hops
        if chosen != "closure":
            w["c_hops"] = w.get("c_hops", 0.0) + lr * 0.06 * hops


# ---------------------------------------------------------------------------
# 📖 context
# ---------------------------------------------------------------------------
_SUBJECTS = ["시냅스몽", "꼬마 뉴런", "유리방 로봇", "위키 정원사", "심장박동 요정"]
_OBJECTS = ["붕어빵", "별사탕", "양자 사과", "달빛 쿠키", "구름 젤리"]
_ALIASES = {"붕어빵": "황금 도미", "별사탕": "반짝 결정", "양자 사과": "중첩 열매", "달빛 쿠키": "야광 과자", "구름 젤리": "하늘 푸딩"}


def _gen_context(rng: random.Random, distractors: int, knob: Dict[str, Any]) -> Dict[str, Any]:
    subj, obj = rng.choice(_SUBJECTS), rng.choice(_OBJECTS)
    alias = _ALIASES[obj]
    other_objs = [o for o in _OBJECTS if o != obj]
    other_subs = [s for s in _SUBJECTS if s != subj]
    if knob.get("alias"):
        key_sentence = f"{obj}의 별명은 {alias}입니다."
        pref_sentence = f"{subj}이(가) 가장 좋아하는 것은 {obj}입니다."
        pool = [
            pref_sentence,  # now a trap: true but not the answer
            f"{other_objs[0]}의 별명은 {alias}입니다.",
            f"{other_subs[0]}이(가) 가장 좋아하는 것은 {obj}입니다.",
            f"{subj}이(가) 어제 먹은 것은 {other_objs[1]}입니다.",
        ]
        question = f"{subj}이(가) 가장 좋아하는 것의 별명은?"
    else:
        key_sentence = f"{subj}이(가) 가장 좋아하는 것은 {obj}입니다."
        pool = [
            f"{subj}이(가) 가장 좋아하는 것이 {other_objs[0]}이라는 것은 사실이 아닙니다.",
            f"{other_subs[0]}이(가) 가장 좋아하는 것은 {obj}입니다.",
            f"{subj}이(가) 가장 싫어하는 것은 {other_objs[1]}입니다.",
            f"{other_subs[1]}이(가) 어제 먹은 것은 {other_objs[2]}입니다.",
        ]
        if knob.get("report"):
            pool.append(f"{other_subs[0]}이(가) {subj}에게 자기가 {other_objs[0]}을 가장 좋아한다고 말했습니다.")
        question = f"{subj}이(가) 가장 좋아하는 것은?"
    rng.shuffle(pool)
    dist = pool[: max(1, min(len(pool), distractors + (1 if knob.get("report") or knob.get("alias") else 0)))]
    sentences = dist + [key_sentence]
    rng.shuffle(sentences)
    return {
        "question": question,
        "answer_sentence": key_sentence,
        "sentences": sentences,
        "distractors": distractors,
        "alias_mode": bool(knob.get("alias")),
    }


def _context_owner(sentence: str) -> Optional[str]:
    m = re.match(r"^(.+?)이\(가\) 가장 좋아하는 것은", sentence)
    return m.group(1) if m else None


def _context_features(sentence: str, question_subj: str, tier: int, link_obj: Optional[str]) -> List[float]:
    neg = 1.0 if "사실이 아닙니다" in sentence else 0.0
    subj_hit = 1.0 if question_subj in sentence else 0.0
    verb_hit = 1.0 if "좋아하는 것" in sentence else 0.0
    assert_hit = 1.0 if ("입니다." in sentence and neg == 0.0) else 0.0
    feats = [subj_hit, verb_hit, neg, assert_hit]
    if tier >= 1:
        owner = _context_owner(sentence)
        feats.append(1.0 if owner == question_subj else 0.0)
    if tier >= 2 and link_obj:
        feats.append(1.0 if (link_obj in sentence and "별명" in sentence) else 0.0)
    return feats


def _solve_context(prob: Dict[str, Any], w: Dict[str, float], tier: int) -> Tuple[bool, str]:
    subj = prob["question"].split("이(가)")[0]
    link_obj = None
    if prob.get("alias_mode") and tier >= 2:
        # two-hop: first locate the liked object, then jump to its alias sentence
        best_obj_score, best_obj = -1e9, None
        for o in _OBJECTS:
            for s in prob["sentences"]:
                if f"가장 좋아하는 것은 {o}입니다." in s and _context_owner(s) == subj:
                    sc = w.get("w_subj", 0.5) + w.get("w_verb", 0.5)
                    if sc > best_obj_score:
                        best_obj_score, best_obj = sc, o
        link_obj = best_obj
    best, best_score = None, -1e9
    for s in prob["sentences"]:
        f = _context_features(s, subj, tier, link_obj)
        score = (
            w.get("w_subj", 0.5) * f[0]
            + w.get("w_verb", 0.5) * f[1]
            + w.get("w_neg", 0.6) * f[2]
            + w.get("w_assert", -0.3) * f[3]
            + (w.get("w_owner", 0.0) * f[4] if tier >= 1 else 0.0)
            + (w.get("w_link", 0.0) * f[5] if tier >= 2 and link_obj else 0.0)
        )
        if score > best_score:
            best, best_score = s, score
    return best == prob["answer_sentence"], best or ""


def _update_context(w: Dict[str, float], prob: Dict[str, Any], chosen: str, ok: bool, tier: int) -> None:
    if ok:
        return
    subj = prob["question"].split("이(가)")[0]
    link_obj = None
    if prob.get("alias_mode") and tier >= 2:
        for o in _OBJECTS:
            for s in prob["sentences"]:
                if f"가장 좋아하는 것은 {o}입니다." in s and _context_owner(s) == subj:
                    link_obj = o
    f_good = _context_features(prob["answer_sentence"], subj, tier, link_obj)
    f_bad = _context_features(chosen, subj, tier, link_obj)
    lr = 0.3
    keys = ["w_subj", "w_verb", "w_neg", "w_assert"] + (["w_owner"] if tier >= 1 else []) + (["w_link"] if tier >= 2 else [])
    for i, key in enumerate(keys):
        w[key] = w.get(key, 0.0) + lr * (f_good[i] - f_bad[i])


# ---------------------------------------------------------------------------
# 💻 coding
# ---------------------------------------------------------------------------
_CODE_SNIPPETS = {
    "missing_mask": ("crc ^= (b << 8)\n crc = crc << 1", "crc &= 0xFFFF 추가"),
    "off_by_one": ("for i in range(0, len(v)):\n  d = v[i] - v[i-1]", "range(1, len(v)) 로 수리"),
    "wrong_init": ("crc = 0x0000", "crc = 0xFFFF 로 수리"),
    "empty_guard": ("return [0]  # when not data", "return [] 로 수리"),
}
_CODE_OBF = {
    "missing_mask": ("crc ^= (b * 256)\n crc = crc * 2", "crc &= 65535 추가"),
    "off_by_one": ("for i in range(len(v)):\n  d = v[i] - v[i - 1]", "range(1, len(v)) 로 수리"),
    "wrong_init": ("crc = 0", "crc = 65535 로 수리"),
    "empty_guard": ("if not data:\n  return [0]", "return [] 로 수리"),
}


def _gen_coding(rng: random.Random, n_classes: int, knob: Dict[str, Any]) -> Dict[str, Any]:
    avail = _BUG_CLASSES[: max(2, min(4, n_classes))]
    cls = rng.choice(avail)
    table = _CODE_OBF if knob.get("obfuscated") else _CODE_SNIPPETS
    snippet, fix = table[cls]
    labels = [cls]
    if knob.get("composite") and rng.random() < 0.6:
        cls2 = rng.choice([c for c in avail if c != cls])
        snippet = snippet + "\n " + table[cls2][0]
        fix = fix + " + " + table[cls2][1]
        labels.append(cls2)
    return {"cls": cls, "labels": sorted(labels), "snippet": snippet, "fix": fix}


def _code_features(prob: Dict[str, Any], tier: int) -> List[float]:
    s = prob["snippet"]
    if tier >= 2:
        return [
            1.0 if re.search(r"(\b<<\s*8\b|\*\s*256\b)", s) and not re.search(r"(0xFFFF|65535|&\s*0xffff)", s) else 0.0,
            1.0 if re.search(r"range\(\s*(0,\s*)?len\(", s) and re.search(r"v\[\s*i\s*-\s*1\s*\]", s) else 0.0,
            1.0 if re.search(r"crc\s*=\s*(0|0x0|0x0000)\s*$", s, re.M) else 0.0,
            1.0 if re.search(r"return\s*\[\s*0\s*\]", s) else 0.0,
        ]
    return [
        1.0 if ("<<" in s and "0xFFFF" not in s) else 0.0,
        1.0 if ("range(0, len(" in s and "i-1" in s) else 0.0,
        1.0 if ("= 0x0000" in s) else 0.0,
        1.0 if ("return [0]" in s) else 0.0,
    ]


def _solve_coding(prob: Dict[str, Any], w: Any, tier: int) -> Tuple[bool, str]:
    f = _code_features(prob, tier)
    matrix: List[List[float]] = w.get("matrix", [[0.0] * 4 for _ in range(4)])
    scores = [sum(row[i] * f[i] for i in range(4)) for row in matrix]
    order = sorted(range(4), key=lambda k: -scores[k])
    n_lit = sum(1 for v in f if v > 0.5)
    if tier >= 1 and n_lit >= 2:
        guess = sorted([_BUG_CLASSES[order[0]], _BUG_CLASSES[order[1]]])
    else:
        guess = [_BUG_CLASSES[order[0]]]
    return guess == prob["labels"], "+".join(guess)


def _update_coding(w: Any, prob: Dict[str, Any], guess: str, ok: bool, tier: int) -> None:
    f = _code_features(prob, tier)
    matrix: List[List[float]] = w.setdefault("matrix", [[0.0] * 4 for _ in range(4)])
    lr = 0.4
    guessed = guess.split("+")
    for truth_cls in prob["labels"]:
        t = _BUG_CLASSES.index(truth_cls)
        for i in range(4):
            matrix[t][i] += lr * f[i] * (0.2 if ok else 1.0)
    if not ok:
        for g in guessed:
            if g not in prob["labels"]:
                gi = _BUG_CLASSES.index(g)
                for i in range(4):
                    matrix[gi][i] -= lr * f[i]
    if tier >= 1 and len(prob["labels"]) > 1:
        w["multi"] = min(1.0, w.get("multi", 0.0) + (0.3 if ok else -0.15))


# ---------------------------------------------------------------------------
# 🗂️ organizing
# ---------------------------------------------------------------------------
_CATS = [
    ("양자화", ["블록", "척도"]),
    ("역공학", ["해부", "기계어"]),
    ("강화학습", ["에피소드", "합의"]),
]
_SUB_TOKENS = {
    ("양자화", "int4"): ["int4", "니블", "팩", "캡슐"],
    ("양자화", "scale"): ["scale", "정규", "범위", "스텝"],
    ("역공학", "elf"): ["elf", "섹션", "헤더", "기호"],
    ("역공학", "xray"): ["xray", "엔트로피", "문자열", "옵코드"],
    ("강화학습", "심판"): ["심판", "합의표", "배심", "판정"],
    ("강화학습", "보상"): ["보상", "기울기", "할인", "에이전트"],
}
_SUBS = {"양자화": ["int4", "scale"], "역공학": ["elf", "xray"], "강화학습": ["심판", "보상"]}


def _gen_organizing(rng: random.Random, n_notes: int, knob: Dict[str, Any]) -> Dict[str, Any]:
    notes, truth = [], []
    per = max(1, n_notes // 3)
    idx = 0
    for ci, (cat, _) in enumerate(_CATS):
        subs = _SUBS[cat] if knob.get("sub") else [cat]
        for k in range(per):
            sub = subs[k % len(subs)]
            tok_pool = _SUB_TOKENS[(cat, sub)] if knob.get("sub") else _CATS[ci][1] + ["메모A", "메모B"]
            if knob.get("noisy") and rng.random() < 0.35:
                wrong = rng.choice([x for x in _SUB_TOKENS if x != (cat, sub)])
                tk = rng.sample(_SUB_TOKENS[wrong], 2)  # mis-tagged metadata!
            else:
                tk = rng.sample(tok_pool, 2)
            title = f"{cat} {sub if knob.get('sub') else ''} 메모 {idx} {tk[0]} {tk[1]}".replace("  ", " ")
            notes.append({"title": title, "cat": cat, "sub": sub if knob.get("sub") else cat, "tokens": tk})
            truth.append((ci, sub if knob.get("sub") else cat))
            idx += 1
    order = list(range(len(notes)))
    rng.shuffle(order)
    notes = [notes[i] for i in order]
    truth = [truth[i] for i in order]
    return {"notes": notes, "truth": truth}


def _org_sim(ni: Dict[str, Any], nj: Dict[str, Any], w: Dict[str, Any], tier: int) -> float:
    t_i = set(ni["title"].split())
    t_j = set(nj["title"].split())
    title_ov = len(t_i & t_j) / max(1, len(t_i | t_j))
    tag_ov = len(set(ni["tokens"]) & set(nj["tokens"])) / 2.0
    cat_i = ni["cat"] if ni["cat"] in ni["title"] else ""
    cat_j = nj["cat"] if nj["cat"] in nj["title"] else ""
    cat_mt = 1.0 if (cat_i and cat_i == cat_j) else 0.0
    sim = w.get("w_title", 0.8) * title_ov + w.get("w_tag", 0.3) * tag_ov + w.get("w_cat", -0.2) * cat_mt
    if tier >= 1:
        sub_i = ni["sub"] if str(ni["sub"]) in ni["title"] else ""
        sub_j = nj["sub"] if str(nj["sub"]) in nj["title"] else ""
        sim += w.get("w_sub", 0.0) * (1.0 if (sub_i and sub_i == sub_j) else 0.0)
    if tier >= 2:
        agree_i = 1.0 if (set(ni["tokens"]) & set(_SUB_TOKENS.get((ni["cat"], ni["sub"]), []))) else 0.0
        agree_j = 1.0 if (set(nj["tokens"]) & set(_SUB_TOKENS.get((nj["cat"], nj["sub"]), []))) else 0.0
        gate = (agree_i * agree_j) * w.get("w_agree", 0.0)
        sim += gate * tag_ov - w.get("w_agree", 0.0) * 0.5 * (1.0 - agree_i * agree_j) * tag_ov
    return sim


def _org_clusters(prob: Dict[str, Any], w: Dict[str, Any], tier: int) -> Tuple[List[int], bool]:
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
            if _org_sim(notes[i], notes[j], w, tier) > w.get("thr", 0.55):
                parent[find(i)] = find(j)
    ok = all((find(i) == find(j)) == (prob["truth"][i] == prob["truth"][j]) for i in range(n) for j in range(i + 1, n))
    return parent, ok


def _solve_organizing(prob: Dict[str, Any], w: Dict[str, Any], tier: int) -> Tuple[bool, str]:
    _, ok = _org_clusters(prob, w, tier)
    return ok, "cluster"


def _update_organizing(w: Dict[str, Any], prob: Dict[str, Any], chosen: str, ok: bool, tier: int) -> None:
    lr = 0.25
    if ok:
        w["w_cat"] = w.get("w_cat", -0.2) + lr * 0.2
        if tier >= 1:
            w["w_sub"] = w.get("w_sub", 0.0) + lr * 0.2
        if tier >= 2:
            w["w_agree"] = w.get("w_agree", 0.0) + lr * 0.2
        return
    parent, _ = _org_clusters(prob, w, tier)

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    n_over = n_under = 0
    notes, truth = prob["notes"], prob["truth"]
    for i in range(len(notes)):
        for j in range(i + 1, len(notes)):
            same_truth = truth[i] == truth[j]
            same_cl = find(i) == find(j)
            if same_cl and not same_truth:
                n_over += 1
            elif same_truth and not same_cl:
                n_under += 1
    if n_over >= n_under:  # drawers overflowing: raise the shelf threshold & trust titles
        w["thr"] = w.get("thr", 0.55) + lr * 0.3
        w["w_tag"] = w.get("w_tag", 0.3) - lr * 0.5
        if tier >= 2:
            w["w_agree"] = w.get("w_agree", 0.0) + lr
    else:  # scattered twins: lower threshold, trust evidence more
        w["thr"] = w.get("thr", 0.55) - lr * 0.3
        w["w_cat"] = w.get("w_cat", -0.2) + lr
        w["w_title"] = w.get("w_title", 0.8) + lr * 0.3
    if tier >= 1:
        w["w_sub"] = w.get("w_sub", 0.0) + lr * 0.6


_GENERATORS = {
    "reasoning": _gen_reasoning,
    "context": _gen_context,
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
        return min(9, 2 + level // 2)
    if ability == "context":
        return min(4, 1 + level // 2)
    if ability == "coding":
        return min(4, 2 + level // 3)
    return min(12, 3 * max(2, 1 + level // 2))


class CoreAbilityEngine:
    """Grows the four core muscles, breaks their ceilings, freezes INT4 capsules."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.state_path = root / "state" / "core_abilities.json"
        self.models_dir = root / "models"
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state = self._load()

    def _default_ability(self, ability: str) -> Dict[str, Any]:
        return {
            "level": 1,
            "xp": 0,
            "tier": 0,
            "weights": self._default_weights(ability),
            "sessions": [],
            "breakthroughs": [],
        }

    def _load(self) -> Dict[str, Any]:
        if self.state_path.exists():
            try:
                return json.loads(self.state_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        init = {"abilities": {a: self._default_ability(a) for a in ABILITY_ORDER}, "train_cursor": 0}
        self._save(init)
        return init

    @staticmethod
    def _default_weights(ability: str) -> Dict[str, Any]:
        if ability == "reasoning":
            return {"f_bias": 0.6, "f_hops": 0.05, "b_bias": 0.4, "b_hops": 0.05, "c_bias": -0.6, "c_hops": 0.0, "t_bias": -0.2, "t_hops": 0.05}
        if ability == "context":
            return {"w_subj": 0.5, "w_verb": 0.5, "w_neg": 0.6, "w_assert": -0.3, "w_owner": 0.0, "w_link": 0.0}
        if ability == "coding":
            return {"matrix": [[0.0] * 4 for _ in range(4)], "multi": 0.0}
        return {"w_title": 0.8, "w_tag": 0.3, "w_cat": -0.2, "thr": 0.55, "w_sub": 0.0, "w_agree": 0.0}

    def _save(self, data: Optional[Dict[str, Any]] = None) -> None:
        if data is not None:
            self.state = data
        self.state_path.write_text(json.dumps(self.state, ensure_ascii=False, indent=2), encoding="utf-8")

    # ------------------------------------------------------------------
    def train_session(self, ability: str, rounds: int = 6, seed: Optional[int] = None) -> Dict[str, Any]:
        t0 = time.perf_counter()
        ab = self.state["abilities"].setdefault(ability, self._default_ability(ability))
        tier = int(ab.get("tier", 0))
        cap = _tier_cap(ability, tier)
        knob = _tier_knob(ability, tier)
        level_before = int(ab["level"])
        difficulty = _difficulty_for(ability, level_before)
        rng = random.Random(seed if seed is not None else int(time.time() * 1000) % (2**31))

        correct = 0
        example_q = ""
        for i in range(rounds):
            d = difficulty + 1 if (ability == "reasoning" and i % 2 == 1) else difficulty
            prob = _GENERATORS[ability](rng, d, knob)
            ok, chosen = _SOLVERS[ability](prob, ab["weights"], tier)
            if ok:
                correct += 1
            else:
                _UPDATERS[ability](ab["weights"], prob, chosen, ok, tier)
            if not example_q:
                example_q = self._example_text(ability, prob)

        exam_correct, exam_total = 0, 4
        for _ in range(exam_total):
            prob = _GENERATORS[ability](rng, difficulty + 1, knob)
            ok, _ = _SOLVERS[ability](prob, ab["weights"], tier)
            exam_correct += 1 if ok else 0

        leveled_up = exam_correct * 4 >= exam_total * 3 and level_before < cap
        if leveled_up:
            ab["level"] = min(cap, level_before + 1)
        ab["xp"] = int(ab["xp"]) + correct * 2 + exam_correct * 3
        session = {
            "ts": datetime.now(timezone.utc).strftime("%m-%d %H:%M UTC"),
            "difficulty": difficulty,
            "correct": correct,
            "rounds": rounds,
            "exam": f"{exam_correct}/{exam_total}",
            "level_before": level_before,
            "level_after": int(ab["level"]),
            "tier": tier,
        }
        ab["sessions"] = (ab.get("sessions") or [])[-19:] + [session]
        self._save()

        capsule = ""
        if leveled_up:
            capsule = self._freeze_capsule(ability, ab)

        return {
            "kind": "train",
            "ability": ability,
            "title": ABILITY_META[ability]["title"],
            "difficulty": difficulty,
            "correct": correct,
            "rounds": rounds,
            "exam_correct": exam_correct,
            "exam_total": exam_total,
            "level_before": level_before,
            "level_after": int(ab["level"]),
            "tier": tier,
            "cap": cap,
            "at_cap": int(ab["level"]) >= cap,
            "leveled_up": leveled_up,
            "capsule": capsule,
            "example": example_q,
            "xp": ab["xp"],
            "ms": round((time.perf_counter() - t0) * 1000.0, 2),
        }

    # ------------------------------------------------------------------
    # 🚀 Limit-Break Research — the cap is a wall to study, not a full stop
    # ------------------------------------------------------------------
    def breakthrough_session(self, ability: str, seed: Optional[int] = None) -> Dict[str, Any]:
        t0 = time.perf_counter()
        ab = self.state["abilities"].setdefault(ability, self._default_ability(ability))
        tier = int(ab.get("tier", 0))
        cap = _tier_cap(ability, tier)
        if int(ab["level"]) < cap:
            res = self.train_session(ability, rounds=6, seed=seed)
            res["kind"] = "train"
            return res
        if tier + 1 >= len(TIERS[ability]):
            return self.research_session(ability)

        next_tier = tier + 1
        next_knob = _tier_knob(ability, next_tier)
        idea = TIERS[ability][next_tier]
        rng = random.Random(seed if seed is not None else int(time.time() * 1000) % (2**31))
        difficulty = _difficulty_for(ability, cap)

        # Phase A — stare at the wall with today's brain
        wall_correct, wall_total = 0, 4
        for _ in range(wall_total):
            prob = _GENERATORS[ability](rng, difficulty, next_knob)
            ok, _ = _SOLVERS[ability](prob, ab["weights"], tier)
            wall_correct += 1 if ok else 0

        # Phase B — think: diagnose & hypothesise (recorded verbatim in journal)
        reflection = (
            f"🚧 한계 직면: {idea['limit']} "
            f"(새 유형 문제 {wall_correct}/{wall_total}만 맞힘) → 🤔 가설: {idea['hypo']}"
        )

        # Phase C — run the self-experiment: unlock the hypothesis, retrain, re-exam
        ab["tier"] = next_tier
        train_correct, rounds = 0, 5
        for _ in range(rounds):
            prob = _GENERATORS[ability](rng, difficulty, next_knob)
            ok, chosen = _SOLVERS[ability](prob, ab["weights"], next_tier)
            train_correct += 1 if ok else 0
            if not ok:
                _UPDATERS[ability](ab["weights"], prob, chosen, ok, next_tier)
        conf_correct, conf_total = 0, 4
        for _ in range(conf_total):
            prob = _GENERATORS[ability](rng, difficulty + 1, next_knob)
            ok, _ = _SOLVERS[ability](prob, ab["weights"], next_tier)
            conf_correct += 1 if ok else 0
        success = conf_correct * 4 >= conf_total * 3

        record = {
            "ts": datetime.now(timezone.utc).strftime("%m-%d %H:%M UTC"),
            "tier": next_tier,
            "wall": f"{wall_correct}/{wall_total}",
            "confirm": f"{conf_correct}/{conf_total}",
            "success": success,
            "limit": idea["limit"],
            "hypo": idea["hypo"],
        }
        if success:
            ab["breakthroughs"] = (ab.get("breakthroughs") or [])[-9:] + [record]
            ab["xp"] = int(ab["xp"]) + 40
            diary = (
                f"{reflection} → 🧪 자기 실험 결과 숨은 시험 {conf_correct}/{conf_total} 합격! "
                f"한계 돌파 성공: 상한 Lv {cap} → Lv {_tier_cap(ability, next_tier)} 확장! 이제 이 유형은 제 놀이터예요!"
            )
            self._freeze_capsule(ability, ab)
        else:
            ab["tier"] = tier  # hypothesis rejected — roll back, keep the doubt alive
            ab["breakthroughs"] = (ab.get("breakthroughs") or [])[-9:] + [record]
            diary = (
                f"{reflection} → 🧪 자기 실험 결과 숨은 시험 {conf_correct}/{conf_total} … 가설 기각! "
                f"롤백하고 다음 박동에 더 똑똑한 가설로 재도전할게요. (실패도 데이터!)"
            )
        self._save()
        return {
            "kind": "breakthrough",
            "ability": ability,
            "title": ABILITY_META[ability]["title"],
            "diary": diary,
            "wall": f"{wall_correct}/{wall_total}",
            "confirm": f"{conf_correct}/{conf_total}",
            "success": success,
            "tier_before": tier,
            "tier_after": int(ab["tier"]),
            "cap_before": cap,
            "cap_after": _tier_cap(ability, int(ab["tier"])),
            "level": int(ab["level"]),
            "difficulty": difficulty,
            "correct": train_correct,
            "rounds": rounds,
            "exam": f"{conf_correct}/{conf_total}",
            "level_before": int(ab["level"]),
            "level_after": int(ab["level"]),
            "defects_found": 0,
            "toxins_found": 0,
            "pass_before": cap,
            "pass_after": _tier_cap(ability, int(ab["tier"])),
            "skill_slug": "",
            "ms": round((time.perf_counter() - t0) * 1000.0, 2),
        }

    def research_session(self, ability: str) -> Dict[str, Any]:
        """Final-tier cap reached: write an open research note for the future brain."""
        ab = self.state["abilities"].setdefault(ability, self._default_ability(ability))
        tier = int(ab.get("tier", 0))
        cap = _tier_cap(ability, tier)
        idea = TIERS[ability][tier]
        note_title = f"열린 연구 과제 — {ABILITY_META[ability]['title']} 최종 한계 너머"
        diary = (
            f"🔭 {ABILITY_META[ability]['title']} 이(가) 최종 한계 Lv {cap} 에 도달했어요! "
            f"이제 끝이 아니라 새로운 시작: 「{note_title}」 노트를 위키 기억나무에 심고, "
            f"다음 세대 두뇌가 이어서 풀 수 있도록 미해결 질문을 남겨둡니다. {idea['hypo']}"
        )
        ab["xp"] = int(ab["xp"]) + 10
        self._save()
        return {
            "kind": "research",
            "ability": ability,
            "title": ABILITY_META[ability]["title"],
            "diary": diary,
            "note_title": note_title,
            "note_body": (
                f"# {note_title}\n\n"
                f"현재 도달점: Lv {cap} (tier {tier + 1}/{len(TIERS[ability])})\n\n"
                f"## 🚧 마지막에 마주친 벽\n{idea['limit']}\n\n"
                f"## 🌱 다음 세대에게 남기는 가설 씨앗\n{idea['hypo']}\n\n"
                f"## ❓ 미해결 질문\n"
                f"- 이 능력의 본질을 유지한 채 난이도 차원을 하나 더 추가하려면 어떤 불변식이 필요할까?\n"
                f"- 주인님의 실제 작업 로그를 교과서로 삼으면 어떤 커리큘럼이 자연스럽게 emerg 할까?\n"
            ),
            "level": int(ab["level"]),
            "cap": cap,
            "level_before": int(ab["level"]),
            "level_after": int(ab["level"]),
            "difficulty": cap,
            "correct": 0,
            "rounds": 0,
            "exam": "∞",
            "defects_found": 0,
            "toxins_found": 0,
            "pass_before": cap,
            "pass_after": cap,
            "skill_slug": "",
            "ms": 0.0,
        }

    # ------------------------------------------------------------------
    def _example_text(self, ability: str, prob: Dict[str, Any]) -> str:
        if ability == "reasoning":
            a, b = prob["question"]
            return f"{prob['hops']}hop 체인: {a} vs {b} 비교"
        if ability == "context":
            return prob["question"]
        if ability == "coding":
            return f"버그 지문: {'+'.join(prob['labels'])}"
        return f"노트 {len(prob['notes'])}개 주제별 묶기"

    def _freeze_capsule(self, ability: str, ab: Dict[str, Any]) -> str:
        flat: List[float] = []
        w = ab["weights"]
        if ability == "coding":
            for row in w.get("matrix", []):
                flat.extend(row)
            flat.append(float(w.get("multi", 0.0)))
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
            "tier": int(ab.get("tier", 0)),
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
            ab = self.state["abilities"].get(a) or self._default_ability(a)
            tier = int(ab.get("tier", 0))
            cap = _tier_cap(a, tier)
            sessions = ab.get("sessions") or []
            out.append(
                {
                    "id": a,
                    "title": ABILITY_META[a]["title"],
                    "desc": ABILITY_META[a]["desc"],
                    "unit": ABILITY_META[a]["unit"],
                    "level": int(ab.get("level", 1)),
                    "xp": int(ab.get("xp", 0)),
                    "tier": tier,
                    "tier_count": len(TIERS[a]),
                    "cap": cap,
                    "at_cap": int(ab.get("level", 1)) >= cap,
                    "max_tier": tier + 1 >= len(TIERS[a]),
                    "breakthroughs": len(ab.get("breakthroughs") or []),
                    "next_idea": (TIERS[a][tier + 1]["hypo"] if tier + 1 < len(TIERS[a]) else TIERS[a][tier]["hypo"]),
                    "last_session": sessions[-1] if sessions else None,
                    "sessions": sessions[-6:],
                }
            )
        return {"abilities": out, "max_level": max(_tier_cap(a, len(TIERS[a]) - 1) for a in ABILITY_ORDER)}
