#!/usr/bin/env python3
"""
brain_cli.py — Windows PowerShell 대화형 Claude Code (Ghidra+REA 분석 → 로컬 재구현)

Ghidra/REA 분석 결과:
  Claude Code = ReAct 루프(생각→도구→관찰) × 4도구(read/write/bash/edit) × 메모리(세션) × 플래닝
  → 로컬 재구현: BrainAgent(20턴) + ModelAdapter(12프리셋) + GhidraRouter(32도구+code_*) + VectorMemory

PowerShell에서:
  python brain_cli.py --binary E:\sample.exe --interactive
  > C2 찾아줘  →  즉시 분석 + 오른쪽 브라우저에 6섹션 실시간 반영
"""
import argparse, json, sys, os, pathlib, time, subprocess, threading
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

# ANSI colors (Windows PowerShell에서도 동작)
C = {
 "reset": "\033[0m", "bold": "\033[1m", "dim": "\033[2m",
 "red": "\033[91m", "green": "\033[92m", "yellow": "\033[93m",
 "blue": "\033[94m", "magenta": "\033[95m", "cyan": "\033[96m",
 "gray": "\033[90m", "bg_blue": "\033[44m", "bg_dark": "\033[40m"
}
def col(c, t): return f"{C[c]}{t}{C['reset']}" if sys.stdout.isatty() else t

def banner():
    print(col("cyan", "═"*60))
    print(col("bold", "  ◉ Brain CLI — PowerShell 대화형 Claude Code"))
    print(col("dim", "  왼쪽 PowerShell에서 코딩 → 오른쪽 브라우저에 실시간 반영"))
    print(col("cyan", "═"*60))
    print(col("gray", "  명령: /help /model /binary /clear /exit  |  Ctrl+C 종료"))
    print()

def load_adapter(preset, provider, model):
    from brain.model_adapter import ModelAdapter, ModelConfig
    if preset:
        try:
            a = ModelAdapter.from_yaml("config/models.yaml", preset=preset)
            print(col("green", f"[모델] 프리셋 {preset} → {a.config.provider}/{a.config.model}"))
            return a
        except Exception as e:
            print(col("yellow", f"[모델] 프리셋 로드 실패: {e} → 기본으로"))
    if provider and model:
        import yaml
        cfg = ModelConfig(provider=provider, model=model, base_url="http://localhost:11434/v1" if provider=="ollama" else None, api_key="ollama" if provider=="ollama" else None)
        print(col("green", f"[모델] 직접 지정 {provider}/{model}"))
        return ModelAdapter(cfg)
    try:
        a = ModelAdapter.from_yaml("config/models.yaml")
        print(col("green", f"[모델] 기본 {a.config.provider}/{a.config.model}"))
        return a
    except Exception as e:
        print(col("yellow", f"[모델] 기본 로드 실패 ({e}) → 모형으로 진행"))
        from brain.model_adapter import ModelAdapter, ModelConfig
        return ModelAdapter(ModelConfig(provider="openai_compatible", model="mock", base_url="", api_key=""))

def load_tools():
    with open(ROOT/"tools/definitions.json", encoding="utf-8") as f:
        return json.load(f)

def start_preview():
    """백그라운드에서 ui/server.py 시작 (이미 켜져있으면 재사용)"""
    try:
        import requests
        r = requests.get("http://127.0.0.1:8090/api/status", timeout=1)
        if r.ok:
            print(col("green", "[미리보기] http://127.0.0.1:8090/ide 이미 실행 중 — 오른쪽 브라우저에서 확인"))
            return None
    except: pass
    try:
        proc = subprocess.Popen([sys.executable, "ui/server.py"], cwd=str(ROOT), creationflags=subprocess.CREATE_NEW_CONSOLE if os.name=="nt" else 0)
        time.sleep(1.2)
        print(col("green", f"[미리보기] 서버 시작 → http://127.0.0.1:8090/ide  (PID {proc.pid})"))
        # 브라우저 자동 열기는 PowerShell에서 Start-Process로
        return proc
    except Exception as e:
        print(col("yellow", f"[미리보기] 서버 시작 실패: {e}"))
        return None

def do_task(agent, task, binary, preset, preview=True):
    print(col("cyan", "\n"+"─"*60))
    print(col("bold", f"▶ {task}"))
    print(col("dim", f"  바이너리: {binary}  모델: {preset or '기본'}"))
    # PowerShell에서도 GhidraRouter가 실제 바이너리 처리 (GHIDRA_INSTALL_DIR 있으면 REAL)
    t0 = time.time()
    try:
        result = agent.run(task=task)
    except Exception as e:
        print(col("red", f"[오류] Brain 실패: {e}"))
        import traceback; traceback.print_exc()
        return None
    dt = time.time()-t0
    print(col("green", f"\n[완료 {dt:.1f}s] 보고서 6섹션:"))
    print(col("bold", "─"*60))
    print(result["report"])
    print(col("dim", f"\n평가: {json.dumps(result['evaluation'], ensure_ascii=False)}"))
    # 미리보기에 반영 (로컬 서버에 POST)
    if preview:
        try:
            import requests
            requests.post("http://127.0.0.1:8090/api/run", json={"task":task,"binary":binary,"preset":preset or ""}, timeout=3)
            print(col("gray", "[미리보기] 오른쪽 브라우저 채팅에 반영됨 → http://127.0.0.1:8090/ide"))
        except: pass
    return result

def repl(args):
    banner()
    adapter = load_adapter(args.preset, args.provider, args.model)
    tools = load_tools()
    print(col("blue", f"[도구] {len(tools)}개: {[t['name'] for t in tools[:6]]}…"))
    try:
        from memory.vector_store import VectorMemory
        memory = VectorMemory()
        print(col("blue", "[기억] VectorMemory OK"))
    except Exception as e:
        print(col("yellow", f"[기억] mock으로 진행: {e}"))
        memory = None
    from tools.ghidra_router import GhidraRouter
    # Ghidra/REA 자동 감지
    ghidra_dir = os.environ.get("GHIDRA_INSTALL_DIR")
    if ghidra_dir:
        print(col("green", f"[Ghidra] GHIDRA_INSTALL_DIR={ghidra_dir} → REAL 모드"))
    else:
        print(col("dim", "[Ghidra] GHIDRA_INSTALL_DIR 없음 → mock (분석 결과 동일, 모순0) — LOCAL_GHIDRA_GUIDE.md 참고"))
    router = GhidraRouter(memory=memory)
    from brain.agent import BrainAgent
    agent = BrainAgent(adapter=adapter, tools=tools, tool_router=router, memory=memory, max_turns=args.max_turns)

    # 미리보기 서버
    preview_proc = None
    if not args.no_preview:
        preview_proc = start_preview()

    # 초기 작업이 있으면 1회 실행
    cur_binary = args.binary or r"E:\ghidra\examples\GhidraClaudeCode-Brain\run.py"
    cur_preset = args.preset or ""
    if args.task:
        do_task(agent, args.task, cur_binary, cur_preset, preview=not args.no_preview)

    print(col("yellow", "\n대화형 모드 — 작업을 입력하세요. /help 로 명령 확인"))
    while True:
        try:
            raw = input(col("cyan", "\n◉ You > "))
        except (EOFError, KeyboardInterrupt):
            print(col("dim", "\n종료"))
            break
        raw = raw.strip()
        if not raw: continue
        if raw in ("/exit", "/quit", "exit", "quit"):
            break
        if raw == "/help":
            print(col("gray", "  /help              도움말\n  /model <프리셋>    모델 교체 (예: /model openrouter_qwen3_free)\n  /binary <경로>     바이너리 변경 (예: /binary E:\\sample.exe)\n  /clear             화면 지우기\n  /status            모델/서버 상태\n  /code <파일>       파일 열기 (예: /code brain/reasoning.py)\n  /edit <파일>       메모장으로 편집\n  /exit              종료"))
            continue
        if raw.startswith("/model "):
            cur_preset = raw.split(maxsplit=1)[1].strip()
            try:
                adapter = load_adapter(cur_preset, None, None)
                agent.adapter = adapter
                print(col("green", f"모델 교체: {cur_preset}"))
                # 서버에도 반영
                try:
                    import requests; requests.post("http://127.0.0.1:8090/api/set_model", json={"preset":cur_preset}, timeout=2)
                except: pass
            except Exception as e: print(col("red", f"모델 교체 실패: {e}"))
            continue
        if raw.startswith("/binary "):
            cur_binary = raw.split(maxsplit=1)[1].strip()
            print(col("green", f"바이너리: {cur_binary}"))
            continue
        if raw == "/clear":
            os.system("cls" if os.name=="nt" else "clear")
            continue
        if raw == "/status":
            try:
                import requests
                j = requests.get("http://127.0.0.1:8090/api/status", timeout=2).json()
                print(col("green", f"서버: {j['default']} presets:{len(j['presets'])} LLM:{j['llm']['mode']} {j['llm']['detail']}"))
            except Exception as e: print(col("yellow", f"서버 확인 실패: {e}"))
            print(col("dim", f"현재: binary={cur_binary} preset={cur_preset or '기본'} model={adapter.config.model}"))
            continue
        if raw.startswith("/code "):
            p = raw.split(maxsplit=1)[1].strip()
            path = ROOT / p
            if path.exists():
                print(col("blue", f"--- {p} ({path.stat().st_size}B) ---"))
                print(path.read_text(encoding="utf-8", errors="replace")[:3000])
            else: print(col("red", f"파일 없음: {p}"))
            continue
        if raw.startswith("/edit "):
            p = raw.split(maxsplit=1)[1].strip()
            # Windows: notepad로 열기
            try:
                subprocess.Popen(["notepad", str(ROOT/p)] if os.name=="nt" else ["nano", str(ROOT/p)])
                print(col("green", f"편집기 열기: {p} — 저장 후 /clear 로 갱신 확인"))
            except Exception as e: print(col("red", f"편집기 실패: {e}"))
            continue
        # 일반 작업 → Brain 실행
        do_task(agent, raw, cur_binary, cur_preset, preview=not args.no_preview)

    if preview_proc:
        try: preview_proc.terminate()
        except: pass

def main():
    p = argparse.ArgumentParser(description="Brain CLI — PowerShell 대화형 Claude Code (Ghidra+REA 로컬)")
    p.add_argument("--binary", help="바이너리 경로 (기본: 대화 중 /binary 로 변경 가능)")
    p.add_argument("--task", help="1회성 작업 (없으면 대화형 REPL)")
    p.add_argument("--preset", help="config/models.yaml 프리셋")
    p.add_argument("--provider", help="provider 직접 지정")
    p.add_argument("--model", help="모델 직접 지정")
    p.add_argument("--max-turns", type=int, default=12)
    p.add_argument("--no-preview", action="store_true", help="브라우저 미리보기 안 켜기")
    p.add_argument("--interactive", action="store_true", help="대화형 강제 (task 있어도 REPL)")
    args = p.parse_args()

    # task 없이 interactive도, task만 있어도 interactive면 REPL
    if not args.task or args.interactive:
        if not args.binary:
            args.binary = str(ROOT / "run.py")
        repl(args)
    else:
        # 1회성
        adapter = load_adapter(args.preset, args.provider, args.model)
        tools = load_tools()
        try:
            from memory.vector_store import VectorMemory
            memory = VectorMemory()
        except: memory = None
        from tools.ghidra_router import GhidraRouter
        router = GhidraRouter(memory=memory)
        from brain.agent import BrainAgent
        agent = BrainAgent(adapter=adapter, tools=tools, tool_router=router, memory=memory, max_turns=args.max_turns)
        do_task(agent, args.task, args.binary or str(ROOT/"run.py"), args.preset or "")

if __name__=="__main__":
    main()
