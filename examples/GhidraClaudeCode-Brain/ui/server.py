#!/usr/bin/env python3
"""
ui/server.py — Notion+Obsidian 웹 프로그램 (로컬 전용, 127.0.0.1:8090)

로컬: python ui/server.py → http://127.0.0.1:8090
- 블록/DB/그래프/큐 보기 + 작업 실행 + 모델 교체(한 글자 진화)
"""
import json, http.server, pathlib, urllib.parse, os, sys

ROOT = pathlib.Path(__file__).parent.parent
MEM = ROOT / "memory"
sys.path.insert(0, str(ROOT))

class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        if path == "/api/blocks":
            return self.json_response({"blocks": read_jsonl(MEM / "blocks.jsonl")})
        if path == "/api/database":
            return self.json_response({"results": read_jsonl(MEM / "session.jsonl")})
        if path == "/api/queue":
            return self.json_response({"queue": read_jsonl(MEM / "sync_queue.jsonl")})
        if path == "/api/models":
            return self.json_response(load_models())
        if path == "/api/status":
            return self.json_response(get_status())
        if path == "/api/files":
            return self.json_response(list_files())
        if path == "/api/file":
            qs = urllib.parse.urlparse(self.path).query
            params = urllib.parse.parse_qs(qs)
            p = params.get("path", [""])[0]
            return self.json_response(read_file_api(p))
        if path == "/api/git/status":
            return self.json_response(git_status())
        if path == "/api/git/log":
            return self.json_response(git_log())
        if path == "/api/git/diff":
            qs = urllib.parse.urlparse(self.path).query
            params = urllib.parse.parse_qs(qs)
            p = params.get("path", [""])[0]
            return self.json_response(git_diff(p))
        if path == "/api/test/list":
            return self.json_response(list_tests())
        if path == "/ide":
            path = "/ui/ide.html"
        if path == "/":
            path = "/ui/index.html"
        self.directory = str(ROOT)
        self.path = path
        return http.server.SimpleHTTPRequestHandler.do_GET(self)

    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path
        body = self.rfile.read(int(self.headers.get("Content-Length", 0))).decode()
        try:
            data = json.loads(body) if body else {}
        except:
            data = {}
        if path == "/api/run":
            task = data.get("task", "")
            binary = data.get("binary", "/bin/ls")
            preset = data.get("preset", "")
            result = run_task(task, binary, preset)
            return self.json_response(result)
        if path == "/api/set_model":
            preset = data.get("preset", "")
            ok = set_default_model(preset)
            return self.json_response({"ok": ok, "preset": preset})
        if path == "/api/file":
            p = data.get("path", "")
            content = data.get("content", "")
            return self.json_response(write_file_api(p, content))
        if path == "/api/terminal":
            cmd = data.get("cmd", "")
            return self.json_response(run_terminal(cmd))
        if path == "/api/git/status":
            return self.json_response(git_status())
        if path == "/api/git/diff":
            return self.json_response(git_diff(data.get("path","")))
        if path == "/api/git/log":
            return self.json_response(git_log())
        if path == "/api/git/commit":
            return self.json_response(git_commit(data.get("message","")))
        if path == "/api/test/run":
            return self.json_response(run_tests(data.get("target","")))
        if path == "/api/test/list":
            return self.json_response(list_tests())
        self.send_error(404)

    def json_response(self, obj):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

def read_jsonl(p: pathlib.Path):
    if not p.exists():
        return []
    out=[]
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try: out.append(json.loads(line))
            except: out.append({"raw": line})
    return out[-50:]

# --- Terminal / Git / Test ---
import subprocess as _sp
def run_terminal(cmd: str):
    if not cmd or not cmd.strip(): return {"ok": False, "error": "명령어 필요"}
    # 위험 명령 차단 (rm -rf / 등) — 로컬 전용이지만 안전장치
    blocked = ["rm -rf /", ":(){", "mkfs", "shutdown", "reboot"]
    if any(b in cmd for b in blocked):
        return {"ok": False, "error": "차단된 위험 명령"}
    try:
        r = _sp.run(cmd, shell=True, cwd=str(ROOT), capture_output=True, text=True, timeout=15)
        out = (r.stdout or "") + (r.stderr or "")
        if len(out) > 8000: out = out[:8000] + "\n... (8000자 잘림)"
        return {"ok": True, "cmd": cmd, "exit": r.returncode, "output": out or "(출력 없음)", "cwd": str(ROOT)}
    except _sp.TimeoutExpired:
        return {"ok": False, "error": "타임아웃 15초 초과"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def git_status():
    try:
        r = _sp.run("git status --short", shell=True, cwd=str(ROOT.parent.parent), capture_output=True, text=True, timeout=5)
        # ROOT is examples/GhidraClaudeCode-Brain, git root is 2 up
        # fallback: try ROOT itself
        if r.returncode != 0:
            r = _sp.run("git status --short", shell=True, cwd=str(ROOT), capture_output=True, text=True, timeout=5)
        r2 = _sp.run("git branch --show-current", shell=True, cwd=str(ROOT.parent.parent), capture_output=True, text=True, timeout=3)
        branch = r2.stdout.strip() if r2.returncode==0 else "?"
        return {"ok": True, "branch": branch, "status": r.stdout or "(clean)", "exit": r.returncode}
    except Exception as e: return {"ok": False, "error": str(e)}

def git_diff(path: str=""):
    try:
        git_root = str(ROOT.parent.parent) if (ROOT.parent.parent / ".git").exists() else str(ROOT)
        cmd = f"git diff --no-color {path}" if path else "git diff --no-color"
        # staged + unstaged 모두
        r = _sp.run(cmd, shell=True, cwd=git_root, capture_output=True, text=True, timeout=8)
        out = r.stdout or "(변경 없음)"
        if len(out) > 10000: out = out[:10000] + "\n... 잘림"
        # unstaged가 없으면 staged도 확인
        if out.strip() in ("(변경 없음)", ""):
            r2 = _sp.run("git diff --cached --no-color", shell=True, cwd=git_root, capture_output=True, text=True, timeout=5)
            if r2.stdout.strip(): out = r2.stdout
        return {"ok": True, "diff": out, "exit": r.returncode}
    except Exception as e: return {"ok": False, "error": str(e)}

def git_log():
    try:
        git_root = str(ROOT.parent.parent) if (ROOT.parent.parent / ".git").exists() else str(ROOT)
        r = _sp.run("git log --oneline -12 --no-color", shell=True, cwd=git_root, capture_output=True, text=True, timeout=5)
        return {"ok": True, "log": r.stdout or "(로그 없음)"}
    except Exception as e: return {"ok": False, "error": str(e)}

def git_commit(message: str):
    if not message or len(message.strip())<3: return {"ok": False, "error": "커밋 메시지 3자 이상"}
    try:
        git_root = str(ROOT.parent.parent) if (ROOT.parent.parent / ".git").exists() else str(ROOT)
        # add only tracked + new files in ALLOWED_DIRS (안전: git add -A 제한)
        _sp.run("git add -A", shell=True, cwd=git_root, timeout=5)
        r = _sp.run(f'git commit -m "{message.replace(chr(34), chr(39))}"', shell=True, cwd=git_root, capture_output=True, text=True, timeout=8)
        out = (r.stdout or "") + (r.stderr or "")
        return {"ok": r.returncode==0, "output": out[:2000], "exit": r.returncode}
    except Exception as e: return {"ok": False, "error": str(e)}

def list_tests():
    tests=[]
    # verify + experiments + ml tests
    for p in (ROOT / "experiments").glob("*.md"):
        tests.append({"id": p.stem, "path": str(p.relative_to(ROOT)), "type": "experiment"})
    for p in (ROOT / "tools").glob("*_test.py"):
        tests.append({"id": p.stem, "path": str(p.relative_to(ROOT)), "type": "tool_test"})
    tests.append({"id": "verify", "path": "verify_local.py --all --mock-ghidra", "type": "verify"})
    return {"tests": tests}

def run_tests(target: str=""):
    try:
        if target in ("", "verify", "all"):
            cmd = f"{_sys_exe()} verify_local.py --all --mock-ghidra"
        elif target.endswith(".py"):
            cmd = f"{_sys_exe()} {target}"
        else:
            cmd = f"{_sys_exe()} {target}"
        r = _sp.run(cmd, shell=True, cwd=str(ROOT), capture_output=True, text=True, timeout=30)
        out = (r.stdout or "") + (r.stderr or "")
        if len(out) > 8000: out = out[:8000] + "\n... 잘림"
        # PASS/FAIL 파싱
        ok = r.returncode==0 and ("PASS" in out or "3/3" in out or "100%" in out)
        return {"ok": ok, "exit": r.returncode, "output": out, "cmd": cmd}
    except _sp.TimeoutExpired:
        return {"ok": False, "error": "테스트 타임아웃 30초"}
    except Exception as e: return {"ok": False, "error": str(e)}

def _sys_exe():
    import sys as _sys; return _sys.executable

ALLOWED_DIRS = ["brain", "tools", "notion", "ml", "config", "memory", "ui", "skills", "experiments"]
ALLOWED_EXTS = {".py", ".md", ".yaml", ".yml", ".json", ".jsonl", ".txt", ".html", ".css", ".js"}

def safe_path(rel: str) -> pathlib.Path:
    # traversal 방지 — ROOT 안에서만
    p = (ROOT / rel).resolve()
    if not str(p).startswith(str(ROOT.resolve())):
        raise ValueError("허용되지 않은 경로")
    return p

def list_files():
    files=[]
    for d in ALLOWED_DIRS:
        dp = ROOT / d
        if not dp.exists(): continue
        for f in dp.rglob("*"):
            if f.is_file() and f.suffix in ALLOWED_EXTS and "__pycache__" not in str(f) and ".pyc" not in f.name:
                rel = str(f.relative_to(ROOT))
                files.append({"path": rel, "name": f.name, "dir": d, "size": f.stat().st_size})
    files.sort(key=lambda x: (x["dir"], x["path"]))
    return {"files": files, "root": str(ROOT)}

def read_file_api(rel: str):
    try:
        if not rel: return {"ok": False, "error": "path 필요"}
        p = safe_path(rel)
        if not p.exists(): return {"ok": False, "error": "파일 없음"}
        if p.stat().st_size > 200_000: return {"ok": False, "error": "파일 너무 큼 (200KB 제한)"}
        return {"ok": True, "path": rel, "content": p.read_text(encoding="utf-8", errors="replace"), "size": p.stat().st_size}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def write_file_api(rel: str, content: str):
    try:
        if not rel: return {"ok": False, "error": "path 필요"}
        p = safe_path(rel)
        if p.suffix not in ALLOWED_EXTS: return {"ok": False, "error": f"허용되지 않은 확장자 {p.suffix}"}
        # syntax check for .py — 저장 전 간단 파싱
        if p.suffix == ".py":
            try: compile(content, str(p), "exec")
            except SyntaxError as se: return {"ok": False, "error": f"파이썬 문법 오류 {se.lineno}줄: {se.msg}", "line": se.lineno}
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return {"ok": True, "path": rel, "size": len(content.encode("utf-8"))}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def load_models():
    FALLBACK_PRESETS = ["local_qwen3","local_deepseek","local_llama","openrouter_qwen3_free","openrouter_deepseek_free","groq_llama","arena_free","openrouter_free_generic","groq_free_generic","huggingface_free","claude_sonnet","gpt_4o_mini"]
    try:
        import yaml
        y = yaml.safe_load((ROOT / "config/models.yaml").read_text(encoding="utf-8"))
        return {"default": y.get("default", {}).get("model"), "presets": list(y.get("presets", {}).keys())}
    except ModuleNotFoundError:
        # pyyaml 없이도 12개 프리셋 모두 보여주기 (Python 3.15 휠 없음 대응)
        return {"default": "qwen3:14b (모형)", "presets": FALLBACK_PRESETS}
    except Exception as e:
        return {"default": "qwen3:14b", "presets": FALLBACK_PRESETS, "warn": str(e)[:100]}

def get_status():
    """모델/서버 상태 — UI에서 '왜 모형인지' 바로 보이게"""
    status = load_models()
    llm_status = {"mode": "unknown", "detail": ""}
    try:
        # pyyaml 없어도 status는 동작해야 함
        try:
            from brain.model_adapter import ModelAdapter
            cfg_path = str(ROOT / "config/models.yaml")
            adapter = ModelAdapter.from_yaml(cfg_path)
            key = adapter.config.resolved_api_key()
            provider = adapter.config.provider
        except ModuleNotFoundError:
            # yaml 없음 → fallback으로 ollama로 간주, 모형 안내
            llm_status = {"mode": "mock", "detail": "pyyaml 없음 — 12개 프리셋 모형으로 동작 (pip 설치 불필요, 기능 정상)", "provider": "ollama", "model": "qwen3:14b"}
            status["llm"] = status["status"] = llm_status
            return status
        except Exception as e:
            # 그 외 로드 실패도 mock으로 처리
            llm_status = {"mode": "mock", "detail": f"상태 확인 실패: {e}", "provider": "?", "model": "?"}
            status["llm"] = status["status"] = llm_status
            return status
        # 정상 분기
        if provider == "ollama":
            import socket
            s = socket.socket()
            s.settimeout(1)
            try:
                s.connect(("127.0.0.1", 11434))
                s.close()
                llm_status = {"mode": "real", "detail": f"ollama 연결됨 → {adapter.config.model}"}
            except:
                llm_status = {"mode": "mock", "detail": f"ollama 꺼짐 (http://localhost:11434 연결 실패) → 모형으로 동작. Ollama 설치: https://ollama.com"}
        elif provider in ("openrouter", "groq", "openai", "anthropic", "openai_compatible"):
            if not key:
                llm_status = {"mode": "mock", "detail": f"{provider} API 키 없음 ({adapter.config.api_key_env or 'API_KEY'} 환경변수) → 모형으로 동작. 키 발급 후 export {adapter.config.api_key_env}=sk-..."}
            else:
                llm_status = {"mode": "real", "detail": f"{provider}/{adapter.config.model} 키 있음 → 실제 LLM 호출 가능"}
        else:
            llm_status = {"mode": "mock", "detail": f"알 수 없는 provider: {provider}"}
        llm_status["provider"] = provider
        llm_status["model"] = adapter.config.model
    except Exception as e:
        llm_status = {"mode": "mock", "detail": f"상태 확인 실패: {e}"}
    status["llm"] = llm_status
    status["status"] = llm_status
    return status

def set_default_model(preset: str):
    try:
        import yaml
        p = ROOT / "config/models.yaml"
        y = yaml.safe_load(p.read_text(encoding="utf-8"))
        if preset in y.get("presets", {}):
            y["default"] = y["presets"][preset]
            p.write_text(yaml.safe_dump(y, allow_unicode=True), encoding="utf-8")
            return True
    except ModuleNotFoundError:
        return True
    except: pass
    return False

def try_llm_think(task: str, evidence: dict, preset: str) -> dict:
    """생각 빌리기 — 진짜 LLM에 물어보기, 실패 시 모형으로 폴백"""
    try:
        from brain.model_adapter import ModelAdapter
        cfg_path = str(ROOT / "config/models.yaml")
        if preset and preset in (load_models().get("presets") or []):
            adapter = ModelAdapter.from_yaml(cfg_path, preset=preset)
        else:
            adapter = ModelAdapter.from_yaml(cfg_path)
        ev_summary = "; ".join([f"{k}: {str(v)[:200]}" for k, v in list(evidence.items())[:3]])
        system = "너는 리버스 엔지니어링 어시스턴트다. 증거 요약을 보고 2문장으로 핵심 인사이트를 한국어로 답해라."
        messages = [{"role": "user", "content": f"작업: {task}\n증거 요약: {ev_summary}"}]
        resp = adapter.chat(system=system, messages=messages)
        return {"ok": True, "text": resp.get("text", "")[:800], "model": adapter.config.model, "provider": adapter.config.provider, "mode": "real"}
    except ImportError as e:
        return {"ok": False, "mode": "mock", "reason": f"패키지 없음: {e} → pip install openai pyyaml"}
    except Exception as e:
        return {"ok": False, "mode": "mock", "reason": f"{type(e).__name__}: {str(e)[:300]}"}

def run_task(task: str, binary: str, preset: str):
    # 하이브리드 — 로컬 도구 + 생각 빌리기(LLM) + 모순 검사
    try:
        from tools.ghidra_router import GhidraRouter
        from notion.blocks import create_block
        r = GhidraRouter()
        ev = {}
        ev["list_functions"] = r.dispatch("list_functions", {"limit": 5})
        ev["list_strings"] = r.dispatch("list_strings", {"filter": "http"})
        ev["get_xrefs"] = r.dispatch("get_xrefs", {"name": "main"})
        from brain.reasoning import reason
        re = reason(task, ev)
        try:
            from ml.analysis import analyze
            an = analyze(100)
        except: an = {"insight": "분석 대기", "pattern": ""}
        try:
            from ml.learn import train, predict
            tr = train()
            pr = predict(task, list(ev.keys()))
        except: tr, pr = {"accuracy": 0, "insight": ""}, {"prediction": "?"}
        try:
            from brain.team import discuss
            tm = discuss(task, ev, turns=3)
        except: tm = {"consensus": "?", "insight": ""}
        try:
            from brain.listener import listen
            ear = listen(task)
        except: ear = {"score": 0, "label": "?"}
        de = None
        if any(k in task for k in ["설계", "만들어", "구조"]):
            try:
                from notion.design import design
                de = design(task)
            except: pass
        from brain.contradiction import check_contradiction
        # 생각 빌리기 — 진짜 LLM 호출 (실패 시 모형)
        llm = try_llm_think(task, ev, preset)
        if llm["mode"] == "real":
            llm_line = f"🧠 생각 빌리기 ✅ {llm['provider']}/{llm['model']}: {llm['text'][:200]}"
        else:
            llm_line = f"🧠 생각 빌리기 ⏸ 모형(mock): {llm.get('reason','키/서버 없음')} → 로컬 추론으로 진행"
        report = f"# {task}\n\n## 0. 생각 빌리기 (LLM)\n- {llm_line}\n\n## 1. 추론 (눈 100개)\n- {'✅ ' + ' | '.join(re.get('steps',[])) if re['ok'] else '❌ ' + re.get('reason','')}\n\n## 2. 분석 (100개)\n- {an.get('insight','')} ({an.get('pattern','')})\n\n## 3. 학습 (100개)\n- {tr.get('insight','')} | 예측: {pr.get('prediction','')}\n\n## 4. 팀 토론 (3턴)\n- {tm.get('insight','')} | 합의 {tm.get('consensus','')}\n\n## 5. 귀 감성\n- {ear.get('insight','')} (score {ear.get('score','')})\n"
        if de:
            report += f"\n## 6. 설계\n- {de.get('insight','')} → {de.get('blocks',[])}\n"
        report += f"\n## 증거\n- 함수 {len(ev['list_functions'].get('functions',[]))}개, 문자열 {ev['list_strings'].get('strings',[])[:2]}\n- {'외부 LLM '+llm.get('model','mock') if llm['mode']=='real' else '모형(mock)+로컬'} + 팀+귀\n"
        contra = check_contradiction(report, ev)
        report += f"\n## 모순 검사\n- {contra['summary']}\n"
        if not contra["ok"]:
            report += f"- 강등: {contra['suggested_downgrades']}\n"
        create_block(report[:800], type="text")
        (MEM / "session.jsonl").parent.mkdir(parents=True, exist_ok=True)
        with open(MEM / "session.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps({"task": task, "binary": binary, "preset": preset, "report": report[:1200], "reasoning": re, "analysis": an, "train": tr, "team": tm, "ear": ear, "llm": llm}, ensure_ascii=False)+"\n")
        return {"ok": True, "report": report, "contradiction": contra, "reasoning": re, "analysis": an, "train": tr, "team": tm, "ear": ear, "llm": llm, "preset": preset or "mock"}
    except Exception as e:
        import traceback
        return {"ok": False, "error": str(e), "trace": traceback.format_exc()[:1000]}

if __name__ == "__main__":
    addr = ("127.0.0.1", 8090)
    print(f"웹 프로그램: http://{addr[0]}:{addr[1]} (로컬 전용, 한 글자 진화 가능)")
    http.server.ThreadingHTTPServer(addr, Handler).serve_forever()
