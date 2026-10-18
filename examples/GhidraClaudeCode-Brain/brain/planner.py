"""
brain/planner.py — 장기 계획 (Planning)

간단한 ReAct는 한 번에 한 걸음만 생각.
Planner는 시작 전에 전체 지도를 그림.
고급 LLM일수록 계획이 좋아지므로, 모델을 바꾸면 자동으로 계획 능력이 진화함.
"""

PLANNER_PROMPT = """\
너는 리버스 엔지니어링 작업의 플래너야.
사용자의 목표를 3~5단계의 구체적인 단계로 나눠라.

각 단계는:
- goal: 이 단계에서 달성할 것
- tools: 필요한 도구 (list_functions, decompile, get_xrefs, list_strings, search_memory 등)
- success: 이 단계가 끝났다고 판단하는 기준

JSON으로만 답해:
{
  "steps": [
    {"id": 1, "goal": "...", "tools": ["..."], "success": "..."},
    ...
  ]
}
"""

def make_plan(adapter, task: str) -> dict:
    """
    adapter: ModelAdapter
    task: 사용자 요청 (예: "C2 주소 찾아줘")
    반환: {"steps": [...]}
    """
    import json
    resp = adapter.chat(
        system=PLANNER_PROMPT,
        messages=[{"role": "user", "content": task}],
        tools=None
    )
    try:
        # LLM이 JSON을 코드블록으로 감싸도 파싱
        text = resp["text"]
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text.strip())
    except Exception:
        # 파싱 실패 시 기본 계획
        return {
            "steps": [
                {"id": 1, "goal": "전체 구조 파악", "tools": ["list_functions", "list_strings"], "success": "함수 목록 확보"},
                {"id": 2, "goal": "핵심 함수 분석", "tools": ["decompile", "get_xrefs"], "success": "의심 함수 의사코드 확보"},
                {"id": 3, "goal": "기억 대조", "tools": ["search_memory"], "success": "유사 사례 찾음"},
                {"id": 4, "goal": "보고서 작성", "tools": [], "success": "증거 포함 보고서 완성"},
            ]
        }
