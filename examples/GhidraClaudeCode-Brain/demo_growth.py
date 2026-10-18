#!/usr/bin/env python3
"""
demo_growth.py — 2번(스킬) + 3번(도구) 성장 검증 데모

새 스킬: unpack_upx, find_crypto
새 도구: patch_bytes, search_bytes, get_bytes, list_imports
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import json

print("="*70)
print(" 🌱 두뇌 성장 검증 — 스킬 2개 + 도구 4개 추가")
print("="*70)

# 1. 스킬 로드 확인
print("\n[스킬]")
for p in Path("skills").glob("*.md"):
    text = p.read_text(encoding="utf-8")
    name = text.split("name:")[1].split("\n")[0].strip() if "name:" in text else p.stem
    triggers = text.split("triggers:")[1].split("\n")[0].strip() if "triggers:" in text else ""
    print(f"  ✓ {p.name:20s} — {name} {triggers}")

# 2. 도구 정의 확인
print("\n[도구]")
with open("tools/definitions.json", encoding="utf-8") as f:
    tools = json.load(f)
for t in tools:
    print(f"  ✓ {t['name']:20s} — {t['description'][:60]}")

new_tools = {"list_imports", "search_bytes", "get_bytes", "patch_bytes"}
has_new = new_tools.issubset({t["name"] for t in tools})
print(f"\n  → 기존 7개 → 현재 {len(tools)}개 ({'✅ 성장 성공' if has_new else '❌ 실패'})")

# 3. 라우터 mock 테스트 — 새 도구 4개
print("\n[새 도구 mock 실행 — 로컬에서 Ghidra 없이 테스트]")
from tools.ghidra_router import GhidraRouter
router = GhidraRouter()

tests = [
    ("UPX 탐지", "list_imports", {"filter": ""}),
    ("UPX 탐지", "search_bytes", {"pattern": "60 BE ?? ?? ?? ?? 8DBE"}),
    ("암호 상수", "search_bytes", {"pattern": "63 7C 77 7B F2 6B 6F C5"}),
    ("키 덤프", "get_bytes", {"address": "0x00403000", "length": 32}),
    ("패치", "patch_bytes", {"address": "0x00401234", "bytes": "90 90", "comment": "라이선스 체크 무력화 (JE → NOP)"}),
]

for label, name, inp in tests:
    print(f"\n  [{label}] → {name}({inp})")
    res = router.dispatch(name, inp)
    print(f"         ← {str(res)[:300]}")

# 4. 시나리오: UPX 패킹 + AES 암호 함께 있는 바이너리
print("\n" + "="*70)
print(" [시나리오] UPX 패킹 + AES 암호가 섞인 악성코드")
print("="*70)
print("  외부 LLM(무료)이 이렇게 계획함:")
print("   1. list_imports → import 3개 뿐, UPX 의심 (unpack_upx 스킬 발동)")
print("   2. search_bytes(UPX pattern) → UPX stub 발견 → upx -d 추천")
print("   3. (언패킹 후) search_bytes(AES S-box) → 0x00401500에서 발견")
print("   4. get_bytes(0x00403000, 32) → AES 키 덤프")
print("   5. rename_function(FUN_00401500 → decrypt_c2_config)")
print("   6. get_xrefs → 라이선스 체크 함수 찾음 → patch_bytes로 JE → NOP 무력화")
print("   7. search_memory → 과거 유사 악성코드 91% 유사")

scenario = [
    ("list_imports", {"filter": ""}),
    ("search_bytes", {"pattern": "60 BE ?? ?? ?? ?? 8DBE"}),
    ("search_bytes", {"pattern": "63 7C 77 7B F2 6B 6F C5 30 01 67 2B"}),
    ("get_bytes", {"address": "0x00403000", "length": 32}),
    ("rename_function", {"old_name": "FUN_00401500", "new_name": "decrypt_c2_config"}),
    ("set_comment", {"name": "decrypt_c2_config", "comment": "CONFIRMED: AES-256-CBC, key at 0x00403000, S-box at 0x00401500"}),
    ("patch_bytes", {"address": "0x00401234", "bytes": "90 90", "comment": "UPX 언패킹 후 라이선스 JNZ 무력화"}),
]

for name, inp in scenario:
    print(f"\n  → {name}({inp})")
    res = router.dispatch(name, inp)
    print(f"    ← {json.dumps(res, ensure_ascii=False)[:250]}")

print("\n" + "="*70)
print(" ✅ 성장 완료!")
print(" - 스킬: find_c2, find_vuln + unpack_upx, find_crypto (4개)")
print(" - 도구: 기존 7개 + list_imports, search_bytes, get_bytes, patch_bytes (11개)")
print(" - WritePlugin: /patch_bytes, /get_bytes, /search_bytes, /list_imports 엔드포인트 추가")
print(" - 다음 분석부터 새 스킬/도구가 자동 사용됨")
print("="*70)
print("\n[저장] 이번 성장은 Arena GitHub 브랜치에 push될 예정")
print("      나중에 로컬로 다운받으면 성장한 두뇌 그대로 사용 가능")
