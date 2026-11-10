"""⚙️ Stage L — drive the REAL Ghidra in-process (PyGhidra) and dump brain facts.

WHY NOT `analyzeHeadless -postScript`
  Two measured walls in this sandbox:
    * Ghidra 12 dropped Jython — a .py postScript dies with "Ghidra was not
      started with PyGhidra. Python is not available".
    * a .java postScript must be compiled at runtime, and the only JDK on the
      allow-list (PyPI jdk4py) ships no jdk.compiler module, so Ghidra's
      LaunchSupport rejects the home and there is no TTY to prompt.
  PyGhidra (also on PyPI, also allowed) starts the very same distribution
  through JPype and speaks the full program API from Python — same analyzers,
  same decompiler, same truths, no compiler involved.

Usage:  python ghidra_facts_pyghidra.py <binary> <out.json> [cap]
Env:    GHIDRA_INSTALL_DIR, JAVA_HOME
"""
from __future__ import annotations

import json
import sys
import warnings

warnings.filterwarnings("ignore")


def main() -> int:
    binary, out = sys.argv[1], sys.argv[2]
    cap = int(sys.argv[3]) if len(sys.argv) > 3 else 400

    import os

    import pyghidra

    # LaunchSupport insists on a full JDK; jdk4py is an honest JRE and we
    # never compile Java here, so when JAVA_HOME is known we hand it to the
    # launcher directly (its setter skips the probe) instead of faking a
    # javac.  Without JAVA_HOME, fall back to PyGhidra's own discovery.
    java_home = os.environ.get("JAVA_HOME", "")
    if java_home and os.path.isdir(java_home):
        from pathlib import Path

        from pyghidra.launcher import HeadlessPyGhidraLauncher

        launcher = HeadlessPyGhidraLauncher()
        launcher.java_home = Path(java_home)
        launcher.start()
    else:
        pyghidra.start()
    from ghidra.app.decompiler import DecompInterface

    facts = {"backend": "analyzeHeadless", "binary": binary.rsplit("/", 1)[-1], "functions": []}
    with pyghidra.open_program(binary, project_location="/tmp/ghidra_pyproj", analyze=True) as flat:
        program = flat.getCurrentProgram()
        fm = program.getFunctionManager()
        listing = program.getListing()
        refs_mgr = program.getReferenceManager()
        symtab = program.getSymbolTable()
        decomp = DecompInterface()
        if not decomp.openProgram(program):
            decomp = None
        for f in fm.getFunctions(True):
            if len(facts["functions"]) >= cap:
                break
            if f.isThunk() or f.isExternal():
                continue
            insns, mnem, calls, refnames = [], [], [], []
            instr = listing.getInstructionAt(f.getEntryPoint())
            guard = 0
            while instr is not None and f.getBody().contains(instr.getMinAddress()) and guard < 16:
                # 전체 피연산자까지 — 첫 피연산자만 적던 버그(XOR AL) 를 고쳐요.
                # 에뮬레이터·노트 모두 완전한 명령 텍스트가 필요해요.
                insns.append("%s:\t%s" % (instr.getMinAddress(), instr.toString()))
                m = instr.getMnemonicString()
                if m not in mnem:
                    mnem.append(m)
                for r in refs_mgr.getReferencesFrom(instr.getMinAddress()):
                    to = r.getToAddress()
                    tgt = fm.getFunctionContaining(to)
                    nm = tgt.getName() if tgt is not None else None
                    if nm is None:
                        ps = symtab.getPrimarySymbol(to)
                        nm = ps.getName() if ps is not None else None
                    if nm is not None:
                        if nm not in refnames:
                            refnames.append(nm)
                        ft = r.getReferenceType()
                        if ft is not None and ft.isCall() and nm != f.getName() and nm not in calls:
                            calls.append(nm)
                instr = instr.getNext()
                guard += 1
            if len(insns) < 3:
                continue
            dec = ""
            if decomp is not None:
                try:
                    dr = decomp.decompileFunction(f, 20, None)
                    if dr is not None and dr.decompileCompleted() and dr.getDecompiledFunction() is not None:
                        c = dr.getDecompiledFunction().getC()
                        if c:
                            dec = "\n".join(c.split("\n")[:24])
                except Exception:
                    dec = ""
            facts["functions"].append({
                "name": f.getName(), "addr": str(f.getEntryPoint()), "insns": insns,
                "mnemonics": mnem, "calls": calls, "refs": refnames, "decompile": dec,
            })
        if decomp is not None:
            decomp.dispose()
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(facts, fh, ensure_ascii=False)
    print("✅ PyGhidra facts: %d functions -> %s" % (len(facts["functions"]), out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
