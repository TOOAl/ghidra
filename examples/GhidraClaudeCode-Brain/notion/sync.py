"""
notion/sync.py — 오프라인 동기화 흡수 (Notion sync/offline.ts 패턴 재구현)

Notion 아이디어: 오프라인 큐에 쌓고, 온라인 시 재시도 + 충돌 해결.
우리에겐: 외부 LLM 오프라인 → 큐에 쌓고, 온라인 시 재실행.
"""
import json
from pathlib import Path
from datetime import datetime

QUEUE_FILE = Path(__file__).parent.parent / "memory" / "sync_queue.jsonl"

def queue_sync(task: str, binary: str = None) -> dict:
    """큐에 추가 — queue_sync 도구"""
    QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
    item = {"task": task, "binary": binary, "queued": datetime.utcnow().isoformat(), "status": "queued"}
    with open(QUEUE_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(item, ensure_ascii=False) + "\n")
    return {"ok": True, "queued": task, "queue_len": count_queued()}

def count_queued() -> int:
    if not QUEUE_FILE.exists():
        return 0
    return sum(1 for l in QUEUE_FILE.read_text(encoding="utf-8").splitlines() if l.strip())

def list_queue(limit: int = 20) -> list:
    if not QUEUE_FILE.exists():
        return []
    return [json.loads(l) for l in QUEUE_FILE.read_text(encoding="utf-8").splitlines()[-limit:] if l.strip()]

def flush_queue(dry_run: bool = True) -> list:
    """온라인 시 큐 비우기 — 실제로는 brain/agent.py가 하나씩 재실행"""
    items = list_queue(100)
    if dry_run:
        return [{"dry_run": True, "would_run": i} for i in items if i.get("status") == "queued"]
    # 실제 flush는 agent가 처리
    return items

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Notion 오프라인 동기화 — 큐")
    p.add_argument("--add", help="큐에 추가할 task")
    p.add_argument("--binary")
    p.add_argument("--list", action="store_true")
    p.add_argument("--flush", action="store_true")
    args = p.parse_args()
    if args.add:
        print(queue_sync(args.add, args.binary))
    if args.list:
        print(list_queue())
    if args.flush:
        print(flush_queue(dry_run=True))
