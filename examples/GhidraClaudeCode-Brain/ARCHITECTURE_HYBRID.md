# ARCHITECTURE_HYBRID — 외부 LLM(무료) + 로컬 두뇌

> 네가 원한 변형: **모델은 외부에서 무료로 빌리고, 도구+기억+스킬은 내 로컬에 저장**

## 가능? — 응, 이게 정석이야

지금 만든 `GhidraClaudeCode-Brain`은 원래 이 하이브리드를 위해 설계됐어.

```
┌─────────────────────────────────────────────────────────────┐
│  외부 (무료) — 추론만 빌림                                   │
│  Arena Agent / OpenRouter(free) / Groq(free) / HF Inference │
│  역할: 생각하기 (Reasoning, Planning) — 두뇌의 CPU           │
└──────────────────────┬──────────────────────────────────────┘
                       │ API 호출 (인터넷)
                       │ 나가는 것: decompiled 코드 조각 + 질문
                       │ 못 나가는 것: 원본 바이너리, 전체 DB
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  로컬 (내 컴퓨터) — 영구 자산                                │
│  ① 도구: Ghidra + REA (읽기) + 플러그인(쓰기)                 │
│  ② 기억: memory/chroma_db + session.jsonl (Vector DB)       │
│  ③ 스킬: skills/*.md (나만의 노하우)                         │
│  ④ 실행기: brain/agent.py (ReAct 루프) — 네가 소유             │
└─────────────────────────────────────────────────────────────┘
```

**핵심: 루프를 돌리는 주체는 로컬이야. 외부 LLM은 "생각 자문"만 해줘.**

```python
# 로컬에서 도는 루프 (brain/agent.py)
while not done:
    생각 = 외부_LLM에게_물어보기("다음에 뭘 해야 할까?", 도구목록, 지금까지_결과)
    결과 = 로컬_Ghidra로_실행(생각.도구)
    기억에_저장(결과)   # ← 이건 로컬에만 남음
```

그래서 바이너리 원본은 절대 외부로 안 나가고, LLM이 바뀌어도 기억은 그대로 누적돼.

## 두 가지 하이브리드 패턴

| 패턴 | 누가 운전? | 장점 | 추천 |
|---|---|---|---|
| **A. 로컬 운전 + 외부 두뇌 (추천)** | 로컬 Python이 루프, 외부 LLM에 API로 질문 | 간단, 안전, 무료. 지금 구조 그대로 | ✅ 네가 원하는 것 |
| **B. 외부 운전 + 로컬 도구** | Arena 같은 외부 에이전트가 로컬 MCP 서버에 접속 | Arena 웹 UI에서 바로 쓰기 | 터널 필요, 복잡 |

**패턴 A가 답이야.** 네 PC에서 `python run.py`가 루프를 돌고, 생각만 `https://api.openrouter.ai` 같은 무료 API에 물어보는 거.

## 왜 Arena Agent 모드처럼 쓸 수 있어?

Arena, OpenRouter, Groq, HuggingFace 모두 **OpenAI 호환 API**를 제공해.
즉, 우리 `brain/model_adapter.py`는 이미 Arena를 지원해.

```yaml
# config/models.yaml 에 추가된 프리셋
arena_free:
  provider: openai_compatible   # 어떤 외부 LLM이든 이 타입
  model: arena-large            # Arena가 주는 모델 이름
  base_url: https://arena.ai/api/v1  # 예시 — 실제 Arena API 주소로 교체
  api_key_env: ARENA_API_KEY
```

실제 무료로 쓸 수 있는 외부 LLM 예시:

| 외부 LLM | 비용 | 모델 예시 | API 주소 |
|---|---|---|---|
| **OpenRouter Free** | 0원 | qwen3-32b:free, deepseek-r1:free | openrouter.ai/api/v1 |
| **Groq Free** | 0원 | llama-3.3-70b | api.groq.com/openai/v1 |
| **HuggingFace Inference** | 0원 | Qwen2.5-Coder-32B | api-inference.huggingface.co |
| **Arena (네가 쓰는 것)** | 0원 | Arena 제공 모델 | Arena API (OpenAI 호환) |

모두 `base_url`과 `model`만 바꾸면 즉시 교체 가능.

## 프라이버시: 뭐가 외부로 나가?

- **나가는 것**: `decompile("FUN_00401000")` 결과 같은 의사코드 조각 + "이 함수 뭐야?" 질문
- **안 나가는 것**: 원본 바이너리 전체, Ghidra 프로젝트 DB, `memory/chroma_db` 전체

민감하면 `brain/agent.py`에 필터 한 줄 추가하면 됨:
```python
# 외부로 보내기 전 민감 문자열 마스킹
code = code.replace("my_secret_key", "***")
```

완전 오프라인 원하면 `preset: local_qwen3`로 바꾸면 외부 호출 0번.

## 비용 0원 유지 전략

1. 평소: 로컬 Ollama (`qwen3:14b`) — 0원, 무제한, 오프라인
2. 어려운 추론 필요: OpenRouter Free 모델 — 0원, 일일 한도 내 무료
3. 정말 중요한 분석: 그때만 유료 모델 (선택)

외부 LLM이 무료인 한, **네 로컬 두뇌는 공짜로 계속 진화**해.

## 다음 단계

1. `config/models.yaml`에 `arena`/`openrouter` 프리셋 추가 — 완료
2. `brain/model_adapter.py`에 `openai_compatible` 범용 프로바이더 추가 — 완료
3. `python run.py --preset arena_free --binary ...` 로 테스트
4. 필요하면 `memory/`를 암호화해서 백업 — 네 두뇌는 네 디스크에만 존재
