---
name: cua_computer_use
description: cua 흡수 — 컴퓨터 화면을 AI가 직접 클릭/타이핑하는 스킬
triggers: ["cua", "컴퓨터 조종", "클릭", "computer use", "화면"]
---

# cua 흡수 — 3단계 (30줄)

cua는 오픈소스 컴퓨터 조종 로봇 팔. 우리 웹 UI(Notion처럼)를 AI가 직접 만지게 한다.

## 흡수한 아이디어

*   `cua`는 운영체제 드라이버로 화면을 보고, 마우스로 클릭한다. 우리도 `computer_use` 도구로 Ghidra 화면을 조종.

## 언제 발동

"컴퓨터 조종해줘", "클릭해줘" 트리거 시

## 3단계

1. **보기 (See)**: `computer_use(action=screenshot)`로 현재 Ghidra/웹 UI 캡처. "어디에 버튼 있나?" 관찰.
2. **조종 (Act)**: `computer_use(action=click, x=320, y=240)`로 클릭 or `type`으로 입력. 예: Notion 블록 편집 버튼 클릭.
3. **확인 (Verify)**: 다시 screenshot 찍어 바뀌었는지 확인. 안 바뀌면 `check_contradiction`으로 모순 검사.

## 출력 규칙

*   보고서에 `cua 보기:` 스크린샷 1장 언급, `cua 조종:` 클릭 1개 필수

## 예시

> cua 보기: Ghidra 함수 목록 스크린샷.
> cua 조종: (320,240) rename 버튼 클릭 → FUN_00401000 → decrypt_config.
