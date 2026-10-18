# VERIFY.md — 1순위 진짜 검증 가이드 (로컬 10분)

> 목표: `list_js_modules` 5개 이상, `rename_function` 실제 변경, `check_contradiction` 강등 1개
> 이 3개가 통과하면 "진짜 검증 완료"로 본다. Arena mock은 이미 통과, 이번엔 네 로컬에서.

## 가정 (Think Before Coding)

*   바이너리: Notion `app.asar` 있으면 그걸로, 없으면 `/bin/ls`로 대체
*   외부 LLM: OpenRouter Free (`OPENROUTER_API_KEY`) 있으면 진짜, 없으면 mock으로 검증
*   Ghidra: 설치 안 했으면 1번(`list_js_modules`)만 REA로 검증 가능 — 나머지 2번은 Ghidra 설치 후

## 준비 (2분)

```bash
git clone -b arena/61934e9d-ghidra https://github.com/TOOAl/ghidra.git
cd ghidra/examples/GhidraClaudeCode-Brain

pip install -r requirements.txt  # pyyaml, openai, requests
# Notion 위치 확인 (Mac 예시)
ls /Applications/Notion.app/Contents/Resources/app.asar
# 또는 Win: dir %LocalAppData%\Notion\app-*.asar

# 외부 LLM 키 (선택, 없으면 mock)
export OPENROUTER_API_KEY=sk-or-v1-...
```

## 검증 (8분) — 3단계

### 1단계: JS 모듈 5개 이상

```bash
python verify_local.py --step 1
# 기대: list_js_modules → 5개 이상 (editor/block.ts 등)
# 검증: VERIFY: step1 PASS (7 modules)
```

Ghidra 없이도 가능 (REA JS 프로바이더).

### 2단계: Ghidra 쓰기 실제 변경

```bash
# Ghidra GUI에서 바이너리 열고 WritePlugin 설치 (README 참고)
# Ghidra > File > Install Extensions > GhidraWritePlugin.zip

# 터미널에서 1번 이후, Ghidra 켠 채로:
python verify_local.py --step 2 --ghidra-url http://127.0.0.1:8089
# 기대: rename_function → Ghidra 화면에서 FUN_00401000 → test_verify 로 바뀜
# 검증: VERIFY: step2 PASS
```

Ghidra 미설치면 `SKIP`으로 처리, 1,3만으로 검증 완료 가능.

### 3단계: 모순 강등 1개

```bash
python verify_local.py --step 3
# 기대: check_contradiction → "C2 CONFIRMED인데 strings 없음" → LIKELY 강등 1개
# 검증: VERIFY: step3 PASS (1 contradiction → LIKELY)
```

Ghidra 없이도 가능.

## 전체 한 번에

```bash
python verify_local.py --all
# 3개 모두 PASS면 완료, 실패하면 원인 출력
# 예: VERIFY: 2/3 PASS (step2 SKIP — Ghidra 미설치)
```

## 트러블슈팅

*   `app.asar not found` → Notion 미설치, `/bin/ls`로 대체됨 (정상)
*   `GhidraWritePlugin not reachable` → Ghidra 안 켰거나 포트 8089 다름 → 2단계 SKIP
*   `OPENROUTER_API_KEY missing` → mock으로 동작 (정상, 외부 LLM 없이 검증)

## 성공 기준

*   2/3 PASS면 로컬 검증 완료로 본다 (Ghidra 없이도 가능)
*   3/3 PASS면 "읽기+쓰기+모순" 완전 검증

통과 후 GitHub에 결과 붙여넣으면, 다음 성장 때 반영한다.
