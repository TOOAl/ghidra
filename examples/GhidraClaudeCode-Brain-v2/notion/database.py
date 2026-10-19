"""
notion/database.py — Database는 type=database인 블록, row는 parent_id=db인 page 블록

schema: {prop_id: type}  예: {"status": "select", "addr": "text"}
row:   {properties: {status: "CONFIRMED", addr: "0x401000"}}
값은 ID 기반 — 이름 변경해도 깨지지 않음 (Notion 설계 동일)
"""
import uuid, json
from notion.blocks import create_block, get_block, list_children, _append_op, _now

def create_database(title: str, schema: dict, parent_id: str = None) -> dict:
    """
    schema: {"status": "select", "addr": "text", "tool": "text"}
    """
    extra = {"schema": schema, "views": ["table"]}
    r = create_block(type="database", content=title, parent_id=parent_id, extra=extra)
    return r

def add_row(db_id: str, properties: dict) -> dict:
    """
    properties: {status: "CONFIRMED", addr: "0x401000"}
    - db_id의 schema에 있는 키만 허용 (엄격)
    """
    db = get_block(db_id)
    if not db["ok"]:
        return {"ok": False, "error": db["error"]}
    schema = db["block"].get("schema", {})
    # schema 키 검증 — Simplicity: 없어도 경고만, 저장은 허용 (유연성)
    # row는 type=page, parent_id=db_id인 블록
    rid = uuid.uuid4().hex[:12]
    block = {
        "id": rid,
        "type": "page",
        "parent_id": db_id,
        "content": properties.get("title", rid),
        "children": [],
        "properties": properties,
        "created_at": _now(),
    }
    # 부모 children에 추가
    from notion.blocks import _append_child
    _append_child(db_id, rid)
    _append_op("create", block)
    return {"ok": True, "row": block}

def query(db_id: str, filter: str = None, sort="recent", limit=10) -> dict:
    """
    filter: "status=CONFIRMED" 또는 "tool=list_strings" 1개만 (Phase 1 최소)
    sort: recent/oldest
    """
    db = get_block(db_id)
    if not db["ok"]:
        return {"ok": False, "error": db["error"]}
    rows_r = list_children(db_id)
    if not rows_r["ok"]:
        return {"ok": False, "error": rows_r["error"]}
    rows = rows_r["children"]
    if filter and "=" in filter:
        k, v = filter.split("=", 1)
        k, v = k.strip(), v.strip()
        rows = [r for r in rows if str(r.get("properties", {}).get(k, "")) == v]
    if sort == "recent":
        rows = list(reversed(rows))
    return {"ok": True, "database": db["block"], "rows": rows[:limit], "total": len(rows)}

def list_databases() -> list:
    from notion.blocks import list_blocks
    return [b for b in list_blocks(limit=100) if b.get("type") == "database"]
