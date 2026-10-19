# 01 — Claude Code 분석 (Ghidra처럼 분해)

> 출처: `code.claude.com/docs`, Agent SDK, 2604.14228 논문, Bun+Ink 역공학.  
> 목표: v2에서 **최소 20%**만 구현해도 80% 체험이 되는 핵심을 추린다.

## 1. 한 줄 정의

```
Claude Code = LLM(두뇌) + Agent Loop(심장) + Tools(손) + Permissions(방패) + Memory(기억)
```
- **LLM**은 생각만 한다 — 파일/명령을 직접 못 만진다.
- **Loop**가 도구 호출을 파싱→권한 검사→실행→결과를 다시 LLM에 먹인다. 이 반복이 전부다.

## 2. Agent Loop — 정확히 이렇게 돈다

```
[User] "C2 찾아줘"
  → [SDK] systemPrompt + messages + tools를 Claude API에 POST
  ← [Claude] {text: "파일을 먼저 보겠다", tool_calls: [Read("list_functions"), Read("list_strings")]}
  → [Harness] 권한 검사 → Read 병렬 실행 (read-only는 concurrent)
  → [Harness] 결과를 UserMessage로 변환: {role:"user", content:[{tool_use_id:1, result:"main@0x401000"}]}
  → [SDK] 다시 POST (messages에 위 history 포함)
  ← [Claude] {text: "증거 확보", tool_calls: [Renamer("...")]}
  → ... 반복
  ← [Claude] {stop_reason:"end_turn", text:"보고서 작성 완료"}
  → [Harness] 종료, transcript 저장
```

**핵심 규칙 (우리가 옮길 것):**

| 규칙 | 왜 중요 | v2 반영 |
|------|---------|---------|
| `readOnlyHint` — Read/Glob/Grep은 병렬, Edit/Write/Bash는 직렬 | 동시 쓰기 레이스 방지 | `tools/definitions.json`에 `readOnly: true/false` 표시, `ghidra_router.dispatch_parallel()`에서 분기 |
| `stop_reason: tool_use`면 계속, `end_turn`이면 종료 | Loop 종료 조건 | `brain/agent.py` `while turn < max_turns: if not tool_calls: break` |
| 권한 4단계: deny → allow → classifier → ask | `rm -rf /` 같은 파괴 방지 | `ui/server.py` `blocked = ["rm -rf /", "mkfs"]` 유지, v2에서는 `tools/permissions.py`로 분리 |
| Context Compaction — 길어지면 요약 | 토큰 절약 | v2 Phase 3에서, 지금은 `max_turns=12`로 자름 (Simplicity) |

## 3. Tools — 4개의 Primitive로 전부 가능

Anthropic 공식 분류를 단순화하면:

| Primitive | Claude Code 도구 | 우리 매핑 | 예시 |
|-----------|-------------------|-----------|------|
| **Read** | Read, Glob, Grep | `list_functions`, `list_strings`, `code_read` (= `GET /api/file`) | `list_strings(filter="http")` → `http://c2.evil.com` |
| **Write** | Write, Edit | `rename_function`, `set_comment`, `code_write` (= `POST /api/file`) | `rename_function(FUN_00401000 → check_license)` |
| **Execute** | Bash | `code_exec` (= `POST /api/terminal`) | `python verify_v2.py --all` |
| **Connect** | MCP, WebFetch | `search_memory`, `openrouter` (외부 LLM) | `search_memory("UPX")` |

> 결론: **Bash가 만능 어댑터** — `git`, `npm`, `ghidraHeadless` 전부 Bash로 된다. 전용 도구는 Read/Write만 있으면 된다.

**v2 최소 도구 5개 (Phase 1):**
`list_functions`, `list_strings`, `code_read`, `code_write`, `code_exec`
→ 이 5개로 `C2 찾아줘 → 파일 열기 → 수정 → 테스트` 전체가 돈다.

## 4. Subagents & Skills — 나중에, 지금은 안 함

- **Explore/Plan/General-purpose** 3 subagent는 각각 Haiku/Sonnet로 모델을 나눈 것 — v2에서는 단일 agent로 시작.
- **Skills**는 `SKILL.md`를 agent 시작 시 읽는 것뿐 — v2에서는 `skills/` 폴더에 `unpack_upx.md` 같은 파일을 두고 `agent.py`가 `open(SKILL.md).read()`로 systemPrompt에 추가하는 3줄로 구현.

## 5. 우리 기존 코드와 매핑

| Claude Code | 우리 v1 | v2 변경 |
|-------------|---------|---------|
| `query.ts` → `client.messages.create()` | `brain/model_adapter.py: ModelAdapter.chat()` | 유지, `openai_compatible` 1개 provider만 (Anthropic/Bedrock은 주석) |
| `tool_runner.ts` → `execute()` + `isConcurrencySafe()` | 없음 (직렬만) | `tools/router.py`에 `dispatch_parallel()` 추가 (readOnly 병렬) |
| `permissions.ts` | `ui/server.py: blocked` 하드코딩 | `tools/permissions.py: check(cmd)`로 분리, allowlist `["git status", "ls"]` 자동 승인 |
| `memory` (transcript) | `memory/session.jsonl` | 유지, 파일명 `transcript.jsonl`로 명확화 |

## 6. v2에서 구현할 것 (체크리스트)

- [ ] `brain/agent.py` — 20턴 → 12턴으로 단순화, `planner.py`는 Phase 2에서 추가 (지금은 plan 없이 ReAct만)
- [ ] `tools/definitions.json`에 `readOnly` 필드 추가, 5개 도구만
- [ ] `tools/permissions.py` — `blocked` + `allowed` 20줄
- [ ] `repl.py` — `/code`, `/edit`, `/model`, 한글 자연어 → `BrainConsole.runsource()` (이미 v1 패치에서 검증됨, 그대로 이식)
- [ ] `verify`에 `parallel read` 테스트 1개: `list_functions` + `list_strings`를 한 턴에 병렬 요청 → 둘 다 결과 오면 PASS

> **Simplicity 판단:** subagent, compaction, MCP는 Phase 3 이후. Phase 1은 *싱글 agent + 5 tools + 12 turns* 로 끝낸다.
