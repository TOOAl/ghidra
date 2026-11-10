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
from brain_engine.semantic_memory import CODE_KIND, CorpusChannels, note_kind  # noqa: E402
from brain_engine.wiki_gardener import WikiGardener  # noqa: E402

FACTS = Path("/tmp/brain_facts.json")
FIXTURE = Path("/tmp/k_fixture/vault")
SCRATCH = Path("/tmp/l_ghidra_vault")
STATE = Path("/tmp/l_ghidra_state")

ok = True


def check(label: str, cond: bool, detail: str = "") -> None:
    global ok
    ok = ok and bool(cond)
    print(f"  {'✅' if cond else '❌'} {label} {detail}")


def main() -> int:
    if not FACTS.exists():
        print("❌ /tmp/brain_facts.json 이 없어요 — fetch_ghidra_dist.sh 를 먼저.")
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

    prose = [WikiGardener._parse_markdown(_S2(), f) for f in sorted(FIXTURE.rglob("*.md"))]
    shutil.rmtree(STATE, ignore_errors=True)
    ch = CorpusChannels(STATE)
    st = ch.train(prose + back)
    pro = (st.get("channels") or {}).get("prose") or {}
    check("산문 어휘 476 그대로", pro.get("vocab_size") == 476, f"= {pro.get('vocab_size')}")
    orp = ch.orphans(prose + back, cos_min=0.45, top_k=99)
    check("산문 구멍 4장 그대로", len(orp) == 4, f"= {len(orp)}")

    def byt(ns, k):
        return next(n for n in ns if k in n["title"])

    n1 = ch.pair_similarity(byt(prose, "스킬 카트리지"), byt(prose, "성좌 원탁 담론"))
    n2 = ch.pair_similarity(byt(prose, "LLM 위키"), byt(prose, "복어"))
    check("엉터리 쌍 낮음", abs(n1 - 0.083) < 0.02 and abs(n2 - 0.045) < 0.02,
          f"= {round(n1, 3)}/{round(n2, 3)}")
    print("── 5) 기계 채널의 구조적 구멍 ──")
    cg = ch.code_orphans(prose + back)
    check("구조적 구멍 보고", isinstance(cg, list) and all("in_edges" in g for g in cg),
          f"= {len(cg)}개 · 간선 {len(edges)}개")
    print("\n" + ("✅ GHIDRA DELIVERY END-TO-END PASSED" if ok else "❌ FAILED"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
