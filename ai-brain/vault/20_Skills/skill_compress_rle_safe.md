---
title: "자가 진화 스킬 카트리지 — compress_rle_safe"
category: "초소형뇌·양자화"
tags: [자가진화공방, 스킬카트리지, 유리방검증, compress_rle_safe]
created: "2026-11-09 13:37 UTC"
---

# 자가 진화 스킬 카트리지 — compress_rle_safe

#자가진화공방 #스킬카트리지 #유리방검증 #compress_rle_safe

## 💡 핵심 요약
원인 역추적 돋보기와 복어 독 제거기를 거쳐 투명 유리방 쌍둥이 검증(6/6 100%)을 통과한 두뇌 영구 장착 스킬입니다.

## 📌 주요 포인트
- 장착 파이썬 모듈: `skills/skill_compress_rle_safe.py`
- 4비트 신경 캡슐: `models/evo_skill_compress_rle_safe_int4.sbrain`
```python
def compress_rle_safe(stream):
    """수리 완료: 복어 독(os.system) 완전 제거 + 빈 배열 방어 + 255 상한 보존"""
    if not stream:
        return []
    out = []
    cur = int(stream[0]) & 0xFF
    count = 1
    for raw_b in stream[1:]:
        b = int(raw_b) & 0xFF
        if b == cur and count < 255:
            count += 1
        else:
            out.extend([count, cur])
            cur = b
            count = 1
    out.extend([count, cur])
    return out
```

## 🔗 연결된 시냅스 (Wiki Links)
- [[역공학 해부 도감 — 🐡 복어 독(위험 명령) 혼입 압축기 (보안 제거 실습)]]
- [[다수 작은 심판 합의형 CPU 강화학습 (Good Judges)]]
- [[자가 진화 스킬 카트리지 — transform_payload]]
- [[역공학 해부 도감 — 🔐 XOR-회전 금고 해독기 (ELF64 x86-64)]]
- [[자가 진화 스킬 카트리지 — pack_nibbles]]
- [[자가 진화 스킬 카트리지 — parity_guard]]
- [[역공학 해부 도감 — 🔁 델타 흐름 압축기]]
- [[자가 진화 스킬 카트리지 — delta_encode]]
- [[역공학 해부 도감 — 🛰️ 수 패리티 수호기]]
- [[역공학 해부 도감 — 🧩 니블 팩커 (4비트 쌍수납 저장소)]]
