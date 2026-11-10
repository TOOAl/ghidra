---
title: "역공학 해부 도감 — 🧩 니블 팩커 (4비트 쌍수납 저장소)"
category: "Ghidra·역공학"
tags: [Ghidra, 역공학해부, 설계도번역, pack_nibbles]
created: "2026-11-10 13:44 UTC"
---

# 역공학 해부 도감 — 🧩 니블 팩커 (4비트 쌍수납 저장소)

#Ghidra #역공학해부 #설계도번역 #pack_nibbles

## 💡 핵심 요약
`dream_fragment_nibble_pack.bin` 바이너리를 분해해 기계어 주소 종속성을 걷어내고 핵심 원리 공식 `out[j] = ((v[2j] & 0x0F) << 4) | (v[2j+1] & 0x0F 또는 0)` 를 추출했습니다.

## 📌 주요 포인트
- 해부 대상 파일: `dream_fragment_nibble_pack.bin`
- 추출 핵심 공식: `out[j] = ((v[2j] & 0x0F) << 4) | (v[2j+1] & 0x0F 또는 0)`
- 멘토 성좌 감수: 클로드 섀넌, 폰 노이만

## 🔗 연결된 시냅스 (Wiki Links)
- [[자가 진화 스킬 카트리지 — pack_nibbles]]
- [[Ghidra 헤드리스 바이너리 분석 파이프라인]]
- [[역공학 해부 도감 — 🛰️ 수 패리티 수호기]]
- [[역공학 해부 도감 — 🐡 복어 독(위험 명령) 혼입 압축기 (보안 제거 실습)]]
- [[역공학 해부 도감 — 🔐 XOR-회전 금고 해독기 (ELF64 x86-64)]]
- [[역공학 해부 도감 — 🔁 델타 흐름 압축기]]
- [[자가 진화 스킬 카트리지 — parity_guard]]
- [[자가 진화 스킬 카트리지 — compress_rle_safe]]
- [[자가 진화 스킬 카트리지 — transform_payload]]
- [[Ghidra 헤드리스와 로컬 AI 역공학 결합]]
