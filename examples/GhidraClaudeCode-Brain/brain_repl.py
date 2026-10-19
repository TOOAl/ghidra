#!/usr/bin/env python3
"""
brain_repl.py — Python에서 Claude Code처럼 (대화형 코딩 + 오른쪽 실시간 실행)

실행:
  cd E:\ghidra\examples\GhidraClaudeCode-Brain
  python brain_repl.py
  >>> C2 찾아줘
  >>> /code brain/reasoning.py
  >>> /edit brain/reasoning.py
  >>> x = brain.run("취약점 찾아줘")  # Python 코드도 그대로 실행

특징: Python REPL 그대로 — import brain, brain.run() 처럼 코딩하면
      왼쪽 Python에서 친 코드가 오른쪽 브라우저(http://127.0.0.1:8090/ide)에 실시간으로 뜬다.
"""
import sys, os, pathlib, code, time, json, subprocess, threading, importlib
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

C = {"reset":"\033[0m","bold":"\033[1m","dim":"\033[2m","red":"\033[91m","green":"\033[92m","yellow":"\033[93m","blue":"\033[94m","cyan":"\033[96m","gray":"\033[90m"}
def col(c,t): return f"{C[c]}{t}{C['reset']}" if sys.stdout.isatty() else t

def start_preview():
    try:
        import requests
        r=requests.get("http://127.0.0.1:8090/api/status",timeout=1)
        if r.ok:
            j=r.json()
            print(col("green", f"[미리보기] http://127.0.0.1:8090/ide 실행 중 — presets:{len(j['presets'])} LLM:{j['llm']['mode']}"))
            return None
    except: pass
    try:
        proc=subprocess.Popen([sys.executable, "ui/server.py"], cwd=str(ROOT), creationflags=subprocess.CREATE_NEW_CONSOLE if os.name=="nt" else 0)
        time.sleep(1)
        print(col("green", f"[미리보기] 서버 시작 → http://127.0.0.1:8090/ide (PID {proc.pid}) — 브라우저에서 확인"))
        return proc
    except Exception as e:
        print(col("yellow", f"[미리보기] 시작 실패: {e}"))
        return None

# Brain 객체 — Python에서 import brain처럼 쓰기 쉽게
class Brain:
    def __init__(self, preset="", binary="", max_turns=12, preview=True):
        from brain.model_adapter import ModelAdapter, ModelConfig
        from tools.ghidra_router import GhidraRouter
        import json as _j
        # adapter
        try:
            self.adapter = ModelAdapter.from_yaml("config/models.yaml", preset=preset) if preset else ModelAdapter.from_yaml("config/models.yaml")
        except Exception:
            self.adapter = ModelAdapter(ModelConfig(provider="openai_compatible", model="mock", base_url="", api_key=""))
        with open(ROOT/"tools/definitions.json", encoding="utf-8") as f:
            self.tools = _j.load(f)
        try:
            from memory.vector_store import VectorMemory
            self.memory = VectorMemory()
        except: self.memory = None
        self.router = GhidraRouter(memory=self.memory)
        from brain.agent import BrainAgent
        self.agent = BrainAgent(adapter=self.adapter, tools=self.tools, tool_router=self.router, memory=self.memory, max_turns=max_turns)
        self.binary = binary or str(ROOT/"run.py")
        self.preset = preset or ""
        self.preview = preview
        print(col("green", f"[Brain] {self.adapter.config.provider}/{self.adapter.config.model} · 도구 {len(self.tools)}개 · {self.binary}"))

    def run(self, task, binary=None, preset=None):
        bin_path = binary or self.binary
        pre = preset if preset is not None else self.preset
        print(col("cyan", f"\n▶ {task}"))
        t0=time.time()
        result = self.agent.run(task=task)
        dt=time.time()-t0
        print(col("green", f"[완료 {dt:.1f}s]"))
        print(result["report"])
        # 오른쪽 브라우저에 실시간 반영
        if self.preview:
            try:
                import requests
                requests.post("http://127.0.0.1:8090/api/run", json={"task":task,"binary":bin_path,"preset":pre}, timeout=3)
                print(col("gray", "[미리보기] 오른쪽 채팅에 반영됨 → http://127.0.0.1:8090/ide"))
            except: pass
        return result

    def code(self, path):
        p=ROOT/path
        if p.exists():
            print(col("blue", f"--- {path} ({p.stat().st_size}B) ---"))
            txt=p.read_text(encoding="utf-8", errors="replace")
            print(txt[:4000])
            if len(txt)>4000: print(col("dim", f"... {len(txt)-4000}자 더 있음"))
            return txt
        else: print(col("red", f"파일 없음: {path}")); return None

    def edit(self, path):
        p=ROOT/path
        try:
            if os.name=="nt": subprocess.Popen(["notepad", str(p)])
            else: subprocess.Popen(["nano", str(p)])
            print(col("green", f"편집기 열기: {path}"))
        except Exception as e: print(col("red", str(e)))

    def set_model(self, preset):
        from brain.model_adapter import ModelAdapter
        self.adapter = ModelAdapter.from_yaml("config/models.yaml", preset=preset)
        self.preset = preset
        print(col("green", f"모델 교체: {preset} → {self.adapter.config.provider}/{self.adapter.config.model}"))
        try:
            import requests; requests.post("http://127.0.0.1:8090/api/set_model", json={"preset":preset}, timeout=2)
        except: pass

    def status(self):
        try:
            import requests
            j=requests.get("http://127.0.0.1:8090/api/status", timeout=2).json()
            print(col("green", f"서버: {j['default']} presets:{len(j['presets'])} LLM:{j['llm']['mode']} {j['llm']['detail']}"))
        except Exception as e: print(col("yellow", f"서버 확인 실패: {e}"))
        print(f"Brain: {self.adapter.config.provider}/{self.adapter.config.model} binary={self.binary} preset={self.preset}")

# REPL
INTRO = col("cyan","═"*60)+"\n"+col("bold","  Python 대화형 Claude Code — 왼쪽 코딩 ↔ 오른쪽 실행")+"\n"+col("dim","  Python 코드 그대로 치면 오른쪽 브라우저에 실시간 반영")+"\n"+col("cyan","═"*60)+"""
예시:
  >>> brain.run("C2 찾아줘")
  >>> brain.code("brain/reasoning.py")
  >>> brain.edit("brain/reasoning.py")  # notepad 열기
  >>> brain.set_model("openrouter_qwen3_free")
  >>> brain.status()
  >>> x=5; print(x*2)  # 일반 Python도 그대로 동작
종료: exit() 또는 Ctrl+Z, Enter
"""

def main():
    import argparse
    ap=argparse.ArgumentParser(description="Python 대화형 Claude Code")
    ap.add_argument("--preset", default="", help="모델 프리셋")
    ap.add_argument("--binary", default="", help="기본 바이너리")
    ap.add_argument("--no-preview", action="store_true")
    args=ap.parse_args()

    print(INTRO)
    preview_proc = None if args.no_preview else start_preview()
    brain = Brain(preset=args.preset, binary=args.binary, preview=not args.no_preview)
    # REPL 네임스페이스 — brain 객체 + 자주 쓰는 것들 미리 import
    ns = {
        "brain": brain,
        "Brain": Brain,
        "ROOT": ROOT,
        "Path": Path,
        "run": brain.run,
        "code": brain.code,
        "edit": brain.edit,
    }
    # 편리한 추가 import
    try:
        import brain.reasoning as reasoning
        import brain.model_adapter as model_adapter
        import tools.ghidra_router as ghidra_router
        ns.update({"reasoning": reasoning, "model_adapter": model_adapter, "ghidra_router": ghidra_router})
    except: pass

    print(col("yellow","대화형 Python — brain.run(\"...\") 또는 Python 코드 입력"))
    # code.interact 사용 — Python REPL 그대로
    try:
        import readline
    except: pass
    console = code.InteractiveConsole(locals=ns)
    console.interact(banner="")
    if preview_proc:
        try: preview_proc.terminate()
        except: pass

if __name__=="__main__":
    main()
