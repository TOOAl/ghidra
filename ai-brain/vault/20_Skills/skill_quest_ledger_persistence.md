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
   등록해요 (markers·craft·chain·**garden**). 러너가 터지면 좀비(active 영원)로
   두지 않고 정직하게 `failed` + 오류를 proof 로 기록.

## 🛡 끈기의 세 적(敵) (심화 — 회복력)
kill -9 만으로는 부족해요. 원장을 훼손하는 세 경로를 모두 막아요:
1. **concurrent (동시 저장)** — `resume_all` 스레드와 POST 퀘스트 스레드가
   동시에 `_save()` 하면 같은 tmp 를 찢거나 "dict changed size" 가 나요.
   → `RLock` 으로 mutate+save 를 직렬화하고, `begin` 의 qid 를
   같은-밀리초 충돌까지 유일하게 보장.
2. **corrupt (원장 훼손)** — `_load` 가 나쁜 JSON 을 **지우지 않고 격리**
   (`quests.corrupt-<ts>.json` 로 `os.replace`) 후 `recovered` 기록과 함께
   빈 상태로 정직 재기동. 증거를 남기지 않는 조용한 초기화 금지.
3. **disk-full (저장 실패)** — `_save` 는 tmp 에 쓰고 **`fsync`** 한 뒤
   `os.replace`(원자+내구). 실패 시 `SaveError` 를 표면화하고 tmp 만
   청소·본파일은 마지막 좋은 상태로 보존(발명 금지). 크래시가 남긴
   미완성 tmp 는 다음 `_load` 가 자동 청소.

## 🌱 garden 퀘스트 (정원 가꾸기도 원장으로)
`reindex → semantic train → report` 를 끈기 있게. 러너는 자가완결이라
payload 의 경로(vault·db)로 `WikiGardener` 를 **재구성**해요(원장은 JSON 이라
라이브 객체를 못 실음). 각 스텝 멱등 — 다시 돌려도 같은 인덱스/의미공간으로 수렴.

## 📈 실측 (기계 증명 — tools/test_quest_resilience.py, 32/32)
- **kill -9**: markers(4스텝·스텝당 4초)를 step 2/4 에서 `kill -9` → 동결
  (`active·index=2`, markers.log `s1,s2`) → 재기동 `resume_all` → **done·4/4**,
  markers.log `s1,s2,s3,s4` **각 정확히 1회**(중복 0). hardened(lock+fsync)로도 동일.
- **동시성**: 12 스레드 × 5 체크포인트 → 오류 0·qid 충돌 0·원장 온전(전부 done·log 유실 0).
- **격리**: 훼손 원장 → 빈 재기동 + `quests.corrupt-*` 에 원본 보존 + `recovered.reason`.
- **디스크 가득**: `os.replace` ENOSPC 주입 → `SaveError`·tmp 청소·본파일=마지막 좋은 상태.
- **garden**: 라이브 `POST /api/quests {"kind":"garden"}` → 35 노트 reindex·vocab 500·fidelity 99.996%.
- craft 퀘스트도 같은 원장으로 end-to-end: xor_vault 두 함수 256 전수 100%.

## 🧭 한계 (정직 고지)
원장은 **이 드라이브의 파일시스템**에 살아요 — git 에 커밋하지 않아요
(`state/.gitignore`). 끈기는 "같은 두뇌가 다시 켜질 때"의 것이지, 다른
기계에 복제되는 것이 아니에요. `os.replace`+`fsync` 는 POSIX 원자·내구성을
따르므로 같은 기계·같은 드라이브에서만 보장돼요. `recovered` 는 훼손을
숨기지 않지만, 격리된 옛 퀘스트를 자동으로 되살리지는 않아요(사람 판단).

## 🔗 연결된 시냅스 (Wiki Links)
- [[자가 복제 공작 루프 — craft-anything 두뇌 판 (clean-room)]]
- [[증거 사슬 다홉 추론 — 인용되거나 침묵하거나 (chain_reasoner)]]
