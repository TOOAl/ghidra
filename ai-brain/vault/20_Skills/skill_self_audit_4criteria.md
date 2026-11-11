---
title: "자가 종합 감사 — 4기준 기계 재감사와 부채 원장 (audit_brain)"
category: "스킬·감사"
tags: [skill, audit, privacy, honesty, portability, debt-ledger]
created: ""
---

# 🔍 자가 종합 감사 — 4기준 기계 재감사와 부채 원장

## 💡 핵심 요약
"A→N1+N2 전체를 개인정보·무료·정직·두뇌 소유 4기준으로 재감사 + 미해결
부채 목록화." — 일회성 수동 주장이 아니라, 두뇌가 **자기 자신을 다시
감사**하는 재생산 가능 게이트로 만들었어요 (`tools/audit_brain.py`,
**15/15 그린**, exit-code 게이트). 자기 위치(`__file__`)에서 커밋 트리를
걷고, git 있으면 best-effort·없으면 파일시스템 폴백. 네트워크 없음.

## 🔩 4기준 검사 (audit_brain.py)
1. **개인정보** — 커밋 텍스트 전수 스캔(파일 수는 `audit_brain` 이 보고):
   하드 시크릿(AKIA·개인키·ghp_·sk-·AIza…) 0 · 개인 이메일 0 · 사용자
   홈경로(Linux `/home/<user>`·Windows 홈경로 리터럴) 0.
2. **무료** — 비-localhost URL 은 전부 **dormant 수동 다운로더**
   (`scripts/download_portable_slm.py`, `__main__` 가드·`--tier` 명시) 안에만,
   외부 호스트는 무료 GGUF(huggingface)뿐(유료 API 0), 그리고 그 다운로더를
   두뇌가 **import 안 함** = 자동 외부흐름 0.
3. **정직** — 환각방어·정직거부 코드 경로가 **실제 존재**: chain_reasoner
   `known:False`+부분사슬, slm_bridge "근거 없으면 모름" 고지, craft_engine
   일치율 기록, quest_ledger 예외 시 정직 `failed`.
4. **두뇌 소유** — 런타임 상태·무거운 바이너리 git 미유입 · 디스크 런타임
   산출물 gitignore 커버 · **이식성**(하드코딩 `/tmp` 런타임 경로 0,
   `/home/user` 절대경로 0).

## 🛠 감사 중 고친 실제 결함 (이식성)
`re_analyzer.py`·`ghidra_facts_pyghidra.py`·`verify_ghidra_facts.py` 가 런타임
스크래치를 `/tmp/…` 에 **하드코딩** → Windows(`start_windows.bat` 존재)엔
`/tmp` 가 없어 Ghidra 경로가 깨졌어요("외장하드에서 스스로 자란다" 소유
주장과 모순). 전부 `tempfile.gettempdir()` 로 교체 — Linux/macOS 에선
`gettempdir()==/tmp` 라 **행동 동일**, Windows 에선 `%TEMP%` 로 정상.
수정 후 verify 올 그린(exit 0)·회복력 32/32 유지로 회귀 없음 확인.
*(단, `self_evolving_forge.py` 의 `/tmp` 문자열은 위험호출 **검출 대상
콘텐츠**고, 주석의 `/tmp/l_probe` 는 측정 근거 기록이라 부채 아님.)*

## 📒 부채 원장 (정직 고지 — 미해결/한계)
1. **✅ Windows 오프라인 이식성 — 해결 (v7.3.3)** — win_amd64 wheel 밴들
   (`jdk4py-25.0.2.1-py3-none-win_amd64` 31MB·`jpype1-1.7.1-cp311-win_amd64`
   0.4MB, 둘 다 sha256 검증) + `re_analyzer.py` 플랫폼 인식(`_IS_WIN`: venv
   `Scripts\python.exe`·JDK PATH `os.pathsep`·`win_x86_64\decompile.exe`·
   `analyzeHeadless.bat`, 기본값은 Linux/macOS 행동 그대로) + Windows 부트스트랩
   `tools/fetch_ghidra_dist.ps1`(+`.bat` 래퍼 — vendor 휠 `--no-index` 오프라인
   설치, 안 맞으면 PyPI 무료 폴백) + `start_windows.bat` 논블로킹 사전점검.
   **잔여(정직 고지):** ⑴ 이 Linux 샌드박스엔 실제 Windows 호스트·pwsh 가
   없어(PowerShell 릴리스가 allow-list 밖 `objects.githubusercontent.com` 으로
   리다이렉트 → 바이너리 불가) .ps1 end-to-end 라이브 미검증 — 대신
   `tools/verify_windows_bootstrap.py`(**49/49 그린**, exit 게이트, v7.3.4)가
   오프라인 설치 가능성(vendor 휠 태그+의존 폐포를 Windows/cp311·Linux/cp311
   양쪽 기계 증명)·이진 재조립 알고리즘(합성 픽스처 실제 실행)·.ps1 구조
   불변식·.sh 단계 패리티를 재생산 가능하게 증명 → **첫 Windows 실행만이
   마지막 미목격 단계** ⑵ jpype1 벤더 휠은 cp311 태그라 Python 3.11 에서만
   오프라인 설치, 다른 파이썬은 PyPI(무료) 폴백.
2. **✅ master 병합 — 해결 (v7.3.5)** — PR #3 MERGED(merge commit `503f1163`,
   CI `Build Ghidra #3` pass 11m0s). N·N1+N2·심화·종합감사·Windows 이식성·
   검증강화·인수검토 7커밋 전부 origin/master 조상 확인. 부채 해소.
3. **dependency-submission 워크플로 삭제** — dep-graph 는 repo admin 전용
   설정(PATCH 403, admin 없음). 복원법: Settings→Dependency graph 활성화 후
   `d4a629a8` yml 복구.
4. **✅ craft_engine 제어흐름·메모리 — 해결 (v7.3.6, Stage N3)** — 직선 스칼라
   전용 한계를 넘어, **제어흐름+스택메모리 x86-64 부분집합 에뮬레이터**
   (`brain_engine/x86_cf_emu.py`: PC·flags ZF/SF/OF/CF·`[rbp±K]` 메모리·조건/
   무조건점프·bounded 루프(스텝캡)·lea) + **규칙 기반 C 부분집합→파이썬 합성기**
   (`brain_engine/c_synthesize.py`: 선언·대입·for/while·if/else·return·폭/부호
   인식). oracle 은 **gcc 네이티브 실행 ground truth 와 1446/1446 전수 일치**로
   기계 증명(루프 `sum_to`·분기 `classify`·스택 `with_local`·lea/rotate `rotl`·
   부분레지스터 `mix`). craft 는 두 경로(직선/제어흐름) 모두 **차분 검증 100%
   만 기록**. 게이트 `tools/test_n3_craft.py` **29/29 그린**(exit 코드).
   **잔여(정직 고지):** CALL(다른 함수)·복잡 addressing·캡 초과 루프는 계속
   정직 skip(발명 금지) — 일반목적 "무엇이든" 은 여전히 여정의 몫.
   *(당시 oracle 이 곱셈/나눗셈 가족에서 bail 하던 구멍은 → 부채⑦ Stage N4 에서 해결.)*
5. **SLM 브리지 — dormant 이지만 이제 실제 역할 있음 (v7.3.6, Stage N3)** —
   `synthesize_python()` 합성 oracle hook 추가: 로컬 엔진(llama.cpp·ollama·
   LM Studio, 전부 127.0.0.1) online 이면 디컴파일 C 의 clean-room 파이썬 합성을
   LLM 에 요청(정적 안전검증 + craft 차분 검증이 최종 게이트 → 환각 기록 구조적
   불가), offline(dormant) 면 **grounded 폴백으로 코드 발명을 정직 거부**
   (`source=None` → 규칙 기반 합성기 사용). GGUF 미밴들(`models/` gitignore,
   다운로드는 수동 opt-in)이라 이 샌드박스엔 dormant — 발명 0.
   **✅ online 분기 기계증명 (v7.3.6)**: `tools/test_n3_slm_online.py`(**13/13 그린**,
   exit 게이트)가 mock 로컬 LLM(OpenAI 호환, 127.0.0.1:8080, 프로세스 내 스레드·
   외부 네트워크 0)으로 online 경로를 실제로 띄워 증명 — ① online 탐지 ② 올바른
   합성→차분 100% ③ **환각(그럴듯하지만 틀린 `fn`)→정적 검증은 통과하나 차분
   게이트가 match<100% 로 잡아내 vault 기록 0건(발명 구조적 차단)** ④ unsafe
   출력(import/던더)→정적 거부 ⑤ 규칙 기반이 정직 실패하는 실함수 `dw`(do-while)
   에서 `synth_for` 가 SLM 을 상담→올바른 합성 100%(규칙 기반이 못 하던 것),
   환각(do-while 오역)은 33.51%<100% 거부, SLM 없으면 정직 skip. **잔여(정직
   고지):** 실제 GGUF 로컬 엔진으로 live LLM 합성은 미목격(엔진 미밴들) — 하지만
   online **코드 경로**와 **환각 방어 게이트**는 기계 증명됨.
6. **산문 절대값 표류** — vault 가 자율 성장하면 산문 구멍 수·코사인 절대값이
   움직여요(현재 1장·0.137/0.08). **차분 불변식(코드 수유 전후 동일)은 항상
   성립**하지만 문서의 낡은 상수(476/4/0.083 등)는 스냅샷 값 — 살아있는
   두뇌 특성상 부채라기보다 설계.
7. **✅ craft 곱셈·나눗셈 가족 — 해결 (v7.3.7, Stage N4)** — 부채④ 잔여 중
   "제수(나눗셈) 쓰는 함수 복제 불가" 구멍을 막았어요. oracle(`x86_cf_emu.py`)에
   **3-operand `IMUL`(magic reciprocal)·one-op `MUL`/`IMUL`(DX:AX)·`CDQ/CQO/CWD/
   CDQE/CBW`·`DIV`/`IDIV`(8/16/32/64, 0 방향 절삭, #DE 정직 bail)** 추가, 합성기
   (`c_synthesize.py`)에 **C-충실 절삭 `/`→`_tdiv`·`%`→`_tmod`**(파이썬 `//`·`%` 는
   음수에서 바닥 나눗셈이라 환각) 추가, 그리고 Ghidra x86-64(LP64) `long`/`ulong`
   =**64비트** 타입폭 오분류 수정. **기계증명**: gcc -O0 네이티브 실행 ground truth
   와 **11 함수 × 271 입력 전수 일치**(미지원 0) — signed/unsigned 상수 나눗셈·
   나머지(magic 3-op imul)·variable 제수(cdq;idiv / div)·제곱·64비트 곱셈. 게이트
   `tools/test_n4_muldiv.py` **51/51 그린**(exit 코드): oracle==네이티브(11)·
   합성==네이티브(9)·craft 차분 100%(9)·record 100%만 저장·절삭 단위 테이블·
   정직(vdiv skip / vmod 70.91% 거부 / 훼손 `x//3` 거부)·gcc 미방출 형태 6개
   독립 참조 검증. **핵심 발견**: gcc 는 상수 제수를 -O0 에서도 magic-number
   reciprocal 곱셈으로 컴파일(`CDQ;IDIV` 아님) → 상수 나눗셈 craft 의 열쇠는
   3-op IMUL. **잔여(정직 고지)**: ⑴ `cmov`(absv·clampv)·`switch`(점프테이블)는
   계속 정직 bail(N4 범위 밖) ⑵ one-op `MUL`/`IMUL`·`CQO`·64비트 `IDIV`·`CDQE`/
   `CWD` 는 gcc 가 단순 단일입력 함수에서 방출하지 않아 **네이티브 아닌 독립
   참조**로 증명(32비트 `CDQ;IDIV`/`DIV` 는 `vdiv`/`uvdiv` 네이티브 증명) ⑶ 합성기는
   부호 바꾸는 캐스트(`(int)uintVar`) 미모델링 → 그런 -O0 디컴파일(`vmod`)은 차분
   ゲ이트 정직 거부 ⑷ 타입폭 LP64 기준, Windows LLP64(`long`=32) 미모델링(어긋나면
   게이트 거부).

## 🔗 연결된 시냅스 (Wiki Links)
- [[자가 치유 끈기 원장 — kill -9 를 견디는 퀘스트 기억 (quest_ledger)]]
- [[증거 사슬 다홉 추론 — 인용되거나 침묵하거나 (chain_reasoner)]]
- [[자가 복제 공작 루프 — craft-anything 두뇌 판 (clean-room)]]
- [[🌀 제어흐름·메모리 자가복제 — craft 가 루프/분기/스택을 배우다 (Stage N3)]]
- [[🌀 곱셈·나눗셈 자가복제 — craft 가 magic reciprocal 과 절삭 나눗셈을 배우다 (Stage N4)]]
