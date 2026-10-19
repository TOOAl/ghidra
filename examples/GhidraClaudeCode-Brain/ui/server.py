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

def load_models():
    try:
        import yaml
        y = yaml.safe_load((ROOT / "config/models.yaml").read_text(encoding="utf-8"))
        return {"default": y.get("default", {}).get("model"), "presets": list(y.get("presets", {}).keys())}
    except ModuleNotFoundError:
        return {"default": "qwen3:14b (모형)", "presets": ["qwen3:14b", "deepseek-r1:free", "gpt-4o-mini"]}
    except: return {"default": "qwen3:14b", "presets": ["qwen3:14b"]}

def get_status():
    """모델/서버 상태 — UI에서 '왜 모형인지' 바로 보이게"""
    status = load_models()
    # LLM 연결 상태 확인
    llm_status = {"mode": "unknown", "detail": ""}
    try:
        from brain.model_adapter import ModelAdapter
        cfg_path = str(ROOT / "config/models.yaml")
        adapter = ModelAdapter.from_yaml(cfg_path)
        # 키/URL 체크 (실제 호출은 안 함, 설정만)
        key = adapter.config.resolved_api_key()
        provider = adapter.config.provider
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
