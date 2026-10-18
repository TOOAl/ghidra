"""
brain/agent.py — 두뇌 본체 (ReAct + Planning + Memory 루프)

이 파일이 "나만의 Claude Code"의 핵심.
LLM이 바뀌어도 이 루프는 그대로 유지 — 그래서 두뇌는 계속 소유됨.
"""
import json
from pathlib import Path

from .model_adapter import ModelAdapter
from .planner import make_plan
from .evaluator import evaluate, save_evaluation

SYSTEM_PROMPT = """\
너는 Ghidra와 REA를 쓰는 리버스 엔지니어링 AI 두뇌다.

원칙:
1. 추측 금지 — Tool 결과에만 근거해라. 확신도는 CONFIRMED/LIKELY/POSSIBLE로 표시.
2. 항상 증거를 남겨라 — 어떤 함수, 어떤 주소에서 그렇게 판단했는지.
3. 먼저 전체를 보고, 그 다음 의심 가는 곳을 깊게 파고, 마지막에 기억(search_memory)과 대조해라.
4. 모든 결론은 Ghidra 분석 기반으로만 내리고, 마지막에 한국어로 요약 보고서를 쓴다.

도구:
- list_functions: 함수 목록
- decompile: 의사코드
- list_strings: 문자열
- get_xrefs: 호출 관계
- rename_function: 함수명 복구 (의미있는 이름으로)
- set_comment: 주석
- search_memory: 과거 기억 검색 (비슷한 함수/버그 찾음)

천재 모드 (task에 트리거 단어 있으면 해당 사고 3단계 자동 추가):
- 다빈치: 관찰→스케치→연결
- 퀴리: 측정→반복→실패로그
- 튜링: 형식화→해독→모방검증
- 오일러: 기호→일반화→우아한 계산
모순 검사: 보고서 전 check_contradiction으로 CONFIRMED 강등 여부 확인
"""

class BrainAgent:
    def __init__(self, adapter: ModelAdapter, tools: list, tool_router, memory=None, max_turns=20, use_planner=True):
        self.adapter = adapter
        self.tools = tools
        self.router = tool_router  # 실제 Ghidra/REA 호출 객체
        self.memory = memory
        self.max_turns = max_turns
        self.use_planner = use_planner

    def run(self, task: str) -> dict:
        """
        task: 사용자 자연어 요청
        반환: {"report": str, "tool_log": list, "plan": dict, "evaluation": dict}
        """
        # 1. 계획
        plan = None
        if self.use_planner:
            print("[Brain] 계획을 세우는 중...")
            plan = make_plan(self.adapter, task)
            print(f"[Brain] 계획: {json.dumps(plan, ensure_ascii=False, indent=2)}")

        # 2. ReAct 루프
        messages = [{"role": "user", "content": self._build_initial_prompt(task, plan)}]
        tool_log = []

        for turn in range(self.max_turns):
            print(f"\n{'='*60}\n[Brain Turn {turn+1}] 추론 중...")
            resp = self.adapter.chat(system=SYSTEM_PROMPT, messages=messages, tools=self.tools)

            if resp["text"]:
                print(f"[Brain] {resp['text'][:600]}")

            if not resp["tool_calls"]:
                # 도구 호출 없으면 최종 보고서로 간주
                if resp["text"]:
                    messages.append({"role": "assistant", "content": resp["text"]})
                    report = resp["text"]
                    break
                else:
                    print("[Brain] 더 이상 할 일이 없어 종료")
                    report = "(보고서 없음)"
                    break

            # 도구 실행
            assistant_msg = {"role": "assistant", "content": resp["text"] or "", "tool_calls": resp["tool_calls"]}
            # OpenAI 형식으로 변환 (어댑터에 따라 다름 — 여기서는 OpenAI 호환 가정)
            messages.append({"role": "assistant", "content": resp["text"] or ""})

            for tc in resp["tool_calls"]:
                print(f"  → Tool: {tc['name']}({json.dumps(tc['input'], ensure_ascii=False)})")
                result = self.router.dispatch(tc["name"], tc["input"])
                tool_log.append({"tool": tc["name"], "input": tc["input"], "result_preview": str(result)[:500]})
                print(f"  ← Result: {str(result)[:400]}...")
                # 결과를 다시 LLM에 전달
                messages.append({
                    "role": "user",
                    "content": f"[Tool {tc['name']} 결과]\n{json.dumps(result, ensure_ascii=False)[:4000]}"
                })

                # 기억 저장 (매 턴)
                if self.memory:
                    self.memory.add_turn(task, tc["name"], tc["input"], result)
        else:
            report = "(최대 턴 초과)"

        # 3. 모순 검사 (통합) — 보고서 전 자동
        print("\n[Brain] 모순 검사 중...")
        contra = self._contradiction_check(report, tool_log)
        print(f"[Brain] 모순: {contra['summary']}")
        if not contra["ok"]:
            print(f"[Brain] 강등 제안: {contra['suggested_downgrades']}")
            report += f"\n\n[모순 검사] {contra['summary']}\n"
            for d in contra["suggested_downgrades"]:
                report += f"- {d['from']}→{d['to']} ({d['reason']})\n"

        # 4. 평가
        print("\n[Brain] 자체 평가 중...")
        evaluation = evaluate(self.adapter, task, report, tool_log)
        print(f"[Brain] 평가: {evaluation}")

        # 5. 블록 저장 (Notion 흡수) — 보고서 1개 = 블록 1개
        try:
            from notion.blocks import create_block
            create_block(report[:500], type="text")
        except Exception:
            pass

        # 6. 세션 저장 (자가학습)
        self._save_session(task, plan, tool_log, report, evaluation)

        return {"report": report, "tool_log": tool_log, "plan": plan, "evaluation": evaluation}

    def _genius_prompt(self, task: str) -> str:
        low = task.lower()
        inject = []
        if any(k in low for k in ["다빈치", "da vinci", "관찰", "스케치"]):
            inject.append("[다빈치] 관찰→스케치(code 블록)→연결 3문장 필수")
        if any(k in low for k in ["퀴리", "curie", "측정", "반복"]):
            inject.append("[퀴리] 측정 숫자3개→반복 차이→실패로그 1문장 필수")
        if any(k in low for k in ["튜링", "turing", "형식화", "해독"]):
            inject.append("[튜링] 형식화 상태도→해독 논리식→모방 반증 1문장 필수")
        if any(k in low for k in ["오일러", "euler", "일반화", "기호"]):
            inject.append("[오일러] 기호 수식→일반화 n개→우아한 2바이트 1문장 필수")
        if "4명" in low or "조합" in low or all(k in low for k in ["다빈치", "퀴리"]):
            inject.append("[조합] 4명 각각 1문장 + 모순 검사로 교차 검증")
        return "\n".join(inject) if inject else ""

    def _contradiction_check(self, report: str, tool_log: list) -> dict:
        try:
            from .contradiction import check_contradiction
            evidence = {t["tool"]: t["input"] for t in tool_log}
            # tool result_preview도 증거에 포함
            for t in tool_log:
                evidence[t["tool"] + "_result"] = t.get("result_preview", "")
            return check_contradiction(report, evidence)
        except Exception as e:
            return {"contradictions": [], "ok": True, "summary": f"검사 실패: {e}"}

    def _build_initial_prompt(self, task: str, plan: dict = None) -> str:
        parts = [f"작업: {task}"]
        genius = self._genius_prompt(task)
        if genius:
            parts.append(f"\n[천재 모드]\n{genius}")
        if plan:
            parts.append(f"\n계획:\n{json.dumps(plan, ensure_ascii=False, indent=2)}")
        if self.memory:
            try:
                recalled = self.memory.search(task, k=3)
                if recalled:
                    parts.append(f"\n[기억에서 찾은 유사 사례]\n{json.dumps(recalled, ensure_ascii=False)[:2000]}")
            except Exception:
                pass
        parts.append("\n위 계획대로 도구를 사용해 분석을 시작해라. 보고서 전 check_contradiction으로 검증하라.")
        return "\n".join(parts)

    def _save_session(self, task, plan, tool_log, report, evaluation):
        session = {
            "task": task,
            "plan": plan,
            "tool_log": tool_log,
            "report": report,
            "evaluation": evaluation
        }
        Path("memory/session.jsonl").parent.mkdir(parents=True, exist_ok=True)
        with open("memory/session.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(session, ensure_ascii=False) + "\n")
        print("[Brain] 세션 저장 완료: memory/session.jsonl")
