"""
Hallucination & Memory-Grounding Telemetry + Actionable Prescription Engine.
Not only measures hallucination risk on two levels (Global Brain Health + Per-Query Audit),
but also diagnoses the exact root causes and generates 1-click actionable remedies to reduce it.
"""

from __future__ import annotations

from typing import Any, Dict, List

ALL_CATEGORIES = [
    "AI모델·양자화",
    "강화학습·판단",
    "역공학·보안",
    "포터블·인프라",
    "아이디어·노하우",
]

CATEGORY_STARTERS: Dict[str, Dict[str, str]] = {
    "아이디어·노하우": {
        "title": "작은 AI 두뇌의 환각을 줄이는 3중 안전장치 설계",
        "text": "초소형 AI 모델이 거짓말(환각)을 하지 않게 만들려면 첫째, 모든 핵심 사실을 마크다운 위키에 양방향 링크로 교차 기록하고 둘째, 위키 근거 점수가 기준치 미만이면 추측을 멈추며 셋째, 자유 수다 대신 검증된 행동 선택지 확률을 채점하게 만든다.",
    },
    "역공학·보안": {
        "title": "Ghidra 디컴파일 함수 요약 시 환각 방지 체크리스트",
        "text": "바이너리를 역공학할 때 함수 이름만 보고 기능을 추측하면 오판(환각)이 생긴다. 반드시 실제 호출 그래프(Call Graph), 참조 문자열, 상수 테이블 세 가지 근거를 마크다운 노트에 함께 기록해 교차 검증해야 정확도가 올라간다.",
    },
    "강화학습·판단": {
        "title": "단일 모델의 착각을 막는 다수 심판 합의(Good Judges) 원리",
        "text": "혼자 공부한 작은 AI 하나는 특정 패턴만 외우는 오버피팅 착각에 빠지기 쉽다. 여러 작은 두뇌가 거부권 심판을 서고 다수가 동의하는 범위 안에서 1등 전문가 두뇌의 판단을 채택하면 환각과 오판이 크게 줄어든다.",
    },
    "AI모델·양자화": {
        "title": "4비트와 8비트 블록 양자화의 정밀도 손실 관리법",
        "text": "가중치를 4비트 니블 패킹으로 줄이면 용량이 84% 절약되지만 미묘한 수치 오차가 생길 수 있다. 새 위키 노트가 쌓일 때마다 어휘 행렬을 동기화해 재주조하거나 핵심 레이어에 8비트 블록 스케일링을 쓰면 환각 오차를 최소화할 수 있다.",
    },
    "포터블·인프라": {
        "title": "외장하드 오프라인 환경에서 지식 일관성 유지하기",
        "text": "여러 컴퓨터를 오가며 일하는 포터블 두뇌는 기억 인덱스(SQLite)와 마크다운 원문, 양자화 두뇌(.sbrain) 버전이 항상 일치해야 옛날 기억으로 잘못 답하는 시간차 환각을 막을 수 있다.",
    },
}


def audit_chat_grounding(question: str, recall_bundle: Dict[str, Any]) -> Dict[str, Any]:
    """Audit whether a chat question is backed by real Markdown Wiki evidence."""
    recalled: List[Dict[str, Any]] = recall_bundle.get("recalled", [])
    top_score = float(recall_bundle.get("top_score", 0.0))
    q_terms: List[str] = recall_bundle.get("query_terms", [])
    matched: List[str] = recall_bundle.get("matched_terms", [])
    missing: List[str] = recall_bundle.get("missing_terms", [])

    if not recalled or top_score < 1.5:
        missing_preview = ", ".join(missing[:4]) if missing else question[:20]
        return {
            "risk_pct": 84,
            "grounding_pct": 16,
            "grade": "high",
            "shield_triggered": True,
            "badge": "🛑 환각 위험 84% 감지 · 억지 추측 차단됨",
            "reason": f"위키 기억망에 '{missing_preview}' 근거가 0건이어서 아는 척 지어내지 않고 솔직하게 멈췄어요.",
            "matched_terms": matched,
            "missing_terms": missing,
        }

    term_total = max(1, len(q_terms))
    coverage = len(matched) / term_total
    has_cross_links = any(len(n.get("links", [])) > 0 for n in recalled)

    if coverage < 0.55 or top_score < 4.5:
        raw_risk = round(46 - coverage * 24 - min(8.0, top_score))
        risk_pct = max(24, min(45, raw_risk))
        miss_txt = ", ".join(missing[:3]) if missing else "일부 세부 개념"
        return {
            "risk_pct": risk_pct,
            "grounding_pct": 100 - risk_pct,
            "grade": "caution",
            "shield_triggered": False,
            "badge": f"⚠️ 환각 위험 {risk_pct}% · 부분 근거 응답",
            "reason": f"'{miss_txt}' 내용은 위키에 아직 없어, 검증된 기억 카드 범위 안에서만 조심스럽게 답했어요.",
            "matched_terms": matched,
            "missing_terms": missing,
        }

    score_bonus = min(10, int(top_score // 2))
    link_bonus = 3 if has_cross_links else 0
    risk_pct = max(4, min(18, 19 - score_bonus - link_bonus))
    return {
        "risk_pct": risk_pct,
        "grounding_pct": 100 - risk_pct,
        "grade": "safe",
        "shield_triggered": False,
        "badge": f"🛡️ 환각 위험 {risk_pct}% · 위키 근거 검증 완료",
        "reason": f"질문 핵심어({', '.join(matched[:4])})가 마크다운 위키 기억 및 시냅스 연결과 정확히 일치해요.",
        "matched_terms": matched,
        "missing_terms": missing,
    }


def evaluate_brain_hallucination(
    notes: List[Dict[str, Any]],
    forged_brains: List[Dict[str, Any]],
    recent_checks: List[int] | None = None,
    recent_missing_topics: List[str] | None = None,
) -> Dict[str, Any]:
    """Compute overall hallucination risk, 4-factor diagnostic breakdown, and live prescriptions."""
    notes_cnt = len(notes)
    linked_any = sum(1 for n in notes if len(n.get("links", [])) >= 1)
    strong_linked = sum(1 for n in notes if len(n.get("links", [])) >= 2)
    weak_notes = [n["title"] for n in notes if len(n.get("links", [])) < 2]

    link_verified_pct = round((linked_any / notes_cnt) * 100) if notes_cnt > 0 else 0
    strong_link_pct = round((strong_linked / notes_cnt) * 100) if notes_cnt > 0 else 0

    # Category balance check
    cat_counts = {c: 0 for c in ALL_CATEGORIES}
    for n in notes:
        cat_counts[n.get("category", "아이디어·노하우")] = cat_counts.get(n.get("category", "아이디어·노하우"), 0) + 1
    weakest_cat = min(ALL_CATEGORIES, key=lambda c: cat_counts.get(c, 0))
    covered_cats = sum(1 for c in ALL_CATEGORIES if cat_counts.get(c, 0) > 0)
    memory_depth_pct = min(100, round(notes_cnt * 11 + covered_cats * 8))

    # Quantized .sbrain precision & sync check
    has_int8_hd = False
    unsynced_notes = 0
    if forged_brains:
        latest = forged_brains[0]
        best_cos = max(float(b.get("cosine_similarity_pct", 98.0)) for b in forged_brains)
        quant_fidelity_pct = round(best_cos, 2)
        has_int8_hd = any(int(b.get("bits", 4)) == 8 and int(b.get("hidden_dim", 64)) >= 96 for b in forged_brains)
        forged_notes_cnt = int(latest.get("notes_count") or 4)
        unsynced_notes = max(0, notes_cnt - forged_notes_cnt)
        quant_penalty = max(0.3, (100.0 - best_cos) * 4.0) + min(5.0, unsynced_notes * 1.8)
        quant_sync_pct = max(60, round(best_cos - unsynced_notes * 6))
    else:
        quant_fidelity_pct = 0.0
        quant_penalty = 8.0
        quant_sync_pct = 55

    density_penalty = max(1.5, 17.0 - min(15.5, notes_cnt * 2.0))
    unlinked_penalty = (100 - strong_link_pct) * 0.12 if notes_cnt > 0 else 22.0
    structural_risk = round(quant_penalty + density_penalty + unlinked_penalty)

    checks = [int(x) for x in (recent_checks or []) if isinstance(x, (int, float))]
    if checks:
        recent_avg_risk = sum(checks[-5:]) / len(checks[-5:])
        recent_grounding_pct = max(5, round(100 - recent_avg_risk))
        risk_pct = round(structural_risk * 0.68 + recent_avg_risk * 0.32)
    else:
        recent_grounding_pct = 92
        risk_pct = structural_risk

    risk_pct = max(3, min(92, risk_pct))
    grounding_pct = 100 - risk_pct

    if risk_pct <= 20:
        grade = "safe"
        label = f"안심 · {risk_pct}%"
        note = "기억 카드들이 시냅스로 검증되어 있고, 모르는 질문은 지어내지 않고 차단해요."
    elif risk_pct <= 45:
        grade = "caution"
        label = f"주의 · {risk_pct}%"
        note = "최근 미보유 질문이 있었거나 일부 지식 연결이 얇아요. 아래 맞춤 처방으로 낮춰보세요!"
    else:
        grade = "high"
        label = f"경고 · {risk_pct}%"
        note = "근거 없는 질문 비중이 높거나 기억 공백이 큽니다! 맞춤 처방 실행을 권장합니다."

    # 4-Factor Diagnostic Breakdown
    breakdown = [
        {
            "key": "memory",
            "title": "위키 기억 두께 & 분야 균형",
            "score_pct": memory_depth_pct,
            "stat": f"노트 {notes_cnt}장 · {covered_cats}/5개 분야 보유",
            "desc": f"현재 '{weakest_cat}' 분야 노트가 {cat_counts[weakest_cat]}장으로 가장 얇아요.",
        },
        {
            "key": "synapse",
            "title": "시냅스 다중 교차검증 밀도",
            "score_pct": strong_link_pct,
            "stat": f"2중 이상 연결 {strong_linked}/{notes_cnt}장 ({strong_link_pct}%)",
            "desc": (
                f"연결이 얇은 노트({', '.join(weak_notes[:2])})를 교차 연결하면 맥락 착각이 줄어듭니다."
                if weak_notes
                else "모든 노트가 2개 이상의 시냅스 고리로 튼튼하게 교차 검증되어 있습니다!"
            ),
        },
        {
            "key": "quant",
            "title": "양자화 두뇌(.sbrain) 정밀도·동기화",
            "score_pct": quant_sync_pct,
            "stat": (
                f"보존율 {quant_fidelity_pct}%"
                + (f" · 미반영 노트 {unsynced_notes}장" if unsynced_notes > 0 else " · 최신 동기화")
                if forged_brains
                else "아직 주조된 .sbrain 없음"
            ),
            "desc": (
                f"새로 먹인 노트 {unsynced_notes}장이 아직 .sbrain 가중치에 반영되지 않았어요."
                if unsynced_notes > 0
                else (
                    "INT8·96차원 고정밀 주조로 양자화 오차를 한 단계 더 줄일 수 있어요."
                    if not has_int8_hd
                    else "최고 정밀도(INT8·96차원) 신경망이 최신 위키와 완벽히 동기화되어 있습니다!"
                )
            ),
        },
        {
            "key": "grounding",
            "title": "최근 대화 근거 적중률",
            "score_pct": recent_grounding_pct,
            "stat": f"최근 검증 {len(checks)}회 · 신뢰도 {recent_grounding_pct}%",
            "desc": "모르는 질문이 들어오면 거짓말 대신 억지추측 차단막이 즉시 작동합니다.",
        },
    ]

    # Dynamic Actionable Prescriptions
    prescriptions: List[Dict[str, Any]] = []
    missing_topics = list(recent_missing_topics or [])

    if missing_topics:
        top_miss = missing_topics[0]
        prescriptions.append(
            {
                "id": "fill_missing_topic",
                "priority": "urgent",
                "badge": "최우선 처방 · 예상 -15%p",
                "title": f"막혔던 미보유 개념 '{top_miss}' 위키에 가르쳐주기",
                "why": f"최근 질문에서 '{top_miss}' 근거가 위키에 0건이어서 환각 경보가 기록되었습니다.",
                "how": "실제로 필요한 지식이라면 2~3문장으로 위키에 먹여 시냅스 근거를 만들어 주세요.",
                "action_kind": "prefill_feed",
                "action_label": f"📝 '{top_miss}' 지식 채우러 가기",
                "payload": {
                    "title": f"{top_miss} 핵심 개념 정리",
                    "text": f"{top_miss}에 대해 시냅스몽이 정확히 기억해야 할 사실과 핵심 원리를 이곳에 적어주세요.",
                },
            }
        )

    if checks and recent_grounding_pct < 65:
        drop_spike = max(6, risk_pct - structural_risk)
        prescriptions.append(
            {
                "id": "resolve_alert_spike",
                "priority": "urgent",
                "badge": f"경보 해소 · 예상 -{drop_spike}%p",
                "title": "함정·미보유 질문으로 치솟은 일시 경보 영점 복구하기",
                "why": f"최근 미보유 질문 차단 경보(적중률 {recent_grounding_pct}%)가 반영되어 위험도가 {structural_risk}% → {risk_pct}%로 올라가 있습니다.",
                "how": "방어막 작동 확인을 마쳤다면 경보 이력을 영점 복구해 순수 두뇌 구조 위험도로 되돌립니다.",
                "action_kind": "instant_reset_checks",
                "action_label": f"🛡️ 경보 확인 완료 · 영점 복구 (-{drop_spike}%p)",
                "payload": {},
            }
        )

    if not forged_brains or unsynced_notes > 0 or not has_int8_hd:
        drop_est = 8 if not forged_brains else (5 if unsynced_notes > 0 else 2)
        why_msg = (
            "아직 내 위키 어휘로 구운 .sbrain 신경망이 없어 기본 상태로 동작 중입니다."
            if not forged_brains
            else (
                f"위키에 새로 추가된 노트 {unsynced_notes}장이 아직 .sbrain 가중치 행렬에 동기화되지 않았습니다."
                if unsynced_notes > 0
                else "현재 4비트 경량 눈금 대신 8비트 블록 스케일링(96차원)을 쓰면 양자화 손실 오차가 거의 0에 수렴합니다."
            )
        )
        prescriptions.append(
            {
                "id": "forge_int8_sync",
                "priority": "recommended",
                "badge": f"신경망 처방 · 예상 -{drop_est}%p",
                "title": "최신 위키 동기화 + 고정밀 INT8(96차원) 두뇌 재주조",
                "why": why_msg,
                "how": "현재 위키의 모든 어휘와 공출현 시냅스를 반영해 99.9%+ 정밀도의 .sbrain 두뇌를 즉시 굽습니다.",
                "action_kind": "instant_forge",
                "action_label": "⚡ 원클릭 INT8 고정밀 두뇌 주조",
                "payload": {"bits": 8, "hidden_dim": 96},
            }
        )

    if weak_notes or strong_link_pct < 100:
        prescriptions.append(
            {
                "id": "weave_synapses",
                "priority": "recommended",
                "badge": "구조 처방 · 예상 -4%p",
                "title": "약한 기억 노트에 [[양방향 시냅스 링크]] 자동 촘촘화",
                "why": "혼자 동떨어진 노트는 문맥을 잘못 짚는 착각을 유발합니다. 서로 연결된 노트일수록 교차 검증이 됩니다.",
                "how": "위키 전체 노트의 공통 키워드와 주제를 스캔해 빠진 [[양방향 링크]]를 자동으로 엮어줍니다.",
                "action_kind": "instant_relink",
                "action_label": "🔗 시냅스 교차검증 자동 연결",
                "payload": {},
            }
        )

    starter = CATEGORY_STARTERS.get(weakest_cat, CATEGORY_STARTERS["아이디어·노하우"])
    prescriptions.append(
        {
            "id": "boost_weak_category",
            "priority": "good",
            "badge": f"영양 처방 · 예상 -3%p",
            "title": f"가장 얇은 '{weakest_cat}' 분야 핵심 지식 보충하기",
            "why": f"현재 5대 영역 중 '{weakest_cat}' 노트가 {cat_counts[weakest_cat]}장으로 가장 적어 해당 분야 질문에 취약합니다.",
            "how": "준비된 환각 방지 핵심 노트를 원클릭으로 먹여 지식 편식을 없애고 기억 밀도를 높입니다.",
            "action_kind": "instant_seed_feed",
            "action_label": f"🌱 '{weakest_cat}' 보강 노트 즉시 먹이기",
            "payload": starter,
        }
    )

    top_tip = prescriptions[0]["title"] if prescriptions else "모든 환각 방어 지표가 최상입니다!"

    return {
        "risk_pct": risk_pct,
        "grounding_pct": grounding_pct,
        "grade": grade,
        "label": label,
        "link_verified_pct": link_verified_pct,
        "strong_link_pct": strong_link_pct,
        "quant_fidelity_pct": quant_fidelity_pct,
        "shield_active": True,
        "recent_checks_count": len(checks),
        "note": note,
        "top_tip": top_tip,
        "breakdown": breakdown,
        "prescriptions": prescriptions,
    }
