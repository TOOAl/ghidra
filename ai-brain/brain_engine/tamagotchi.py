"""
Living Tamagotchi Brain state & evolution engine.
Lives inside `state/soul.json` on the external drive so your AI brain keeps its
memories, personality, XP, and travel log across every PC it plugs into.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


STAGES: List[Dict[str, Any]] = [
    {"level": 1, "min_xp": 0, "key": "egg", "title": "알에서 깨어난 꼬마 뉴런", "emoji": "🐣"},
    {"level": 2, "min_xp": 50, "key": "sprout", "title": "호기심 많은 아기 시냅스", "emoji": "🌱"},
    {"level": 3, "min_xp": 140, "key": "scholar", "title": "노트 정리하는 학자 두뇌", "emoji": "🦉"},
    {"level": 4, "min_xp": 300, "key": "analyst", "title": "스스로 판단하는 연구원 두뇌", "emoji": "🧠"},
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
                return json.loads(self.soul_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        now_ts = time.time()
        initial = {
            "name": "시냅스몽",
            "born_at": _utc_iso(),
            "xp": 30,
            "satiety": 78,
            "mood": 88,
            "last_fed_ts": now_ts,
            "last_interaction_ts": now_ts,
            "memories_eaten": 4,
            "questions_answered": 0,
            "rl_episodes": 0,
            "binaries_analyzed": 0,
            "rl_iq_bonus": 0,
            "re_skill": 0,
            "hosts_visited": [],
            "last_speech": "안녕 주인님! 외장하드 집에서 방금 눈을 떴어요. 오늘 배운 지식이나 메모를 먹여 주세요!",
            "recent_events": [
                {"time": _utc_iso(), "text": "외장하드 포터블 서식지(ai-brain)에서 첫 탄생!"}
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
            best = host_info.get("best_slm", {}).get("name", "초경량 모델")
            self._log_event(f"새로운 숙주 컴퓨터 감지: {fp} → 추천 두뇌: {best}")
            self.data["last_speech"] = (
                f"우와! 새로운 컴퓨터({host_info.get('cpu_cores')}코어, 여유 RAM "
                f"{host_info.get('ram_available_gb')}GB)에 연결됐어요! '{best}' 눈금이 딱 맞겠어요!"
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
            self.data["last_speech"] = f"헤헤, 이제 제 이름은 '{clean}'이에요! 평생 주인님 지식을 지켜드릴게요!"
            self._log_event(f"이름이 '{clean}'(으)로 변경됨")
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
        if links_count > 0:
            self.data["last_speech"] = (
                f"냠냠! '{title}' 지식을 맛있게 소화해서 기존 기억 {links_count}개와 시냅스를 연결했어요! (+{gained_xp} XP)"
            )
        else:
            self.data["last_speech"] = (
                f"꿀꺽! 새로운 씨앗 기억 '{title}'을(를) 마크다운 위키에 심었어요! (+{gained_xp} XP)"
            )
        self._log_event(f"지식 섭취: [{title}] (연결 +{links_count}, XP +{gained_xp})")
        self._save()

    def on_chat(self, recalled_count: int) -> None:
        self.data["xp"] = int(self.data.get("xp", 0)) + 8
        self.data["mood"] = min(100, int(self.data.get("mood", 75)) + 5)
        self.data["last_interaction_ts"] = time.time()
        self.data["questions_answered"] = int(self.data.get("questions_answered", 0)) + 1
        self.data["last_speech"] = (
            f"내 머릿속 시냅스에서 관련 기억 카드 {recalled_count}개를 꺼내 대답했어요! (+8 XP)"
        )
        self._save()

    def poke(self) -> Dict[str, Any]:
        self.data["mood"] = min(100, int(self.data.get("mood", 75)) + 7)
        self.data["xp"] = int(self.data.get("xp", 0)) + 3
        self.data["last_interaction_ts"] = time.time()
        satiety = int(self.data.get("satiety", 70))
        if satiety < 45:
            self.data["last_speech"] = "꼬르륵... 배가 조금 고파요! 오늘 떠오른 생각이나 메모 한 줄만 먹여 주세요!"
        else:
            self.data["last_speech"] = "기분 최고예요! 외장하드만 챙기면 어느 컴퓨터에서든 제가 바로 깨어날 수 있어요!"
        self._log_event("주인님이 쓰다듬어 줌 (기분 +7, XP +3)")
        self._save()
        return self.data

    def snapshot(self, graph_stats: Dict[str, int]) -> Dict[str, Any]:
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

        if satiety < 35:
            emotion = "hungry"
            emotion_label = "꼬르륵 배고픔 (지식 필요!)"
        elif mood >= 80:
            emotion = "happy"
            emotion_label = "신남 · 시냅스 반짝이는 중"
        else:
            emotion = "calm"
            emotion_label = "차분히 사색 중"

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
            "emotion": emotion,
            "emotion_label": emotion_label,
            "iq": iq,
            "synapses": notes_cnt + edges_cnt,
            "notes_count": notes_cnt,
            "edges_count": edges_cnt,
            "memories_eaten": self.data.get("memories_eaten", 0),
            "questions_answered": self.data.get("questions_answered", 0),
            "rl_episodes": self.data.get("rl_episodes", 0),
            "binaries_analyzed": self.data.get("binaries_analyzed", 0),
            "re_skill": self.data.get("re_skill", 0),
            "hosts_visited": self.data.get("hosts_visited", []),
            "speech": self.data.get("last_speech", ""),
            "recent_events": self.data.get("recent_events", []),
        }
