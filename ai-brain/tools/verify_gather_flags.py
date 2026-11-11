#!/usr/bin/env python3
"""🔬 live 채집 검증 — 캡 완전성 플래그와 N3 픽스처를 **실제 Ghidra**로 증명해요.

왜 존재하나
    v7.3.8 감사에서 두 가지를 고쳤지만 **기계증명하지 못했어요**:
      ⑤ `ghidra_facts_pyghidra.py` 의 캡(`_INSN_CAP`/`_DEC_LINE_CAP`)과 새 플래그
        (`insns_complete`/`decompile_truncated`) — 이 샌드박스에 Ghidra dist 가 없어서
        py_compile 검증만 했어요. 플래그가 **실제 채집에서 뒤집히는지**는 미검증.
      ③ `test_n3_craft.py` 의 `classify` 픽스처 RET 복구 — gcc 재컴파일 + objdump
        대조로 근거를 확보했지만, **Ghidra 자체의 출력**과 대조한 것은 아니었어요.
    이 도구가 그 둘을 live Ghidra 로 닫아요.

검증 내용
  A) 픽스처 충실성 — SPECIMEN_C 를 gcc 로 다시 컴파일하고 live Ghidra 로 채집해서,
     픽스처의 명령 행렬이 **실제 Ghidra 출력과 일치**하는지 전수 대조해요
     (특히 `classify` 가 실제로 RET 로 끝나는지 = ③ 복구 검증).
  B) 캡 플래그 — 캡을 **넘기는** 함수를 일부러 만들어 `insns_complete=False`·
     `decompile_truncated=True` 가 실제로 찍히는지, 그리고 그 값이 캡 상수와
     **정확히** 일치하는지(명령 수 == _INSN_CAP, C 줄 수 == _DEC_LINE_CAP) 검증.
  C) 작은 함수는 두 플래그가 각각 True/False 여야 해요(과잉 보고 금지).

정직 원칙: 선행조건(gcc·Ghidra 설치·pyghidra)이 없으면 **추측하지 않고 rc=3 으로
정직 skip** 해요(다른 verify_* 도구와 같은 규칙). rc=0 만이 "증명됨"이에요.

실행 방법 (dist 는 tools/fetch_ghidra_dist.sh 가 배달해요):
    GHIDRA_INSTALL_DIR=<ghidra_root> <jdkenv>/bin/python tools/verify_gather_flags.py
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
GATHERER = HERE / "ghidra_facts_pyghidra.py"

_PASS = 0
_FAIL = 0


def check(cond: bool, label: str, detail: str = "") -> None:
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ✅ {label}")
    else:
        _FAIL += 1
        print(f"  ❌ {label}" + (f"\n       → {detail}" if detail else ""))


def _skip(why: str) -> int:
    print(f"\n⚠️  정직 skip — 검증하지 않았어요 (rc=3): {why}")
    print("   dist 배달: bash ai-brain/tools/fetch_ghidra_dist.sh")
    return 3


def _load_module(name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def _split_specimen(text: str) -> Tuple[str, str]:
    """SPECIMEN_C 를 -O0 블록과 -O2 블록으로 갈라요(픽스처 채집 조건과 동일하게).

    주의: 헤더 주석은 **여러 줄**이에요. 한 줄 안에 `/* ... */` 가 닫히는 것만
    마커로 보고, 열린 주석은 `*/` 가 나올 때까지 통째로 건너뛰어요.
    """
    o0: List[str] = []
    o2: List[str] = []
    cur = o0
    in_comment = False
    for line in text.split("\n"):
        st = line.strip()
        if in_comment:
            if "*/" in st:
                in_comment = False
            continue
        if st.startswith("/*"):
            if "*/" not in st:                  # 여러 줄 주석 시작 → 건너뛰기
                in_comment = True
                continue
            if "-O2" in st:
                cur = o2
            elif "-O0" in st:
                cur = o0
            continue
        if st:
            cur.append(line)
    return "\n".join(o0) + "\n", "\n".join(o2) + "\n"


def _collect(work: Path, src_name: str, c_src: str, opt: str,
             out_name: str) -> Optional[Dict[str, Any]]:
    """gcc 로 컴파일 → live Ghidra(pyghidra) 채집 → facts dict."""
    cpath = work / src_name
    cpath.write_text(c_src, encoding="utf-8")
    opath = work / out_name
    cp = subprocess.run(["gcc", opt, "-c", str(cpath), "-o", str(opath)],
                        capture_output=True, text=True)
    if cp.returncode != 0:
        print(f"  ❌ gcc {opt} 실패: {cp.stderr.strip()[:200]}")
        return None
    fpath = work / (out_name + ".facts.json")
    env = dict(os.environ)
    cp = subprocess.run([sys.executable, str(GATHERER), str(opath), str(fpath)],
                        capture_output=True, text=True, env=env)
    if cp.returncode != 0 or not fpath.exists():
        print(f"  ❌ 채집 실패(rc={cp.returncode}): "
              f"{(cp.stderr or cp.stdout).strip()[-400:]}")
        return None
    return json.loads(fpath.read_text(encoding="utf-8"))


def _body(insn: str) -> str:
    """`0010002e:\\tPUSH RBP` → `PUSH RBP` (주소는 컴파일/로더에 따라 달라져요)."""
    return insn.split(":", 1)[-1].strip() if ":" in insn else insn.strip()


def main() -> int:
    print("🔬 live 채집 검증 — 캡 완전성 플래그 + N3 픽스처 충실성\n")
    inst = os.environ.get("GHIDRA_INSTALL_DIR", "")
    if not inst or not (Path(inst) / "support" / "analyzeHeadless").exists():
        return _skip(f"GHIDRA_INSTALL_DIR 가 Ghidra 설치를 가리키지 않아요 ({inst!r})")
    if not shutil.which("gcc"):
        return _skip("gcc 가 없어 specimen 을 컴파일할 수 없어요")
    try:
        import pyghidra  # noqa: F401
    except Exception as exc:                              # noqa: BLE001
        return _skip(f"pyghidra 를 import 할 수 없어요 ({type(exc).__name__}) — "
                     "jdkenv 파이썬으로 실행하셨나요?")
    if not GATHERER.exists():
        return _skip(f"채집기가 없어요: {GATHERER.name}")

    n3 = _load_module("test_n3_craft")
    fixture: Dict[str, Any] = n3.FUNCS
    o0_src, o2_src = _split_specimen(n3.SPECIMEN_C)
    check(bool(o0_src) and bool(o2_src), "SPECIMEN_C 를 -O0/-O2 블록으로 분리",
          f"o0={len(o0_src)}자 o2={len(o2_src)}자")

    work = Path(tempfile.mkdtemp(prefix="live_gather_"))
    try:
        # ── A) 픽스처 충실성: 실제 Ghidra 출력과 전수 대조 ─────────────────
        print("\n[A] 픽스처 충실성 — SPECIMEN_C 재컴파일 → live Ghidra 채집 → 대조")
        facts_o0 = _collect(work, "n3.c", o0_src, "-O0", "n3.o")
        facts_o2 = _collect(work, "sl.c", o2_src, "-O2", "sl.o")
        live: Dict[str, Dict[str, Any]] = {}
        for f in (facts_o0, facts_o2):
            if f:
                for fn in f.get("functions", []):
                    live[fn["name"]] = fn
        check(facts_o0 is not None and facts_o2 is not None,
              "live 채집 성공(-O0 · -O2 둘 다)", "채집 실패")
        if not live:
            print("\n❌ live 출력이 없어 대조 불가 — 정직하게 실패로 보고해요")
            return 1

        present = sorted(set(fixture) & set(live))
        check(len(present) == len(fixture),
              f"픽스처 {len(fixture)}개 함수 전부 live 출력에 존재",
              f"누락={sorted(set(fixture) - set(live))}")

        mismatch: List[str] = []
        ret_ok: List[str] = []
        for name in present:
            want = [_body(i) for i in fixture[name]["insns"]]
            got = [_body(i) for i in live[name].get("insns", [])]
            if want != got:
                # 어디서 갈리는지 첫 지점을 찾아요(진단 정보)
                at = next((k for k in range(max(len(want), len(got)))
                           if (want[k:k + 1] or ["<끝>"]) != (got[k:k + 1] or ["<끝>"])), -1)
                mismatch.append(f"{name}[{at}]: 픽스처={want[at:at+1]} live={got[at:at+1]} "
                                f"(길이 {len(want)} vs {len(got)})")
            elif got and got[-1].lower().startswith("ret"):
                ret_ok.append(name)
        check(not mismatch,
              f"{len(present)}개 함수 명령 행렬이 live Ghidra 와 완전 일치",
              " | ".join(mismatch[:4]))
        check(len(ret_ok) == len(present),
              f"{len(ret_ok)}개 함수 전부 RET 로 종결(③ 픽스처 복구 검증)",
              f"RET 아님={sorted(set(present) - set(ret_ok))}")
        # ③의 핵심: classify 는 구버전 캡(16) 시절 잘려 있었어요
        cl = live.get("classify", {}).get("insns", [])
        check(len(cl) == len(fixture.get("classify", {}).get("insns", []))
              and _body(cl[-1]).lower().startswith("ret") if cl else False,
              f"classify 실제 {len(cl)}명령·RET 종결 = 픽스처와 동일(③ 복구 정답)",
              f"live={[_body(i) for i in cl[-2:]]}")

        # ── B) 캡 플래그: 캡을 넘기는 함수로 실제로 뒤집히는지 ──────────────
        print("\n[B] 캡 플래그 — 캡 초과 함수에서 실제로 뒤집히는가")
        caps = dict(re.findall(r"^(_[A-Z_]*CAP)\s*=\s*(\d+)",
                               GATHERER.read_text(encoding="utf-8"), re.M))
        insn_cap = int(caps.get("_INSN_CAP", "0"))
        dec_cap = int(caps.get("_DEC_LINE_CAP", "0"))
        check(insn_cap > 0 and dec_cap > 0, f"캡 상수 읽힘 insn={insn_cap} dec={dec_cap}",
              str(caps))

        # 캡을 확실이 넘기는 함수를 **의도적으로** 만들어요.
        #   ⚠ 시행착오로 배운 것: 산술 연쇄(`x = x*3+i;` 1500개)나 `volatile` 누산은
        #     Ghidra 디컴파일러가 **하나의 거대 중첩 표현식으로 접어요**(10,276자지만
        #     112줄뿐) → dec 캡(120줄)을 못 넘기고 `decompile_truncated=False` 가
        #     나오는데, 그건 **플래그가 맞고 specimen 이 틀린** 경우였어요.
        #     `if` 연쇄는 표현식으로 접히지 않으므로 줄 수가 실제로 늘어요.
        branches = "\n".join(f"  if (x == {i}) return {i * 10};" for i in range(1, 201))
        big_src = ("int smallfn(int x){ return x ^ 0x5a; }\n\n"
                   "int bigfn(int x){\n" + branches + "\n  return 0;\n}\n")
        facts_big = _collect(work, "big.c", big_src, "-O0", "big.o")
        if not facts_big:
            check(False, "캡 초과 specimen 채집", "채집 실패")
        else:
            by = {f["name"]: f for f in facts_big.get("functions", [])}
            big = by.get("bigfn")
            small = by.get("smallfn")
            check(big is not None, "bigfn 채집됨", str(sorted(by)))
            if big:
                n_ins = len(big.get("insns", []))
                n_dec = len((big.get("decompile") or "").split("\n"))
                check(big.get("insns_complete") is False,
                      f"bigfn: insns_complete=False (명령 {n_ins}개, 캡 {insn_cap})",
                      f"값={big.get('insns_complete')}")
                check(big.get("decompile_truncated") is True,
                      f"bigfn: decompile_truncated=True (C {n_dec}줄, 캡 {dec_cap})",
                      f"값={big.get('decompile_truncated')}")
                # 플래그가 **정확히** 캡과 일치해야 해요(대충 True 가 아니라)
                check(n_ins == insn_cap,
                      f"잘린 명령 수가 캡과 정확히 일치 ({n_ins} == {insn_cap})",
                      f"n_ins={n_ins}")
                check(n_dec == dec_cap,
                      f"잘린 C 줄 수가 캡과 정확히 일치 ({n_dec} == {dec_cap})",
                      f"n_dec={n_dec}")
            if small:
                check(small.get("insns_complete") is True
                      and small.get("decompile_truncated") is False,
                      "smallfn: 캡 미달 → complete=True/truncated=False (과잉 보고 금지)",
                      f"{small.get('insns_complete')}/{small.get('decompile_truncated')}")

        # ── D) 프로젝트 캐시 staleness — 같은 경로·다른 내용 → 새 분석이어야 해요 ──
        print("\n[D] 캐시 staleness — 같은 경로에 다른 바이너리면 침묵 재사용 금지")
        f1 = _collect(work, "same.c", "int onlyA(int x){ return x ^ 0x5a; }\n",
                      "-O0", "same.o")
        f2 = _collect(work, "same.c", "int onlyB(int x){ return x * 3 + 1; }\n",
                      "-O0", "same.o")
        if not (f1 and f2):
            check(False, "두 변형 채집", "채집 실패")
        else:
            n1 = {q["name"] for q in f1.get("functions", [])}
            n2 = {q["name"] for q in f2.get("functions", [])}
            check("onlyA" in n1 and "onlyB" not in n1, f"변형1 은 onlyA 만({sorted(n1)})",
                  str(sorted(n1)))
            check("onlyB" in n2 and "onlyA" not in n2,
                  "같은 경로에 덮어쓴 변형2 는 onlyB 만 — **이전 분석 재사용 안 함**",
                  str(sorted(n2)))
            check(f1.get("source_sha256") != f2.get("source_sha256"),
                  "source_sha256 가 두 변형에서 다름(출처 기록 작동)",
                  f"{f1.get('source_sha256')} vs {f2.get('source_sha256')}")
            # 기록된 해시가 **실제 파일**과 일치하는지(거짓 출처 기록 금지)
            import hashlib
            opath = work / "same.o"
            real = hashlib.sha256(opath.read_bytes()).hexdigest()
            check(f2.get("source_sha256") == real,
                  "기록된 source_sha256 == 실제 파일 해시(출처 진실성)",
                  f"{f2.get('source_sha256')} vs {real}")
            check(f2.get("project_key") and real[:16] in str(f2.get("project_key")),
                  f"project_key 가 내용 해시로 파생됨({f2.get('project_key')})",
                  str(f2.get("project_key")))
            check(f2.get("insn_cap") == 64 and f2.get("dec_line_cap") == 120,
                  "facts 가 적용된 캡을 스스로 기록(데이터 자기기술)",
                  f"{f2.get('insn_cap')}/{f2.get('dec_line_cap')}")

        # ── C) 캡 미달 함수에서는 플래그가 조용해야 해요 ────────────────────
        print("\n[C] 캡 미달 함수 — 플래그 과잉 보고 금지")
        over = []
        for f in (facts_o0, facts_o2):
            if not f:
                continue
            for fn in f.get("functions", []):
                if fn.get("insns_complete") is not True:
                    over.append(f"{fn['name']}:insns_complete={fn.get('insns_complete')}")
                if fn.get("decompile_truncated") is not False:
                    over.append(f"{fn['name']}:dec_trunc={fn.get('decompile_truncated')}")
        check(not over, "작은 specimen 함수 전부 complete=True/truncated=False",
              ", ".join(over[:6]))
    finally:
        shutil.rmtree(work, ignore_errors=True)

    print("\n" + "=" * 72)
    if _FAIL:
        print(f"❌ LIVE GATHER VERIFY FAILED — {_PASS} passed / {_FAIL} failed")
        return 1
    print(f"✅ LIVE GATHER VERIFY PASSED — {_PASS} passed / 0 failed")
    print("   ⑤ 캡·완전성 플래그가 **실제 Ghidra 채집**에서 올바르게 뒤집힘을 증명.")
    print("   ③ N3 픽스처(classify 포함)가 **실제 Ghidra 출력과 일치**함을 증명.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
