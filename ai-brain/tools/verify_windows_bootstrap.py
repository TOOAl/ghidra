#!/usr/bin/env python3
"""🪟 Windows 부트스트랩 정적·알고리즘 검증 게이트 (fetch_ghidra_dist.ps1).

왜 이 도구가 있나
    부채①(Windows 오프라인 이식성)을 닫으며 tools/fetch_ghidra_dist.ps1 를 썼지만
    이 Linux 샌드박스엔 실제 Windows 호스트도 pwsh 도 없어요 — PowerShell 릴리스는
    allow-list 밖 호스트(objects.githubusercontent.com)로 리다이렉트되어 바이너리를
    받을 수 없고, PyPI 에 PowerShell 파서도 없어요.  그래서 "눈으로 봤다" 대신
    **돌릴 수 있는 것은 실제로 돌려** 기계 증거로 남기고, 못 돌리는 것(실 Windows
    실행)은 정직하게 범위를 명시해요.  자가완결·네트워크 없음·exit-code 게이트.

증명하는 것 (재생산 가능):
  1) 오프라인 설치 가능성 — vendor 휠 태그(PEP425) + 의존 그래프(METADATA) 를
     풀어, Windows/cp311 타깃에서 `pip --no-index --find-links vendor jdk4py
     pyghidra jpype1` 의 의존 폐포가 전부 호환 휠 + 버전 제약으로 만족됨을 증명.
     Linux/cp311 도 함께(양 플랫폼 오프라인).  ← 부채① 의 핵심 주장.
  2) 이진 청크 재조립 알고리즘 — .ps1 가 쓰는 "이름순 정렬 + 바이너리 연결 +
     SHA256" 을 합성 픽스처(0바이트 포함)로 실제 실행해 비트복원·체크섬 일치 증명.
  3) .ps1 구조 불변식 — $env:TEMP(하드코딩 /tmp 0·홈경로 리터럴 0)·venv
     Scripts\\python.exe·analyzeHeadless.bat·--no-index 오프라인+PyPI 정직 폴백·
     Get-FileHash SHA256 체크섬·FileStream 이진 재조립(Get-Content -Raw 아님)·
     facts+verify 호출·$ErrorActionPreference=Stop·$LASTEXITCODE 검사+exit(조용한
     통과 없음)·중괄호/괄호 균형·외부 URL = allow-list 무료 호스트뿐.
  4) .ps1 ↔ .sh 단계 패리티 — Windows 미러가 증명된 Linux 원본의 모든 논리 단계를
     빠짐없이 덮음(배달→재조립→체크섬→전개→venv→오프라인설치→폴백→JAVA_HOME→
     GHIDRA_INSTALL_DIR→facts→verify).
  5) .bat 래퍼 + start_windows.bat 일관성 — Bypass 로 .ps1 호출·exitcode 전파·CRLF·
     사전점검이 .ps1 와 같은 venv 경로(%TEMP%\\jdkenv\\Scripts\\python.exe).

정직하게 증명하지 못하는 것 (부채원장 잔여로 기록):
  · 실제 Windows 호스트에서 .ps1 end-to-end 실행 — 호스트 없음·pwsh 불가.
    첫 Windows 실행이 마지막 미목격 단계로 남아요.
  · PowerShell 구문 트리 파싱 — 파서 없음. 구조 불변식+균형 검사로 대리.
"""
from __future__ import annotations

import hashlib
import random
import re
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Dict, List, Set, Tuple

HERE = Path(__file__).resolve().parent
BRAIN = HERE.parent
VENDOR = BRAIN / "vendor"
TOOLS = BRAIN / "tools"
PS1 = TOOLS / "fetch_ghidra_dist.ps1"
BAT = TOOLS / "fetch_ghidra_dist.bat"
SH = TOOLS / "fetch_ghidra_dist.sh"
START_BAT = BRAIN / "start_windows.bat"

PASS = FAIL = 0
FAILURES: List[str] = []


def check(cond: bool, label: str, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ✅ {label}")
    else:
        FAIL += 1
        FAILURES.append(label)
        print(f"  ❌ {label} — {detail}")


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _strip_ps(t: str) -> str:
    """주석(<# #>·#…)과 문자열 리터럴을 걷어낸 '코드' 근사.

    경로(/tmp)·구분자(괄호) 검사는 문서 주석이나 문자열 내용이 아니라 **실제
    코드**에 대해서만 해야 정확해요 — 예: '.ps1 주석에 "/tmp 대신 $env:TEMP"
    라는 설명'은 하드코딩 /tmp 가 아니죠.  PowerShell 전체 파서는 없으니
    (샌드박스에 pwsh 불가) 문자열/주석을 접어 코드 뼈대만 남기는 가벼운 스트리퍼.
    """
    t = re.sub(r"<#.*?#>", "", t, flags=re.DOTALL)            # 블록 주석 제거
    out: List[str] = []
    for line in t.splitlines():
        line = re.sub(r'"(?:[^"`]|`.|"")*"', '""', line)       # 이중인용 문자열 → ""
        line = re.sub(r"'(?:[^']|'')*'", "''", line)           # 단일인용 문자열 → ''
        i = line.find("#")                                     # 행 주석(문자열 접은 뒤)
        if i >= 0:
            line = line[:i]
        out.append(line)
    return "\n".join(out)


# ── 휠 태그 / 의존 헬퍼 (PEP 425 태그 · PEP 503 정규화) ─────────────────────
def _norm(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def parse_wheel(fn: str) -> Tuple[str, str, str, str, str]:
    b = fn[:-4] if fn.endswith(".whl") else fn
    parts = b.split("-")
    return _norm(parts[0]), parts[1], parts[-3], parts[-2], parts[-1]


def tag_compatible(pytag: str, abitag: str, plattag: str, target: Dict[str, Set[str]]) -> bool:
    return bool((set(pytag.split(".")) & target["py"])
                and (set(abitag.split(".")) & target["abi"])
                and (set(plattag.split(".")) & target["plat"]))


def _vt(v: str) -> Tuple[int, ...]:
    return tuple(int(x) for x in re.findall(r"\d+", v)[:4])


def _spec_ok(ver: str, spec: str) -> bool:
    """최소 버전제약 검사(>=,<=,>,<,==,!=,~=) — 자가완결, 외부 packaging 불필요."""
    if not spec:
        return True
    for clause in [c.strip() for c in spec.split(",") if c.strip()]:
        m = re.match(r"(~=|==|!=|>=|<=|>|<)\s*v?([0-9][0-9.]*)", clause)
        if not m:
            continue
        op, val = m.group(1), m.group(2)
        vv, sv = _vt(ver), _vt(val)
        n = max(len(vv), len(sv))
        vv = vv + (0,) * (n - len(vv))
        sv = sv + (0,) * (n - len(sv))
        if op == ">=" and not vv >= sv:
            return False
        if op == "<=" and not vv <= sv:
            return False
        if op == ">" and not vv > sv:
            return False
        if op == "<" and not vv < sv:
            return False
        if op == "==" and not vv == sv:
            return False
        if op == "!=" and vv == sv:
            return False
        if op == "~=":
            if not vv >= sv:
                return False
            prefix = max(1, len(_vt(val)) - 1)
            if vv[:prefix] != sv[:prefix]:
                return False
    return True


def requires_of(wheel: Path) -> List[Tuple[str, str]]:
    """METADATA 의 Requires-Dist — extra 마커(선택 의존)는 기본설치 아니므로 제외."""
    out: List[Tuple[str, str]] = []
    try:
        z = zipfile.ZipFile(wheel)
        meta = [n for n in z.namelist() if n.endswith("METADATA")]
        if not meta:
            return out
        for line in z.read(meta[0]).decode("utf-8", "ignore").splitlines():
            if not line.startswith("Requires-Dist:"):
                continue
            rd = line.split(":", 1)[1].strip()
            if "extra ==" in rd or "extra==" in rd:
                continue
            m = re.match(r"([A-Za-z0-9._-]+)\s*(.*)", rd)
            if m:
                spec = m.group(2).strip()
                if spec.startswith("(") and spec.endswith(")"):
                    spec = spec[1:-1].strip()
                out.append((m.group(1), spec))
    except (OSError, zipfile.BadZipFile):
        pass
    return out


# ── 1) 오프라인 설치 가능성 ─────────────────────────────────────────────────
def audit_offline_install() -> None:
    print("── 1) 오프라인 설치 가능성 (vendor 휠 태그 + 의존 폐포) ──")
    wheels = sorted(VENDOR.glob("*.whl")) if VENDOR.exists() else []
    check(bool(wheels), "vendor 에 휠 존재", str(VENDOR))
    idx: Dict[str, List[Tuple[str, str, str, str, Path]]] = {}
    for w in wheels:
        name, ver, py, abi, plat = parse_wheel(w.name)
        idx.setdefault(name, []).append((ver, py, abi, plat, w))

    targets = {
        "Windows/cp311": {"py": {"cp311", "py3", "py311"},
                          "abi": {"cp311", "none"},
                          "plat": {"win_amd64", "any"}},
        "Linux/cp311": {"py": {"cp311", "py3", "py311"},
                        "abi": {"cp311", "none"},
                        "plat": {"manylinux_2_17_x86_64", "manylinux_2_24_x86_64",
                                 "manylinux_2_28_x86_64", "manylinux2014_x86_64",
                                 "linux_x86_64", "any"}},
    }
    roots = ["jdk4py", "pyghidra", "jpype1"]  # .ps1/.sh 가 설치하는 최상위 패키지

    for tname, target in targets.items():
        need = [_norm(r) for r in roots]
        seen: Set[str] = set()
        specs: Dict[str, List[str]] = {}
        missing: List[str] = []
        incompatible: List[str] = []
        while need:
            pkg = need.pop()
            if pkg in seen:
                continue
            seen.add(pkg)
            cands = idx.get(pkg, [])
            if not cands:
                missing.append(pkg)
                continue
            comp = [c for c in cands if tag_compatible(c[1], c[2], c[3], target)]
            if not comp:
                incompatible.append(f"{pkg}(휠 {len(cands)}개 있으나 타깃 비호환)")
                continue
            for dep, spec in requires_of(comp[0][4]):
                dn = _norm(dep)
                if spec:
                    specs.setdefault(dn, []).append(spec)
                if dn not in seen:
                    need.append(dn)
        specfail = []
        for pkg, splist in specs.items():
            comp = [c for c in idx.get(pkg, []) if tag_compatible(c[1], c[2], c[3], target)]
            if not comp or not any(all(_spec_ok(c[0], s) for s in splist) for c in comp):
                vers = [c[0] for c in comp]
                specfail.append(f"{pkg}{splist} (후보 {vers})")
        check(not missing, f"[{tname}] 의존 폐포에 빠진 패키지 0 (오프라인 완전해결)", str(missing))
        check(not incompatible, f"[{tname}] 모든 의존이 호환 휠로 만족", str(incompatible))
        check(not specfail, f"[{tname}] 버전 제약(>=,!=,~=) 만족", str(specfail))


# ── 2) 이진 청크 재조립 알고리즘 ────────────────────────────────────────────
def audit_reassembly() -> None:
    print("── 2) 이진 청크 재조립 알고리즘 (.ps1 방식 실제 실행) ──")
    tmp = Path(tempfile.mkdtemp(prefix="wbtest_"))
    try:
        orig = bytes(random.getrandbits(8) for _ in range(300_000))  # 0바이트 포함 바이너리
        n = 7
        size = (len(orig) + n - 1) // n
        for i in range(n):
            (tmp / f"ghidra_headless.tgz.part{i:02d}").write_bytes(orig[i * size:(i + 1) * size])
        # .ps1: Get-ChildItem ... | Sort-Object Name  +  FileStream 바이너리 연결
        full = tmp / "ghidra_headless.tgz"
        with open(full, "wb") as out:
            for p in sorted(tmp.glob("ghidra_headless.tgz.part*"), key=lambda q: q.name):
                out.write(p.read_bytes())
        got = full.read_bytes()
        check(got == orig, "이진 재조립 비트일치 (0바이트 보존 — 텍스트모드 아님)",
              f"{len(got)} vs {len(orig)}")
        check(hashlib.sha256(got).digest() == hashlib.sha256(orig).digest(),
              "SHA256 체크섬 일치 (Get-FileHash 동치)")
        names = sorted(p.name for p in tmp.glob("ghidra_headless.tgz.part*"))
        check(names == [f"ghidra_headless.tgz.part{i:02d}" for i in range(n)],
              "이름순 정렬 = 분할순 (zero-pad → .sh cat part* 와 동일 어순)")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ── 3) .ps1 구조 불변식 ─────────────────────────────────────────────────────
def audit_ps1_structure() -> None:
    print("── 3) fetch_ghidra_dist.ps1 구조 불변식 ──")
    t = _read(PS1)
    check(PS1.exists() and bool(t), ".ps1 존재·비어있지 않음", str(PS1))
    low = t.lower()
    code = _strip_ps(t)          # 주석·문자열 접은 코드 뼈대
    low_code = code.lower()
    # 이식성 (경로 검사는 코드 기준 — 주석의 '/tmp 대신 $env:TEMP' 설명은 문서일 뿐)
    check("$env:temp" in low, "$env:TEMP 사용 (Windows temp)", "")
    check("/tmp" not in code, "코드에 하드코딩 /tmp 0 (주석 제외)", "")
    check("c:\\users" not in low, "Windows 홈경로 리터럴 0 (주석 포함 엄격)", "")
    check("scripts\\python.exe" in low, "venv Scripts\\python.exe (Windows 인터프리터)", "")
    check("analyzeheadless.bat" in low, "analyzeHeadless.bat (Windows 런처)", "")
    # 오프라인 우선 + 정직 폴백
    check("--no-index" in code and "--find-links" in code, "vendor 오프라인 설치(--no-index --find-links)", "")
    check(all(pkg in low for pkg in ("jdk4py", "pyghidra", "jpype1")), "세 최상위 패키지 설치", "")
    check("pypi" in low and "$lastexitcode" in low, "오프라인 실패 시 PyPI 정직 폴백($LASTEXITCODE 분기)", "")
    # 무결성
    check("get-filehash" in low and "sha256" in low, "Get-FileHash SHA256 체크섬", "")
    check("sha256sums.txt" in low, "SHA256SUMS.txt 와 대조", "")
    check("[system.io.file]" in low, "FileStream 이진 재조립", "")
    check("get-content -raw" not in low_code, "코드에 바이너리 깨는 Get-Content -Raw 미사용", "")
    check("ghidra_facts_pyghidra.py" in t and "verify_ghidra_facts.py" in t, "facts 추출 + verify 호출", "")
    # 조용한 통과 없음
    check("$erroractionpreference" in low and '"stop"' in low, "$ErrorActionPreference = Stop", "")
    exits = re.findall(r"\bexit\s+\d+", code)
    check("$lastexitcode" in low and len(exits) >= 4,
          f"$LASTEXITCODE 검사 + nonzero exit (조용한 통과 없음, exit {len(exits)}곳)", "")
    # 구조 균형 (코드 기준 — 문자열/주석 안 괄호는 PowerShell 문법과 무관)
    check(code.count("{") == code.count("}"), "코드 중괄호 균형",
          f"{{={code.count('{')} }}={code.count('}')}")
    check(code.count("(") == code.count(")"), "코드 괄호 균형",
          f"(={code.count('(')} )={code.count(')')}")
    check(re.search(r"(?m)^param\(", t) is not None, "param() 블록", "")
    # 외부 URL = allow-list 무료 호스트뿐 (스킴 리터럴 없이 :// 뒤 호스트만 추출)
    hosts = set(re.findall(r"://([A-Za-z0-9._-]+)", t))
    allowed = {"codeload.github.com", "github.com"}
    check(hosts and hosts <= allowed, f"외부 호스트 = 무료 allow-list 뿐 {sorted(hosts)}",
          str(sorted(hosts - allowed)))


# ── 4) .ps1 ↔ .sh 단계 패리티 ───────────────────────────────────────────────
def audit_parity() -> None:
    print("── 4) .ps1 ↔ .sh 논리 단계 패리티 (Windows 미러 = Linux 원본) ──")
    sh, ps = _read(SH), _read(PS1)
    check(bool(sh) and bool(ps), ".sh 와 .ps1 둘 다 존재", "")
    steps = [
        ("codeload 배달", ["codeload.github.com"]),
        ("청크 재조립", ["ghidra_headless.tgz.part"]),
        ("SHA256 체크섬", ["SHA256SUMS.txt"]),
        ("dist 전개(tar)", ["tar "]),
        ("jdkenv venv", ["jdkenv"]),
        ("오프라인 설치", ["--no-index", "--find-links"]),
        ("PyPI 폴백", ["PyPI", "폴백"]),
        ("JAVA_HOME(jdk4py)", ["JAVA_HOME", "jdk4py.JAVA_HOME"]),
        ("GHIDRA_INSTALL_DIR", ["GHIDRA_INSTALL_DIR"]),
        ("facts 추출", ["ghidra_facts_pyghidra.py"]),
        ("verify 검증", ["verify_ghidra_facts.py"]),
    ]
    for name, needles in steps:
        in_sh = any(n in sh for n in needles)
        in_ps = any(n.lower() in ps.lower() for n in needles)
        check(in_sh and in_ps, f"단계 '{name}' 을 .sh 와 .ps1 둘 다 커버",
              f"sh={in_sh} ps={in_ps}")


# ── 5) .bat 래퍼 + start_windows.bat 일관성 ─────────────────────────────────
def audit_bat_consistency() -> None:
    print("── 5) .bat 래퍼 + start_windows.bat 일관성 ──")
    wb = _read(BAT)
    check(BAT.exists() and bool(wb), ".bat 래퍼 존재", str(BAT))
    wbl = wb.lower()
    check("executionpolicy" in wbl and "bypass" in wbl, "ExecutionPolicy Bypass 로 .ps1 호출", "")
    check("fetch_ghidra_dist.ps1" in wbl, ".ps1 을 -File 로 지목", "")
    check("errorlevel" in wbl and "exit /b" in wbl, "exitcode 전파(%ERRORLEVEL% → exit /b)", "")
    raw = BAT.read_bytes()
    check(b"\r\n" in raw and raw.count(b"\n") == raw.count(b"\r\n"),
          ".bat CRLF 정규화(Windows 배치 canon)", "")
    sb = _read(START_BAT)
    check("%temp%\\jdkenv\\scripts\\python.exe" in sb.lower(),
          "start_windows.bat 사전점검이 .ps1 와 같은 venv 경로(%TEMP%\\jdkenv) 사용", "")
    check("fetch_ghidra_dist.bat" in sb.lower(), "start_windows.bat 이 부트스트랩 힌트 안내", "")


def main() -> int:
    print("🪟 Windows 부트스트랩 검증 게이트 — fetch_ghidra_dist.ps1")
    print("   (정적 구조 + 알고리즘 실행 + 오프라인 해결 증명 · 네트워크 없음)\n")
    audit_offline_install()
    audit_reassembly()
    audit_ps1_structure()
    audit_parity()
    audit_bat_consistency()
    print(f"\n{'='*60}")
    total = PASS + FAIL
    if FAIL:
        print(f"❌ WINDOWS BOOTSTRAP VERIFY FAILED — {PASS}/{total} (실패 {FAIL})")
        for f in FAILURES:
            print(f"   · {f}")
        return 1
    print(f"✅ WINDOWS BOOTSTRAP VERIFIED — {PASS}/{total} 통과")
    print("   정직 범위: 정적 구조·알고리즘·오프라인 해결은 증명됨. 실 Windows 호스트")
    print("   end-to-end 실행은 이 샌드박스에서 불가(호스트·pwsh 없음) → 미목격 잔여.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
