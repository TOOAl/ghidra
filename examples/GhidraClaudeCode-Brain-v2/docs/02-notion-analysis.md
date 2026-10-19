# 02 — Notion 분석 (블록→DB→동기화 3층)

> 출처: notion.com/blog `offline`, `crdt`, educative.io `system-design`, howworks.ai.  
> 목표: v2에서 Notion의 **블록 모델 + DB + 오프라인 큐** 3가지를 최소로 구현.

## 1. 한 줄 정의

```
Notion = Block Tree (모든 것이 블록) + Database (블록의 특수형) + Transaction Log (모든 편집은 연산)
```

## 2. Block 모델 — 모든 것이 블록

```json
{
  "id": "uuid-1234",
  "type": "text | heading_1 | to_do | page | database | table_row",
  "parent_id": "uuid-parent",
  "content": "rich text or typed payload",
  "children": ["uuid-child1", "uuid-child2"],  // content pointer (렌더 순서)
  "created_at": "2026-10-19T09:00:00Z"
}
```

**핵심 2가지 포인터 (howworks.ai):**

| 포인터 | 용도 | 예 |
|--------|------|-----|
| `children` (content) | 렌더 트리 — 블록 안에 블록 | `page` → `[text, to_do, database]` |
| `parent_id` | 권한 상속 | `page`가 private이면 자식도 private |

**왜 중요한가:** `page`와 `database`와 `database row`가 모두 *같은* 블록 타입이다. DB row는 `type: page`인 블록이 `parent_id: database-id`인 것뿐. 이 재귀 덕에 "DB 안에 페이지, 페이지 안에 DB"가 공짜로 된다.

**v2 최소 블록 6타입 (Phase 1):**

| type | content 예 | 용도 |
|------|------------|------|
| `page` | `{title: "C2 분석"}` | 최상위 문서 |
| `text` | `{text: "http://c2.evil.com 발견"}` | 보고서 본문 |
| `heading_1` | `{text: "1. 증거"}` | 섹션 |
| `to_do` | `{text: "check_license 분석", checked: false}` | 할 일 |
| `code` | `{text: "FUN_00401000", lang: "c"}` | 의사코드 |
| `database` | `{schema: {status: "select", addr: "text"}, views: ["table"]}` | 분석 결과 테이블 |

> `database`의 `schema`는 `{property_id: type}` 맵, row는 `parent_id=database`인 `page` 블록. 값은 `{prop_id: value}`로 저장 — 이름이 아니라 ID로 저장해 rename해도 깨지지 않는다.

## 3. Database 엔진 — 블록을 재활용

```
database block (id: db-1)
  schema: {status: "select", addr: "text", tool: "text"}
  children: [row-1, row-2, row-3]
    row-1 (type: page, parent_id: db-1)
      properties: {status: "CONFIRMED", addr: "0x401000", tool: "list_strings"}
      children: [text-1] // row 안의 본문
```

**View:** Table/Board/Calendar는 같은 rows에 필터·정렬을 다르게 보여주는 것뿐 — v2에서는 Table 1개만 (Simplicity).

**v2 구현 (20줄):**
- `notion/blocks.py` — `create_block(type, content, parent_id)` + `get_block(id)` + `list_children(parent_id)`
- `notion/database.py` — `create_database(schema)` + `add_row(db_id, properties)` + `query(db_id, filter)` (filter는 `prop == value` 1개만)

## 4. Offline Sync — 3단계 파이프라인

Notion 공식 5단계 → v2는 3단계로 단순화:

```
[사용자 입력]
  1) 낙관적 적용 (optimistic) — 로컬에 즉시 반영, UI는 즉시 갱신
  2) 큐에 저장 — TransactionQueue (localStorage / SQLite 대신 memory/sync_queue.jsonl)
  3) 서버에 POST /api/sync — 서버는 append-only log에 저장, 다른 클라이언트에 broadcast (v2에서는 1인용이므로 log만)
```

**CRDT vs OT 트레이드오프:**

|  | OT | CRDT (Notion 선택) |
|--|-----|---------------------|
| 서버 필요 | 항상 | 없어도 됨 (decentralized) |
| 오프라인 | 제한적 | 네이티브 — 끊겨도 편집 가능 |
| 메모리 | 낮음 | 높음 (tombstone) |
| 구현 | 중간 | 높음 |

**v2 결정:** Phase 1은 **OT 없이 append-only log**만 — 같은 블록을 두 곳에서 동시 편집하는 충돌은 `last-write-wins` + `hindsight.jsonl`에 기록해 반복0으로 감지. Phase 3에서 RGA 기반 CRDT 도입.

**저장소:**
- `memory/blocks.jsonl` — append-only, 한 줄이 한 operation: `{"op": "create", "block": {...}, "ts": "..."}`
- `memory/sync_queue.jsonl` — 아직 서버에 안 간 연산. 온라인이면 즉시 `POST /api/sync`, 오프라인이면 큐에 남아 있다가 재연결 시 flush.

## 5. Real-time — MessageStore + WebSocket (v2는 폴링)

Notion 본물은 `syncRecordValues` WebSocket으로 push. v2는 Phase 1에서 `GET /api/database` 2초 폴링으로 대체 (우리는 이미 `ide.js pollChat()`으로 검증 완료). Phase 2에서 `Server-Sent Events`로 업그레이드 (WebSocket보다 단순).

## 6. 우리 코드 매핑

| Notion | 우리 v1 | v2 변경 |
|--------|---------|---------|
| `offline_page`, `offline_action` | `notion/blocks.py` (일부) | 유지, `parent_id` + `children` 2포인터 명확히 |
| `saveTransactions` | `POST /api/file` (파일 저장) | `POST /api/blocks`로 분리 — 파일은 파일, 블록은 블록 |
| `syncRecordValues` | 폴링 2초 | 유지, Phase 2에서 SSE |
| Database | `notion/database.py` 미흡 | `schema` ID 기반 + `query()` 필터 1개로 최소 구현 |

## 7. v2 체크리스트

- [ ] `notion/blocks.py` — 6타입, `create/get/list_children`, append-only `blocks.jsonl`
- [ ] `notion/database.py` — `create_database`, `add_row`, `query` (ID 기반)
- [ ] `memory/sync_queue.jsonl` — `enqueue(op)` + `flush()` (지금은 항상 online이므로 flush 즉시)
- [ ] `ui/server.py` — `GET /api/blocks`, `POST /api/blocks`, `GET /api/database`, `POST /api/sync` 4개 엔드포인트 (파일용 `/api/file`과 분리)
- [ ] 검증: `verify_v2.py --step notion` → block 1개 생성 → get → children 1개면 PASS, DB 1개 생성 → row 2개 → query 1개면 PASS
