"""
agent.py — GhidraClaudeCode 메인 에이전트 루프 (ReAct 패턴)

Claude Code의 핵심은:
  1) LLM이 Task를 보고 도구 호출을 계획
  2) 도구를 실행하고 결과를 다시 LLM에 피드백
  3) 완료될 때까지 반복

Ghidra 버전도 동일 — 도구만 Ghidra API로 바뀌었을 뿐.
"""
import os
import json
from ghidra_tools import GHIDRA_TOOLS, GhidraBackend
from prompts import SYSTEM_PROMPT

# anthropic SDK가 있으면 실제 호출, 없으면 mock 동작
try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False
    print("[agent] anthropic SDK 미설치 — mock 모드로 동작 (pip install anthropic)")


def run_agent(binary: str, task: str, max_turns: int = 10):
    backend = GhidraBackend(binary)

    if HAS_ANTHROPIC and os.getenv("ANTHROPIC_API_KEY"):
        client = anthropic.Anthropic()
        messages = [{"role": "user", "content": task}]

        for turn in range(max_turns):
            print(f"\n{'='*60}\n[Turn {turn+1}] LLM 호출 중...")
            resp = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                tools=GHIDRA_TOOLS,
                messages=messages
            )
            print(f"  stop_reason: {resp.stop_reason}")

            # LLM의 텍스트 출력
            for block in resp.content:
                if block.type == "text":
                    print(f"  [LLM] {block.text[:500]}")
                    messages.append({"role": "assistant", "content": resp.content})
                elif block.type == "tool_use":
                    print(f"  [Tool Call] {block.name}({json.dumps(block.input, ensure_ascii=False)})")
                    result = backend.dispatch(block.name, block.input)
                    print(f"  [Tool Result] {json.dumps(result, ensure_ascii=False)[:400]}...")
                    # 결과를 다시 LLM에 전달
                    messages.append({"role": "assistant", "content": resp.content})
                    messages.append({
                        "role": "user",
                        "content": [{
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(result, ensure_ascii=False)
                        }]
                    })
                    break
            else:
                # tool_use가 없었고 텍스트만 있으면 종료 조건 확인
                if resp.stop_reason == "end_turn":
                    print("\n[완료] 에이전트가 작업을 마쳤습니다.")
                    break

    else:
        # Mock 데모: 실제 API 없이 흐름 시연
        print(f"\n[Mock Agent] Task: {task}")
        print(f"[Mock Agent] Binary: {binary}")
        print("[Mock Agent] 시뮬레이션 루프:")
        steps = [
            ("list_functions", {"filter": "", "limit": 20}),
            ("decompile_function", {"name": "main"}),
            ("get_xrefs", {"name": "check_license", "direction": "both"}),
            ("rename_function", {"old_name": "FUN_00401200", "new_name": "decrypt_config"}),
            ("set_comment", {"name": "check_license", "comment": "라이선스 검증 — 취약점 후보: strcmp 사용"}),
        ]
        for name, inp in steps:
            print(f"  → {name}({inp})")
            result = backend.dispatch(name, inp)
            print(f"    ← {json.dumps(result, ensure_ascii=False)[:200]}")
        print("\n[Mock 완료] 실제 환경에서는 Claude가 위 도구 호출을 자율적으로 결정합니다.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="GhidraClaudeCode — Ghidra 기반 리버싱 에이전트")
    parser.add_argument("--binary", required=True, help="분석할 바이너리 경로")
    parser.add_argument("--task", required=True, help="자연어 작업 지시 (예: 'main 함수 취약점 분석')")
    parser.add_argument("--max-turns", type=int, default=10)
    args = parser.parse_args()
    run_agent(args.binary, args.task, args.max_turns)
