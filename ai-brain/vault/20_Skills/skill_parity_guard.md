---
title: "자가 진화 스킬 카트리지 — parity_guard"
category: "초소형뇌·양자화"
tags: [자가진화공방, 스킬카트리지, 유리방검증, parity_guard]
created: "2026-11-10 13:59 UTC"
---

# 자가 진화 스킬 카트리지 — parity_guard

#자가진화공방 #스킬카트리지 #유리방검증 #parity_guard

## 💡 핵심 요약
원인 역추적 돋보기와 복어 독 제거기를 거쳐 투명 유리방 쌍둥이 검증(6/6 100%)을 통과한 두뇌 영구 장착 스킬입니다.

## 📌 주요 포인트
- 장착 파이썬 모듈: `skills/skill_parity_guard.py`
- 4비트 신경 캡슐: `models/evo_skill_parity_guard_int4.sbrain`
```python
def parity_guard(bytes_in):
    """수리 완료: 복어 독 제거 + 정확한 짝수 패리티 보정"""
    if not bytes_in:
        return []
    guard = []
    for b in bytes_in:
        ones = bin(int(b) & 0xFF).count('1')
        guard.append(ones % 2)
    return guard
```

## 🔗 연결된 시냅스 (Wiki Links)
- [[역공학 해부 도감 — 🛰️ 수 패리티 수호기]]
- [[다수 작은 심판 합의형 CPU 강화학습 (Good Judges)]]
