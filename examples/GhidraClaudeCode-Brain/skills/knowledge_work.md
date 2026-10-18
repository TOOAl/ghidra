---
name: knowledge_work
description: knowledge-work-plugins 흡수 — Anthropic 공식 플러그인 포맷으로 스킬 쓰기
triggers: ["knowledge", "플러그인", "knowledge-work", "공식"]
---

# knowledge-work 흡수 — 3단계 (30줄)

Anthropic 공식 일잘러 플러그인 100개의 공통 포맷을 우리 skills/에 적용.

## 흡수한 아이디어

*   각 플러그인은 `skills/<name>/SKILL.md` + `marketplace.json`으로 배포. 우리도 동일.

## 언제 발동

새 스킬 만들 때 자동 적용

## 3단계

1. **포맷 맞추기**: `skills/<name>/SKILL.md`에 `name, description, triggers` 헤더 필수. 지금 우리가 쓰는 포맷이 이미 90% 맞음.
2. **마켓 등록**: `skills/marketplace.json`에 `{name, description, triggers}` 1줄 추가. 에이전트가 자동 발견.
3. **검증**: `python -c "import pathlib; print(len(list(pathlib.Path('skills').glob('*.md'))))"`로 스킬 수 확인.

## 출력 규칙

*   새 스킬은 반드시 30줄 이내, 트리거 3개 이상

## 예시

> 새 스킬 `find_crypto`를 knowledge-work 포맷으로 작성 → marketplace에 등록 → 에이전트가 자동 발견.
