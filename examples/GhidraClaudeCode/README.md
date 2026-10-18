# GhidraClaudeCode — 나만의 Claude Code를 Ghidra로 만들기

> Ghidra를 백엔드로 하는 리버스 엔지니어링 전용 AI 에이전트 프로토타입

Claude Code가 소스코드 개발에서 `파일 읽기 → 수정 → 빌드 → 테스트` 루프를 자동화하듯,
**GhidraClaudeCode는 바이너리 분석에서 `디컴파일 → 분석 → 이름 복구 → 주석 → 패치` 루프를 자동화**합니다.

## 아키텍처

```
┌─────────────────────────────────────────────────────────┐
│  Claude Code (터미널)  ↔  사용자 자연어 프롬프트         │
└──────────────────────┬──────────────────────────────────┘
                       │ MCP (Model Context Protocol)
                       ▼
┌─────────────────────────────────────────────────────────┐
│  Ghidra MCP Server / PyGhidra Agent (Python)           │
│  - Tool 정의: decompile, list_functions, rename, etc.  │
│  - Agent Loop: ReAct (Reason + Act)                    │
└──────────────────────┬──────────────────────────────────┘
                       │ JPype / REST
                       ▼
┌─────────────────────────────────────────────────────────┐
│  Ghidra Headless / PyGhidra Engine (Java)              │
│  - 로더, 분석기, 디컴파일러, P-code, 디버거             │
│  - Program DB, FunctionManager, Decompiler API         │
└─────────────────────────────────────────────────────────┘
```

## 3가지 구현 경로

| 경로 | 난이도 | 설명 | 추천 대상 |
|------|--------|------|----------|
| **경로 1: GhidraMCP + Claude Code** | ★☆☆ | 기존 GhidraMCP 확장 설치 후 Claude Code가 Ghidra를 도구로 호출 | 가장 빠름 (5분) |
| **경로 2: PyGhidra 독립 에이전트** | ★★☆ | `pyghidra` + `anthropic` SDK로 직접 ReAct 에이전트 구현 | 나만의 Claude Code 완전 복제 |
| **경로 3: Ghidra 플러그인 내장 LLM** | ★★★ | Ghidra GUI 플러그인에 채팅 창 탑재 (GhidrAssist/GhidraGPT 방식) | Ghidra UI 안에서 AI 어시스턴트 |

이 디렉토리에는 **경로 2의 최소 프로토타입**이 포함되어 있습니다.

## 파일 구성

- `agent.py` — Claude API를 호출하는 ReAct 에이전트 메인 루프
- `ghidra_tools.py` — Ghidra 기능을 LLM Tool(JSON Schema)로 노출
- `prompts.py` — 시스템 프롬프트 (리버싱 전문가 페르소나)
- `.mcp.json` — 경로 1용 MCP 설정 예시
- `requirements.txt`

## 빠른 시작 (경로 2)

```bash
# 1. Ghidra 설치 (12.1+ 권장) 및 환경변수
export GHIDRA_INSTALL_DIR=/path/to/ghidra_12.1_PUBLIC
pip install -r requirements.txt  # pyghidra, anthropic, mcp

# 2. API 키 설정
export ANTHROPIC_API_KEY=sk-ant-...

# 3. 바이너리 분석 (headless, GUI 불필요)
python agent.py --binary /bin/ls --task "main 함수에서 취약점 찾아줘"

# 내부 동작:
# 1) pyghidra로 바이너리 import + auto-analysis
# 2) LLM이 list_functions → decompile → xrefs 순으로 호출
# 3) 결과를 바탕으로 함수명 복구 / 주석 제안 / 보고서 생성
```

## 빠른 시작 (경로 1 — Claude Code + GhidraMCP)

```bash
# GhidraMCP 설치: Ghidra에서 File > Install Extensions > GhidraMCP.zip
# Ghidra 실행 후 HTTP 서버가 localhost:8080에서 대기

# Claude Code에 MCP 추가
claude mcp add ghidra --transport http http://127.0.0.1:8080/mcp

# 이후 Claude Code 안에서:
# > 이 바이너리에서 암호화 함수 찾아서 설명해줘
# Claude가 자동으로 ghidra/list_functions, ghidra/decompile 호출
```

자세한 설명은 상위 README 및 `agent.py` 주석을 참고하세요.
