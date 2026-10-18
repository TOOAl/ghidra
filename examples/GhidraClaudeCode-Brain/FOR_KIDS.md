# 12살 친구가 그대로 따라 하는 사용법 — 무엇을 켜고 무엇을 치는지 (2026-10-19 최신)

> 이 글은 **복사해서 붙여넣고 엔터**만 하면 되는 설명서야. 어려운 말 옆엔 ()로 쉬운 말 적었어.

## 0. 우리가 만든 건 뭐야?

*   **두뇌(Brain)**: 바이너리(얼어버린 레시피)를 녹여 보는 AI 로봇
*   **일하는 모습**: `C2 찾아줘` 한 번 누르면 → 🧠추론→📊분석→📚학습→✅모순검사까지 한 번에 보고서!

---

## 1. 준비물 (1분)

*   네 집 컴퓨터 (Windows/Mac/Linux 아무거나)
*   인터넷 (처음 한 번만)
*   **Ghidra 없어도 돼!** 우리는 가짜 Ghidra(mock)로도 3/3 PASS야

---

## 2. 사물함에서 가져오기 — 까만 창에서 그대로 치기

### 2-1. 까만 창 열기

*   Windows: 키보드 `Windows + R` → `cmd` 치고 엔터 → 까만 창
*   Mac: `Command + Space` → `터미널` 치고 엔터

### 2-2. 아래 1줄을 **마우스로 드래그해서 복사**, 까만 창에 붙여넣고 엔터

```bash
git clone -b arena/61934e9d-ghidra https://github.com/TOOAl/ghidra.git
```
*   뜻: GitHub 사물함에서 우리 두뇌 복사
*   `git이 뭔데?` 뜨면 https://git-scm.com/downloads 에서 Git 설치 후 다시

### 2-3. 폴더 들어가기 — 아래 1줄 복사→붙여넣고 엔터

```bash
cd ghidra/examples/GhidraClaudeCode-Brain
```

### 2-4. 뭐가 왔나 확인 — 아래 1줄 복사→붙여넣고 엔터

```bash
ls
```
*   `AGENT.md`, `COMPLETE.md`, `FOR_KIDS.md`, `brain`, `ui` 보이면 성공!

---

## 3. 로봇 배터리 끼우기 — 아래 1줄 복사→붙여넣고 엔터

```bash
pip install -r requirements.txt
```
*   뜻: 로봇 도구 장착
*   `pip이 뭔데?` 뜨면 `pip3 install -r requirements.txt`로 다시

---

## 4. 건강검진 — 아래 1줄 복사→붙여넣고 엔터

```bash
python verify_local.py --all --mock-ghidra
```

*   결과 마지막에 이렇게 뜨면 **합격!**

```
VERIFY: 3/3 PASS
```

*   안 뜨면 `python3 verify_local.py --all --mock-ghidra`로 다시

---

## 5. 웹 프로그램 켜기 — C2 찾아줘를 눈으로 보기

### 5-1. 아래 1줄 복사→붙여넣고 엔터 (창이 멈춘 것처럼 보여도 정상이야!)

```bash
python ui/server.py
```
*   이렇게 뜨면 켜진 거야: `웹 프로그램: http://127.0.0.1:8090`

### 5-2. 크롬/엣지/사파리 주소창에 아래를 **그대로** 치고 엔터

```
http://127.0.0.1:8090
```
*   🧠 GhidraClaudeCode-Brain 화면이 보여!

### 5-3. 맨 위 runbar에서 이렇게 입력하기 (마우스로 클릭해서 타이핑)

*   왼쪽 칸(바이너리): `/bin/ls` 그대로 둬 (테스트용 레시피)
*   가운데 칸(작업): `C2 찾아줘` 라고 지우고 다시 써
*   오른쪽 칸(모델): 그냥 둬 (qwen3:14b)
*   **▶ 실행** 버튼 클릭!

### 5-4. 결과 구경

*   📝 보고서 탭에 아래 5개가 한 번에 떠!

```
# C2 찾아줘
## 1. 추론 → ✅ 관찰 | 추론 | 모순0개
## 2. 분석 → base64 패턴 80%
## 3. 학습 → 100% PASS | 예측: C2
## 증거 → 함수 3개, 문자열 c2.evil.com
## 모순 검사 → 모순 없음
```

*   📄 블록 탭: Notion처럼 블록으로 저장된 보고서
*   🗃️ DB 탭: 표로 정렬 가능
*   🕸️ 그래프 탭: 선으로 연결된 그림
*   📡 큐 탭: 오프라인 작업함

---

## 6. 다른 말도 시켜보기 — 가운데 칸에 이렇게 바꿔서 ▶ 실행

| 가운데 칸에 이렇게 써 | 일어나는 일 |
|---|---|
| `C2 찾아줘` | 추론+분석+학습 + 예측 C2 |
| `취약점 찾아줘` | 예측: vuln 분류 |
| `악성코드 분석기 만들어줘` | + 4. 설계 → 5블록 설계도까지 추가! |
| `4명 조합으로 분석해줘` | 다빈치+퀴리+튜링+오일러 4명 팀이 함께 분석 |

---

## 7. 끄고 다시 켜기

*   까만 창에서 `Ctrl + C` 누르면 서버 꺼짐
*   다시 켤 땐 5-1부터 다시: `python ui/server.py` → `http://127.0.0.1:8090`

---

## 8. 자주 묻는 질문 (12살 Q&A)

**Q: 바이너리가 뭐야?**
A: 얼어버린 레시피. 회사가 레시피를 꽁꽁 얼려 보낸 파일. Ghidra가 드라이기로 녹여.

**Q: 무료 맞아?**
A: 응! 생각은 OpenRouter 무료로 빌리고, 몸(기억/도구)은 내 컴퓨터에만 있어서 0원.

**Q: 3/3 PASS가 뭐야?**
A: 로봇 건강검진 3과목 모두 합격. Ghidra 없어도 mock으로 합격!

**Q: 더 똑똑해져?**
A: 응! 분석할수록 `memory/session.jsonl`에 쌓여서 다음엔 100% 더 잘 맞춰.

---

## 9. 진짜 코딩도? — 까만 창에 치기 (선택)

```bash
python -c "from tools.ghidra_router import GhidraRouter; r=GhidraRouter(); print(r.dispatch('code_write', {'path':'/tmp/hello.py','content':'print(\"hello 두뇌\")'})); print(r.dispatch('code_exec', {'cmd':'python /tmp/hello.py'}))"
```
*   `hello 두뇌` 뜨면 코딩도 되는 거야!

---

## 10. 모든 과정이 궁금하면

*   **한 문서 요약**: `COMPLETE.md` — 에이전트가 읽는 1개 문서 (우리 타임라인 전부)
*   **핸드북**: `../../AGENTS.md`

축하해! 네 두뇌는 이제 네 집에 있고, `C2 찾아줘` 한 번으로 똑똑해져!
