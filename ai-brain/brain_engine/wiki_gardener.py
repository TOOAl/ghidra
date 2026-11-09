"""
Stage A — P-Reinforce Autonomous Markdown Wiki Gardener & Graph Memory Engine.
- Stores 100% Obsidian-compatible Markdown notes with YAML frontmatter & [[Wiki Links]]
- Uses relative paths only, so unplugging and moving the external drive never breaks links
- Maintains an automatic SQLite index (`state/wiki_index.db`) rebuilt from `vault/` if missing
"""

from __future__ import annotations

import math
import re
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple


CATEGORY_RULES: List[Tuple[str, List[str]]] = [
    ("AI모델·양자화", ["slm", "llm", "양자화", "quant", "gguf", "gemma", "qwen", "ollama", "라마", "모델", "토큰", "비트", "lora", "메모리", "ram"]),
    ("강화학습·판단", ["강화학습", "rl", "dqn", "ppo", "보상", "reward", "시뮬레이터", "다수결", "에이전트", "정책", "policy"]),
    ("역공학·보안", ["ghidra", "기드라", "역공학", "디컴파일", "어셈블리", "바이너리", "binary", "elf", "exe", "보안", "해킹", "취약점", "함수", "analyzeheadless"]),
    ("포터블·인프라", ["외장하드", "usb", "ssd", "포터블", "깃허브", "github", "백업", "오프라인", "로컬", "다마고치"]),
    ("아이디어·노하우", ["아이디어", "기획", "비즈니스", "수익", "목표", "전략", "프로젝트", "연구", "노트", "위키"]),
]

STOPWORDS: Set[str] = {
    "그리고", "하지만", "그래서", "때문에", "위해서", "통해서", "대한", "있는", "없는", "하는", "되는",
    "에서", "으로", "에게", "처럼", "같은", "이것", "그것", "저것", "우리", "내가", "나의", "정말",
    "너무", "아주", "모든", "이런", "그런", "합니다", "입니다", "있다", "없다", "한다", "된다",
    "the", "and", "for", "with", "that", "this", "from", "into", "your", "are", "was", "have",
}


def _slugify(title: str) -> str:
    cleaned = re.sub(r"[^\w\s가-힣-]", "", title).strip()
    cleaned = re.sub(r"\s+", "_", cleaned)
    return cleaned[:60] or f"note_{int(datetime.now().timestamp())}"


def extract_keywords(text: str, top_k: int = 8) -> List[str]:
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9_.-]{1,24}|[가-힣]{2,12}", text)
    normed: List[str] = []
    for tok in tokens:
        low = tok.lower()
        if re.match(r"^[가-힣]+$", low) and len(low) >= 3:
            for suffix in ("에서는", "으로서", "이라서", "입니다", "합니다", "하기", "에서", "으로", "에게", "까지", "부터", "처럼", "만의", "들이", "들은", "들을", "이다", "이고", "이나", "하는", "되는"):
                if low.endswith(suffix) and len(low) - len(suffix) >= 2:
                    low = low[: -len(suffix)]
                    break
            if len(low) >= 3 and low[-1] in ("은", "는", "이", "가", "을", "를", "의", "에", "로", "도", "만", "과", "와"):
                low = low[:-1]
        if low not in STOPWORDS and len(low) >= 2:
            normed.append(low)
    counts = Counter(normed)
    return [w for w, _ in counts.most_common(top_k)]


def infer_category(text: str) -> str:
    low = text.lower()
    best_cat = "아이디어·노하우"
    best_hits = 0
    for cat, words in CATEGORY_RULES:
        hits = sum(1 for w in words if w in low)
        if hits > best_hits:
            best_hits = hits
            best_cat = cat
    return best_cat


SEED_NOTES: List[Dict[str, Any]] = [
    {
        "title": "초소형 언어모델(SLM)과 4비트 양자화 원리",
        "category": "AI모델·양자화",
        "tags": ["SLM", "양자화", "GGUF", "Q4_K_M", "노트북RAM"],
        "summary": "수천억 개의 거대 모델 대신 0.5B~4B 초소형 모델의 숫자 눈금을 16비트에서 4비트·8비트로 압축하면 데이터센터 GPU 없이 일반 노트북 RAM에서 빠르게 돌아간다.",
        "points": [
            "원본 FP16 대비 4비트(Q4_K_M) 양자화는 용량을 약 70~75% 줄이면서 핵심 추론 능력을 대부분 유지한다.",
            "0.8B 모델(Q8_0)은 약 812MB, 2B 모델(Q4_K_M)은 약 1.5GB라 외장하드에 여러 개를 넣어 다닐 수 있다.",
            "지식 암기는 마크다운 위키에 맡기고, SLM은 '읽고 판단하는 추론 엔진' 역할만 맡기는 것이 핵심이다.",
        ],
        "links": ["외장하드 서식형 포터블 다마고치 두뇌 설계", "LLM 위키와 P-Reinforce 자율 정원사"],
    },
    {
        "title": "외장하드 서식형 포터블 다마고치 두뇌 설계",
        "category": "포터블·인프라",
        "tags": ["외장하드", "포터블AI", "다마고치", "무설치", "숙주감지"],
        "summary": "모델 가중치(GGUF), 추론 실행기(llama-server), 마크다운 기억 금고(vault), 다마고치 영혼(soul.json)을 모두 외장하드 한 폴더 안에 상대경로로 가두어 어느 PC에 꽂아도 즉시 깨어난다.",
        "points": [
            "일반 AI 도구는 C드라이브 사용자 폴더에 파일을 흩뿌려 PC를 옮기면 기억이 끊기지만, 포터블 구조는 흔적을 남기지 않는다.",
            "깨어나는 순간 연결된 숙주 PC의 여유 RAM과 CPU 코어를 스캔해 가장 알맞은 양자화 눈금 모델을 고른다.",
            "지식을 먹으면 포만감과 시냅스가 자라고, 강화학습과 역공학 경험이 쌓일수록 진화한다.",
        ],
        "links": ["초소형 언어모델(SLM)과 4비트 양자화 원리", "LLM 위키와 P-Reinforce 자율 정원사", "Ghidra 헤드리스와 로컬 AI 역공학 결합"],
    },
    {
        "title": "LLM 위키와 P-Reinforce 자율 정원사",
        "category": "아이디어·노하우",
        "tags": ["LLM위키", "옵시디언", "마크다운", "시냅스그래프", "제2의두뇌"],
        "summary": "파편화된 메모를 그냥 쌓아두지 않고, 에이전트가 제목·카테고리·태그·양방향 [[링크]]를 붙여 마크다운 지식 그물망으로 구조화하면 검색 토큰을 아끼며 기억이 평생 축적된다.",
        "points": [
            "단순 RAG는 매번 긴 문서를 통째로 읽어 느리지만, 마크다운 위키는 연결된 핵심 기억 카드만 정밀 인출한다.",
            "옵시디언(Obsidian)과 100% 호환되는 순수 .md 파일이라 특정 회사 서비스가 사라져도 내 지식은 영원히 남는다.",
            "GitHub와 동기화하면 외장하드를 분실해도 언제든 복구할 수 있는 불멸의 제2의 두뇌가 된다.",
        ],
        "links": ["초소형 언어모델(SLM)과 4비트 양자화 원리", "외장하드 서식형 포터블 다마고치 두뇌 설계"],
    },
    {
        "title": "Ghidra 헤드리스와 로컬 AI 역공학 결합",
        "category": "역공학·보안",
        "tags": ["Ghidra", "analyzeHeadless", "역공학", "보안분석", "로컬AI"],
        "summary": "TOOAl/ghidra에서 빌드한 Ghidra 12.3의 analyzeHeadless가 실행 파일에서 함수·문자열·호출 구조를 추출하면, 포터블 AI 두뇌가 이를 해석해 위키 지식으로 축적한다.",
        "points": [
            "민감한 바이너리나 보안 분석 데이터를 외부 클라우드에 올리지 않고 100% 오프라인으로 안전하게 분석한다.",
            "자주 만나는 암호화 패턴이나 시스템 호출 구조를 위키 시냅스로 기억해 분석할수록 점점 더 빨라진다.",
            "C단계에서 이 두뇌의 '역공학 해부실' 모듈과 직접 연결된다.",
        ],
        "links": ["외장하드 서식형 포터블 다마고치 두뇌 설계", "초소형 언어모델(SLM)과 4비트 양자화 원리"],
    },
]


class WikiGardener:
    def __init__(self, vault_dir: Path, db_path: Path) -> None:
        self.vault_dir = vault_dir
        self.raw_dir = vault_dir / "00_Raw"
        self.wiki_dir = vault_dir / "10_Wiki"
        self.skills_dir = vault_dir / "20_Skills"
        self.ghidra_dir = vault_dir / "30_Ghidra"
        for d in (self.raw_dir, self.wiki_dir, self.skills_dir, self.ghidra_dir):
            d.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        self._ensure_seeds()
        self.rebuild_index()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS notes (
                    slug TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    category TEXT NOT NULL,
                    tags TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    body TEXT NOT NULL,
                    links_json TEXT NOT NULL,
                    rel_path TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

    def _ensure_seeds(self) -> None:
        existing = list(self.wiki_dir.glob("*.md"))
        if existing:
            return
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        for seed in SEED_NOTES:
            self._write_wiki_markdown(
                title=seed["title"],
                category=seed["category"],
                tags=seed["tags"],
                summary=seed["summary"],
                points=seed["points"],
                links=seed["links"],
                created=now,
            )

    def _write_wiki_markdown(
        self,
        title: str,
        category: str,
        tags: List[str],
        summary: str,
        points: List[str],
        links: List[str],
        created: str,
    ) -> Path:
        slug = _slugify(title)
        path = self.wiki_dir / f"{slug}.md"
        tag_str = ", ".join(tags)
        hash_tags = " ".join(f"#{t}" for t in tags)
        points_md = "\n".join(f"- {p}" for p in points) if points else f"- {summary}"
        links_md = (
            "\n".join(f"- [[{lk}]]" for lk in links)
            if links
            else "- *(아직 연결된 시냅스가 없습니다 — 새 메모를 넣으면 자동 연결됩니다)*"
        )
        md = (
            f"---\n"
            f"title: \"{title}\"\n"
            f"category: \"{category}\"\n"
            f"tags: [{tag_str}]\n"
            f"created: \"{created}\"\n"
            f"---\n\n"
            f"# {title}\n\n"
            f"{hash_tags}\n\n"
            f"## 💡 핵심 요약\n"
            f"{summary}\n\n"
            f"## 📌 주요 포인트\n"
            f"{points_md}\n\n"
            f"## 🔗 연결된 시냅스 (Wiki Links)\n"
            f"{links_md}\n"
        )
        path.write_text(md, encoding="utf-8")
        return path

    def _parse_markdown(self, md_path: Path) -> Dict[str, Any]:
        raw = md_path.read_text(encoding="utf-8", errors="ignore")
        title = md_path.stem.replace("_", " ")
        category = "아이디어·노하우"
        tags: List[str] = []
        updated_at = datetime.fromtimestamp(
            md_path.stat().st_mtime, tz=timezone.utc
        ).strftime("%Y-%m-%d %H:%M UTC")

        fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n", raw, flags=re.DOTALL)
        body = raw
        if fm_match:
            fm = fm_match.group(1)
            body = raw[fm_match.end() :]
            t_m = re.search(r'^title:\s*"?(.+?)"?\s*$', fm, flags=re.MULTILINE)
            c_m = re.search(r'^category:\s*"?(.+?)"?\s*$', fm, flags=re.MULTILINE)
            g_m = re.search(r"^tags:\s*\[(.*?)\]\s*$", fm, flags=re.MULTILINE)
            d_m = re.search(r'^created:\s*"?(.+?)"?\s*$', fm, flags=re.MULTILINE)
            if t_m:
                title = t_m.group(1).strip()
            if c_m:
                category = c_m.group(1).strip()
            if g_m:
                tags = [x.strip().strip('"\'') for x in g_m.group(1).split(",") if x.strip()]
            if d_m:
                updated_at = d_m.group(1).strip()

        links = list(dict.fromkeys(m.strip() for m in re.findall(r"\[\[([^\]]+)\]\]", body) if m.strip()))
        sum_match = re.search(r"## 💡 핵심 요약\s*\n+(.+?)(?:\n\n|\n## )", body, flags=re.DOTALL)
        summary = sum_match.group(1).strip() if sum_match else body.strip().splitlines()[0][:180]
        return {
            "slug": md_path.stem,
            "title": title,
            "category": category,
            "tags": tags,
            "summary": summary,
            "body": raw,
            "links": links,
            "rel_path": str(md_path.relative_to(self.vault_dir)),
            "updated_at": updated_at,
        }

    def rebuild_index(self) -> None:
        all_md = sorted(
            list(self.wiki_dir.glob("*.md"))
            + list(self.skills_dir.glob("*.md"))
            + list(self.ghidra_dir.glob("*.md"))
        )
        rows = [self._parse_markdown(p) for p in all_md]
        with self._connect() as conn:
            conn.execute("DELETE FROM notes")
            for r in rows:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO notes
                    (slug, title, category, tags, summary, body, links_json, rel_path, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        r["slug"],
                        r["title"],
                        r["category"],
                        ",".join(r["tags"]),
                        r["summary"],
                        r["body"],
                        "|".join(r["links"]),
                        r["rel_path"],
                        r["updated_at"],
                    ),
                )

    def list_notes(self) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            cur = conn.execute("SELECT * FROM notes ORDER BY updated_at DESC, title ASC")
            out: List[Dict[str, Any]] = []
            for row in cur.fetchall():
                out.append(
                    {
                        "slug": row["slug"],
                        "title": row["title"],
                        "category": row["category"],
                        "tags": [t for t in row["tags"].split(",") if t],
                        "summary": row["summary"],
                        "body": row["body"],
                        "links": [lk for lk in row["links_json"].split("|") if lk],
                        "rel_path": row["rel_path"],
                        "updated_at": row["updated_at"],
                    }
                )
            return out

    def get_graph(self) -> Dict[str, Any]:
        notes = self.list_notes()
        title_to_slug = {n["title"]: n["slug"] for n in notes}
        nodes = [
            {
                "id": n["slug"],
                "title": n["title"],
                "category": n["category"],
                "tags": n["tags"],
                "summary": n["summary"],
                "rel_path": n["rel_path"],
            }
            for n in notes
        ]
        edge_set: Set[Tuple[str, str]] = set()
        for n in notes:
            src = n["slug"]
            for lk in n["links"]:
                dst = title_to_slug.get(lk) or _slugify(lk)
                if dst != src and any(x["slug"] == dst for x in notes):
                    pair = (min(src, dst), max(src, dst))
                    edge_set.add(pair)
        edges = [{"source": a, "target": b} for a, b in sorted(edge_set)]
        return {"nodes": nodes, "edges": edges, "stats": {"notes": len(nodes), "edges": len(edges)}}

    def digest_raw_memory(
        self, raw_text: str, custom_title: str = "", slm_structured: Dict[str, Any] | None = None
    ) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        created_str = now.strftime("%Y-%m-%d %H:%M UTC")
        stamp = now.strftime("%Y%m%d_%H%M%S")

        # 1. Preserve untouched raw input in 00_Raw
        raw_file = self.raw_dir / f"raw_{stamp}.md"
        raw_file.write_text(f"# Raw Input ({created_str})\n\n{raw_text.strip()}\n", encoding="utf-8")

        # 2. Extract structured fields (from SLM if provided, else deterministic NLP organizer)
        lines = [ln.strip() for ln in raw_text.strip().splitlines() if ln.strip()]
        keywords = extract_keywords(raw_text, top_k=6)

        if slm_structured and slm_structured.get("title"):
            title = str(slm_structured["title"]).strip()
            category = str(slm_structured.get("category") or infer_category(raw_text))
            tags = [str(t).lstrip("#").strip() for t in slm_structured.get("tags", keywords[:5]) if str(t).strip()]
            summary = str(slm_structured.get("summary") or lines[0][:180])
            points = [str(p).strip() for p in slm_structured.get("points", []) if str(p).strip()]
        else:
            if custom_title.strip():
                title = custom_title.strip()
            else:
                first = re.sub(r"^[#*\-\d.\s]+", "", lines[0]) if lines else "새로운 기억 조각"
                title = first[:42] if len(first) <= 42 else (first[:40].rsplit(" ", 1)[0] + "…")
            category = infer_category(raw_text)
            tags = keywords[:5] if keywords else ["메모", "제2의두뇌"]
            sentences = [
                s.strip()
                for s in re.split(r"(?<=[.!?다요음함])\s+|\n+", raw_text.strip())
                if len(s.strip()) >= 6
            ]
            summary = sentences[0][:200] if sentences else raw_text.strip()[:200]
            points = sentences[:4] if len(sentences) > 1 else [raw_text.strip()[:240]]

        # 3. Discover semantic/keyword connections to existing Wiki cards
        existing_notes = self.list_notes()
        new_kw_set = set(w.lower() for w in (keywords + tags + extract_keywords(title, top_k=4)))
        scored_links: List[Tuple[int, Dict[str, Any]]] = []
        for note in existing_notes:
            if note["title"] == title:
                continue
            note_kw = set(
                w.lower()
                for w in (
                    note["tags"]
                    + extract_keywords(note["title"] + " " + note["summary"] + " " + note["body"], top_k=14)
                )
            )
            overlap = len(new_kw_set & note_kw)
            cat_bonus = 1 if note["category"] == category else 0
            score = overlap * 2 + cat_bonus
            if score >= 2:
                scored_links.append((score, note))

        scored_links.sort(key=lambda x: x[0], reverse=True)
        linked_notes = [n for _, n in scored_links[:3]]
        link_titles = [n["title"] for n in linked_notes]

        # 4. Write structured Wiki Markdown & update bidirectional backlinks
        wiki_path = self._write_wiki_markdown(
            title=title,
            category=category,
            tags=tags,
            summary=summary,
            points=points,
            links=link_titles,
            created=created_str,
        )

        for target in linked_notes:
            t_path = self.vault_dir / target["rel_path"]
            if t_path.exists():
                content = t_path.read_text(encoding="utf-8", errors="ignore")
                marker = f"[[{title}]]"
                if marker not in content:
                    content = content.rstrip() + f"\n- {marker}\n"
                    t_path.write_text(content, encoding="utf-8")

        self.rebuild_index()
        return {
            "slug": wiki_path.stem,
            "title": title,
            "category": category,
            "tags": tags,
            "summary": summary,
            "links": link_titles,
            "rel_path": str(wiki_path.relative_to(self.vault_dir)),
            "raw_path": str(raw_file.relative_to(self.vault_dir)),
        }

    def recall_memories(self, query: str, limit: int = 2) -> Dict[str, Any]:
        notes = self.list_notes()
        if not notes:
            return {"recalled": [], "total_notes": 0, "saved_tokens_pct": 0}

        q_lower = query.lower()
        q_terms = extract_keywords(query, top_k=10)
        scored: List[Tuple[float, Dict[str, Any]]] = []
        for n in notes:
            hay = f"{n['title']} {' '.join(n['tags'])} {n['category']} {n['summary']} {n['body']}".lower()
            score = 0.0
            for term in q_terms:
                if term in n["title"].lower():
                    score += 5.0
                if any(term in tg.lower() for tg in n["tags"]):
                    score += 4.0
                occurrences = hay.count(term)
                if occurrences > 0:
                    score += 1.5 * (1.0 + math.log(occurrences))
            if score == 0.0 and any(ch in hay for ch in q_lower.split() if len(ch) >= 2):
                score += 1.0
            scored.append((score, n))

        scored.sort(key=lambda x: x[0], reverse=True)
        max_cards = min(limit, max(1, len(notes) - 2)) if len(notes) >= 4 else limit
        primary = [n for sc, n in scored if sc > 0][:max_cards]
        if not primary:
            primary = [n for _, n in scored[:1]]

        # 1-hop graph expansion along [[Wiki Links]] when vault grows larger
        recalled_slugs = {n["slug"] for n in primary}
        recalled = list(primary)
        if len(notes) >= 6:
            title_map = {n["title"]: n for n in notes}
            for p in primary:
                if len(recalled) >= max_cards + 1:
                    break
                for lk in p["links"]:
                    neighbor = title_map.get(lk)
                    if neighbor and neighbor["slug"] not in recalled_slugs:
                        recalled.append(neighbor)
                        recalled_slugs.add(neighbor["slug"])
                        break

        total_chars = sum(len(n["body"]) for n in notes) or 1
        used_chars = sum(len(n["body"]) for n in recalled)
        saved_pct = max(0, min(95, round((1.0 - used_chars / total_chars) * 100)))
        return {
            "recalled": recalled,
            "total_notes": len(notes),
            "saved_tokens_pct": saved_pct,
        }
