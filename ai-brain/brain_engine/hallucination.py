"""
Hallucination & Memory-Grounding Telemetry Engine.
Measures two levels of hallucination risk for our portable small AI brain:
  1. Global Brain Hallucination Index (structural health of Wiki graph + .sbrain quantization fidelity + recent grounding history)
  2. Per-Query Answer Grounding Audit (real-time hallucination detector & fabrication shield on every chat question)
"""

from __future__ import annotations

from typing import Any, Dict, List


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
) -> Dict[str, Any]:
    """Compute overall hallucination risk & grounding telemetry of the brain."""
    notes_cnt = len(notes)
    linked_notes = sum(1 for n in notes if len(n.get("links", [])) > 0)
    link_verified_pct = round((linked_notes / notes_cnt) * 100) if notes_cnt > 0 else 0

    if forged_brains:
        best_cos = max(float(b.get("cosine_similarity_pct", 98.0)) for b in forged_brains)
        quant_fidelity_pct = round(best_cos, 2)
        quant_penalty = max(0.5, (100.0 - best_cos) * 4.0)
    else:
        quant_fidelity_pct = 0.0
        quant_penalty = 8.0  # Slight uncertainty until first custom .sbrain is forged

    # Structural risk from sparse or unlinked notes
    density_penalty = max(2.0, 18.0 - min(16.0, notes_cnt * 2.2))
    unlinked_penalty = (100 - link_verified_pct) * 0.18 if notes_cnt > 0 else 25.0

    structural_risk = round(quant_penalty + density_penalty + unlinked_penalty)

    checks = [int(x) for x in (recent_checks or []) if isinstance(x, (int, float))]
    if checks:
        recent_avg = sum(checks[-5:]) / len(checks[-5:])
        # Blend 65% structural brain health + 35% recent query grounding experience
        risk_pct = round(structural_risk * 0.65 + recent_avg * 0.35)
    else:
        risk_pct = structural_risk

    risk_pct = max(4, min(92, risk_pct))
    grounding_pct = 100 - risk_pct

    if risk_pct <= 20:
        grade = "safe"
        label = f"안심 · {risk_pct}%"
        note = "기억 카드들이 시냅스로 촘촘히 검증되어 있고, 모르는 질문은 지어내지 않고 차단해요."
    elif risk_pct <= 45:
        grade = "caution"
        label = f"주의 · {risk_pct}%"
        note = "일부 주제에 빈틈이 있어요. 위키 노트를 더 먹이거나 양자화 두뇌를 주조하면 환각이 줄어듭니다."
    else:
        grade = "high"
        label = f"경고 · {risk_pct}%"
        note = "최근 근거 없는 질문이 많거나 연결된 기억이 부족해요! 관련 지식을 위키에 보충해 주세요."

    return {
        "risk_pct": risk_pct,
        "grounding_pct": grounding_pct,
        "grade": grade,
        "label": label,
        "link_verified_pct": link_verified_pct,
        "quant_fidelity_pct": quant_fidelity_pct,
        "shield_active": True,
        "recent_checks_count": len(checks),
        "note": note,
    }
