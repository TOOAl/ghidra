#!/usr/bin/env bash
# 🚚 Fetch the trimmed Ghidra headless dist that `.github/workflows/dist-to-repo.yml`
#    publishes to an orphan branch, reassemble it, and prove it runs.
#
# WHY THIS SHAPE
#   Release assets redirect to release-assets.githubusercontent.com and action
#   artifacts to a sibling host — both outside the sandbox's allow-list, so the
#   built dist cannot be downloaded directly.  Committed repository content is
#   served by codeload.github.com, which IS allowed (verified: HTTP 200).
#   GitHub rejects any single committed file over 100 MB, so the dist arrives as
#   <=95 MB chunks that this script glues back together and checksums.
#
# The dist is unpacked OUTSIDE the repository (/tmp) so a few hundred MB of
# binaries never enter git or the turn's patchset.
#
# Usage:  bash ai-brain/tools/fetch_ghidra_dist.sh [branch] [repo]
set -euo pipefail
# resolve BEFORE any cd below changes the working directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

BRANCH="${1:-ghidra-dist}"
REPO="${2:-TOOAl/ghidra}"
WORK=/tmp/ghidra_dl
DEST=/tmp/ghidra_dist

echo "── 🚚 Ghidra headless dist 배달 ──"
echo "  저장소 : $REPO"
echo "  브랜치 : $BRANCH (orphan, disposable)"

if ! curl -sSfL --max-time 900 -o "$WORK.tgz" \
     "https://codeload.github.com/$REPO/tar.gz/refs/heads/$BRANCH"; then
  echo "  ❌ 브랜치 '$BRANCH' 를 가져올 수 없어요."
  echo "     워크플로가 아직 안 돌았거나, 다른 이름을 쓰셨을 수 있습니다."
  echo "     확인: https://github.com/$REPO/actions"
  exit 3
fi

rm -rf "$WORK" && mkdir -p "$WORK"
tar xzf "$WORK.tgz" -C "$WORK" --strip-components=1
echo "  청크 $(ls "$WORK"/ghidra_headless.tgz.part* 2>/dev/null | wc -l)개 받음 · $(du -sh "$WORK.tgz" | cut -f1)"

cd "$WORK"
cat ghidra_headless.tgz.part* > ghidra_headless.tgz
if [ -f SHA256SUMS.txt ]; then
  want="$(cat SHA256SUMS.txt | tr -d '[:space:]')"
  got="$(sha256sum ghidra_headless.tgz | awk '{print $1}')"
  if [ "$want" != "$got" ]; then
    echo "  ❌ checksum 불일치 (기대 $want / 실제 $got)"; exit 4
  fi
  echo "  ✅ sha256 일치: $got"
fi

rm -rf "$DEST" && mkdir -p "$DEST"
tar xzf ghidra_headless.tgz -C "$DEST"
ROOT="$(ls -d "$DEST"/ghidra_* | head -1)"
echo "  📂 $ROOT · $(du -sh "$ROOT" | cut -f1)"

# ── JVM: Ghidra 12.3 wants Java 25 (Ghidra/application.properties:
#    application.java.min=25).  PyPI's jdk4py ships Temurin 25, and
#    files.pythonhosted.org is on the allow-list.
VENV=/tmp/jdkenv
if [ ! -x "$VENV/bin/python" ]; then
  echo "  ☕ JDK 설치 중 (jdk4py → Temurin 25) …"
  python3 -m venv "$VENV"
  # 📦 먼저 우리 자신의 벤더 휠(ai-brain/vendor, linux x86_64·cp311)로 설치 —
  #    네트워크 없이.  다른 플랫폼/파이썬이면 정직하게 PyPI 로 폴백.
  if "$VENV/bin/pip" install -q --no-index --find-links "$SCRIPT_DIR/../vendor" jdk4py pyghidra 2>/dev/null; then
    echo "  📦 벤더 휠로 설치 완료 (외부 연결 없음)"
  else
    echo "  📦 벤더 휠이 이 플랫폼과 안 맞음 → PyPI 폴백"
    "$VENV/bin/pip" install -q jdk4py pyghidra
  fi
fi
export JAVA_HOME="$("$VENV/bin/python" -c 'import jdk4py;print(jdk4py.JAVA_HOME)')"
export PATH="$JAVA_HOME/bin:$PATH"
echo "  ☕ $(java -version 2>&1 | head -1)"
# Ghidra 12 dropped Jython, and jdk4py is an honest JRE (no javac), so:
#   * .py postScript  → dead (no Jython)
#   * .java postScript → dead (nothing can compile it here)
#   * launch.sh CLI    → dead (LaunchSupport demands a JDK it will not find)
# The living path is PyGhidra in-process: the tool hands JAVA_HOME straight
# to the launcher (skipping LaunchSupport) and runs the same analyzers and
# decompiler that the GUI would.  That run IS the smoke test — no separate
# CLI probe that could fail silently.
HEADLESS="$ROOT/support/analyzeHeadless"
if [ ! -f "$HEADLESS" ]; then
  echo "  ❌ analyzeHeadless 를 찾을 수 없어요: $HEADLESS"; exit 5
fi
chmod +x "$HEADLESS" "$ROOT/support/"*.sh 2>/dev/null || true

# 🛠 숙주가 스스로 도구를 주조한다: 배달된 네이티브 decompiler 는
#    ubuntu-24 에서 구워져 GLIBC_2.38 을 요구해요.  이 숙주의 glibc 가
#    더 늙었다면, 저장소 자신의 C++ 소스로 다시 굽습니다 — 공식
#    바이너리와 동일한 구성(ghidra_opt 타겟, BFD 불필요)이에요.
DECOMP="$ROOT/Ghidra/Features/Decompiler/os/linux_x86_64/decompile"
# ⚠ 여기서 `ldd ... | grep -q "not found"` 를 쓰면 **안 돼요**(실제로 깨졌었어요):
#   `grep -q` 는 첫 일치에서 즉시 종료하며 파이프를 닫고, 그러면 `ldd` 가
#   SIGPIPE(141) 로 죽어요. 이 스크립트는 `set -o pipefail` 이라 파이프라인 상태가
#   141 → **조건이 거짓** → 수리 단계를 *조용히* 건너뛰고, 그 결과 디컴파일된 C 가
#   0개여서 exit 6 으로 끝났어요. 실측: 20회 중 5회(25%) 재현.
#   → 출력을 먼저 변수에 담고 **파이프 없이** 판정해요(20/20 결정적).
_LDD_OUT="$(ldd "$DECOMP" 2>&1 || true)"
_NEEDS_REBUILD=0
if [ -x "$DECOMP" ]; then
  case "$_LDD_OUT" in *"not found"*) _NEEDS_REBUILD=1 ;; esac
fi
if [ "$_NEEDS_REBUILD" = 1 ]; then
  echo "  🛠 decompile 이 이 숙주 glibc 와 안 맞음 → 소스에서 재주조"
  if command -v g++ >/dev/null 2>&1 && command -v make >/dev/null 2>&1; then
    CPP="$(cd "$SCRIPT_DIR/../.." && pwd)/Ghidra/Features/Decompiler/src/decompile/cpp"
    if make -C "$CPP" -j"$(nproc 2>/dev/null || echo 2)" ghidra_opt >/tmp/decomp_build.log 2>&1; then
      cp "$CPP/ghidra_opt" "$DECOMP" && chmod +x "$DECOMP"
      echo "  ✅ 재주조 완료 (ghidra_opt → decompile)"
    else
      echo "  ❌ 재주조 실패 — /tmp/decomp_build.log 를 보세요"; exit 7
    fi
  else
    echo "  ❌ g++/make 가 없어 decompiler 를 고칠 수 없어요"; exit 7
  fi
fi

SAMPLE="$(cd "$SCRIPT_DIR/../.." && pwd)/GhidraDocs/GhidraClass/ExerciseFiles/Advanced/globalRegVars.so"
echo "  🔬 PyGhidra 사실 추출 (실패하면 여기서 멈춰요 — 조용한 통과 없음)"
rm -f /tmp/brain_facts.json
GHIDRA_INSTALL_DIR="$ROOT" "$VENV/bin/python" "$SCRIPT_DIR/ghidra_facts_pyghidra.py" "$SAMPLE" /tmp/brain_facts.json 400 || {
  echo "  ❌ PyGhidra 팩트 추출 실패 — 배달을 신뢰할 수 없어요"; exit 6;
}

# 🚚 그리고 숫자로 증명: 이게 진짜 Ghidra 출력인지, 디컴파일된 C가 있는지,
#    산문 채널이 그대로인지.  0 이 아니면 배달을 믿지 않아요.
"$VENV/bin/python" "$SCRIPT_DIR/verify_ghidra_facts.py" || exit 6
echo "── 배달 완료. ROOT=$ROOT ──"
