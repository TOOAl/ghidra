"""
tools/ghidra_router.py — REA + Ghidra 플러그인 읽기/쓰기 라우터

- 읽기 (REA Provider): list_functions, decompile, get_xrefs, list_strings
  → REA가 이미 Ghidra로 분석한 결과를 MCP로 가져옴 (무료, 읽기전용)
- 쓰기 (Ghidra Plugin): rename_function, set_comment
  → 네가 만든 플러그인이 Ghidra DB에 직접 씀
- 기억 (Memory): search_memory
  → 로컬 Vector DB에서 유사 사례 검색

이 라우터가 "읽기+쓰기+여러 포맷"을 하나로 합치는 접착제.
"""
import json
from pathlib import Path

class GhidraRouter:
    def __init__(self, rea_client=None, ghidra_plugin_url=None, memory=None):
        """
        rea_client: REA MCP 클라이언트 (예: mcp.Client)
        ghidra_plugin_url: 네 플러그인의 HTTP 엔드포인트 (예: http://127.0.0.1:8080)
        memory: Memory 객체
        """
        self.rea = rea_client
        self.plugin_url = ghidra_plugin_url
        self.memory = memory

    def dispatch(self, name: str, inp: dict) -> dict:
        # 1. 기억 검색 — 로컬에서 처리
        if name == "search_memory" and self.memory:
            return self.memory.search(inp.get("query", ""), k=inp.get("k", 3))

        # 2. 쓰기 — Ghidra 플러그인으로 (patch 포함)
        if name in ("rename_function", "set_comment", "set_plate_comment", "patch_bytes", "create_label") and self.plugin_url:
            return self._call_plugin(name, inp)

        # 3. 읽기 — REA로
        if self.rea:
            try:
                return self.rea.call_tool(name, inp)
            except Exception as e:
                return {"error": f"REA 호출 실패: {e}", "fallback": "mock"}

        # 4. Mock (REA/Ghidra 없이도 데모 가능)
        return self._mock(name, inp)

    def _call_plugin(self, name: str, inp: dict) -> dict:
        import requests
        # plugin URL이 / 로 끝나면 그대로, 아니면 name 붙이기
        url = self.plugin_url.rstrip("/")
        if not url.endswith(name):
            url = f"{url}/{name}"
        try:
            resp = requests.post(url, json=inp, timeout=5)
            try:
                return resp.json()
            except Exception:
                return {"ok": resp.status_code == 200, "message": resp.text[:800], "status": resp.status_code}
        except Exception as e:
            return {"error": f"Plugin 호출 실패: {e}", "input": inp, "url": url}

    def _mock(self, name: str, inp: dict) -> dict:
        mocks = {
            "list_functions": {"functions": [
                {"name": "main", "addr": "0x401000", "size": 320},
                {"name": "FUN_00401200", "addr": "0x401200", "size": 89},
                {"name": "check_license", "addr": "0x401350", "size": 210},
            ]},
            "decompile": {"name": inp.get("name"), "c_code": f"// {inp.get('name')} 의사코드\nint {inp.get('name')}() {{ if (auth==0) return -1; }}"},
            "list_strings": {"strings": ["http://c2.evil.com", "license check failed", "AES_KEY_1234", "UPX!", "UPX0"]},
            "get_xrefs": {"to": ["main"], "from": ["strcmp", "send"]},
            "list_imports": {"imports": ["kernel32.dll!CreateFileA", "advapi32.dll!CryptEncrypt", "ws2_32.dll!send", "ntdll.dll!NtProtectVirtualMemory"]},
            "search_bytes": {"pattern": inp.get("pattern"), "hits": [{"address": "0x00401500", "bytes": "63 7C 77 7B", "note": "AES S-box 시그니처"}]},
            "get_bytes": {"address": inp.get("address"), "bytes": "42 43 44 45 " * 8, "ascii": "BCDEFG...", "entropy": 7.2},
            "patch_bytes": {"ok": True, "address": inp.get("address"), "patched": inp.get("bytes"), "comment": inp.get("comment"), "backup": "원본 바이트는 Ghidra undo로 복구 가능"},
            "rename_function": {"ok": True, "old": inp.get("old_name"), "new": inp.get("new_name")},
            "set_comment": {"ok": True},
            "search_memory": {"results": [
                {"case": "2024-10 악성코드 A", "similarity": 0.91, "note": "동일한 C2 패턴"},
                {"case": "2025-01 CVE-2024-1234", "similarity": 0.87, "note": "버퍼오버플로우 유사"},
            ]},
            "list_js_modules": {"asar": inp.get("asar_path", "app.asar"), "modules": ["editor/block.ts", "editor/toggle.ts", "sync/offline.ts", "sync/queue.ts", "database/query.ts", "database/rollup.ts", "notion/ipc.ts"]},
            "get_js_source": {"module": inp.get("module"), "source": f"// {inp.get('module')} — Notion 패턴 (mock)\n// Block CRDT, sync queue, DB query 로직\n// 이 패턴을 notion/ 폴더 3기능으로 재구현\n"},
            "list_ipc_channels": {"channels": ["notion:sync", "notion:db-query", "notion:block-update", "notion:offline-queue"]},
            "list_dotnet_info": {"path": inp.get("path"), "assemblies": ["Notion.Desktop.dll"]},
            "list_firmware_info": {"path": inp.get("path"), "regions": ["squashfs", "u-boot"]},
            "get_website_structure": {"url": inp.get("url"), "title": "Notion — block-based workspace", "scripts": ["app.js"]},
            "create_block": {"ok": True, "type": inp.get("type", "text"), "id": "blk_" + inp.get("content", "")[:8].replace(" ", "_")},
            "query_database": {"filter": inp.get("filter"), "results": [{"task": "C2 분석", "model": "qwen/qwen3-32b:free", "date": "2026-10-18"}]},
            "queue_sync": {"ok": True, "queued": inp.get("task"), "queue_len": 1},
        }
        return mocks.get(name, {"mock": True, "input": inp})
