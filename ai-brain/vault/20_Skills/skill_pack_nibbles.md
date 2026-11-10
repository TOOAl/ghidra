---
title: "자가 진화 스킬 카트리지 — pack_nibbles"
category: "초소형뇌·양자화"
tags: [자가진화공방, 스킬카트리지, 유리방검증, pack_nibbles]
created: "2026-11-10 13:44 UTC"
---

# 자가 진화 스킬 카트리지 — pack_nibbles

#자가진화공방 #스킬카트리지 #유리방검증 #pack_nibbles

## 💡 핵심 요약
원인 역추적 돋보기와 복어 독 제거기를 거쳐 투명 유리방 쌍둥이 검증(6/6 100%)을 통과한 두뇌 영구 장착 스킬입니다.

## 📌 주요 포인트
- 장착 파이썬 모듈: `skills/skill_pack_nibbles.py`
- 4비트 신경 캡슐: `models/evo_skill_pack_nibbles_int4.sbrain`
```python
def pack_nibbles(vals):
    """수리 완료: 니블 순서 정위치 + 홀수 길이 0 패딩 방어"""
    if not vals:
        return []
    out = []
    for i in range(0, len(vals), 2):
        hi = vals[i] & 0x0F
        lo = vals[i + 1] & 0x0F if i + 1 < len(vals) else 0
        out.append((hi << 4) | lo)
    return out
```

## 🔗 연결된 시냅스 (Wiki Links)
- [[역공학 해부 도감 — 🧩 니블 팩커 (4비트 쌍수납 저장소)]]
- [[다수 작은 심판 합의형 CPU 강화학습 (Good Judges)]]
- [[자가 진화 스킬 카트리지 — compress_rle_safe]]
- [[자가 진화 스킬 카트리지 — transform_payload]]
