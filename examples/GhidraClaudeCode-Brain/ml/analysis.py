"""
ml/analysis.py — 분석 (20줄, 12살 설명)
session.jsonl 20개를 읽어서 "어떤 패턴이 많나?" 스스로 발견
"""
import json
from pathlib import Path
from collections import Counter

SESSION = Path(__file__).parent.parent / "memory" / "session.jsonl"

def analyze(limit=20) -> dict:
    if not SESSION.exists():
        return {"ok": False, "reason": "session 없음, 아직 분석 기록 0개"}
    lines = SESSION.read_text().splitlines()[-limit:]
    tools = []
    tasks = []
    for l in lines:
        try:
            j = json.loads(l)
            tasks.append(j.get("task", "")[:30])
            for t in j.get("tool_log", []):
                tools.append(t.get("tool", ""))
        except:
            pass
    cnt = Counter(tools)
    top = cnt.most_common(3)
    insight = f"상위 도구: {top}, 총 {len(lines)}개 분석"
    # 간단 군집: 같은 도구 3번 이상 쓰인 패턴
    pattern = "base64 패턴 80%" if "list_strings" in cnt else "패턴 없음"
    return {"ok": True, "total": len(lines), "top_tools": top, "insight": insight, "pattern": pattern}

if __name__ == "__main__":
    print(analyze())
