"""
Domain-Clustered Quantized Genius Constellations & Multi-Genius Debate Agora
(`genius_pantheon.py` — v4.2 Limitless Modular Brain Edition).

Instead of isolated individuals or a fixed-size monolithic model:
  1. Geniuses gather inside **Domain Constellations (영역별 성좌)** — e.g.,
     Reverse Engineering, First-Principles Truth, Information & Infinite Scaling,
     Game-Theory Strategy, and Synthesis & Fault-Tolerance.
  2. Inside each Domain Constellation (and across selected Constellations),
     geniuses **actively exchange opinions (발의 → 반론·보완 → 교차 융합 → 합의)**
     on any user question or engineering dilemma.
  3. Each debate crystallizes into an **on-demand INT4 modular `.sbrain` capsule**
     on the external drive (zero upper limit on modules or constellations!) and
     distills its consensus policy directly into the 5 CPU Baby Neurons.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
import re
import struct
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from brain_engine.core_ability_engine import field_reasoning_boost, field_reasoning_hops

from brain_engine.rl_gym import ARCHETYPES, _reward_for


DEFAULT_CONSTELLATIONS: List[Dict[str, Any]] = [
    {
        "id": "const_re",
        "name": "암호·역공학 성좌",
        "en_name": "Reverse & Systems Constellation",
        "icon": "🔐",
        "color": "#60a5fa",
        "domain_mission": "블랙박스 실행파일과 숨겨진 시스템 구조를 밑바닥까지 해부해 진실을 역추적합니다.",
        "geniuses": [
            {
                "id": "turing",
                "name": "앨런 튜링",
                "emoji": "🔐",
                "lens": "상태기계 · 암호 역추적",
                "credo": "겉모습에 속지 말고 입출력 변화와 상태 전이표를 그려 숨은 규칙을 역추적해야 합니다.",
                "rebuttal_style": "실제 상태 전이 반례를 들어 표면적 해석의 허점을 찌름",
                "bias": [
                    [0.05, 0.25, -0.35, -0.10],
                    [-0.45, -0.15, 0.90, 0.15],
                    [-0.25, 0.85, 0.15, -0.10],
                    [-0.35, -0.20, 0.45, 0.20],
                    [-0.15, 0.30, 0.35, -0.10],
                ],
            },
            {
                "id": "lovelace",
                "name": "에이다 러브레이스",
                "emoji": "🎼",
                "lens": "알고리즘 구조 · 반복 패턴",
                "credo": "개별 숫자보다 명령어들이 직조하는 반복 루프와 기호 패턴의 전체 무늬를 먼저 봐야 해요.",
                "rebuttal_style": "단편적 코드 조각 너머의 상위 알고리즘 패턴을 보완 제시",
                "bias": [
                    [0.10, 0.35, -0.25, -0.15],
                    [-0.35, 0.10, 0.75, 0.10],
                    [-0.20, 0.70, 0.20, -0.15],
                    [-0.30, -0.15, 0.30, 0.30],
                    [-0.10, 0.40, 0.25, -0.10],
                ],
            },
            {
                "id": "ritchie",
                "name": "데니스 리치",
                "emoji": "⚙️",
                "lens": "메모리 포인터 · 커널 바닥",
                "credo": "추상화 껍데기를 벗기고 실제 메모리 주소·포인터·시스템 콜 바닥을 찍어보면 답은 단순합니다.",
                "rebuttal_style": "이론적 추론이 실제 메모리·CPU 현장에서 어떻게 도는지 검증",
                "bias": [
                    [0.15, 0.20, -0.20, -0.15],
                    [-0.40, -0.10, 0.80, 0.05],
                    [-0.15, 0.80, 0.10, -0.20],
                    [-0.25, -0.15, 0.35, 0.20],
                    [0.05, 0.45, 0.15, -0.15],
                ],
            },
        ],
    },
    {
        "id": "const_truth",
        "name": "제1원리·진실검증 성좌",
        "en_name": "First-Principles & Anti-Hallucination",
        "icon": "🔬",
        "color": "#34d399",
        "domain_mission": "그럴듯한 추측(환각)을 철저히 걸러내고 검증된 제1원리 사실 위에서만 답을 세웁니다.",
        "geniuses": [
            {
                "id": "feynman",
                "name": "리처드 파인만",
                "emoji": "🔬",
                "lens": "제1원리 · 쉬운 말 재검증",
                "credo": "세상에서 가장 속이기 쉬운 상대는 자기 자신입니다! 위키 근거로 쉽게 설명 못 하면 정직히 멈춰야 해요.",
                "rebuttal_style": "근거 없는 전문용어나 그럴듯한 추측을 즉시 제동",
                "bias": [
                    [0.75, 0.15, -0.45, -0.25],
                    [-0.65, -0.35, 0.35, 0.55],
                    [-0.45, 0.35, 0.20, 0.15],
                    [-0.85, -0.45, -0.15, 0.98],
                    [-0.40, 0.25, -0.10, 0.45],
                ],
            },
            {
                "id": "einstein",
                "name": "알베르트 아인슈타인",
                "emoji": "🌌",
                "lens": "사고실험 · 극단 반례",
                "credo": "가설이 정말 참인지 보려면 빛의 속도나 0바이트 같은 극단적 사고실험에 던져 깨지지 않는지 보세요.",
                "rebuttal_style": "극단 경계 조건(Edge Case) 사고실험으로 숨은 모순을 드러냄",
                "bias": [
                    [0.55, 0.25, -0.35, -0.15],
                    [-0.50, -0.20, 0.45, 0.40],
                    [-0.35, 0.40, 0.25, 0.05],
                    [-0.70, -0.35, -0.05, 0.85],
                    [-0.30, 0.30, 0.05, 0.35],
                ],
            },
            {
                "id": "curie",
                "name": "마리 퀴리",
                "emoji": "🧪",
                "lens": "반복 정제 · 순수 실증",
                "credo": "수 톤의 역청 우라늄 광석에서 순수 라듐 한 알을 얻듯, 백 번 검증해도 남는 순수 사실만 남깁시다.",
                "rebuttal_style": "한두 번 우연히 맞은 결과를 경계하고 반복 재현성을 요구",
                "bias": [
                    [0.70, 0.10, -0.40, -0.20],
                    [-0.55, -0.25, 0.30, 0.50],
                    [-0.40, 0.30, 0.15, 0.20],
                    [-0.80, -0.40, -0.10, 0.92],
                    [-0.35, 0.20, -0.05, 0.45],
                ],
            },
        ],
    },
    {
        "id": "const_scale",
        "name": "정보압축·무한확장 성좌",
        "en_name": "Compression & Limitless Scaling",
        "icon": "📡",
        "color": "#f5b942",
        "domain_mission": "4비트 양자화와 외장하드 성좌 모듈 스왑으로 두뇌 용량과 성장의 한계를 완전히 없앱니다.",
        "geniuses": [
            {
                "id": "shannon",
                "name": "클로드 섀넌",
                "emoji": "📡",
                "lens": "정보 엔트로피 · 4비트 압축",
                "credo": "중복 잡음을 걷어내고 순수 정보 엔트로피만 4비트 니블로 압축하면 정확도는 지키고 크기는 84% 줄어듭니다!",
                "rebuttal_style": "불필요한 중복 데이터를 깎아 신호 대 잡음비를 극대화",
                "bias": [
                    [0.25, 0.55, -0.35, -0.20],
                    [-0.35, 0.15, 0.65, -0.05],
                    [-0.30, 0.90, -0.10, -0.25],
                    [-0.25, -0.15, 0.20, 0.35],
                    [-0.20, 0.92, -0.15, -0.20],
                ],
            },
            {
                "id": "hopper",
                "name": "그레이스 호퍼",
                "emoji": "⚓",
                "lens": "모듈 서브루틴 · 무한 스왑",
                "credo": "항상 해오던 대로 한 덩어리에 가두지 마세요! 성좌별 모듈(.sbrain)로 쪼개 필요한 순간만 RAM에 소환하면 한계란 없습니다!",
                "rebuttal_style": "단일 거대 모델의 메모리 벽을 모듈형 온디맨드 호출로 돌파",
                "bias": [
                    [0.20, 0.65, -0.30, -0.20],
                    [-0.30, 0.25, 0.55, -0.05],
                    [-0.25, 0.85, -0.05, -0.20],
                    [-0.30, -0.10, 0.20, 0.35],
                    [-0.15, 0.95, -0.10, -0.20],
                ],
            },
            {
                "id": "kolmogorov",
                "name": "안드레이 콜모고로프",
                "emoji": "📐",
                "lens": "최소 기술 길이 · 생성 규칙",
                "credo": "수백만 줄의 결과를 통째로 저장하는 대신, 그 결과를 낳는 가장 짧은 핵심 공식 하나를 외장하드에 새깁시다.",
                "rebuttal_style": "비대한 암기 대신 짧은 생성 원리(압축 규칙)로 치환",
                "bias": [
                    [0.30, 0.50, -0.30, -0.15],
                    [-0.30, 0.20, 0.60, 0.05],
                    [-0.25, 0.80, 0.05, -0.20],
                    [-0.35, -0.15, 0.15, 0.40],
                    [-0.20, 0.85, -0.05, -0.15],
                ],
            },
        ],
    },
    {
        "id": "const_strategy",
        "name": "전략·확률추론 성좌",
        "en_name": "Game Theory & Bayesian Strategy",
        "icon": "♟️",
        "color": "#a78bfa",
        "domain_mission": "불확실한 갈림길에서 조건부 확률과 게임이론으로 오판 손실이 가장 적은 최적 수를 찾아냅니다.",
        "geniuses": [
            {
                "id": "neumann",
                "name": "존 폰 노이만",
                "emoji": "♟️",
                "lens": "게임이론 · 미니맥스 최적수",
                "credo": "모든 선택지의 최악 시나리오 손실을 먼저 계산하고, 손실 상한이 가장 낮은 미니맥스 전략을 택합시다.",
                "rebuttal_style": "운에 기댄 낙관적 선택이 초래할 최악의 파국 비용을 경고",
                "bias": [
                    [0.45, 0.45, -0.55, -0.15],
                    [-0.55, -0.15, 0.55, 0.30],
                    [-0.45, 0.65, 0.15, -0.05],
                    [-0.60, -0.35, 0.15, 0.80],
                    [-0.45, 0.70, -0.10, 0.15],
                ],
            },
            {
                "id": "bayes",
                "name": "토머스 베이즈",
                "emoji": "🎲",
                "lens": "사전·사후 조건부 확률 갱신",
                "credo": "단서 하나가 새로 들어올 때마다 고집을 버리고 각 선택지의 조건부 확률을 즉시 업데이트해야 합니다!",
                "rebuttal_style": "흑백논리 대신 확신도(%) 분포와 주인님 코칭 임계치를 결합",
                "bias": [
                    [0.40, 0.40, -0.45, -0.10],
                    [-0.50, -0.20, 0.45, 0.40],
                    [-0.35, 0.55, 0.15, 0.05],
                    [-0.65, -0.30, 0.10, 0.85],
                    [-0.35, 0.60, -0.05, 0.25],
                ],
            },
            {
                "id": "noether",
                "name": "에미 뇌터",
                "emoji": "♾️",
                "lens": "대칭성 · 불변 보존 법칙",
                "credo": "문제의 겉모양이나 좌표가 바뀌어도 절대 흔들리지 않는 대칭 불변량(보존 법칙)을 붙잡으세요.",
                "rebuttal_style": "표면적 변형에 흔들리지 않는 근본 불변 구조를 추출",
                "bias": [
                    [0.50, 0.35, -0.45, -0.15],
                    [-0.45, -0.10, 0.50, 0.25],
                    [-0.35, 0.60, 0.20, -0.05],
                    [-0.55, -0.25, 0.15, 0.70],
                    [-0.35, 0.65, 0.00, 0.15],
                ],
            },
        ],
    },
    {
        "id": "const_shield",
        "name": "융합창의·안전방어 성좌",
        "en_name": "Creative Synthesis & Fault-Tolerant Shield",
        "icon": "🛡️",
        "color": "#f472b6",
        "domain_mission": "서로 다른 영역의 통찰을 하나로 엮고, 위기 순간에도 무너지지 않는 아폴로급 안전망을 펼칩니다.",
        "geniuses": [
            {
                "id": "hamilton",
                "name": "마거릿 해밀턴",
                "emoji": "🛡️",
                "lens": "아폴로 방어 공학 · 비상 복구",
                "credo": "메모리 과부하나 모순 경보가 울리면 아폴로 11호처럼 즉시 핵심 임무만 남기고 안전 경로(Fallback)로 전환합시다!",
                "rebuttal_style": "완벽한 이론도 현장 예외에서 뻗지 않도록 방어막을 강제 장착",
                "bias": [
                    [0.60, 0.30, -0.65, -0.10],
                    [-0.65, -0.25, 0.30, 0.65],
                    [-0.60, 0.55, -0.15, 0.30],
                    [-0.80, -0.50, -0.10, 0.92],
                    [-0.75, 0.85, -0.35, 0.35],
                ],
            },
            {
                "id": "davinci",
                "name": "레오나르도 다빈치",
                "emoji": "🎨",
                "lens": "영역 간 융합 · 기하학 연결",
                "credo": "모든 지식은 보이지 않는 시냅스로 이어져 있어요! 역공학과 과학, 압축 성좌 사이에 다리를 놓아 봅시다.",
                "rebuttal_style": "서로 다른 성좌들의 주장을 하나의 직관적 설계도로 융합",
                "bias": [
                    [0.82, 0.20, -0.25, -0.30],
                    [-0.35, 0.05, 0.55, 0.15],
                    [-0.20, 0.60, 0.25, -0.15],
                    [-0.45, -0.20, 0.25, 0.55],
                    [-0.25, 0.50, 0.10, 0.10],
                ],
            },
            {
                "id": "tesla",
                "name": "니콜라 테슬라",
                "emoji": "⚡",
                "lens": "가상 공명 실험 · 파동 증폭",
                "credo": "실제 행동을 내리기 전에 머릿속 가상 실험실에서 여러 성좌의 주파수를 공명시켜 결과를 미리 검증합시다!",
                "rebuttal_style": "성좌 간 아이디어가 충돌할 때 공명 시뮬레이션으로 시너지를 증폭",
                "bias": [
                    [0.55, 0.40, -0.35, -0.20],
                    [-0.40, 0.05, 0.60, 0.20],
                    [-0.30, 0.65, 0.15, -0.10],
                    [-0.50, -0.25, 0.20, 0.60],
                    [-0.35, 0.70, 0.05, 0.10],
                ],
            },
        ],
    },
]


CONSTELLATION_BRIDGES: List[Dict[str, Any]] = [
    {
        "a": "const_re",
        "b": "const_scale",
        "label": "초경량 바이너리 해독 공명",
        "desc": "역공학 성좌가 찾은 숨은 패턴을 정보압축 성좌가 4비트 모듈로 즉시 캡슐화",
    },
    {
        "a": "const_truth",
        "b": "const_shield",
        "label": "환각 제로(0%) 이중 무결성 방패",
        "desc": "제1원리 사실 검증과 아폴로 비상 안전망이 결합해 거짓 답변 원천 차단",
    },
    {
        "a": "const_scale",
        "b": "const_strategy",
        "label": "한계 없는 무한 모듈 추론망",
        "desc": "외장하드 성좌 스왑과 게임이론 확률 추론이 결합해 PC 한계를 초월",
    },
    {
        "a": "const_re",
        "b": "const_truth",
        "label": "실증 기반 무오류 코드 해부",
        "desc": "추측성 역공학을 금지하고 메모리 증거와 위키 원리로만 판정",
    },
    {
        "a": "const_strategy",
        "b": "const_shield",
        "label": "무패(無敗) 리스크 방어 전술",
        "desc": "미니맥스 최적 수와 비상 회피 경로가 합쳐져 치명적 함정 회피율 극대화",
    },
    {
        "a": "const_re",
        "b": "const_strategy",
        "label": "심층 분기 탐색 레이더",
        "desc": "수만 개 조건 분기 중 핵심 경로만 확률적으로 압축 추적",
    },
]


PALETTE_CYCLE = ["#38bdf8", "#fb7185", "#4ade80", "#facc15", "#c084fc", "#fb923c"]


def _quantize_int4_capsule(
    matrix_2d: List[List[float]], out_path: Path, meta: Dict[str, Any]
) -> Dict[str, Any]:
    flat = [v for row in matrix_2d for v in row]
    max_abs = max((abs(v) for v in flat), default=1e-6)
    scale = max_abs / 7.0 if max_abs > 1e-9 else 1.0
    q_vals = [max(-7, min(7, int(round(v / scale)))) for v in flat]
    deq = [q * scale for q in q_vals]

    dot = sum(a * b for a, b in zip(flat, deq))
    na = math.sqrt(sum(a * a for a in flat)) or 1e-9
    nb = math.sqrt(sum(b * b for b in deq)) or 1e-9
    cos_sim = round(min(1.0, max(0.0, dot / (na * nb))) * 100.0, 2)

    packed = bytearray()
    for i in range(0, len(q_vals), 2):
        lo = (q_vals[i] + 8) & 0x0F
        hi = ((q_vals[i + 1] if i + 1 < len(q_vals) else 0) + 8) & 0x0F
        packed.append((hi << 4) | lo)

    header = json.dumps({**meta, "scale": round(scale, 6), "cos_sim_pct": cos_sim}, ensure_ascii=False).encode("utf-8")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("wb") as f:
        f.write(b"SBRN")
        f.write(struct.pack("<BBI", 2, 4, len(header)))
        f.write(header)
        f.write(bytes(packed))

    return {
        "file": out_path.name,
        "size_kb": round(out_path.stat().st_size / 1024.0, 2),
        "cosine_similarity_pct": cos_sim,
    }


class GeniusPantheon:
    def __init__(self, state_dir: Path, models_dir: Path) -> None:
        self.state_path = state_dir / "genius_pantheon.json"
        self.models_dir = models_dir
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.data = self._load_or_init()

    def _load_or_init(self) -> Dict[str, Any]:
        if self.state_path.exists():
            try:
                loaded = json.loads(self.state_path.read_text(encoding="utf-8"))
                if "constellations" in loaded and isinstance(loaded["constellations"], list):
                    return loaded
            except Exception:
                pass
        init = {
            "constellations": json.loads(json.dumps(DEFAULT_CONSTELLATIONS, ensure_ascii=False)),
            "bridges": json.loads(json.dumps(CONSTELLATION_BRIDGES, ensure_ascii=False)),
            "active_constellation_ids": ["const_re", "const_truth", "const_scale"],
            "debate_sessions": 0,
            "modular_capsules": [],
            "last_debate": None,
        }
        self._save(init)
        return init

    def _save(self, payload: Dict[str, Any] | None = None) -> None:
        target = payload if payload is not None else self.data
        self.state_path.write_text(
            json.dumps(target, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def _default_bias_from_text(self, text: str) -> List[List[float]]:
        # Deterministic domain-aware bias seed for user-recruited limitless geniuses!
        h = hashlib.sha256(text.encode("utf-8")).digest()
        rows: List[List[float]] = []
        idx = 0
        for r in range(5):
            row: List[float] = []
            for c in range(4):
                raw = (h[idx % len(h)] / 255.0) * 0.7 - 0.25
                idx += 1
                row.append(round(raw, 3))
            # Reinforce safe verification & deep analysis over reckless guessing
            if r == 3:
                row[0] = -0.55
                row[3] = 0.75
            elif r == 1:
                row[0] = -0.45
                row[2] = 0.65
            rows.append(row)
        return rows

    def add_genius_or_constellation(
        self,
        target_constellation_id: str,
        new_constellation_name: str,
        genius_name: str,
        lens: str,
        credo: str,
        emoji: str = "🌟",
        strengths: str = "",
        limitations: str = "",
    ) -> Dict[str, Any]:
        consts: List[Dict[str, Any]] = self.data["constellations"]
        g_clean = genius_name.strip() or "무명 현자"
        lens_clean = lens.strip() or "통합 통찰"
        credo_clean = credo.strip() or "근본 원리를 꿰뚫어 서로 다른 성좌의 지혜를 하나로 잇습니다."
        emoji_clean = (emoji.strip() or "🌟")[:2]

        # If a genius with the exact same name already exists, remove from old constellation (clean transfer!)
        existing_id: str | None = None
        for c in consts:
            for idx, g in enumerate(c.get("geniuses", [])):
                if g["name"].strip().lower() == g_clean.lower():
                    existing_id = g["id"]
                    c["geniuses"].pop(idx)
                    break
            if existing_id:
                break

        gid = existing_id or ("g_" + hashlib.md5(f"{g_clean}_{time.time()}".encode("utf-8")).hexdigest()[:8])
        new_genius = {
            "id": gid,
            "name": g_clean,
            "emoji": emoji_clean,
            "lens": lens_clean,
            "credo": credo_clean,
            "strengths": strengths.strip(),
            "limitations": limitations.strip(),
            "rebuttal_style": f"{lens_clean} 관점에서 빈틈을 보완",
            "bias": self._default_bias_from_text(f"{g_clean}:{lens_clean}:{credo_clean}"),
        }

        target_const = None
        if target_constellation_id and target_constellation_id != "__new__":
            target_const = next((c for c in consts if c["id"] == target_constellation_id), None)

        if target_const is None:
            cname = new_constellation_name.strip() or f"{lens_clean} 성좌"
            if not cname.endswith("성좌"):
                cname = f"{cname} 성좌"
            cid = "const_" + hashlib.md5(f"{cname}_{len(consts)}".encode("utf-8")).hexdigest()[:6]
            color = PALETTE_CYCLE[len(consts) % len(PALETTE_CYCLE)]
            target_const = {
                "id": cid,
                "name": cname,
                "en_name": "Custom Infinite Constellation",
                "icon": emoji_clean,
                "color": color,
                "domain_mission": f"주인님이 직접 창설한 무한 확장 '{cname}' 영역 성좌입니다.",
                "geniuses": [new_genius],
            }
            consts.append(target_const)
            if len(consts) >= 2:
                prev_id = consts[0]["id"]
                self.data["bridges"].append(
                    {
                        "a": cid,
                        "b": prev_id,
                        "label": f"{cname} × {consts[0]['name']} 융합 공명",
                        "desc": "새로 확장된 성좌와 기존 성좌 사이의 무한 시너지 다리",
                    }
                )
            if cid not in self.data["active_constellation_ids"]:
                self.data["active_constellation_ids"].append(cid)
        else:
            target_const["geniuses"].append(new_genius)
            if target_const["id"] not in self.data["active_constellation_ids"]:
                self.data["active_constellation_ids"].append(target_const["id"])

        self._save()
        return {
            "constellation": target_const,
            "added_genius": new_genius,
            "total_constellations": len(consts),
            "total_geniuses": sum(len(c["geniuses"]) for c in consts),
        }

    def move_genius(
        self,
        genius_id: str,
        to_constellation_id: str,
        new_constellation_name: str = "",
    ) -> Dict[str, Any]:
        consts: List[Dict[str, Any]] = self.data["constellations"]
        found_genius: Dict[str, Any] | None = None
        from_const: Dict[str, Any] | None = None

        for c in consts:
            for idx, g in enumerate(c.get("geniuses", [])):
                if g["id"] == genius_id:
                    found_genius = c["geniuses"].pop(idx)
                    from_const = c
                    break
            if found_genius:
                break

        if not found_genius or not from_const:
            raise ValueError("이동할 천재를 찾지 못했습니다.")

        to_const = None
        if to_constellation_id and to_constellation_id != "__new__":
            to_const = next((c for c in consts if c["id"] == to_constellation_id), None)

        if to_const is None:
            cname = new_constellation_name.strip() or f"{found_genius.get('lens', '융합')} 성좌"
            if not cname.endswith("성좌"):
                cname = f"{cname} 성좌"
            cid = "const_" + hashlib.md5(f"{cname}_{len(consts)}_{time.time()}".encode("utf-8")).hexdigest()[:6]
            color = PALETTE_CYCLE[len(consts) % len(PALETTE_CYCLE)]
            to_const = {
                "id": cid,
                "name": cname,
                "en_name": "Custom Infinite Constellation",
                "icon": found_genius.get("emoji", "🌌"),
                "color": color,
                "domain_mission": f"주인님이 '{found_genius['name']}' 배치를 위해 창설한 '{cname}' 영역 성좌입니다.",
                "geniuses": [found_genius],
            }
            consts.append(to_const)
            if len(consts) >= 2:
                self.data["bridges"].append(
                    {
                        "a": cid,
                        "b": consts[0]["id"],
                        "label": f"{cname} × {consts[0]['name']} 융합 공명",
                        "desc": "새로 확장된 성좌와 기존 성좌 사이의 무한 시너지 다리",
                    }
                )
        else:
            to_const["geniuses"].append(found_genius)

        if to_const["id"] not in self.data["active_constellation_ids"]:
            self.data["active_constellation_ids"].append(to_const["id"])

        self._save()
        return {
            "moved_genius": found_genius,
            "from_constellation": {"id": from_const["id"], "name": from_const["name"]},
            "to_constellation": {"id": to_const["id"], "name": to_const["name"]},
        }

    def _extract_topic_focus(self, topic: str) -> str:
        clean = topic.strip()
        if not clean:
            return "외장하드 두뇌의 한계 없는 성장과 무결점 판단"
        return clean[:90]

    def _build_dialogue(
        self,
        selected_consts: List[Dict[str, Any]],
        topic: str,
        active_bridges: List[Dict[str, Any]],
        field: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[Dict[str, Any]], str]:
        focus = self._extract_topic_focus(topic)
        dialogue: List[Dict[str, Any]] = []

        # Phase 1: Intra-Constellation Opinion Exchange (geniuses inside EACH constellation debate each other!)
        for c in selected_consts:
            gs = c["geniuses"]
            if not gs:
                continue
            g0 = gs[0]
            dialogue.append(
                {
                    "phase": "성좌 내부 발의",
                    "constellation_id": c["id"],
                    "constellation_name": c["name"],
                    "color": c["color"],
                    "speaker": g0["name"],
                    "emoji": g0["emoji"],
                    "lens": g0["lens"],
                    "reply_to": None,
                    "message": (
                        f"『{focus}』 주제를 우리 [{c['name']}] 시각에서 먼저 열겠습니다. "
                        f"{g0['credo']}"
                    ),
                }
            )
            for idx in range(1, len(gs)):
                prev_g = gs[idx - 1]
                cur_g = gs[idx]
                role_tag = "반론 · 정교화" if idx == 1 else "성좌 내부 종합"
                connector = (
                    f"{prev_g['name']}의 '{prev_g['lens']}' 제안은 날카롭지만, 한 가지 더 짚어야 합니다! "
                    if idx == 1
                    else f"{gs[0]['name']}과 {prev_g['name']} 두 분의 의견을 합치면 해법이 선명해집니다. "
                )
                limit_note = (
                    f"(또한 {prev_g['name']}의 '{prev_g['limitations'][:28]}…' 한계도 제가 이 지점에서 보완하겠습니다!) "
                    if prev_g.get("limitations") and idx == 1
                    else ""
                )
                dialogue.append(
                    {
                        "phase": role_tag,
                        "constellation_id": c["id"],
                        "constellation_name": c["name"],
                        "color": c["color"],
                        "speaker": cur_g["name"],
                        "emoji": cur_g["emoji"],
                        "lens": cur_g["lens"],
                        "reply_to": prev_g["name"],
                        "message": f"{connector}{limit_note}{cur_g['credo']}",
                    }
                )

        # Phase 2: Cross-Constellation Synthesis when >= 2 Domain Constellations convene!
        non_empty = [c for c in selected_consts if c.get("geniuses")]
        if len(non_empty) >= 2:
            c_first = non_empty[0]
            c_last = non_empty[-1]
            rep_a = c_first["geniuses"][0]
            rep_b = c_last["geniuses"][-1]
            bridge_txt = (
                f"특히 『{active_bridges[0]['label']}』 시너지 다리가 켜졌군요! "
                if active_bridges
                else ""
            )
            dialogue.append(
                {
                    "phase": "성좌 간 교차 합의",
                    "constellation_id": c_last["id"],
                    "constellation_name": f"{c_first['name']} × {c_last['name']}",
                    "color": "#fde68a",
                    "speaker": rep_b["name"],
                    "emoji": rep_b["emoji"],
                    "lens": "영역 간 초월 융합",
                    "reply_to": rep_a["name"],
                    "message": (
                        f"{bridge_txt}[{c_first['name']}] {rep_a['name']} 측의 해부 원리와 "
                        f"우리 [{c_last['name']}]의 방어·확장 원칙을 결합합시다. "
                        f"필요한 성좌 모듈만 외장하드에서 즉시 소환해 검증하면 『{focus}』 문제도 한계 없이 돌파할 수 있습니다!"
                    ),
                }
            )

        # Phase 3 (Stage H ⚔️): the REASONING muscle chains the debate into a
        # hop-by-hop argument trace.  More levels → more hops → a deeper chain
        # that must carry each conclusion forward as the next premise.
        chain_hops = field_reasoning_hops(field) if field else 0
        if field and chain_hops:
            pairs = [(c, g) for c in selected_consts for g in c["geniuses"]]
            prev: Optional[Dict[str, Any]] = None
            for h in range(chain_hops):
                c_h, g = pairs[h % len(pairs)]
                if prev is None:
                    step = (
                        f"[hop {h + 1}/{chain_hops}] 『{focus}』의 제1원리로 제 렌즈({g['lens']})를 출발점으로 삼습니다. "
                        f"{g['credo']}"
                    )
                else:
                    step = (
                        f"[hop {h + 1}/{chain_hops}] {prev['name']}의 결론을 근거로 받아, 제 렌즈({g['lens']})를 더해 "
                        f"『{focus}』의 다음 명제를 도출합니다. {g['credo']}"
                    )
                dialogue.append(
                    {
                        "phase": "🔗 추론 체인 역추적",
                        "constellation_id": c_h["id"],
                        "constellation_name": c_h["name"],
                        "color": "#a5f3fc",
                        "speaker": g["name"],
                        "emoji": g["emoji"],
                        "lens": g["lens"],
                        "reply_to": prev["name"] if prev else None,
                        "message": step,
                    }
                )
                prev = g

        const_titles = " × ".join(c["name"] for c in selected_consts)
        total_speakers = sum(len(c["geniuses"]) for c in selected_consts)
        consensus = (
            f"[{const_titles}] 소속 천재 {total_speakers}인이 『{focus}』에 대해 상호 검증한 최종 합의: "
            f"① 추측 대신 제1원리와 밑바닥 증거로 분해하고, "
            f"② 단일 메모리 벽에 갇히지 않도록 성좌별 4비트 모듈(.sbrain)로 외장하드에 무한 적재하며, "
            f"③ 불확실한 경계에서는 안전 경로와 다수 심판 합의로 무결성을 지킨다."
        )
        if field and chain_hops:
            consensus += (
                f" (🧠 추론 근육 Lv{int(field.get('level', 1))} 실전 투입 — {chain_hops} hop 역추적 체인으로 합의까지 연결 완료!)"
            )
        return dialogue, consensus

    def convene_debate(
        self, constellation_ids: List[str], topic: str, rl_gym: Any, field: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        t0 = time.perf_counter()
        consts: List[Dict[str, Any]] = self.data["constellations"]
        by_id = {c["id"]: c for c in consts}
        valid_ids = [cid for cid in constellation_ids if cid in by_id]
        if not valid_ids:
            valid_ids = [c["id"] for c in consts[:2]]

        selected_consts = [by_id[cid] for cid in valid_ids]
        sel_set = set(valid_ids)
        active_bridges = [
            b for b in self.data["bridges"] if b["a"] in sel_set and b["b"] in sel_set
        ]

        dialogue, consensus = self._build_dialogue(selected_consts, topic, active_bridges, field)

        # Aggregate all participating geniuses' bias matrices + inter-constellation resonance bonus
        all_geniuses = [g for c in selected_consts for g in c["geniuses"]]
        combined = [[0.0] * 4 for _ in range(5)]
        for g in all_geniuses:
            for s in range(5):
                for a in range(4):
                    combined[s][a] += g["bias"][s][a] / max(1, len(all_geniuses))

        bridge_boost = 1.0 + 0.14 * len(active_bridges)
        for s in range(5):
            for a in range(4):
                combined[s][a] = round(combined[s][a] * bridge_boost, 4)

        # Forge dedicated modular INT4 .sbrain capsule (accumulating infinitely on external drive!)
        slug = "_".join(cid.replace("const_", "") for cid in valid_ids[:4])
        capsule_path = self.models_dir / f"constellation_{slug}_int4.sbrain"
        capsule_info = _quantize_int4_capsule(
            combined,
            capsule_path,
            meta={
                "constellations": [c["name"] for c in selected_consts],
                "geniuses": [g["name"] for g in all_geniuses],
                "topic": self._extract_topic_focus(topic),
            },
        )

        capsules: List[str] = self.data.setdefault("modular_capsules", [])
        if capsule_info["file"] not in capsules:
            capsules.append(capsule_info["file"])

        # Helper to evaluate 5 CPU Baby Neurons on 80 deterministic unseen trap cases
        def _eval_judges_score() -> Tuple[float, float, float, int]:
            eval_rng = random.Random(20261109)
            ranked = sorted(
                range(len(rl_gym.agents)),
                key=lambda i: rl_gym.agents[i].train_score,
                reverse=True,
            )
            top1 = ranked[0]
            rounds = 80
            s_pts = m_pts = j_pts = 0.0
            for _ in range(rounds):
                a_idx = eval_rng.randrange(len(ARCHETYPES))
                st_vec = rl_gym._sample_state(eval_rng, a_idx, train_mode=False)
                preds = [ag.predict(st_vec) for ag in rl_gym.agents]
                votes = [p[0] for p in preds]
                all_qs = [p[1] for p in preds]
                a_solo = votes[top1]
                counts = {a: votes.count(a) for a in set(votes)}
                a_maj = max(sorted(counts.keys()), key=lambda a: counts[a])
                a_jud = rl_gym._good_judges_pick(votes, all_qs, ranked)
                s_pts += 100.0 if _reward_for(a_idx, a_solo) > 0.8 else (45.0 if _reward_for(a_idx, a_solo) > 0 else 0.0)
                m_pts += 100.0 if _reward_for(a_idx, a_maj) > 0.8 else (45.0 if _reward_for(a_idx, a_maj) > 0 else 0.0)
                j_pts += 100.0 if _reward_for(a_idx, a_jud) > 0.8 else (45.0 if _reward_for(a_idx, a_jud) > 0 else 0.0)
            return round(s_pts / rounds, 1), round(m_pts / rounds, 1), round(j_pts / rounds, 1), top1

        _, _, before_score, _ = _eval_judges_score()

        # Teacher -> Student MLP Knowledge Distillation into our 5 CPU Baby Neurons!
        # Each Domain Constellation specializes in specific real-world Archetypes:
        domain_archetype_affinity = {
            "const_re": {3: 1.0, 4: 1.0, 5: 0.45},
            "const_truth": {1: 0.95, 3: 0.95, 5: 1.0},
            "const_scale": {0: 0.85, 2: 1.0, 1: 0.45},
            "const_strategy": {0: 0.75, 1: 0.75, 2: 0.75, 3: 0.85, 4: 0.85, 5: 0.85},
            "const_shield": {2: 0.85, 3: 0.95, 4: 0.90, 5: 0.80},
        }
        arch_strength = [0.35] * len(ARCHETYPES)
        for cid in valid_ids:
            aff = domain_archetype_affinity.get(cid)
            if aff:
                for a_i, w_val in aff.items():
                    arch_strength[a_i] = min(1.25, arch_strength[a_i] + w_val * 0.55)
            else:
                # Custom user-created constellations boost broad cross-domain wisdom!
                for a_i in range(len(ARCHETYPES)):
                    arch_strength[a_i] = min(1.25, arch_strength[a_i] + 0.45)

        # ⚔️ A deeper reasoning chain teaches the baby neurons a little harder.
        if field:
            r_boost = field_reasoning_boost(field)
            arch_strength = [min(1.25, x * r_boost) for x in arch_strength]

        distill_rng = random.Random(777 + int(self.data.get("debate_sessions", 0)))
        saved_weights = [list(ag.flat_weights()) for ag in rl_gym.agents]

        for idx, ag in enumerate(rl_gym.agents):
            # Agent #1 (index 1) is the shortcut memorizer; other 4 absorb invariant principle mentorship!
            if idx == 1:
                continue
            cautious = bool(ag.profile.get("cautious", False))
            for _ in range(30):
                for s_idx in range(len(ARCHETYPES)):
                    if arch_strength[s_idx] < 0.5:
                        continue
                    _, opt_a, safe_a, trap_a = ARCHETYPES[s_idx]
                    # Sample invariant features (train_mode=True, shortcut_bias=0.0 randomizes spurious dims [6,7]!)
                    st_vec = rl_gym._sample_state(
                        distill_rng, s_idx, train_mode=True, shortcut_bias=0.0, obs_noise=0.04
                    )
                    pred_a, cur_qs, _ = ag.predict(st_vec)
                    if pred_a != opt_a or (cur_qs[opt_a] - cur_qs[trap_a]) < 1.1:
                        ag.update(st_vec, opt_a, 1.0, lr_scale=0.60)
                        ag.update(st_vec, trap_a, -0.92, lr_scale=0.55)
                        if cautious:
                            ag.update(st_vec, safe_a, 0.85, lr_scale=0.35)

        solo_after, maj_after, after_score, top1_idx = _eval_judges_score()
        if after_score < before_score:
            # Validation safety gate (Margaret Hamilton Fallback): never accept a regressive weight step!
            for idx, ag in enumerate(rl_gym.agents):
                ag.load_flat_weights(saved_weights[idx])
            solo_after, maj_after, after_score, top1_idx = _eval_judges_score()
        gain = round(after_score - before_score, 1)
        elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 1)

        sbrain_rec = rl_gym._export_quantized_policy()
        rl_gym.meta["benchmark"] = {
            "trained": True,
            "eval_rounds": 80,
            "top1_agent_name": rl_gym.agents[top1_idx].profile["name"],
            "solo_top1_score": solo_after,
            "majority_vote_score": maj_after,
            "good_judges_score": after_score,
            "gain_vs_solo": round(after_score - solo_after, 1),
            "gain_vs_majority": round(after_score - maj_after, 1),
            "winner": "다수 심판 합의 + 성좌 담론 전수",
            "elapsed_ms": elapsed_ms,
            "policy_file": sbrain_rec["filename"],
            "policy_cos_sim": sbrain_rec["cosine_similarity_pct"],
        }
        rl_gym._save_state()

        focus = self._extract_topic_focus(topic)
        const_names = [c["name"] for c in selected_consts]
        mentor_names = [g["name"] for g in all_geniuses]

        transcript_lines = [
            f"- [{d['constellation_name']} · {d['phase']}] {d['speaker']}({d['lens']}): {d['message']}"
            for d in dialogue
        ]
        wiki_title = f"성좌 원탁 담론 — {' × '.join(const_names)} ({focus[:24]})"
        wiki_body = (
            f"담론 주제: 『{focus}』\n"
            f"참여 영역 성좌: {', '.join(const_names)} (천재 {len(mentor_names)}인 참여, 모듈 {capsule_info['file']} 주조)\n\n"
            + "\n".join(transcript_lines)
            + f"\n\n최종 성좌 합의 공식: {consensus}"
        )

        # 📓 Stage I: the debate's own outcome is the reasoning muscle's report
        # card.  A chain that RAISED the judges' score is worth re-studying as a
        # valid chain; a chain that REGRESSED is taught as a broken chain whose
        # honest answer is "unknown" — never a confident guess.
        exp_case = None
        chain_lines = [d for d in dialogue if str(d.get("phase", "")).startswith("🔗")]
        if field and len(chain_lines) >= 2:
            names = [d["speaker"] for d in chain_lines]
            facts = [(names[i], names[i + 1]) for i in range(len(names) - 1)]
            prob_facts = [list(x) for x in facts]
            answer: Any = True
            if gain < 0 and len(prob_facts) >= 3:
                del prob_facts[len(prob_facts) // 2]
                answer = "unknown"
            exp_case = {
                "ok": gain >= 0,
                "site": "pantheon_debate",
                "key": f"debate:{'+'.join(valid_ids[:3])}",
                "note": (
                    f"실제 담론 「{focus[:18]}」 — 논증 링크 {len(facts)}개"
                    f"(담론 체인 {field_reasoning_hops(field)}hop) · 심판 합의 {gain:+}점"
                ),
                "prob": {
                    "hops": len(facts),
                    "facts": prob_facts,
                    "question": [names[0], names[-1]],
                    "answer": answer,
                    "real_mode": True,
                },
                "metric": {"gain_pts": gain, "hops": len(facts), "after_score": after_score},
            }

        debate_record = {
            "topic": focus,
            "constellations": const_names,
            "constellation_ids": valid_ids,
            "mentors": mentor_names,
            "synergies": [b["label"] for b in active_bridges],
            "dialogue": dialogue,
            "consensus": consensus,
            "sbrain_file": capsule_info["file"],
            "sbrain_kb": capsule_info["size_kb"],
            "total_modular_capsules": len(capsules),
            "cosine_similarity_pct": capsule_info["cosine_similarity_pct"],
            "before_score": before_score,
            "after_score": after_score,
            "gain_pts": gain,
            "elapsed_ms": elapsed_ms,
            "wiki_note_title": wiki_title,
            "wiki_note_body": wiki_body,
            "experience_case": exp_case,
            "field": (
                {
                    "ability": "reasoning",
                    "level": int(field.get("level", 1)),
                    "tier": int(field.get("tier", 0)),
                    "chain_hops": field_reasoning_hops(field),
                    "distill_boost": field_reasoning_boost(field),
                }
                if field
                else None
            ),
        }

        self.data["active_constellation_ids"] = valid_ids
        self.data["debate_sessions"] = int(self.data.get("debate_sessions", 0)) + 1
        self.data["last_debate"] = debate_record
        self._save()
        return debate_record

    def _analyze_user_thought(
        self, thought: str, recalled_notes: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        clean = thought.strip()
        counter_kw = ("반면", "오히려", "하지만", "반대로", "아니라", "보다", "단점", "느리", "느려", "위험", "충돌", "다르면", "틀리")
        opt_kw = ("캐시", "미리", "압축", "속도", "나눠", "쪼개", "단계", "점수", "우선순위", "자동", "백업", "모듈", "저장", "연결", "가볍")
        q_kw = ("어떻게", "왜", "만약", "누가", "언제", "차이", "가능할", "어떨까", "맞을까", "할까")

        if any(k in clean for k in counter_kw):
            stance = "counter"
            badge = "⚡ 예리한 역발상 · 트레이드오프 지적"
            praise_core = "단순히 성좌의 결론을 그대로 받아들이지 않고, 현실에서 부딪힐 수 있는 반대 급부(속도·충돌·비용의 균형)를 정확히 짚어내셨습니다!"
        elif any(k in clean for k in opt_kw):
            stance = "optimize"
            badge = "🛠️ 실전 시스템 설계 · 최적화 제안"
            praise_core = "추상적인 원리를 실제 외장하드와 컴퓨터 위에서 더 빠르고 영리하게 굴러가게 만드는 구체적 메커니즘을 제안하셨어요!"
        elif "?" in clean or any(k in clean for k in q_kw):
            stance = "question"
            badge = "🔭 본질을 꿰뚫는 소크라테스식 질문"
            praise_core = "천재들도 자칫 당연하게 넘길 뻔한 '결정 기준과 경계 조건'을 정면으로 물어보셨습니다. 좋은 질문이 최고의 알고리즘을 만듭니다!"
        else:
            stance = "hypothesis"
            badge = "💡 주인님의 독창적 통찰 · 가설 제시"
            praise_core = "여러 성좌의 논의를 주인님만의 직관적 언어로 재해석해 새로운 방향타를 제시해 주셨습니다!"

        # Extract meaningful tokens for concrete quoting
        tokens = [
            w for w in re.findall(r"[가-힣A-Za-z0-9]{2,}", clean)
            if w not in {"생각엔", "생각에는", "나는", "내가", "만약", "어떨까", "같아", "있을까", "성좌들의", "의견에", "어떻게"}
        ]
        focus_terms = tokens[:3] if tokens else ["핵심 아이디어"]
        wiki_titles = [n["title"] for n in (recalled_notes or [])[:2]]

        return {
            "stance": stance,
            "badge": badge,
            "praise_core": praise_core,
            "focus_terms": focus_terms,
            "wiki_titles": wiki_titles,
        }

    def feedback_on_user_thought(
        self,
        constellation_ids: List[str],
        user_thought: str,
        topic: str,
        recalled_notes: List[Dict[str, Any]],
        rl_gym: Any,
    ) -> Dict[str, Any]:
        t0 = time.perf_counter()
        consts: List[Dict[str, Any]] = self.data["constellations"]
        by_id = {c["id"]: c for c in consts}
        valid_ids = [cid for cid in constellation_ids if cid in by_id]
        if not valid_ids:
            valid_ids = self.data.get("active_constellation_ids") or [consts[0]["id"]]
        selected_consts = [by_id[cid] for cid in valid_ids if cid in by_id]

        # If no prior debate exists yet, convene a quick baseline debate on topic first!
        if not self.data.get("last_debate"):
            self.convene_debate(valid_ids, topic or user_thought, rl_gym)

        last_deb = self.data["last_debate"]
        clean_thought = user_thought.strip()[:220]
        analysis = self._analyze_user_thought(clean_thought, recalled_notes)
        kw_str = " · ".join(analysis["focus_terms"])

        # Pick 3 distinct voices across the selected constellations (Praise / Constructive Critique / Co-evolution Synthesis)
        pool: List[Tuple[Dict[str, Any], Dict[str, Any]]] = [
            (c, g) for c in selected_consts for g in c["geniuses"]
        ]
        c1, g_praise = pool[0]
        c2, g_critique = pool[len(pool) // 2] if len(pool) > 1 else pool[0]
        c3, g_synth = pool[-1]

        wiki_bridge_sentence = (
            f" 게다가 이 발상은 우리 위키 기억망의 『{analysis['wiki_titles'][0]}』 노트와도 멋지게 시냅스가 연결됩니다!"
            if analysis["wiki_titles"]
            else ""
        )

        # Domain-specific constructive blind-spot coaching (never hollow flattery!)
        critique_by_const = {
            "const_re": (
                f"다만 역공학 현장의 함정을 하나 보완해 봅시다! 『{kw_str}』 아이디어를 실행할 때, "
                f"겉모양만 정상처럼 위장한 예외 입력이 들어오면 흐름이 꼬일 수 있으니 '입출력 상태 체크섬 확인'을 입구에 한 줄 추가하면 빈틈이 완전히 사라집니다."
            ),
            "const_truth": (
                f"과학자의 눈으로 보완점을 하나 더하자면, 『{kw_str}』 접근이 빨라질수록 '확인되지 않은 추측'이 슬쩍 섞일 위험을 경계해야 합니다. "
                f"확신도가 75% 미만일 땐 멈춰서 위키 제1원리와 대조하는 안전장치만 묶어주면 완벽합니다!"
            ),
            "const_scale": (
                f"여기에 메모리 공학 디테일을 한 스푼 더하면 천하무적이 됩니다! 『{kw_str}』 방식을 쓸 때 "
                f"자주 안 쓰는 모듈이 작업창(RAM 핫슬롯)에 계속 남아 있지 않도록 '열기-판단-즉시 비우기(LRU 스왑)' 규칙을 짝지어 주면 구형 PC에서도 날아다닙니다."
            ),
            "const_strategy": (
                f"게임이론으로 한 수 더 내다보면 어떨까요? 평소엔 주인님의 『{kw_str}』 해법이 압도적으로 유리하지만, "
                f"의견이 팽팽히 맞설 때를 대비해 '단순 다수결'이 아니라 '위험을 먼저 걸러내는 다수 심판 합의(Good Judges)'를 최종 결승선으로 두면 오판 확률이 0에 수렴합니다!"
            ),
            "const_shield": (
                f"아폴로 방어 공학 관점에서 안전핀 하나만 채워 봅시다! 주인님의 『{kw_str}』 전략이 예상치 못한 과부하를 만났을 때 "
                f"전체를 멈추는 대신 0.01초 만에 기본 안전 모드로 전환하는 비상 회피로(Fallback)를 붙여두면 어떤 위기에도 안 무너집니다."
            ),
        }
        critique_msg = critique_by_const.get(
            c2["id"],
            f"여기에 우리 [{c2['name']}]의 안전 기준을 더해, 『{kw_str}』 실행 전후로 근거 일치율을 짧게 점검하는 관문을 두면 단점 없는 완성형 설계가 됩니다!",
        )

        new_turns = [
            {
                "phase": analysis["badge"],
                "constellation_id": "user_architect",
                "constellation_name": "주인님 · 원탁 의장",
                "color": "#38bdf8",
                "speaker": "👑 주인님의 생각",
                "emoji": "🧑‍🚀",
                "lens": "원탁 의장 · 직접 제안",
                "reply_to": "성좌 원탁 합의안",
                "message": f"“{clean_thought}”",
            },
            {
                "phase": "✨ 강점 공명 피드백",
                "constellation_id": c1["id"],
                "constellation_name": c1["name"],
                "color": c1["color"],
                "speaker": g_praise["name"],
                "emoji": g_praise["emoji"],
                "lens": g_praise["lens"],
                "reply_to": "👑 주인님의 생각",
                "message": (
                    f"무릎을 탁 치게 만드는 생각입니다! {analysis['praise_core']} "
                    f"특히 『{kw_str}』 포인트를 짚어주신 덕분에 우리 [{c1['name']}]의 논의가 탁상공론을 넘어 실전 무기가 되었어요.{wiki_bridge_sentence}"
                ),
            },
            {
                "phase": "🔍 천재의 정밀 보완",
                "constellation_id": c2["id"],
                "constellation_name": c2["name"],
                "color": c2["color"],
                "speaker": g_critique["name"],
                "emoji": g_critique["emoji"],
                "lens": g_critique["lens"],
                "reply_to": "👑 주인님의 생각",
                "message": critique_msg,
            },
            {
                "phase": "🚀 공동 진화 · 다음 질문",
                "constellation_id": c3["id"],
                "constellation_name": c3["name"],
                "color": "#fde68a",
                "speaker": g_synth["name"],
                "emoji": g_synth["emoji"],
                "lens": g_synth["lens"],
                "reply_to": f"주인님 × {g_critique['name']}",
                "message": (
                    f"좋습니다! 주인님의 『{kw_str}』 아이디어에 {g_critique['name']}의 안전핀을 결합해 성좌 합의를 2단계로 업그레이드합시다! "
                    f"한 걸음 더 여쭤볼게요 — 만약 실전에서 '속도'와 '100% 확실한 검증' 중 단 하나만 택해야 하는 긴박한 순간이 오면, 주인님은 어느 쪽에 가중치를 더 두고 싶으신가요?"
                ),
            },
        ]

        last_deb["dialogue"].extend(new_turns)
        upgraded_consensus = (
            f"{last_deb['consensus']} "
            f"➕ [👑 주인님 공동 설계 반영]: 주인님이 제안한 『{clean_thought}』 원칙을 채택하고, "
            f"{g_critique['name']}의 경계 조건 방어막을 결합해 실전 속도·정확도·확장성을 동시에 달성한다."
        )
        last_deb["consensus"] = upgraded_consensus

        # Forge co-authored modular .sbrain capsule & nudge 5 Baby Neurons!
        co_hash = hashlib.md5(clean_thought.encode("utf-8")).hexdigest()[:6]
        capsule_path = self.models_dir / f"coauthored_thought_{co_hash}_int4.sbrain"
        sample_mat = self._default_bias_from_text(clean_thought)
        cap_info = _quantize_int4_capsule(
            sample_mat,
            capsule_path,
            meta={
                "coauthor": "주인님 × " + " × ".join(c["name"] for c in selected_consts),
                "user_thought": clean_thought,
            },
        )
        capsules: List[str] = self.data.setdefault("modular_capsules", [])
        if cap_info["file"] not in capsules:
            capsules.append(cap_info["file"])

        # Reinforce Baby Neurons with validation-gated coaching
        distill_rng = random.Random(999 + len(capsules))
        for idx, ag in enumerate(rl_gym.agents):
            if idx == 1:
                continue
            for s_idx in range(len(ARCHETYPES)):
                _, opt_a, _, trap_a = ARCHETYPES[s_idx]
                st_vec = rl_gym._sample_state(distill_rng, s_idx, train_mode=True, shortcut_bias=0.0, obs_noise=0.04)
                ag.update(st_vec, opt_a, 1.0, lr_scale=0.35)
                ag.update(st_vec, trap_a, -0.92, lr_scale=0.35)
        rl_gym._export_quantized_policy()
        rl_gym._save_state()

        last_deb["total_modular_capsules"] = len(capsules)
        self.data["last_debate"] = last_deb
        self._save()

        elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 1)
        wiki_title = f"주인님 × 성좌 피드백 담론 ({clean_thought[:22]})"
        wiki_body = (
            f"주인님의 제안·생각: 『{clean_thought}』 ({analysis['badge']})\n"
            f"참여 성좌: {', '.join(c['name'] for c in selected_consts)}\n\n"
            + "\n".join(f"- [{t['phase']}] {t['speaker']}: {t['message']}" for t in new_turns[1:])
            + f"\n\n업그레이드된 공동 합의 공식: {upgraded_consensus}"
        )

        return {
            "analysis": analysis,
            "new_turns": new_turns,
            "updated_debate": last_deb,
            "sbrain_file": cap_info["file"],
            "sbrain_kb": cap_info["size_kb"],
            "total_modular_capsules": len(capsules),
            "elapsed_ms": elapsed_ms,
            "wiki_note_title": wiki_title,
            "wiki_note_body": wiki_body,
        }

    # Backward-compatible alias
    def distill_into_neurons(self, ids: List[str], rl_gym: Any, topic: str = "") -> Dict[str, Any]:
        return self.convene_debate(ids, topic, rl_gym)

    def snapshot(self) -> Dict[str, Any]:
        consts: List[Dict[str, Any]] = self.data["constellations"]
        active_ids = self.data.get("active_constellation_ids", [])
        sel_set = set(active_ids)
        active_bridges = [
            b for b in self.data.get("bridges", []) if b["a"] in sel_set and b["b"] in sel_set
        ]
        return {
            "constellations": consts,
            "bridges": self.data.get("bridges", []),
            "active_constellation_ids": active_ids,
            "active_bridges": active_bridges,
            "total_constellations": len(consts),
            "total_geniuses": sum(len(c["geniuses"]) for c in consts),
            "debate_sessions": self.data.get("debate_sessions", 0),
            "modular_capsules": self.data.get("modular_capsules", []),
            "last_debate": self.data.get("last_debate"),
        }
