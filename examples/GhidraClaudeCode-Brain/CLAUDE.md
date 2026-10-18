# CLAUDE.md — 이 두뇌(Brain)를 위한 가이드

> 상위 `/CLAUDE.md`를 상속 + 이 폴더 전용 규칙

## 이 폴더에서 작업할 때

1. **코딩 전 생각하기**
   - "새 도구/스킬을 추가한다" → 가정: 사용자가 정말 쓸 것이다. → 질문: 지금 당장 필요한가, 아니면 다음 분석에서 필요할 때 추가할까?

2. **단순함 우선**
   - 도구 11개 중 이번 작업에 필요한 것만 건든다. 나머지는 mock 유지.
   - `demo_*.py`는 50줄 이내로. 200줄 데모는 다시 쓴다.

3. **외과적 변경**
   - `brain/agent.py` 루프는 건드리지 않는다. 새 기능은 `tools/`와 `skills/`에만 추가.
   - `GhidraWritePlugin`은 새 엔드포인트만 추가, 기존 엔드포인트 수정 금지.

4. **목표 중심**
   - 모든 PR은 검증 명령을 포함:
     ```
     1. skills/unpack_upx.md 추가 → 검증: python demo_growth.py 에 unpack_upx 스킬 표시
     2. patch_bytes 도구 추가 → 검증: python test_write_plugin.py --mock 에서 patch ok:true
     ```

## 현재 성공 기준 (다음 PR까지)

- [ ] skills 4개가 `demo_growth.py`에서 모두 표시
- [ ] tools 11개가 `definitions.json`에 있고, mock 5개가 ok
- [ ] WritePlugin 8개 엔드포인트가 `test_write_plugin.py --mock` 통과
- [ ] `git push` 후 GitHub 브랜치에서 폴더 보임

이 4개가 모두 통과하면 성장 완료로 본다.
