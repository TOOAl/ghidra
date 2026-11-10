---
title: "🛠 craft — specimen_xor_vault.elf:FUN_00400078"
category: "역공학·자가복제"
tags: [machine-output, crafted, clean-room, analyzeHeadless]
kind: "code"
created: ""
---

# 🛠 craft — specimen_xor_vault.elf:FUN_00400078

## 💡 핵심 요약
원본 바이트를 직접 실행한 에뮬레이터와 차분 테스트 **100.0%**
(256개 벡터, 전수 검증) 를 통과한 자가 복제 변환이에요.

## 🔩 합성된 변환 (Ghidra 디컴파일 C 로부터)
```python
lambda x: ((x ^ 0x5a) << 3 | (x ^ 0x5a) >> 5) + 0
```

## 🧭 출처와 방법
영감: storytold/craft-anything (MIT OR Apache-2.0) — 검사→제작→비교 루프.
우리 판은 외부 모델 없이: 검사=Ghidra(PyGhidra) · 제작=규칙 기반 C 파싱 ·
비교=원본 바이트 실행 소형 에뮬레이터. 불일치였다면 이 노트는 없었어요.
