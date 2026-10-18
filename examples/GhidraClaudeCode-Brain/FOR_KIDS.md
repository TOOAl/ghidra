# 로컬로 옮기고 실행하는 방법 — 12살 친구에게

> 이 글은 12살 친구도 따라 할 수 있게 쓴 설명서야. 어려운 단어는 옆에 쉽게 풀어놨어.

## 0. 우리가 만든 건 뭐야?

*   **두뇌(Brain)**: 네 컴퓨터 안에서 바이너리(얼어버린 레시피)를 녹여서 읽는 AI 로봇
*   **외부 LLM(무료)**: 로봇의 생각 CPU — OpenRouter 무료로 빌림
*   **기억/스킬**: 로봇이 배운 걸 저장하는 공책

## 1. 왜 Arena에서 바로 안 보였을까?

Arena는 **학교 컴퓨터** 같은 임시 컴퓨터야. 전원을 끄면 사라져.
그래서 우리가 GitHub라는 **클라우드 사물함**에 백업해뒀어.

```
/home/user/ghidra/  → 학교 컴퓨터 (임시, 너는 못 봄)
/AGENTS.md          → 클라우드 사물함 (GitHub, 너는 볼 수 있음)
```

## 2. 로컬로 옮기기 (3분) — 사진 찍듯이 따라 해

### 2-1. 사물함에서 가져오기

1.  네 진짜 컴퓨터(집 컴퓨터)에서 **터미널**(까만 화면) 켜기
2.  아래 한 줄 복사해서 붙여넣고 엔터:

```bash
git clone -b arena/61934e9d-ghidra https://github.com/TOOAl/ghidra.git
```

*   `git clone` = 사물함에서 내 책상 위로 복사
*   `-b arena/61934e9d-ghidra` = 우리가 쓰던 사물함 칸 이름

3.  끝나면 이렇게 쳐:

```bash
cd ghidra/examples/GhidraClaudeCode-Brain
ls
# → AGENT.md, brain, memory 같은 폴더가 보이면 성공!
```

### 2-2. 로봇 배터리 끼우기

```bash
pip install -r requirements.txt
```

*   `pip install` = 로봇이 쓰는 도구(망치, 돋보기) 장착

### 2-3. 무료 생각 CPU 빌리기 (1분)

1.  https://openrouter.ai 접속 → 로그인 → https://openrouter.ai/settings/keys → Create Key
2.  키 복사 (sk-or-v1-...)

```bash
export OPENROUTER_API_KEY=sk-or-v1-...네키...
```

*   `export` = "이제부터 이 키로 생각 CPU 빌릴게"라고 선언

없어도 돼! 없으면 로봇이 혼자 생각(mock)해서 보여줘.

## 3. 실행하기 — 버튼 누르기

### 3-1. 로봇이 일하는지 테스트 (2분)

```bash
python verify_local.py --all --mock-ghidra
```

*   `verify_local.py` = 로봇 건강검진
*   결과에 `VERIFY: 3/3 PASS` 뜨면 건강한 거야!

### 3-2. 진짜 분석 시키기 (3분)

```bash
python run.py --binary /bin/ls --task "4명 조합으로 분석해줘" --preset openrouter_free_generic
```

*   `--binary /bin/ls` = 분석할 얼어버린 레시피 (ls는 파일 목록 보여주는 버튼)
*   `--task` = 로봇에게 시키는 말
*   `--preset` = 어떤 생각 CPU 쓸지 (무료 qwen3)

로봇이 이렇게 일해:

```
1. 외부 LLM에게 물어봄: "다음에 뭘 할까?" (생각은 외부 무료)
2. 로컬에서 실행: list_functions (눈은 로컬)
3. 기억 저장: memory/*.jsonl (기억은 로컬에만 남음)
```

### 3-3. Notion/Obsidian UI 보기 (1분)

```bash
python ui/server.py
```

브라우저에서 `http://127.0.0.1:8090` 들어가면:

*   📄 블록: Notion처럼 분석 결과가 블록으로 보여
*   🗃️ DB: 표로 필터/정렬 가능
*   🕸️ 그래프: Obsidian처럼 블록들이 선으로 연결

## 4. 자주 묻는 질문 (12살 Q&A)

**Q: 바이너리가 뭐야?**
A: 얼어버린 레시피. 게임 회사가 레시피를 꽁꽁 얼려서 보내준 거. Ghidra가 드라이기로 녹여서 보여줘.

**Q: 왜 외부 LLM은 무료야?**
A: OpenRouter가 무료 모델을 빌려줘. 생각만 외부에서 빌리고, 몸(도구/기억)은 내 컴퓨터에 있어서 공짜로 계속 커져.

**Q: GhidraWritePlugin은 뭐야?**
A: 로봇의 손. 분석 결과 "이 함수 이름 바꿔!" 하면 Ghidra 화면에서 진짜로 바뀌게 해주는 손.

**Q: 4명 천재는 뭐야?**
A: 로봇에게 "다빈치처럼 관찰해!" 하면 스케치하고, "퀴리처럼 측정해!" 하면 숫자로 기록하는 특별한 안경 4개.

## 5. 다음에 할 일

*   네가 Ghidra를 설치하면 2단계(쓰기)도 3/3 PASS가 돼
*   Notion app.asar가 있으면 `python verify_local.py --step 1`로 Notion도 분석 가능
*   다 컸으면 UI에서 블록들을 구경하면 돼!

축하해! 이제 네 두뇌는 네 집 컴퓨터에 있어!
