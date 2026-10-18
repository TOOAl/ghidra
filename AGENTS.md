# AGENTS.md — GhidraClaudeCode-Brain Agent Handbook

> 모든 에이전트(Claude Code, Codex, Cursor, Gemini CLI 등)가 읽는 파일.
> 이 문서 하나만 읽으면 지금까지 만든 두뇌를 이해하고, 로컬에서 바로 실행할 수 있다.
> 언어: 한국어(사용자) + 영어(도구/코드) 혼합 — 에이전트는 둘 다 읽는다.

## 0. 한눈 요약

*   **이름**: GhidraClaudeCode-Brain — 무료로 진화하는 나만의 Claude Code
*   **철학**: 모델은 빌리고(외부 LLM 무료), 두뇌는 소유한다(로컬 도구+기억+스킬)
*   **위치**: `examples/GhidraClaudeCode-Brain/` (GitHub `arena/61934e9d-ghidra` 브랜치)
*   **비용**: 0원 기본 (Ollama 로컬 or OpenRouter Free `qwen/qwen3-32b:free`)
*   **상태**: Arena에서 최종 진화 완료 → 로컬 `git clone` 준비 완료

## 1. 아키텍처

```
외부 LLM(무료)  ──API──▶  로컬 Brain (brain/agent.py, ReAct 루프)
  qwen3-32b:free            ├── 도구: Ghidra+REA (읽기) + WritePlugin (쓰기)
  deepseek-r1:free          ├── 기억: memory/*.jsonl + chroma_db (로컬 영구)
                            ├── 스킬: skills/*.md (10개)
                            ├── 천재 4명: 다빈치/퀴리/튜링/오일러 (각 30줄)
                            └── UI: ui/server.py → http://127.0.0.1:8090
```

## 2. 디렉토리

```
GhidraClaudeCode-Brain/
├── CLAUDE.md              # 작업 가이드 (Think Before Coding 등 4원칙)
├── AGENT.md               # 이 파일 (에이전트 핸드북)
├── VERIFY.md              # 진짜 검증 3단계
├── README.md              # 사용자용
├── ARCHITECTURE*.md       # 설계도
├── config/models.yaml     # 모델 교체 슬롯 (한 줄 변경으로 진화)
├── config/settings.yaml   # Ghidra, Memory 설정
├── brain/                 # 두뇌 본체
│   ├── agent.py           # ReAct + 천재 주입 + 모순검사 + 블록저장
│   ├── model_adapter.py   # ollama/openrouter/groq/anthropic 통합
│   ├── planner.py         # 작업 3~5단계 계획
│   ├── evaluator.py       # 100점 자체 채점
│   └── contradiction.py   # 모순 3룰 (C2/rename/patch)
├── tools/                 # 도구 정의
│   ├── definitions.json   # 21개 도구 (MCP)
│   ├── core.json          # 핵심 7개 (기본)
│   ├── extras.json        # 나머지 14개
│   └── ghidra_router.py   # REA(mock) + WritePlugin + Memory 라우터
├── skills/                # 스킬 10개
│   ├── SKILL.md           # 메인 행동 강령
│   ├── find_c2.md, find_vuln.md, find_crypto.md, unpack_upx.md
│   ├── analyze_notion.md  # Notion 3기능 흡수
│   └── genius_*.md         # 다빈치/퀴리/튜링/오일러 각 30줄
├── notion/                # Notion 흡수 3기능
│   ├── blocks.py          # 블록 편집 (Notion block.ts 재구현)
│   ├── sync.py            # 오프라인 큐 (Notion sync 재구현)
│   └── database.py        # DB 조회 (Notion DB 재구현)
├── memory/                # 로컬 영구 기억 (외부로 안 나감)
│   ├── session.jsonl      # 모든 분석 세션
│   ├── blocks.jsonl       # 블록
│   ├── sync_queue.jsonl   # 오프라인 큐
│   └── chroma_db/         # Vector DB
├── ui/                    # Notion+Obsidian UI (로컬 전용)
│   ├── index.html, style.css, app.js
│   └── server.py          # http://127.0.0.1:8090
├── verify_local.py        # 진짜 검증 3단계
├── demo_*.py              # 데모 3개
└── run.py                 # 한 줄 실행

GhidraWritePlugin/          # Ghidra 쓰기 손 (별도)
├── src/.../GhidraWritePlugin.java      # rename 등 트랜잭션
├── src/.../WriteHttpServer.java        # 127.0.0.1:8089 8개 엔드포인트
└── ghidra_scripts/RenameWithLLM.py    # 빌드 없이 테스트
```

## 3. 도구 21개

*코어 7* (기본): `list_functions`, `decompile`, `list_strings`, `get_xrefs`, `rename_function`, `set_comment`, `search_memory`
*엑스트라 14*: `list_imports`, `search_bytes`, `get_bytes`, `patch_bytes`, `list_js_modules`, `get_js_source`, `list_ipc_channels`, `list_dotnet_info`, `list_firmware_info`, `get_website_structure`, `create_block`, `query_database`, `queue_sync`, `check_contradiction`

## 4. 스킬 10개

*   `find_c2`, `find_vuln`, `find_crypto`, `unpack_upx` — 분석
*   `analyze_notion` — Notion 블록/동기화/DB
*   `genius_da_vinci` (관찰→스케치→연결), `genius_curie` (측정→반복→실패로그), `genius_turing` (형식화→해독→모방), `genius_euler` (기호→일반화→우아한 계산)

## 5. 천재 + 모순

*   천재 4명 각 30줄, task에 "다빈치/퀴리/튜링/오일러" 또는 "4명 조합" 있으면 자동 주입
*   모순 3룰: C2_claim_without_string(high→LIKELY), rename_without_function(medium→POSSIBLE), patch_without_original(medium→POSSIBLE) — 보고서 전 자동 검사

## 6. 메모: 어디에 저장?

*   코드: GitHub `arena/61934e9d-ghidra` 브랜치 (영구 백업)
*   기억: `memory/*.jsonl` + `chroma_db` 로컬에만 (외부로 안 나감)
*   샌드박스 `/home/user/ghidra/`는 임시 — GitHub이 진짜 저장소

## 7. 검증 (Goal-Driven)

```bash
python verify_local.py --all --mock-ghidra  # Arena에서 3/3 PASS
# step1 list_js_modules 7개 PASS
# step2 rename_function mock PASS
# step3 check_contradiction 1개 강등 PASS
python demo_4genius.py       # 4명 조합 5단계 PASS
python notion/blocks.py --add "test" && python notion/database.py --filter qwen  # Notion 3기능 PASS
```

## 8. 로컬 실행 (에이전트용)

```bash
git clone -b arena/61934e9d-ghidra https://github.com/TOOAl/ghidra.git
cd ghidra/examples/GhidraClaudeCode-Brain
pip install -r requirements.txt
export OPENROUTER_API_KEY=sk-or-v1-...  # https://openrouter.ai/settings/keys 무료
python run.py --binary ./sample --task "C2 찾아줘" --preset openrouter_free_generic
python ui/server.py  # http://127.0.0.1:8090
```

## 9. 진화

*   모델 교체: `config/models.yaml` 한 줄 변경
*   스킬 추가: `skills/*.md` 1개 추가
*   도구 추가: `tools/definitions.json` + `ghidra_router.py` mock

## 10. 규칙 (CLAUDE.md 요약)

*   Think Before Coding: 가정 명시, 여러 해석이면 제시
*   Simplicity First: 최소 코드, 200줄이면 50줄로
*   Surgical: 꼭 필요한 것만, 기존 스타일 유지
*   Goal-Driven: `1. [단계] → 검증: [방법]` 형태
