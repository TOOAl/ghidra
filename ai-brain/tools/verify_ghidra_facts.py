"""🚚 Stage L — end-to-end verification of a delivered Ghidra distribution.

Run AFTER tools/fetch_ghidra_dist.sh has unpacked a dist and its smoke test has
written /tmp/brain_facts.json through ghidra_facts_pyghidra.py (PyGhidra,
in-process — Ghidra 12 has no Jython and no javac is available).  This script then
proves, with numbers, that the REAL Ghidra (not objdump) now feeds the machine
channel without touching the prose channel:

  1. the facts file is genuine Ghidra output (functions, mnemonics, calls)
  2. the decompiler actually produced C (the thing objdump can never give)
  3. the facts become `kind: code` memories that survive a vault round-trip
  4. training them beside the 12 prose memories leaves prose EXACTLY as it was
     (vocab 476, gaps 4/4, nonsense pairs 0.083/0.045) — the Stage-L invariant
  5. the machine channel's blind spots are structural facts from the call graph

Exit code 0 = the delivery is real and safe to teach from.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from brain_engine import re_analyzer  # noqa: E402
from brain_engine.semantic_memory import CODE_KIND, PROSE_KIND, CorpusChannels, note_kind  # noqa: E402
from brain_engine.wiki_gardener import WikiGardener  # noqa: E402

# 공유 가변 경로를 믿지 않아요: verify 는 검증용 팩트를 **스스로 뽑아요**
# (마지막 ingest/craft 가 /tmp/brain_facts.json 을 덮어쓴 사고 실측).
FACTS = Path("/tmp/verify_facts.json")
SAMPLE = (Path(__file__).resolve().parent.parent.parent / "GhidraDocs" /
          "GhidraClass" / "ExerciseFiles" / "Advanced" / "globalRegVars.so")
# 산문 불변의 기준은 /tmp 픽스처가 아니라 **커밋된 vault 산문 노트**예요 —
# 새 숙주에서도 스스로 재생성돼야 검증이 재현돼요 (소유권 원칙).
FIXTURE = Path(__file__).resolve().parent.parent / "vault"
SCRATCH = Path("/tmp/l_ghidra_vault")
STATE = Path("/tmp/l_ghidra_state")

ok = True


def check(label: str, cond: bool, detail: str = "") -> None:
    global ok
    ok = ok and bool(cond)
    print(f"  {'✅' if cond else '❌'} {label} {detail}")


def main() -> int:
    import os
    import subprocess

    headless = re_analyzer.ghidra_headless()
    if not headless or not SAMPLE.exists():
        print("❌ dist 또는 표본이 없어요 — fetch_ghidra_dist.sh 를 먼저.")
        return 3
    env = re_analyzer._java_env()
    env["GHIDRA_INSTALL_DIR"] = str(headless.parent.parent)
    tool = Path(__file__).resolve().parent / "ghidra_facts_pyghidra.py"
    proc = subprocess.run([sys.executable, str(tool), str(SAMPLE), str(FACTS), "400"],
                          capture_output=True, text=True, timeout=1200,
                          check=False, env=env)
    if not FACTS.exists():
        print("❌ 팩트 자가 추출 실패:", (proc.stderr or proc.stdout)[-300:])
        return 3
    raw = json.loads(FACTS.read_text(encoding="utf-8"))
    funcs = raw.get("functions") or []
    print(f"── 1) Ghidra 사실 파일: {raw.get('binary')} · 함수 {len(funcs)}개 ──")
    check("함수 존재", len(funcs) > 0, f"= {len(funcs)}")
    check("니모닉 존재", all(f.get("mnemonics") for f in funcs[:20]))
    dec = [f for f in funcs if (f.get("decompile") or "").strip()]
    print("── 2) 디컴파일러(objdump는 결코 못 주는 것) ──")
    check("디컴파일된 C 존재", len(dec) > 0, f"= {len(dec)}개 함수")
    if dec:
        first = dec[0]["decompile"].strip().splitlines()
        print("     예:", first[0][:80] if first else "-")
    print("── 3) 사실 → 기계 기억 → vault 왕복 ──")
    notes = re_analyzer.build_notes({"backend": raw.get("backend", "analyzeHeadless"), "binary": raw.get("binary", "ghidra"), "functions": funcs})
    check("kind=code 부여", all(note_kind(n) == CODE_KIND for n in notes), f"{len(notes)}장")
    shutil.rmtree(SCRATCH, ignore_errors=True)
    (SCRATCH / "30_Ghidra").mkdir(parents=True, exist_ok=True)
    paths = re_analyzer.write_code_notes(SCRATCH, notes)

    class _Stub:
        vault_dir = SCRATCH

    back = [WikiGardener._parse_markdown(_Stub(), p) for p in paths]
    check("왕복 후 kind 보존", all(note_kind(n) == CODE_KIND for n in back),
          f"{sum(1 for n in back if note_kind(n) == CODE_KIND)}/{len(back)}")
    edges = re_analyzer.call_edges(back)
    print("── 4) 산문 불변(Stage L 불변식) ──")

    class _S2:
        vault_dir = FIXTURE

    prose = [WikiGardener._parse_markdown(_S2(), f)
             for f in sorted(FIXTURE.rglob("*.md"))
             if 'kind: "code"' not in f.read_text(encoding="utf-8")]
    # 불변식은 낡은 상수가 아니라 **같은 런 안의 차이**예요: 산문만 훈련한
    # 채널과 산문+기계 노트 훈련 채널이 산문에 대해 동일해야 해요.
    # (vault 산문은 시냅스 relink 로 진화하므로 476/4/0.083 은 스냅샷 값일 뿐)
    STATE2 = Path("/tmp/l_ghidra_state_base")
    shutil.rmtree(STATE, ignore_errors=True)
    shutil.rmtree(STATE2, ignore_errors=True)
    base = CorpusChannels(STATE2)
    st0 = base.train(prose)
    ch = CorpusChannels(STATE)
    st = ch.train(prose + back)
    pro0 = (st0.get("channels") or {}).get("prose") or {}
    pro = (st.get("channels") or {}).get("prose") or {}
    check("산문 어휘: 코드 수유 전후 동일",
          pro0.get("vocab_size") == pro.get("vocab_size"),
          f"= {pro0.get('vocab_size')} vs {pro.get('vocab_size')}")
    orp0 = [g["slug"] for g in base.orphans(prose, cos_min=0.45, top_k=99)]
    orp = [g["slug"] for g in ch.orphans(prose + back, cos_min=0.45, top_k=99)
           if note_kind(next(n for n in prose + back if n["slug"] == g["slug"])) == PROSE_KIND]
    check("산문 구멍 목록: 코드 수유 전후 동일", orp0 == orp,
          f"= {len(orp)}장 {orp if len(orp) <= 5 else ''}")

    def byt(ns, k):
        return next(n for n in ns if k in n["title"])

    a1 = base.pair_similarity(byt(prose, "스킬 카트리지"), byt(prose, "성좌 원탁 담론"))
    a2 = base.pair_similarity(byt(prose, "LLM 위키"), byt(prose, "복어"))
    n1 = ch.pair_similarity(byt(prose, "스킬 카트리지"), byt(prose, "성좌 원탁 담론"))
    n2 = ch.pair_similarity(byt(prose, "LLM 위키"), byt(prose, "복어"))
    check("산문 쌍 코사인: 코드 수유 전후 동일",
          abs(a1 - n1) < 1e-9 and abs(a2 - n2) < 1e-9,
          f"= {round(n1, 3)}/{round(n2, 3)} (전 {round(a1, 3)}/{round(a2, 3)})")
    check("엉터리 쌍은 낮음(절대 sanity)", max(n1, n2) < 0.2,
          f"= max {round(max(n1, n2), 3)}")
    print("── 5) 기계 채널의 구조적 구멍 ──")
    cg = ch.code_orphans(prose + back)
    check("구조적 구멍 보고", isinstance(cg, list) and all("in_edges" in g for g in cg),
          f"= {len(cg)}개 · 간선 {len(edges)}개")
    print("\n" + ("✅ GHIDRA DELIVERY END-TO-END PASSED" if ok else "❌ FAILED"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
