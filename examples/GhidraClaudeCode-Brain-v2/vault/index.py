"""
vault/index.py — Obsidian Vault 최소 구현

Vault = 폴더, Note = .md 파일, Edge = [[Wikilink]]
MetadataCache = index (nodes/edges + frontmatter)
"""
import pathlib, re, json, os

ROOT = pathlib.Path(__file__).parent.parent
VAULT = ROOT / "vault"
INDEX_FILE = VAULT / ".index.json"

# [[link]] 정규식 — code block 안은 제외해야 하므로 전처리
WIKILINK_RE = re.compile(r"\[\[([^\[\]]+)\]\]")
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
CODE_BLOCK_RE = re.compile(r"```.*?```", re.DOTALL)

def _strip_code_blocks(text: str) -> str:
    return CODE_BLOCK_RE.sub("", text)

def _parse_frontmatter(text: str) -> dict:
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}
    fm = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            fm[k.strip()] = v.strip().strip('"').strip("'")
    return fm

def _extract_links(text: str) -> list:
    clean = _strip_code_blocks(text)
    links = []
    for m in WIKILINK_RE.finditer(clean):
        raw = m.group(1).strip()
        # alias: [[target|alias]] → target만
        target = raw.split("|")[0].strip()
        # heading: [[note#heading]] → note만
        target = target.split("#")[0].strip()
        if target:
            links.append(target)
    return links

def build_index(vault_path=None) -> dict:
    vp = pathlib.Path(vault_path) if vault_path else VAULT
    vp.mkdir(exist_ok=True)
    files = list(vp.rglob("*.md"))
    nodes = []
    edges = []
    file_map = {}  # basename → path

    for f in files:
        rel = str(f.relative_to(vp))
        stem = f.stem  # basename without .md
        file_map[stem] = rel
        file_map[rel] = rel
        # frontmatter aliases도 맵에 추가
        try:
            txt = f.read_text(encoding="utf-8", errors="replace")
        except:
            txt = ""
        fm = _parse_frontmatter(txt)
        # aliases: "a, b" 또는 "[a, b]"
        aliases = fm.get("aliases", "")
        if aliases:
            for a in re.split(r"[,\[\]]", aliases):
                a = a.strip().strip('"').strip("'")
                if a:
                    file_map[a] = rel
        nodes.append({
            "id": rel,
            "label": stem,
            "path": rel,
            "group": f.parent.name if f.parent != vp else "root",
            "frontmatter": fm,
        })

    # edges — links 해석 (basename 우선)
    for f in files:
        rel = str(f.relative_to(vp))
        try:
            txt = f.read_text(encoding="utf-8", errors="replace")
        except:
            continue
        links = _extract_links(txt)
        for target in links:
            # 해석 우선순위: 풀패스 > alias > basename
            resolved = file_map.get(target)
            if not resolved:
                # basename으로 시도
                basename = pathlib.Path(target).stem
                resolved = file_map.get(basename)
            if resolved and resolved != rel:
                edges.append({"from": rel, "to": resolved, "raw": target})

    # 노드 크기 = incoming links 수
    incoming = {}
    for e in edges:
        incoming[e["to"]] = incoming.get(e["to"], 0) + 1
    for n in nodes:
        n["size"] = 5 + incoming.get(n["id"], 0) * 3

    index = {"nodes": nodes, "edges": edges, "vault": str(vp), "total": len(nodes)}
    # 캐시 저장
    try:
        VAULT.mkdir(exist_ok=True)
        (VAULT / ".index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    except:
        pass
    return index

def get_backlinks(file: str, index=None) -> list:
    idx = index or build_index()
    return [e for e in idx["edges"] if e["to"] == file]

def get_outgoing(file: str, index=None) -> list:
    idx = index or build_index()
    return [e for e in idx["edges"] if e["from"] == file]

def write_note(path: str, content: str) -> dict:
    """vault/path 에 .md 쓰기 — 노트 생성"""
    vp = VAULT
    full = (vp / path).resolve()
    if not str(full).startswith(str(vp.resolve())):
        return {"ok": False, "error": "허용되지 않은 경로"}
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(content, encoding="utf-8")
    # 인덱스 갱신
    build_index()
    return {"ok": True, "path": str(full.relative_to(vp)), "size": len(content.encode("utf-8"))}

def read_note(path: str) -> dict:
    vp = VAULT
    full = (vp / path).resolve()
    if not full.exists():
        return {"ok": False, "error": f"파일 없음: {path}"}
    return {"ok": True, "path": path, "content": full.read_text(encoding="utf-8", errors="replace")}
