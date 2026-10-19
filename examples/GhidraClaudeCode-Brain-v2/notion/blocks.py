"""
notion/blocks.py — Notion Block 모델 최소 구현 (v2)

모든 것은 블록: page, text, heading_1, to_do, code, database
2포인터: children(렌더 순서), parent_id(권한 상속)
저장: memory/blocks.jsonl append-only — 한 줄이 한 operation
"""
import uuid, json, pathlib, datetime

ROOT = pathlib.Path(__file__).parent.parent
MEM = ROOT / "memory"
MEM.mkdir(exist_ok=True)

ALLOWED_TYPES = {"page", "text", "heading_1", "to_do", "code", "database"}

def _now():
    return datetime.datetime.utcnow().isoformat() + "Z"

def create_block(type: str, content: str, parent_id: str = None, extra: dict = None) -> dict:
    if type not in ALLOWED_TYPES:
        raise ValueError(f"허용되지 않은 블록 타입: {type} — {ALLOWED_TYPES}")
    bid = uuid.uuid4().hex[:12]
    block = {
        "id": bid,
        "type": type,
        "parent_id": parent_id,
        "content": content,
        "children": [],
        "created_at": _now(),
    }
    if extra:
        block.update(extra)
    # 부모 children에 추가
    if parent_id:
        _append_child(parent_id, bid)
    # append-only 저장
    _append_op("create", block)
    return {"ok": True, "block": block}

def get_block(bid: str) -> dict:
    for op in _read_ops():
        if op.get("op") == "create" and op.get("block", {}).get("id") == bid:
            return {"ok": True, "block": op["block"]}
    return {"ok": False, "error": f"블록 없음: {bid}"}

def list_children(parent_id: str) -> dict:
    # parent의 children 순서대로 블록 반환
    parent = get_block(parent_id)
    if not parent["ok"]:
        return {"ok": False, "error": parent["error"]}
    cids = parent["block"].get("children", [])
    blocks = []
    for cid in cids:
        r = get_block(cid)
        if r["ok"]:
            blocks.append(r["block"])
    return {"ok": True, "parent": parent["block"], "children": blocks}

def list_blocks(limit=50) -> list:
    ops = _read_ops()
    blocks = [o["block"] for o in ops if o.get("op") == "create"]
    return blocks[-limit:]

def _append_child(parent_id: str, child_id: str):
    # 부모 블록을 찾아 children 갱신 — append-only이므로 update operation으로 기록
    # 간단히: 기존 블록을 읽어 children 추가 후 update op로 저장 (실제 Notion은 CRDT이지만 v2는 last-write-wins)
    for op in _read_ops():
        if op.get("op") == "create" and op["block"]["id"] == parent_id:
            # 기존 children에 추가
            updated = dict(op["block"])
            updated["children"] = updated.get("children", []) + [child_id]
            _append_op("update", updated)
            return
    # 부모를 못 찾으면 무시 (orphan 허용)

def _append_op(op: str, block: dict):
    p = MEM / "blocks.jsonl"
    with open(p, "a", encoding="utf-8") as f:
        f.write(json.dumps({"op": op, "block": block}, ensure_ascii=False) + "\n")

def _read_ops():
    p = MEM / "blocks.jsonl"
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                out.append(json.loads(line))
            except:
                pass
    return out

def read_jsonl(p: pathlib.Path):
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                out.append(json.loads(line))
            except:
                pass
    return out[-50:]
