#!/usr/bin/env python3
"""
run.py — 한 줄로 나만의 Claude Code 실행

예:
  python run.py --binary /bin/ls --task "main 함수 설명해줘"
  python run.py --binary samples/malware.exe --task "C2 주소 찾아줘" --preset openrouter_qwen3_free
  python run.py --binary samples/app --task "취약점 찾아줘" --provider ollama --model qwen3:32b
"""
import argparse
import json
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
import sys
sys.path.insert(0, str(Path(__file__).parent))

from brain.model_adapter import ModelAdapter, ModelConfig
from brain.agent import BrainAgent
from tools.ghidra_router import GhidraRouter
from memory.vector_store import VectorMemory

def load_tools():
    with open("tools/definitions.json", encoding="utf-8") as f:
        return json.load(f)

def main():
    p = argparse.ArgumentParser(description="GhidraClaudeCode-Brain — 무료 진화형 AI 두뇌")
    p.add_argument("--binary", required=True, help="분석할 바이너리 경로")
    p.add_argument("--task", required=True, help="자연어 작업 (예: 'C2 주소 찾아줘')")
    p.add_argument("--preset", help="config/models.yaml의 프리셋 이름 (예: local_qwen3)")
    p.add_argument("--provider", help="provider 직접 지정 (ollama/openrouter/groq/anthropic 등)")
    p.add_argument("--model", help="모델 이름 직접 지정")
    p.add_argument("--max-turns", type=int, default=20)
    args = p.parse_args()

    # 1. 모델 어댑터
    if args.preset:
        adapter = ModelAdapter.from_yaml("config/models.yaml", preset=args.preset)
        print(f"[run] 프리셋 로드: {args.preset} → {adapter.config.provider}/{adapter.config.model}")
    elif args.provider and args.model:
        # 임시 config
        import yaml
        adapter = ModelAdapter(ModelConfig(provider=args.provider, model=args.model, base_url=None))
        # Ollama 기본 URL 자동 설정
        if args.provider == "ollama" and not adapter.config.base_url:
            adapter.config.base_url = "http://localhost:11434/v1"
            adapter.config.api_key = "ollama"
        print(f"[run] 직접 지정: {args.provider}/{args.model}")
    else:
        adapter = ModelAdapter.from_yaml("config/models.yaml")
        print(f"[run] 기본 모델: {adapter.config.provider}/{adapter.config.model}")

    # 2. 도구 + 기억
    tools = load_tools()
    print(f"[run] 도구 {len(tools)}개 로드: {[t['name'] for t in tools]}")

    # Memory (ChromaDB 있으면 사용, 없으면 mock)
    try:
        memory = VectorMemory()
    except Exception as e:
        print(f"[run] Memory 초기화 실패 (mock으로 진행): {e}")
        memory = None

    # REA/Ghidra 라우터 (지금은 mock, REA 설치 시 자동 연결)
    router = GhidraRouter(memory=memory)
    # 실제 REA 연결 예 (주석 해제):
    # from mcp import Client
    # rea_client = Client("rea", command="npx", args=["rea-agents", "mcp"])
    # router = GhidraRouter(rea_client=rea_client, ghidra_plugin_url="http://127.0.0.1:8080", memory=memory)

    # 3. 두뇌 실행
    brain = BrainAgent(adapter=adapter, tools=tools, tool_router=router, memory=memory, max_turns=args.max_turns)
    print(f"\n[run] 바이너리: {args.binary}")
    print(f"[run] 작업: {args.task}")
    result = brain.run(task=args.task)

    # 4. 최종 보고서 출력
    print("\n" + "="*60)
    print("최종 보고서")
    print("="*60)
    print(result["report"])
    print("\n평가:", json.dumps(result["evaluation"], ensure_ascii=False, indent=2))
    print(f"\n세션 저장: memory/session.jsonl")
    print("다음 분석 때 이 기억이 자동으로 활용됩니다.")

if __name__ == "__main__":
    main()
