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
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

# 💡 Stage J: the vault's own meaning space.  This module has no project
# dependencies of its own, so importing it here is cycle-free.
from brain_engine.semantic_memory import SemanticMemory

# NOTE: the Stage H field helpers live in core_ability_engine, which (via
# quant_forge) imports `extract_keywords` from THIS module — so they are
# imported lazily inside the methods below to avoid a circular import.


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


def org_lesson_tokens(note: Dict[str, Any], keywords: Iterable[str]) -> List[str]:
    """The ONE token list both the weaving muscle and its lesson must see.

    ⚠️ Stage K: the weaver passed `(tags ∪ body keywords)[:8]` while the lesson
    passed `tags + body keywords[:8]`.  Two shelves that look alike are not the
    same shelf: 4 pairs the lesson scored as correct merged in the field and the
    muscle could never diagnose why, because the problem it re-studied was not
    the problem it had just solved.
    """
    return list(note.get("tags") or []) + sorted(str(k).lower() for k in keywords if k)[:8]


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
        # 💡 Stage J: the vault's own meaning space, trained from these very
        # notes and cached in the state dir (int8, no external model, no network).
        self.semantic = SemanticMemory(self.db_path.parent)
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

    def recall_memories(
        self, query: str, limit: int = 2, field: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        notes = self.list_notes()
        if not notes:
            return {"recalled": [], "total_notes": 0, "saved_tokens_pct": 0}

        q_lower = query.lower()
        # Strip generic question endings in Korean so real topic words stand out
        cleaned_q = re.sub(
            r"(무엇인가요|무엇이야|뭐야|어떻게|어디야|누구야|알려줘|설명해줘|궁금해|있어|할까|인가요|예정이야|원리가|전략이)",
            " ",
            q_lower,
        )
        q_terms = extract_keywords(cleaned_q, top_k=8) or extract_keywords(query, top_k=8)
        scored: List[Tuple[float, Dict[str, Any]]] = []
        matched_term_set: Set[str] = set()

        for n in notes:
            hay = f"{n['title']} {' '.join(n['tags'])} {n['category']} {n['summary']} {n['body']}".lower()
            score = 0.0
            for term in q_terms:
                if term in n["title"].lower():
                    score += 5.0
                    matched_term_set.add(term)
                if any(term in tg.lower() for tg in n["tags"]):
                    score += 4.0
                    matched_term_set.add(term)
                occurrences = hay.count(term)
                if occurrences > 0:
                    score += 1.5 * (1.0 + math.log(occurrences))
                    matched_term_set.add(term)
            scored.append((score, n))

        # ⚔️ Stage H: the CONTEXT muscle re-ranks these REAL memories using the
        # very weights it learned in the gym (6 features: subj/verb/neg/assert/owner/link).
        muscle: Optional[Dict[str, Any]] = None
        if field:
            from brain_engine.core_ability_engine import field_context_limit, field_context_rerank

            bonus = field_context_rerank(field, [n for _, n in scored], q_terms)
            scored = [(sc + 2.0 * bn, n) for (sc, n), bn in zip(scored, bonus)]
            muscle = {
                "ability": "context",
                "level": int(field.get("level", 1)),
                "tier": int(field.get("tier", 0)),
                "weights_used": sorted((field.get("weights") or {}).keys()),
                "rerank_bonus": bonus[:6],
            }

        # 💡 Stage J — graduate from keyword matching.  A note that shares NO
        # word with the question can still be its answer, because the meaning
        # space was grown from the vault itself.  How much that counts is not a
        # constant: it is the context muscle's own learned trust (w_sem), so a
        # muscle that has been misled by meaning learns to trust it less.
        from brain_engine.core_ability_engine import (
            SEM_MIN_COVERAGE_PCT,
            SEM_SCORE_SCALE,
            field_context_semantic_trust,
        )

        trust = field_context_semantic_trust(field)
        sem_stats = self.semantic.ensure_trained(notes)
        sem_by_slug: Dict[str, float] = {}
        sem_sims: List[float] = []
        for _, n in scored:
            sim = self.semantic.similarity(query, n)
            sem_sims.append(sim)
            sem_by_slug[str(n.get("slug"))] = sim
        best_sem = max(sem_sims) if sem_sims else 0.0
        q_cov = self.semantic.coverage(query)
        # 💡 Measured, not guessed: on a real vault a genuine meaning match
        # (sim 0.56 with 1 of 5 words understood) and a coincidence (sim 0.72
        # with 1 of 4 words understood) CANNOT be told apart by the score, the
        # margin or the ratio.  So searching is allowed to use meaning freely —
        # a librarian may fetch a shelf she is unsure about — and the honesty
        # gate lives where a claim is made: the audit grade and the lesson
        # ledger, both of which require real understanding of the question.
        try:
            cov_pct = float(q_cov.get("pct") or 0.0)
        except (TypeError, ValueError):
            cov_pct = 0.0
        sem_understood = cov_pct >= SEM_MIN_COVERAGE_PCT
        scored = [(sc + SEM_SCORE_SCALE * trust * sim, n) for (sc, n), sim in zip(scored, sem_sims)]

        scored.sort(key=lambda x: x[0], reverse=True)
        top_score = round(scored[0][0], 2) if scored else 0.0
        if field:
            eff_limit = max(limit, field_context_limit(field))
        else:
            eff_limit = limit
        max_cards = min(eff_limit, max(1, len(notes) - 2)) if len(notes) >= 4 else eff_limit

        # Never fabricate unrelated recall when score == 0 (prevents hallucination!)
        primary = [n for sc, n in scored if sc >= 1.5][:max_cards]

        # 1-hop graph expansion along [[Wiki Links]] when vault grows larger
        recalled_slugs = {n["slug"] for n in primary}
        recalled = list(primary)
        if primary and len(notes) >= 6:
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
        saved_pct = max(0, min(95, round((1.0 - used_chars / total_chars) * 100))) if recalled else 100
        missing_terms = [t for t in q_terms if t not in matched_term_set]

        # Which of the two paths carried each recalled memory — shown verbatim so
        # a meaning-based answer never pretends it matched words.
        why_map: Dict[str, str] = {}
        for n in recalled:
            slug = str(n.get("slug"))
            sim = sem_by_slug.get(slug, 0.0)
            hay = f"{n['title']} {' '.join(n['tags'])} {n['category']} {n['summary']}".lower()
            lexical = any(t in hay for t in q_terms)
            # What ACTUALLY carried this memory: meaning counts as soon as its
            # points could lift a note over the evidence line.  (Understanding of
            # the question is reported separately — it gates the GRADE and the
            # lesson, not the label.)
            meaning = sim * SEM_SCORE_SCALE * trust >= 1.5
            why_map[slug] = "📝+💡" if (lexical and meaning) else ("💡 의미" if meaning else ("📝 단어" if lexical else "🔗 연결"))
        bridges = self.semantic.bridges(query, recalled[0], top_k=3) if recalled else []
        out = {
            "recalled": recalled,
            "total_notes": len(notes),
            "saved_tokens_pct": saved_pct,
            "top_score": top_score,
            "query_terms": q_terms,
            "matched_terms": sorted(matched_term_set),
            "missing_terms": missing_terms,
            "cards_limit": eff_limit,
            "semantic": {
                "trust_w_sem": round(trust, 3),
                "by_slug": {k: round(v, 4) for k, v in sem_by_slug.items()},
                "grounded_pct": round(100.0 * best_sem, 1),
                "query_coverage": q_cov,
                "understood": sem_understood,
                "coverage_pct": cov_pct,
                "engine": {
                    "trained": bool(sem_stats.get("trained")),
                    "vocab_size": int(sem_stats.get("vocab_size") or 0),
                    "notes": int(sem_stats.get("notes") or 0),
                    "quant_bits": int(sem_stats.get("quant_bits") or 8),
                    "cosine_fidelity_pct": sem_stats.get("cosine_fidelity_pct"),
                    "cache_kb": sem_stats.get("cache_kb"),
                },
                "why": why_map,
                "bridges": bridges,
            },
        }
        if muscle:
            out["field"] = muscle
        return out

    def weave_missing_synapses(self, field: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Scan all Wiki notes and weave missing bidirectional [[links]] between related concepts.

        ⚔️ Stage H: when the ORGANIZING muscle is deployed, the weave decision is
        made by the muscle's own `_org_sim` + learned shelf threshold instead of
        the fixed `overlap + same_cat >= 1` heuristic — a stronger muscle links
        fewer false pairs and catches more true ones.
        """
        notes = self.list_notes()
        kw_map: Dict[str, Set[str]] = {}
        for n in notes:
            kws = set(
                w.lower()
                for w in (
                    n["tags"]
                    + extract_keywords(n["title"] + " " + n["summary"] + " " + n["body"], top_k=16)
                )
            )
            kw_map[n["slug"]] = kws

        thr = 0.0
        sem_w = 0.0
        org_view: Dict[str, Dict[str, Any]] = {}
        if field:
            from brain_engine.core_ability_engine import (
                field_org_semantic_trust,
                field_org_threshold,
                real_org_note_view,
            )

            thr = field_org_threshold(field)
            # 💡 Stage K: the weaver now sees MEANING, and how much meaning counts
            # is the muscle's own learned weight — not a new hardcoded rule.
            sem_w = field_org_semantic_trust(field)
            self.semantic.ensure_trained(notes)
            for n in notes:
                # Same translation the experience lesson uses, so revision
                # actually transfers to the weaving the muscle does here.
                # ⚠️ Stage K: [:8] is part of that translation, not a detail —
                # the lesson caps tokens at 8 and the weaver used to pass all 16,
                # so the shelf the muscle was graded on was NOT the shelf it
                # stood at: 4 pairs the lesson called correct merged in the field
                # (Ghidra-headless × every skill cartridge) and the muscle could
                # never see why.
                org_view[n["slug"]] = real_org_note_view(
                    n["title"], n["category"], org_lesson_tokens(n, kw_map[n["slug"]])
                )

        added_pairs = 0
        muscle_pairs = 0
        muscle_sims: List[float] = []
        sem_pairs = 0
        sem_examples: List[Dict[str, Any]] = []
        for i in range(len(notes)):
            for j in range(i + 1, len(notes)):
                a, b = notes[i], notes[j]
                already_ab = b["title"] in a["links"]
                already_ba = a["title"] in b["links"]
                if already_ab and already_ba:
                    continue
                overlap = len(kw_map[a["slug"]] & kw_map[b["slug"]])
                same_cat = 1 if a["category"] == b["category"] else 0
                if field:
                    from brain_engine.core_ability_engine import field_org_pair_sim

                    cs = self.semantic.pair_similarity(a, b)
                    sim = field_org_pair_sim(field, org_view[a["slug"]], org_view[b["slug"]], sem=cs)
                    muscle_pairs += 1
                    if sim > thr:
                        muscle_sims.append(round(sim, 3))
                    # Which evidence actually did it?  Subtract meaning back out:
                    # if the pair only crosses the shelf WITH meaning, then two
                    # memories that share no words were just connected — and the
                    # user is told which words carried the bridge.
                    if sim > thr and (sim - sem_w * cs) <= thr:
                        sem_pairs += 1
                        if len(sem_examples) < 6:
                            sem_examples.append(
                                {
                                    "a": a["title"],
                                    "b": b["title"],
                                    "cos": round(cs, 3),
                                    "keyword_overlap": overlap,
                                    "bridges": self.semantic.pair_bridges(a, b, top_k=3),
                                }
                            )
                    should_link = sim > thr
                else:
                    should_link = overlap + same_cat >= 1
                if should_link:
                    for src, dst in ((a, b), (b, a)):
                        p = self.vault_dir / src["rel_path"]
                        if p.exists():
                            txt = p.read_text(encoding="utf-8", errors="ignore")
                            marker = f"[[{dst['title']}]]"
                            if marker not in txt:
                                txt = txt.rstrip() + f"\n- {marker}\n"
                                p.write_text(txt, encoding="utf-8")
                    added_pairs += 1

        self.rebuild_index()
        out: Dict[str, Any] = {"added_pairs": added_pairs, "total_notes": len(notes)}
        if field:
            # 🕳️ Stage K: the vault's blind spots — notes whose strongest meaning
            # neighbour is still weak.  Pointing at them is how a brain that
            # cannot answer says so BEFORE it is asked.
            try:
                gaps = self.semantic.orphans(notes, cos_min=0.30, top_k=6)
            except Exception:
                gaps = []
            out.update(
                {
                    "sem_trust": round(sem_w, 3),
                    "semantic_pairs": sem_pairs,
                    "semantic_examples": sem_examples,
                    "muscle_pairs": muscle_pairs,
                    "gaps": gaps,
                    "gap_count": len(gaps),
                }
            )
        if field:
            # 📓 Stage I: grade the muscle on the REAL vault — cluster these very
            # notes and compare against each note's own inferred category.
            try:
                from brain_engine.core_ability_engine import build_real_org_problem, grade_real_org_problem

                real_notes = [
                    {
                        "title": n["title"],
                        "category": n["category"],
                        # Tags are passed for TRUTH (the lesson grades which notes
                        # belong together); keywords stay the shared FEATURE
                        # translation.  org_lesson_tokens already includes the
                        # tags, so the token SET the muscle sees is unchanged.
                        "tags": list(n.get("tags") or []),
                        "keywords": org_lesson_tokens(n, kw_map[n["slug"]]),
                        # 💡 Stage K: summary rides along so the frozen meaning
                        # cosines are built from what the note MEANS, not only
                        # from its title words.
                        "summary": n.get("summary", ""),
                        "slug": n["slug"],
                        # The vault's own links ride along: they are the second
                        # opinion `_org_same_truth` refuses to overrule.
                        "links": list(n.get("links") or []),
                    }
                    for n in notes
                ]
                prob = build_real_org_problem(real_notes, sem=self.semantic)
                if prob:
                    grade = grade_real_org_problem(field, prob)
                    out["experience_case"] = {
                        "ok": grade["ok"],
                        "site": "wiki_weave",
                        "key": "weave:vault",
                        "note": (
                            f"실제 위키 {len(prob['notes'])}장 묶기 — 과잉병합 {grade['over']}쌍 / "
                            f"누락 {grade['under']}쌍 → 묶음 {grade['clusters']}개 (품질 {grade['quality_pct']}%)"
                            + (
                                f" · 💡 의미로 이은 쌍 {sem_pairs}개 (신뢰도 {sem_w})"
                                f" · 🕳️ 아직 어떤 가중치로도 도달 못 하는 쌍 {grade.get('unreachable', 0)}개"
                                if field
                                else ""
                            )
                        ),
                        # Only claim the lesson is ABOUT meaning when meaning
                        # actually decided a link — a label it did not earn would
                        # teach the master to skim past the ones that did.
                        **({"kind": "의미"} if sem_pairs else {}),
                        "prob": prob,
                        "metric": {
                            "over": grade["over"],
                            "under": grade["under"],
                            "clusters": grade["clusters"],
                            "notes": len(prob["notes"]),
                            "total_pairs": grade["total_pairs"],
                            "quality_pct": grade["quality_pct"],
                            # 🕳️ Stage K: how many misses NO weight could reach,
                            # and the score over the pairs it could.  Without
                            # this the muscle is graded on gaps that only new
                            # memories can fill.
                            "unreachable": grade.get("unreachable", 0),
                            "reachable_quality_pct": grade.get("reachable_quality_pct", grade["quality_pct"]),
                            "semantic_pairs": sem_pairs,
                            "sem_trust": sem_w,
                        },
                    }
            except Exception:
                pass
            out["field"] = {
                "ability": "organizing",
                "level": int(field.get("level", 1)),
                "tier": int(field.get("tier", 0)),
                "threshold": round(thr, 3),
                "pairs_examined": muscle_pairs,
                "pairs_approved": added_pairs,
                "avg_sim_of_approved": round(sum(muscle_sims) / len(muscle_sims), 3) if muscle_sims else 0.0,
            }
        return out
