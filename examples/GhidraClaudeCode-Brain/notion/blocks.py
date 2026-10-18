"""
notion/blocks.py — 블록 편집 흡수 (Notion block.ts 패턴 재구현)

Notion 아이디어: 모든 문서는 블록의 트리. 우리도 분석 보고서를 블록으로 저장.
복사가 아닌 재구현: Notion의 CRDT/트랜스클루전 아이디어만 차용.
"""
import json
from pathlib import Path
from datetime import datetime
import uuid

BLOCKS_FILE = Path(__file__).parent.parent / "memory" / "blocks.jsonl"

def create_block(content: str, type: str = "text", parent: str = None) -> dict:
    """블록 1개 생성 — create_block 도구"""
    BLOCKS_FILE.parent.mkdir(parents=True, exist_ok=True)
    block = {
        "id": "blk_" + uuid.uuid4().hex[:8],
        "type": type,  # text | code | toggle | callout
        "content": content,
        "parent": parent,
        "created": datetime.utcnow().isoformat(),
    }
    with open(BLOCKS_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(block, ensure_ascii=False) + "\n")
    return {"ok": True, "id": block["id"], "type": type}

def list_blocks(limit: int = 20) -> list:
    if not BLOCKS_FILE.exists():
        return []
    lines = BLOCKS_FILE.read_text(encoding="utf-8").strip().splitlines()
    return [json.loads(l) for l in lines[-limit:]]

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Notion 블록 — 분석 보고서를 블록으로 저장")
    p.add_argument("--add", help="블록 내용")
    p.add_argument("--type", default="text", choices=["text", "code", "toggle", "callout"])
    p.add_argument("--list", action="store_true")
    args = p.parse_args()
    if args.add:
        print(create_block(args.add, args.type))
    if args.list:
        for b in list_blocks():
            print(f"[{b['type']}] {b['id']}: {b['content'][:80]}")
