---
name: ml_analysis
description: ML 분석 — 20개 분석에서 패턴 스스로 찾기
triggers: ["분석", "analysis", "패턴", "통계", "ml"]
---

# ML 분석 흡수 — 3단계 (30줄)

20개 분석을 모아서 "base64 80%" 같은 인사이트를 두뇌가 스스로 찾아.

## 언제 발동

세션 20개 쌓이면 자동, 또는 "분석해줘" 트리거

## 3단계

1. **모으기**: `ml/analysis.py`가 `memory/session.jsonl` 최근 20개 읽기. 도구 사용 횟수 세기.
2. **찾기**: `Counter`로 상위 도구 3개 찾기. 예: list_strings 15번 → "base64 패턴 80%".
3. **저장**: 인사이트를 블록 1개로 저장. 다음 추론 때 `search_memory`가 활용.

## 출력 규칙

*   보고서에 `분석 인사이트:` 1문장 필수

## 예시

> 분석 인사이트: 20개 중 16개가 list_strings 사용 → base64 패턴 80%
