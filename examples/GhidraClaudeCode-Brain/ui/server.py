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
            # 작업 실행 — 외부 LLM(mock) + 로컬 도구 + 블록 저장
            task = data.get("task", "")
            binary = data.get("binary", "/bin/ls")
            preset = data.get("preset", "")
            result = run_task(task, binary, preset)
            return self.json_response(result)
        if path == "/api/set_model":
            # 한 글자 진화 — config/models.yaml default 변경 (로컬에만)
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

def run_task(task: str, binary: str, preset: str):
    # 최소 실행 — 데모 하이브리드와 동일, mock LLM + 로컬 도구
    try:
        from tools.ghidra_router import GhidraRouter
        from notion.blocks import create_block
        r = GhidraRouter()
        # 간단 증거 수집 (실제 agent 루프 대신 최소 시연)
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
        # 우선순위 2: 팀 토론 3턴 12문장
        try:
            from brain.team import discuss
            tm = discuss(task, ev, turns=3)
        except: tm = {"consensus": "?", "insight": ""}
        # 우선순위 3: 귀 감성
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
        report = f"# {task}\n\n## 1. 추론 (눈 100개)\n- {'✅ ' + ' | '.join(re.get('steps',[])) if re['ok'] else '❌ ' + re.get('reason','')}\n\n## 2. 분석 (100개)\n- {an.get('insight','')} ({an.get('pattern','')})\n\n## 3. 학습 (100개)\n- {tr.get('insight','')} | 예측: {pr.get('prediction','')}\n\n## 4. 팀 토론 (3턴)\n- {tm.get('insight','')} | 합의 {tm.get('consensus','')}\n\n## 5. 귀 감성\n- {ear.get('insight','')} (score {ear.get('score','')})\n"
        if de:
            report += f"\n## 6. 설계\n- {de.get('insight','')} → {de.get('blocks',[])}\n"
        report += f"\n## 증거\n- 함수 {len(ev['list_functions'].get('functions',[]))}개, 문자열 {ev['list_strings'].get('strings',[])[:2]}\n- 외부 LLM({preset or 'mock'}) + 로컬 + 팀+귀\n"
        contra = check_contradiction(report, ev)
        report += f"\n## 모순 검사\n- {contra['summary']}\n"
        if not contra["ok"]:
            report += f"- 강등: {contra['suggested_downgrades']}\n"
        create_block(report[:800], type="text")
        (MEM / "session.jsonl").parent.mkdir(parents=True, exist_ok=True)
        with open(MEM / "session.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps({"task": task, "binary": binary, "preset": preset, "report": report[:1200], "reasoning": re, "analysis": an, "train": tr, "team": tm, "ear": ear}, ensure_ascii=False)+"\n")
        return {"ok": True, "report": report, "contradiction": contra, "reasoning": re, "analysis": an, "train": tr, "team": tm, "ear": ear, "preset": preset or "mock"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

if __name__ == "__main__":
    addr = ("127.0.0.1", 8090)
    print(f"웹 프로그램: http://{addr[0]}:{addr[1]} (로컬 전용, 한 글자 진화 가능)")
    http.server.ThreadingHTTPServer(addr, Handler).serve_forever()
