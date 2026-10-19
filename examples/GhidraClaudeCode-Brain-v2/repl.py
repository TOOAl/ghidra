#!/usr/bin/env python3
"""
repl.py — v2 유일한 REPL (Claude Code + Notion + Obsidian 통합)

PowerShell:
  cd E:\ghidra\examples\GhidraClaudeCode-Brain-v2
  python repl.py
  >>> C2 찾아줘              ← 자연어 (한글) 바로 → agent 12턴 → Notion 블록 + Obsidian .md + 브라우저 채팅 동시 저장
  >>> /code vault/C2-1019.md  ← vault 노트 보기
  >>> /graph                  ← vault 그래프 정보
  >>> /blocks                 ← notion 블록 목록
  >>> x=5; print(x*2)        ← 일반 Python도 그대로
"""
import sys, os, pathlib, code, time, json, subprocess
from pathlib import Path
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))
C = {"reset":"\033[0m","bold":"\033[1m","dim":"\033[2m","red":"\033[91m","green":"\033[92m","yellow":"\033[93m","blue":"\033[94m","cyan":"\033[96m","gray":"\033[90m"}
def col(c,t): return f"{C[c]}{t}{C['reset']}" if sys.stdout.isatty() else t

def start_preview():
    try:
        import requests
        r=requests.get("http://127.0.0.1:8090/api/status", timeout=1)
        if r.ok:
            j=r.json()
            print(col("green", f"[미리보기] http://127.0.0.1:8090/ide 실행 중 — {j.get('presets',[])[:3]} LLM:{j.get('llm',{}).get('mode')}"))
            return None
    except: pass
    try:
        proc=subprocess.Popen([sys.executable, "ui/server.py"], cwd=str(ROOT), creationflags=subprocess.CREATE_NEW_CONSOLE if os.name=="nt" else 0)
        time.sleep(1)
        print(col("green", f"[미리보기] 서버 시작 → http://127.0.0.1:8090/ide (PID {proc.pid})"))
        return proc
    except Exception as e:
        print(col("yellow", f"[미리보기] 시작 실패: {e}"))
        return None

class Brain:
    def __init__(self, preset="", binary="", max_turns=12, preview=True):
        from brain.model_adapter import ModelAdapter, ModelConfig
        from tools.router import Router
        # adapter — pyyaml 없어도 mock으로
        try:
            self.adapter = ModelAdapter.from_yaml("config/models.yaml", preset=preset) if preset else ModelAdapter.from_yaml("config/models.yaml")
        except Exception:
            self.adapter = ModelAdapter(ModelConfig(provider="openai_compatible", model="mock", base_url="", api_key=""))
        with open(ROOT/"tools/definitions.json", encoding="utf-8") as f:
            self.tools = json.load(f)
        self.router = Router(root=ROOT)
        from brain.agent import BrainAgent
        self.agent = BrainAgent(adapter=self.adapter, tools=self.tools, router=self.router, max_turns=max_turns)
        self.binary = binary or str(ROOT/"run.py")
        self.preset = preset or ""
        self.preview = preview
        print(col("green", f"[Brain] {self.adapter.config.provider}/{self.adapter.config.model} · 도구 {len(self.tools)}개"))

    def run(self, task, binary=None, preset=None):
        bin_path = binary or self.binary
        pre = preset if preset is not None else self.preset
        print(col("cyan", f"\n▶ {task}"))
        t0=time.time()
        result = self.agent.run(task=task)
        dt=time.time()-t0
        print(col("green", f"[완료 {dt:.1f}s]"))
        print(result["report"])
        # 3기둥 통합 저장 — 서버에 POST하면 Notion 블록 + Obsidian .md + session이 한 번에
        if self.preview:
            try:
                import requests
                # 로컬 미리보기
                requests.post("http://127.0.0.1:8090/api/run", json={"task":task,"binary":bin_path,"preset":pre}, timeout=5)
                print(col("gray", "[미리보기] 오른쪽 채팅 + Notion 블록 + Obsidian vault에 반영 → http://127.0.0.1:8090/ide"))
                # 로컬 파일로도 직접 vault 기록 (서버 없이도)
                try:
                    from vault.index import write_note
                    from datetime import datetime
                    slug = task.replace(" ","-")[:20]
                    write_note(f"{slug}.md", f"# {task}\n\n{result['report'][:800]}")
                except: pass
            except Exception as e:
                print(col("yellow", f"[미리보기] POST 실패: {e}"))
        return result

    def code(self, path):
        p=ROOT/path
        if p.exists():
            print(col("blue", f"--- {path} ({p.stat().st_size}B) ---"))
            txt=p.read_text(encoding="utf-8", errors="replace")
            print(txt[:4000])
            if len(txt)>4000: print(col("dim", f"... {len(txt)-4000}자 더"))
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
            print(col("green", f"서버: {j.get('default')} presets:{len(j.get('presets',[]))} LLM:{j.get('llm',{}).get('mode')} {j.get('llm',{}).get('detail')}"))
        except Exception as e: print(col("yellow", f"서버 확인 실패: {e}"))
        print(f"Brain: {self.adapter.config.provider}/{self.adapter.config.model} binary={self.binary} preset={self.preset}")
    def blocks(self, limit=5):
        try:
            from notion.blocks import list_blocks
            bs=list_blocks(limit=limit)
            for b in bs: print(f"- {b['type']} {b['id']} {b['content'][:60]}")
            return bs
        except Exception as e: print(col("red", str(e)))
    def graph(self):
        try:
            from vault.index import build_index
            g=build_index()
            print(f"Vault graph: nodes {len(g['nodes'])} edges {len(g['edges'])}")
            for n in g["nodes"][:5]: print(f"  ● {n['label']} ({n['path']})")
            for e in g["edges"][:5]: print(f"  → {e['from']} --[[{e['raw']}]]--> {e['to']}")
            return g
        except Exception as e: print(col("red", str(e)))

INTRO_HELP = """명령어:
  C2 찾아줘              ← 자연어 그대로 → 3기둥(에이전트+블록+vault) 실행
  brain.run("...")       ← Python 방식도 OK
  /code <경로>           ← 파일 보기  예: /code vault/C2-1019.md
  /edit <경로>           ← 메모장 열기
  /model <프리셋>        ← 모델 변경
  /status                ← 서버/Brain 상태
  /blocks                ← Notion 블록 목록
  /graph                 ← Obsidian vault 그래프
  /help                  ← 이 도움말
  Python 코드도 그대로: x=5; print(x*2)
"""

INTRO = col("cyan","═"*60)+"\n"+col("bold","  v2 통합 REPL — Claude Code + Notion + Obsidian")+"\n"+col("dim","  한글은 자연어→에이전트, Notion 블록+Obsidian vault 동시 저장, 브라우저 실시간")+"\n"+col("cyan","═"*60)+"""
예시:
  >>> C2 찾아줘                    ← 자연어 바로 (3기둥)
  >>> brain.run("취약점 찾아줘")
  >>> /code vault/C2-1019.md
  >>> /blocks
  >>> /graph
  >>> brain.status()
  >>> x=5; print(x*2)
  >>> /help
종료: exit() 또는 Ctrl+Z
"""

class BrainConsole(code.InteractiveConsole):
    def __init__(self, brain, *a, **kw):
        super().__init__(*a, **kw)
        self.brain = brain
    def runsource(self, source, filename="<input>", symbol="single"):
        s = source.strip()
        if not s: return False
        if s.startswith("/"):
            self.handle_slash(s)
            return False
        try:
            codeobj = code.compile_command(source, filename, symbol)
        except (OverflowError, SyntaxError, ValueError):
            if any('\uac00' <= c <= '\ud7a3' for c in source):
                print(col("cyan", f"\n▶ {s}  (자연어 → 3기둥 실행)"))
                try: self.brain.run(s)
                except Exception as e: print(col("red", f"실행 실패: {e}")); import traceback; traceback.print_exc()
                return False
            self.showsyntaxerror(filename)
            return False
        if codeobj is None: return True
        try: self.runcode(codeobj)
        except SystemExit: raise
        except: self.showtraceback()
        return False
    def handle_slash(self, line):
        parts=line.split(maxsplit=1); cmd=parts[0].lower(); arg=parts[1].strip() if len(parts)>1 else ""
        if cmd in ("/code","/read","/cat"):
            if arg: self.brain.code(arg)
            else: print("사용법: /code vault/C2-1019.md 또는 /code brain/agent.py")
        elif cmd in ("/edit","/open"):
            if arg: self.brain.edit(arg)
            else: print("사용법: /edit vault/C2-1019.md")
        elif cmd in ("/model","/preset"):
            if arg: self.brain.set_model(arg)
            else: print(f"현재 모델: {self.brain.preset or '(기본)'}  사용법: /model openrouter_qwen3_free")
        elif cmd in ("/status","/info"): self.brain.status()
        elif cmd in ("/blocks","/notion"): self.brain.blocks(limit=int(arg) if arg.isdigit() else 5)
        elif cmd in ("/graph","/vault"): self.brain.graph()
        elif cmd in ("/help","/h","/?","도움"): print(INTRO_HELP)
        elif cmd in ("/clear","/cls"): os.system("cls" if os.name=="nt" else "clear")
        else: print(f"알 수 없는 명령: {cmd}  — /help")

def main():
    import argparse
    ap=argparse.ArgumentParser(description="v2 통합 REPL")
    ap.add_argument("--preset", default="", help="모델 프리셋")
    ap.add_argument("--binary", default="", help="기본 바이너리")
    ap.add_argument("--no-preview", action="store_true")
    args=ap.parse_args()
    print(INTRO)
    preview_proc = None if args.no_preview else start_preview()
    brain = Brain(preset=args.preset, binary=args.binary, preview=not args.no_preview)
    ns = {"brain": brain, "Brain": Brain, "ROOT": ROOT, "Path": Path, "run": brain.run, "code": brain.code, "edit": brain.edit}
    try:
        import brain.reasoning as reasoning
        import brain.model_adapter as model_adapter
        import tools.router as router
        ns.update({"reasoning": reasoning, "model_adapter": model_adapter, "router": router})
    except: pass
    print(col("yellow","대화형 — 자연어(C2 찾아줘) 또는 brain.run(\"...\") 입력"))
    try: import readline
    except: pass
    console = BrainConsole(brain, locals=ns)
    console.interact(banner="")
    if preview_proc:
        try: preview_proc.terminate()
        except: pass
if __name__=="__main__":
    main()
