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
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

CODE_CATEGORY = "역공학·분석결과"

# Windows 인지 — venv 인터프리터(Scripts\python.exe vs bin/python), JDK bin PATH
# 구분자(; vs :), Ghidra decompiler os 폴더·실행파일, analyzeHeadless.bat 가
# 플랫폼마다 달라요.  기본(False)은 Linux/macOS = 현재 라이브 숙주 행동 그대로.
_IS_WIN = os.name == "nt"


def norm_symbol(s: str) -> str:
    """`PySys_Audit@@Base` / `printf@plt` / `foo+0x10` -> the plain name."""
    return re.sub(r"[@+].*$", "", str(s)).strip()


# ── backend discovery ────────────────────────────────────────────────────────
def ghidra_headless() -> Optional[Path]:
    """Where analyzeHeadless lives, if a distribution has been delivered."""
    cands: List[Path] = []
    _hl = "analyzeHeadless.bat" if _IS_WIN else "analyzeHeadless"
    env = os.environ.get("GHIDRA_HOME")
    if env:
        cands.append(Path(env) / "support" / _hl)
    cands += sorted((Path(tempfile.gettempdir()) / "ghidra_dist").glob(f"ghidra_*/support/{_hl}"))
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
        env["PATH"] = os.path.join(jh, "bin") + os.pathsep + env.get("PATH", "")
    return env


def health() -> Dict[str, Any]:
    """정직한 자가 점검 — Ghidra 사슬의 각 고리를 지금 실제로 검증해요.

    조용한 가정 금지: 각 부품이 ✓/✗ 와 이유를 보고해서, 두뇌가 지금
    실제로 가진 능력만을 주장하게 해요.  경로 존재 여부(available_backends)
    와 달리 여기서는 subprocess 로 진짜 임포트·glibc 호환까지 봐요.
    """
    out: Dict[str, Any] = {}
    tools_dir = Path(__file__).resolve().parent.parent / "tools"
    _boot = "fetch_ghidra_dist.ps1" if _IS_WIN else "fetch_ghidra_dist.sh"
    headless = ghidra_headless()
    out["dist"] = {"ok": bool(headless),
                   "detail": str(headless) if headless else f"dist 없음 — tools/{_boot} 실행 필요"}
    if headless:
        _os_dir = "win_x86_64" if _IS_WIN else "linux_x86_64"
        _dec = "decompile.exe" if _IS_WIN else "decompile"
        decomp = headless.parent.parent / "Ghidra" / "Features" / "Decompiler" / "os" / _os_dir / _dec
        if decomp.exists():
            if _IS_WIN:
                # Windows 에 ldd/glibc 가 없어요 — 네이티브 decompile.exe 존재로 만족.
                out["decompiler"] = {"ok": True,
                                     "detail": "네이티브 decompile.exe — Windows (ldd/glibc 점검 대상 아님)"}
            else:
                try:
                    ldd = subprocess.run(["ldd", str(decomp)], capture_output=True,
                                         text=True, timeout=30, check=False)
                    missing = [ln.strip() for ln in ldd.stdout.splitlines() if "not found" in ln]
                    out["decompiler"] = {"ok": not missing,
                                         "detail": "네이티브 decompile — 이 숙주 glibc 와 호환" if not missing
                                         else f"재주조 필요(fetch 스크립트가 자동): {missing[0][:90]}"}
                except Exception as exc:  # ldd itself missing etc.
                    out["decompiler"] = {"ok": False, "detail": f"점검 불가: {exc}"}
        else:
            out["decompiler"] = {"ok": False, "detail": "decompile 바이너리가 dist 에 없음"}
    else:
        out["decompiler"] = {"ok": False, "detail": "dist 없음"}
    py = ghidra_python()
    out["pyghidra_python"] = {"ok": bool(py),
                              "detail": str(py) if py else "PyGhidra 인터프리터 없음 (GHIDRA_PYTHON 또는 jdkenv venv)"}
    if py:
        try:
            probe = subprocess.run(
                [str(py), "-c", "import jdk4py, pyghidra; print(jdk4py.JAVA_HOME)"],
                capture_output=True, text=True, timeout=180, check=False)
            ok = probe.returncode == 0 and bool(probe.stdout.strip())
            out["jvm_and_bridge"] = {
                "ok": ok,
                "detail": (f"JVM(JRE) = {probe.stdout.strip()[:100]} · pyghidra 임포트 성공"
                           if ok else f"프로브 실패: {((probe.stderr or '').strip()[-200:])}")}
        except Exception as exc:
            out["jvm_and_bridge"] = {"ok": False, "detail": f"프로브 예외: {exc}"}
    else:
        out["jvm_and_bridge"] = {"ok": False, "detail": "인터프리터 없음"}
    vendor = Path(__file__).resolve().parent.parent / "vendor"
    wheels = sorted(q.name for q in vendor.glob("*.whl")) if vendor.exists() else []
    _plat = "win_amd64·cp311" if _IS_WIN else "linux x86_64·cp311"
    out["vendor_wheels"] = {
        "ok": any(w.startswith("jdk4py") for w in wheels) and any(w.startswith("pyghidra") for w in wheels),
        "detail": (f"{len(wheels)}개 휠을 저장소가 소유 — 오프라인 재구성 가능 ({_plat} + py3-none-any)"
                   if wheels else "vendor 없음 — 재구성에 PyPI 연결 필요")}
    tools = ["ghidra_facts_pyghidra.py", "verify_ghidra_facts.py", _boot]
    miss = [t for t in tools if not (tools_dir / t).exists()]
    out["tools"] = {"ok": not miss,
                    "detail": "팩트 추출·검증·배달 스크립트 모두 존재" if not miss else f"빠진 도구: {miss}"}
    out["all_ok"] = all(v.get("ok") for k, v in out.items() if isinstance(v, dict))
    return out


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
        # 정직한 라우팅: Ghidra 는 형식(ELF/PE)이 있어야 읽어요.  헤더 없는
        # raw 바이트는 Ghidra 가 짐작할 수 없으니(거짓 언어를 발명하지 않아요)
        # objdump 채널로 보내고, 노트 tags 에 백엔드가 사실대로 기록돼요.
        with binary.open("rb") as fh:
            magic = fh.read(4)
        formatted = magic.startswith(b"\x7fELF") or magic.startswith(b"MZ")
        backend = ("analyzeHeadless"
                   if formatted and ghidra_headless() and ghidra_python()
                   else "objdump")

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
    _venv = Path(tempfile.gettempdir()) / "jdkenv"
    cands += [_venv / "Scripts" / "python.exe"] if _IS_WIN else [_venv / "bin" / "python"]
    for c in cands:
        if c.exists():
            return c
    return None


def _analyze_ghidra(binary: Path, cap: int, project_dir: Optional[Path]) -> Dict[str, Any]:
    """The real Ghidra path — identical note shape, richer facts (decompile)."""
    headless = ghidra_headless()
    assert headless, "Ghidra dist 가 없어요 (fetch_ghidra_dist 스크립트 먼저)"
    py = ghidra_python()
    assert py, "PyGhidra 인터프리터가 없어요 (GHIDRA_PYTHON 또는 jdkenv venv)"
    tool = Path(__file__).resolve().parent.parent / "tools" / "ghidra_facts_pyghidra.py"
    out_json = Path(tempfile.gettempdir()) / "brain_facts.json"
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
