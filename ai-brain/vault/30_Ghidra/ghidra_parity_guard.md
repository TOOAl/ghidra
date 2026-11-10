---
title: "역공학 해부 도감 — 🛰️ 수 패리티 수호기"
category: "Ghidra·역공학"
tags: [Ghidra, 역공학해부, 설계도번역, parity_guard]
created: "2026-11-10 13:59 UTC"
---

# 역공학 해부 도감 — 🛰️ 수 패리티 수호기

#Ghidra #역공학해부 #설계도번역 #parity_guard

## 💡 핵심 요약
`dream_fragment_parity_guard.bin` 바이너리를 분해해 기계어 주소 종속성을 걷어내고 핵심 원리 공식 `guard[i] = bin(b & 0xFF).count('1') % 2` 를 추출했습니다.

## 📌 주요 포인트
- 해부 대상 파일: `dream_fragment_parity_guard.bin`
- 추출 핵심 공식: `guard[i] = bin(b & 0xFF).count('1') % 2`
- 멘토 성좌 감수: 리처드 해밍, 클로드 섀넌

## 🔗 연결된 시냅스 (Wiki Links)
- [[자가 진화 스킬 카트리지 — parity_guard]]
- [[Ghidra 헤드리스 바이너리 분석 파이프라인]]
