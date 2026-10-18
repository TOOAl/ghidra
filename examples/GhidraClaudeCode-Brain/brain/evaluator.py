"""
brain/evaluator.py — 스스로 채점하고 성장

매 분석 후 100점 만점으로 채점.
낮은 점수는 다음 분석의 프롬프트 개선 재료가 됨.
"""

EVALUATOR_PROMPT = """\
너는 리버스 엔지니어링 보고서의 심사위원이야.
다음 보고서를 100점 만점으로 채점해라.

채점 기준:
- accuracy (40점): 사실 정확도, 추측 없이 증거 기반인가?
- evidence (30점): decompile, xrefs 등 증거를 충분히 제시했는가?
- completeness (20점): 빠진 함수나 시나리오 없는가?
- readability (10점): 보고서가 읽기 쉬운가?

JSON으로만 답해:
{
  "scores": {"accuracy": 0, "evidence": 0, "completeness": 0, "readability": 0, "total": 0},
  "feedback": "개선할 점 2~3문장",
  "strength": "잘한 점 1문장"
}
"""

def evaluate(adapter, task: str, report: str, tool_log: list) -> dict:
    import json
    context = f"Task: {task}\n\nTool log: {json.dumps(tool_log, ensure_ascii=False)[:4000]}\n\nReport:\n{report}"
    resp = adapter.chat(system=EVALUATOR_PROMPT, messages=[{"role": "user", "content": context}])
    try:
        text = resp["text"]
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text.strip())
    except Exception:
        return {"scores": {"total": 0}, "feedback": "평가 파싱 실패", "strength": ""}

def save_evaluation(session_path: str, evaluation: dict):
    import json, pathlib
    p = pathlib.Path(session_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding="utf-8") as f:
        f.write(json.dumps({"type": "evaluation", **evaluation}, ensure_ascii=False) + "\n")
