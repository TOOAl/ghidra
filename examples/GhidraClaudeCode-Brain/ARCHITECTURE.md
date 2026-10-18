# ARCHITECTURE — 무료 진화형 AI 두뇌 설계도

## 1. 설계 원칙 4가지

1.  **모델 불가지론 (Model-Agnostic)**: 어떤 LLM이든 같은 인터페이스로 호출. 미래 모델이 나와도 코드 수정 0.
2.  **도구 중심 (Tool-Centric)**: 지능은 모델보다 도구에 있다. Ghidra+REA 도구만 잘 만들면 약한 모델도 강해짐.
3.  **기억 우선 (Memory-First)**: 한 번 분석한 건 절대 잊지 않는다. Vector DB에 저장해 다음 분석에 재사용.
4.  **무료 기본 (Free by Default)**: 로컬 Ollama로 오프라인 완전 동작. 돈은 선택.

## 2. 컴포넌트 상세

### A. Model Adapter (`brain/model_adapter.py`)

모든 LLM 제공자를 OpenAI 호환 인터페이스로 통일.

```python
adapter = ModelAdapter.from_config("config/models.yaml")
# 내부에서:
# if provider == "ollama": call http://localhost:11434/v1/chat/completions
# if provider == "openrouter": call https://openrouter.ai/api/v1/...
# if provider == "anthropic": call anthropic SDK
# 반환은 항상 동일한 타입: {text, tool_calls}
```

지원 목록 (무료 우선):
- `ollama` — 로컬 무료 (qwen3, deepseek-r1, llama3.1, gemma3)
- `openrouter` — 무료 티어 모델들 (qwen/qwen3-32b:free, deepseek-r1:free 등)
- `groq` — 무료 초고속 추론
- `huggingface` — Inference API 무료
- `anthropic` / `openai` — 유료 옵션 (원할 때만)

### B. Agent Loop (`brain/agent.py` + `planner.py`)

Claude Code의 ReAct 루프를 그대로 차용하되, 계획 단계를 추가.

```
사용자 Task
  → Planner: "이 작업은 5단계로 나눌 수 있다" (Tree-of-Thought)
  → Agent Loop (최대 20턴):
      1. Reason: "지금까지 뭘 알았지? 다음에 뭘 해야 하지?"
      2. Act: Tool 호출 (Ghidra)
      3. Observe: 결과 받고 Memory에 저장
      4. Reflect: "목표에 가까워졌나?"
  → Evaluator: 100점 채점 + 보고서 생성
```

Planner는 고급 LLM일수록 잘함. 그래서 모델을 업그레이드하면 계획 능력만 자동으로 좋아짐.

### C. Tools (`tools/*.py` + `definitions.json`)

REA가 제공하는 읽기 도구 + 우리가 만든 쓰기 도구.

| Tool | 역할 | REA/Ghidra |
|---|---|---|
| `list_functions` | 함수 목록 | REA (읽기) |
| `decompile` | 의사코드 | REA (읽기) |
| `get_xrefs` | 호출 관계 | REA (읽기) |
| `list_strings` | 문자열 | REA (읽기) |
| `rename_function` | 이름 복구 | Ghidra Plugin (쓰기) |
| `set_comment` | 주석 | Ghidra Plugin (쓰기) |
| `search_memory` | 과거 기억 검색 | Memory (RAG) |

`definitions.json`은 MCP 스펙을 따름. LLM이 보는 도구 설명서.

### D. Memory (`memory/`)

3층 기억 구조:

1.  **Session Memory** (`session.jsonl`) — 이번 분석의 대화 로그. 가장 최신.
2.  **Vector Memory** (`vector_store.py` + ChromaDB) — 과거 모든 분석의 함수/버그 패턴. 유사도 검색.
3.  **Knowledge Graph** (`knowledge.py`) — "이 함수는 이 API를 호출하고, 이 취약점과 연결됨" 같은 관계.

예: 새로운 바이너리에서 `FUN_00401000`을 보면, Vector Memory에서 "아, 3개월 전 분석한 ○○ 악성코드의 C2 통신 함수랑 95% 유사"를 찾아줌.

### E. Skills (`skills/SKILL.md`)

REA의 SKILL.md 시스템을 그대로 차용. 에이전트가 시작할 때 읽는 "행동 강령".

```markdown
---
name: reverse-engineer-anything
description: 바이너리 분석 시 항상 증거와 함께 답하라
---

## 워크플로우
1. 먼저 list_functions로 전체 파악
2. decompile로 의심 함수 확인
3. get_xrefs로 호출 관계 추적
4. 마지막에 보고서 작성 (CONFIRMED/LIKELY/POSSIBLE 라벨 필수)
```

스킬 파일 하나 추가하면 에이전트가 새로운 행동을 배움. 예: `skills/unpack_upx.md`를 추가하면 UPX 패킹 해제 능력 생김.

## 3. 진화 시나리오

| 시간 | 새 LLM 출시 | 네가 할 일 | 결과 |
|---|---|---|---|
| 지금 | Qwen3-14B (무료) | `models.yaml: qwen3:14b` | 기본 분석 가능 |
| 3개월 뒤 | DeepSeek-R3 (무료) | `models.yaml: deepseek-r3:free` | 추론 능력 2배 |
| 6개월 뒤 | GPT-6 (유료) | `models.yaml: gpt-6` + API 키 | 최고 성능, 기존 기억 그대로 활용 |
| 1년 뒤 | 로컬 70B 모델이 무료 | `models.yaml: local-70b` | 오프라인 초고성능 |

코드는 그대로, 모델 이름만 바꿈. 두뇌(도구+기억+스킬)는 계속 쌓임.

## 4. 비용 0원 유지 전략

- 개발/테스트: Ollama 로컬 (0원, 무제한)
- 가끔 강한 추론 필요: OpenRouter 무료 모델 (0원, 일일 한도)
- 중요한 분석만: Groq 무료 티어 or 유료 모델 (선택)

## 5. 보안

- 분석 대상 바이너리는 절대 외부로 업로드 안 함 (Ghidra/REA는 로컬 실행)
- LLM API로 나가는 건 decompiled pseudocode 일부만 (민감 정보 필터링 가능)
- 완전 오프라인 원하면 Ollama만 쓰면 됨
