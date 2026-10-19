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

def _build_latest():
    latest={}
    for op in _read_ops():
        bid=op.get("block",{}).get("id")
        if bid:
            latest[bid]=op["block"]
    return latest

def get_block(bid: str) -> dict:
    latest=_build_latest()
    if bid in latest:
        return {"ok": True, "block": latest[bid]}
    return {"ok": False, "error": f"블록 없음: {bid}"}

def list_children(parent_id: str) -> dict:
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
    latest=_build_latest()
    return list(latest.values())[-limit:]

def _append_child(parent_id: str, child_id: str):
    latest=_build_latest()
    if parent_id not in latest:
        return  # 부모 없음 → orphan 허용
    updated=dict(latest[parent_id])
    updated["children"]=updated.get("children",[])+[child_id]
    _append_op("update", updated)

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
