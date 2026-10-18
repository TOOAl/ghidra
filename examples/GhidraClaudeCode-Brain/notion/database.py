"""
notion/database.py — 데이터베이스 흡수 (Notion database/query.ts 패턴 재구현)

Notion 아이디어: 모든 것이 DB, 필터/정렬/롤업으로 조회.
우리에겐: session.jsonl을 DB처럼 조회.
"""
import json
from pathlib import Path

SESSION_FILE = Path(__file__).parent.parent / "memory" / "session.jsonl"

def query_database(filter: str = None, sort: str = "recent", limit: int = 10) -> dict:
    """DB 조회 — query_database 도구"""
    if not SESSION_FILE.exists():
        return {"filter": filter, "results": []}
    rows = []
    for line in SESSION_FILE.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            r = json.loads(line)
            if filter:
                # 간단 필터: "key:value" 또는 키워드
                if ":" in filter:
                    k, v = filter.split(":", 1)
                    if v.lower() not in str(r.get(k, "")).lower() and v.lower() not in json.dumps(r, ensure_ascii=False).lower():
                        continue
                elif filter.lower() not in json.dumps(r, ensure_ascii=False).lower():
                    continue
            rows.append(r)
        except:
            continue
    if sort == "recent":
        rows = rows[::-1]
    return {"filter": filter, "sort": sort, "count": len(rows[:limit]), "results": rows[:limit]}

def rollup_stats() -> dict:
    """롤업: 전체 통계"""
    q = query_database(limit=1000)
    total = len(q["results"])
    models = {}
    for r in q["results"]:
        m = r.get("model", "unknown")
        models[m] = models.get(m, 0) + 1
    return {"total_sessions": total, "by_model": models}

if __name__ == "__main__":
    import argparse, json as j
    p = argparse.ArgumentParser(description="Notion DB — session 조회")
    p.add_argument("--filter", help="예: model:qwen 또는 키워드")
    p.add_argument("--sort", default="recent", choices=["recent", "oldest"])
    p.add_argument("--limit", type=int, default=10)
    p.add_argument("--rollup", action="store_true")
    args = p.parse_args()
    if args.rollup:
        print(j.dumps(rollup_stats(), ensure_ascii=False, indent=2))
    else:
        print(j.dumps(query_database(args.filter, args.sort, args.limit), ensure_ascii=False, indent=2))
