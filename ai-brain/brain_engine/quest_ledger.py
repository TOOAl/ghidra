"""🧭 Stage N1 — 영속 퀘스트 원장: 재시작해도 끈기 있게.

퀘스트는 메모리가 아니라 **디스크의 원장**에 살아요 (state/quests.json,
원자 기록). 서버가 kill -9 로 죽어도 원장은 남고, 다음 기동에서 멈춘
스텝부터 이어가요. 각 스텝은 "효과 → 체크포인트" 순서라 효과는 한 번만
일어나요 (적어도 한 번이 아니라, 관측 가능한 효과는 정확히 한 번).

끈기의 세 적(敵)도 막아요:
  concurrent — 두 퀘스트 스레드가 동시에 저장 → RLock 으로 직렬화
  corrupt    — 원장이 훼손 → 지우지 않고 격리(quarantine) 후 정직 재기동
  disk-full  — 저장 실패 → tmp 청소·본파일 보존·오류 표면화(발명 금지)

루프: begin → run(step…) → checkpoint → … → complete(proof).
러너는 kind 별로 스텝 의미를 알아요 (craft / chain / markers / garden).
"""
from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

RUNNERS: Dict[str, Callable[..., None]] = {}


def runner(kind: str):
    def deco(fn):
        RUNNERS[kind] = fn
        return fn
    return deco


class SaveError(RuntimeError):
    """원장을 디스크에 못 썼어요 (디스크 가득·권한). 끈기 보장 불가."""


class QuestLedger:
    def __init__(self, state_dir: Path) -> None:
        self.path = Path(state_dir) / "quests.json"
        self.tmp = self.path.with_suffix(".json.tmp")
        self.quests: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()      # mutate+save 직렬화 (스레드 경주 방지)
        self.recovered: Optional[Dict[str, Any]] = None   # 훼손 복구 기록
        self.last_save_error: Optional[str] = None        # 최근 저장 실패
        self._load()

    # ── 원장 I/O (원자·내구) ───────────────────────────────────────────────
    def _load(self) -> None:
        with self._lock:
            self._clean_orphan_tmp()
            if not self.path.exists():
                self.quests = {}
                return
            try:
                raw = self.path.read_text(encoding="utf-8")
                data = json.loads(raw)
                if not isinstance(data, dict):
                    raise ValueError(f"원장은 dict 여야 해요, got {type(data).__name__}")
                self.quests = data
                self.recovered = None
            except Exception as exc:  # noqa: BLE001 — 훼손을 정직하게 격리
                self.quests, self.recovered = {}, self._quarantine(exc)

    def _clean_orphan_tmp(self) -> None:
        """크래시가 남긴 미완성 tmp 를 치워요 (본파일은 os.replace 전까지 불변)."""
        try:
            if self.tmp.exists():
                self.tmp.unlink()
        except OSError:
            pass

    def _quarantine(self, exc: Exception) -> Dict[str, Any]:
        """훼손 원장을 지우지 않고 옆으로 옮겨 증거를 보존해요."""
        ts = int(time.time())
        dest = self.path.with_name(f"quests.corrupt-{ts}.json")
        moved: Optional[str] = None
        try:
            os.replace(self.path, dest)
            moved = str(dest)
        except OSError:
            moved = None
        return {"reason": f"{type(exc).__name__}: {exc}",
                "quarantined_to": moved, "ts": ts}

    def _save(self) -> None:
        """tmp 에 쓰고 fsync 한 뒤 os.replace — 원자 + 내구. 실패는 표면화."""
        with self._lock:
            self.last_save_error = None
            try:
                with self.tmp.open("w", encoding="utf-8") as fh:
                    json.dump(self.quests, fh, ensure_ascii=False, indent=1)
                    fh.flush()
                    os.fsync(fh.fileno())
                os.replace(self.tmp, self.path)
            except OSError as exc:
                # 디스크 가득·권한 등 — tmp 만 치우고 본파일은 보존(발명 금지)
                self._clean_orphan_tmp()
                self.last_save_error = f"{type(exc).__name__}: {exc}"
                raise SaveError(self.last_save_error) from exc

    # ── 수명 주기 ──────────────────────────────────────────────────────────
    def begin(self, kind: str, title: str, payload: Dict[str, Any],
              steps: List[str]) -> str:
        with self._lock:
            qid = f"q-{kind}-{int(time.time() * 1000)}"
            n = 0
            while qid in self.quests:        # 같은 ms 동시 begin 충돌 방지
                n += 1
                qid = f"q-{kind}-{int(time.time() * 1000)}-{n}"
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
        with self._lock:
            q = self.quests[qid]
            q["step_index"] = next_index
            if data:
                q["checkpoint"].update(data)
            q["log"].append({"step": next_index - 1, "ts": time.time(), "note": note})
            q["updated_ts"] = time.time()
            self._save()

    def complete(self, qid: str, proof: Any = None, status: str = "done") -> None:
        with self._lock:
            q = self.quests[qid]
            q["status"] = status
            q["proof"] = proof
            q["updated_ts"] = time.time()
            self._save()

    def active(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [q for q in self.quests.values() if q["status"] == "active"]

    def health(self) -> Dict[str, Any]:
        """원장 자기 진단 — 복구 이력·저장 오류·퀘스트 수."""
        with self._lock:
            return {"quests": len(self.quests),
                    "active": sum(1 for q in self.quests.values()
                                  if q["status"] == "active"),
                    "recovered": self.recovered,
                    "last_save_error": self.last_save_error}

    # ── 실행 / 재개 ────────────────────────────────────────────────────────
    def run(self, qid: str, max_steps: int = 64) -> Dict[str, Any]:
        with self._lock:
            q = self.quests[qid]
        fn = RUNNERS.get(q["kind"])
        if fn is None:
            self._fail(qid, f"러너 없어요: {q['kind']}")
            return q
        while q["status"] == "active" and q["step_index"] < len(q["steps"]) \
                and max_steps > 0:
            max_steps -= 1
            step = q["steps"][q["step_index"]]
            try:
                fn(self, q, step)
            except Exception as exc:  # noqa: BLE001 — 죽은 퀘스트 금지
                self._fail(qid, f"{step}: {exc}")
                return q
        if q["status"] == "active" and q["step_index"] >= len(q["steps"]):
            try:
                self.complete(qid, proof=q["checkpoint"].get("proof"))
            except SaveError as exc:      # 완료조차 못 쓰는 극한 — 메모리만 표시
                with self._lock:
                    q["status"], q["proof"] = "done", {"save_error": str(exc)}
        return q

    def _fail(self, qid: str, error: str) -> None:
        """실패 기록 — 저장마저 실패하면 메모리에라도 정직하게 표시."""
        try:
            self.complete(qid, proof={"error": error}, status="failed")
        except SaveError as exc:
            with self._lock:
                q = self.quests.get(qid)
                if q:
                    q["status"] = "failed"
                    q["proof"] = {"error": error, "save_error": str(exc)}

    def resume_all(self) -> List[str]:
        """기동 시 멈춰 있던 퀘스트를 이어서 — 끈기의 증거."""
        done: List[str] = []
        for q in self.active():
            self.run(q["id"])
            done.append(q["id"])
        return done
