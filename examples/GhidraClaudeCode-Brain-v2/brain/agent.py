"""
brain/agent.py — Claude Code agent loop의 최소 구현 (v2 Phase 1)

원칙: readOnly 병렬, 쓰기 직렬, 12턴, mock 폴백.
Planner는 Phase 2에서 — 지금은 ReAct만.
"""
import json, time
from pathlib import Path

SYSTEM_PROMPT = """너는 Ghidra와 코드 분석을 하는 리버스 엔지니어링 AI다.
원칙:
1. 추측 금지 — Tool 결과에만 근거, 확신도는 CONFIRMED/LIKELY/POSSIBLE
2. 증거를 남겨라 — 어떤 함수/주소/문자열에서 판단했는지
3. 먼저 list_functions/list_strings로 전체 파악, 그 다음 깊게 파기
도구: list_functions(함수 목록), list_strings(문자열), code_read(파일 읽기), code_write(파일 쓰기), code_exec(명령 실행)
"""

class BrainAgent:
    def __init__(self, adapter, tools, router, memory=None, max_turns=12):
        self.adapter = adapter
        self.tools = tools
        self.router = router
        self.memory = memory
        self.max_turns = max_turns
        self.tool_log = []

    def _build_initial(self, task: str) -> str:
        return f"작업: {task}\n먼저 전체 구조를 파악한 뒤 증거를 모아 보고서로 정리하라."

    def run(self, task: str) -> dict:
        messages = [{"role": "user", "content": self._build_initial(task)}]
        evidence = {}
        tool_log = []

        for turn in range(self.max_turns):
            resp = self.adapter.chat(system=SYSTEM_PROMPT, messages=messages, tools=self.tools)
            text = resp.get("text", "")
            calls = resp.get("tool_calls", [])

            if text:
                # 디버그 출력 (repl.py에서 보임)
                print(f"[Agent Turn {turn+1}] {text[:400]}")

            if not calls:
                # 도구 호출 없으면 최종 보고서로 간주
                report = text or "(보고서 없음 — 증거만 있고 결론이 없습니다)"
                break

            # Claude Code 병렬 규칙: readOnly 병렬, 쓰기 직렬
            if hasattr(self.router, "dispatch_parallel"):
                # id 보정 — adapter가 주는 id 사용, 없으면 생성
                norm = []
                for idx, c in enumerate(calls):
                    norm.append({"name": c["name"], "input": c.get("input", c.get("arguments", {})), "id": c.get("id", f"c{idx}")})
                results = self.router.dispatch_parallel(norm)
                # results를 messages에 추가
                for r in results:
                    call = next(c for c in norm if c["id"] == r["id"])
                    out = r["result"]
                    evidence[call["name"]] = out
                    tool_log.append({"name": call["name"], "input": call["input"], "output": out})
                    messages.append({"role": "user", "content": f"[Tool {call['name']} result] {json.dumps(out, ensure_ascii=False)[:2000]}"})
                # assistant 메시지 기록
                messages.append({"role": "assistant", "content": text or f"Called {len(calls)} tools"})
            else:
                # 폴백 — 직렬
                for c in calls:
                    name = c["name"]
                    inp = c.get("input", c.get("arguments", {}))
                    out = self.router.dispatch(name, inp)
                    evidence[name] = out
                    tool_log.append({"name": name, "input": inp, "output": out})
                    messages.append({"role": "user", "content": f"[Tool {name} result] {json.dumps(out, ensure_ascii=False)[:2000]}"})
                messages.append({"role": "assistant", "content": text or f"Called {len(calls)} tools"})
        else:
            report = "(max_turns 도달 — 보고서 미완성)"

        # reasoning + contradiction (최소)
        try:
            from brain.reasoning import reason
            re = reason(task, evidence)
        except Exception as e:
            re = {"ok": False, "reason": str(e)}
        try:
            from brain.contradiction import check_contradiction
            contra = check_contradiction(report, evidence)
        except Exception as e:
            contra = {"ok": True, "summary": f"모순 검사 실패: {e}"}

        # 최종 보고서가 비어있으면 증거 기반으로 간단 생성
        if not report or report.startswith("("):
            report = self._fallback_report(task, evidence, re, contra)

        return {
            "report": report,
            "tool_log": tool_log,
            "evidence": evidence,
            "reasoning": re,
            "contradiction": contra,
        }

    def _fallback_report(self, task, evidence, re, contra) -> str:
        ev_summary = ", ".join(evidence.keys()) or "없음"
        funcs = evidence.get("list_functions", {}).get("functions", [])
        strs = evidence.get("list_strings", {}).get("strings", [])
        lines = [f"# {task}", ""]
        lines.append("## 증거")
        lines.append(f"- 함수 {len(funcs)}개: {funcs[:2]}")
        lines.append(f"- 문자열 {len(strs)}개: {strs[:2]}")
        lines.append(f"- 도구: {ev_summary}")
        lines.append("")
        lines.append("## 추론")
        lines.append(f"- {re.get('steps', re.get('reason', ''))}")
        lines.append("")
        lines.append("## 모순 검사")
        lines.append(f"- {contra.get('summary', '')}")
        if not contra.get("ok"):
            lines.append(f"- 강등: {contra.get('suggested_downgrades', '')}")
        return "\n".join(lines)
