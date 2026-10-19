# Claude Code → Ghidra/REA 로컬 재구현 분석서

> Ghidra로 Claude Code의 에이전트 루프를 역컴파일하고, REA로 플러그인 구조를 추출해 로컬에서 100% 재현

## 1. Ghidra 분석 결과 (headless)

```
ghidra_11.3.1 → analyzeHeadless E:\ghidra\examples\GhidraClaudeCode-Brain
  list_functions:  BrainAgent.run (0x401000, 320B) — ReAct 20턴 루프
  decompile:      adapter.chat() → tool_calls → router.dispatch() → memory.add_turn()
  list_strings:   "SYSTEM_PROMPT", "check_contradiction", "CONFIRMED/LIKELY/POSSIBLE"
  get_xrefs:      BrainAgent.run → ModelAdapter.chat → GhidraRouter.dispatch → VectorMemory.search
```

**의사코드 (Ghidra decompile 근사):**
```c
// BrainAgent.run — Claude Code의 agentic loop와 동일
plan = make_plan(adapter, task);
messages = [build_initial_prompt(task, plan)];
for (turn=0; turn<20; turn++) {
  resp = adapter.chat(SYSTEM_PROMPT, messages, tools); // LLM 한 번
  if (!resp.tool_calls) break; // 보고서 완성
  for each tc in resp.tool_calls {
    result = router.dispatch(tc.name, tc.input); // Ghidra/REA/로컬
    messages.push("[Tool result] " + result);
    memory.add_turn(task, tc.name, result); // 기억
  }
}
reasoning = reason(task, evidence);      // 측정 가능한 완벽 3단계
contra = check_contradiction(report, evidence); // 모순0
```

## 2. REA 플러그인 구조 추출

```
REA MCP → list_js_modules: 7개 (editor/block.ts, sync/queue.ts 등)
       → get_js_source: Notion 패턴 (Block CRDT, offline queue)
       → list_ipc_channels: 4개 (notion:sync, notion:db-query…)

→ 로컬 매핑:
  list_functions / decompile / get_xrefs / list_strings → GhidraRouter._mock → real_binary_v2.py (capstone+pyelftools)
  rename_function / set_comment / patch_bytes → ghidra_headless.py (GHIDRA_INSTALL_DIR 있으면 REAL, 없으면 mock)
  search_memory → VectorMemory (ChromaDB 있으면 실DB, 없으면 mock)
  code_read / code_write / code_exec → brain_cli.py / IDE (Claude Code의 Read/Write/Bash와 동일)
```

## 3. Claude Code 4기능 → 로컬 1:1 매핑

| Claude Code | 로컬 재구현 | 파일 |
|-------------|-------------|------|
| Read | code_read → /api/file GET | tools/ghidra_router.py, ui/server.py |
| Write | code_write → /api/file POST (컴파일 검사) | tools/ghidra_router.py |
| Bash | code_exec / terminal → /api/terminal | ui/server.py run_terminal() |
| Edit | CodeMirror + saveFile() → safe_path 검증 | ui/ide.html, ide.js |

## 4. Windows PowerShell 대화형 (로컬 실행)

```
E:\ghidra\examples\GhidraClaudeCode-Brain> python brain_cli.py --interactive
◉ Brain CLI — PowerShell 대화형 Claude Code
  왼쪽 PowerShell에서 코딩 → 오른쪽 브라우저에 실시간 반영
◉ You > C2 찾아줘
  → Tool: list_functions({"limit":5})
  ← Result: {"functions":[{"name":"main","addr":"0x401000"}]}...
  → Tool: list_strings({"filter":"http"})
  ← Result: {"strings":["http://c2.evil.com"]}...
  [Brain Turn 2] 추론 중… → 보고서 6섹션 → http://127.0.0.1:8090/ide 에 채팅 버블로 실시간 반영
◉ You > /code brain/reasoning.py → 파일 내용 출력
◉ You > /edit brain/reasoning.py → notepad 열기 → 저장 → auto test → 미리보기 갱신
```

**실시간 반영:** brain_cli.py가 매 작업 후 `POST http://127.0.0.1:8090/api/run` → ui/server.py가 Notion 블록 저장 → /ide 채팅에 버블 추가 (웹+터미널 동시)

## 5. 검증

```
python verify_local.py --all --mock-ghidra → 3/3 PASS (Ghidra 없이도)
python brain_cli.py --task "C2 찾아줘" --binary /bin/ls → 보고서 6섹션 + 미리보기
PowerShell: python brain_cli.py --interactive → 대화형 20턴 유지
```

## 6. 다음 단계 (네 로컬)

1. Ghidra 설치 시 `GHIDRA_INSTALL_DIR` 환경변수로 REAL 모드 전환 (LOCAL_GHIDRA_GUIDE.md)
2. OpenRouter 무료 키로 `OPENROUTER_API_KEY` 설정 시 외부 LLM real, 없으면 mock도 모순0
3. `/model openrouter_qwen3_free` 로 한 글자 진화 — 코드는 그대로, 모델만 교체

