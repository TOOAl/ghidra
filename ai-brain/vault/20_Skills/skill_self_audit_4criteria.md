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
2. **master 미병합** — N·N1+N2·심화·종합감사·Windows 이식성·검증강화 6커밋
   (`6df25860`·`e1c57b38`·`cc3f32f8`·`8f0d857c`·`3555921f`·+v7.3.4)이 arena
   브랜치에 있고 master 미병합(PR#2 는 M단계까지).
3. **dependency-submission 워크플로 삭제** — dep-graph 는 repo admin 전용
   설정(PATCH 403, admin 없음). 복원법: Settings→Dependency graph 활성화 후
   `d4a629a8` yml 복구.
4. **craft_engine 한계** — 직선 스칼라 변환 가족만; 루프·메모리·점프는
   정직 skip. 일반목적 "무엇이든" 은 N3(SLM) 여정의 몫.
5. **SLM 브리지 dormant** — GGUF 미밴들(`models/` gitignore, 다운로드는 수동
   opt-in). 로컬 엔진(llama.cpp·ollama·LM Studio, 전부 127.0.0.1) 없으면
   grounded Synapse 폴백으로 동작 — 발명 0 이지만 일반목적 추론은 아님.
6. **산문 절대값 표류** — vault 가 자율 성장하면 산문 구멍 수·코사인 절대값이
   움직여요(현재 1장·0.137/0.08). **차분 불변식(코드 수유 전후 동일)은 항상
   성립**하지만 문서의 낡은 상수(476/4/0.083 등)는 스냅샷 값 — 살아있는
   두뇌 특성상 부채라기보다 설계.

## 🔗 연결된 시냅스 (Wiki Links)
- [[자가 치유 끈기 원장 — kill -9 를 견디는 퀘스트 기억 (quest_ledger)]]
- [[증거 사슬 다홉 추론 — 인용되거나 침묵하거나 (chain_reasoner)]]
- [[자가 복제 공작 루프 — craft-anything 두뇌 판 (clean-room)]]
