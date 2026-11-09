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

from brain_engine.evolution_heartbeat import EvolutionHeartbeat  # noqa: E402
from brain_engine.genius_pantheon import GeniusPantheon  # noqa: E402
from brain_engine.genius_scout import analyze_candidate_genius  # noqa: E402
from brain_engine.hallucination import (  # noqa: E402
    audit_chat_grounding,
    evaluate_brain_hallucination,
)
from brain_engine.host_probe import probe_host  # noqa: E402
from brain_engine.quant_forge import CustomBrainForge, dissect_architecture  # noqa: E402
from brain_engine.rl_gym import PortableRLGym  # noqa: E402
from brain_engine.self_evolving_forge import SelfEvolvingForge  # noqa: E402
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
        self.rl_gym = PortableRLGym(root / "state", root / "models")
        self.pantheon = GeniusPantheon(root / "state", root / "models")
        self.evo_forge = SelfEvolvingForge(root)
        self.heartbeat = EvolutionHeartbeat(
            self.evo_forge,
            self.soul,
            self.gardener,
            self.rl_gym,
            interval_sec=int(__import__('os').environ.get('HEARTBEAT_INTERVAL_SEC', '120')),
        )
        self.host_info = probe_host(root)
        self.soul.register_host(self.host_info)

    def full_status(self) -> Dict[str, Any]:
        self.host_info = probe_host(self.root)
        notes = self.gardener.list_notes()
        graph = self.gardener.get_graph()
        forged = self.forge.list_forged_brains()
        rl_snap = self.rl_gym.status_snapshot()
        rl_trained = bool(rl_snap.get("benchmark", {}).get("trained", False))
        env_grade = self.host_info.get("environment", {}).get("grade", "optimal")
        recent_checks = self.soul.data.get("recent_hallucination_checks", [])
        recent_missing = self.soul.data.get("recent_missing_topics", [])
        hallucination = evaluate_brain_hallucination(
            notes,
            forged,
            recent_checks,
            recent_missing_topics=recent_missing,
            rl_trained=rl_trained,
        )
        return {
            "ui_version": "6.0",
            "soul": self.soul.snapshot(graph["stats"], env_grade=env_grade),
            "hallucination": hallucination,
            "host": self.host_info,
            "engine": self.slm.detect_active_engine(),
            "forged_brains": forged,
            "rl": rl_snap,
            "pantheon": self.pantheon.snapshot(),
            "evo_forge": self.evo_forge.snapshot(),
            "graph": graph,
            "roadmap": {
                "stage_a": {"status": "done", "title": "A단계: 마크다운 위키 & 자체 양자화 주조"},
                "stage_b": {"status": "done", "title": "B단계: CPU 강화학습 & 천재 성좌 합의"},
                "stage_c": {"status": "active", "title": "C단계: 6단계 자가 진화 역공학·코딩 공방"},
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
            if route == "/api/evo/heartbeat":
                self._send_json(state.heartbeat.status())
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
            if route == "/api/rl/scenario":
                qs = parse_qs(parsed.query)
                sc_id = (qs.get("id") or ["sc_ambiguous_crypto"])[0]
                self._send_json(state.rl_gym.evaluate_scenario(sc_id))
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
            if target.name == "index.html":
                boot_json = json.dumps(state.full_status(), ensure_ascii=False)
                inject = f"<script>window.__INITIAL_STATUS__ = {boot_json};</script>".encode("utf-8")
                content = content.replace(b"<!--__INITIAL_STATE__-->", inject)

            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
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
                audit = audit_chat_grounding(question, recall_bundle)
                result = state.slm.answer_with_memories(question, recall_bundle)
                state.soul.on_chat(
                    len(recall_bundle["recalled"]),
                    risk_pct=audit["risk_pct"],
                    missing_terms=audit.get("missing_terms", []),
                )
                self._send_json(
                    {
                        "answer": result["answer"],
                        "engine": result["engine"],
                        "hallucination_audit": audit,
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

            if route in ("/api/pantheon/debate", "/api/pantheon/distill"):
                cids = body.get("constellation_ids") or body.get("genius_ids") or []
                if not isinstance(cids, list):
                    cids = []
                topic = str(body.get("topic") or "").strip()
                res = state.pantheon.convene_debate(
                    [str(x) for x in cids], topic, state.rl_gym
                )
                digested = state.gardener.digest_raw_memory(
                    res["wiki_note_body"], custom_title=res["wiki_note_title"]
                )
                state.soul.on_genius_mentorship(
                    res["mentors"], res["after_score"], res["constellations"]
                )
                self._send_json(
                    {
                        "debate": res,
                        "distilled": res,
                        "digested_note": digested,
                        "status": state.full_status(),
                    }
                )
                return

            if route == "/api/pantheon/scout":
                query = str(body.get("query") or "").strip()
                if not query:
                    self._send_json({"error": "검색할 인물 이름을 입력해 주세요!"}, status=400)
                    return
                custom_hint = str(body.get("custom_hint") or "").strip()
                dossier = analyze_candidate_genius(
                    query_name=query,
                    constellations=state.pantheon.data["constellations"],
                    wiki_notes=state.gardener.list_notes(),
                    custom_hint=custom_hint,
                )
                self._send_json({"dossier": dossier})
                return

            if route == "/api/pantheon/add":
                g_name = str(body.get("genius_name") or "").strip()
                strengths = str(body.get("strengths") or "").strip()
                limitations = str(body.get("limitations") or "").strip()
                proof = str(body.get("proof_of_genius") or "").strip()
                achievements = body.get("achievements") or []
                added = state.pantheon.add_genius_or_constellation(
                    target_constellation_id=str(body.get("target_constellation_id") or ""),
                    new_constellation_name=str(body.get("new_constellation_name") or ""),
                    genius_name=g_name,
                    lens=str(body.get("lens") or ""),
                    credo=str(body.get("credo") or ""),
                    emoji=str(body.get("emoji") or "🌟"),
                    strengths=strengths,
                    limitations=limitations,
                )
                if g_name and (strengths or proof):
                    ach_txt = "\n".join(f"- {a}" for a in achievements[:4]) if isinstance(achievements, list) else ""
                    dossier_md = (
                        f"영입 천재: {g_name} ({added['added_genius']['lens']})\n"
                        f"배치 성좌: {added['constellation']['name']}\n\n"
                        f"[주요 업적 추적]\n{ach_txt}\n\n"
                        f"[천재성 입증]\n{proof}\n\n"
                        f"[천재성 강점]: {strengths}\n"
                        f"[명확한 한계점]: {limitations}\n"
                        f"[원탁 핵심 철학]: {added['added_genius']['credo']}"
                    )
                    state.gardener.digest_raw_memory(
                        dossier_md, custom_title=f"천재 영입 심사록 — {g_name}"
                    )
                    state.soul.on_feed_memory(f"천재 영입: {g_name}", 2)
                self._send_json({"added": added, "status": state.full_status()})
                return

            if route == "/api/pantheon/move":
                gid = str(body.get("genius_id") or "").strip()
                to_cid = str(body.get("to_constellation_id") or "").strip()
                new_cname = str(body.get("new_constellation_name") or "").strip()
                try:
                    moved = state.pantheon.move_genius(gid, to_cid, new_cname)
                except ValueError as exc:
                    self._send_json({"error": str(exc)}, status=400)
                    return
                state.soul._log_event(
                    f"천재 성좌 이동: {moved['moved_genius']['name']} ({moved['from_constellation']['name']} → {moved['to_constellation']['name']})"
                )
                state.soul.data["pose"] = "06_star"
                state.soul.data["last_speech"] = (
                    f"자리 이동 완료! [{moved['moved_genius']['name']}] 스승님이 "
                    f"[{moved['from_constellation']['name']}]에서 [{moved['to_constellation']['name']}] 성좌로 합류하셨어요!"
                )
                state.soul._save()
                self._send_json({"moved": moved, "status": state.full_status()})
                return

            if route == "/api/pantheon/feedback":
                user_thought = str(body.get("user_thought") or "").strip()
                if not user_thought:
                    self._send_json({"error": "주인님의 생각을 한 줄 이상 적어주세요!"}, status=400)
                    return
                cids = body.get("constellation_ids") or []
                if not isinstance(cids, list):
                    cids = []
                topic = str(body.get("topic") or "").strip()
                recall_bundle = state.gardener.recall_memories(user_thought, limit=2)
                fb = state.pantheon.feedback_on_user_thought(
                    constellation_ids=[str(x) for x in cids],
                    user_thought=user_thought,
                    topic=topic,
                    recalled_notes=recall_bundle.get("recalled", []),
                    rl_gym=state.rl_gym,
                )
                digested = state.gardener.digest_raw_memory(
                    fb["wiki_note_body"], custom_title=fb["wiki_note_title"]
                )
                state.soul.on_user_thought_feedback(
                    fb["analysis"]["badge"], user_thought
                )
                self._send_json(
                    {
                        "feedback": fb,
                        "digested_note": digested,
                        "status": state.full_status(),
                    }
                )
                return

            if route == "/api/rl/train":
                episodes = int(body.get("episodes") or 600)
                snap = state.rl_gym.train_episodes(episodes=episodes)
                bm = snap.get("benchmark", {})
                state.soul.on_rl_train(
                    episodes=episodes,
                    judges_score=float(bm.get("good_judges_score", 0.0)),
                    solo_score=float(bm.get("solo_top1_score", 0.0)),
                )
                self._send_json({"rl": snap, "status": state.full_status()})
                return

            if route == "/api/rl/coach":
                scenario_id = str(body.get("scenario_id") or "sc_ambiguous_crypto")
                action_id = int(body.get("action_id") or 3)
                coached = state.rl_gym.coach_scenario(scenario_id, action_id)
                sc_title = coached["updated_eval"]["scenario"]["title"]
                conf = coached["updated_eval"]["council_confidence_pct"]
                state.soul.on_rl_coach(sc_title, conf)
                self._send_json({"coached": coached, "status": state.full_status()})
                return

            if route == "/api/remedy":
                action = str(body.get("action") or "").strip()
                if action == "relink_synapses":
                    res = state.gardener.weave_missing_synapses()
                    added = res["added_pairs"]
                    msg = (
                        f"시냅스 그물망을 점검해 새로운 교차검증 고리 {added}쌍을 엮었어요!"
                        if added > 0
                        else "모든 노트의 시냅스 교차검증 그물망을 재정비 완료했어요!"
                    )
                    state.soul.on_remedy(msg)
                    self._send_json({"remedy": res, "message": msg, "status": state.full_status()})
                    return
                if action == "reset_checks":
                    state.soul.data["recent_hallucination_checks"] = []
                    state.soul.data["recent_missing_topics"] = []
                    state.soul.on_remedy("최근 환각 경보 기록을 초기화하고 방어막 영점을 재조정했어요!")
                    self._send_json({"message": "초기화 완료", "status": state.full_status()})
                    return
                self._send_json({"error": "Unknown remedy action"}, status=400)
                return

            if route == "/api/evo/dissect":
                spec_id = str(body.get("specimen_id") or "xor_rot_vault").strip()
                up_name = str(body.get("uploaded_name") or "").strip()
                up_b64 = str(body.get("uploaded_b64") or "").strip()
                bundle = state.evo_forge.dissect_and_draft(
                    specimen_id=spec_id,
                    uploaded_name=up_name,
                    uploaded_b64=up_b64,
                )
                self._send_json({"bundle": bundle, "status": state.full_status()})
                return

            if route == "/api/evo/audit":
                spec_id = str(body.get("specimen_id") or "xor_rot_vault").strip()
                code = str(body.get("code") or "")
                audit = state.evo_forge.audit_code(specimen_id=spec_id, code=code)
                self._send_json({"audit": audit})
                return

            if route == "/api/evo/repair":
                spec_id = str(body.get("specimen_id") or "xor_rot_vault").strip()
                current_code = str(body.get("current_code") or "")
                mode = str(body.get("mode") or "auto").strip()
                edited_code = str(body.get("edited_code") or "")
                repaired = state.evo_forge.repair_and_verify(
                    specimen_id=spec_id,
                    current_code=current_code,
                    mode=mode,
                    edited_code=edited_code,
                )
                self._send_json({"repaired": repaired, "status": state.full_status()})
                return

            if route == "/api/evo/rollback":
                spec_id = str(body.get("specimen_id") or "xor_rot_vault").strip()
                snap_id = str(body.get("snap_id") or "").strip()
                rb = state.evo_forge.rollback_snapshot(specimen_id=spec_id, snap_id=snap_id)
                self._send_json({"rollback": rb})
                return

            if route == "/api/evo/install":
                spec_id = str(body.get("specimen_id") or "xor_rot_vault").strip()
                code = str(body.get("code") or "")
                try:
                    installed = state.evo_forge.install_skill_cartridge(
                        specimen_id=spec_id,
                        verified_code=code,
                        gardener=state.gardener,
                        rl_gym=state.rl_gym,
                    )
                except ValueError as exc:
                    self._send_json({"error": str(exc)}, status=400)
                    return
                state.soul.on_evo_skill_installed(installed["title"], installed["entry_fn"])
                self._send_json({"installed": installed, "status": state.full_status()})
                return

            if route == "/api/evo/run-skill":
                skill_id = str(body.get("skill_id") or "").strip()
                args_val = body.get("args")
                try:
                    ran = state.evo_forge.execute_installed_skill(skill_id, args_val)
                except ValueError as exc:
                    self._send_json({"error": str(exc)}, status=400)
                    return
                self._send_json({"ran": ran})
                return

            if route == "/api/evo/heartbeat/toggle":
                paused = state.heartbeat.toggle_paused()
                self._send_json({"paused": paused, "heartbeat": state.heartbeat.status()})
                return

            if route == "/api/evo/heartbeat/beat":
                entry = state.heartbeat.beat_once(trigger="manual")
                self._send_json({"entry": entry, "heartbeat": state.heartbeat.status(), "status": state.full_status()})
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
    state.heartbeat.start()
    print(f" 💓 Heartbeat    : every {state.heartbeat.interval_sec}s (dream quests: {state.heartbeat.status()['pool_size']})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        state.heartbeat.stop()
        server.server_close()


if __name__ == "__main__":
    main()
