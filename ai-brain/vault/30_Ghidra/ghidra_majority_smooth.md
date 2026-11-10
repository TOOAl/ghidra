---
title: "역공학 해부 도감 — 🗳️ 3연속 다수결 스무더"
category: "Ghidra·역공학"
tags: [Ghidra, 역공학해부, 설계도번역, majority_smooth]
created: "2026-11-10 14:42 UTC"
---

# 역공학 해부 도감 — 🗳️ 3연속 다수결 스무더

#Ghidra #역공학해부 #설계도번역 #majority_smooth

## 💡 핵심 요약
`dream_fragment_majority.bin` 바이너리를 분해해 기계어 주소 종속성을 걷어내고 핵심 원리 공식 `out[i] = 1 if (bits[i-1] + bits[i] + bits[i+1]) >= 2 else 0 (경계는 복제)` 를 추출했습니다.

## 📌 주요 포인트
- 해부 대상 파일: `dream_fragment_majority.bin`
- 추출 핵심 공식: `out[i] = 1 if (bits[i-1] + bits[i] + bits[i+1]) >= 2 else 0 (경계는 복제)`
- 멘토 성좌 감수: 튜링, 파인만

## 🔗 연결된 시냅스 (Wiki Links)
- [[자가 진화 스킬 카트리지 — majority_smooth]]
- [[Ghidra 헤드리스 바이너리 분석 파이프라인]]
- [[역공학 해부 도감 — 🎚️ 데드존 양자화기]]
- [[자가 진화 스킬 카트리지 — deadzone_quant]]
- [[역공학 해부 도감 — 🔁 델타 흐름 압축기]]
- [[자가 진화 스킬 카트리지 — delta_encode]]
- [[역공학 해부 도감 — 🛰️ 수 패리티 수호기]]
- [[자가 진화 스킬 카트리지 — parity_guard]]
- [[역공학 해부 도감 — 🧩 니블 팩커 (4비트 쌍수납 저장소)]]
- [[자가 진화 스킬 카트리지 — pack_nibbles]]
- [[역공학 해부 도감 — 🐡 복어 독(위험 명령) 혼입 압축기 (보안 제거 실습)]]
- [[자가 진화 스킬 카트리지 — compress_rle_safe]]
- [[역공학 해부 도감 — 🔐 XOR-회전 금고 해독기 (ELF64 x86-64)]]
- [[자가 진화 스킬 카트리지 — transform_payload]]
- [[Ghidra 헤드리스와 로컬 AI 역공학 결합]]
- [[역공학 해부 도감 — 🛡️ 8비트 합 체크섬 파수꾼]]
- [[자가 진화 스킬 카트리지 — checksum_guard]]
