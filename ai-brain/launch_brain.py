#!/usr/bin/env python3
"""
Portable Living AI Brain Launcher (Zero external dependencies).
Run directly from an external drive (USB/SSD) on Windows, macOS, or Linux:
    python3 launch_brain.py --port 8765
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict
from urllib.parse import parse_qs, urlparse

BRAIN_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(BRAIN_ROOT))

from brain_engine.host_probe import probe_host  # noqa: E402
from brain_engine.quant_forge import CustomBrainForge, dissect_architecture  # noqa: E402
from brain_engine.slm_bridge import PortableSLMBridge  # noqa: E402
from brain_engine.tamagotchi import TamagotchiSoul  # noqa: E402
from brain_engine.wiki_gardener import WikiGardener  # noqa: E402


class BrainState:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.web_dir = root / "web"
        self.gardener = WikiGardener(root / "vault", root / "state" / "wiki_index.db")
        self.soul = TamagotchiSoul(root / "state" / "soul.json")
        self.slm = PortableSLMBridge(root / "models")
        self.forge = CustomBrainForge(root / "models")
        self.host_info = probe_host(root)
        self.soul.register_host(self.host_info)

    def full_status(self) -> Dict[str, Any]:
        self.host_info = probe_host(self.root)
        graph = self.gardener.get_graph()
        env_grade = self.host_info.get("environment", {}).get("grade", "optimal")
        return {
            "soul": self.soul.snapshot(graph["stats"], env_grade=env_grade),
            "host": self.host_info,
            "engine": self.slm.detect_active_engine(),
            "forged_brains": self.forge.list_forged_brains(),
            "graph": graph,
            "roadmap": {
                "stage_a": {"status": "active", "title": "A단계: 마크다운 위키 & 자체 양자화 주조"},
                "stage_b": {"status": "next", "title": "B단계: CPU 강화학습 훈련소"},
                "stage_c": {"status": "upcoming", "title": "C단계: Ghidra 12.3 역공학 해부실"},
            },
        }


def make_handler(state: BrainState):
    class BrainHTTPHandler(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args: Any) -> None:
            sys.stdout.write(f"[ai-brain] {self.address_string()} - {fmt % args}\n")
            sys.stdout.flush()

        def _send_json(self, payload: Any, status: int = 200) -> None:
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.end_headers()
            self.wfile.write(data)

        def _read_json_body(self) -> Dict[str, Any]:
            length = int(self.headers.get("Content-Length", "0") or "0")
            if length <= 0:
                return {}
            raw = self.rfile.read(length).decode("utf-8", errors="ignore")
            return json.loads(raw) if raw.strip() else {}

        def do_OPTIONS(self) -> None:  # noqa: N802
            self.send_response(HTTPStatus.NO_CONTENT)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.end_headers()

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            route = parsed.path

            if route == "/api/status":
                self._send_json(state.full_status())
                return
            if route == "/api/notes":
                self._send_json({"notes": state.gardener.list_notes()})
                return
            if route == "/api/note":
                qs = parse_qs(parsed.query)
                slug = (qs.get("slug") or [""])[0]
                for note in state.gardener.list_notes():
                    if note["slug"] == slug:
                        self._send_json({"note": note})
                        return
                self._send_json({"error": "Note not found"}, status=404)
                return
            if route == "/api/dissect":
                qs = parse_qs(parsed.query)
                bp_id = (qs.get("id") or ["custom-synapse-seed"])[0]
                self._send_json(dissect_architecture(bp_id, state.root / "models"))
                return

            rel = "index.html" if route in ("", "/") else route.lstrip("/")
            target = (state.web_dir / rel).resolve()
            if not str(target).startswith(str(state.web_dir.resolve())) or not target.is_file():
                target = state.web_dir / "index.html"

            ctype, _ = mimetypes.guess_type(str(target))
            if not ctype:
                ctype = "application/octet-stream"
            if ctype.startswith("text/") or ctype in ("application/javascript", "application/json"):
                ctype += "; charset=utf-8"

            content = target.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(content)

        def do_POST(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            route = parsed.path
            try:
                body = self._read_json_body()
            except Exception as exc:
                self._send_json({"error": f"Invalid JSON: {exc}"}, status=400)
                return

            if route == "/api/feed":
                raw_text = str(body.get("text") or "").strip()
                custom_title = str(body.get("title") or "").strip()
                if not raw_text:
                    self._send_json({"error": "먹일 지식이나 메모 내용을 입력해 주세요!"}, status=400)
                    return
                digested = state.gardener.digest_raw_memory(raw_text, custom_title=custom_title)
                state.soul.on_feed_memory(digested["title"], len(digested["links"]))
                self._send_json({"digested": digested, "status": state.full_status()})
                return

            if route == "/api/chat":
                question = str(body.get("question") or "").strip()
                if not question:
                    self._send_json({"error": "질문을 입력해 주세요!"}, status=400)
                    return
                recall_bundle = state.gardener.recall_memories(question, limit=2)
                result = state.slm.answer_with_memories(question, recall_bundle)
                state.soul.on_chat(len(recall_bundle["recalled"]))
                self._send_json(
                    {
                        "answer": result["answer"],
                        "engine": result["engine"],
                        "recalled": [
                            {"slug": n["slug"], "title": n["title"], "category": n["category"]}
                            for n in recall_bundle["recalled"]
                        ],
                        "saved_tokens_pct": recall_bundle["saved_tokens_pct"],
                        "status": state.full_status(),
                    }
                )
                return

            if route == "/api/forge":
                bits = int(body.get("bits") or 4)
                hidden_dim = int(body.get("hidden_dim") or 64)
                notes = state.gardener.list_notes()
                record = state.forge.forge_from_wiki(notes, bits=bits, hidden_dim=hidden_dim)
                state.soul.on_forge_brain(
                    bits=record["bits"],
                    saved_pct=record["saved_vs_fp32_pct"],
                    cos_sim=record["cosine_similarity_pct"],
                )
                self._send_json({"forged": record, "status": state.full_status()})
                return

            if route == "/api/poke":
                state.soul.poke()
                self._send_json({"status": state.full_status()})
                return

            if route == "/api/rename":
                name = str(body.get("name") or "").strip()
                state.soul.rename(name)
                self._send_json({"status": state.full_status()})
                return

            self._send_json({"error": "Unknown endpoint"}, status=404)

    return BrainHTTPHandler


def main() -> None:
    parser = argparse.ArgumentParser(description="Portable Tamagotchi AI Brain Server")
    parser.add_argument("--host", default="0.0.0.0", help="Bind host (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8765, help="Bind port (default: 8765)")
    args = parser.parse_args()

    (BRAIN_ROOT / "models" / ".gitkeep").parent.mkdir(parents=True, exist_ok=True)
    (BRAIN_ROOT / "models" / ".gitkeep").touch(exist_ok=True)
    (BRAIN_ROOT / "runtime" / ".gitkeep").parent.mkdir(parents=True, exist_ok=True)
    (BRAIN_ROOT / "runtime" / ".gitkeep").touch(exist_ok=True)

    state = BrainState(BRAIN_ROOT)
    env = state.host_info["environment"]
    server = ThreadingHTTPServer((args.host, args.port), make_handler(state))
    print("============================================================")
    print(f" 🧠 Portable Living AI Brain awake at http://{args.host}:{args.port}")
    print(f" 📂 Habitat Root : {BRAIN_ROOT}")
    print(f" 💻 Host Sensor  : {state.host_info['cpu_cores']} cores | Free RAM {state.host_info['ram_available_gb']} GB")
    print(f" 🌡️ Workspace    : {env['label']} ({env['score']}/100)")
    print("============================================================", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()


if __name__ == "__main__":
    main()
