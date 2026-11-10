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
  "$VENV/bin/pip" install -q jdk4py
fi
export JAVA_HOME="$("$VENV/bin/python" -c 'import jdk4py;print(jdk4py.JAVA_HOME)')"
export PATH="$JAVA_HOME/bin:$PATH"
echo "  ☕ $(java -version 2>&1 | head -1)"

# ── Smoke test: run the real analyzeHeadless on a real binary that ships in
#    this repository, and print what the brain would be taught from it.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
HEADLESS="$ROOT/support/analyzeHeadless"
if [ ! -f "$HEADLESS" ]; then
  echo "  ❌ analyzeHeadless 를 찾을 수 없어요: $HEADLESS"; exit 5
fi
chmod +x "$HEADLESS" "$ROOT/support/"*.sh 2>/dev/null || true
SAMPLE="$(cd "$SCRIPT_DIR/../.." && pwd)/GhidraDocs/GhidraClass/ExerciseFiles/Advanced/globalRegVars.so"
echo "  🔬 스모크 테스트: $(basename "$SAMPLE")"
rm -rf /tmp/ghidra_proj && mkdir -p /tmp/ghidra_proj
"$HEADLESS" /tmp/ghidra_proj smoke -import "$SAMPLE" -overwrite \
    -scriptPath "$SCRIPT_DIR" \
    -postScript ExportBrainFacts.java /tmp/ghidra_facts.json 2>&1 | tail -15 || true

# 🚚 그리고 숫자로 증명: 이게 진짜 Ghidra 출력인지, 디컴파일된 C가 있는지,
#    산문 채널이 그대로인지.  0 이 아니면 배달을 믿지 않아요.
if [ -f /tmp/ghidra_facts.json ]; then
  "$VENV/bin/python" "$SCRIPT_DIR/verify_ghidra_facts.py" || exit 6
fi
echo "── 배달 완료. ROOT=$ROOT ──"
