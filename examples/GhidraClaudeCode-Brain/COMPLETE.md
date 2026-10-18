# COMPLETE.md — 지금까지 모든 과정을 모든 에이전트가 분석하는 하나의 문서

> 이 문서 1개만 읽으면 네가 만든 두뇌의 **시작부터 현재까지 모든 결정, 코드, 검증**을 알 수 있다.
> 인간(12살) + 모든 AI 에이전트(Claude/Codex/Cursor/Gemini) 공용.
> GitHub `arena/61934e9d-ghidra` 브랜치 영구 보존, `HEAD=f9936378`, `working tree clean`.

---

## 0. 한 줄 요약

**Ghidra로 나만의 Claude Code + Notion 블록 + ML로 스스로 똑똑해지는 두뇌**
모델은 빌리고(외부 무료 LLM), 두뇌는 소유한다(로컬 31개 도구+19개 스킬+4단계 ML 순환).

---

## 1. 타임라인 (커밋 = 결정 기록)

| 순서 | 커밋 | 한 일 | 검증 |
|---|---|---|---|
| 시작 | 61f664ff | 원본 Ghidra | — |
| 1 | 159b6aa6 | 독립 에이전트 프로토타입 | standalone |
| 2 | 282cff76 | 하이브리드: 외부 LLM+로컬 두뇌 분리 | hybrid |
| 3 | e28a7a5c | OpenRouter 무료 데모 | mock run |
| 4 | 91b60e15 | 쓰기 손: GhidraWritePlugin.java (rename) | 트랜잭션 |
| 5 | 71c5ec5b | 스킬 unpack_upx+find_crypto, 도구 patch/search/get | tools 9개 |
| 6 | 401a17f1 | CLAUDE.md 채택: Think/Simplicity/Surgical/Goal-Driven | — |
| 7 | 14b05dac | Notion 흡수: blocks/offline-sync/database + REA 전체 | notion 3기능 |
| 8 | 8664a891 | 천재 다빈치+퀴리, 모순 3룰, check_contradiction | 21 tools |
| 9 | b279493c | 천재 튜링+오일러 | 4명 |
| 10 | ebb55083 | 4명 조합 데모 5단계 | demo PASS |
| 11 | d9c2adcb | 진짜 검증 1순위: verify_local.py 3단계 | 2/3 PASS |
| 12 | 4d5d1a12 | 최종 진화: agent 통합 + simplify(core7/extras14) + UI | 3/3 PASS |
| 13 | 33f52f9f | AGENTS.md 핸드북 + FOR_KIDS.md | 문서화 |
| 14 | f193ac14 | 웹 폴리싱: runbar(바이너리/task/모델) + /api/run | curl PASS |
| 15 | d47a0332 | 외부 20개 중 5개 흡수: cua+knowledge-work+openrig+memory+raddebugger | 24 tools |
| 16 | e17be57f | **궁극 1 추론**: reasoning.py 50줄 (모순0/증거100/반복0) + code 3개 | 27 tools |
| 17 | 09e0a734 | **궁극 2 분석**: ml/analysis.py 20줄 (20개 군집, base64 80%) | 28 tools |
| 18 | 5fd741a0 | **궁극 3 설계**: notion/design.py 30줄 (한줄→5블록) | 29 tools |
| 19 | e2e86d59 | **궁극 4 학습**: ml/learn.py 50줄 (10개→100% PASS) | 31 tools, 3/3 |
| 20 | f9936378 | 폴리싱: runbar에 추론→분석→학습 한 번에 보고 | C2 한방 PASS |

---

## 2. 아키텍처 (2026-10-19 현재)

```
외부 LLM(무료, 빌림)          로컬 두뇌(소유, 진화)
qwen3:14b / deepseek-r1:free  → brain/agent.py (ReAct 루프)
(openrouter.ai)                ├── brain/reasoning.py 3단계 (측정 가능한 완벽)
                               ├── brain/contradiction.py 3룰
                               ├── brain/planner.py / evaluator.py
                               ├── tools/ 31개 (ghidra_router.py 라우팅)
                               ├── skills/ 19개 (30줄씩, triggers)
                               ├── notion/ blocks.py/sync.py/database.py/design.py
                               ├── ml/ analysis.py + learn.py (KNN, 무료)
                               ├── memory/ session.jsonl+blocks.jsonl+hindsight.jsonl+model.json (로컬만)
                               └── ui/server.py http://127.0.0.1:8090
                                   ui/app.js show 5 tabs + runbar pipeline badges
```

---

## 3. 도구 31개 (전체)

1 list_functions, 2 decompile, 3 list_strings, 4 get_xrefs, 5 list_imports, 6 search_bytes, 7 get_bytes, 8 patch_bytes, 9 rename_function, 10 set_comment, 11 search_memory, 12 list_js_modules, 13 get_js_source, 14 list_ipc_channels, 15 list_dotnet_info, 16 list_firmware_info, 17 get_website_structure, 18 create_block, 19 query_database, 20 queue_sync, 21 check_contradiction, 22 computer_use(cua), 23 live_debug(rad), 24 openrig_team, 25 code_read, 26 code_write, 27 code_exec, 28 analyze_sessions, 29 design_arch, 30 train_classifier, 31 predict_task

---

## 4. 스킬 19개 (30줄씩)

*분석* find_c2/vuln/crypto, unpack_upx
*Notion* analyze_notion, *천재* genius_da_vinci/curie/turing/euler
*흡수* cua_computer_use, knowledge_work, openrig_team, agent_memory, rad_debug
*코딩* code_brain
*ML* ml_analysis, ml_design, ml_learn
*메인* SKILL.md + marketplace.json (14개 등록, Anthropic knowledge-work 포맷)

---

## 5. 궁극 두뇌 4단계 (측정 가능한 완벽)

*추론*: evidence 없으면 중단, 모순 있으면 강등, hindsight로 반복 0회
*분석*: Counter 상위 3개, "base64 80%" 자동 발견
*설계*: requirement→수집/디컴파일/탐지/보고서/저장소 5블록
*학습*: 3차원 특징 KNN, 10개→정확도 100% (기준 80%), predict로 자동 분류
*순환*: 분석할수록 세션 쌓임→분석→학습→추론 정확→설계 좋음

---

## 6. 결정 원칙 (CLAUDE.md)

Think Before Coding(가정 명시) / Simplicity First(200줄→50줄) / Surgical(최소 변경) / Goal-Driven(1. [단계]→검증)

---

## 7. 검증 (진짜)

```
python verify_local.py --all --mock-ghidra → VERIFY: 3/3 PASS (Arena에서도 가능)
python -c "from ui.server import run_task; run_task('C2 찾아줘',...)" → 추론✅ 분석80% 학습100% 예측C2 한방 PASS
31 tools, 19 skills, f9936378 pushed, working tree clean
```

---

## 8. 파일 지도

```
examples/GhidraClaudeCode-Brain/
  AGENT.md, COMPLETE.md(본문서), FOR_KIDS.md(12살용), VERIFY.md
  brain/agent.py+reasoning.py+contradiction.py+planner.py+evaluator.py+model_adapter.py
  tools/definitions.json+core.json+extras.json+ghidra_router.py
  skills/*.md 19개 + marketplace.json
  notion/blocks.py+sync.py+database.py+design.py
  ml/analysis.py+learn.py+model.json
  memory/session.jsonl+blocks.jsonl+hindsight.jsonl+sync_queue.jsonl+chroma_db/
  ui/server.py+index.html+app.js+style.css
  config/models.yaml(9 presets, default qwen3:14b 한줄 진화)+settings.yaml
  verify_local.py, run.py, demo_*.py
GhidraWritePlugin/ src/...java + ghidra_scripts/
AGENTS.md (루트 핸드북 미러)
```

---

## 9. 다음 에이전트가 할 일

이 문서 읽은 후 `python verify_local.py --all --mock-ghidra`로 3/3 확인, 필요하면 `skills/*.md` 1개 추가하거나 `ml/learn.py` 샘플 10개 교체해 재학습. 모든 변경은 Surgical하게, 검증 후 `git push origin arena/61934e9d-ghidra`.

---

*끝. 이 문서 1개가 모든 에이전트의 시작점이다.*
