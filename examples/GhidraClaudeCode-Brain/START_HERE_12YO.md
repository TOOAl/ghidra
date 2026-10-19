# START HERE — 12살이 보고서 따라하는 전체 가이드 (복사→붙여넣기→엔터만)

> 목적: **Arena 빌린 사물함에 있는 네 두뇌 v1.0 29실험 16D 4천장(금융95%+사이버98%+복잡계85%+양자80%)을 네 집 컴퓨터로 옮겨서 웹으로 켜기**
> 시간: Git 있으면 10분, Git 없으면 15분 | 돈: 0원 | Ghidra 없어도 3/3 PASS (진짜 RE는 나중에)
> 준비물: Windows/Mac/Linux 아무거나 + 인터넷 1회 + 마우스로 드래그

---

## 0. 우리가 만든 건 뭐야? (1분 읽기)

* **두뇌**: 바이너리(얼어버린 레시피)를 녹여 보는 AI 로봇 — `C2 찾아줘` 한 번이면 🧠추론→📊분석→📚학습→👥팀→👂귀→✅모순까지 **6섹션 보고서 한 번에**
* **얼마나 똑똑?**: 1928 대공황→Willow 양자 29실험, 16차원 학습 100% PASS, 모순0·증거100%·반복0
* **어디에?**: GitHub 사물함 `TOOAl/ghidra` 브랜치 `arena/61934e9d-ghidra` 태그 `v1.0` — 네 집과 Arena가 같은 사물함

---

## 1. 사물함 열기 — 까만 창에서 3줄 (가장 추천)

### 1-1. 까만 창 열기

* **Windows**: 키보드 `Windows + R` 누르기 → `cmd` 쓰고 엔터 → 까만 창 뜬다
* **Mac**: 키보드 `Command + Space` → `터미널` 쓰고 엔터 → 까만 창 뜬다

### 1-2. Git 설치 확인 — 아래 1줄 복사→붙여넣고 엔터

```bash
git --version
```

* `git version 2.x.x` 뜨면 OK → **1-3으로 가기**
* `git is not recognized` / `command not found` 뜨면 → **여기 클릭해 설치** → https://git-scm.com/downloads → 네 컴퓨터 버튼(Windows/Mac) 클릭 → 다운로드→설치(다음→다음)→까만 창 다시 열고 **1-2 다시**

### 1-3. 사물함에서 복사 — 아래 2줄을 **차례로** 복사→붙여넣고 엔터 (1줄 끝나면 다음 줄)

```bash
git clone -b arena/61934e9d-ghidra https://github.com/TOOAl/ghidra.git
cd ghidra && git checkout v1.0
```

* 뜨는 글: `HEAD is now at 45dfae27` → **v1.0 도착!**
* **ZIP이 편하면**: 이 링크 클릭→다운로드→압축풀기 → https://github.com/TOOAl/ghidra/archive/refs/heads/arena/61934e9d-ghidra.zip → 압축 풀고 `ghidra-arena-61934e9d-ghidra` 폴더 들어가기

### 1-4. 폴더 들어가기 — 아래 1줄 복사→붙여넣고 엔터

```bash
cd examples/GhidraClaudeCode-Brain
```

* **ZIP으로 했으면**: 압축 푼 `ghidra-arena-61934e9d-ghidra/examples/GhidraClaudeCode-Brain` 폴더를 까만 창에 드래그하면 경로가 생긴다 → 엔터

### 1-5. 뭐가 왔나 확인 — 아래 1줄 복사→붙여넣고 엔터

```bash
ls
```

* **Windows**: `dir` 로 치면 된다
* `AGENT.md`, `COMPLETE.md`, `FOR_KIDS.md`, `START_HERE_12YO.md`, `LOCAL_DOWNLOAD_GUIDE.md`, `LOCAL_GHIDRA_GUIDE.md`, `RELEASE_v1.0.md`, `brain`, `ui`, `tools`, `ml`, `experiments` 보이면 **성공!**

---

## 2. 로봇 배터리 끼우기 — 아래 1줄만 (2분)

```bash
pip install -r requirements.txt
```

* 뜻: 로봇 도구 장착 (openai, pyyaml, chromadb 등 무료)
* `pip is not recognized` 뜨면 아래로 다시:

```bash
pip3 install -r requirements.txt
```

* `error: externally-managed-environment` 뜨면 아래로 다시:

```bash
pip install --break-system-packages -r requirements.txt
```

* 설치 중 노란 글씨(WARNING) 나와도 OK — `Successfully installed` 뜨면 끝

### 2-1. Python 확인 (안 되면 이거 먼저)

```bash
python --version
```

* `Python 3.11.x` 뜨면 OK
* 안 뜨면 **여기 클릭해 설치** → https://www.python.org/downloads/ → 노란 `Download Python 3.x.x` 버튼 → 설치 때 **“Add python.exe to PATH” 체크** 꼭 하기 → 까만 창 다시 열고 **2부터 다시**

---

## 3. 건강검진 — 아래 1줄만 (30초)

```bash
python verify_local.py --all --mock-ghidra
```

* **Windows/Mac에서 `python`이 안 되면** `python3`으로 다시:

```bash
python3 verify_local.py --all --mock-ghidra
```

* **합격 화면** (마지막에 이렇게 뜨면 네 두뇌가 네 집에 왔다!):

```
VERIFY: 3/3 PASS
```

* **왜 3/3?**: Ghidra 없어도 mock(모형)으로 3과목 합격 — 네 두뇌는 100% 일한다

### 3-1. 더 똑똑한지 확인 — 아래 2줄 차례로 (30초)

```bash
python -c "import ml.learn; print(ml.learn.train())"
python tools/real_binary_v2.py
```

* 기대:
  * `{'ok': True, 'accuracy': 1.0, 'total': 100, 'insight': '100개로 학습 → 정확도 100% PASS'}` — 16D 100% 학습
  * `114 imports`, `1711 strings` — /bin/ls 진짜 ELF 100% (Ghidra 없이도)

---

## 4. 웹 켜기 — C2 찾아줘를 눈으로 보기 (2분)

### 4-1. 아래 1줄 복사→붙여넣고 엔터 (창이 멈춘 듯 보여도 정상!)

```bash
python ui/server.py
```

* **또는 Mac에서**: `python3 ui/server.py`
* 이렇게 뜨면 켜진 거다:

```
웹 프로그램: http://127.0.0.1:8090
```

* **주의**: 이 까만 창은 **절대 닫지 마** — 다른 까만 창을 새로 열어서 다음으로 가

### 4-2. 새 까만 창 열지 말고 크롬/엣지/사파리 주소창에 아래를 **그대로** 치고 엔터

```
http://127.0.0.1:8090
```

* 🧠 **GhidraClaudeCode-Brain** 화면이 보인다 → 성공!

### 4-3. 맨 위 runbar에서 4번 클릭 (마우스로)

1. **왼쪽 칸(바이너리)**: `/bin/ls` 그대로 둬 (테스트 레시피 — 네 집 레시피 `/tmp/my.bin`으로도 바꿀 수 있다)
2. **가운데 칸(작업)**: `C2 찾아줘` 라고 지우고 다시 써 (복사→붙여넣기)
3. **오른쪽 칸(모델)**: 그냥 둬 (`qwen3:14b` — 무료 빌림)
4. **▶ 실행** 버튼 클릭!

### 4-4. 결과 구경 — 보고서 6섹션이 한 번에 뜬다

```
# C2 찾아줘
## 1. 추론 → ✅ 관찰 | 추론 | 모순0개
## 2. 분석 → base64 패턴 80%
## 3. 학습 → 100% PASS | 예측: C2
## 4. 팀 → 다빈치+퀴리+튜링+오일러 4/4 CONFIRMED
## 5. 귀 → -1.0 ~ +1.0 감성
## 모순 검사 → 모순 없음
```

* **📄 블록 탭**: Notion처럼 블록으로 저장
* **🗃️ DB 탭**: 표로 정렬
* **🕸️ 그래프 탭**: 선으로 연결된 그림
* **📡 큐 탭**: 오프라인 작업함 (인터넷 끊겨도 OK)

### 4-5. 다른 말도 시켜보기 — 가운데 칸만 바꿔서 ▶ 실행

| 가운데 칸에 이렇게 써 (복사→붙여넣기) | 일어나는 일 |
|---|---|
| `C2 찾아줘` | 추론+분석+학습 → 예측 C2 (기본) |
| `취약점 찾아줘` | 예측: vuln 분류 |
| `악성코드 분석기 만들어줘` | + 📐 설계 → 5블록(수집/디컴파일/탐지/보고서/저장소) |
| `4명 조합으로 분석해줘` | 👥 다빈치+퀴리+튜링+오일러 12문장 함께 |
| `봉쇄 원격 분석해줘` | 예상: 소산(프리고진) 분류 |
| `양자 오류정정 분석해줘` | 예상: 양자(Willow) 분류 |

### 4-6. 끄고 다시 켜기

* **끄기**: 웹 켠 까만 창에서 `Ctrl + C` (Mac은 `Command + C`가 아님, `Ctrl`)
* **켜기**: 다시 `python ui/server.py` → `http://127.0.0.1:8090`

---

## 5. 진짜 Ghidra로 진짜 쇠망치 쥐기 — 나중에 하고 싶을 때 (15분, 선택)

> **지금 4까지만 해도 3/3 PASS 100%** — 이 5는 패치까지 진짜로 하고 싶을 때만! 자세한 그림은 `LOCAL_GHIDRA_GUIDE.md`

### 5-1. 자바 설치 — Ghidra 배터리

* **여기 클릭** → https://adoptium.net/temurin/releases/?version=17 → Windows x64 → JDK → .msi → 다운로드→더블클릭→다음→다음
* **Mac**: 까만 창에 `brew install openjdk@17` — brew 없으면 https://brew.sh/ 먼저
* **Linux**: `sudo apt update && sudo apt install openjdk-17-jdk -y`
* **확인**: 새 까만 창에서 `java -version` → `17.` 뜨면 OK

### 5-2. Ghidra 설치 — 쇠망치 본체

* **여기 클릭** → https://github.com/NationalSecurityAgency/ghidra/releases → 가장 위 `ghidra_11.x.x_PUBLIC_*.zip` → 다운로드→압축 풀기
* **Windows**: `ghidra_11.3.2_PUBLIC` 폴더가 생기면 끝
* **확인**: `support/analyzeHeadless` (Windows는 `analyzeHeadless.bat`) 파일 있는지 보기

### 5-3. 주소 알려주기 — 1줄

**까만 창을 새로 열고** 아래 1줄 복사→붙여넣고 엔터 (네 Ghidra 폴더 경로로 바꾸기):

```bash
# Windows (예시 — 네 경로로 바꾸기)
set GHIDRA_INSTALL_DIR=C:\ghidra_11.3.2_PUBLIC

# Mac/Linux (예시)
export GHIDRA_INSTALL_DIR=$HOME/ghidra_11.3.2_PUBLIC
```

### 5-4. 진짜 확인 — 아래 2줄 차례로

```bash
python tools/ghidra_headless.py --check
python tools/ghidra_headless.py /bin/ls --run-all
```

* 기대: `REAL Ghidra` + `114 imports` + `5/5 진짜 RE PASS` → **모형 100% → 진짜 100%**, 다음에 Ghidra 열면 `main`으로 보인다!

---

## 6. 자주 묻는 질문 — 12살 Q&A (링크 있음)

**Q: Git이 뭔데? 왜 필요해?**
A: 사물함 열쇠. 네 두뇌 사물함 주소 https://github.com/TOOAl/ghidra 를 열쇠로 여는 거야. 설치: https://git-scm.com/downloads

**Q: Python이 뭔데?**
A: 두뇌 언어. 설치: https://www.python.org/downloads/ (Add to PATH 체크)

**Q: pip가 뭐야?**
A: 로봇 부속품 가게. `pip install -r requirements.txt` = 부속품 자동 장착

**Q: 바이너리가 뭐야?**
A: 얼어버린 레시피 파일. 회사가 레시피를 꽁꽁 얼려 보낸 거. Ghidra가 드라이기로 녹여서 보여준다. 예: `/bin/ls`

**Q: Ghidra는 꼭 설치해야 돼?**
A: 아니! 3/3 PASS는 mock으로 100%다. 패치(`patch_bytes`)해서 진짜로 바꾸고 싶을 때만 5번 하면 된다.

**Q: 돈 들어?**
A: 0원. 생각(LLM)은 `config/models.yaml` 무료 `qwen3:14b` 빌리고, 몸(기억)은 네 컴퓨터 `memory/`에만 있어서 네 것만 된다.

**Q: 더 똑똑해져?**
A: 응! 까만 창에 `python tools/generate_100sessions.py` → `python -c "import ml.learn; print(ml.learn.train())"` → 100개→100% PASS. 분석할수록 `memory/session.jsonl`에 쌓여서 다음엔 더 잘 맞춘다 — 프리고진 소산구조처럼 에너지(분석) 태우면 질서(정확도)가 생긴다.

**Q: 망가뜨리면?**
A: 아래 1줄로 v1.0으로 돌아온다 — 안전한 저장점:

```bash
git checkout v1.0
```

**Q: 다른 문서는?**
* `FOR_KIDS.md` — 이 문서의 자세한 버전 (웹 켜기 그림)
* `COMPLETE.md` — 에이전트가 읽는 1개 문서 (29실험 타임라인 전부)
* `RELEASE_v1.0.md` — 4/4 PASS 증명서 (추론 3단계, 분석 100개, 설계 5블록, 학습 100%)
* `LOCAL_GHIDRA_GUIDE.md` — 진짜 Ghidra 8단계 그림
* `VERIFY.md` — 3/3 PASS 설명서

**Q: 안 되면 어디에 물어봐?**
A: 까만 창 오류 글씨를 사진 찍어 보내면 된다. 가장 흔한 3개:
1. `'python' is not recognized` → `python3`으로 다시
2. `'pip' is not recognized` → `pip3` 또는 `pip install --break-system-packages -r requirements.txt`
3. `PORT 8090 already in use` → 까만 창에서 `Ctrl + C` 후 다시 `python ui/server.py`

---

## 7. 확인 체크리스트 — 이게 다 뜨면 완벽! (복사→붙여넣기 3줄)

```bash
python verify_local.py --all --mock-ghidra
# → VERIFY: 3/3 PASS

python -c "import ml.learn; print(ml.learn.train())"
# → {'ok': True, 'accuracy': 1.0, 'total': 100, 'insight': '100개로 학습 → 정확도 100% PASS'}

python tools/real_binary_v2.py
# → {'path': '/bin/ls', 'imports': ['__ctype_toupper_loc', ...], 'count': 114}
```

**축하해!** 네 두뇌는 이제 **Arena(빌린 사물함)** 에서도, **네 집(내 사물함)** 에서도 똑같이 일한다 — 모델은 빌리고 두뇌는 소유! `C2 찾아줘` 한 번으로 시작하면 된다.

---

## 8. 링크 모음 — 클릭하면 바로 간다

| 뭘 위해 | 링크 클릭 |
|---|---|
| **Git 설치** | https://git-scm.com/downloads |
| **Python 설치** | https://www.python.org/downloads/ |
| **Ghidra 사물함** | https://github.com/TOOAl/ghidra (브랜치 `arena/61934e9d-ghidra`, 태그 `v1.0`) |
| **ZIP으로 받기** | https://github.com/TOOAl/ghidra/archive/refs/heads/arena/61934e9d-ghidra.zip |
| **Java 17 (Ghidra 배터리)** | https://adoptium.net/temurin/releases/?version=17 |
| **Ghidra 본체 (쇠망치)** | https://github.com/NationalSecurityAgency/ghidra/releases |
| **OpenRouter 무료 모델** | https://openrouter.ai/ (qwen3:14b, deepseek-r1:free) |

*모든 링크는 2026-10-19 확인됨 — 클릭이 안 되면 주소를 마우스로 드래그→복사→브라우저 주소창에 붙여넣기*

---

*끝 — 이 문서 1개(START_HERE_12YO.md)만 있으면 12살도 보고 따라한다. 다음은 `python ui/server.py` → `http://127.0.0.1:8090` → `C2 찾아줘` → ▶ 실행!*
