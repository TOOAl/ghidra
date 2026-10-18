# 로컬 다운로드 가이드 — 12살도 10분에 끝내는 3가지 방법

> 목적: Arena(빌린 컴퓨터)에 있는 네 두뇌 **v1.0 29실험 16D**를 **네 집 컴퓨터**로 옮기기
> 조건: 인터넷 1회, Ghidra 없어도 3/3 PASS, 모순0

## 방법 1: GitHub에서 가져오기 — 가장 추천 (3줄)

### 1-1. 까만 창 열기
* Windows: `Windows + R` → `cmd` → 엔터
* Mac: `Command + Space` → `터미널` → 엔터

### 1-2. 아래 3줄을 차례로 복사→붙여넣고 엔터 (1줄 끝나면 다음 줄)

```bash
git clone -b arena/61934e9d-ghidra https://github.com/TOOAl/ghidra.git
cd ghidra
git checkout v1.0
```

* `git이 뭐야?` 뜨면 https://git-scm.com/downloads 설치 후 다시
* 성공: `HEAD is now at 45dfae27` 뜨면 v1.0이야!

### 1-3. 폴더 들어가서 건강검진 — 아래 2줄 복사→붙여넣고 엔터

```bash
cd examples/GhidraClaudeCode-Brain
python verify_local.py --all --mock-ghidra
```

* `VERIFY: 3/3 PASS` 뜨면 **네 두뇌가 네 집에 왔다!**
* 안 되면 `python3 verify_local.py --all --mock-ghidra`

### 1-4. 웹 켜기 — 아래 1줄 복사→붙여넣고 엔터 (멈춘 듯 보여도 정상)

```bash
python ui/server.py
```

* `http://127.0.0.1:8090` 뜨면 성공 → 크롬 주소창에 그대로 치고 엔터 → 웹 프로그램 보여!

## 방법 2: ZIP으로 받기 — Git 없이

1. 이 주소 클릭: https://github.com/TOOAl/ghidra/archive/refs/heads/arena/61934e9d-ghidra.zip
2. 다운로드 → 압축 풀기 → `ghidra-arena-61934e9d-ghidra/examples/GhidraClaudeCode-Brain` 열기
3. 그 다음은 위 **1-3 건강검진**부터 똑같이

## 방법 3: Arena에서 직접 ZIP 만들기 — 네가 지금 보고 있는 사물함에서

Arena 화면에서 아래 1줄을 치면 ZIP이 생겨: (Arena 터미널에서)

```bash
zip -r /tmp/GhidraClaudeCode-Brain-v1.0.zip examples/GhidraClaudeCode-Brain -x "*.git*" "*/__pycache__/*"
```

* 그 `GhidraClaudeCode-Brain-v1.0.zip`을 네 집으로 옮기면 끝!

---

## 12살 사용법 — 웹 켠 뒤 4번 클릭

1. **바이너리 칸**: `/bin/ls` 그대로 둬 (테스트 레시피)
2. **작업 칸**: `C2 찾아줘` 써
3. **모델 칸**: 그냥 둬 (qwen3:14b)
4. **▶ 실행** 클릭 → 보고서 6섹션(추론·분석·학습·팀·귀·모순)이 한 번에 떠!

### 다른 말 시키기 — 작업 칸만 바꿔서 ▶ 실행

| 작업 칸에 써 | 결과 |
|---|---|
| `C2 찾아줘` | 예측 C2 |
| `취약점 찾아줘` | 예측 vuln |
| `악성코드 분석기 만들어줘` | + 5블록 설계 |
| `4명 조합으로 분석해줘` | 다빈치+퀴리+튜링+오일러 12문장 |

### 끄기/켜기

* 끄기: 까만 창 `Ctrl + C`
* 켜기: `python ui/server.py` → `http://127.0.0.1:8090` 다시

### 코딩도 가능 — 까만 창에 아래 치기 (선택)

```bash
python -c "from tools.ghidra_router import GhidraRouter; r=GhidraRouter(); print(r.dispatch('code_write', {'path':'/tmp/hello.py','content':'print(\"hello 두뇌\")'})); print(r.dispatch('code_exec', {'cmd':'python /tmp/hello.py'}))"
```

* `hello 두뇌` 뜨면 코딩 OK!

---

## 자주 묻는 질문 — 12살 Q&A

**Q: Ghidra 설치해야 돼?** A: 아니! `verify_local.py --mock-ghidra`로 3/3 PASS. 나중에 하고 싶으면 https://ghidra-sre.org/ 에서 설치 후 `Ghidra/RuntimeScripts/support/analyzeHeadless` 쓰면 돼.

**Q: 돈 들어?** A: 0원. LLM은 `config/models.yaml` 무료 모델(qwen3:14b) 빌리고, 기억(100 sessions)은 네 컴퓨터에만 저장.

**Q: 더 똑똑해져?** A: 응! `python tools/generate_100sessions.py` 치면 100개 쌓여서 `ml/learn.py`가 100% PASS로 진화해. 분석할수록 똑똑해지는 게 네 두뇌의 핵심!

**Q: 망가뜨리면?** A: `git checkout v1.0` 치면 v1.0으로 돌아와. 안전한 저장점이야.

**Q: 뭐가 들어있어?** A: `COMPLETE.md` 1개만 읽으면 29실험 타임라인 전부 보여! `FOR_KIDS.md`는 이 가이드의 자세한 버전.

---

## 확인 체크리스트 — 네 집에서 이게 뜨면 성공!

```
cd examples/GhidraClaudeCode-Brain
python verify_local.py --all --mock-ghidra
→ VERIFY: 3/3 PASS

python -c "import ml.learn; print(ml.learn.train())"
→ {'ok': True, 'accuracy': 1.0, 'total': 100, 'insight': '100개로 학습 → 정확도 100% PASS'}

python tools/real_binary.py
→ /bin/ls 10 GLIBC, 1 ELF sig, 114 imports 100% PASS
```

축하해! 이제 네 두뇌는 Arena(빌린 사물함)에서도, 네 집(내 사물함)에서도 똑같이 일한다 — 모델은 빌리고 두뇌는 소유!
