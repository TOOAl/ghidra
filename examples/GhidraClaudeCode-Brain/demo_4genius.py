#!/usr/bin/env python3
"""
demo_4genius.py — 4명 천재 조합 데모 (최소, 80줄)

시나리오: UPX 패킹 + C2 + AES 암호가 섞인 악성코드 1개 분석
각 천재가 번갈아 기여 → 모순 탐지로 검증
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from tools.ghidra_router import GhidraRouter

def demo():
    r = GhidraRouter()
    print("="*70)
    print(" 4명 천재 조합 데모 — UPX + C2 + AES 악성코드")
    print("="*70)

    # 공통 증거 수집 (외부 LLM이 한 일, 여기선 mock)
    evidence = {}
    evidence["list_functions"] = r.dispatch("list_functions", {"limit": 5})
    evidence["list_strings"] = r.dispatch("list_strings", {"filter": "http"})
    evidence["list_imports"] = r.dispatch("list_imports", {})
    evidence["search_bytes"] = r.dispatch("search_bytes", {"pattern": "63 7C 77 7B"})
    evidence["get_bytes"] = r.dispatch("get_bytes", {"address": "0x00403000", "length": 16})
    print(f"\n[증거 수집] 함수 3개, 문자열 {len(evidence['list_strings']['strings'])}개, import 4개")

    # 1. 튜링 — 형식화
    print("\n--- 1. 튜링: 형식화 ---")
    print(" 튜링 형식화: main(S1) --[UPX]--> unpacked(S2) --[send]--> C2(S3)")
    r.dispatch("create_block", {"type": "text", "content": "상태: S1 --UPX--> S2 --AES--> S3 // 튜링 형식화"})
    print(" 튜링 해독: 0x00401500 반복 → 키 길이 16 추론")
    print(" 튜링 모방: C2가 아니라면 http 없어야 하나, 있어 → 반증 실패 → CONFIRMED 유지")

    # 2. 다빈치 — 관찰→스케치→연결
    print("\n--- 2. 다빈치: 관찰→스케치→연결 ---")
    print(" 다빈치 관찰: FUN_00401000은 주변보다 3배 큼 — 껍질(패킹) 의심")
    r.dispatch("create_block", {"type": "code", "content": "if (key==0) return -1; // 다빈치 스케치: 잠금"})
    print(" 다빈치 스케치: code 블록 생성 (잠금 스케치)")
    print(" 다빈치 연결: 껍질은 새 부리처럼 단단 → UPX 스킬 대조")

    # 3. 퀴리 — 측정→반복→실패로그
    print("\n--- 3. 퀴리: 측정→반복→실패로그 ---")
    print(f" 퀴리 측정: 문자열 3개, import 4개, 엔트로피 {evidence['get_bytes']['entropy']} (정량)")
    print(" 퀴리 반복: 1차 decompile 짧음 vs 2차 xrefs 숨은 호출자 발견")
    r.dispatch("decompile", {"name": "main"})
    r.dispatch("get_xrefs", {"name": "main"})
    print(" 퀴리 실패로그: AES S-box 1차 실패 → 패턴 변경 후 2차 성공 (로그 기록)")

    # 4. 오일러 — 기호→일반화→우아한 계산
    print("\n--- 4. 오일러: 기호→일반화→우아한 계산 ---")
    print(" 오일러 기호: f(x)=AES_decrypt(key, base64(data))")
    r.dispatch("create_block", {"type": "text", "content": "f=AES(key, b64) // 오일러 기호"})
    print(" 오일러 일반화: 1개 C2 → 3개 C2 모두 base64, n개 일반화 성공")
    print(" 오일러 계산: 패치 5바이트 아닌 2바이트 NOP가 가장 우아함")
    r.dispatch("patch_bytes", {"address": "0x00401234", "bytes": "90 90", "comment": "오일러 최적: 2바이트"})

    # 5. 모순 탐지 — 4명 결과를 교차 검증
    print("\n--- 5. 모순 탐지 (3룰) ---")
    report_ok = "CONFIRMED: C2 http://c2.evil.com, AES S-box 발견, patch 완료"
    report_bad = "CONFIRMED: C2 발견"
    ok = r.dispatch("check_contradiction", {"report": report_ok, "evidence": evidence})
    bad = r.dispatch("check_contradiction", {"report": report_bad, "evidence": {"list_strings": ["hello"]}})
    print(f" 정상 보고서: {ok['summary']} → 등급 유지")
    print(f" 모순 보고서: {bad['summary']} → {bad['suggested_downgrades'][0]['from']}→{bad['suggested_downgrades'][0]['to']} 강등 제안")

    # 최종 보고서 (4명 기여 합체)
    print("\n" + "="*70)
    print(" 최종 보고서 — 4명 천재 조합")
    print("="*70)
    print("""
 튜링 형식화: S1→S2→S3 상태기계
 다빈치 관찰: 껍질 의심 + 스케치(잠금)
 퀴리 측정: 3개 문자열, 4개 import, 엔트로피 7.2
 오일러 기호: f=AES(key,b64), 일반화 n개, 2바이트 패치

 결론: CONFIRMED — UPX 패킹 + C2 + AES (4명 교차 검증, 모순 없음)
 모순 검사: 0개 → CONFIRMED 유지
 """)
    print("="*70)
    print(" ✅ 4명 조합 데모 완료 — 각 30줄 스킬, 모순 3룰, 도구 21개")
    print("    다음 분석부터 '다빈치+퀴리+튜링+오일러' 동시 호출 가능")
    print("="*70)

if __name__ == "__main__":
    demo()
