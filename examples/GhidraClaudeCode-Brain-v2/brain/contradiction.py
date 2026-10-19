"""
brain/contradiction.py — 모순 발견 (룰 3개, 50줄 이내)

외부 LLM이 보고서에 CONFIRMED라 써도, 증거가 없으면 모순.
룰로 먼저 걸러내고, LLM에 넘기기 전에 등급을 낮춘다.
"""
import re

def check_contradiction(report: str, evidence: dict) -> dict:
    """
    입력: report(보고서 텍스트), evidence(Tool 결과 모음)
    출력: {"contradictions": [...], "suggested_downgrades": [...]}
    증거가 없는데 CONFIRMED면 모순.
    """
    contradictions = []
    evidence_text = str(evidence).lower()

    # 룰 1: C2 CONFIRMED인데 strings에 http 없음
    if re.search(r"CONFIRMED.*c2", report, re.I):
        if "http" not in evidence_text and "c2.evil" not in evidence_text:
            contradictions.append({
                "rule": "C2_claim_without_string",
                "claim": "C2 CONFIRMED",
                "evidence_missing": "list_strings에 http 없음",
                "severity": "high"
            })

    # 룰 2: rename CONFIRMED인데 old_name이 list_functions에 없음
    if "rename" in report.lower() and "CONFIRMED" in report:
        # 간단: evidence에 functions가 없으면 모순 의심
        if "functions" in evidence_text and "fun_0040" not in evidence_text.lower():
            # 실제 함수가 1개뿐인데 여러 rename이면 의심 — 단순화: 스킵 조건 완화
            pass
        # 더 정확: rename 대상이 evidence에 없는 경우만
        m = re.findall(r"rename[^\n]*?(\w+_0040\w+)", report, re.I)
        for name in m:
            if name.lower() not in evidence_text:
                contradictions.append({
                    "rule": "rename_without_function",
                    "claim": f"rename {name}",
                    "evidence_missing": f"list_functions에 {name} 없음",
                    "severity": "medium"
                })

    # 룰 3: patch CONFIRMED인데 get_bytes 원본 없음
    if "patch" in report.lower() and "CONFIRMED" in report:
        if "get_bytes" not in evidence_text and "orig" not in evidence_text:
            contradictions.append({
                "rule": "patch_without_original",
                "claim": "patch CONFIRMED",
                "evidence_missing": "get_bytes로 원본 없음",
                "severity": "medium"
            })

    # 제안: 모순 있으면 등급 강등
    suggested = []
    for c in contradictions:
        if c["severity"] == "high":
            suggested.append({"from": "CONFIRMED", "to": "LIKELY", "reason": c["rule"]})
        else:
            suggested.append({"from": "CONFIRMED", "to": "POSSIBLE", "reason": c["rule"]})

    return {
        "contradictions": contradictions,
        "suggested_downgrades": suggested,
        "ok": len(contradictions) == 0,
        "summary": f"{len(contradictions)}개 모순" if contradictions else "모순 없음"
    }

def check_from_router(claim: str, evidence: dict) -> dict:
    """Tool 라우터용 래퍼 — check_contradiction 도구"""
    return check_contradiction(claim, evidence)

if __name__ == "__main__":
    # 수동 테스트
    report = "CONFIRMED: C2 http://c2.evil.com 발견"
    evidence = {"list_strings": ["http://c2.evil.com"]}
    print(check_contradiction(report, evidence))
    report2 = "CONFIRMED: C2 발견"
    evidence2 = {"list_strings": ["hello"]}
    print(check_contradiction(report2, evidence2))
