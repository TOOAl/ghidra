#!/usr/bin/env python3
"""🧭🔗 Stage N hardening — 퀘스트 원장 + 사슬 추론의 회복력 기계 증명.

자가완결·멱등: 임시 디렉터리만 쓰고(라이브 state/vault 불변), 외부 모델·
네트워크 없음. 어떤 검사든 실패하면 exit 1 (CI 게이트 가능).

커버:
  1) 동시성  — N 스레드 begin/checkpoint/complete → 원장 손상 0·qid 충돌 0
  2) 훼손 격리 — garbage quests.json → 빈 상태 재기동 + corrupt 파일 격리 + recovered 기록
  3) 디스크 가득 — os.replace ENOSPC → SaveError, tmp 청소, 본파일(마지막 좋은 상태) 보존
  4) orphan tmp — 크래시가 남긴 .json.tmp → 로드 시 청소, 본파일 불변
  5) 부분 사슬 — 도달 불가 두 초점 → known:False + partial(가장 가까운 접근) 보고
  6) 깊은 다홉 — 5-링크 사슬: max_hops=3 부분실패, max_hops=6 성공(hops=5)
  7) garden 퀘스트 — 임시 vault+db 로 reindex→train→report end-to-end (두뇌 소유)
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import threading
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
BRAIN = HERE.parent
sys.path.insert(0, str(BRAIN))

from brain_engine import chain_reasoner as cr          # noqa: E402
from brain_engine import quest_runners                 # noqa: E402,F401  러너 등록
from brain_engine.quest_ledger import QuestLedger, SaveError  # noqa: E402

PASS = FAIL = 0


def check(cond: bool, label: str, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ✅ {label}")
    else:
        FAIL += 1
        print(f"  ❌ {label} — {detail}")


def _note(slug: str, title: str, links=None, tags=None) -> dict:
    return {"slug": slug, "title": title, "category": "c",
            "tags": tags or [], "summary": title, "body": "",
            "links": links or [], "rel_path": ""}


# ── 1) 동시성 ─────────────────────────────────────────────────────────────
def test_concurrency(tmp: Path) -> None:
    print("── 1) 동시 저장 (스레드 경주) ──")
    led = QuestLedger(tmp)
    n_threads, per = 12, 5
    qids: list = []
    lock = threading.Lock()
    errors: list = []

    def worker(w: int) -> None:
        try:
            qid = led.begin("markers", f"t{w}", {"dir": str(tmp / f"m{w}"),
                                                 "delay": 0},
                            [f"s{i}" for i in range(per)])
            with lock:
                qids.append(qid)
            for i in range(per):
                led.checkpoint(qid, i + 1, note=f"w{w}s{i}")
            led.complete(qid, proof={"w": w})
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{type(exc).__name__}: {exc}")

    ts = [threading.Thread(target=worker, args=(w,)) for w in range(n_threads)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    check(not errors, f"스레드 {n_threads}개 오류 0", str(errors[:2]))
    check(len(set(qids)) == n_threads, "qid 충돌 0 (전부 유일)",
          f"uniq={len(set(qids))}/{n_threads}")
    # 디스크에서 다시 로드 — torn write 없어야 함
    reloaded = QuestLedger(tmp)
    check(len(reloaded.quests) == n_threads,
          f"원장에 {n_threads}퀘스트 온전", f"got {len(reloaded.quests)}")
    check(all(q["status"] == "done" for q in reloaded.quests.values()),
          "전부 done (완전성)", "일부 미완")
    check(all(len(q["log"]) == per for q in reloaded.quests.values()),
          f"각 퀘스트 log {per}개 (유실 0)", "log 유실")


# ── 2) 훼손 격리 ──────────────────────────────────────────────────────────
def test_corrupt_quarantine(tmp: Path) -> None:
    print("── 2) 훼손 원장 격리 ──")
    good = QuestLedger(tmp)
    qid = good.begin("markers", "keep", {"dir": str(tmp), "delay": 0}, ["s0"])
    good.complete(qid, proof={"ok": 1})
    before = (tmp / "quests.json").read_text(encoding="utf-8")
    # 훼손
    (tmp / "quests.json").write_text("{ 이건 json 이 아님 ::: ", encoding="utf-8")
    led = QuestLedger(tmp)
    check(led.quests == {}, "훼손 → 빈 상태로 정직 재기동 (발명 없음)",
          f"quests={len(led.quests)}")
    rec = led.recovered or {}
    check(bool(rec.get("reason")), "recovered.reason 기록", str(rec))
    qpath = rec.get("quarantined_to")
    check(bool(qpath) and Path(qpath).exists(), "손상본 격리 파일로 보존",
          str(qpath))
    check("json 이 아님" in Path(qpath).read_text(encoding="utf-8")
          if qpath and Path(qpath).exists() else False,
          "격리 파일 = 원래 손상 내용 (증거 보존)", "")
    # 격리 후 새 저장은 깨끗한 파일로
    led.begin("markers", "fresh", {"dir": str(tmp), "delay": 0}, ["s0"])
    check(json.loads((tmp / "quests.json").read_text(encoding="utf-8")) != {},
          "격리 후 새 원장 쓰기 정상", "")
    _ = before


# ── 3) 디스크 가득 ────────────────────────────────────────────────────────
def test_disk_full(tmp: Path) -> None:
    print("── 3) 디스크 가득 (저장 실패) ──")
    led = QuestLedger(tmp)
    qid = led.begin("markers", "d", {"dir": str(tmp), "delay": 0}, ["s0", "s1"])
    led.checkpoint(qid, 1, note="good")           # 마지막 좋은 상태 저장됨
    good_disk = (tmp / "quests.json").read_text(encoding="utf-8")
    good_index = json.loads(good_disk)[qid]["step_index"]

    real_replace = os.replace
    os.replace = lambda *a, **k: (_ for _ in ()).throw(
        OSError(28, "No space left on device"))
    try:
        raised = False
        try:
            led.checkpoint(qid, 2, note="will fail")
        except SaveError:
            raised = True
        check(raised, "SaveError 표면화 (조용한 유실 아님)", "")
        check(led.last_save_error and "space" in led.last_save_error.lower(),
              "last_save_error 기록", str(led.last_save_error))
        check(not (tmp / "quests.json.tmp").exists(), "실패 후 tmp 청소", "tmp 잔존")
        after = (tmp / "quests.json").read_text(encoding="utf-8")
        check(after == good_disk, "본파일 = 마지막 좋은 상태 보존 (손상 0)",
              "본파일 변질")
        check(json.loads(after)[qid]["step_index"] == good_index,
              "디스크 진도 = 마지막 성공 체크포인트", "진도 어긋남")
    finally:
        os.replace = real_replace


# ── 4) orphan tmp ─────────────────────────────────────────────────────────
def test_orphan_tmp(tmp: Path) -> None:
    print("── 4) 크래시 잔재 tmp 청소 ──")
    led = QuestLedger(tmp)
    qid = led.begin("markers", "o", {"dir": str(tmp), "delay": 0}, ["s0"])
    led.complete(qid, proof={"ok": 1})
    main_before = (tmp / "quests.json").read_text(encoding="utf-8")
    (tmp / "quests.json.tmp").write_text("{ 미완성 쓰기 ", encoding="utf-8")
    led2 = QuestLedger(tmp)                        # 로드 시 청소되어야 함
    check(not (tmp / "quests.json.tmp").exists(), "orphan tmp 자동 청소", "잔존")
    check((tmp / "quests.json").read_text(encoding="utf-8") == main_before,
          "본파일 불변 (orphan 이 안 덮어씀)", "본파일 변질")
    check(led2.quests.get(qid, {}).get("status") == "done",
          "기존 퀘스트 온전 로드", "")


# ── 5) 부분 사슬 ──────────────────────────────────────────────────────────
def test_partial_chain() -> None:
    print("── 5) 부분 사슬 보고 (도달 불가) ──")
    # 두 단절 성분: alpha{uno,dos} 와 omega{trois,quatre} — 공유 토큰·간선 없음
    notes = [_note("a0", "alpha uno", links=["alpha dos"]),
             _note("a1", "alpha dos"),
             _note("z0", "omega trois"),
             _note("z1", "omega quatre", links=["omega trois"])]
    r = cr.reason("alpha uno 와 omega quatre 는 어떻게 이어져?", notes, max_hops=6)
    check(r["known"] is False, "도달 불가 → known:False (발명 거부)", str(r["known"]))
    part = r.get("partial") or {}
    check(bool(part), "partial 보고 존재", str(r.get("answer"))[:60])
    check(part.get("reached", 0) >= 1, "탐색 도달 수 보고", str(part))
    check("가장 가까운 접근" in r["answer"], "답에 closest approach 명시",
          r["answer"][:60])
    check(part.get("overlap", -1) == 0, "단절 성분 → 도착과 공유 토큰 0", str(part))


# ── 6) 깊은 다홉 ──────────────────────────────────────────────────────────
def test_deep_hops() -> None:
    print("── 6) 깊은 다홉 (>3) ──")
    titles = [f"node {w}" for w in ("alpha", "beta", "gamma", "delta",
                                     "epsilon", "zeta")]
    notes = []
    for i, t in enumerate(titles):
        links = [titles[i + 1]] if i + 1 < len(titles) else []
        notes.append(_note(f"n{i}", t, links=links))
    q = f"{titles[0]} 와 {titles[-1]} 는 어떻게 이어져?"   # 5 홉
    r3 = cr.reason(q, notes, max_hops=3)
    r6 = cr.reason(q, notes, max_hops=6)
    check(r3["known"] is False and bool(r3.get("partial")),
          "max_hops=3 → 5홉 도달 불가 (부분 보고)", str(r3["known"]))
    check(r6["known"] is True and r6["hops"] == 5,
          "max_hops=6 → hops=5 사슬 완성", f"hops={r6.get('hops')}")
    check(all(e["type"] == "link" for e in r6["evidence"]),
          "사슬 전부 link 증거 (실제 [[링크]])",
          str([e["type"] for e in r6["evidence"]]))
    r99 = cr.reason(q, notes, max_hops=99)
    check(r99["known"] is True, "max_hops 상한(8) 캡 후에도 도달", "")


# ── 7) garden 퀘스트 ──────────────────────────────────────────────────────
def test_garden_quest(tmp: Path) -> None:
    print("── 7) garden 퀘스트 end-to-end (임시 vault+db) ──")
    vault = tmp / "vault"
    for sub in ("00_Raw", "10_Wiki", "20_Skills", "30_Ghidra"):
        (vault / sub).mkdir(parents=True, exist_ok=True)
    for i in range(3):
        (vault / "10_Wiki" / f"note{i}.md").write_text(
            f"---\ntitle: \"테스트 노트 {i}\"\ncategory: \"wiki\"\n"
            f"tags: [test, n{i}]\ncreated: \"\"\n---\n\n# 테스트 노트 {i}\n\n"
            f"내용 {i} — 정원 가꾸기 회복력 검사용.\n", encoding="utf-8")
    db = tmp / "st" / "wiki_index.db"
    db.parent.mkdir(parents=True, exist_ok=True)
    led = QuestLedger(tmp / "st")
    qid = led.begin("garden", "garden test", {"vault": str(vault), "db": str(db)},
                    ["reindex", "train", "report"])
    led.run(qid)
    q = led.quests[qid]
    check(q["status"] == "done", "garden 퀘스트 done", q.get("proof"))
    p = q.get("proof") or {}
    check((p.get("notes") or 0) >= 3, f"reindex 노트 ≥3 ({p.get('notes')})", str(p))
    check(p.get("trained") is True, "semantic train 됨", str(p))
    check((p.get("vocab") or 0) > 0, f"vocab >0 ({p.get('vocab')})", str(p))
    # db/semantic 캐시가 임시 디렉터리에만 — 라이브 불변
    check((tmp / "st" / "wiki_index.db").exists(), "임시 db 생성 (격리)", "")


def main() -> int:
    print("🧭🔗 Stage N 회복력 기계 증명 — quest_ledger + chain_reasoner\n")
    for fn in (test_concurrency, test_corrupt_quarantine, test_disk_full,
               test_orphan_tmp, test_garden_quest):
        d = Path(tempfile.mkdtemp(prefix="qtest_"))
        try:
            fn(d)
        except Exception:  # noqa: BLE001
            global FAIL
            FAIL += 1
            print(f"  ❌ 예외:\n{traceback.format_exc()}")
        finally:
            shutil.rmtree(d, ignore_errors=True)
    for fn in (test_partial_chain, test_deep_hops):
        try:
            fn()
        except Exception:  # noqa: BLE001
            FAIL += 1
            print(f"  ❌ 예외:\n{traceback.format_exc()}")
    print(f"\n{'✅ QUEST RESILIENCE PASSED' if FAIL == 0 else '❌ FAILED'}"
          f" — {PASS} passed / {FAIL} failed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
