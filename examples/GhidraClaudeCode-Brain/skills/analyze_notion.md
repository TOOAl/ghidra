---
name: analyze_notion
description: Notion(Electron) 앱을 분석하고 그 패턴을 내 두뇌에 흡수하는 스킬
triggers: ["notion", "Notion", "노션", "블록", "block", "데이터베이스", "database", "동기화", "sync"]
---

# Notion 분석 스킬 — 블록/오프라인/DB 흡수

Notion은 Electron 앱: JS가 본체, native는 일부. REA의 JS 프로바이더가 Ghidra보다 적합.

## 언제 발동

- "Notion 바이너리 분석해줘" → 전체 Electron 분석
- "블록 편집 흡수해줘" → block 패턴만
- "오프라인 동기화 흡수해줘" → sync 패턴만
- "데이터베이스 흡수해줘" → database 패턴만

## 절차 (REA JS 도구 3개 사용)

1. `list_js_modules`로 Notion `app.asar` 모듈 목록 → `notion://`, `editor/`, `sync/` 찾기
2. `get_js_source`로 핵심 3개 소스 읽기:
   - `editor/block.ts` → 블록 편집 (CRDT, toggle, transclusion)
   - `sync/offline.ts` → 오프라인 큐 + 재시도 + 충돌 해결
   - `database/query.ts` → 필터/정렬/롤업 쿼리
3. `list_ipc_channels`로 메인↔렌더러 통신: `notion:sync`, `notion:db-query` 등
4. `search_memory`로 과거 Electron 분석 기억 대조
5. 결과를 `notion/` 폴더의 3개 흡수 모듈로 변환 (복사가 아닌 재구현)

## 흡수 결과 (내 두뇌 기능)

- **블록 편집** → `notion/blocks.py`: 분석 보고서를 블록 단위(코드/텍스트/토글)로 저장
- **오프라인 동기화** → `notion/sync.py`: 외부 LLM 오프라인 시 큐에 쌓고, 온라인 시 재시도
- **데이터베이스** → `notion/database.py`: session.jsonl을 Notion DB처럼 필터/정렬/롤업

## 예시 보고서

> CONFIRMED: Notion `app.asar/editor/block.ts`에서 Block CRDT 발견 (list_js_modules). 내 두뇌에는 `notion/blocks.py`로 흡수: 분석 보고서가 블록 단위로 저장됨. → 검증: `python notion/blocks.py --add "C2 분석"`
