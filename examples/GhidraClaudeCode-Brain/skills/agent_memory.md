---
name: agent_memory
description: Agent Memory Repo + Hindsight 흡수 — AI 기억을 더 똑똑하게
triggers: ["기억", "memory", "hindsight", "되돌아보기"]
---

# Agent Memory 흡수 — 3단계 (30줄)

Agent Memory Repo는 AI 기억 저장소, Hindsight는 "나중에 보니" 회고. 우리 memory/를 업그레이드.

## 흡수한 아이디어

*   기억을 `session.jsonl`만이 아니라, `hindsight.jsonl`에 "당시엔 몰랐지만 지금 보니"를 별도 저장.

## 언제 발동

분석 후 자동

## 3단계

1. **저장**: `memory/session.jsonl`에 이번 분석 저장 (기존)
2. **회고**: 1시간 후 `hindsight.jsonl`에 "Hindsight: 당시 C2를 LIKELY라 했지만, 지금 보니 xrefs 2개 더 있어 CONFIRMED" 추가. `search_memory`가 둘 다 검색.
3. **재활용**: 다음 분석 시 `search_memory`가 session + hindsight 둘 다 찾아 재활용.

## 출력 규칙

*   보고서 후 `hindsight` 블록 1개 자동 생성 (나중에 보니)

## 예시

> Hindsight: 지난 C2 분석은 import 1개로 LIKELY였으나, 오늘 list_imports 3개로 CONFIRMED로 승격.
