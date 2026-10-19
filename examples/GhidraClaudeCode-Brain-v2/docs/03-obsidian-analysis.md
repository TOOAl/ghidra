# 03 — Obsidian 분석 (Vault→링크→그래프)

> 출처: obsidian.md/help, DeepWiki `core plugins`, `graph view`, excalibrain, vault-graph.  
> 목표: v2에서 **Vault(폴더) + [[링크]] + Graph/Backlinks** 3가지를 최소로 구현.

## 1. 한 줄 정의

```
Obsidian = 폴더( Vault ) + Markdown 파일( Note ) + [[Wikilink]]( Edge ) + MetadataCache ( 인덱스 )
```

- **서버 없음, 클라우드 없음** — 모든 것이 로컬 파일. Git으로 버전 관리 가능.
- **플러그인은 그냥 JS** — Core plugins(Backlinks, Graph, Canvas)도 토글형, 커뮤니티 플러그인은 `vault/.obsidian/plugins/`에 넣으면 된다.

## 2. Vault — 그냥 폴더

```
vault/
├── .obsidian/               ← 설정 (테마, 핫키, 플러그인 on/off) — v2에서는 없음, 폴더 자체가 vault
├── 01 - 분석/
│   ├── C2-2026-10-19.md     ← note (Markdown + YAML frontmatter)
│   └── check_license.md
├── 02 - 실험/
│   └── WannaCry-2017.md
└── templates/
    └── daily.md
```

**v2 Vault:** `examples/GhidraClaudeCode-Brain-v2/vault/` 폴더 자체. 파일 1개 = 노트 1개. 앞의 `brain/`, `tools/` 등은 Vault 밖(코드)이고, Vault 안은 오직 `*.md` 분석 노트만.

## 3. 링크 — 3종류, 모두 텍스트

| 문법 | 의미 | 예 | v2 |
|------|------|-----|-----|
| `[[노트명]]` | Wikilink (내부) | `[[C2-2026-10-19]]` → `C2-2026-10-19.md` | 정규식 `\[\[([^\]]+)\]\]`로 파싱 |
| `[[노트명\|별명]]` | Alias | `[[FUN_00401000\|check_license]]` | `|` 앞이 실제 타깃 |
| `![[노트명]]` | Embed (내용 포함) | `![[C2-2026-10-19#증거]]` | Phase 2 |
| `[텍스트](http://...)` | 외부 Markdown 링크 | `[c2.evil.com](http://c2.evil.com)` | 무시 (그래프 edge 아님) |
| `#태그` | Tag | `#C2 #UPX` | Phase 2 — 지금은 미구현 |

**해석 규칙 (Obsidian과 동일, 우선순위):**
1. `[[path/to/note.md]]` 풀패스가 있으면 정확히
2. `[[별명]]`이면 frontmatter `aliases: [별명]`에서 찾음
3. `[[basename]]`이면 파일명(basename) 일치 1개 — 중복 시 첫 번째

**v2 최소 구현:** `vault.getMarkdownFiles()`처럼 폴더를 `rglob("*.md")`로 스캔, 파일마다 `re.findall(r"\[\[([^\]]+)\]\]", text)`로 links 추출 → `{source, target}` edge 리스트. fenced code block(`` ``` ``) 안은 제외 (Dataview 쿼리가 edge를 만들지 않게).

## 4. MetadataCache — 인덱스 (우리의 핵심)

Obsidian은 파일을 열 때마다 파싱하지 않고, **MetadataCache**에 미리 인덱스를 만든다.

```ts
// Obsidian 내부 (개념)
metadataCache.getFileCache(file) → {
  links: [{link: "C2-2026-10-19", original: "[[C2-2026-10-19]]", position: ...}],
  frontmatter: {aliases: ["c2"], tags: ["malware"]},
  headings: [{heading: "증거", level: 1}],
  blocks: ... // block id
}
```

**v2 MetadataCache (15줄):**
- `vault/index.py` — `build_index(vault_path) → {files: [{path, links, frontmatter}], edges: [{from, to}]}`
- `cachedRead` 대신 `Path.read_text()`로 파일 내용 읽기 — vault가 100개 파일 이내면 0.1초에 끝남 (vault-graph 실측)
- 저장: `vault/.index.json` (gitignore) — 매번 스캔 대신 캐시, 파일 `mtime`으로 갱신 여부 판단

## 5. Core Plugins — 3개만 (나머지는 커뮤니티)

| 플러그인 | 하는 일 | v2 |
|----------|---------|-----|
| **Backlinks** | 현재 노트를 가리키는 incoming links + Unlinked mentions(텍스트에 이름만 있는 것) | `GET /api/vault/backlinks?file=C2.md` → `[{source: "WannaCry.md", line: 12}]` |
| **Graph View** | force-directed layout (center + repel + link distance) | `GET /api/vault/graph` → `{nodes: [{id, label, group}], edges: [{from, to}]}` → `ui/graph.js`에서 Canvas로 렌더 (WebGL 아님, 2D canvas) |
| **Outgoing Links** | 현재 노트가 가리키는 links | `GET /api/vault/outgoing?file=C2.md` |

**Graph 렌더 규칙:**
- 노드 크기 = incoming links 수 (많을수록 크게)
- 색 = 폴더별 (01-분석=파랑, 02-실험=초록)
- 클릭 → 해당 노트 열기 (`openFile()`)

**v2 최소 Graph (50줄):**
- 서버: `vault/index.py: build_graph()` → nodes + edges JSON
- 클라이언트: `ui/vault_graph.js` — `canvas` + `requestAnimationFrame`으로 force 30프레임 (D3나 Sigma.js 없이 50줄로 가능, 100노드 이내면 충분)

## 6. 우리 코드 매핑

| Obsidian | 우리 v1 | v2 변경 |
|----------|---------|---------|
| Vault (폴더) | 없음 (모든 것이 `brain/`/`tools/`에 섞임) | `v2/vault/` 폴더 신설 — `.md` 분석 노트만 |
| `[[Wikilink]]` | `get_xrefs` (Ghidra 호출 관계) | Wikilink 파서 + Backlinks API 추가 — Ghidra xrefs와 병존 (하나는 바이너리, 하나는 지식) |
| Graph View | `canvas#graph` (더미 데이터) | 실제 `vault/.index.json` 기반 force-directed + 클릭→파일 열기 |
| Daily notes / Templates | 없음 | Phase 2 — 지금은 `vault/templates/` 1개만 |
| `.obsidian/plugins/` | `skills/` | Skills는 Skills로, Obsidian 플러그인은 플러그인으로 — 이름 충돌 없게 `vault/.obsidian/`과 `skills/` 분리 |

## 7. 통합 아이디어 (Phase 1에서 합치는 지점)

```
Claude Code가 Notion 블록을 만들고 → 그 블록을 Obsidian Vault의 .md로도 저장
  BrainAgent.run("C2 찾아줘")
    → Tool: list_strings → "http://c2.evil.com"
    → notion/blocks.py: create_block(type=text, content="C2: http://c2.evil.com")
    → vault/write.py:   write_note("vault/C2-2026-10-19.md", "# C2 분석\n[[check_license]]\n- http://c2.evil.com")
    → vault/index.py:   build_index() 갱신 → graph에 C2 노드 추가
    → ui/server.py:     POST /api/run → session.jsonl + blocks.jsonl + vault/.md 3곳에 동시 저장
```

> **한 번의 분석이 세 곳에 남는다:** 세션 로그(기억), 블록(DB), 마크다운(Vault). 이게 Notion+Obsidian을 합친 이유 — **검색은 DB로, 탐색은 그래프로**.

## 8. v2 체크리스트

- [ ] `vault/` 폴더 + `templates/analysis.md` 1개
- [ ] `vault/index.py` — `rglob("*.md")` → `[[링크]]` 파싱 (code block 제외) → `nodes/edges` + `frontmatter`
- [ ] `ui/server.py` — `GET /api/vault/graph`, `GET /api/vault/backlinks?file=`, `GET /api/vault/outgoing?file=`
- [ ] `ui/vault_graph.js` — 50줄 canvas force-directed + 클릭→openFile
- [ ] 검증: `verify_v2.py --step obsidian` → `C2.md` 1개 만들고 `[[check_license]]` 링크 → graph nodes 2, edges 1이면 PASS
