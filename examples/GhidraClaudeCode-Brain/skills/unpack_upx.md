---
name: unpack_upx
description: UPX 등 패킹된 바이너리를 탐지하고 언패킹하는 스킬
triggers: ["UPX", "packed", "패킹", "언패킹", "Themida", "VMProtect", "압축"]
---

# UPX 언패킹 스킬

패킹된 바이너리는 Ghidra로 바로 봐도 코드가 안 보이고 `UPX!` 같은 문자열만 보인다.

## 탐지 (Detection)

1. `list_strings`에서 `UPX0`, `UPX1`, `UPX!` 검색 — UPX 시그니처
2. `list_segments`에서 entropy 높은 섹션 확인 (`.upx0`는 크기 0인데 메모리에서 큼)
3. `get_imports`에서 import가 3개 이하로 극도로 적으면 패킹 의심

## 절차 (Workflow)

1. 탐지 결과 `search_memory`로 과거 언패킹 사례 대조
2. 외부 언패커 추천:
   - UPX: `upx -d sample.exe -o unpacked.exe` (로컬에서 실행)
   - 일반: `python -m unblob` or `binwalk -e` (펌웨어일 경우 REA provider)
3. 언패킹 후 `list_functions`로 다시 분석 — 함수 수가 10배 늘어나면 성공
4. 보고서에 `CONFIRMED: UPX packed (UPX! 시그니처 + 섹션 UPX0)` 명시

## 도구

- `list_strings` (UPX 시그니처)
- `list_imports` (import 수)
- `get_bytes` (섹션 헤더 확인)
- `search_bytes` (UPX stub 패턴: `60 BE ?? ?? ?? ?? 8DBE`)
- `search_memory` (과거 언패킹 기억)

## 주의

- 언패킹은 원본을 수정하지 않고 `unpacked.exe` 새 파일로 저장
- GhidraWritePlugin으로는 패킹 해제 불가 — 로컬 `upx` 명령어 사용
- 언패킹 실패 시 `LIKELY: packed but unpacker not found`로 보고

## 예시 보고서 문장

> CONFIRMED: UPX 3.96 packed — `list_strings`에서 `UPX!` 발견, 섹션 3개 중 2개가 UPX0/UPX1. `upx -d`로 언패킹 후 함수 12개 → 247개로 증가.
