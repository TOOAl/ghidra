# GhidraWritePlugin — 쓰기 플러그인 (rename_function / set_comment)

> GhidraClaudeCode-Brain의 **쓰기 손**을 완성하는 플러그인
> 외부 LLM(무료) + 로컬 두뇌가 Ghidra DB에 직접 쓰고, 그 결과를 기억으로 저장하는 마지막 퍼즐

## 왜 필요?

- REA만 쓰면 **읽기 전용** (pseudocode 보기만 가능)
- 이 플러그인을 설치하면 **쓰기 가능**: `rename_function`, `set_comment`, `set_plate_comment`, `create_label`
- GhidraClaudeCode-Brain의 `tools/ghidra_router.py`가 이 플러그인의 HTTP 서버를 호출

```
외부 LLM (OpenRouter 무료, 생각만)
   ↓ MCP / Tool Call
로컬 Brain (agent.py, 루프 운전)
   ↓ HTTP POST http://127.0.0.1:8089/rename_function
GhidraWritePlugin (이 플러그인, Ghidra CodeBrowser 안에서 실행)
   ↓ Program API (트랜잭션)
Ghidra Program DB (함수명/주석이 진짜 바뀜)
   ↓ 저장
memory/chroma_db (로컬 기억) — 다음 분석 때 재사용
```

## 설치 (2분)

### 방법 A: 소스에서 빌드 (개발자)

```bash
# Ghidra 소스 루트에서
cp -r examples/GhidraWritePlugin Ghidra/Extensions/GhidraWritePlugin
# 또는 심볼릭 링크: ln -s $(pwd)/examples/GhidraWritePlugin Ghidra/Extensions/GhidraWritePlugin

gradle buildExtension -PExtensionName=GhidraWritePlugin
# 결과: Ghidra/Extensions/GhidraWritePlugin/dist/ghidra_*-GhidraWritePlugin.zip

# Ghidra GUI에서: File > Install Extensions > + > 위 zip 선택 > 재시작
```

### 방법 B: 수동 복사 (빌드 없이 테스트)

Eclipse나 IntelliJ 없이도 `ghidra_scripts` 폴더에 있는 스크립트 버전으로 먼저 테스트 가능:

```bash
# Ghidra CodeBrowser > Window > Script Manager > Add Script Directory
# examples/GhidraWritePlugin/ghidra_scripts 를 추가
# RenameWithLLM.py 를 실행하면 같은 효과 (플러그인 없이도 쓰기 가능)
```

## 사용

1. Ghidra CodeBrowser에서 바이너리 열기
2. Tool Options > GhidraWritePlugin 에서 포트 확인 (기본 8089)
3. 터미널에서 Brain 실행:

```bash
export OPENROUTER_API_KEY=sk-or-v1-...
python examples/GhidraClaudeCode-Brain/run.py \
  --binary ./sample.exe \
  --task "FUN_00401000이 뭔지 이름 복구하고 주석 달아줘" \
  --preset openrouter_free_generic

# 또는 하이브리드 데모
python examples/GhidraClaudeCode-Brain/demo_hybrid_openrouter.py --binary ./sample.exe --real
```

Brain이 `rename_function`을 호출하면, Ghidra 화면에서 함수명이 실시간으로 바뀌는 걸 볼 수 있음.

## API

플러그인은 로컬에서만 듣는 HTTP 서버 (127.0.0.1:8089, 인증 없음 — 로컬 전용)

| Endpoint | Method | Body | 설명 |
|---|---|---|---|
| `/health` | GET | - | 플러그인 살아있는지 확인 |
| `/rename_function` | POST | `{"old_name": "FUN_00401000", "new_name": "decrypt_config"}` | 함수명 변경 (트랜잭션) |
| `/set_comment` | POST | `{"name": "FUN_00401000", "comment": "C2 통신 함수"}` | PRE_COMMENT 주석 |
| `/set_plate_comment` | POST | `{"name": "FUN_00401000", "comment": "라이선스 검증"}` | 함수 상단 plate 주석 |
| `/create_label` | POST | `{"address": "0x00401234", "label": "c2_url"}` | 라벨 생성 |
| `/list_functions` | GET | `?filter=FUN&limit=50` | 읽기 확인용 |
| `/patch_bytes` | POST | `{"address": "0x00401234", "bytes": "90 90", "comment": "nop patch"}` | 바이트 패치 (undo 가능) |
| `/get_bytes` | POST/GET | `{"address": "0x00403000", "length": 32}` | 바이트 읽기 (키 덤프) |
| `/search_bytes` | POST | `{"pattern": "63 7C 77 7B ?? ??"}` | 바이트 패턴 검색 (AES S-box 등) |
| `/list_imports` | GET/POST | `?filter=Crypt` | Import 목록 (filter 지원) |

모든 쓰기는 `program.startTransaction()` / `endTransaction(true)` 로 안전하게 처리되고, 실패 시 `endTransaction(false)`로 롤백.

## 보안

- 기본 바인딩: `127.0.0.1`만 (외부에서 접속 불가)
- Ghidra가 꺼지면 서버도 같이 꺼짐
- 쓰기 전 확인 다이얼로그 옵션: Tool Options > GhidraWritePlugin > Require confirmation

## 다음 단계

- `rename_function`에 정규식 일괄 변경: `{"pattern": "FUN_0040*", "new_pattern": "sub_{addr}"}`
- `patch_bytes` 추가: 취약점 패치 바이트 직접 쓰기 (주의 필요)
- `memory/chroma_db`에 쓰기 이력 자동 저장 → 다음 유사 함수에 자동 제안
