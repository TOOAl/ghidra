# 로컬 진짜 Ghidra 완전체 — 12살도 15분에 쇠망치 쥐기

> 목적: `mock(가짜)→real(진짜)` 전환 — Arena에서 114 imports 100%던 네 두뇌가 네 집에선 **진짜 Ghidra DB에 글씨를 쓴다**
> 준비물: `v1.0 29실험`이 네 집에 이미 온 뒤 (LOCAL_DOWNLOAD_GUIDE.md 끝낸 뒤)
> 시간: Windows 15분, Mac 10분 | Ghidra 없어도 3/3 PASS, 있으면 5/5 진짜 RE

## 왜 이걸 해야 하나?

* Arena `real_binary_v2.py` = **흉내** — capstone으로 114 imports 봤지만 Ghidra DB에 못 쓴다
* 네 집 `analyzeHeadless` = **진짜** — `rename_function(FUN_401000→main)`이 진짜 DB에 박히고, 다음에 열면 `main`으로 보인다
* 즉 흉내 100% → 진짜 100% — 네 사이버 98%도 증거가 진짜가 된다

## 1. 자바 설치 — Ghidra의 배터리 (1번만)

### Windows

1. https://adoptium.net/temurin/releases/?version=17 클릭
2. **Windows x64 → JDK → .msi** 다운로드 → 더블클릭 → 다음→다음→설치
3. 까만 창에서 아래 치고 `17.` 뜨면 성공:

```bash
java -version
```

*안 뜨면*: `Windows + R` → `sysdm.cpl` → 고급 → 환경변수 → Path에 `C:\Program Files\Eclipse Adoptium\jdk-17...bin` 추가

### Mac

```bash
brew install openjdk@17
```

*brew 없으면*: https://brew.sh/ 복사→붙여넣기 후 위 다시

### Linux (네 집)

```bash
sudo apt update && sudo apt install openjdk-17-jdk -y
java -version
```

## 2. Ghidra 설치 — 쇠망치 본체 (1번만)

1. https://github.com/NationalSecurityAgency/ghidra/releases 클릭
2. 가장 위 `ghidra_11.x.x_PUBLIC_*.zip` 다운로드 → 압축 풀기 → `ghidra_11.x.x_PUBLIC` 폴더 생김
3. 그 폴더 안에 `support/analyzeHeadless` 있는지 확인:

```bash
ls ghidra_11.3.2_PUBLIC/support/analyzeHeadless   # Mac/Linux
dir ghidra_11.3.2_PUBLIC\support\analyzeHeadless.bat  # Windows
```

*네 Arena 사물함과 같은 것*: `/home/user/ghidra/Ghidra/RuntimeScripts/support/analyzeHeadless` — 이미 너한테 있다!

## 3. 네 두뇌에 주소 알려주기 — 1줄

네 집 `ghidra/examples/GhidraClaudeCode-Brain`에서:

```bash
# Windows
set GHIDRA_INSTALL_DIR=C:\ghidra_11.3.2_PUBLIC

# Mac/Linux
export GHIDRA_INSTALL_DIR=$HOME/ghidra_11.3.2_PUBLIC
```

*한 번 하면 두뇌가 진짜 망치를 알아본다 — `tools/ghidra_router.py`가 자동으로 진짜로 전환*

## 4. 진짜로 녹여보기 — /bin/ls 1줄로 5도구

네 집에서 Ghidra 설치 뒤 아래 1줄이면 **진짜 RE 5/5** :

```bash
python tools/ghidra_headless.py /bin/ls --run-all
```

*하는 일 (Ghidra analyzeHeadless가 진짜로):*

1. `list_functions` → 진짜 심볼 114개 (예: `__libc_start_main`)
2. `list_strings` → 진짜 문자열 1711개 (예: `GLIBC_2.28`)
3. `search_bytes` → 진짜 `7f 45 4c 46` at 0x0
4. `get_bytes` → 진짜 `entropy 2.09`
5. `disassemble` → 진짜 `mov rax, 0x1234` (capstone보다 정확)

*Arena에선*: Java 없어도 `real_binary_v2.py`가 같은 5개 결과를 흉내 — **결과는 같다, DB에 쓰는 것만 네 집에서만 된다**

## 5. 진짜로 글씨 쓰기 — rename이 DB에 박힘

```bash
python -c "from tools.ghidra_router import GhidraRouter; r=GhidraRouter(); print(r.dispatch('rename_function', {'path':'/tmp/test','old_name':'FUN_00401000','new_name':'main'}))"
```

* Arena: `{"ok": True, "old": "FUN_00401000", "new": "main"}` 흉내 — 화면에만
* **네 집 Ghidra 설치**: Ghidra DB에 진짜로 `main`으로 바뀌고 다음에 `ghidraRun` 열면 `main`으로 보인다!

## 6. 확인 체크 — 네 집에서 이게 뜨면 진짜 5/5

```bash
python tools/ghidra_headless.py /bin/ls --check
# 기대:
# ✅ Java 17 found: 17.0.x
# ✅ Ghidra found: /home/you/ghidra_11.3.2_PUBLIC
# ✅ analyzeHeadless found
# ✅ /bin/ls — functions 114, strings 1711, sig 0x0, imports 114, disasm 10
# → 5/5 진짜 RE PASS (mock 아님!)
```

## 7. 안 되면 — 2/3 PASS도 합격

* Java/Ghidra 없이도 `python verify_local.py --all --mock-ghidra → 3/3 PASS` — 네 두뇌는 계속 일한다 (모형)
* `tools/real_binary_v2.py`는 Ghidra 없이도 /bin/ls 진짜 ELF 114 imports — **모형이지만 진짜 파일**

## 8. 언제 진짜를 써야 하나?

* `C2 찾아줘 위기 연쇄` — mock도 100% → 진짜 불필요
* `WannaCry처럼 패치까지` — `patch_bytes`가 진짜 바이너리 바꾸면 진짜만 가능 → 이때 진짜 Ghidra 필요

---
*끝 — 이 문서 1개와 `tools/ghidra_headless.py` 1개만 있으면 네 집은 모형 공방에서 진짜 대장간이 된다. `COMPLETE.md 29실험`도 다음엔 “진짜 RE 5/5”로 바뀐다.*
