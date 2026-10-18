---
name: code_brain
description: 일반 코딩 — 파일 읽고 쓰고 실행하기 (Claude Code처럼)
triggers: ["코딩", "code", "파일", "실행", "만들어줘"]
---

# 일반 코딩 흡수 — 3단계 (30줄)

리버싱 말고 일반 코딩도 되는 두뇌. Claude Code처럼 파일 3개로.

## 흡수한 아이디어

*   Claude Code는 read_file/write_file/bash 3개로 코딩. 우리도 동일.

## 언제 발동

"파일 만들어줘", "코딩해줘" 트리거 시

## 3단계

1. **읽기**: `code_read(path="src/app.js")`로 기존 코드 보기. 없으면 새로 만들기.
2. **쓰기**: `code_write(path="src/new.py", content="...")`로 코드 저장. 반드시 `reasoning.py`로 검증 후 저장.
3. **실행**: `code_exec(cmd="python src/new.py")`로 실행, 결과 확인. 실패하면 hindsight에 저장.

## 출력 규칙

*   모든 코드는 reason()으로 모순 0개 확인 후 저장

## 예시

> code_read → code_write → code_exec → 보고서 CONFIRMED
