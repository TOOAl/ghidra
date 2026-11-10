"""🔗 Stage N2 — 증거 사슬 추론: 답은 인용된 사슬이거나 "몰라요".

vault 위에서 다홉 질문을 받을 때, 각 홉은 **실제 증거**만 인정해요:
  link  — 한 노트의 [[위키 링크]]가 다른 노트의 제목을 지목
  tag   — 공유 태그 (1개 이상)
  ident — 기계 채널의 공유 식별자 (calls/refs 겹침)
증거 없는 홉은 없어요. 사슬을 못 찾으면 발명하지 않고 "증거로 이을 수
없어요" + 구멍 보고. 답 문장은 사슬 노트의 요약과 다리 증거만으로
조립해요 (새 주장 추가 금지).
"""
from __future__ import annotations

import re
from collections import deque
from typing import Any, Dict, List, Optional, Sequence, Tuple

_TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]{2,}|[가-힣]{2,}")


def _tokens(n: Dict[str, Any]) -> set:
    out = set(t.lower() for t in (n.get("tags") or []))
    out |= set(t.lower() for t in _TOKEN_RE.findall(str(n.get("title", ""))))
    out |= set(t.lower() for t in _TOKEN_RE.findall(str(n.get("summary", ""))[:400]))
    return out


def _idents(n: Dict[str, Any]) -> set:
    body = str(n.get("body", ""))
    calls = set(re.findall(r"^호출:\s*(.+)$", body, re.M))
    refs = set(re.findall(r"^참조:\s*(.+)$", body, re.M))
    out: set = set()
    for line in calls | refs:
        out |= set(line.split())
    return {t for t in out if len(t) > 3}


def edges_of(notes: Sequence[Dict[str, Any]]) -> Dict[str, List[Tuple[str, str, str]]]:
    """slug → [(other_slug, evidence_type, bridge)] — 전부 vault 사실에서."""
    by_title = {str(n.get("title", "")).strip(): n for n in notes}
    tags_of = {n["slug"]: {str(t).lower() for t in (n.get("tags") or [])} for n in notes}
    id_of = {n["slug"]: _idents(n) for n in notes}
    out: Dict[str, List[Tuple[str, str, str]]] = {n["slug"]: [] for n in notes}
    for a in notes:
        links = {str(l).strip() for l in (a.get("links") or [])}
        for b in notes:
            if a["slug"] == b["slug"]:
                continue
            if str(b.get("title", "")).strip() in links:
                out[a["slug"]].append((b["slug"], "link", str(b.get("title"))[:60]))
                continue
            shared = tags_of[a["slug"]] & tags_of[b["slug"]]
            if shared:
                out[a["slug"]].append((b["slug"], "tag", sorted(shared)[0]))
                continue
            si = id_of[a["slug"]] & id_of[b["slug"]]
            if si:
                out[a["slug"]].append((b["slug"], "ident", sorted(si)[0]))
    return out


_SPLIT_RE = re.compile(r"\s+(?:와|과|랑|하고|and|&)\s+", re.I)


def _foci(question: str) -> List[set]:
    """질문을 두 초점 토큰집합으로 쪼개요 ("A 와 B 는…" → {A},{B})."""
    head = re.split(r"\s+(?:은|는)\s", question, maxsplit=1)[0]
    parts = [p for p in _SPLIT_RE.split(head) if p.strip()]
    if len(parts) < 2:
        parts = [head]
    foci = [{t.lower() for t in _TOKEN_RE.findall(p)} for p in parts]
    return [f for f in foci if f]


def _best(focus: set, notes: Sequence[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not focus:
        return None
    scored = sorted(notes, key=lambda n: -len(focus & _tokens(n)))
    top = scored[0]
    return top if (focus & _tokens(top)) else None


def reason(question: str, notes: Sequence[Dict[str, Any]],
           max_hops: int = 3) -> Dict[str, Any]:
    """질문의 두 초점 기억을 증거 사슬로 잇어요. 못 이으면 정직하게 몰라요."""
    foci = _foci(question)
    if len(foci) < 2:
        # 두 초점을 named 하지 않은 질문 — 양끝 사슬을 정직하게 못 만듦
        return {"answer": "증거로 이을 수 없어요 — 'A 와 B' 형태로 두 기억을 "
                          "짚어 주세요.",
                "chain": [], "evidence": [], "hops": 0, "known": False}
    matched = [_best(f, notes) for f in foci[:2]]
    # 한쪽 초점이라도 vault에 없으면 발명하지 않고 거부
    if any(m is None for m in matched) or matched[0]["slug"] == matched[1]["slug"]:
        miss = [foci[i] for i, m in enumerate(matched) if m is None]
        hint = f" (없는 기억: {sorted(miss[0])[:3]})" if miss else ""
        return {"answer": "증거로 이을 수 없어요 — 초점 기억을 특정할 수 "
                          f"없어요{hint}.",
                "chain": [], "evidence": [], "hops": 0, "known": False}
    a, b = matched
    edges = edges_of(notes)
    prev: Dict[str, Optional[tuple]] = {a["slug"]: None}
    dq = deque([a["slug"]])
    found = False
    while dq and not found:
        cur = dq.popleft()
        if _depth(prev, cur) >= max_hops:
            continue
        for nxt, etype, bridge in edges.get(cur, []):
            if nxt in prev:
                continue
            prev[nxt] = (cur, etype, bridge)
            if nxt == b["slug"]:
                found = True
                break
            dq.append(nxt)
    if not found:
        return {"answer": "증거로 이을 수 없어요 — 두 초점 기억 사이에 사슬이 "
                          "닿지 않아요 (구멍 보고).",
                "chain": [a["slug"], b["slug"]], "evidence": [], "hops": 0,
                "known": False}
    chain: List[str] = []
    ev: List[Dict[str, str]] = []
    cur = b["slug"]
    while cur:
        chain.append(cur)
        par = prev[cur]
        if par:
            ev.append({"from": par[0], "to": cur, "type": par[1], "bridge": par[2]})
        cur = par[0] if par else None
    chain.reverse()
    ev.reverse()
    by_slug = {n["slug"]: n for n in notes}
    parts = [f"[{i + 1}] {by_slug[sx].get('title', sx)}: "
             f"{str(by_slug[sx].get('summary', ''))[:160]}"
             for i, sx in enumerate(chain)]
    answer = " → ".join(f"{e['type']}({e['bridge']})" for e in ev)
    return {"answer": answer, "chain": chain, "evidence": ev,
            "hops": len(ev), "known": True, "notes": parts}


def _depth(seen: Dict[str, Any], slug: str) -> int:
    d = 0
    cur = slug
    while True:
        par = seen.get(cur)
        if not par:            # None(시드) 또는 미방문 → 멈춤
            break
        cur = par[0]
        d += 1
    return d


def hop_benchmark(notes: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """2-홉 양성 문항 + 연결 없는 음성 문항을 vault 구조에서 자동 조성."""
    edges = edges_of(notes)
    pos: List[Dict[str, Any]] = []
    for a in notes:
        for b_slug, _, _ in edges.get(a["slug"], []):
            for c_slug, _, _ in edges.get(b_slug, []):
                if c_slug == a["slug"]:
                    continue
                if any(e[0] == c_slug for e in edges.get(a["slug"], [])):
                    continue  # 1-홉이면 2-홉 문항 자격 없음
                pos.append({"a": a["slug"], "mid": b_slug, "c": c_slug})
        if len(pos) >= 6:
            break
    pos = pos[:6]
    connected: set = set()
    for a in notes:
        seen = {a["slug"]}
        dq = deque([a["slug"]])
        while dq:
            cur = dq.popleft()
            for nxt, _, _ in edges.get(cur, []):
                if nxt not in seen:
                    seen.add(nxt)
                    dq.append(nxt)
        connected |= {(a["slug"], s) for s in seen}
    neg: List[Dict[str, str]] = []
    for i, a in enumerate(notes):
        for b in notes[i + 1:]:
            if (a["slug"], b["slug"]) not in connected \
               and (b["slug"], a["slug"]) not in connected \
               and not (_tokens(a) & _tokens(b)):
                neg.append({"a": a["slug"], "c": b["slug"]})
        if len(neg) >= 4:
            break
    return {"positive": pos, "negative": neg[:4]}
