---
name: find_vuln
description: 버퍼오버플로우 등 취약점 찾는 스킬
triggers: ["취약점", "vuln", "overflow", "RCE", "버그"]
---

# 취약점 찾기 스킬

## 절차

1. `list_imports`로 위험 함수 확인: strcpy, sprintf, gets, memcpy, system, exec
2. 그 함수를 호출하는 곳 `get_xrefs` → `decompile` 로 인수 길이 검증 여부 확인
3. 사용자 입력 → 위험 함수까지 경로 추적
4. `search_memory`로 과거 CVE 패턴 대조
5. PoC 아이디어까지 제안 (가능하면)

## 라벨

- CONFIRMED: 입력 길이 검증 없이 strcpy에 그대로 전달됨 (decompile 증거 있음)
- LIKELY: 길이 검증 로직 있으나 우회 가능해 보임
- POSSIBLE: 위험 함수 사용하나 경로 불명확
