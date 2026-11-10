---
title: "자가 치유 끈기 원장 — kill -9 를 견디는 퀘스트 기억 (quest_ledger)"
category: "스킬·끈기"
tags: [skill, persistence, quest, crash-safe, atomic]
created: ""
---

# 🧭 자가 치유 끈기 원장 — kill -9 를 견디는 퀘스트 기억

## 💡 핵심 요약
"오래 달리는 일을 하다가 전원이 뽑혀도, 다시 켜면 **멈춘 그 자리**에서
이어서 끝낸다." — Fable 류 장기 에이전트의 끈기를 **외부 모델 없이** 두뇌
자신의 것으로 재주조했어요 (`brain_engine/quest_ledger.py`). 비결은
기억을 머리가 아닌 **디스크에 원자로** 적는 것: `state/quests.json` 에
tmp 파일 + `os.replace()` 로 써서, 쓰다 죽어도 파일은 항상 온전해요.

## 🔩 세 규칙 (brain_engine/quest_ledger.py · quest_runners.py)
1. **스텝 = 효과 → 체크포인트**: 각 스텝은 먼저 *멱등 효과*를 내고, 그
   뒤에 `checkpoint(next_index)` 로 진도를 디스크에 새겨요. 효과가 먼저,
   기록이 나중 — 그래서 어디서 죽어도 "기록된 인덱스"는 항상 참.
2. **재개 = 기록된 인덱스부터**: `resume_all()` 이 기동 시 `active` 퀘스트를
   찾아 `step_index` 부터 이어요. 이미 낸 효과는 멱등이라 다시 내도
   관측이 두 번이 되지 않아요.
3. **러너 레지스트리**: `@runner("kind")` 로 퀘스트 종류별 스텝 의미를
   등록해요 (markers·craft·chain). 러너가 터지면 좀비(active 영원)로
   두지 않고 정직하게 `failed` + 오류를 proof 로 기록.

## 📈 실측 (kill -9 기계 증명)
- markers 퀘스트(스텝 4, 각 스텝 후 4초 지연) 실행 중 **step 2/4 에서
  `kill -9`** → `quests.json` 은 `active·step_index=2` 로 동결, markers.log 는
  `s1,s2` 까지만.
- 재기동 → `resume_all()` 이 3·4 스텝을 이어서 → **done·step 4/4**,
  markers.log `s1,s2,s3,s4` **각각 정확히 1회** (중복 0).
- craft 퀘스트도 같은 원장으로 end-to-end: xor_vault 두 함수 256 전수 100%.

## 🧭 한계 (정직 고지)
원장은 **이 드라이브의 파일시스템**에 살아요 — git 에 커밋하지 않아요
(`state/.gitignore`). 끈기는 "같은 두뇌가 다시 켜질 때"의 것이지, 다른
기계에 복제되는 것이 아니에요. `os.replace` 는 POSIX 원자성을 따르므로
같은 기계·같은 드라이브에서만 보장돼요.

## 🔗 연결된 시냅스 (Wiki Links)
- [[자가 복제 공작 루프 — craft-anything 두뇌 판 (clean-room)]]
- [[증거 사슬 다홉 추론 — 인용되거나 침묵하거나 (chain_reasoner)]]
