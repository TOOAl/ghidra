---
name: rad_debug
description: RAD Debugger 흡수 — Epic 초고속 디버거 아이디어
triggers: ["raddebugger", "디버거", "debug", "실행 추적"]
---

# RAD Debugger 흡수 — 3단계 (30줄)

Epic Games의 초고속 네이티브 디버거. 우리 Ghidra 디버거보다 빠른 라이브 추적 아이디어 흡수.

## 흡수한 아이디어

*   RAD는 그래픽 디버거로 프로세스 여러 개를 동시에 본다. 우리는 `live_debug` 도구로 흉내.

## 언제 발동

"실행해봐줘", "디버깅해줘" 트리거 시

## 3단계

1. **붙이기**: `live_debug(pid, action=attach)`로 프로세스에 붙기 (mock은 Ghidra 에뮬레이터 P-code 실행)
2. **추적**: `live_debug(action=trace, addr=0x00401000)`로 10줄 실행 추적. `get_bytes`로 레지스터 확인.
3. **비교**: 정적 `decompile` 결과와 동적 trace 결과 비교. 다르면 `check_contradiction`으로 모순 표시.

## 출력 규칙

*   보고서에 `rad_debug 추적:` 10줄, `정적 vs 동적 차이:` 1문장 필수

## 예시

> rad_debug 추적: 0x401000 → 0x401010 10스텝, eax=1.
> 정적 vs 동적 차이: decompile은 auth==0이었으나, 동적은 auth==1 → 모순 발견.
