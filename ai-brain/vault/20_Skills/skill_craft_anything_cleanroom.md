---
title: "자가 복제 공작 루프 — craft-anything 두뇌 판 (clean-room)"
category: "스킬·자가복제"
tags: [skill, craft, clean-room, ghidra]
created: ""
---

# 🛠 자가 복제 공작 루프 — craft-anything 두뇌 판

## 💡 핵심 요약
"원본을 실제 검사 도구로 분석하고, 나만의 버전을 만들고, 원본과 비교하며
다듬는다" — storytold/craft-anything(MIT OR Apache-2.0)의 루프를 **외부
모델 없이** 두뇌 자신의 것으로 재주조했어요. 원본 엔진의 빌더는 외부 코딩
에이전트지만, 우리 빌더와 오라클은 전부 소유예요.

## 🔩 세 단계 (brain_engine/craft_engine.py)
1. **검사**: Ghidra(PyGhidra) 디컴파일 C + objdump 명령 텍스트
2. **제작**: 디컴파일 C 반환식을 폭-감싼 산술(_W)로 파싱 → 파이썬 변환 합성
   (CONCAT22·rot·xor·add 지원, 입력 식별자는 첫 입력 레지스터만 x)
3. **비교**: **원본 바이트를 실행하는 소형 x86-64 에뮬레이터**와 차분 테스트
   — 바이트 함수는 256 전수, 그 외 1024 벡터. **100% 만 vault 에 기록**
   (record), 미달성은 발명하지 않고 match% 와 불일치 목록으로 보고.

## 📈 실측
- specimen_xor_vault.elf: FUN_00400078·entry — 256 전수 ×2 **100%**
- specimen_crc16_packet.exe: entry — 1024 벡터 **100%**
- 루프형 C(puffer)는 정직하게 skip ("C 반환식 파싱 불가")
- 라이브: `POST /api/remedy {"action":"craft","binary":…}` → vault 노트 3장

## 🧭 한계 (정직 고지)
직선 스칼라 변환 가족에 한정 — 점프·메모리·루프는 에뮬레이터가 지원 밖으로
표시하고 건너뛰어요. 일반 목적 "무엇이든" 은 N3(SLM) 여정의 몫.

## 🔗 연결된 시냅스 (Wiki Links)
- [[Ghidra 헤드리스와 로컬 AI 역공학 결합]]
- [[역공학 해부 도감 — 🔐 XOR-회전 금고 해독기 (ELF64 x86-64)]]
- [[자가 치유 끈기 원장 — kill -9 를 견디는 퀘스트 기억 (quest_ledger)]]
