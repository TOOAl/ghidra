"""🧭🔗 Stage N 러너들 — 퀘스트 kind 별로 스텝의 의미를 알아요.

각 스텝은 "효과(멱등) → 체크포인트" 순서. kill -9 가 어디에 떨어져도
재개 후 효과가 두 번 관측되지 않아요.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict

from brain_engine import chain_reasoner, craft_engine, re_analyzer
from brain_engine.quest_ledger import runner


@runner("markers")
def _markers(led, q: Dict[str, Any], step: str) -> None:
    """끈기 기계 검증용: 멱등 마커 쓰기 → 체크포인트 → 지연(킬 창)."""
    payload = q["payload"]
    target = Path(payload["dir"]) / "markers.log"
    target.parent.mkdir(parents=True, exist_ok=True)
    have = target.read_text(encoding="utf-8") if target.exists() else ""
    if step not in have.splitlines():          # 멱등 효과
        with target.open("a", encoding="utf-8") as fh:
            fh.write(step + "\n")
    idx = q["steps"].index(step) + 1
    led.checkpoint(q["id"], idx, note=f"marker {step}")
    time.sleep(float(payload.get("delay", 0)))


@runner("craft")
def _craft(led, q: Dict[str, Any], step: str) -> None:
    binary = Path(q["payload"]["binary"])
    cp = q["checkpoint"]
    if step == "inspect":
        facts = re_analyzer.analyze(binary, backend="auto", cap=200)
        led.checkpoint(q["id"], 1, {"facts": facts}, "ghidra facts")
    elif step == "build":
        facts = cp["facts"]
        is_pe = binary.read_bytes()[:2] == b"MZ"
        built: Dict[str, Any] = {}
        for f in facts["functions"]:
            raw = f.get("insns") or []
            ins = raw.splitlines() if isinstance(raw, str) else list(raw)
            dec = (f.get("decompile") or "").strip()
            if not dec or not ins:
                continue
            # Stage N3: 직선 스칼라 + 제어흐름·메모리 모두 synth_for 한 경로로
            synth = craft_engine.synth_for(dec, ins, is_pe)
            if synth:
                built[f["name"]] = synth
        led.checkpoint(q["id"], 2, {"built": built}, "synthesized")
    elif step == "compare":
        facts = cp["facts"]
        built = cp["built"]
        results = []
        for f in facts["functions"]:
            name = f["name"]
            if name not in built:
                continue
            raw = f.get("insns") or []
            ins = raw.splitlines() if isinstance(raw, str) else list(raw)
            synth = built[name]
            if isinstance(synth, str):           # 옛 체크포인트 하위 호환
                synth = {"kind": "straight", "src": synth}
            try:
                diff = craft_engine.differential(ins, synth)
            except Exception as exc:  # noqa: BLE001
                results.append({"name": name, "why": f"diff {exc}"})
                continue
            if synth.get("kind") == "cf" and diff["vectors"] < craft_engine._MIN_CF_COMPARABLE:
                results.append({"name": name, "why": "cf 비교가능 벡터 부족"})
                continue
            results.append({"name": name, "kind": synth.get("kind"),
                            "vectors": diff["vectors"], "match_pct": diff["match_pct"]})
        led.checkpoint(q["id"], 3, {"results": results}, "differential test")
    elif step == "record":
        results = cp["results"]
        ok = [r for r in results if r.get("match_pct") == 100.0]
        led.checkpoint(q["id"], 4,
                       {"proof": {"verified": [r["name"] for r in ok],
                                  "results": results,
                                  "binary": binary.name}},
                       "record")


@runner("garden")
def _garden(led, q: Dict[str, Any], step: str) -> None:
    """정원 가꾸기를 원장으로 — reindex → semantic train → report.

    러너는 자가완결: payload 의 경로로 WikiGardener 를 재구성해요
    (원장은 JSON 이라 라이브 객체를 못 실어요). 각 스텝은 멱등 —
    다시 돌려도 같은 인덱스/의미공간으로 수렴.
    """
    from brain_engine.wiki_gardener import WikiGardener
    p = q["payload"]
    g = WikiGardener(Path(p["vault"]), Path(p["db"]))
    if step == "reindex":
        g.rebuild_index()
        n = len(g.list_notes())
        led.checkpoint(q["id"], 1, {"notes": n}, f"reindexed {n} notes")
    elif step == "train":
        st = g.semantic.train(g.list_notes())
        led.checkpoint(q["id"], 2,
                       {"vocab": st.get("vocab_size", 0),
                        "trained": bool(st.get("trained"))},
                       f"trained vocab={st.get('vocab_size', 0)}")
    elif step == "report":
        cp = q["checkpoint"]
        st = g.semantic.status()
        led.checkpoint(q["id"], 3,
                       {"proof": {"notes": cp.get("notes"),
                                  "vocab": cp.get("vocab"),
                                  "trained": cp.get("trained"),
                                  "cosine_fidelity_pct":
                                      st.get("cosine_fidelity_pct"),
                                  "cache_kb": st.get("cache_kb")}},
                       "garden report")


@runner("chain")
def _chain(led, q: Dict[str, Any], step: str) -> None:
    notes = q["payload"]["notes"]
    if step == "reason":
        res = chain_reasoner.reason(q["payload"]["question"], notes,
                                    max_hops=int(q["payload"].get("max_hops", 3)))
        led.checkpoint(q["id"], 1, {"result": res}, "reasoned")
    elif step == "audit":
        res = cp_result = q["checkpoint"].get("result") or {}
        root = Path(q["payload"]["root"]) / "vault"
        audit_ok = True
        for e in res.get("evidence", []):
            a = next((n for n in notes if n["slug"] == e["from"]), None)
            b = next((n for n in notes if n["slug"] == e["to"]), None)
            if not a or not b:
                audit_ok = False
                continue
            try:
                ta = (root / a["rel_path"]).read_text(encoding="utf-8")
                tb = (root / b["rel_path"]).read_text(encoding="utf-8")
            except OSError:
                audit_ok = False
                continue
            if e["type"] == "link":
                audit_ok &= f"[[{b['title']}]]" in ta
            else:  # tag·ident — edges_of 가 소문자화하므로 대조도 소문자로
                lo_a, lo_b, br = ta.lower(), tb.lower(), e["bridge"].lower()
                audit_ok &= br in lo_a and br in lo_b
        led.checkpoint(q["id"], 2,
                       {"proof": {"answer": res.get("answer"),
                                  "hops": res.get("hops"),
                                  "audit_ok": bool(audit_ok)}},
                       "audited against files")
