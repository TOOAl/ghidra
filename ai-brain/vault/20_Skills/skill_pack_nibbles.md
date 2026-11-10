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
- [[자가 진화 스킬 카트리지 — parity_guard]]
- [[역공학 해부 도감 — 🔁 델타 흐름 압축기]]
- [[자가 진화 스킬 카트리지 — delta_encode]]
- [[역공학 해부 도감 — 🛰️ 수 패리티 수호기]]
- [[역공학 해부 도감 — 🔐 XOR-회전 금고 해독기 (ELF64 x86-64)]]
- [[역공학 해부 도감 — 🎚️ 데드존 양자화기]]
- [[자가 진화 스킬 카트리지 — deadzone_quant]]
- [[역공학 해부 도감 — 🐡 복어 독(위험 명령) 혼입 압축기 (보안 제거 실습)]]
- [[역공학 해부 도감 — 🗳️ 3연속 다수결 스무더]]
- [[자가 진화 스킬 카트리지 — majority_smooth]]
- [[Ghidra 헤드리스와 로컬 AI 역공학 결합]]
- [[역공학 해부 도감 — 🛡️ 8비트 합 체크섬 파수꾼]]
- [[자가 진화 스킬 카트리지 — checksum_guard]]
