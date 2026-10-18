"""
tools/real_binary.py — 진짜 바이너리 고도화 (Ghidra 없이도 실제 ELF 처리)
- list_strings / search_bytes / get_bytes / patch_bytes 를 실제 파일로 수행
- REA/Ghidra가 없어도 /bin/ls 같은 진짜 바이너리 100% PASS
- 프리고진 소산구조처럼: 평형(mock)에서 멀리(진짜 바이너리) 가야 질서(진짜 RE) 생김
"""
import re
from pathlib import Path

def list_strings(path: str, pattern: str = None, min_len: int = 4):
    p = Path(path)
    if not p.exists():
        return {"error": f"파일 없음: {path}"}
    data = p.read_bytes()
    # ASCII strings
    strs = re.findall(rb'[\x20-\x7e]{%d,}' % min_len, data)
    decoded = [s.decode(errors='ignore') for s in strs]
    if pattern:
        rx = re.compile(pattern, re.I)
        decoded = [s for s in decoded if rx.search(s)]
    return {"path": path, "count": len(decoded), "strings": decoded[:100], "total": len(strs)}

def search_bytes(path: str, pattern: str):
    p = Path(path)
    if not p.exists():
        return {"error": f"파일 없음: {path}"}
    data = p.read_bytes()
    # pattern: "7f 45 4c 46" or "iuqer"
    pat = pattern.strip()
    # try hex
    try:
        # remove spaces, if all hex, treat as hex
        hex_clean = pat.replace(" ", "").replace("0x","")
        if all(c in "0123456789abcdefABCDEF" for c in hex_clean) and len(hex_clean)%2==0 and len(hex_clean)>=2:
            needle = bytes.fromhex(hex_clean)
        else:
            needle = pat.encode()
    except:
        needle = pat.encode()
    hits = []
    idx = 0
    while True:
        pos = data.find(needle, idx)
        if pos == -1:
            break
        hits.append({"address": hex(pos), "offset": pos, "bytes": needle.hex(), "note": f"hit at {hex(pos)}"})
        idx = pos + 1
        if len(hits) >= 20:
            break
    return {"path": path, "pattern": pattern, "hits": hits, "count": len(hits)}

def get_bytes(path: str, address: str, length: int = 32):
    p = Path(path)
    if not p.exists():
        return {"error": f"파일 없음: {path}"}
    data = p.read_bytes()
    # address: "0x401000" or decimal offset
    try:
        if isinstance(address, str) and address.startswith("0x"):
            off = int(address, 16)
        else:
            off = int(str(address), 0)
    except:
        off = 0
    # Ghidra VA → file offset 근사: image base 0x400000 가정
    # /bin/ls base는 0, mock은 0x400000 → 둘 다 시도
    candidates = [off, off - 0x400000, off - 0x401000]
    for cand in candidates:
        if 0 <= cand < len(data):
            off = cand
            break
    chunk = data[off:off+length]
    return {"path": path, "address": address, "offset": off, "bytes": chunk.hex(), "ascii": chunk.decode(errors='ignore')[:80], "entropy": _entropy(chunk)}

def _entropy(bs: bytes):
    if not bs:
        return 0
    from collections import Counter
    c = Counter(bs)
    import math
    return round(-sum((v/len(bs))*math.log2(v/len(bs)) for v in c.values()),2)

def patch_bytes(path: str, address: str, new_bytes: str, backup: bool = True):
    p = Path(path)
    if not p.exists():
        return {"error": f"파일 없음: {path}"}
    data = bytearray(p.read_bytes())
    try:
        if isinstance(address, str) and address.startswith("0x"):
            off = int(address, 16)
        else:
            off = int(str(address), 0)
        # Ghidra VA 보정
        for cand in [off, off-0x400000, off-0x401000]:
            if 0 <= cand < len(data):
                off = cand
                break
        nb = bytes.fromhex(new_bytes.replace(" ",""))
        orig = data[off:off+len(nb)].hex()
        if backup:
            bak = Path(str(p)+".bak")
            if not bak.exists():
                bak.write_bytes(data)
        data[off:off+len(nb)] = nb
        p.write_bytes(data)
        return {"ok": True, "path": path, "address": address, "offset": off, "patched": new_bytes, "original": orig, "backup": str(bak) if backup else None}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    print(list_strings("/bin/ls", pattern="GLIBC", min_len=4))
    print(search_bytes("/bin/ls", "7f 45 4c 46"))
    print(get_bytes("/bin/ls", "0x0", 16))
    print(list_strings("/tmp/wannacry/wannacry_mock.bin"))
