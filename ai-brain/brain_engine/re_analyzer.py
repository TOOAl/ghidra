"""⚙️ Stage L — the reverse-engineering channel: real machine truth, two backends.

WHY THIS MODULE EXISTS
    The brain's machine memories must come from a disassembler, never from
    imagination.  Two backends produce the SAME note shape:

      objdump         always available (binutils), used right now
      analyzeHeadless the real Ghidra, used the moment a distribution exists
                      (see ai-brain/tools/fetch_ghidra_dist.sh; the sandbox
                      cannot download release assets, only committed content)

    Switching backends changes nothing downstream: notes carry `kind: code`,
    so CorpusChannels trains them in their OWN vocabulary budget — measured,
    sharing one budget with prose evicts 175 discriminative prose words and
    blinds the blind-spot detector.

WHY COSINE IS NOT USED INSIDE THIS CHANNEL
    Measured against the call graph objdump prints (/tmp/l_probe/code_thr2.py,
    1912 real functions, 18252 real call edges): call-connected pairs cos
    median 0.796 vs UNRELATED pairs 0.591 — overlapping distributions, every
    threshold admits 70-99% intruders.  Machine code is mostly the same
    mnemonics, so similarity there is theater.  The GRAPH is exact truth, and
    `CorpusChannels.code_orphans` states gaps structurally.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

CODE_CATEGORY = "역공학·분석결과"


def norm_symbol(s: str) -> str:
    """`PySys_Audit@@Base` / `printf@plt` / `foo+0x10` -> the plain name."""
    return re.sub(r"[@+].*$", "", str(s)).strip()


# ── backend discovery ────────────────────────────────────────────────────────
def ghidra_headless() -> Optional[Path]:
    """Where analyzeHeadless lives, if a distribution has been delivered."""
    cands: List[Path] = []
    env = os.environ.get("GHIDRA_HOME")
    if env:
        cands.append(Path(env) / "support" / "analyzeHeadless")
    cands += sorted(Path("/tmp/ghidra_dist").glob("ghidra_*/support/analyzeHeadless"))
    for c in cands:
        if c.exists():
            return c
    return None


def _java_env() -> Dict[str, str]:
    """JAVA_HOME for PyGhidra — asked from the interpreter that has it.

    Ghidra 12 speaks Python only through PyGhidra, which needs a real JDK
    home.  The server process runs on system python (no jdk4py module), so
    when the import fails we ask the PyGhidra interpreter itself where its
    bundled JDK lives.
    """
    env = dict(os.environ)
    jh = ""
    try:
        import jdk4py  # type: ignore

        jh = str(jdk4py.JAVA_HOME)
    except Exception:
        py = ghidra_python()
        if py:
            try:
                probe = subprocess.run(
                    [str(py), "-c", "import jdk4py;print(jdk4py.JAVA_HOME)"],
                    capture_output=True, text=True, timeout=60, check=False,
                )
                jh = probe.stdout.strip()
            except Exception:
                jh = ""
    if jh:
        env["JAVA_HOME"] = jh
        env["PATH"] = f"{jh}/bin:" + env.get("PATH", "")
    return env


def available_backends() -> List[str]:
    out = ["objdump"]
    if ghidra_headless() and ghidra_python():
        out.append("analyzeHeadless")
    return out


# ── objdump backend (real bytes in, real instructions out) ───────────────────
def parse_objdump(binary: Path, cap: int = 400) -> List[Dict[str, Any]]:
    proc = subprocess.run(
        ["objdump", "-d", "--no-show-raw-insn", str(binary)],
        capture_output=True, text=True, timeout=600,
    )
    funcs: List[Dict[str, Any]] = []
    cur: List[str] = []
    name = addr = ""
    for ln in proc.stdout.splitlines():
        m = re.match(r"^([0-9a-f]+) <(.+)>:$", ln.strip())
        if m:
            if name and len(cur) >= 3:
                funcs.append({"name": norm_symbol(name), "addr": addr, "insns": cur})
            if len(funcs) >= cap:
                break
            name, addr, cur = norm_symbol(m.group(2)), m.group(1), []
        elif name and re.match(r"^\s+[0-9a-f]+:\t", ln):
            cur.append(ln.strip())
    if name and len(cur) >= 3 and len(funcs) < cap:
        funcs.append({"name": norm_symbol(name), "addr": addr, "insns": cur})
    return funcs


def _calls_of(insns: Sequence[str], known: Set[str]) -> List[str]:
    out: List[str] = []
    for ln in insns:
        m = re.search(r"\bcall\w*\s+(?:[0-9a-f]+|0x[0-9a-f]+)\s+<([^>]+)>", ln)
        if m:
            t = norm_symbol(m.group(1))
            if t and t not in out:
                out.append(t)
    return out


def analyze(binary: Path, backend: str = "auto", cap: int = 400,
            project_dir: Optional[Path] = None) -> Dict[str, Any]:
    """Run one backend over one real binary and return uniform facts."""
    binary = Path(binary)
    if not binary.exists():
        raise FileNotFoundError(f"바이너리가 없어요: {binary}")
    if backend == "auto":
        backend = "analyzeHeadless" if ghidra_headless() else "objdump"

    if backend == "analyzeHeadless":
        return _analyze_ghidra(binary, cap, project_dir)

    funcs = parse_objdump(binary, cap=cap)
    known = {f["name"] for f in funcs}
    for f in funcs:
        f["calls"] = _calls_of(f["insns"], known)
        f["refs"] = sorted({norm_symbol(t) for t in re.findall(r"<([^>]+)>", "\n".join(f["insns"]))})
        f["mnemonics"] = sorted({i.split("\t")[-1].split()[0] for i in f["insns"]})
    return {"backend": "objdump", "binary": binary.name, "functions": funcs}


def ghidra_python() -> Optional[Path]:
    """The interpreter that has PyGhidra — the only Python Ghidra 12 speaks.

    Ghidra 12 dropped Jython, and a .java postScript needs a compiler the
    allow-list cannot supply (jdk4py ships no jdk.compiler), so the dist is
    driven in-process through PyGhidra: same analyzers, same decompiler.
    """
    cands = [Path(os.environ.get("GHIDRA_PYTHON", ""))] if os.environ.get("GHIDRA_PYTHON") else []
    cands += [Path("/tmp/jdkenv/bin/python")]
    for c in cands:
        if c.exists():
            return c
    return None


def _analyze_ghidra(binary: Path, cap: int, project_dir: Optional[Path]) -> Dict[str, Any]:
    """The real Ghidra path — identical note shape, richer facts (decompile)."""
    headless = ghidra_headless()
    assert headless, "Ghidra dist 가 없어요 (fetch_ghidra_dist.sh 먼저)"
    py = ghidra_python()
    assert py, "PyGhidra 인터프리터가 없어요 (GHIDRA_PYTHON 또는 /tmp/jdkenv)"
    tool = Path(__file__).resolve().parent.parent / "tools" / "ghidra_facts_pyghidra.py"
    out_json = Path("/tmp/brain_facts.json")
    if out_json.exists():
        out_json.unlink()
    env = _java_env()
    env["GHIDRA_INSTALL_DIR"] = str(headless.parent.parent)
    proc = subprocess.run(
        [str(py), str(tool), str(binary), str(out_json), str(cap)],
        capture_output=True, text=True, timeout=1800, check=False, env=env,
    )
    if not out_json.exists():
        tail = ((proc.stderr or "") + (proc.stdout or "")).strip()[-600:]
        raise RuntimeError(f"Ghidra 가 사실 파일을 내놓지 않았어요: {tail}")
    raw = json.loads(out_json.read_text(encoding="utf-8"))
    return {"backend": "analyzeHeadless", "binary": binary.name,
            "functions": raw.get("functions", [])[:cap]}


# ── facts -> memories ────────────────────────────────────────────────────────
def build_notes(facts: Dict[str, Any]) -> List[Dict[str, Any]]:
    bn = facts["binary"]
    notes: List[Dict[str, Any]] = []
    for f in facts["functions"]:
        insns = f.get("insns") or []
        calls = f.get("calls") or []
        refs = f.get("refs") or []
        mn = f.get("mnemonics") or sorted({i.split("\t")[-1].split()[0] for i in insns})
        body = "\n".join(f"  {i}" for i in insns[:16])
        if calls:
            body += "\n호출: " + " ".join(calls[:10])
        if refs:
            body += "\n참조: " + " ".join(refs[:10])
        dec = f.get("decompile")
        if dec:
            body += "\n디컴파일:\n" + "\n".join(dec.splitlines()[:24])
        notes.append({
            "kind": "code",
            "slug": f"re-{bn}-{f['name']}-{f.get('addr', '0')}",
            "title": f"{f['name']} (0x{f.get('addr', '0')})",
            "category": CODE_CATEGORY,
            "tags": ["machine-output", facts["backend"], bn],
            "summary": (f"{bn} 의 {f['name']}: 명령 {len(insns)}개"
                        + (f", 호출 {len(calls)}개" if calls else "")
                        + f", 니모닉 {' '.join(mn[:8])}"),
            "body": body,
            "links": [],
        })
    return notes


def write_code_notes(vault_dir: Path, notes: Sequence[Dict[str, Any]]) -> List[Path]:
    """Land machine memories as vault files that say `kind: code` in front matter."""
    dest = Path(vault_dir) / "30_Ghidra"
    dest.mkdir(parents=True, exist_ok=True)
    written: List[Path] = []
    for n in notes:
        safe = re.sub(r"[^\w가-힣.-]", "_", n["slug"])[:90]
        p = dest / f"{safe}.md"
        tags = ", ".join(n["tags"])
        p.write_text(
            "---\n"
            f'title: "{n["title"]}"\n'
            f'category: "{n["category"]}"\n'
            f"tags: [{tags}]\n"
            'kind: "code"\n'
            f'created: "{n.get("created", "")}"\n'
            "---\n\n"
            f"# {n['title']}\n\n"
            f"## 💡 핵심 요약\n{n['summary']}\n\n"
            f"## 🔩 기계어 진실\n{n['body']}\n",
            encoding="utf-8",
        )
        written.append(p)
    return written


def call_edges(notes: Sequence[Dict[str, Any]]) -> Set[Tuple[str, str]]:
    """Exact truth of this channel: who calls whom, as printed by the backend."""
    names = {re.sub(r"\s*\(0x[0-9a-f]+\)\s*$", "", n["title"]).strip() for n in notes}
    edges: Set[Tuple[str, str]] = set()
    for n in notes:
        caller = re.sub(r"\s*\(0x[0-9a-f]+\)\s*$", "", n["title"]).strip()
        for ln in str(n.get("body") or "").splitlines():
            if ln.startswith("호출:"):
                for t in ln.split(":")[1].split():
                    if t in names and t != caller:
                        edges.add((caller, t))
    return edges
