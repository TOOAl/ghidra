# DEMO — 하이브리드 + 쓰기 플러그인 완성 데모

이 문서는 "외부 LLM(무료) + 로컬 두뇌 + 쓰기 플러그인"이 합쳐진 최종 형태를 보여줌.

## 1. Mock 쓰기 테스트 (Ghidra 없이도 가능)

```bash
cd examples/GhidraWritePlugin
python test_write_plugin.py --mock
```

출력:
```
→ rename_function({"old_name": "FUN_00401000", "new_name": "decrypt_config"})
← {"ok": true, "old": "FUN_00401000", "new": "decrypt_config"}
  [로컬 기억] memory/session.jsonl 에 쓰기 이력 저장 → 다음 분석 때 재사용
```

## 2. 전체 하이브리드 데모 (외부 LLM mock + 로컬 쓰기 mock)

```bash
cd examples/GhidraClaudeCode-Brain
python demo_hybrid_openrouter.py --binary /bin/ls
# → 외부 LLM(무료) 6턴 + 로컬 Ghidra/기억 + 쓰기 제안까지 포함된 보고서
```

## 3. 진짜 Ghidra에서 쓰기 (실제 DB 변경)

### A. 플러그인 설치
```bash
cp -r examples/GhidraWritePlugin Ghidra/Extensions/GhidraWritePlugin
gradle buildExtension -PExtensionName=GhidraWritePlugin
# Ghidra GUI: File > Install Extensions > + > dist/*.zip > 재시작
```

또는 빌드 없이 스크립트로 먼저 테스트:
```
Ghidra > Script Manager > Add Directory > examples/GhidraWritePlugin/ghidra_scripts
> RenameWithLLM.py 실행
```

### B. Ghidra 켜고 Brain 실행
```bash
# Ghidra CodeBrowser에서 바이너리 열기 (플러그인이 127.0.0.1:8089에서 대기)

# 터미널 1: 플러그인 확인
curl http://127.0.0.1:8089/health
# → {"status":"ok","plugin":"GhidraWritePlugin","port":8089}

# 터미널 2: Brain 실행 (외부 무료 LLM + 로컬 쓰기)
export OPENROUTER_API_KEY=sk-or-v1-...
python run.py --binary ./sample.exe --task "C2 찾아서 이름 복구하고 주석 달아줘" --preset openrouter_free_generic
# 또는
python demo_hybrid_openrouter.py --binary ./sample.exe --real

# 결과: Ghidra 화면에서 FUN_00401000 → decrypt_config 로 실시간 변경 확인!
```

### C. 쓰기 테스트
```bash
cd examples/GhidraWritePlugin
python test_write_plugin.py --url http://127.0.0.1:8089
# POST /rename_function, POST /set_comment 가 실제 Ghidra DB에 반영
```

## 완성된 구조

```
외부 LLM (OpenRouter qwen3:32b:free, 0원)
   ↓ Tool Call
로컬 Brain (agent.py)
   ↓ HTTP POST
GhidraWritePlugin (127.0.0.1:8089, 로컬 전용)
   ↓ startTransaction / endTransaction
Ghidra Program DB (진짜로 바뀜)
   ↓ 저장
memory/session.jsonl + memory/chroma_db (로컬 영구 기억)
```

이제 "읽기+쓰기+여러 포맷" 완성. 다음 모델이 나와도 config/models.yaml 한 줄 변경으로 진화.
