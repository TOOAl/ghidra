# GhidraClaudeCode-Brain v2 — Claude Code + Notion + Obsidian 통합

> **한 줄:** `C2 찾아줘` 한 번에 **에이전트(Claude Code) → 블록(Notion) → 그래프(Obsidian)** 3곳에 동시 저장

## 1. 3기둥 — 각각 20줄로 핵심만

| 기둥 | 파일 | 핵심 |
|------|------|------|
| **Claude Code** | `brain/agent.py` 12턴 + `tools/router.py` 병렬 + `tools/permissions.py` | Read 3개 병렬, Write 직렬, 권한 deny/allow |
| **Notion** | `notion/blocks.py` + `notion/database.py` + `memory/sync_queue.py` | 모든 것은 블록 6타입, DB는 page 블록, offline 큐 3단계 |
| **Obsidian** | `vault/index.py` + `ui/vault_graph.js` | 폴더=vault, `[[링크]]` 파싱, force-directed graph |

합치면: `POST /api/run` 한 번이 `session.jsonl` + `blocks.jsonl` + `vault/*.md` 3곳에 동시 저장

## 2. 실행 (Windows PowerShell)

```powershell
cd E:\ghidra
git pull origin arena/61934e9d-ghidra
cd examples\GhidraClaudeCode-Brain-v2
python ui/server.py              # 1) 서버 — http://127.0.0.1:8090/ide

# 새 PowerShell 탭에서
python repl.py                   # 2) REPL — 한글 자연어 바로
>>> C2 찾아줘                    # → 12턴 → 보고서 + 블록 + vault 저장 + 브라우저 채팅 동시
>>> /code vault/C2-1019.md
>>> /blocks
>>> /graph
>>> /help
```

브라우저 `http://127.0.0.1:8090/ide` → `Ctrl+Shift+R` → 왼쪽 EXPLORER + 오른쪽 채팅 + Blocks/Graph 탭 확인

## 3. 검증 — 4/4 PASS여야 v1.0

```bash
python verify_v2.py --all --mock-ghidra
# ✅ contradiction (모순0)
# ✅ evidence (증거100%)
# ✅ no_repeat (반복0)
# ✅ integration (서버+자연어+vault)
# VERIFY: 4/4 PASS
```

## 4. 구조

```
v2/
├── docs/01-claude-code-analysis.md, 02-notion, 03-obsidian — 분석 3문서
├── brain/agent.py, model_adapter.py, reasoning.py, contradiction.py
├── tools/definitions.json (5개), router.py, permissions.py
├── notion/blocks.py, database.py
├── vault/index.py, templates/analysis.md
├── ui/server.py, ide.html/js/css, vault_graph.js
├── repl.py — 유일한 REPL (한글 자연어 + /명령)
└── verify_v2.py — 4/4 측정
```

## 5. 다음: Phase 2

- Planner (Tree-of-Thought) + Memory VectorStore
- Ghidra REAL 모드 (`GHIDRA_INSTALL_DIR` 설정 시)
- Skills (`unpack_upx`, `find_crypto`)
