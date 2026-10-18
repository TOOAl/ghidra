---
name: openrig_team
description: openrig 흡수 — Claude Code 여러 명이 팀으로 일하기
triggers: ["openrig", "팀", "team", "역할", "협업"]
---

# openrig 흡수 — 3단계 (30줄)

openrig는 Claude Code, Codex, Pi가 팀(역할+공유 컨텍스트)으로 일한다. 우리 천재 4명을 팀으로.

## 흡수한 아이디어

*   각 에이전트에 역할(owner)과 공유 컨텍스트. 우리도 다빈치=관찰, 퀴리=측정, 튜링=해독, 오일러=일반화로 역할 분담.

## 언제 발동

"팀으로 해줘", "역할 나눠줘" 트리거 시

## 3단계

1. **역할 배정**: `openrig_team(task="C2 분석")` → 다빈치(관찰), 퀴리(측정), 튜링(형식화), 오일러(일반화) 4 역할 생성.
2. **공유 컨텍스트**: `memory/blocks.jsonl`을 팀 공용 칠판으로. 각 천재가 블록 1개씩 추가.
3. **합의**: 4명 결과를 `check_contradiction`으로 교차 검증, 3명 이상 동의한 것만 CONFIRMED.

## 출력 규칙

*   보고서 마지막에 `openrig 팀 합의: 4/4 동의 → CONFIRMED` 1문장 필수

## 예시

> openrig 팀: 다빈치(껍질), 퀴리(7.2), 튜링(S1→S2), 오일러(f(x)) → 4명 합의로 CONFIRMED.
