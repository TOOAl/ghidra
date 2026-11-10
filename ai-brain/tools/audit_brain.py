#!/usr/bin/env python3
"""🔍 Stage N 종합 감사 — A→N1+N2 전체를 4기준으로 기계 재감사.

두뇌가 **자기 자신을 감사**해요: 일회성 수동 주장이 아니라, 언제 어느
숙주에서든 다시 돌려 same 답을 내는 재생산 가능 게이트. 어떤 기준이라도
깨지면 exit 1 (CI/기동 전 검사 가능).

4기준 (사용자 상시 제약):
  개인정보 — 커밋 텍스트에 하드 시크릿·이메일·홈경로 0
  무료     — 외부(비-localhost) URL 은 전부 dormant 한 수동 다운로더에만,
             그 다운로더는 두뇌가 import 하지 않음 (자동 외부흐름 0)
  정직     — 환각방어·정직거부·100%-만-기록 코드 경로가 실제로 존재
  두뇌 소유 — 런타임 상태·무거운 바이너리 git 미유입 + gitignore 커버 +
             이식성(하드코딩 /tmp 런타임 경로·샌드박스 홈 절대경로 0)

자가완결: 자기 위치(__file__)에서 ai-brain 트리를 걷고, git 은 있으면
best-effort 로 쓰고 없으면 파일시스템으로 폴백. 네트워크 없음.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Iterable, List

HERE = Path(__file__).resolve().parent
BRAIN = HERE.parent                      # …/ai-brain
TEXT_EXT = {".py", ".md", ".json", ".js", ".html", ".css", ".sh", ".bat", ".yml"}
# 디스크 런타임 산출물 — 커밋 트리에 있으면 안 됨
RUNTIME_PATTERNS = ("quests.json", "semantic.json", "wiki_index.db", ".gguf",
                    "quest_markers", "sem-prose", "sem-code", ".corrupt-",
                    ".gguf.part")
RUNTIME_DIRS = {"state", "models", "runtime", "specimens", "__pycache__",
                "sem-prose", "sem-code", "quest_markers"}

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


def _in_git() -> bool:
    try:
        r = subprocess.run(["git", "-C", str(BRAIN), "rev-parse", "--is-inside-work-tree"],
                           capture_output=True, text=True, timeout=10)
        return r.returncode == 0 and r.stdout.strip() == "true"
    except Exception:
        return False


def _git_files() -> List[Path]:
    r = subprocess.run(["git", "-C", str(BRAIN), "-c", "core.quotepath=false",
                        "ls-files", "."], capture_output=True, text=True, timeout=30)
    return [BRAIN / line for line in r.stdout.splitlines() if line.strip()]


def _walk_files() -> List[Path]:
    """git 없을 때 폴백: 런타임 디렉터리 건너뛰고 텍스트 파일 수집."""
    out: List[Path] = []
    for p in BRAIN.rglob("*"):
        if not p.is_file():
            continue
        rel_parts = set(p.relative_to(BRAIN).parts[:-1])
        if rel_parts & RUNTIME_DIRS:
            continue
        if p.suffix in TEXT_EXT:
            out.append(p)
    return out


def committed_text_files() -> List[Path]:
    """감사 대상 = 커밋된(=두뇌가 소유·푸시한) 텍스트 파일."""
    if _in_git():
        files = [f for f in _git_files() if f.suffix in TEXT_EXT]
        if files:
            return files
    return _walk_files()


# ── 1) 개인정보 ───────────────────────────────────────────────────────────
SECRET_RE = re.compile(
    r"AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY|ghp_[A-Za-z0-9]{36}"
    r"|github_pat_[A-Za-z0-9_]{20,}|xox[baprs]-[A-Za-z0-9-]{10,}"
    r"|sk-[A-Za-z0-9]{32,}|AIza[0-9A-Za-z_-]{35}")
EMAIL_RE = re.compile(
    r"[A-Za-z0-9._%+-]+@(?:gmail|naver|daum|hanmail|outlook|yahoo|hotmail)\.[a-z.]+"
    r"|[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+\.(?:com|net|org|kr)\b")
HOME_RE = re.compile(r"/home/[a-z_][a-z0-9_]{2,}/|/Users/[a-zA-Z0-9._]{2,}/"
                     r"|C:\\Users\\[a-zA-Z0-9._]{2,}")
EMAIL_ALLOW = re.compile(r"example\.|schema|w3\.org|@2x|@types")


def audit_privacy(files: Iterable[Path]) -> None:
    print("── 1) 개인정보 (privacy) ──")
    secrets, emails, homes = [], [], []
    for f in files:
        try:
            txt = f.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        rel = str(f.relative_to(BRAIN))
        for i, line in enumerate(txt.splitlines(), 1):
            if SECRET_RE.search(line):
                secrets.append(f"{rel}:{i}")
            if EMAIL_RE.search(line) and not EMAIL_ALLOW.search(line):
                emails.append(f"{rel}:{i}")
            if HOME_RE.search(line):
                homes.append(f"{rel}:{i}")
    check(not secrets, "하드 시크릿(클라우드/API키/개인키/토큰) 0", str(secrets[:3]))
    check(not emails, "개인 이메일 주소 0", str(emails[:3]))
    check(not homes, "사용자 홈경로(사용자명 노출) 0", str(homes[:3]))


# ── 2) 무료 (자동 외부흐름 0) ─────────────────────────────────────────────
URL_RE = re.compile(r"https?://[A-Za-z0-9._:/-]+")
LOCALHOST_RE = re.compile(r"https?://(?:127\.0\.0\.1|localhost|\[::1\])")
DORMANT_DOWNLOADER = "scripts/download_portable_slm.py"


def audit_free(files: Iterable[Path]) -> None:
    print("── 2) 무료 (자동 외부흐름 0 · 유료 의존 0) ──")
    external: List[str] = []
    for f in files:
        if f.suffix != ".py":
            continue
        rel = str(f.relative_to(BRAIN)).replace(os.sep, "/")
        try:
            txt = f.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for i, line in enumerate(txt.splitlines(), 1):
            for u in URL_RE.findall(line):
                if not LOCALHOST_RE.match(u):
                    external.append(f"{rel}:{i}:{u[:48]}")
    # 모든 외부 URL 은 dormant 수동 다운로더 안에만 있어야 함
    stray = [e for e in external if not e.startswith(DORMANT_DOWNLOADER)]
    check(not stray, "비-localhost URL 은 수동 다운로더(dormant)에만", str(stray[:3]))
    check(all("huggingface.co" in e for e in external),
          "외부 URL = 무료 GGUF 호스트(huggingface)뿐 (유료 API 0)",
          str([e for e in external if "huggingface.co" not in e][:2]))
    # 그 다운로더가 두뇌에 import 되면 dormant 가 아님
    imported = False
    for f in files:
        if f.suffix != ".py" or f.relative_to(BRAIN).as_posix() == DORMANT_DOWNLOADER:
            continue
        try:
            txt = f.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if re.search(r"import\s+download_portable_slm|from\s+.*download_portable_slm", txt):
            imported = True
    check(not imported, "수동 다운로더는 두뇌가 import 안 함 (자동 다운로드 0)", "")


# ── 3) 정직 (코드 경로 존재) ──────────────────────────────────────────────
def _read(files: Iterable[Path], rel: str) -> str:
    for f in files:
        if f.relative_to(BRAIN).as_posix() == rel:
            try:
                return f.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                return ""
    return ""


def audit_honesty(files: Iterable[Path]) -> None:
    print("── 3) 정직 (환각방어·정직거부 코드 경로 존재) ──")
    cr = _read(files, "brain_engine/chain_reasoner.py")
    check('"known": False' in cr and "증거로 이을 수 없어요" in cr,
          "chain_reasoner: 증거 없으면 정직 거부(known:False) 경로 존재", "")
    check("_partial" in cr and "가장 가까운 접근" in cr,
          "chain_reasoner: 도달 실패 시 부분사슬 정직 보고 경로 존재", "")
    sb = _read(files, "brain_engine/slm_bridge.py")
    check("환각" in sb and "지어내" in sb or "억지 추측" in sb,
          "slm_bridge: 근거 없으면 환각 대신 '모름' 고지 경로 존재", "")
    ce = _read(files, "brain_engine/craft_engine.py")
    check("100.0" in ce or "match_pct" in ce,
          "craft_engine: 일치율 측정·기록 경로 존재", "")
    ql = _read(files, "brain_engine/quest_ledger.py")
    check("status=\"failed\"" in ql or '"failed"' in ql,
          "quest_ledger: 러너 예외 시 좀비 대신 정직 failed 기록 경로 존재", "")


# ── 4) 두뇌 소유 (git 위생 + 이식성) ──────────────────────────────────────
TMP_RUNTIME_RE = re.compile(r'Path\(\s*["\']/tmp|open\(\s*["\']/tmp'
                            r'|os\.path\.join\(\s*["\']/tmp|=\s*["\']/tmp/')


def audit_ownership(files: Iterable[Path]) -> None:
    print("── 4) 두뇌 소유 (git 위생 + 이식성) ──")
    # 4a) 커밋 트리에 런타임 상태·무거운 바이너리 없음
    leaked = []
    allf = _git_files() if _in_git() else list(BRAIN.rglob("*"))
    for f in allf:
        rel = f.relative_to(BRAIN).as_posix() if f.is_relative_to(BRAIN) else str(f)
        if any(pat in rel for pat in RUNTIME_PATTERNS):
            leaked.append(rel)
        if f.suffix in {".gguf", ".bin", ".safetensors"} and "specimens" not in rel:
            leaked.append(rel)
    check(not leaked, "런타임 상태·무거운 바이너리 git 미유입", str(leaked[:3]))
    # 4b) 이식성: 하드코딩 /tmp 런타임 경로 0 (tempfile.gettempdir() 사용)
    tmp_hits = []
    for f in files:
        if f.suffix != ".py":
            continue
        rel = f.relative_to(BRAIN).as_posix()
        try:
            txt = f.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for i, line in enumerate(txt.splitlines(), 1):
            s = line.strip()
            if s.startswith("#"):
                continue
            if TMP_RUNTIME_RE.search(line):
                tmp_hits.append(f"{rel}:{i}")
    check(not tmp_hits, "하드코딩 /tmp 런타임 경로 0 (이식성)", str(tmp_hits[:3]))
    # 4c) 이식성: 커밋 .py 에 샌드박스 홈 절대경로 0
    #     needle 을 이어붙여 이 감사 도구 자신의 소스가 self-match 하지 않게.
    sandbox_home = "/home/" + "user"
    abs_hits = []
    for f in files:
        if f.suffix != ".py":
            continue
        try:
            txt = f.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if sandbox_home in txt:
            abs_hits.append(f.relative_to(BRAIN).as_posix())
    check(not abs_hits, "커밋 코드에 샌드박스 홈 절대경로 0", str(abs_hits[:3]))
    # 4d) 런타임 산출물을 긷이그노어가 커버 (디스크에 있으면)
    if _in_git():
        uncovered = []
        for name in ("state/quests.json", "state/semantic.json",
                     "state/wiki_index.db"):
            p = BRAIN / name
            if p.exists():
                r = subprocess.run(["git", "-C", str(BRAIN), "check-ignore", "-q", name],
                                   capture_output=True, timeout=10)
                if r.returncode != 0:
                    uncovered.append(name)
        check(not uncovered, "디스크 런타임 산출물 = gitignore 커버", str(uncovered))


def main() -> int:
    print("🔍 Stage N 종합 감사 — A→N1+N2 · 4기준 기계 재감사")
    print(f"   대상 트리: {BRAIN}\n")
    files = committed_text_files()
    print(f"   감사 파일 수 (커밋된 텍스트): {len(files)}\n")
    audit_privacy(files)
    audit_free(files)
    audit_honesty(files)
    audit_ownership(files)
    print()
    if FAIL == 0:
        print(f"✅ BRAIN AUDIT PASSED — {PASS} passed / 0 failed "
              f"(개인정보·무료·정직·두뇌소유 4기준 그린)")
    else:
        print(f"❌ BRAIN AUDIT FAILED — {PASS} passed / {FAIL} failed")
        for f in FAILURES:
            print(f"     · {f}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
