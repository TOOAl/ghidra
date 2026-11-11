---
title: "🌀 제어흐름·메모리 자가복제 — craft 가 루프/분기/스택을 배우다 (Stage N3)"
category: "역공학·자가복제"
tags: [skill, craft, emulator, control-flow, clean-room, n3, machine-proof]
kind: "code"
created: ""
---

# 🌀 제어흐름·메모리 자가복제 — craft 가 루프/분기/스택을 배우다 (Stage N3)

## 💡 핵심 요약
Stage N 의 craft 는 **직선 스칼라 변환**(점프·메모리 없는 코드)만 복제할 수
있었어요. 루프·분기·스택 지역변수를 쓰는 함수는 에뮬레이터가 정직하게 skip 했죠
(부채④). N3 는 이 한계를 두 개의 새 부품으로 넘었어요 — **제어흐름+메모리
에뮬레이터**(oracle)와 **C 부분집합→파이썬 합성기**(build). 그리고 가장 중요한
것: oracle 이 진짜 맞는지 **gcc 네이티브 실행과 1446/1446 전수 대조**로 기계
증명했어요. 짐작이 아니라 증거예요.

## 🔩 두 부품
- **`brain_engine/x86_cf_emu.py`** — x86-64 부분집합 에뮬레이터. PC·플래그
  (ZF/SF/OF/CF)·스택 메모리(`[rbp±K]`/`[rsp±K]`)·조건점프(je/jne/jg/jl/jle/
  ja/jb…)·무조건점프·**스텝캡이 있는 bounded 루프**·lea·부분레지스터 쓰기
  (AL/AH…)·movzx/movsx 를 실행해요. 입력 레지스터는 실행 전 **사전 탐지**
  (LEA/메모리 경유 읽힘도 counted — 게으른 주입은 이걸 놓쳐 rotl 에서 0 을
  읽던 실제 버그가 있었어요). 확신 없는 것(CALL·복잡 addressing·캡 초과)은
  절대 짐작하지 않고 `unsupported` 에 넣고 **멈춰요**.
- **`brain_engine/c_synthesize.py`** — Ghidra 디컴파일 C 의 작은 부분집합을
  **폭·부호 인식** 파이썬 함수로 옮겨요(선언·대입·for/while·if/else·return·
  산술/논리/비트/비교·캐스트·`1U` 리터럴 접미어). C 의 signed `int` 비교와
  두's complement 래핑을 그대로 재현하고, 파싱 못 하면 `None`(정직 skip).

## 🧭 정직 게이트 (환각이 structurally 불가능한 이유)
craft 는 **차분 검증**으로만 주장해요: 원본 바이트를 실행한 oracle 과 합성
함수를 많은 입력에서 대조 → **100% 일치만 vault 에 기록**. 합성기가(혹은
online SLM 이) 잘못 만들어도 차분 검증이 잡아내 기록이 차단돼요. 게이트
`tools/test_n3_craft.py`(**29/29 그린**, exit 코드)가 이걸 재생산 가능하게
증명해요 — 실제 Ghidra insn + gcc 네이티브 ground truth 픽스처로:
1. oracle == 네이티브 (6 함수 × 91 입력)
2. 합성 == 네이티브 (6 함수 × 91 입력)
3. craft 차분 100% (루프 `sum_to`·분기 `classify`·스택 `with_local`·직선
   `xorv`·lea/rotate `rotl`·부분레지스터 `mix`)
4. CALL → oracle bail → 거짓 100% 기록 안 함
5. 잘못된 합성 → match<100% → record 0건

## 🤖 SLM 합성 hook (부채⑤ 에 역할 부여)
`slm_bridge.synthesize_python()` — 로컬 LLM online 이면 디컴파일 C 의 clean-room
파이썬을 요청(정적 안전검증 + 차분 검증이 최종 게이트), dormant 면 **grounded
폴백으로 코드 발명을 정직 거부**(`source=None` → 규칙 기반 합성기 사용). SLM 이
환각해도 차분 검증이 막으므로, online 이든 offline 이든 vault 는 오염되지 않아요.

이 online 분기는 **기계 증명**됐어요 — `tools/test_n3_slm_online.py`(**13/13 그린**)가
mock 로컬 LLM(OpenAI 호환, 127.0.0.1:8080, 프로세스 내 스레드·외부 네트워크 0)으로
online 경로를 실제로 띄워: 올바른 합성→차분 100%, **환각(그럴듯하지만 틀린 `fn`)→
정적 검증은 통과하나 차분 게이트가 match<100% 로 잡아내 vault 기록 0건**, unsafe
출력→정적 거부, 그리고 규칙 기반이 정직 실패하는 `dw`(do-while)에서 SLM 이 대신
합성해 100% (환각 do-while 오역은 33.51% 거부)를 보였어요. 즉 **SLM 이 가치를
더하는 경우와 환각하는 경우 모두 게이트가 올바로 판정**함이 증명돼요.

## 🚧 남은 한계 (정직 고지)
CALL(다른 함수 호출)·복잡한 addressing 모드·스텝캡 초과 루프는 계속 정직
skip 해요. "무엇이든 craft" 가 아니라 "검증 가능한 만큼만 craft" — 이게
이 두뇌의 방식이에요. *(N3 당시 oracle 이 곱셈/나눗셈 가족 `IMUL` 3-op·`CDQ`·
`DIV`/`IDIV` 에서 bail 하던 구멍은 → Stage N4 에서 해결돼 제수를 쓰는 함수도
복제돼요. 아래 N4 노트 참고.)*

## 🔗 연결된 시냅스 (Wiki Links)
- [[🌀 곱셈·나눗셈 자가복제 — craft 가 magic reciprocal 과 절삭 나눗셈을 배우다 (Stage N4)]]
- [[자가 복제 공작 루프 — craft-anything 두뇌 판 (clean-room)]]
- [[자가 종합 감사 — 4기준 기계 재감사와 부채 원장 (audit_brain)]]
