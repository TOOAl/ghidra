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

# 💡 Stage J — meaning trust.  `w_sem` is the context muscle's own answer to
# "how much should a memory that shares NO words with the question still count?"
# SEM_SCORE_SCALE maps that trust onto the recall scoreboard, where a title hit
# is worth 5.0 points and 1.5 points is the floor for "this is real evidence".
CONTEXT_SEM_PRIOR = 0.35
SEM_SCORE_SCALE = 8.0
SEM_TRUST_MAX = 1.5
# If the meaning space understands less than a third of the question's words,
# its score for the rest is imagination, not evidence — so it is not allowed to
# pull a memory over the "this is real evidence" line.  (A question built from
# one known word out of seven must stay honestly unanswerable.)
SEM_MIN_COVERAGE_PCT = 30.0

# 💡 Stage K — the ORGANIZING muscle gets its own trust in meaning.  Measured on
# the real 12-note vault before choosing a number: pairs whose keywords do not
# overlap AT ALL (skill cartridge ↔ XOR-vault autopsy) sit at meaning cosine
# 0.43 while the muscle's own similarity says 0.05, so keyword Jaccard is
# structurally blind to them.  Sweeping the weight showed 1.1 recovering 6 of the
# 17 genuinely linked pairs with ZERO invented links, and 1.4 recovering 11 but
# inventing 2 — so the newborn starts timid and the cap stays just past the point
# where invention was still unmeasurable.
ORG_SEM_PRIOR = 0.35
ORG_SEM_MAX = 1.2
# A missed pair counts as "meaning could have fixed this" only when the two notes
# are at least this close in meaning.  Measured on the real vault: pairs in the
# same drawer average cos 0.452 (median 0.374) while pairs in different drawers
# average 0.117 (median 0.069), so 0.30 sits on the observed dividing line.
ORG_SEM_HOPE = 0.30
# How far below the shelf a keyword score may sit and still count as "one nudge
# away".  A pair whose evidence is nowhere near the shelf cannot be fixed by ANY
# setting of these valves — chasing those dragged `thr` from 0.55 down to 0.21 on
# 16 real notes, which only bought new wrong merges.  The vault, not the muscle,
# is what has to grow before those pairs become linkable.
ORG_REACH_BAND = 0.15


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
    # Stored experiences come back from JSON as lists of lists; `set(facts)` below
    # needs hashable pairs, so normalise once at the door.
    facts = [tuple(f) for f in prob["facts"]]
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
    if prob.get("real_mode"):
        # 📓 Stage I: a REAL recall problem — the 6 features were frozen when the
        # chat actually happened, so the same weights are exercised on real text.
        feats = prob.get("features") or []
        sems = prob.get("sem_sims") or []
        w_sem = float(w.get("w_sem", CONTEXT_SEM_PRIOR))
        best, best_score = None, -1e18
        for i, sent in enumerate(prob.get("sentences") or []):
            f = feats[i] if i < len(feats) else [0.0] * 6
            score = (
                w.get("w_subj", 0.5) * f[0]
                + w.get("w_verb", 0.5) * f[1]
                + w.get("w_neg", 0.6) * f[2]
                + w.get("w_assert", -0.3) * f[3]
                + (w.get("w_owner", 0.0) * f[4] if tier >= 1 and len(f) > 4 else 0.0)
                + (w.get("w_link", 0.0) * f[5] if tier >= 2 and len(f) > 5 else 0.0)
                + (w_sem * float(sems[i]) if i < len(sems) else 0.0)
            )
            if score > best_score:
                best, best_score = sent, score
        return best == prob.get("answer_sentence"), best or ""

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
    keys = ["w_subj", "w_verb", "w_neg", "w_assert"] + (["w_owner"] if tier >= 1 else []) + (["w_link"] if tier >= 2 else [])
    if prob.get("real_mode"):
        # Same perceptron rule as the gym, applied to the frozen REAL features:
        # move toward the note that truly grounded the answer, away from the one
        # the muscle actually picked.
        sents = prob.get("sentences") or []
        feats = prob.get("features") or []
        gi = sents.index(prob.get("answer_sentence")) if prob.get("answer_sentence") in sents else -1
        bi = sents.index(chosen) if chosen in sents else -1
        if gi < 0:
            return
        lr_real = 0.3
        f_good = feats[gi] if gi < len(feats) else [0.0] * len(keys)
        f_bad = feats[bi] if 0 <= bi < len(feats) else [0.0] * len(keys)
        for i, key in enumerate(keys):
            if i < len(f_good) and i < len(f_bad):
                w[key] = w.get(key, 0.0) + lr_real * (f_good[i] - f_bad[i])
        sems = prob.get("sem_sims") or []
        if sems and gi < len(sems):
            # 💡 Stage J: when the note that REALLY grounded the answer sat closer
            # in meaning than the note the muscle picked, trust meaning more —
            # and less when meaning led it astray.  This is the only place w_sem
            # moves; invented gym puzzles emit no sem_sims, so they cannot
            # corrupt a weight that only real memory work can teach.
            good_sem = float(sems[gi])
            if 0 <= bi < len(sems):
                ref_sem = float(sems[bi])
            else:
                others = [float(v) for i, v in enumerate(sems) if i != gi]
                ref_sem = sum(others) / len(others) if others else 0.0
            w["w_sem"] = max(
                0.0,
                min(
                    SEM_TRUST_MAX,
                    float(w.get("w_sem", CONTEXT_SEM_PRIOR)) + lr_real * (good_sem - ref_sem),
                ),
            )
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
    # Bounded evidence: the matrix records HOW STRONGLY each fingerprint implies
    # each bug class, so it saturates instead of growing with every repetition.
    lo, hi = -3.0, 3.0
    for truth_cls in prob["labels"]:
        t = _BUG_CLASSES.index(truth_cls)
        for i in range(4):
            matrix[t][i] = max(lo, min(hi, matrix[t][i] + lr * f[i] * (0.2 if ok else 1.0)))
    if not ok:
        for g in guessed:
            if g not in prob["labels"]:
                gi = _BUG_CLASSES.index(g)
                for i in range(4):
                    matrix[gi][i] = max(lo, min(hi, matrix[gi][i] - lr * f[i]))
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


def _org_sim(
    ni: Dict[str, Any],
    nj: Dict[str, Any],
    w: Dict[str, Any],
    tier: int,
    real: bool = False,
    sem: Optional[float] = None,
) -> float:
    t_i = set(ni["title"].split())
    t_j = set(nj["title"].split())
    title_ov = len(t_i & t_j) / max(1, len(t_i | t_j))
    shared = set(ni["tokens"]) & set(nj["tokens"])
    if real:
        # Jaccard: real notes carry 4-8 tags, and the gym's "/2.0" (tuned for
        # 2-tag puzzles) would score a SINGLE shared tag as 0.5 = near max,
        # gluing unrelated notes together no matter what the muscle learns.
        union = set(ni["tokens"]) | set(nj["tokens"])
        tag_ov = len(shared) / len(union) if union else 0.0
    else:
        tag_ov = len(shared) / 2.0
    cat_i = ni["cat"] if ni["cat"] in ni["title"] else ""
    cat_j = nj["cat"] if nj["cat"] in nj["title"] else ""
    cat_mt = 1.0 if (cat_i and cat_i == cat_j) else 0.0
    sim = w.get("w_title", 0.8) * title_ov + w.get("w_tag", 0.3) * tag_ov + w.get("w_cat", -0.2) * cat_mt
    # 💡 Stage K: MEANING as a shelf feature.  Only on the real path and only
    # when a frozen cosine came with the problem — invented gym puzzles have no
    # meaning space behind them, and pretending otherwise would let the gym
    # train a weight that the field can never reproduce.
    if real and sem is not None:
        sim += float(w.get("w_sem", ORG_SEM_PRIOR)) * float(sem)
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


def _org_same_truth(prob: Dict[str, Any], i: int, j: int) -> bool:
    """Do notes i and j belong in the same drawer?  One answer, used everywhere.

    Category + document kind is the gym's opinion.  On a REAL vault the brain
    holds a second, older opinion of its own: the [[links]] it already wrote.  A
    pair the vault has already connected was judged related by the brain itself,
    so punishing the muscle for merging it teaches the muscle to contradict its
    own wiki — measured on 14 real notes this is exactly what froze `w_sem`:
    the strongest cross-drawer meaning pair (cos 0.61) is a pair the vault had
    ALREADY linked, and every attempt to trust meaning enough to fix three real
    misses (cos 0.55–0.71) was cancelled by that invented "over-merge".

    Link COMPONENTS are far too loose to serve as truth (19 links collapse 14
    notes into 2 blobs, calling 40 pairs mandatory), so only direct pairs count.

    💡 Stage K: a SHARED TAG is the third opinion, and it is the one that survived
    measurement.  Splitting the category label into topic words looked tempting
    («역공학·보안» vs «Ghidra·역공학» are one shelf written twice) but on 12 real
    notes it mandated 12 extra pairs of which 10 were nonsense — «스킬 카트리지»
    glued to «성좌 담론» merely because both labels contain 양자화, at meaning
    cosine 0.08.  Sharing an actual tag added exactly 2 pairs and both were the
    genuine ones (the «ghidra» tag, cosine 0.35).  So truth is built only from
    evidence the vault wrote itself: its links and its tags.
    """
    truth = prob.get("truth") or []
    if i < len(truth) and j < len(truth) and truth[i] == truth[j]:
        return True
    key = f"{min(i, j)}-{max(i, j)}"
    lp = prob.get("linked_pairs")
    if lp and key in (lp if isinstance(lp, (set, frozenset)) else set(lp)):
        return True
    st = prob.get("shared_tag_pairs")
    if st:
        return key in (st if isinstance(st, (set, frozenset)) else set(st))
    return False


def _org_clusters(prob: Dict[str, Any], w: Dict[str, Any], tier: int) -> Tuple[List[int], bool]:
    notes = prob["notes"]
    n = len(notes)
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    # Frozen meaning cosines for the SAME pair order used below (i ascending,
    # j > i).  They are captured when the lesson is written, so revision re-solves
    # the exact situation the muscle actually faced — never a re-guessed one.
    real = bool(prob.get("real_mode"))
    sems = prob.get("sem_pairs") if real else None
    k = 0
    for i in range(n):
        for j in range(i + 1, n):
            cs = None
            if sems and k < len(sems):
                try:
                    cs = float(sems[k])
                except (TypeError, ValueError):
                    cs = None
            k += 1
            if _org_sim(notes[i], notes[j], w, tier, real, cs) > w.get("thr", 0.55):
                parent[find(i)] = find(j)
    ok = all((find(i) == find(j)) == _org_same_truth(prob, i, j) for i in range(n) for j in range(i + 1, n))
    return parent, ok


def _solve_organizing(prob: Dict[str, Any], w: Dict[str, Any], tier: int) -> Tuple[bool, str]:
    _, ok = _org_clusters(prob, w, tier)
    return ok, "cluster"


def _update_organizing(w: Dict[str, Any], prob: Dict[str, Any], chosen: str, ok: bool, tier: int) -> None:
    lr = 0.25
    if ok:
        # Deliberate NO-OP on success.  Rewarding a correct clustering by raising
        # w_cat/w_sub makes every pair look similar → drawers over-merge → the
        # shelf threshold chases them upward until nothing links at all.  This
        # muscle only learns from its own over/under-merge diagnosis below.
        # (Its starting weights are already non-zero, so unlike the coding
        # matrix it never "claims to know" an answer with zero evidence.)
        return
    parent, _ = _org_clusters(prob, w, tier)

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    n_over = n_under = 0
    notes = prob["notes"]
    for i in range(len(notes)):
        for j in range(i + 1, len(notes)):
            same_truth = _org_same_truth(prob, i, j)
            same_cl = find(i) == find(j)
            if same_cl and not same_truth:
                n_over += 1
            elif same_truth and not same_cl:
                n_under += 1
    total_pairs = len(notes) * (len(notes) - 1) // 2
    if prob.get("real_mode") and total_pairs:
        # 💡 Stage K — CREDIT ASSIGNMENT on the real shelf.
        #
        # Four valves share one shelf: `thr` (how high), `w_tag`/`w_cat`/`w_title`
        # (keyword evidence) and `w_sem` (meaning).  Until now every valve
        # reacted to the TOTAL confusion, and they fought: a wrong merge caused
        # by a runaway `w_title` was punished by cutting `w_sem`, while a missed
        # pair that meaning could have fixed was "fixed" by raising `w_title`
        # until every pair sharing the word 「역공학」 merged by itself.  Measured on
        # 16 real notes: misses 23 -> 10 while over-merges exploded 0 -> 21 and
        # `w_sem` was dragged 0.35 -> 1.2 -> 0.17 in a sawtooth.
        #
        # So each wrong pair is attributed to the evidence that actually carried
        # it, and ONLY that valve moves.  Meaning is blamed only for pairs that
        # crossed the shelf BECAUSE of meaning (keyword score below, total above),
        # and it is trusted only where the keyword score cannot reach and the two
        # notes are genuinely close in meaning (>= ORG_SEM_HOPE).
        sems = prob.get("sem_pairs") or []
        w_sem = float(w.get("w_sem", ORG_SEM_PRIOR))
        thr_v = float(w.get("thr", 0.55))
        # Over-merge blame is SPLIT, not assigned whole: on the real vault the
        # stubborn wrong pairs («역공학 해부 도감» ↔ «Ghidra 헤드리스») sit at
        # keyword score 0.385 with meaning cosine 0.34 — the shelf was already
        # nearly reached and meaning delivered the last push.  Charging all of it
        # to `w_sem` drove it 0.70 -> 0.07 in six rounds while the keyword valve
        # went untouched, so each valve now pays in proportion to what it added.
        kw_over = 0.0
        sem_over = 0.0
        kw_under = sem_hope = sem_hold = far = 0
        k = 0
        for i in range(len(notes)):
            for j in range(i + 1, len(notes)):
                cs = None
                if sems and k < len(sems):
                    try:
                        cs = float(sems[k])
                    except (TypeError, ValueError):
                        cs = None
                k += 1
                base = _org_sim(notes[i], notes[j], w, tier, real=True)
                sim = base + (w_sem * cs if cs is not None else 0.0)
                same_t = _org_same_truth(prob, i, j)
                same_c = find(i) == find(j)
                if same_c and not same_t:
                    if cs is not None and base <= thr_v < sim:
                        added = sim - base
                        share = (sim - thr_v) / added if added > 1e-9 else 1.0
                        share = max(0.0, min(1.0, share))
                        sem_over += share      # the decisive slice of the push
                        kw_over += 1.0 - share  # the shelf was already this close
                    else:
                        kw_over += 1.0          # keywords invented this link alone
                elif same_t and not same_c:
                    # Only count a miss when SOME valve could actually fix it.
                    # Meaning gets the pair if raising w_sem to its cap would
                    # carry it over the shelf; keywords get it if the score is
                    # already within one nudge.  Everything else is a gap in the
                    # vault's own evidence, not a mistake to be chased.
                    if cs is not None and cs >= ORG_SEM_HOPE and (base + ORG_SEM_MAX * cs) > thr_v:
                        sem_hope += 1          # meaning could fix this miss
                    elif base >= thr_v - ORG_REACH_BAND:
                        kw_under += 1          # one nudge of the shelf would fix it
                    else:
                        far += 1               # honestly out of reach for now
                elif same_t and same_c and cs is not None and base <= thr_v < sim:
                    sem_hold += 1              # meaning is what holds this pair

        # --- the meaning valve: reward and blame applied AT THE SAME TIME ---
        # (`elif` used to mean that a single wrong merge silenced every reason to
        # trust meaning, so the weight could only fall — it never found a level.)
        if sem_over or sem_hope or sem_hold:
            delta = (sem_hope * 0.6 + sem_hold * 0.3) - (sem_over * 1.2)
            step_sem = max(-1.0, min(1.0, delta * 8.0 / total_pairs))
            w["w_sem"] = round(max(0.0, min(ORG_SEM_MAX, w_sem + lr * 1.1 * step_sem)), 4)

        # --- the keyword valves: the shelf height follows KEYWORD confusion ---
        need_merge = (kw_under - kw_over) / float(total_pairs)   # >0 = merge more
        step = max(-lr * 0.3, min(lr * 0.3, 0.45 * need_merge))
        w["thr"] = round(max(0.12, min(1.15, float(w.get("thr", 0.55)) - step)), 4)
        if kw_over:
            rate = min(1.0, kw_over * 8.0 / total_pairs)
            w["w_tag"] = max(-0.4, w.get("w_tag", 0.3) - lr * 0.5 * rate)
            # The runaway was w_title, and nothing ever braked it: a pair whose
            # titles share one long word («역공학 해부 도감») scores 0.57 alone,
            # above the 0.55 shelf, before any other evidence is consulted.
            w["w_title"] = round(max(0.0, float(w.get("w_title", 0.8)) - lr * 0.6 * rate), 4)
            w["w_cat"] = round(max(-0.6, float(w.get("w_cat", -0.2)) - lr * 0.4 * rate), 4)
        if kw_under and not kw_over:
            rate = min(1.0, kw_under * 8.0 / total_pairs)
            w["w_cat"] = min(1.2, w.get("w_cat", -0.2) + lr * rate)
            w["w_title"] = min(1.6, w.get("w_title", 0.8) + lr * 0.3 * rate)
        if tier >= 1 and kw_under > kw_over:
            w["w_sub"] = min(1.5, w.get("w_sub", 0.0) + lr * 0.6)
        return

    if n_over >= n_under:  # drawers overflowing: raise the shelf threshold & trust titles
        w["thr"] = min(1.15, w.get("thr", 0.55) + lr * 0.3)
        w["w_tag"] = w.get("w_tag", 0.3) - lr * 0.5
        if tier >= 2:
            w["w_agree"] = w.get("w_agree", 0.0) + lr
    else:  # scattered twins: lower threshold, trust evidence more
        w["thr"] = max(0.12, w.get("thr", 0.55) - lr * 0.3)
        w["w_cat"] = w.get("w_cat", -0.2) + lr
        w["w_title"] = w.get("w_title", 0.8) + lr * 0.3
    if tier >= 1:
        w["w_sub"] = min(1.5, w.get("w_sub", 0.0) + lr * 0.6)


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

# ===========================================================================
# Stage H — FIELD DEPLOYMENT ⚔️  (the muscles leave the gym and do REAL work)
# ---------------------------------------------------------------------------
# Master's directive: a muscle is only a real ability when it is USED.  Each of
# the four muscles is wired into one live organ, and — crucially — the organ
# consumes the SAME learned weights the gym trained, through the SAME feature
# functions (`_context_features` semantics, `_code_features`, `_org_sim`).  No
# parallel "fake" scoring: what the muscle learned is literally what the organ
# now does, so a higher level measurably changes real output.
# ===========================================================================
FIELD_SITES: Dict[str, Dict[str, str]] = {
    "reasoning": {
        "site": "pantheon_debate",
        "title": "🏛️ 성좌 원탁 담론",
        "verb": "논증 체인 역추적",
        "detail": "천재들의 발언을 hop 수(2 + Lv÷4)만큼 사슬로 엮어 결론까지 역추적하고, 그 깊이만큼 증류 강도를 올립니다.",
    },
    "context": {
        "site": "wiki_recall",
        "title": "📚 위키 기억 호출",
        "verb": "기억 재랭킹",
        "detail": "학습된 문맥 가중치 6종(주어·서술·부정·단정·소유주·링크)으로 실제 위키 기억 카드를 다시 정렬하고 호출 매수를 늘립니다.",
    },
    "coding": {
        "site": "forge_audit",
        "title": "🛠️ 4단계 원인 감사",
        "verb": "버그 지문 예측",
        "detail": "학습된 4×4 버그 지문 행렬로 실제 편집창 코드를 훑어 의심 클래스 순위를 매기고 처방전 우선순위를 재배열합니다.",
    },
    "organizing": {
        "site": "wiki_weave",
        "title": "🕸️ 위키 시냅스 엮기",
        "verb": "자동 그룹핑",
        "detail": "학습된 임계값(thr)과 제목·태그·카테고리·하위주제 가중치로 실제로 엮을 노트 쌍만을 선별합니다.",
    },
}

# Honest gym-feature → real-document-feature mapping (context muscle).
_CTX_NEG_RE = re.compile(r"(아닙니다|아니에요|없다|없음|없습니다|한계|불가|금지|주의|\bnot\b|\bnever\b)")
_CTX_ASSERT_RE = re.compile(r"(반드시|항상|원리|핵심|공식|불변식|규칙|\bmust\b|\balways\b)")

# Real finding text → gym bug class (coding muscle ground truth for scoring).
_BUG_CLASS_TEXT_RE = {
    "missing_mask": re.compile(r"(0xFF|0xFFFF|65535|마스크|마스킹|8비트|16비트|넘침|overflow)", re.I),
    "off_by_one": re.compile(r"(range\(|off.by.one|1비트|마지막|한 번|반복 횟수)", re.I),
    "wrong_init": re.compile(r"(초기값|초기화|\binit\b|0x0000|seed)", re.I),
    "empty_guard": re.compile(r"(빈 입력|빈 배열|empty|return \[\]|길이)", re.I),
}


def field_reasoning_hops(field: Dict[str, Any]) -> int:
    """How many argument hops the round-table may chain (Lv 1→2, Lv 32→6)."""
    return max(2, min(6, 2 + int(field.get("level", 1)) // 4))


def field_reasoning_boost(field: Dict[str, Any]) -> float:
    """Deeper chains → slightly stronger mentorship distillation into neurons."""
    return round(1.0 + 0.012 * min(int(field.get("level", 1)), 32), 4)


def field_context_limit(field: Dict[str, Any]) -> int:
    """A sharper context muscle is trusted with more recall cards (2 → 6)."""
    return max(2, min(6, 2 + int(field.get("level", 1)) // 6))


def field_context_features(field: Dict[str, Any], notes: List[Dict[str, Any]], query_terms: List[str]) -> List[List[float]]:
    """The 6 REAL-document features per note, in `_context_features` order.

    [subj, verb, neg, assert, owner, link] — the same six concepts the gym
    trains, mapped onto wiki notes (see FIELD_SITES for the mapping).  Exposed
    separately so a real recall can be stored as a re-studyable problem.
    """
    tier = int(field.get("tier", 0))
    subj = ((query_terms[0] if query_terms else "") or "").lower()
    feats: List[List[float]] = []
    for n in notes:
        tl = str(n.get("title", "")).lower()
        body = f"{n.get('summary', '')} {n.get('body', '')}".lower()
        cat = str(n.get("category", "")).lower()
        tags = " ".join(str(t) for t in (n.get("tags") or [])).lower()
        f_subj = 1.0 if (subj and subj in tl) else 0.0
        f_verb = 1.0 if any(t and str(t).lower() in body for t in query_terms) else 0.0
        f_neg = 1.0 if _CTX_NEG_RE.search(body) else 0.0
        f_assert = 1.0 if (_CTX_ASSERT_RE.search(body) and f_neg == 0.0) else 0.0
        f_owner = 1.0 if (subj and (subj in cat or subj in tags)) else 0.0
        f_link = 1.0 if n.get("links") else 0.0
        f = [f_subj, f_verb, f_neg, f_assert]
        if tier >= 1:
            f.append(f_owner)
        if tier >= 2:
            f.append(f_link)
        feats.append(f)
    return feats


def field_context_semantic_trust(field: Optional[Dict[str, Any]]) -> float:
    """How strongly the context muscle currently trusts MEANING (learned, not fixed)."""
    w = (field or {}).get("weights") or {}
    try:
        trust = float(w.get("w_sem", CONTEXT_SEM_PRIOR))
    except (TypeError, ValueError):
        trust = CONTEXT_SEM_PRIOR
    return max(0.0, min(SEM_TRUST_MAX, trust))


def field_context_rerank(field: Dict[str, Any], notes: List[Dict[str, Any]], query_terms: List[str]) -> List[float]:
    """Score REAL wiki notes with the context muscle's LEARNED weights."""
    w = field.get("weights") or {}
    tier = int(field.get("tier", 0))
    feats = field_context_features(field, notes, query_terms)
    scores: List[float] = []
    for f in feats:
        sc = (
            float(w.get("w_subj", 0.5)) * f[0]
            + float(w.get("w_verb", 0.5)) * f[1]
            + float(w.get("w_neg", 0.6)) * f[2]
            + float(w.get("w_assert", -0.3)) * f[3]
        )
        if tier >= 1 and len(f) > 4:
            sc += float(w.get("w_owner", 0.0)) * f[4]
        if tier >= 2 and len(f) > 5:
            sc += float(w.get("w_link", 0.0)) * f[5]
        scores.append(round(sc, 4))
    return scores


def context_experience_case(
    field: Dict[str, Any], query: str, recall_bundle: Dict[str, Any], audit: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """📓 Stage I: the hallucination audit IS the context muscle's report card.

    safe    -> the note it ranked first truly grounded the answer   (ok)
    caution -> another recalled note carried more matched evidence, so THAT note
               becomes the answer the muscle must learn to pick      (mistake)
    high    -> the vault holds no evidence at all; that is not the muscle's
               fault, so no lesson is written (honest bookkeeping)
    """
    grade = str(audit.get("grade") or "")
    recalled = recall_bundle.get("recalled") or []
    if grade not in ("safe", "caution") or len(recalled) < 2:
        return None
    # 💡 Stage J: a lesson needs a trustworthy right answer.  When the question
    # was only partly understood, "which memory really grounded it" is a guess —
    # and teaching a guess is how a brain learns to be confidently wrong.
    sem_info = recall_bundle.get("semantic") or {}
    try:
        cov_pct = float((sem_info.get("query_coverage") or {}).get("pct") or 0.0)
    except (TypeError, ValueError):
        cov_pct = 100.0
    if grade == "caution" and cov_pct < SEM_MIN_COVERAGE_PCT:
        return None
    q_terms = recall_bundle.get("query_terms") or []
    matched = [str(t).lower() for t in (audit.get("matched_terms") or [])]

    sem_by_slug = ((recall_bundle.get("semantic") or {}).get("by_slug")) or {}

    def grounding(n: Dict[str, Any]) -> float:
        """Shared words PLUS closeness in meaning — both are real evidence."""
        hay = f"{n.get('title', '')} {' '.join(n.get('tags') or [])} {n.get('summary', '')}".lower()
        lexical = float(sum(1 for t in matched if t and t in hay))
        try:
            meaning = float(sem_by_slug.get(n.get("slug"), 0.0))
        except (TypeError, ValueError):
            meaning = 0.0
        return lexical + meaning

    best_idx = max(range(len(recalled)), key=lambda i: (grounding(recalled[i]), -i))
    ok = grade == "safe" or best_idx == 0
    answer_idx = 0 if ok else best_idx
    sem_sims: List[float] = []
    for n in recalled:
        try:
            sem_sims.append(float(sem_by_slug.get(n.get("slug"), 0.0)))
        except (TypeError, ValueError):
            sem_sims.append(0.0)
    prob = build_real_context_problem(field, query, recalled, q_terms, answer_idx, 0, sem_sims)
    if not prob:
        return None
    return {
        "ok": ok,
        "site": "wiki_recall",
        "note": (
            f"실제 채팅 「{query[:20]}」 — 환각 감사 {grade} (위험 {audit.get('risk_pct')}%) · "
            f"근육이 고른 1순위 기억이 "
            + ("실제로 근거가 됐어요" if ok else f"근거 최다 기억(#{best_idx + 1}번)이 아니었어요")
        ),
        "prob": prob,
        "metric": {
            "grade": grade,
            "risk_pct": audit.get("risk_pct"),
            "answer_index": answer_idx,
            "grounding_kind": audit.get("grounding_kind", "단어"),
            "semantic_pct": audit.get("semantic_pct"),
            "w_sem_trust": round(field_context_semantic_trust(field), 3),
        },
    }


def master_feedback_case(
    field: Dict[str, Any], query: str, recall_bundle: Dict[str, Any], answer_slug: str
) -> Optional[Dict[str, Any]]:
    """💡 Stage J: the master grades a recall the brain could not grade itself.

    A paraphrased question is only partly understood, so no automatic report
    card can say which memory really answered it — and a lesson built on a guess
    is how a brain learns to be confidently wrong.  The master's click is the
    honest oracle for exactly those cases.

    Clicking the note that was ranked #1 is a hit; clicking any other recalled
    note is a mistake WITH a known right answer, which is the most valuable
    lesson there is: the muscle learns it had the right memory and ranked it too
    low (and whether meaning or words led it astray).
    """
    recalled = recall_bundle.get("recalled") or []
    slugs = [str(n.get("slug")) for n in recalled]
    ans = str(answer_slug or "")
    if not recalled or ans not in slugs:
        return None
    answer_idx = slugs.index(ans)
    ok = answer_idx == 0
    q_terms = recall_bundle.get("query_terms") or []
    sem_info = recall_bundle.get("semantic") or {}
    sem_by_slug = sem_info.get("by_slug") or {}
    sem_sims: List[float] = []
    for n in recalled:
        try:
            sem_sims.append(float(sem_by_slug.get(str(n.get("slug")), 0.0)))
        except (TypeError, ValueError):
            sem_sims.append(0.0)
    prob = build_real_context_problem(field, query, recalled, q_terms, answer_idx, 0, sem_sims)
    if not prob:
        return None
    cov = (sem_info.get("query_coverage") or {}).get("pct")
    kind = "의미" if not (recall_bundle.get("matched_terms") or []) else "단어"
    return {
        "ok": ok,
        "site": "master_feedback",
        "key": f"feedback:{query[:28]}:{ans[:16]}",
        "note": (
            f"주인님 직접 채점 「{query[:18]}」 — "
            + (f"1순위 기억이 정답이었어요 (이해 {cov}%)" if ok
               else f"정답은 #{answer_idx + 1}번 기억이었는데 근육은 다른 걸 1순위로 올렸어요 (이해 {cov}%)")
        ),
        "prob": prob,
        "metric": {
            "grade": "master",
            "answer_index": answer_idx,
            "grounding_kind": kind,
            "coverage_pct": cov,
            "semantic_pct": sem_info.get("grounded_pct"),
            "w_sem_trust": round(field_context_semantic_trust(field), 3),
        },
    }


def build_real_context_problem(
    field: Dict[str, Any],
    query: str,
    notes: List[Dict[str, Any]],
    query_terms: List[str],
    answer_index: int,
    chosen_index: int,
    sem_sims: Optional[List[float]] = None,
) -> Optional[Dict[str, Any]]:
    """Turn one REAL chat recall into a re-studyable context problem.

    The six features are frozen at capture time, so re-studying never depends on
    the vault still holding those notes.
    """
    if not notes or answer_index < 0 or answer_index >= len(notes):
        return None
    feats = field_context_features(field, notes, query_terms)
    pad = len(feats[0])
    for f in feats:
        while len(f) < pad:
            f.append(0.0)
    sentences = [str(n.get("summary") or n.get("title") or "") for n in notes]
    return {
        "question": query,
        "sentences": sentences,
        "answer_sentence": sentences[answer_index],
        "features": feats,
        "distractors": max(0, len(notes) - 1),
        "alias_mode": False,
        "real_mode": True,
        "chosen_sentence": sentences[chosen_index] if 0 <= chosen_index < len(sentences) else "",
        "sem_sims": [float(x) for x in (sem_sims or [])][: len(sentences)],
    }


def field_org_threshold(field: Dict[str, Any]) -> float:
    """The shelf threshold the organizing muscle learned in the gym."""
    return float((field.get("weights") or {}).get("thr", 0.55))


def field_org_sub(category: str, tokens: List[str]) -> str:
    """Guess a real note's sub-topic using the LEARNED `_SUB_TOKENS` lexicon."""
    best, best_hit = category, 0
    low = {str(t).lower() for t in tokens}
    for (cat, sub), toks in _SUB_TOKENS.items():
        if cat != category:
            continue
        hit = len(low & {str(t).lower() for t in toks})
        if hit > best_hit:
            best, best_hit = sub, hit
    return best


def _real_cat_alias(category: str, title: str) -> str:
    """Pick the part of a compound category that ACTUALLY appears in the title.

    The gym's evidence test is `cat in title`, and real categories are compound
    ("Ghidra·역공학").  Without this alias the test is always false on real
    notes, so the w_cat weight the muscle learned would be silently dead.
    """
    for part in re.split(r"[·/,|\s]+", str(category)):
        part = part.strip()
        if len(part) >= 2 and part in title:
            return part
    return str(category)


def _real_doc_kind(title: str) -> str:
    """The document kind = the head of the title before the first em dash.

    Real vault titles look like "역공학 해부 도감 — 🎚️ 데드존 양자화기", so the
    head is a genuine sub-topic the muscle can learn to group by.
    """
    head = re.split(r"[—–]", str(title))[0].strip()
    return head[:28] if head else ""


def real_org_note_view(title: str, category: str, tokens: List[str]) -> Dict[str, Any]:
    """Translate ONE real note into the gym's note shape.

    Single source of truth on purpose: the experience lesson and the muscle's
    real act (gardener weaving) must see the SAME translation, otherwise what
    it learns in revision never transfers to what it does in the field.
    """
    toks = sorted({str(t).lower() for t in tokens if t})[:8]
    cat = str(category)
    return {
        "title": str(title),
        "cat": _real_cat_alias(cat, str(title)),
        "sub": _real_doc_kind(str(title)) or field_org_sub(cat, toks),
        "tokens": toks,
    }


def build_real_org_problem(
    notes: List[Dict[str, Any]], sem: Optional[Any] = None
) -> Optional[Dict[str, Any]]:
    """Turn the REAL wiki vault into a clustering problem the gym can solve.

    `notes`: [{"title","category","tags","keywords"}].  Ground truth is each
    note's own inferred category plus its document kind, so the muscle must
    group real memories from title/tag evidence alone — no hidden fields.
    """
    usable = [n for n in notes if n.get("title") and n.get("category")]
    if len(usable) < 6:
        return None
    cats = sorted({str(n["category"]) for n in usable})
    if len(cats) < 2:
        return None
    cat_idx = {c: i for i, c in enumerate(cats)}
    kept = usable[:24]
    org_notes: List[Dict[str, Any]] = []
    truth: List[Tuple[int, str]] = []
    for n in kept:
        cat = str(n["category"])
        view = real_org_note_view(
            n["title"], cat, list(n.get("tags") or []) + list(n.get("keywords") or [])
        )
        org_notes.append(view)
        truth.append((cat_idx[cat], view["sub"]))
    prob: Dict[str, Any] = {"notes": org_notes, "truth": truth, "real_mode": True, "categories": cats}
    # The vault's OWN links, as index pairs — the second opinion described in
    # `_org_same_truth`.  Stored as strings so a JSON round trip through the
    # experience ledger cannot turn them into unhashable lists.
    title_idx: Dict[str, int] = {}
    for i, n in enumerate(kept):
        title_idx.setdefault(str(n.get("title")), i)
    linked: set = set()
    for i, n in enumerate(kept):
        for lk in n.get("links") or []:
            j = title_idx.get(str(lk))
            if j is not None and j != i:
                linked.add(f"{min(i, j)}-{max(i, j)}")
    if linked:
        prob["linked_pairs"] = sorted(linked)
    # Tags the notes declare themselves — the third and (measured) most precise
    # source of "these two belong together".
    tagsets = [{str(t).lower() for t in (n.get("tags") or []) if t} for n in kept]
    tagged: set = set()
    for i in range(len(kept)):
        for j in range(i + 1, len(kept)):
            if tagsets[i] and tagsets[j] and (tagsets[i] & tagsets[j]):
                tagged.add(f"{i}-{j}")
    if tagged:
        prob["shared_tag_pairs"] = sorted(tagged)
    if sem is not None:
        # Freeze the meaning of every pair NOW, in the same order `_org_clusters`
        # walks them, so the lesson and the field always see one reality.
        try:
            prob["sem_pairs"] = [
                round(float(sem.pair_similarity(kept[i], kept[j])), 4)
                for i in range(len(kept))
                for j in range(i + 1, len(kept))
            ]
        except Exception:
            prob.pop("sem_pairs", None)
    return prob


def field_org_pair_sim(
    field: Dict[str, Any], ni: Dict[str, Any], nj: Dict[str, Any], sem: Optional[float] = None
) -> float:
    """Reuse the gym's own `_org_sim` on two REAL notes (same math, no fake path).

    💡 Stage K: `sem` is the pair's frozen meaning cosine.  The weaver passes it,
    the lesson stores it, and the muscle's learned `w_sem` decides how much it
    counts — one formula on both sides, so what it learns transfers.
    """
    return _org_sim(ni, nj, field.get("weights") or {}, int(field.get("tier", 0)), real=True, sem=sem)


def field_org_semantic_trust(field: Optional[Dict[str, Any]]) -> float:
    """How much the ORGANIZING muscle currently trusts meaning (learned, not set)."""
    w = (field or {}).get("weights") or {}
    try:
        return float(w.get("w_sem", ORG_SEM_PRIOR))
    except (TypeError, ValueError):
        return ORG_SEM_PRIOR


def grade_real_org_problem(field: Dict[str, Any], prob: Dict[str, Any]) -> Dict[str, Any]:
    """Solve a REAL vault clustering problem with the muscle's current weights.

    Returns an honest over-merge / under-merge count so the experience ledger
    records WHY the decision was wrong, not just that it was.
    """
    w = field.get("weights") or {}
    tier = int(field.get("tier", 0))
    ok, _ = _solve_organizing(prob, w, tier)
    parent, _ = _org_clusters(prob, w, tier)

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    notes = prob["notes"]
    n_over = n_under = 0
    for i in range(len(notes)):
        for j in range(i + 1, len(notes)):
            same_truth = _org_same_truth(prob, i, j)
            same_cl = find(i) == find(j)
            if same_cl and not same_truth:
                n_over += 1
            elif same_truth and not same_cl:
                n_under += 1
    clusters = len({find(i) for i in range(len(notes))})
    total_pairs = len(notes) * (len(notes) - 1) // 2
    # `ok` stays strict (a perfect partition) because that strictness is what
    # drives learning, but a 190-pair vault hides real progress behind it — so
    # report the continuous quality too.
    quality = round(100.0 * (1.0 - (n_over + n_under) / total_pairs), 1) if total_pairs else 100.0
    # 💡 Stage K: how many of those misses NO valve setting could reach — the
    # vault simply has not written the evidence yet.  Reporting it keeps the
    # muscle from being blamed (and from wrecking its own weights) over gaps that
    # only new memories can fill.
    unreachable = 0
    if prob.get("real_mode"):
        sems = prob.get("sem_pairs") or []
        w_sem = float(w.get("w_sem", ORG_SEM_PRIOR))
        thr_v = float(w.get("thr", 0.55))
        k = 0
        for i in range(len(notes)):
            for j in range(i + 1, len(notes)):
                cs = None
                if sems and k < len(sems):
                    try:
                        cs = float(sems[k])
                    except (TypeError, ValueError):
                        cs = None
                k += 1
                if find(i) == find(j) or not _org_same_truth(prob, i, j):
                    continue
                base = _org_sim(notes[i], notes[j], w, tier, real=True)
                best = base + (ORG_SEM_MAX * cs if cs is not None else 0.0)
                if best <= thr_v and base < thr_v - ORG_REACH_BAND:
                    unreachable += 1
    # ⚠️ The reachable score must also REMOVE the unreachable misses from the
    # numerator — dividing all misses by a shrunken denominator reported 30%
    # where the muscle was actually right on 38 of 40 reachable pairs.
    reach_total = max(1, total_pairs - unreachable)
    reach_err = max(0, n_over + n_under - unreachable)
    return {
        "ok": ok,
        "over": n_over,
        "under": n_under,
        "clusters": clusters,
        "total_pairs": total_pairs,
        "quality_pct": quality,
        "unreachable": unreachable,
        "reachable_quality_pct": round(100.0 * (1.0 - reach_err / reach_total), 1),
    }


def field_coding_suspects(field: Dict[str, Any], code: str) -> Dict[str, Any]:
    """Run the coding muscle's LEARNED fingerprint matrix over real workshop code."""
    f = _code_features({"snippet": code or ""}, int(field.get("tier", 0)))
    matrix = (field.get("weights") or {}).get("matrix") or [[0.0] * 4 for _ in range(4)]
    scores = [sum(float(row[i]) * f[i] for i in range(4)) for row in matrix]
    order = sorted(range(4), key=lambda k: -scores[k])
    n_lit = sum(1 for v in f if v > 0.5)
    top = order[:2] if (int(field.get("tier", 0)) >= 1 and n_lit >= 2) else order[:1]
    denom = sum(abs(x) for x in scores)
    # HONESTY GATE: an all-zero matrix has learned nothing, so it must NOT be
    # allowed to claim a lucky argmax hit.  Report "untrained" instead.
    if denom < 1e-9:
        return {
            "features": f,
            "lit_fingerprints": n_lit,
            "untrained": True,
            "predicted": [],
            "suspects": [],
        }
    return {
        "features": f,
        "lit_fingerprints": n_lit,
        "untrained": False,
        "predicted": [_BUG_CLASSES[k] for k in top],
        "suspects": [
            {
                "cls": _BUG_CLASSES[k],
                "score": round(scores[k], 4),
                "confidence": round(abs(scores[k]) / denom, 3),
            }
            for k in order
        ],
    }


def field_coding_classes_of(text: str) -> List[str]:
    """Map a real diagnosis sentence onto gym bug classes (to score the muscle)."""
    return [c for c, rx in _BUG_CLASS_TEXT_RE.items() if rx.search(text or "")]


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
            return {
                "w_subj": 0.5,
                "w_verb": 0.5,
                "w_neg": 0.6,
                "w_assert": -0.3,
                "w_owner": 0.0,
                "w_link": 0.0,
                # 💡 Stage J: a newborn trust in MEANING, not a learned one —
                # only real chats (which freeze sem_sims into a lesson) move it.
                "w_sem": CONTEXT_SEM_PRIOR,
            }
        if ability == "coding":
            return {"matrix": [[0.0] * 4 for _ in range(4)], "multi": 0.0}
        return {
            "w_title": 0.8,
            "w_tag": 0.3,
            "w_cat": -0.2,
            "thr": 0.55,
            "w_sub": 0.0,
            "w_agree": 0.0,
            # 💡 Stage K: newborn trust in meaning — moved only by real weaving.
            "w_sem": ORG_SEM_PRIOR,
        }

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

        # 📓 Stage I: part of every session re-studies the brain's OWN real
        # field records — mistakes first, because they are why the ledger exists.
        pool_size = len(self.state.get("experiences", {}).get(ability) or [])
        want = max(1, rounds // 3)
        if pool_size:
            # Real field lessons come first; invented puzzles only fill what is
            # left.  More distinct lessons -> more of the session is real.
            want = max(want, min(rounds - 1, pool_size * 3))
        exp_probs = self.experience_curriculum(ability, rng, want=want)
        exp_used = 0
        exp_correct = 0
        correct = 0
        example_q = ""
        for i in range(rounds):
            d = difficulty + 1 if (ability == "reasoning" and i % 2 == 1) else difficulty
            if i < len(exp_probs):
                prob = exp_probs[i]
                exp_used += 1
            else:
                prob = _GENERATORS[ability](rng, d, knob)
            ok, chosen = _SOLVERS[ability](prob, ab["weights"], tier)
            if ok:
                correct += 1
                if exp_used and i < exp_used:
                    exp_correct += 1
            # ALWAYS let the updater see the outcome.  Every updater owns an
            # `if ok:` reinforcement branch (reasoning: reward-weighted evidence,
            # coding: 0.2x truth-row strengthening, organizing: drawer tightening,
            # context: no-op) — skipping it on success froze an all-zero coding
            # matrix forever, so the muscle could claim a lucky argmax hit with
            # zero learned evidence.  Correct answers must build evidence too.
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
            "experience_rounds": exp_used,
            "level_before": level_before,
            "level_after": int(ab["level"]),
            "tier": tier,
        }
        ab["sessions"] = (ab.get("sessions") or [])[-19:] + [session]
        if exp_used:
            st = self.state.setdefault("field_stats", {}).setdefault(
                ability, {"attempts": 0, "hits": 0, "quality_sum": 0.0, "quality_n": 0, "taught": 0}
            )
            st["taught"] = int(st.get("taught", 0)) + exp_used
            for e in self.state.get("experiences", {}).get(ability) or []:
                if e.get("prob") in exp_probs[:exp_used]:
                    e["taught"] = int(e.get("taught", 0)) + 1
        session["experience_rounds"] = exp_used
        session["experience_correct"] = exp_correct
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
            "experience_rounds": exp_used,
            "experience_correct": exp_correct,
            "experience_available": len(self.state.get("experiences", {}).get(ability) or []),
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
        saved_weights = json.loads(json.dumps(ab["weights"]))
        ab["tier"] = next_tier
        train_correct, rounds = 0, 5
        for _ in range(rounds):
            prob = _GENERATORS[ability](rng, difficulty, next_knob)
            ok, chosen = _SOLVERS[ability](prob, ab["weights"], next_tier)
            train_correct += 1 if ok else 0
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
            # ...and roll the WEIGHTS back too: a rejected experiment must not
            # smuggle its side-effects into the brain (209 rejects once piled up
            # w_sub = 156.75, a residue no exam ever approved).
            ab["weights"] = saved_weights
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
                    "field_metrics": self.field_metrics(a),
                }
            )
        return {
            "abilities": out,
            "max_level": max(_tier_cap(a, len(TIERS[a]) - 1) for a in ABILITY_ORDER),
            "field": self.field_report(),
            "experience": self.experience_report(),
        }

    # ------------------------------------------------------------------
    # Stage H — Field Command ⚔️ : hand a muscle to a real organ & keep the report
    # ------------------------------------------------------------------
    def field_profile(self, ability: str) -> Dict[str, Any]:
        """Live level + tier + LEARNED weights of one muscle, for real organs."""
        ab = self.state["abilities"].get(ability) or self._default_ability(ability)
        site = FIELD_SITES[ability]
        tier = int(ab.get("tier", 0))
        return {
            "ability": ability,
            "title": ABILITY_META[ability]["title"],
            "site": site["site"],
            "site_title": site["title"],
            "verb": site["verb"],
            "level": int(ab.get("level", 1)),
            "tier": tier,
            "cap": _tier_cap(ability, tier),
            "weights": json.loads(json.dumps(ab.get("weights") or self._default_weights(ability))),
        }

    def log_deployment(self, ability: str, effect: str, metric: Dict[str, Any]) -> Dict[str, Any]:
        """Record one real-world sortie of a muscle (the ⚔️ field report ledger)."""
        prof = self.field_profile(ability)
        rec = {
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "ability": ability,
            "muscle_title": prof["title"],
            "site": prof["site"],
            "site_title": prof["site_title"],
            "verb": prof["verb"],
            "level": prof["level"],
            "tier": prof["tier"],
            "effect": effect,
            "metric": metric,
        }
        deps = self.state.setdefault("deployments", [])
        deps.append(rec)
        self.state["deployments"] = deps[-40:]
        counts = self.state.setdefault("field_counts", {})
        counts[ability] = int(counts.get(ability, 0)) + 1
        self._save()
        return rec

    # ------------------------------------------------------------------
    # Stage I — EXPERIENCE LEDGER 📓 (the brain studies its OWN real mistakes)
    # ------------------------------------------------------------------
    # A muscle that only ever solves problems I invented is a puzzle solver,
    # not an ability.  Every real organ already produces a genuine verdict:
    #   💻 coding    — audit `top1_hit` (predicted class vs the classes the
    #                   static diagnosis actually reported)
    #   📖 context   — `audit_chat_grounding` grade (safe / caution / high risk)
    #   🗂️ organizing — the wiki graph after weaving (orphan notes, edge count)
    #   🧠 reasoning  — debate `gain_pts` (did the judges' score rise or regress?)
    # Each verdict is stored here as a REAL problem, and `train_session` now
    # spends part of every session re-studying those problems — mistakes first.

    def record_experience(self, ability: str, case: Dict[str, Any]) -> Dict[str, Any]:
        """Store one real-world outcome as tomorrow's teaching material."""
        if ability not in ABILITY_ORDER or not case.get("prob"):
            return {}
        rec = {
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "ok": bool(case.get("ok")),
            "site": str(case.get("site") or FIELD_SITES[ability]["site"]),
            "note": str(case.get("note") or ""),
            "prob": case["prob"],
            "metric": case.get("metric") or {},
            "key": str(case.get("key") or ""),
        }
        stats = self.state.setdefault("field_stats", {}).setdefault(
            ability, {"attempts": 0, "hits": 0, "quality_sum": 0.0, "quality_n": 0, "taught": 0}
        )
        stats["attempts"] = int(stats["attempts"]) + 1
        if rec["ok"]:
            stats["hits"] = int(stats["hits"]) + 1
        q = (case.get("metric") or {}).get("quality_pct")
        if q is not None:
            stats["quality_sum"] = float(stats["quality_sum"]) + float(q)
            stats["quality_n"] = int(stats["quality_n"]) + 1
        # 🕳️ Stage K: also accumulate the score over pairs the muscle COULD
        # reach.  On a real vault most misses are gaps in what has been written
        # yet, and grading those as failures hides every real improvement.
        rq = (case.get("metric") or {}).get("reachable_quality_pct")
        if rq is not None:
            stats["reach_sum"] = float(stats.get("reach_sum", 0.0)) + float(rq)
            stats["reach_n"] = int(stats.get("reach_n", 0)) + 1

        log = self.state.setdefault("experience_log", [])
        log.append(
            {
                "ts": rec["ts"],
                "ability": ability,
                "title": ABILITY_META[ability]["title"],
                "ok": bool(rec["ok"]),
                "site": str(rec.get("site", "")),
                "note": str(rec.get("note", "")),
                "key": str(rec.get("key", "")),
                "kind": str((case.get("metric") or {}).get("grounding_kind") or ""),
                "superseded": False,
            }
        )
        del log[:-24]

        exps = self.state.setdefault("experiences", {}).setdefault(ability, [])
        # A living vault keeps changing, so an old snapshot of the SAME situation
        # is a stale textbook: one key = one lesson, always the latest verdict.
        # (Without this, the organizing muscle re-studied contradictory vault
        # snapshots and its shelf threshold oscillated instead of settling.)
        if rec["key"]:
            exps = [e for e in exps if e.get("key") != rec["key"]]
        exps.append(rec)
        # Mistakes are the reason this ledger exists, so they outlive successes.
        mistakes = [e for e in exps if not e["ok"]][-40:]
        successes = [e for e in exps if e["ok"]][-20:]
        self.state["experiences"][ability] = mistakes + successes
        self._save()
        return rec

    def experience_curriculum(self, ability: str, rng: random.Random, want: int) -> List[Dict[str, Any]]:
        """Build training problems out of the brain's own real field records."""
        exps = self.state.get("experiences", {}).get(ability) or []
        usable = [e for e in exps if e.get("prob")]
        if not usable or want <= 0:
            return []
        mistakes = [e for e in usable if not e["ok"]]
        successes = [e for e in usable if e["ok"]]
        rng.shuffle(mistakes)
        rng.shuffle(successes)
        n_miss = min(len(mistakes), max(1, (want * 2) // 3))
        picked = mistakes[:n_miss] + successes[: max(0, want - n_miss)]
        if not picked:
            return []
        out_probs: List[Dict[str, Any]] = []
        i = 0
        while len(out_probs) < want:
            # Repeating a real lesson is how a skill settles; being dragged
            # between one real lesson and four invented ones is what made the
            # organizing muscle's threshold oscillate.
            out_probs.append(picked[i % len(picked)]["prob"])
            i += 1
        return out_probs

    def field_metrics(self, ability: str) -> Dict[str, Any]:
        """The honest ability indicator: how the muscle does in REAL work.

        Reads the cumulative counters, because the ledger itself only keeps the
        latest lesson per situation (a living vault must not be re-studied from
        a stale snapshot).
        """
        st = (self.state.get("field_stats") or {}).get(ability) or {}
        attempts = int(st.get("attempts", 0))
        hits = int(st.get("hits", 0))
        mistakes = attempts - hits
        rate = round(100.0 * hits / attempts, 1) if attempts else None
        taught = int(st.get("taught", 0))
        ledger = self.state.get("experiences", {}).get(ability) or []
        if not attempts:
            verdict = "📓 경험 0건 — 아직 실전 채점지가 없어요 (실제로 일을 시켜주세요!)"
        elif rate is not None and rate >= 80:
            verdict = f"🎯 실전 적중률 {rate}% ({hits}/{attempts}) — 오답 노트 {len([e for e in ledger if not e['ok']])}장을 교재로 쓰는 중!"
        elif rate is not None and rate >= 50:
            verdict = f"🌱 실전 적중률 {rate}% ({hits}/{attempts}) — 오답 노트를 복습하며 자라는 중!"
        else:
            verdict = f"🧗 실전 적중률 {rate}% ({hits}/{attempts}) — 오답 노트가 두껍지만, 그게 바로 교재예요!"
        out = {
            "ability": ability,
            "title": ABILITY_META[ability]["title"],
            "real_attempts": attempts,
            "real_hits": hits,
            "real_mistakes": mistakes,
            "real_hit_rate_pct": rate,
            "experience_rounds_taught": taught,
            "lessons_held": len(ledger),
            "mistakes_held": len([e for e in ledger if not e["ok"]]),
            "verdict": verdict,
        }
        if ability == "context":
            # 💡 Stage J: the context muscle's own trust in meaning is part of its
            # report card — it is learned from real recalls, never hardcoded.
            out["sem_trust"] = round(field_context_semantic_trust(self.field_profile(ability)), 3)
        elif ability == "organizing":
            # 💡 Stage K: same honesty for the weaver.
            out["sem_trust"] = round(field_org_semantic_trust(self.field_profile(ability)), 3)
        qn = int(st.get("quality_n", 0))
        if qn:
            out["real_quality_pct"] = round(float(st.get("quality_sum", 0.0)) / qn, 1)
            out["verdict"] += f" · 🧹 실제 정리 품질 {out['real_quality_pct']}%"
        rn = int(st.get("reach_n", 0))
        if rn:
            out["real_reachable_quality_pct"] = round(float(st.get("reach_sum", 0.0)) / rn, 1)
            out["verdict"] += f" · 🎯 조절 가능 {out['real_reachable_quality_pct']}%"
        return out

    def experience_report(self) -> Dict[str, Any]:
        per = [self.field_metrics(a) for a in ABILITY_ORDER]
        taught_by_key: Dict[str, int] = {}
        for a in ABILITY_ORDER:
            for e in self.state.get("experiences", {}).get(a) or []:
                taught_by_key[f"{a}|{e.get('key', '')}"] = int(e.get("taught", 0))
        recent: List[Dict[str, Any]] = []
        for entry in reversed(list(self.state.get("experience_log") or [])):
            row = dict(entry)
            row["taught"] = taught_by_key.get(f"{entry['ability']}|{entry['key']}", 0)
            recent.append(row)
        return {
            "total_experiences": sum(m["real_attempts"] for m in per),
            "total_mistakes": sum(m["real_mistakes"] for m in per),
            "lessons_held": sum(m["lessons_held"] for m in per),
            "mistakes_held": sum(m["mistakes_held"] for m in per),
            "per_muscle": per,
            "recent": recent[:14],
        }

    def field_report(self) -> Dict[str, Any]:
        deps = list(self.state.get("deployments") or [])
        counts = self.state.get("field_counts") or {}
        per_muscle = []
        for a in ABILITY_ORDER:
            ab = self.state["abilities"].get(a) or self._default_ability(a)
            site = FIELD_SITES[a]
            tier = int(ab.get("tier", 0))
            per_muscle.append(
                {
                    "id": a,
                    "title": ABILITY_META[a]["title"],
                    "site_title": site["title"],
                    "verb": site["verb"],
                    "detail": site["detail"],
                    "level": int(ab.get("level", 1)),
                    "tier": tier,
                    "cap": _tier_cap(a, tier),
                    "deployments": int(counts.get(a, 0)),
                    "metrics": self.field_metrics(a),
                    "last_effect": next(
                        (d["effect"] for d in reversed(deps) if d["ability"] == a),
                        "아직 실전 투입 전 — 체육관에서 훈련 중이에요!",
                    ),
                }
            )
        return {
            "total_deployments": len(deps),
            "per_muscle": per_muscle,
            "recent": deps[-10:][::-1],
        }
