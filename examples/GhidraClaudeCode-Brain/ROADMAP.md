# ROADMAP — 4주 완성 로드맵

## Week 0 — 오늘 (Day 1): MVP 가동

- [ ] `config/models.yaml` 작성 (Ollama qwen3:14b 기본)
- [ ] `brain/model_adapter.py` 완성 (Ollama + OpenRouter 어댑터)
- [ ] `tools/definitions.json` 작성 (REA 8개 도구)
- [ ] `run.py`로 바이너리 1개 분석 성공
- 목표: "main 함수 뭐해?" 질문에 답하는 데모

## Week 1: 읽기+쓰기 완성

- [ ] Ghidra 플러그인 쓰기 도구 2개 추가 (`rename_function`, `set_comment`)
- [ ] REA `rea doctor --provider ghidra` 통과
- [ ] Claude Code에서 `npx rea-agents`로 Ghidra 제어 확인
- 목표: AI가 스스로 함수 이름 고치고 주석 다는 것

## Week 2: 기억 장착 (Memory)

- [ ] `memory/vector_store.py` — ChromaDB 설치 + 함수 임베딩 저장
- [ ] `search_memory` Tool 추가
- [ ] 과거 분석 10개 넣고 유사 함수 검색 테스트
- 목표: "이 함수 전에 본 적 있는데, 그때는 뭐였지?" 기억하는 AI

## Week 3: 스킬 & 계획 (Planning)

- [ ] `brain/planner.py` — 작업을 3~5단계로 나누는 플래너
- [ ] `skills/` 폴더 — `find_c2.md`, `find_vuln.md` 스킬 2개 작성
- [ ] `brain/evaluator.py` — 분석 결과 100점 채점
- 목표: "C2 찾아줘" 하면 스스로 계획 세워서 10턴 안에 보고서 쓰는 AI

## Week 4: 진화 루프

- [ ] `config/models.yaml`에서 모델 교체 테스트 (qwen3 → deepseek-r1 → gpt-4o-mini 무료)
- [ ] 세션 로그로 프롬프트 자동 개선 실험
- [ ] GitHub README + 데모 영상
- 목표: 모델만 바꿔도 성능 올라가는 것 증명

---

## 매일 30분 루틴

1.  Ollama 로컬 모델로 테스트 (0원)
2.  안 되면 OpenRouter 무료 모델로 재시도
3.  성공한 분석은 `memory/session.jsonl`에 저장
4.  실패한 건 `skills/`에 교훈으로 기록

1개월 뒤 네 두뇌는 모델과 상관없이 계속 남는다.
