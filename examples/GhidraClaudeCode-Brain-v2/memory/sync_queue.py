"""
memory/sync_queue.py — Notion offline sync 큐 최소 구현

1) 낙관적 적용 — 로컬 즉시 반영
2) 큐에 저장 — sync_queue.jsonl
3) flush — 서버 POST (v2에서는 항상 online이므로 즉시 flush, offline이면 큐에 남음)
"""
import json, pathlib, time

ROOT = pathlib.Path(__file__).parent.parent
MEM = ROOT / "memory"
MEM.mkdir(exist_ok=True)
QUEUE = MEM / "sync_queue.jsonl"

def enqueue(op: dict) -> dict:
    op = dict(op)
    op["enqueued_at"] = time.time()
    op["status"] = "queued"
    with open(QUEUE, "a", encoding="utf-8") as f:
        f.write(json.dumps(op, ensure_ascii=False) + "\n")
    # v2 Phase 1: 항상 online 가정 → 즉시 flush 시도
    # 실패하면 큐에 남겨 재시도 (offline)
    return {"ok": True, "op": op, "queue_len": len(read_queue())}

def read_queue() -> list:
    if not QUEUE.exists():
        return []
    out = []
    for line in QUEUE.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                out.append(json.loads(line))
            except:
                pass
    return out

def flush(server_url="http://127.0.0.1:8090/api/sync") -> dict:
    """큐에 남은 것들을 서버에 POST — 실패하면 큐 유지"""
    q = read_queue()
    if not q:
        return {"ok": True, "flushed": 0}
    try:
        import requests
        r = requests.post(server_url, json={"ops": q}, timeout=3)
        if r.ok:
            # 성공 시 큐 비움
            QUEUE.write_text("", encoding="utf-8")
            return {"ok": True, "flushed": len(q)}
        else:
            return {"ok": False, "error": f"server {r.status_code}", "queue_len": len(q)}
    except Exception as e:
        return {"ok": False, "error": str(e), "queue_len": len(q), "note": "offline — 큐에 유지됨, 재연결 시 재시도"}
