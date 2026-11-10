"""🧭 Stage N1 — 영속 퀘스트 원장: 재시작해도 끈기 있게.

퀘스트는 메모리가 아니라 **디스크의 원장**에 살아요 (state/quests.json,
원자 기록). 서버가 kill -9 로 죽어도 원장은 남고, 다음 기동에서 멈춘
스텝부터 이어가요. 각 스텝은 "효과 → 체크포인트" 순서라 효과는 한 번만
일어나요 (적어도 한 번이 아니라, 관측 가능한 효과는 정확히 한 번).

루프: begin → run(step…) → checkpoint → … → complete(proof).
러너는 kind 별로 스텝 의미를 알아요 (craft / chain / markers).
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

RUNNERS: Dict[str, Callable[..., None]] = {}


def runner(kind: str):
    def deco(fn):
        RUNNERS[kind] = fn
        return fn
    return deco


class QuestLedger:
    def __init__(self, state_dir: Path) -> None:
        self.path = Path(state_dir) / "quests.json"
        self.quests: Dict[str, Dict[str, Any]] = {}
        self._load()

    # ── 원장 I/O (원자) ────────────────────────────────────────────────────
    def _load(self) -> None:
        if self.path.exists():
            try:
                self.quests = json.loads(self.path.read_text(encoding="utf-8"))
            except Exception:  # 훼손된 원장은 발명하지 않고 빈 상태로
                self.quests = {}

    def _save(self) -> None:
        tmp = self.path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(self.quests, ensure_ascii=False, indent=1),
                       encoding="utf-8")
        os.replace(tmp, self.path)

    # ── 수명 주기 ──────────────────────────────────────────────────────────
    def begin(self, kind: str, title: str, payload: Dict[str, Any],
              steps: List[str]) -> str:
        qid = f"q-{kind}-{int(time.time() * 1000)}"
        self.quests[qid] = {
            "id": qid, "kind": kind, "title": title, "payload": payload,
            "steps": steps, "step_index": 0, "status": "active",
            "log": [], "checkpoint": {}, "proof": None,
            "created_ts": time.time(), "updated_ts": time.time(),
        }
        self._save()
        return qid

    def checkpoint(self, qid: str, next_index: int,
                   data: Optional[Dict[str, Any]] = None, note: str = "") -> None:
        q = self.quests[qid]
        q["step_index"] = next_index
        if data:
            q["checkpoint"].update(data)
        q["log"].append({"step": next_index - 1, "ts": time.time(), "note": note})
        q["updated_ts"] = time.time()
        self._save()

    def complete(self, qid: str, proof: Any = None, status: str = "done") -> None:
        q = self.quests[qid]
        q["status"] = status
        q["proof"] = proof
        q["updated_ts"] = time.time()
        self._save()

    def active(self) -> List[Dict[str, Any]]:
        return [q for q in self.quests.values() if q["status"] == "active"]

    # ── 실행 / 재개 ────────────────────────────────────────────────────────
    def run(self, qid: str, max_steps: int = 64) -> Dict[str, Any]:
        q = self.quests[qid]
        fn = RUNNERS.get(q["kind"])
        if fn is None:
            self.complete(qid, proof={"error": f"러너 없어요: {q['kind']}"},
                          status="failed")
            return q
        while q["status"] == "active" and q["step_index"] < len(q["steps"]) \
                and max_steps > 0:
            max_steps -= 1
            step = q["steps"][q["step_index"]]
            try:
                fn(self, q, step)
            except Exception as exc:  # noqa: BLE001 — 죽은 퀘스트 금지
                self.complete(qid, proof={"error": f"{step}: {exc}"},
                              status="failed")
                return q
        if q["status"] == "active" and q["step_index"] >= len(q["steps"]):
            self.complete(qid, proof=q["checkpoint"].get("proof"))
        return q

    def resume_all(self) -> List[str]:
        """기동 시 멈춰 있던 퀘스트를 이어서 — 끈기의 증거."""
        done: List[str] = []
        for q in self.active():
            self.run(q["id"])
            done.append(q["id"])
        return done
