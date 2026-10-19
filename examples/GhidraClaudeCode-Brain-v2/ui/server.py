#!/usr/bin/env python3
"""
ui/server.py — v2 통합 서버 (200줄 목표, 3기둥 합체)

Claude Code( agent loop ) + Notion( blocks/database ) + Obsidian( vault/graph ) 를
하나의 127.0.0.1:8090 서버에서 제공한다.

Endpoints:
  GET  /api/status, /api/files, /api/file?path=, /api/blocks, /api/database, /api/vault/graph, /api/vault/backlinks, /api/vault/outgoing
  POST /api/run, /api/file, /api/blocks, /api/sync, /api/terminal
"""
import json, http.server, pathlib, urllib.parse, os, sys, subprocess, re
ROOT = pathlib.Path(__file__).parent.parent
MEM = ROOT / "memory"
sys.path.insert(0, str(ROOT))

class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        p = urllib.parse.urlparse(self.path).path
        if p == "/api/status": return self.json(get_status())
        if p == "/api/files": return self.json(list_files())
        if p == "/api/blocks": return self.json({"blocks": read_jsonl(MEM/"blocks.jsonl")})
        if p == "/api/database": return self.json({"results": read_jsonl(MEM/"session.jsonl")})
        if p == "/api/queue": return self.json({"queue": read_jsonl(MEM/"sync_queue.jsonl")})
        if p == "/api/models": return self.json(load_models())
        if p == "/api/vault/graph": return self.json(vault_graph())
        if p == "/api/file":
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            return self.json(read_file_api(qs.get("path",[""])[0]))
        if p == "/api/vault/backlinks":
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            return self.json(vault_backlinks(qs.get("file",[""])[0]))
        if p == "/api/vault/outgoing":
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            return self.json(vault_outgoing(qs.get("file",[""])[0]))
        if p in ("/api/git/status","/api/git/log","/api/git/diff","/api/test/list"):
            return self.json(git_status() if "status" in p else git_log() if "log" in p else git_diff() if "diff" in p else list_tests())
        if p == "/ide": p = "/ui/ide.html"
        if p == "/": p = "/ui/index.html"
        self.directory = str(ROOT)
        self.path = p
        return http.server.SimpleHTTPRequestHandler.do_GET(self)

    def do_POST(self):
        p = urllib.parse.urlparse(self.path).path
        body = self.rfile.read(int(self.headers.get("Content-Length",0))).decode()
        try: data = json.loads(body) if body else {}
        except: data = {}
        if p == "/api/run": return self.json(run_task(data.get("task",""), data.get("binary","/bin/ls"), data.get("preset","")))
        if p == "/api/file": return self.json(write_file_api(data.get("path",""), data.get("content","")))
        if p == "/api/blocks": return self.json(create_block_api(data))
        if p == "/api/sync": return self.json({"ok": True, "flushed": len(data.get("ops",[]))})
        if p == "/api/set_model": return self.json({"ok": set_default_model(data.get("preset","")), "preset": data.get("preset","")})
        if p == "/api/terminal": return self.json(run_terminal(data.get("cmd","")))
        if p in ("/api/git/status","/api/git/diff","/api/git/log","/api/git/commit","/api/test/run","/api/test/list"):
            return self.json(handle_git_test(p, data))
        self.send_error(404)

    def json(self, obj):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(200)
        self.send_header("Content-Type","application/json; charset=utf-8")
        self.send_header("Content-Length",str(len(body)))
        self.send_header("Access-Control-Allow-Origin","*")
        self.send_header("Cache-Control","no-cache")
        self.end_headers()
        self.wfile.write(body)
    def log_message(self, fmt, *a): sys.stderr.write("["+self.log_date_time_string()+"] "+fmt%a+"\n")

def read_jsonl(p: pathlib.Path):
    if not p.exists(): return []
    out=[]
    for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.strip():
            try: out.append(json.loads(line))
            except: out.append({"raw": line})
    return out[-50:]

# --- file ops (Claude Code Read/Write) ---
ALLOWED_DIRS = ["brain","tools","notion","vault","memory","ui","skills","config"]
ALLOWED_EXTS = {".py",".md",".yaml",".yml",".json",".jsonl",".txt",".html",".css",".js"}
def safe_path(rel: str) -> pathlib.Path:
    p = (ROOT/rel).resolve()
    if not str(p).startswith(str(ROOT.resolve())): raise ValueError("허용되지 않은 경로")
    return p
def list_files():
    files=[]
    for d in ALLOWED_DIRS:
        dp = ROOT/d
        if not dp.exists(): continue
        for f in dp.rglob("*"):
            if f.is_file() and f.suffix in ALLOWED_EXTS and "__pycache__" not in str(f):
                files.append({"path": str(f.relative_to(ROOT)), "name": f.name, "dir": d, "size": f.stat().st_size})
    files.sort(key=lambda x: (x["dir"], x["path"]))
    return {"files": files, "root": str(ROOT)}
def read_file_api(rel: str):
    try:
        if not rel: return {"ok": False, "error": "path 필요"}
        p = safe_path(rel)
        if not p.exists(): return {"ok": False, "error": "파일 없음"}
        if p.stat().st_size>200_000: return {"ok": False, "error": "200KB 제한"}
        return {"ok": True, "path": rel, "content": p.read_text(encoding="utf-8", errors="replace"), "size": p.stat().st_size}
    except Exception as e: return {"ok": False, "error": str(e)}
def write_file_api(rel: str, content: str):
    try:
        if not rel: return {"ok": False, "error": "path 필요"}
        p = safe_path(rel)
        if p.suffix not in ALLOWED_EXTS: return {"ok": False, "error": f"허용되지 않은 확장자 {p.suffix}"}
        if p.suffix==".py":
            try: compile(content, str(p), "exec")
            except SyntaxError as se: return {"ok": False, "error": f"문법 오류 {se.lineno}줄: {se.msg}", "line": se.lineno}
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return {"ok": True, "path": rel, "size": len(content.encode("utf-8"))}
    except Exception as e: return {"ok": False, "error": str(e)}

# --- Notion blocks ---
def create_block_api(data: dict):
    try:
        from notion.blocks import create_block
        r = create_block(type=data.get("type","text"), content=data.get("content",""), parent_id=data.get("parent_id"), extra=data.get("extra"))
        return r
    except Exception as e: return {"ok": False, "error": str(e)}

# --- Obsidian vault ---
def vault_graph():
    try:
        from vault.index import build_index
        return build_index()
    except Exception as e: return {"nodes": [], "edges": [], "error": str(e)}
def vault_backlinks(file: str):
    try:
        from vault.index import get_backlinks
        return {"file": file, "backlinks": get_backlinks(file)}
    except Exception as e: return {"error": str(e)}
def vault_outgoing(file: str):
    try:
        from vault.index import get_outgoing
        return {"file": file, "outgoing": get_outgoing(file)}
    except Exception as e: return {"error": str(e)}

# --- terminal / git / test (minimal) ---
def run_terminal(cmd: str):
    if not cmd.strip(): return {"ok": False, "error": "명령어 필요"}
    blocked = ["rm -rf /", ":(){", "mkfs", "shutdown", "reboot"]
    if any(b in cmd for b in blocked): return {"ok": False, "error": "차단된 위험 명령"}
    try:
        r = subprocess.run(cmd, shell=True, cwd=str(ROOT), capture_output=True, text=True, timeout=15)
        out = (r.stdout or "") + (r.stderr or "")
        if len(out)>8000: out = out[:8000]+"\n... 잘림"
        return {"ok": r.returncode==0, "cmd": cmd, "exit": r.returncode, "output": out or "(출력 없음)"}
    except Exception as e: return {"ok": False, "error": str(e)}
def git_status():
    try:
        gr = str(ROOT.parent.parent) if (ROOT.parent.parent/".git").exists() else str(ROOT)
        r = subprocess.run("git status --short", shell=True, cwd=gr, capture_output=True, text=True, timeout=5)
        r2 = subprocess.run("git branch --show-current", shell=True, cwd=gr, capture_output=True, text=True, timeout=3)
        return {"ok": True, "branch": r2.stdout.strip() if r2.returncode==0 else "?", "status": r.stdout or "(clean)"}
    except Exception as e: return {"ok": False, "error": str(e)}
def git_log():
    try:
        gr = str(ROOT.parent.parent) if (ROOT.parent.parent/".git").exists() else str(ROOT)
        r = subprocess.run("git log --oneline -12", shell=True, cwd=gr, capture_output=True, text=True, timeout=5)
        return {"ok": True, "log": r.stdout or "(로그 없음)"}
    except Exception as e: return {"ok": False, "error": str(e)}
def git_diff(path=""):
    try:
        gr = str(ROOT.parent.parent) if (ROOT.parent.parent/".git").exists() else str(ROOT)
        cmd = f"git diff --no-color {path}" if path else "git diff --no-color"
        r = subprocess.run(cmd, shell=True, cwd=gr, capture_output=True, text=True, timeout=8)
        out = r.stdout or "(변경 없음)"
        if out.strip() in ("(변경 없음)",""):
            r2 = subprocess.run("git diff --cached --no-color", shell=True, cwd=gr, capture_output=True, text=True, timeout=5)
            if r2.stdout.strip(): out = r2.stdout
        return {"ok": True, "diff": out}
    except Exception as e: return {"ok": False, "error": str(e)}
def handle_git_test(p, data):
    if p=="/api/git/status": return git_status()
    if p=="/api/git/log": return git_log()
    if p=="/api/git/diff": return git_diff(data.get("path",""))
    if p=="/api/git/commit":
        msg=data.get("message","")
        if len(msg.strip())<3: return {"ok": False, "error": "3자 이상"}
        gr = str(ROOT.parent.parent) if (ROOT.parent.parent/".git").exists() else str(ROOT)
        subprocess.run("git add -A", shell=True, cwd=gr, timeout=5)
        r = subprocess.run(f'git commit -m "{msg.replace(chr(34),chr(39))}"', shell=True, cwd=gr, capture_output=True, text=True, timeout=8)
        return {"ok": r.returncode==0, "output": (r.stdout or "")+(r.stderr or "")}
    if p=="/api/test/list": return list_tests()
    if p=="/api/test/run": return run_tests(data.get("target",""))
    return {"ok": False, "error": "unknown"}
def list_tests():
    tests=[{"id":"notion","path":"notion","type":"notion"}, {"id":"obsidian","path":"vault","type":"obsidian"}, {"id":"verify","path":"verify_v2.py --all --mock-ghidra","type":"verify"}]
    return {"tests": tests}
def run_tests(target: str=""):
    try:
        exe = sys.executable
        cmd = f"{exe} verify_v2.py --all --mock-ghidra" if target in ("","verify","all") else f"{exe} {target}"
        r = subprocess.run(cmd, shell=True, cwd=str(ROOT), capture_output=True, text=True, timeout=30)
        out = (r.stdout or "")+(r.stderr or "")
        ok = r.returncode==0 and ("PASS" in out or "4/4" in out)
        return {"ok": ok, "exit": r.returncode, "output": out[:8000], "cmd": cmd}
    except Exception as e: return {"ok": False, "error": str(e)}

# --- models / status (pyyaml 없이도 동작) ---
FALLBACK = ["local_qwen3","local_deepseek","openrouter_qwen3_free","openrouter_deepseek_free","groq_llama","claude_sonnet","gpt_4o_mini"]
def load_models():
    try:
        import yaml
        y = yaml.safe_load((ROOT/"config/models.yaml").read_text(encoding="utf-8"))
        return {"default": y.get("default",{}).get("model"), "presets": list(y.get("presets",{}).keys())}
    except ModuleNotFoundError:
        return {"default": "qwen3:14b (모형)", "presets": FALLBACK}
    except Exception as e:
        # yaml 없이도 presets는 regex로 파싱
        try:
            txt = (ROOT/"config/models.yaml").read_text(encoding="utf-8")
            presets = re.findall(r"^\s{2}(\w+):", txt, re.MULTILINE)
            return {"default": presets[0] if presets else "qwen3:14b", "presets": presets or FALLBACK}
        except:
            return {"default": "qwen3:14b", "presets": FALLBACK, "warn": str(e)[:80]}

def get_status():
    s = load_models()
    llm = {"mode": "mock", "detail": "pyyaml 없음 — 모형으로 동작 (pip 설치 불필요)", "provider":"ollama","model":"qwen3:14b"}
    try:
        from brain.model_adapter import ModelAdapter
        cfg = str(ROOT/"config/models.yaml")
        try:
            ad = ModelAdapter.from_yaml(cfg)
            key = ad.config.resolved_api_key()
            prov = ad.config.provider
            if prov=="ollama":
                import socket
                so=socket.socket(); so.settimeout(1)
                try: so.connect(("127.0.0.1",11434)); so.close(); llm={"mode":"real","detail":f"ollama 연결됨 → {ad.config.model}","provider":prov,"model":ad.config.model}
                except: llm={"mode":"mock","detail":f"ollama 꺼짐 → 모형. 설치: https://ollama.com","provider":prov,"model":ad.config.model}
            elif prov in ("openrouter","groq","openai","anthropic","openai_compatible"):
                if not key: llm={"mode":"mock","detail":f"{prov} 키 없음 ({ad.config.api_key_env}) → 모형","provider":prov,"model":ad.config.model}
                else: llm={"mode":"real","detail":f"{prov}/{ad.config.model} 키 있음","provider":prov,"model":ad.config.model}
            else: llm={"mode":"mock","detail":f"알 수 없는 provider: {prov}"}
            llm["provider"]=prov; llm["model"]=ad.config.model
        except ModuleNotFoundError:
            pass
        except Exception as e:
            llm={"mode":"mock","detail":f"상태 확인 실패: {e}","provider":"?","model":"?"}
    except Exception as e:
        llm={"mode":"mock","detail": str(e)}
    s["llm"]=llm; s["status"]=llm
    return s

def set_default_model(preset: str):
    try:
        import yaml
        p = ROOT/"config/models.yaml"
        y = yaml.safe_load(p.read_text(encoding="utf-8"))
        if preset in y.get("presets",{}):
            y["default"]=y["presets"][preset]
            p.write_text(yaml.safe_dump(y, allow_unicode=True), encoding="utf-8")
            return True
    except: pass
    return False

# --- run_task: 3기둥 합체 ---
def run_task(task: str, binary: str, preset: str):
    try:
        from tools.router import Router
        from notion.blocks import create_block
        from vault.index import write_note
        import datetime
        router = Router(root=ROOT)
        # 1. Claude Code — agent loop
        from brain.model_adapter import ModelAdapter, ModelConfig
        try:
            adapter = ModelAdapter.from_yaml(str(ROOT/"config/models.yaml"), preset=preset) if preset else ModelAdapter.from_yaml(str(ROOT/"config/models.yaml"))
        except:
            adapter = ModelAdapter(ModelConfig(provider="openai_compatible", model="mock", base_url="", api_key=""))
        try:
            with open(ROOT/"tools/definitions.json", encoding="utf-8") as f:
                tools = json.load(f)
        except: tools = []
        from brain.agent import BrainAgent
        agent = BrainAgent(adapter=adapter, tools=tools, router=router, max_turns=12)
        result = agent.run(task=task)
        report = result["report"]
        evidence = result["evidence"]

        # 2. Notion — 블록으로 저장
        notion_blocks=[]
        try:
            b1 = create_block(type="page", content=f"{task} — {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
            b2 = create_block(type="text", content=report[:800], parent_id=b1["block"]["id"])
            notion_blocks = [b1["block"]["id"], b2["block"]["id"]]
        except Exception as e:
            notion_blocks = [f"notion 실패: {e}"]

        # 3. Obsidian — vault에 .md로 저장 (검색은 DB, 탐색은 그래프)
        vault_path = None
        try:
            slug = re.sub(r"[^\w가-힣]+","-", task).strip("-")[:30] or "note"
            fname = f"{slug}-{datetime.datetime.now().strftime('%m%d-%H%M')}.md"
            # [[링크]]는 증거의 함수명에서 추출
            links = ""
            funcs = evidence.get("list_functions",{}).get("functions",[])
            if funcs:
                links = "\n".join([f"[[{f['name']}]]" for f in funcs[:3]])
            md = f"# {task}\n\n{links}\n\n## 보고서\n{report[:1200]}\n\n## 증거\n- 함수 {len(funcs)}개\n- 문자열 {evidence.get('list_strings',{}).get('strings',[])[:2]}\n"
            r = write_note(fname, md)
            vault_path = r.get("path")
        except Exception as e:
            vault_path = f"vault 실패: {e}"

        # 세션 저장 (기억)
        (MEM/"session.jsonl").parent.mkdir(parents=True, exist_ok=True)
        with open(MEM/"session.jsonl","a",encoding="utf-8") as f:
            f.write(json.dumps({"task":task,"binary":binary,"preset":preset,"report":report[:1200],"evidence":list(evidence.keys()),"notion":notion_blocks,"vault":vault_path}, ensure_ascii=False)+"\n")

        # sync 큐에도 enqueue (Notion offline)
        try:
            from memory.sync_queue import enqueue
            enqueue({"task":task, "report": report[:400]})
        except: pass

        return {"ok": True, "report": report, "evidence": evidence, "reasoning": result["reasoning"], "contradiction": result["contradiction"], "notion": notion_blocks, "vault": vault_path, "preset": preset or "mock"}
    except Exception as e:
        import traceback
        return {"ok": False, "error": str(e), "trace": traceback.format_exc()[:1000]}

if __name__=="__main__":
    import socket
    # PORT 환경변수로 고정 가능 (verify가 8091로 테스트)
    preferred=int(os.getenv("PORT","0"))
    ports = ([preferred]+[8090,8091,8092]) if preferred else [8090,8091,8092]
    port=ports[0]
    for p in ports:
        s=socket.socket()
        try: s.bind(("127.0.0.1",p)); s.close(); port=p; break
        except: continue
    print(f"웹 프로그램: http://127.0.0.1:{port} (로컬 전용, 한 글자 진화 가능) — v2 3기둥 통합")
    http.server.ThreadingHTTPServer(("127.0.0.1",port), Handler).serve_forever()
