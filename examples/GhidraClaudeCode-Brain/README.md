# GhidraClaudeCode-Brain — 무료로 진화하는 나만의 AI 두뇌

> 목표: 앞으로 나올 모든 LLM의 추론·분석·계획 능력을 빨아들여 계속 성장하는, 나만의 Claude Code

비유: **레고 두뇌** — LLM은 갈아끼울 수 있는 CPU, Ghidra+REA는 손과 눈, Memory는 기억장치. CPU만 새 걸로 바꾸면 전체가 똑똑해짐.

## 핵심 철학: LLM에 종속되지 않기

미래의 GPT-6, Claude 5, Gemini 3, Qwen3, DeepSeek-R3가 나와도 **코드 한 줄 안 바꾸고** 흡수해야 함.

그래서 이 프로젝트는 이렇게 설계됨:

```
┌─────────────────────────────────────────────────────┐
│  너의 두뇌 (Brain) — 이게 핵심 자산                  │
│  - 추론 루프 (ReAct + Planning)                      │
│  - 기억 (Memory)                                     │
│  - 기술 (Skills)                                     │
│  - 도구 정의 (Tools = Ghidra+REA)                    │
├─────────────────────────────────────────────────────┤
│  모델 어댑터 (Model Adapter) — 교체 가능한 CPU 슬롯  │
│  Ollama(로컬 무료) / OpenRouter(무료 API) /           │
│  Groq / HuggingFace / Claude / OpenAI 모두 동일 인터페이스 │
└─────────────────────────────────────────────────────┘
```

**즉, 두뇌는 네가 소유하고, LLM은 빌려 쓰는 부품.**

## 왜 무료로 가능한가?

| 필요 요소 | 무료 해법 | 비고 |
|---|---|---|
| LLM 추론 | **Ollama** (로컬 완전 무료) + **OpenRouter/Groq 무료 티어** | Qwen3-32B, DeepSeek-R1, Llama-3.1-405B 등 무료 모델 수십 개 |
| Ghidra | NSA 무료 (Apache 2.0) | 이미 가짐 |
| REA | MIT 무료 | `npx rea-agents setup` |
| 기억장치 | ChromaDB / SQLite (로컬) | 무료 |
| 코드 실행 | 로컬 Python | 무료 |

나중에 돈 내고 싶은 최상위 모델이 생기면, `config/models.yaml`에서 모델 이름 한 줄만 바꾸면 됨.

## 아키텍처

```
                    ┌──────────────────────┐
                    │   사용자 (너)         │
                    │ "이 악성코드 분석해줘"│
                    └──────────┬───────────┘
                               │ 자연어
                    ┌──────────▼───────────┐
                    │  Brain (brain/agent.py) │
                    │  1. 계획 (Plan)         │
                    │  2. 추론 (Reason)      │
                    │  3. 도구 사용 (Act)    │
                    │  4. 기억 저장          │
                    └──────────┬───────────┘
                               │ Tool Call (MCP)
              ┌────────────────┼────────────────┐
              │                │                │
     ┌────────▼──────┐ ┌──────▼──────┐ ┌──────▼──────┐
     │ Ghidra (읽기) │ │ Ghidra 플러그인│ │ Memory     │
     │ REA Provider │ │ (쓰기: rename)│ │ (기억)     │
     │ list_functions│ │ set_comment   │ │ "작년에 본  │
     │ decompile     │ │ patch_bytes   │ │  악성코드와 │
     │ xrefs         │ │               │ │  유사도 91%"│
     └───────────────┘ └──────────────┘ └────────────┘
                               │
                    ┌──────────▼───────────┐
                    │ Model Adapter         │
                    │ - Ollama (로컬)       │
                    │ - OpenRouter (클라우드 무료) │
                    │ - Claude/OpenAI (유료 옵션)  │
                    └──────────────────────┘
```

## 폴더 구조

```
GhidraClaudeCode-Brain/
├── README.md            # 이 파일 (전체 지도)
├── ARCHITECTURE.md      # 상세 설계도
├── ROADMAP.md           # 4주 성장 로드맵
├── config/
│   ├── models.yaml      # LLM 교체 슬롯 — 여기만 바꾸면 진화
│   └── settings.yaml    # Ghidra 경로, Memory 설정
├── brain/
│   ├── agent.py         # 추론·계획·실행 루프 (두뇌 본체)
│   ├── model_adapter.py # 모든 LLM을 하나로 보이게 하는 어댑터
│   ├── planner.py       # 장기 계획 (Tree-of-Thought)
│   └── evaluator.py     # 스스로 채점하고 프롬프트 개선
├── tools/
│   ├── ghidra_read.py   # REA/Ghidra 읽기 도구
│   ├── ghidra_write.py  # 플러그인 쓰기 도구
│   └── definitions.json # MCP Tool 정의 (LLM이 보는 도구 목록)
├── memory/
│   ├── vector_store.py  # ChromaDB — 과거 분석 기억
│   ├── knowledge.py     # 함수 시그니처 지식 그래프
│   └── session.jsonl    # 매 분석 세션 로그 (자가학습 재료)
├── skills/
│   ├── SKILL.md         # REA 호환 스킬 정의 (에이전트가 읽는 설명서)
│   ├── analyze_malware.md
│   └── find_vuln.md
├── requirements.txt
└── run.py               # 한 줄 실행: python run.py --binary ./sample --task "..."
```

## 지금 바로 시작 (5분)

### 1) 무료 두뇌 설치

```bash
cd examples/GhidraClaudeCode-Brain

# 로컬 LLM (완전 무료, 오프라인) — 추천: Qwen3 14B
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen3:14b        # 또는 deepseek-r1:14b, llama3.1:8b
ollama serve &               # http://localhost:11434 에서 대기

# 또는 클라우드 무료 LLM (OpenRouter) — 가입 후 무료 키 발급
export OPENROUTER_API_KEY=sk-or-v1-...
# config/models.yaml 에서 provider: openrouter 로 변경
```

### 2) Ghidra + REA 연결 (이미 있으면 스킵)

```bash
export GHIDRA_INSTALL_DIR=/path/to/ghidra_12.1.4_PUBLIC
export JAVA_HOME=/path/to/jdk-21
npx rea-agents setup          # REA MCP 자동 등록
rea doctor --provider ghidra --json
```

### 3) 실행

```bash
pip install -r requirements.txt

# 예: 악성코드 분석 시키기
python run.py --binary samples/malware.exe --task "이 악성코드가 통신하는 C2 주소 찾아줘" --model qwen3:14b

# 예: 취약점 찾기
python run.py --binary samples/vuln_app --task "버퍼오버플로우 터지는 곳 찾아서 보고서 써줘" --provider openrouter
```

AI가 스스로 계획을 세우고, Ghidra로 함수를 뒤지고, 기억에서 비슷한 사례를 찾아, 마지막에 보고서까지 써준다.

## 진화 메커니즘 — 어떻게 계속 똑똑해지나?

1.  **모델 교체 진화**: 6개월 뒤 GPT-6 나오면 `config/models.yaml` 한 줄 변경. 두뇌 로직은 그대로인데 성능이 점프.
2.  **기억 진화**: 분석할 때마다 `memory/session.jsonl`에 자동 저장. 다음 분석 때 과거 기억을 RAG로 참조.
3.  **스킬 진화**: `skills/` 폴더에 `.md` 파일 하나 추가하면 에이전트가 새 능력 습득 (예: `unpack_packed_binary.md`).
4.  **자가 평가 진화**: `brain/evaluator.py`가 매 분석을 100점 만점으로 채점하고, 프롬프트를 자동 개선.

> 목표: **모델은 빌리고, 두뇌는 소유한다.**
