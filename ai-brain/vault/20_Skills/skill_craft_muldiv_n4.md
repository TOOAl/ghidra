---
title: "🌀 곱셈·나눗셈 자가복제 — craft 가 magic reciprocal 과 절삭 나눗셈을 배우다 (Stage N4)"
category: "역공학·자가복제"
tags: [skill, craft, emulator, muldiv, magic-number, clean-room, n4, machine-proof]
kind: "code"
created: ""
---

# 🌀 곱셈·나눗셈 자가복제 — craft 가 magic reciprocal 과 절삭 나눗셈을 배우다 (Stage N4)

## 💡 핵심 요약
N3 까지 craft 의 oracle(에뮬레이터)은 가감법·비트·시프트·제어흐름·메모리는
실행했지만 **곱셈/나눗셈 가족**(`IMUL` 3-operand·`CDQ/CQO`·`DIV/IDIV`·one-op
`MUL/IMUL`)은 만나면 정직하게 `unsupported` 로 멈췄어요. 그래서 제수(나누는 수)를
쓰는 함수는 복제 불가였죠(부채④ 잔여). N4 는 이 구멍을 막았어요 — oracle 에
곱셈/나눗셈 가족을 추가하고, 합성기에 **C-충실 절삭 나눗셈**(`/`·`%`)을 추가.
그리고 N3 와 같은 정직 방법론으로 기계증명: **gcc -O0 네이티브 실행 ground
truth 와 11개 함수 전수 대조**(각 271 입력, 미지원 0).

핵심 발견: gcc 는 상수 제수를 `-O0` 에서도 **magic-number reciprocal 곱셈**
(3-operand `IMUL RDX,RDX,0x55555556` + shifts)으로 컴파일해요(`CDQ;IDIV` 아님).
`CDQ;IDIV`/`DIV` 는 **variable 제수**에서만 나와요. 즉 상수 나눗셈 craft 의 열쇠는
3-operand IMUL 이었고, variable 나눗셈의 열쇠는 CDQ+IDIV/DIV 였어요.

## 🔩 확장된 두 부품
- **`brain_engine/x86_cf_emu.py`** (oracle) — 곱셈/나눗셈 가족 추가:
  - **3-operand `IMUL dst,src,imm`** — `dst = (src*imm)` 폭 래핑(magic reciprocal 의
    핵심). 2-operand `IMUL dst,src` 는 기존 ARITH 경로 그대로.
  - **one-op `MUL`/`IMUL r/m`** — `DX:AX` 페어(8/16/32/64 폭별 `_ACC`)에 곱.
    `MUL` unsigned, `IMUL` signed(두's complement 하위 비트는 동일).
  - **부호확장** `CDQ`(EDX←sext EAX)·`CQO`(RDX←sext RAX)·`CWD`·`CDQE`·`CWDE`·`CBW`.
  - **`DIV`/`IDIV r/m`** — `DX:AX`(폭별 2w 비트 피제수) ÷ src → 몫 `AX`·나머지 `DX`.
    `IDIV` 는 **0 방향 절삭**(C semantics), 제수 0·몫 오버플로(#DE)는 정직 bail.
- **`brain_engine/c_synthesize.py`** (build) — C 정수 `/`·`%` 를 **C-충실 절삭**
  헬퍼로 합성: `/`→`_tdiv`, `%`→`_tmod`(AST `NodeTransformer` 로 치환 후 unparse).
  파이썬 `//`·`%` 는 **바닥 나눗셈**이라 음수에서 C 와 달라요(`-7//3=-3` but C
  `-7/3=-2`; `-7%3=2` but C `-7%3=-1`) — 그대로 쓰면 환각. `_tdiv(a,b)` 는
  `abs(a)//abs(b)` 에 부호를 곱제수 기준으로 붙여 절삭, `_tmod(a,b)=a-_tdiv(a,b)*b`
  (피제수 부호). 제수가 상수든 표현식이든(`x/((x&7)+2)`) 동일하게 동작.
  - **타입폭 수정**: Ghidra x86-64(LP64) 렌더의 `long`/`ulong` 은 **64비트**
    (이전 `_TYPE_WIDTH` 가 `long:32` 로 오분류 → 64비트 곱셈 반환을 32비트로
    잘라 차분 게이트가 거부했음). `ulong` 은 누락돼 추가.

## 🧭 정직 게이트 (환각이 structurally 불가능한 이유)
N3 와 동일 구조 — **차분 검증 100% 만 vault 기록**. 게이트
`tools/test_n4_muldiv.py`(**51/51 그린**, exit 코드)가 재생산 가능하게 증명:
1. **oracle == gcc 네이티브** — 11 함수 × 271 입력 전수(미지원 0): signed/unsigned
   상수 나눗셈·나머지(magic 3-op imul: `idiv3`·`imod5`·`udiv7`·`umod9`)·variable
   제수(`vdiv`·`vmod` cdq;idiv / `uvdiv`·`uvmod` div)·제곱(`square` 2-op imul)·
   64비트 곱셈(`umulwide`·`imulwide`, long 반환)
2. **합성 == 네이티브** — 깔끔한 디컴파일 9 함수 전수(`_tdiv`/`_tmod` 절삭 검증)
3. **craft 차분 100%** — 9 함수 + `record` 는 100% 9개만 저장(발명 금지)
4. **C-충실 절삭 단위 테이블** — `_tdiv`/`_tmod` 가 C 와 일치하고 파이썬 `//`·`%`
   와는 음수에서 다름을 명시 입증
5. **정직** — `vdiv`(지저분한 -O0 16바이트 구조체 렌더)→합성 `None`→skip;
   `vmod`(병적 `(long)(int)` 캐스트)→합성 불일치→차분 70.91%<100%→record 차단;
   훼손 합성(올바른 `_tdiv(x,3)` 을 바닥 `x//3` 으로 교체)→차분 <100% 거부
6. **참조 검증** — gcc 가 방출하지 않은 형태(one-op `MUL`/`IMUL` 32·64, `CQO`+64
   `IDIV`, `CDQE`, `CWD`)를 **독립 파이썬 참조**(x86 문서화 semantics)와 대조

## 🚧 남은 한계 (정직 고지)
- `cmov`(조건부 이동 — `absv`·`clampv`)·`switch`(점프테이블)는 계속 정직 bail
  (N4 범위 = 곱셈/나눗셈 가족만 확장).
- one-op `MUL`/`IMUL`·`CQO`·64비트 `IDIV`·`CDQE`/`CWD` 는 gcc 가 단순 단일입력
  함수에서 방출하지 않아 **네이티브가 아닌 독립 참조**로 증명(oracle 구현은
 complete, 32비트 `CDQ;IDIV`/`DIV` 는 `vdiv`/`uvdiv` 로 네이티브 증명됨).
- 합성기는 부호를 바꾸는 캐스트(`(int)uintVar`)를 모델링하지 않음 → 그런 지저분한
  -O0 디컴파일(`vmod`)은 차분 게이트가 정직 거부(거짓 기록 없음).
- 타입폭은 LP64(x86-64 Linux) 기준 — Windows LLP64(`long`=32) 는 미모델링,
  어긋나면 차분 게이트가 거부.
- "무엇이든 craft" 가 아니라 "검증 가능한 만큼만 craft" — N3 와 같은 방식.

## 🔗 연결된 시냅스 (Wiki Links)
- [[🌀 제어흐름·메모리 자가복제 — craft 가 루프/분기/스택을 배우다 (Stage N3)]]
- [[자가 복제 공작 루프 — craft-anything 두뇌 판 (clean-room)]]
- [[자가 종합 감사 — 4기준 기계 재감사와 부채 원장 (audit_brain)]]
