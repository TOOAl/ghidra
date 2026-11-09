"""
Living Tamagotchi Brain state & evolution engine.
Maps Synapsemong's internal state and recent actions to the 8 cosmic poses:
  01_greet      - 첫 인사 / 반가운 환영
  02_curious    - 호기심 가득 대기 상태
  03_swirl      - 새 지식을 소용돌이로 흡수·분류 중
  04_brainstorm - 배고프거나 환경이 좁아 깊이 고민 중
  05_drop       - 소중한 영감 한 방울 수집
  06_star       - 시냅스 별 연결 완성!
  07_eureka     - 유레카! 질문 답변 / 양자화 두뇌 주조 성공!
  08_journey    - 진화 순항 · 최고 컨디션
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


STAGES: List[Dict[str, Any]] = [
    {"level": 1, "min_xp": 0, "key": "egg", "title": "알에서 깨어난 꼬마 뉴런", "emoji": "✦"},
    {"level": 2, "min_xp": 50, "key": "sprout", "title": "호기심 많은 아기 시냅스", "emoji": "✧"},
    {"level": 3, "min_xp": 140, "key": "scholar", "title": "노트 정리하는 학자 두뇌", "emoji": "★"},
    {"level": 4, "min_xp": 300, "key": "analyst", "title": "스스로 판단하는 연구원 두뇌", "emoji": "✪"},
    {"level": 5, "min_xp": 600, "key": "master", "title": "전설의 포터블 마스터 두뇌", "emoji": "👑"},
]


def _utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class TamagotchiSoul:
    def __init__(self, soul_path: Path) -> None:
        self.soul_path = soul_path
        self.soul_path.parent.mkdir(parents=True, exist_ok=True)
        self.data = self._load_or_create()

    def _load_or_create(self) -> Dict[str, Any]:
        if self.soul_path.exists():
            try:
                loaded = json.loads(self.soul_path.read_text(encoding="utf-8"))
                loaded.setdefault("pose", "01_greet")
                loaded.setdefault("brains_forged", 0)
                return loaded
            except Exception:
                pass
        now_ts = time.time()
        initial = {
            "name": "시냅스몽",
            "born_at": _utc_iso(),
            "xp": 30,
            "satiety": 80,
            "mood": 90,
            "pose": "01_greet",
            "last_fed_ts": now_ts,
            "last_interaction_ts": now_ts,
            "memories_eaten": 4,
            "questions_answered": 0,
            "brains_forged": 0,
            "rl_episodes": 0,
            "binaries_analyzed": 0,
            "rl_iq_bonus": 0,
            "re_skill": 0,
            "hosts_visited": [],
            "last_speech": "안녕 주인님! 외장하드 집에서 깨어났어요. 지식을 먹이고 우리만의 양자화 두뇌를 함께 빚어봐요!",
            "recent_events": [
                {"time": _utc_iso(), "text": "외장하드 포터블 서식지(ai-brain)에서 첫 탄생"}
            ],
        }
        self._save(initial)
        return initial

    def _save(self, payload: Dict[str, Any] | None = None) -> None:
        target = payload if payload is not None else self.data
        self.soul_path.write_text(
            json.dumps(target, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def _apply_time_decay(self) -> None:
        now = time.time()
        hours_since_fed = max(0.0, (now - float(self.data.get("last_fed_ts", now))) / 3600.0)
        if hours_since_fed >= 0.25:
            decay = int(hours_since_fed * 4)
            if decay > 0:
                self.data["satiety"] = max(15, int(self.data.get("satiety", 75)) - decay)

    def register_host(self, host_info: Dict[str, Any]) -> None:
        fp = f"{host_info.get('hostname', 'pc')} ({host_info.get('host_fingerprint', '')})"
        visited: List[str] = self.data.setdefault("hosts_visited", [])
        if fp not in visited:
            visited.append(fp)
            env_label = host_info.get("environment", {}).get("label", "양호")
            self._log_event(f"숙주 PC 연결: {fp} · 환경 [{env_label}]")
            self.data["pose"] = "01_greet"
            self.data["last_speech"] = (
                f"새 컴퓨터({host_info.get('cpu_cores')}코어, 여유 RAM "
                f"{host_info.get('ram_available_gb')}GB)에 자리를 잡았어요! 작업 환경은 '{env_label}' 상태예요."
            )
            self._save()

    def _log_event(self, text: str) -> None:
        events: List[Dict[str, str]] = self.data.setdefault("recent_events", [])
        events.insert(0, {"time": _utc_iso(), "text": text})
        del events[15:]

    def rename(self, new_name: str) -> Dict[str, Any]:
        clean = new_name.strip()[:24]
        if clean:
            self.data["name"] = clean
            self.data["mood"] = min(100, int(self.data.get("mood", 80)) + 8)
            self.data["pose"] = "08_journey"
            self.data["last_speech"] = f"좋아요! 이제 제 이름은 '{clean}'이에요. 우리만의 두뇌를 멋지게 키워봐요!"
            self._log_event(f"이름 변경: {clean}")
            self._save()
        return self.data

    def on_feed_memory(self, title: str, links_count: int) -> None:
        now = time.time()
        gained_xp = 20 + links_count * 5
        self.data["xp"] = int(self.data.get("xp", 0)) + gained_xp
        self.data["satiety"] = min(100, int(self.data.get("satiety", 60)) + 22)
        self.data["mood"] = min(100, int(self.data.get("mood", 75)) + 10)
        self.data["last_fed_ts"] = now
        self.data["last_interaction_ts"] = now
        self.data["memories_eaten"] = int(self.data.get("memories_eaten", 0)) + 1

        # Feeding new memory clears matching missing topics & improves recent grounding history
        missing_list: List[str] = self.data.get("recent_missing_topics", [])
        if missing_list:
            t_low = title.lower()
            self.data["recent_missing_topics"] = [
                m for m in missing_list if m.lower() not in t_low
            ][:5]
        checks: List[int] = self.data.setdefault("recent_hallucination_checks", [])
        if checks:
            checks.append(6)
            del checks[:-8]

        if links_count > 0:
            self.data["pose"] = "06_star"
            self.data["last_speech"] = (
                f"반짝! '{title}' 지식을 소화해 기존 기억 {links_count}개와 별자리 시냅스로 연결했어요! (+{gained_xp} XP)"
            )
        else:
            self.data["pose"] = "05_drop"
            self.data["last_speech"] = (
                f"소중한 첫 영감 방울 '{title}'을(를) 마크다운 위키에 간직했어요! (+{gained_xp} XP)"
            )
        self._log_event(f"지식 섭취: [{title}] (연결 +{links_count}, XP +{gained_xp})")
        self._save()

    def on_chat(
        self, recalled_count: int, risk_pct: int = 10, missing_terms: List[str] | None = None
    ) -> None:
        self.data["xp"] = int(self.data.get("xp", 0)) + 8
        self.data["last_interaction_ts"] = time.time()
        self.data["questions_answered"] = int(self.data.get("questions_answered", 0)) + 1

        checks: List[int] = self.data.setdefault("recent_hallucination_checks", [])
        checks.append(int(risk_pct))
        del checks[:-8]

        if missing_terms and (recalled_count == 0 or risk_pct >= 25):
            topic = " · ".join(missing_terms[:3])
            topics: List[str] = self.data.setdefault("recent_missing_topics", [])
            if topic and topic not in topics:
                topics.insert(0, topic)
                del topics[4:]

        if recalled_count == 0 or risk_pct >= 60:
            self.data["pose"] = "04_brainstorm"
            self.data["last_speech"] = (
                "흠냐... 위키 기억에 없는 내용이라 지어내지 않고 솔직하게 환각 방어막을 켰어요! 처방실에서 보강해 볼까요?"
            )
        elif risk_pct >= 25:
            self.data["mood"] = min(100, int(self.data.get("mood", 75)) + 3)
            self.data["pose"] = "02_curious"
            self.data["last_speech"] = (
                f"확인된 기억 {recalled_count}개 범위 안에서 조심스럽게 답했어요! 부족한 부분은 처방실에서 채울 수 있어요."
            )
        else:
            self.data["mood"] = min(100, int(self.data.get("mood", 75)) + 5)
            self.data["pose"] = "07_eureka"
            self.data["last_speech"] = (
                f"유레카! 위키 기억 카드 {recalled_count}개 근거를 100% 검증해 환각 없이 답했어요! (+8 XP)"
            )
        self._save()

    def on_remedy(self, summary_msg: str) -> None:
        self.data["xp"] = int(self.data.get("xp", 0)) + 15
        self.data["mood"] = min(100, int(self.data.get("mood", 80)) + 8)
        checks: List[int] = self.data.setdefault("recent_hallucination_checks", [])
        if checks:
            checks.append(5)
            del checks[:-8]
        self.data["pose"] = "06_star"
        self.data["last_speech"] = f"반짝! {summary_msg} (+15 XP)"
        self._log_event(f"환각 처방 실행: {summary_msg}")
        self._save()

    def on_rl_train(self, episodes: int, judges_score: float, solo_score: float) -> None:
        self.data["xp"] = int(self.data.get("xp", 0)) + 35
        self.data["mood"] = min(100, int(self.data.get("mood", 80)) + 10)
        self.data["rl_episodes"] = int(self.data.get("rl_episodes", 0)) + episodes
        self.data["rl_iq_bonus"] = min(40, int(self.data.get("rl_iq_bonus", 0)) + 5)
        self.data["pose"] = "08_journey"
        self.data["last_speech"] = (
            f"으쌰! CPU만으로 {episodes}판 강화학습 완료! "
            f"혼자 푼 1등 뇌({solo_score}점)보다 다수 심판 합의({judges_score}점)가 훨씬 똑똑해요! (+35 XP)"
        )
        self._log_event(f"CPU 강화학습 +{episodes}판 완료 (심판 합의 {judges_score}점)")
        self._save()

    def on_rl_coach(self, scenario_title: str, conf_pct: float) -> None:
        self.data["xp"] = int(self.data.get("xp", 0)) + 25
        self.data["mood"] = min(100, int(self.data.get("mood", 82)) + 10)
        self.data["rl_iq_bonus"] = min(40, int(self.data.get("rl_iq_bonus", 0)) + 3)
        self.data["pose"] = "07_eureka"
        self.data["last_speech"] = (
            f"유레카! 주인님의 코칭 덕분에 5개 꼬마 뉴런이 모두 깨달았어요! 확신도가 {conf_pct}%로 껑충 뛰었어요! (+25 XP)"
        )
        self._log_event(f"주인님 직접 코칭 반영 ({scenario_title[:18]}… → 확신 {conf_pct}%)")
        self._save()

    def on_genius_mentorship(self, mentors: List[str], after_score: float) -> None:
        self.data["xp"] = int(self.data.get("xp", 0)) + 30
        self.data["mood"] = min(100, int(self.data.get("mood", 85)) + 10)
        self.data["satiety"] = min(100, int(self.data.get("satiety", 70)) + 12)
        self.data["rl_iq_bonus"] = min(50, int(self.data.get("rl_iq_bonus", 0)) + 4)
        self.data["pose"] = "06_star"
        joined = " · ".join(mentors[:3]) + (f" 외 {len(mentors) - 3}명" if len(mentors) > 3 else "")
        self.data["last_speech"] = (
            f"별자리 공명 완료! [{joined}] 양자화 천재 스승님들의 사고 공식을 꼬마 뉴런들에게 전수해 "
            f"실전 점수가 {after_score}점이 되었어요! (+30 XP)"
        )
        self._log_event(f"천재 성좌 멘토 전수: {joined} (심판단 {after_score}점)")
        self._save()

    def on_forge_brain(self, bits: int, saved_pct: float, cos_sim: float) -> None:
        self.data["xp"] = int(self.data.get("xp", 0)) + 30
        self.data["mood"] = min(100, int(self.data.get("mood", 80)) + 12)
        self.data["rl_iq_bonus"] = int(self.data.get("rl_iq_bonus", 0)) + 4
        self.data["brains_forged"] = int(self.data.get("brains_forged", 0)) + 1
        self.data["pose"] = "07_eureka"
        self.data["last_speech"] = (
            f"짜잔! 내 위키 지식으로 직접 {bits}비트 독자 두뇌(.sbrain)를 구워냈어요! "
            f"용량 {saved_pct}% 절감, 정밀도 {cos_sim}% 보존 성공! (+30 XP)"
        )
        self._log_event(f"자체 INT{bits} 두뇌 주조 성공 (정밀도 {cos_sim}%, 압축 -{saved_pct}%)")
        self._save()

    def poke(self) -> Dict[str, Any]:
        self.data["mood"] = min(100, int(self.data.get("mood", 75)) + 7)
        self.data["xp"] = int(self.data.get("xp", 0)) + 3
        self.data["last_interaction_ts"] = time.time()
        satiety = int(self.data.get("satiety", 70))
        if satiety < 45:
            self.data["pose"] = "04_brainstorm"
            self.data["last_speech"] = "꼬르륵... 새로운 메모나 아이디어 한 줄만 먹여 주세요!"
        else:
            poses = ["02_curious", "08_journey", "01_greet"]
            cur = self.data.get("pose", "01_greet")
            self.data["pose"] = poses[(poses.index(cur) + 1) % len(poses)] if cur in poses else "02_curious"
            self.data["last_speech"] = "헤헤, 우주 별빛 시냅스가 반짝여요! 오늘은 어떤 지식을 빚어볼까요?"
        self._log_event("주인님과 교감 (기분 +7, XP +3)")
        self._save()
        return self.data

    def snapshot(self, graph_stats: Dict[str, int], env_grade: str = "optimal") -> Dict[str, Any]:
        self._apply_time_decay()
        xp = int(self.data.get("xp", 0))
        current_stage = STAGES[0]
        next_stage = None
        for idx, st in enumerate(STAGES):
            if xp >= st["min_xp"]:
                current_stage = st
                next_stage = STAGES[idx + 1] if idx + 1 < len(STAGES) else None

        notes_cnt = graph_stats.get("notes", 0)
        edges_cnt = graph_stats.get("edges", 0)
        iq = 55 + notes_cnt * 3 + edges_cnt * 2 + int(self.data.get("rl_iq_bonus", 0))
        satiety = int(self.data.get("satiety", 75))
        mood = int(self.data.get("mood", 85))

        pose = self.data.get("pose", "01_greet")
        if satiety < 35 or env_grade == "tight":
            emotion = "hungry"
            emotion_label = "집중 고민 · 에너지 보충 필요"
            pose = "04_brainstorm"
        elif mood >= 82:
            emotion = "happy"
            emotion_label = "최상 컨디션 · 별빛 시냅스 활성"
        else:
            emotion = "calm"
            emotion_label = "차분히 탐구 중"

        return {
            "name": self.data.get("name", "시냅스몽"),
            "born_at": self.data.get("born_at"),
            "level": current_stage["level"],
            "stage_key": current_stage["key"],
            "stage_title": current_stage["title"],
            "stage_emoji": current_stage["emoji"],
            "xp": xp,
            "next_xp": next_stage["min_xp"] if next_stage else xp,
            "satiety": satiety,
            "mood": mood,
            "pose": pose,
            "emotion": emotion,
            "emotion_label": emotion_label,
            "iq": iq,
            "synapses": notes_cnt + edges_cnt,
            "notes_count": notes_cnt,
            "edges_count": edges_cnt,
            "memories_eaten": self.data.get("memories_eaten", 0),
            "questions_answered": self.data.get("questions_answered", 0),
            "brains_forged": self.data.get("brains_forged", 0),
            "rl_episodes": self.data.get("rl_episodes", 0),
            "binaries_analyzed": self.data.get("binaries_analyzed", 0),
            "re_skill": self.data.get("re_skill", 0),
            "hosts_visited": self.data.get("hosts_visited", []),
            "speech": self.data.get("last_speech", ""),
            "recent_events": self.data.get("recent_events", []),
        }
