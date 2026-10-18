#!/usr/bin/env python3
"""
demo_hybrid_openrouter.py — OpenRouter 무료 모델 하이브리드 데모 (인터넷 없이 mock으로 동작)

실제로는:
  로컬 agent.py → 외부 OpenRouter API (qwen/qwen3-32b:free) → 로컬 Ghidra/기억

데모에서는:
  외부 LLM 응답을 미리 녹화한 mock으로 재현 — 인터넷 없이도 흐름을 그대로 볼 수 있음.
  실제 OpenRouter 키가 있으면 mock_llm=False로 바꾸면 진짜 API 호출.

실행: python demo_hybrid_openrouter.py --binary /bin/ls
"""
import argparse
import json
import os
import time
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent))

from tools.ghidra_router import GhidraRouter
from memory.vector_store import VectorMemory

# Mock LLM: 외부 OpenRouter가 이렇게 답한다고 가정 (녹화된 응답)
MOCK_LLM_TURNS = [
    {
        "text": "작업을 분석했습니다. 먼저 전체 구조를 파악해야 합니다.",
        "tool_calls": [{"id": "t1", "name": "list_functions", "input": {"filter": "", "limit": 20}}]
    },
    {
        "text": "main과 check_license가 의심됩니다. main을 디컴파일해 보겠습니다.",
        "tool_calls": [{"id": "t2", "name": "decompile", "input": {"name": "main"}}]
    },
    {
        "text": "main에서 문자열 참조가 보입니다. 문자열 목록을 확인합니다.",
        "tool_calls": [{"id": "t3", "name": "list_strings", "input": {"filter": "http", "limit": 50}}]
    },
    {
        "text": "C2 패턴과 유사한 과거 사례가 있는지 기억에서 찾아보겠습니다.",
        "tool_calls": [{"id": "t4", "name": "search_memory", "input": {"query": "C2 통신 함수", "k": 3}}]
    },
    {
        "text": "check_license의 호출 관계를 추적합니다.",
        "tool_calls": [{"id": "t5", "name": "get_xrefs", "input": {"name": "check_license", "direction": "both"}}]
    },
    {
        "text": "",  # 마지막 턴: 도구 호출 없이 보고서
        "tool_calls": []
    }
]

FINAL_REPORT = """\
# 분석 보고서 — C2 주소 탐색 (OpenRouter qwen/qwen3-32b:free, 무료)

## 요약
- **작업**: C2 주소 찾아줘
- **모델**: qwen/qwen3-32b:free (OpenRouter 무료, 외부 LLM)
- **도구/기억**: 로컬 Ghidra + REA + Vector DB (내 PC에만 저장)

## 발견
1. **CONFIRMED**: `list_strings`에서 `http://c2.evil.com/api` 발견 — 0x00401234 주소에 저장됨
2. **LIKELY**: `main` 함수(0x401000)가 `check_license`를 호출하며, 이 함수가 위 C2 문자열을 `WSAConnect`로 전송
3. **기억 대조**: 과거 사례 "2024-10 악성코드 A"와 91% 유사 (memory/chroma_db)

## 조치
- `FUN_00401200` → `decrypt_config` 로 이름 복구 제안 (rename_function)
- `check_license`에 주석 추가: "C2 통신 — 외부 LLM 분석, 증거: decompile 12번째 줄"

## 비용
- 외부 LLM: 0원 (OpenRouter Free Tier)
- 로컬 도구/기억: 0원
- 바이너리 원본: 외부로 전송 안 됨 (의사코드 조각만 전송)

## 다음 단계
- 실제 환경에서는 `Ghidra 플러그인(쓰기)`가 위 rename/comment를 DB에 반영
- `memory/chroma_db`에 이번 분석 자동 저장 → 다음 분석 때 재사용
"""

class MockOpenRouterAdapter:
    """외부 OpenRouter LLM을 흉내내는 mock — 인터넷 없이 데모"""
    def __init__(self, model="qwen/qwen3-32b:free"):
        self.model = model
        self.turn = 0
        self.provider = "openrouter"
        self.config = type("obj", (), {"provider": "openrouter", "model": model})()

    def chat(self, system, messages, tools=None):
        # 실제라면 여기서 requests.post("https://openrouter.ai/api/v1/chat/completions", ...) 호출
        print(f"\n[외부 LLM 호출 → {self.model} @ OpenRouter (무료)]")
        print(f"  보내는 것: system={system[:60]}..., messages={len(messages)}개, tools={len(tools) if tools else 0}개")
        print(f"  (실제 환경에서는 의사코드 조각 + 질문만 전송, 원본 바이너리는 로컬에만 있음)")

        if self.turn < len(MOCK_LLM_TURNS):
            resp = MOCK_LLM_TURNS[self.turn]
            self.turn += 1
            # 마지막 턴은 보고서
            if self.turn == len(MOCK_LLM_TURNS):
                resp = {"text": FINAL_REPORT, "tool_calls": []}
            print(f"  ← 외부 LLM 응답: {resp['text'][:80]}...")
            if resp["tool_calls"]:
                print(f"     tool_calls: {[c['name'] for c in resp['tool_calls']]}")
            return resp
        return {"text": FINAL_REPORT, "tool_calls": []}


def main():
    parser = argparse.ArgumentParser(description="OpenRouter 무료 하이브리드 데모")
    parser.add_argument("--binary", default="/bin/ls", help="분석할 바이너리 (데모는 mock이므로 어떤 파일이든 가능)")
    parser.add_argument("--real", action="store_true", help="진짜 OpenRouter API 호출 (OPENROUTER_API_KEY 필요)")
    args = parser.parse_args()

    print("="*70)
    print(" GhidraClaudeCode-Brain — 하이브리드 데모")
    print(" 외부 LLM(무료) + 로컬 도구/기억/스킬")
    print("="*70)
    print(f"\n[설정]")
    print(f"  바이너리: {args.binary} (로컬에만 존재, 외부로 안 나감)")
    print(f"  외부 LLM: qwen/qwen3-32b:free @ OpenRouter (무료, https://openrouter.ai)")
    print(f"  로컬 도구: Ghidra(읽기) + 플러그인(쓰기) + Vector DB")
    print(f"  모드: {'REAL API 호출' if args.real else 'MOCK 데모 (인터넷 없이 동작, 흐름 동일)'}")

    # 1. OpenRouter 무료 키 안내
    print(f"\n[OpenRouter 무료 키 발급 방법 — 1분]")
    print(f"  1. https://openrouter.ai 접속 → Sign in (GitHub/Google)")
    print(f"  2. https://openrouter.ai/settings/keys → Create Key")
    print(f"  3. export OPENROUTER_API_KEY=sk-or-v1-...")
    print(f"  4. 무료 모델 목록: https://openrouter.ai/models?filter=free")
    print(f"     - qwen/qwen3-32b:free (추천, 추론 강함)")
    print(f"     - deepseek/deepseek-r1:free")
    print(f"     - meta-llama/llama-3.3-70b-instruct:free")
    print(f"     - google/gemma-3-27b-it:free")

    if args.real:
        key = os.getenv("OPENROUTER_API_KEY")
        if not key:
            print("\n[에러] OPENROUTER_API_KEY 환경변수가 없습니다. 위 방법으로 키를 발급받아 export 해주세요.")
            return
        print(f"\n[REAL 모드] 키 확인: {key[:10]}... (외부 LLM에 실제 호출)")

        from brain.model_adapter import ModelAdapter, ModelConfig
        adapter = ModelAdapter(ModelConfig(
            provider="openai_compatible",
            model="qwen/qwen3-32b:free",
            base_url="https://openrouter.ai/api/v1",
            api_key=key
        ))
    else:
        print(f"\n[MOCK 모드] 외부 LLM 응답을 녹화된 데이터로 재현 (인터넷 불필요, 실제와 동일 흐름)")
        adapter = MockOpenRouterAdapter()

    # 2. 로컬 도구/기억 로드
    import json as _json
    with open("tools/definitions.json", encoding="utf-8") as f:
        tools = _json.load(f)
    print(f"\n[로컬] 도구 {len(tools)}개 로드: {[t['name'] for t in tools]}")
    print(f"[로컬] 기억: memory/chroma_db (로컬 Vector DB, 외부로 안 나감)")
    print(f"[로컬] 스킬: skills/find_c2.md, skills/find_vuln.md (로컬)")

    try:
        memory = VectorMemory()
    except Exception as e:
        print(f"[로컬] Memory mock으로 진행: {e}")
        memory = None

    router = GhidraRouter(memory=memory)
    print(f"[로컬] Ghidra Router 준비 (REA 읽기 + 플러그인 쓰기 + Memory)")

    # 3. Brain Loop (하이브리드)
    print(f"\n{'='*70}")
    print(f" 작업: \"C2 주소 찾아줘\"")
    print(f" 바이너리: {args.binary}")
    print(f"{'='*70}")

    # 간단한 ReAct 루프 (brain/agent.py와 동일 로직, 데모용 간소화)
    system_prompt = open("skills/SKILL.md", encoding="utf-8").read() if Path("skills/SKILL.md").exists() else "너는 리버싱 AI다."
    messages = [{"role": "user", "content": f"바이너리 {args.binary}에서 C2 주소 찾아줘. 증거와 함께 한국어로 보고해줘."}]

    for turn in range(6):
        print(f"\n{'-'*70}")
        print(f"[Turn {turn+1}] 로컬 agent.py → 외부 LLM에 질문")
        time.sleep(0.5)
        resp = adapter.chat(system=system_prompt, messages=messages, tools=tools)

        if resp["text"]:
            print(f"[외부 LLM 생각] {resp['text'][:400]}")

        if not resp["tool_calls"]:
            print(f"\n{'='*70}")
            print(f" 최종 보고서 (외부 LLM이 생성, 로컬에서 저장)")
            print(f"{'='*70}")
            print(resp["text"])
            # 로컬에 저장
            Path("memory").mkdir(exist_ok=True)
            with open("memory/session.jsonl", "a", encoding="utf-8") as f:
                f.write(_json.dumps({"task": "C2 주소 찾아줘", "model": "qwen/qwen3-32b:free", "report": resp["text"]}, ensure_ascii=False) + "\n")
            print(f"\n[로컬] memory/session.jsonl 에 저장 완료 — 다음 분석 때 자동 재사용")
            print(f"[로컬] memory/chroma_db 에 함수 임베딩 저장 — 영구 기억")
            break

        # 도구 실행은 항상 로컬에서!
        for tc in resp["tool_calls"]:
            print(f"\n[로컬 실행] Tool: {tc['name']}({tc['input']})")
            print(f"  → Ghidra/REA/Memory가 내 PC에서 실행 (외부로 안 나감)")
            result = router.dispatch(tc["name"], tc["input"])
            print(f"  ← 결과: {str(result)[:350]}...")
            # 결과를 다시 외부 LLM에 전달 (의사코드 조각만)
            messages.append({"role": "assistant", "content": resp["text"]})
            messages.append({"role": "user", "content": f"[Tool {tc['name']} 결과]\n{_json.dumps(result, ensure_ascii=False)[:2000]}"})
            if memory:
                try:
                    memory.add_turn("C2 주소 찾아줘", tc["name"], tc["input"], result)
                except Exception:
                    pass

    print(f"\n{'='*70}")
    print(f" 하이브리드 완료!")
    print(f" - 외부 LLM 비용: 0원 (OpenRouter Free)")
    print(f" - 로컬 자산: memory/session.jsonl, memory/chroma_db, skills/*.md (내 PC에만 저장)")
    print(f" - 진화: 다음 모델이 나오면 config/models.yaml 한 줄 변경으로 업그레이드")
    print(f"{'='*70}")
    print(f"\n[다음에 진짜로 돌리는 법]")
    print(f"  export OPENROUTER_API_KEY=sk-or-v1-...")
    print(f"  python demo_hybrid_openrouter.py --binary ./your_binary --real")
    print(f"  # 또는")
    print(f"  python run.py --binary ./your_binary --task \"C2 주소 찾아줘\" --preset openrouter_free_generic")
    print(f"\n[로컬 전용(완전 오프라인)도 가능]")
    print(f"  ollama pull qwen3:14b && python run.py --binary ./your_binary --task \"...\" --preset local_qwen3")

if __name__ == "__main__":
    main()
