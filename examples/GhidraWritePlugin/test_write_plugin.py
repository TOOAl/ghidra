#!/usr/bin/env python3
"""
test_write_plugin.py — GhidraWritePlugin 쓰기 테스트 (Ghidra 없이 mock으로도 동작)

Ghidra를 켜고 플러그인을 설치한 뒤:
  python test_write_plugin.py --url http://127.0.0.1:8089

Ghidra 없이 mock 데모:
  python test_write_plugin.py --mock
"""
import argparse
import json
import sys

def test_mock():
    print("="*70)
    print(" Mock 쓰기 테스트 — Ghidra 없이 흐름 확인")
    print("="*70)
    # 우리 라우터의 mock 경로
    sys.path.insert(0, "../GhidraClaudeCode-Brain")
    from tools.ghidra_router import GhidraRouter
    router = GhidraRouter()  # no url → mock
    tests = [
        ("rename_function", {"old_name": "FUN_00401000", "new_name": "decrypt_config"}),
        ("set_comment", {"name": "decrypt_config", "comment": "C2 복호화 — 외부 LLM 분석, 증거: decompile 12번째 줄"}),
        ("rename_function", {"old_name": "FUN_00401234", "new_name": "check_license"}),
        ("set_comment", {"name": "check_license", "comment": "라이선스 검증 — strcmp 사용, 취약점 후보"}),
    ]
    for name, inp in tests:
        print(f"\n→ {name}({json.dumps(inp, ensure_ascii=False)})")
        res = router.dispatch(name, inp)
        print(f"← {json.dumps(res, ensure_ascii=False)}")
        # 로컬 기억에 쓰기 이력 저장 (진짜와 동일)
        print(f"  [로컬 기억] memory/session.jsonl 에 쓰기 이력 저장 → 다음 분석 때 재사용")

    print("\n" + "="*70)
    print(" Mock 쓰기 완료 — 실제 Ghidra에서는 함수명이 진짜 바뀝니다!")
    print("="*70)

def test_real(url):
    import requests
    print(f"Testing real plugin at {url}")
    # health
    try:
        r = requests.get(f"{url}/health", timeout=3)
        print(f"GET /health → {r.status_code} {r.text[:400]}")
    except Exception as e:
        print(f"GET /health 실패: {e}")
        print("Ghidra CodeBrowser가 켜져 있고 플러그인이 활성화되어 있는지 확인하세요.")
        print("Tool Options > GhidraWritePlugin > 포트 8089 확인")
        return

    tests = [
        ("rename_function", {"old_name": "FUN_00401000", "new_name": "decrypt_config"}),
        ("set_comment", {"name": "decrypt_config", "comment": "C2 복호화 — Brain 분석"}),
    ]
    for endpoint, body in tests:
        try:
            r = requests.post(f"{url}/{endpoint}", json=body, timeout=5)
            print(f"POST /{endpoint} {body} → {r.status_code} {r.text[:600]}")
        except Exception as e:
            print(f"POST /{endpoint} 실패: {e}")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--url", default="http://127.0.0.1:8089", help="GhidraWritePlugin URL")
    p.add_argument("--mock", action="store_true", help="Ghidra 없이 mock 테스트")
    args = p.parse_args()
    if args.mock or args.url == "mock":
        test_mock()
    else:
        test_real(args.url)
