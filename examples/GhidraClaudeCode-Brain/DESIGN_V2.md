# DESIGN_V2 — 처음부터 다시, 확실하게

> **상태:** 설계 확정 단계 (spec_first) — 이 문서가 확정되면 `GhidraClaudeCode-Brain-v2/` 폴더에 깨끗한 코드로 재구현한다.  
> **브랜치:** Arena 제약상 `arena/61934e9d-ghidra`를 유지한다. 논리적 v2는 `*-v2/` 폴더로 분리해 기존 `GhidraClaudeCode-Brain/` (레거시)는 건드리지 않는다. Git에서 폴더로 브랜치 효과를 낸다.  
> **원칙:** 상위 `CLAUDE.md` 4원칙(Think/Simplicity/Surgical/Goal-Driven)을 이 문서 자체에 적용했다.

---

## 0. 왜 다시 시작하나 — 실패 회고 (증거 기반)

### 0.1 이번 연동 실패 3원인 (실측)

| # | 증상 | 근본 원인 | 증거 | CLAUDE.md 위반 |
|---|------|-----------|------|----------------|
| 1 | `연결 확인 중…` + `불러오는 중…` 멈춤 | `ui/ide.js:296` `querySelector('.ide-layout')` → HTML은 `<div class="ide">` → `null.clientWidth` → `TypeError` → `DOMContentLoaded` 전체 중단 | `grep -n ide-layout` / 스크린샷 둘 다 초기값 유지 | Surgical 위반: HTML 클래스 바꾸면서 JS는 안 바꿈 |
| 2 | PowerShell `C2 찾아줘` → `SyntaxError` | `brain_repl.py`가 순수 `InteractiveConsole` — 문서에 `>>> C2 찾아줘`라 썼지만 실제로는 `brain.run("…")`만 됨 | `python -m py_compile` 이후 `timeout 20` 테스트에서 한글+SyntaxError→라우팅 없을 때 실패 | Think 위반: 가정(사용자가 brain.run을 쓸 것)이 문서와 다름 |
| 3 | 서버는 떴는데 브라우저는 옛 파일 | `ide.js` 수정 후 cache-bust 없었고, 서버 재시작 없이 `git pull`만 → 브라우저 디스크 캐시가 옛 `ide.js`를 계속 사용 | `curl /api/status`는 200인데 `checkHealth`가 호출조차 안 된 스크린샷 | Goal-Driven 위반: `verify_local.py` 같은 통합 검증 없이 배포 |

### 0.2 구조적 부채

- **패치 누적:** `start.py` → `brain_cli.py` → `brain_repl.py` 3개 REPL이 병존, 어느 것이 정답인지 불명확.
- **테스트 없음:** `verify_local.py --all`이 3단계 중 Ghidra 없이 2/3만 보고, `PowerShell 자연어→브라우저` 경로는 테스트에 없었다.
- **선택자/경로 하드코딩:** `ALLOWED_DIRS`, `ALLOWED_EXTS`, `.ide-layout` 등 4곳에 분산.
- **문서 분산:** `README.md`, `COMPLETE.md`, `ARCHITECTURE.md`, `CLAUDE_CODE_ANALYSIS.md`가 서로 다른 시점의 진실을 말함.

**교훈:** 다음 설계는 *한 기능=한 파일=한 테스트*로 끝내고, 통합 테스트가 항상 먼저다.

---

## 1. 요구사항 — 구체적이고 측정 가능하게

### 1.1 사용자 스토리 (이번에 꼭 필요한 것만 — Simplicity First)

1. **US-1 PowerShell 대화형:** Windows PowerShell에서 `cd E:\ghidra\...-v2` → `python repl.py` → `C2 찾아줘` (따옴표 없이)를 치면 BrainAgent가 12턴 이내 보고서를 만든다.
2. **US-2 브라우저 동기화:** 위 보고서가 `http://127.0.0.1:8090/ide` 오른쪽 채팅에 2초 내 자동 표시된다.
3. **US-3 파일 편집:** 왼쪽 EXPLORER에서 파일을 열고, 중앙에서 수정→`Ctrl+S`하면 저장되고, `저장 후 실행` 시 US-1과 같은 경로로 보고서가 갱신된다.
4. **US-4 Ghidra REAL 모드:** `GHIDRA_INSTALL_DIR`이 있으면 `list_functions` 등이 mock이 아니라 Ghidra headless를 호출한다. 없으면 mock으로 동일 인터페이스 동작.

> 범위 밖 (이번에 안 함): `Brian.psm1`, `start.ps1`, Electron, VS Code 확장, ChromaDB. 필요할 때 Skills로 추가.

### 1.2 성공 기준 — 측정 가능 4/4 (선택한 검증)

기존 `모순0/증거100%/반복0` + `4/4 PASS`를 유지하되, **통합 경로**를 포함해 4개로 재정의한다.

| # | 기준 | 측정 | PASS 조건 | 테스트 커맨드 |
|---|------|------|-----------|---------------|
| 1 | **모순0** | 모든 `run()` 결과의 `check_contradiction(report, evidence)` | `contra["ok"] == True` | `python verify_v2.py --step contradiction` |
| 2 | **증거100%** | 보고서가 최소 2개 Tool 결과를 인용 | `len(evidence) >=2` and 보고서에 주소/문자열 포함 | `python verify_v2.py --step evidence` |
| 3 | **반복0** | 같은 task로 두 번 실행해도 이전 실수(`hindsight.jsonl`)를 반복 안 함 | 두 번째 실행의 `steps`에 과거 `mistake` 미포함 | `python verify_v2.py --step no_repeat` |
| 4 | **통합4/4** | `US-1→US-2→US-3`이 한 번에 | (a) `repl.py --no-preview`에서 한글 자연어 0.6s 보고서 (b) `POST /api/run` 후 `GET /api/database`에 저장 (c) `ide.html` EXPLORER 파일 수 >0 (d) 채팅 버블 1개 이상 | `python verify_v2.py --all --mock-ghidra` (4/4가 모두 PASS여야 v1.0) |

> **강한 성공 기준:** 위 `verify_v2.py --all`을 누가 실행해도 동일 결과가 나온다. 로그에 `VERIFY: 4/4 PASS`가 찍히면 끝.

### 1.3 제약

- 로컬 전용, `127.0.0.1:8090`만 listen, 바이너리 원본은 외부로 안 나간다.
- 무료 우선: Ollama + OpenRouter Free로 검증 가능, 유료는 선택.
- Windows PowerShell 5.1 + Python 3.11+에서 동작 (pyyaml 휠 없어도 mock으로 동작해야 함 — 이번에 `FALLBACK_PRESETS`를 서버가 아니라 `requirements` 없이도 동작하게 함).

---

## 2. 아키텍처 — 유지하는 것 / 바꾸는 것

### 2.1 유지 (keep_python_server)

```
Python + http.server + CodeMirror — Ghidra REAL 모드와 이미 호환되므로 유지.
```

**트레이드오프:**
- 가정: `http.server`는 프로덕션용이 아니지만, 로컬 1인용 IDE에는 충분하다. → 대안 FastAPI는 의존성+빌드 복잡도만 늘어난다. → 결정: 유지.
- 가정: Electron보다 브라우저가 단순하다. → 결정: 유지.

### 2.2 새로 그리는 구조 (v2)

```
GhidraClaudeCode-Brain-v2/
├── DESIGN_V2.md          ← 이 문서 (진실의 원천)
├── README_V2.md          ← US-1~4만 설명하는 1페이지 README (COMPLETE.md 대체)
├── requirements.txt      ← openai, requests만 필수; pyyaml, chromadb는 선택
├── config/
│   └── models.yaml       ← presets 12개 (FALLBACK을 코드가 아니라 이 파일에 넣는다 — 단일 원천)
├── brain/
│   ├── agent.py          ← ReAct 12턴 루프만 (planner/evaluator는 skills로 분리)
│   ├── model_adapter.py  ← openai_compatible 1개만 지원 (나머지는 주석으로 보관 — Simplicity)
│   ├── reasoning.py      ← 3단계 관찰→추론→검증 (모순0)
│   ├── contradiction.py  ← check_contradiction
│   └── team/             ← 4명 토론은 skills/ 로 이동
├── tools/
│   ├── definitions.json  ← 도구 정의 (MCP)
│   ├── ghidra_router.py  ← mock/real 분기 1곳에만
│   └── real_binary.py    ← capstone+headless (선택)
├── memory/
│   ├── session.jsonl     ← 세션
│   ├── hindsight.jsonl   ← 반복0용
│   └── vector_store.py   ← 선택 (없으면 JSON fallback)
├── skills/               ← unpack_upx, find_crypto 등 skill은 여기서만 추가
├── ui/
│   ├── server.py         ← 200줄 이하 목표 (현재 407줄 → 절반으로)
│   │                    7개 GET + 7개 POST만, safe_path 1곳, ALLOWED 1곳
│   ├── ide.html          ← 단일 페이지, ?v= 해시로 cache-bust
│   ├── ide.js            ← init은 try-catch 격리, selector는 상수 1곳
│   └── ide.css           ← 다크 테마 유지
├── repl.py               ← 유일한 REPL (brain_cli.py/brain_repl.py 통합, 1개만)
├── run.py                ← 프로그래밍 API (import로 호출)
└── verify_v2.py          ← 4/4 측정 (위 표대로)
```

**바꾸는 점:**
- REPL 3개 → 1개 (`repl.py`). 자연어 라우팅은 `BrainConsole`로 기본 포함.
- `server.py` 절반으로: `load_models()`/`get_status()`가 pyyaml 없이도 동일 동작하도록 파일 자체에 `FALLBACK`을 두지 말고 `models.yaml` 읽기 실패 시 그 파일의 `presets`를 그대로 fallback으로 쓴다 (중복 원천 제거).
- `initSplitter` 버그의 재발 방지: selector 문자열을 `ui/config.json` 같은 1곳에 두지 말고 `ide.html`에 `data-layout=".ide"`로 두고 JS는 그 값을 읽는다 — HTML이 바뀌면 JS도 따라간다 (수술적 결합 최소화).
- 모든 `fetch()`에 `?v=` + `Cache-Control: no-cache` 헤더 추가.

### 2.3 데이터 흐름 (US-1→US-2)

```
PowerShell: repl.py "C2 찾아줘"
  → BrainConsole.runsource() 감지 (한글+SyntaxError)
  → Brain.run(task) → BrainAgent.run(12턴)
      → ModelAdapter.chat() (ollama/openrouter/mock)
      → GhidraRouter.dispatch() (list_functions, list_strings …)
      → reasoning.py / contradiction.py
      → report 생성
  → POST http://127.0.0.1:8090/api/run {task, report} → memory/session.jsonl 저장
  → 브라우저 ide.js pollChat() GET /api/database 2초마다 → addChat(assistant, report)

브라우저: EXPLORER 파일 클릭
  → GET /api/file?path=brain/agent.py → CodeMirror 표시
  → Ctrl+S → POST /api/file {path, content} → compile() 검사 → 저장
  → 저장 후 실행 → POST /api/run 과 동일 흐름
```

---

## 3. 검증 계획 — 테스트가 설계보다 먼저

### 3.1 verify_v2.py (새로 만든다 — 기존 verify_local.py는 건드리지 않는다)

```bash
# 각 단계는 독립적으로 실행 가능 (Goal-Driven)
python verify_v2.py --step contradiction   # 모순0
python verify_v2.py --step evidence       # 증거100%
python verify_v2.py --step no_repeat     # 반복0
python verify_v2.py --step integration   # PowerShell 자연어→브라우저 (mock 서버 띄워 테스트)

python verify_v2.py --all --mock-ghidra  # 4/4 PASS면 v2 MVP 완료
```

- `integration`은 `http.server`를 `127.0.0.1:8091`에 임시로 띄워 `repl.py --no-preview` 결과를 `POST`하고 `GET /api/database`로 확인한다. 브라우저 없이도 CI에서 돈다.
- Ghidra가 없으면 `--mock-ghidra`로 동일 인터페이스로 PASS해야 한다 (Free by Default).

### 3.2 수동 체크리스트 (측정과 함께 눈으로도)

1. PowerShell `python repl.py` → `C2 찾아줘` → `[완료 0.xs]` 보고서 6섹션 보이는가
2. 브라우저 `http://127.0.0.1:8090/ide` `Ctrl+Shift+R` 후 상단 `● 서버` + 왼쪽 파일 수 >0 + 오른쪽 채팅에 보고서가 2초 내 뜨는가
3. `brain/reasoning.py` 열고 한 줄 고쳐 `Ctrl+S` → 저장됨 배지 + `verify` 자동 실행되는가

---

## 4. 구현 단계 — 한 단계=한 PR=한 검증

| 단계 | 목표 | 산출물 | 검증 |
|------|------|--------|------|
| **Phase 0** | 이 문서 확정 | `DESIGN_V2.md` (지금) | 당신이 이 문서를 승인하면 다음으로 |
| **Phase 1** | 최소 뼈대 (Mock만) | `v2/ui/server.py` + `v2/ui/ide.html/js/css` + `v2/repl.py` (Ghidra 없이 mock 5개 도구로 US-1~3 동작) | `verify_v2.py --step integration` 1/4 PASS — `git push` 후 당신 PowerShell에서 `C2 찾아줘`가 브라우저에 뜨면 Phase 1 완료 |
| **Phase 2** | 두뇌 붙이기 | `v2/brain/` 4파일 + `tools/` + `memory/` + 4/4 중 모순0/증거100% | `verify_v2.py --step contradiction --step evidence` 2/4 PASS |
| **Phase 3** | Ghidra REAL + Skills | `GHIDRA_INSTALL_DIR` 분기 + `skills/unpack_upx.md` 등 | `verify_v2.py --all --mock-ghidra` 4/4 PASS → v2 MVP |
| **Phase 4** | 성장 (선택) | `ml/`, `notion/design` 등은 v2 MVP 이후 별도 PR | `ml/learn.py` 100% 등은 Phase 4에서 |

> 각 Phase는 200줄 이하로, `git log --oneline`에 한 줄로 남는다. Surgical: Phase N에서는 Phase N 파일만 만진다.

---

## 5. 위험과 대응

| 위험 | 대응 |
|------|------|
| Windows `python` 경로 다름 (`py`/`python3`) | `repl.py` 시작 시 `sys.executable`을 그대로 쓰고, `start.py`는 3개 후보를 모두 시도 (이미 함) |
| pyyaml 휠 없음 (Python 3.15) | `models.yaml`은 표준 YAML 1.2 subset만 쓰고, 파서는 `yaml` 없으면 `json` fallback이 아니라 `re`로 `presets:` 키만 파싱 — 의존성 0 |
| 브라우저 캐시 | 모든 `fetch()`에 `headers: {"Cache-Control":"no-cache"}` + `script?v=hash` |
| 포트 8090 점유 | `server.py` 시작 시 `socket.bind` 실패하면 `8091`로 자동 폴백하고 URL을 출력 |
| PowerShell 자연어 오판 (예: `x = 1`을 자연어로) | 한글 포함+`SyntaxError`일 때만 라우팅 — `x=1`은 컴파일 성공이라 Python으로 실행됨 (이미 검증 10) |

---

## 6. 다음 행동 (당신이 승인하면 바로 시작)

1. **승인:** 이 문서에 대해 “좋다, Phase 1 가” 라고 하면 Phase 1 뼈대를 `GhidraClaudeCode-Brain-v2/`에 만든다.
2. **Phase 1 PR:** `v2/ui/server.py` (200줄), `v2/ui/ide.*` (selector 버그 없음), `v2/repl.py` (한글 라우팅 포함), `v2/verify_v2.py` (integration 1개) — `git commit -m "v2 Phase1: 최소 뼈대 — mock US-1~3"` → `git push`.
3. **당신이 PowerShell에서 검증:** `cd E:\ghidra\examples\GhidraClaudeCode-Brain-v2` → `python repl.py` → `C2 찾아줘` → 브라우저에 뜨는지.

> 이 문서는 살아있는 문서다. Phase마다 “무엇을 배웠나”를 0.1에 한 줄 추가한다. 코드는 문서보다 짧아야 한다.

---

## 부록: 기존 레거시는 어떻게 되나

- `examples/GhidraClaudeCode-Brain/` (현재)는 **읽기 전용**으로 보존 — `git log`로 모든 결정이 남는다.
- `v2/`가 4/4 PASS하면 `README_V2.md`에 “v2가 진실”이라고 쓰고, 레거시는 `_legacy/`로 옮기거나 그대로 둔다. 삭제하지 않는다 (Surgical: 고장 나지 않은 것은 두둔다).

