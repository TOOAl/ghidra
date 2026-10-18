#!/usr/bin/env python3
"""
ui/server.py — Obsidian/Notion-like UI 서버 (최소, 60줄)

로컬에서: python ui/server.py
→ http://127.0.0.1:8090 에서 블록/DB/그래프/큐 확인
외부 노출 없음 (127.0.0.1만)
"""
import json, http.server, pathlib, urllib.parse

ROOT = pathlib.Path(__file__).parent.parent
MEM = ROOT / "memory"

class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        # API
        if path == "/api/blocks":
            self.json_response({"blocks": read_jsonl(MEM / "blocks.jsonl")})
            return
        if path == "/api/database":
            # session.jsonl을 DB처럼
            self.json_response({"results": read_jsonl(MEM / "session.jsonl")})
            return
        if path == "/api/queue":
            self.json_response({"queue": read_jsonl(MEM / "sync_queue.jsonl")})
            return
        # 정적 파일 (ui/*)
        if path == "/":
            path = "/ui/index.html"
        # SimpleHTTPRequestHandler가 ROOT 기준으로 서빙
        self.directory = str(ROOT)
        self.path = path
        return http.server.SimpleHTTPRequestHandler.do_GET(self)

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
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                out.append(json.loads(line))
            except:
                out.append({"raw": line})
    return out[-50:]  # 최근 50개만

if __name__ == "__main__":
    addr = ("127.0.0.1", 8090)
    print(f"UI 서버: http://{addr[0]}:{addr[1]} (로컬 전용)")
    print("블록: Notion처럼, 그래프: Obsidian처럼, DB: Notion DB처럼")
    http.server.ThreadingHTTPServer(addr, Handler).serve_forever()
