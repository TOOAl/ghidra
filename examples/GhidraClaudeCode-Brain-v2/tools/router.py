"""
tools/router.py — Claude Code tool_runner 대응

readOnly 도구는 병렬, 쓰기 도구는 직렬.
Ghidra REAL 모드: GHIDRA_INSTALL_DIR 있으면 headless, 없으면 mock.
"""
import os, pathlib, subprocess, json, concurrent.futures

ROOT = pathlib.Path(__file__).parent.parent
MEM = ROOT / "memory"

# mock 데이터 — Phase 1용, Ghidra 없이도 동작
MOCK_FUNCS = [
    {"name": "main", "addr": "0x401000", "size": 320},
    {"name": "FUN_00401200", "addr": "0x401200", "size": 89},
    {"name": "check_license", "addr": "0x401350", "size": 210},
]
MOCK_STRS = ["http://c2.evil.com", "license check failed", "AES_KEY_1234", "UPX!", "UPX0"]

class Router:
    def __init__(self, root=None):
        self.root = pathlib.Path(root) if root else ROOT
        self.is_real = bool(os.getenv("GHIDRA_INSTALL_DIR"))
        # definitions 로드 — readOnly 플래그 확인용
        try:
            with open(self.root / "tools/definitions.json", encoding="utf-8") as f:
                self.defs = {d["name"]: d for d in json.load(f)}
        except:
            self.defs = {}

    def is_readonly(self, name: str) -> bool:
        return self.defs.get(name, {}).get("readOnly", True)

    def dispatch(self, name: str, inp: dict) -> dict:
        """단일 도구 실행 — router.dispatch(name, input)"""
        if name == "list_functions":
            return self._list_functions(inp)
        if name == "list_strings":
            return self._list_strings(inp)
        if name == "code_read":
            return self._code_read(inp)
        if name == "code_write":
            return self._code_write(inp)
        if name == "code_exec":
            return self._code_exec(inp)
        return {"ok": False, "error": f"unknown tool: {name}"}

    def dispatch_parallel(self, calls: list) -> list:
        """
        Claude Code 병렬 규칙 구현:
        - 연속된 readOnly 도구들은 병렬 (ThreadPool)
        - 쓰기 도구는 직렬 (순서 보장)
        calls: [{"name": str, "input": dict, "id": str}, ...]
        반환: [{"id": str, "result": dict}, ...] — 입력 순서 유지
        """
        results = []
        # readOnly 배치를 찾아 병렬 실행
        i = 0
        while i < len(calls):
            # readOnly 연속 구간 찾기
            j = i
            while j < len(calls) and self.is_readonly(calls[j]["name"]):
                j += 1
            if j > i:
                # 병렬 구간
                batch = calls[i:j]
                with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
                    futs = {ex.submit(self.dispatch, c["name"], c["input"]): c for c in batch}
                    batch_results = {}
                    for fut in concurrent.futures.as_completed(futs):
                        c = futs[fut]
                        try:
                            batch_results[c["id"]] = fut.result()
                        except Exception as e:
                            batch_results[c["id"]] = {"ok": False, "error": str(e)}
                    for c in batch:
                        results.append({"id": c["id"], "result": batch_results[c["id"]]})
                i = j
            else:
                # 쓰기 1개는 직렬
                c = calls[i]
                try:
                    r = self.dispatch(c["name"], c["input"])
                except Exception as e:
                    r = {"ok": False, "error": str(e)}
                results.append({"id": c["id"], "result": r})
                i += 1
        return results

    # --- 개별 구현 ---

    def _list_functions(self, inp: dict) -> dict:
        filt = inp.get("filter", "")
        limit = inp.get("limit", 50)
        funcs = MOCK_FUNCS
        if filt:
            funcs = [f for f in funcs if filt.lower() in f["name"].lower()]
        return {"ok": True, "functions": funcs[:limit]}

    def _list_strings(self, inp: dict) -> dict:
        filt = inp.get("filter", "")
        strs = MOCK_STRS
        if filt:
            strs = [s for s in strs if filt.lower() in s.lower()]
        return {"ok": True, "strings": strs}

    def _code_read(self, inp: dict) -> dict:
        from tools.permissions import check  # noqa
        p = inp.get("path", "")
        if not p:
            return {"ok": False, "error": "path 필요"}
        # safe_path — ROOT 안에서만
        full = (self.root / p).resolve()
        if not str(full).startswith(str(self.root.resolve())):
            return {"ok": False, "error": "허용되지 않은 경로"}
        if not full.exists():
            return {"ok": False, "error": f"파일 없음: {p}"}
        if full.stat().st_size > 200_000:
            return {"ok": False, "error": "200KB 제한"}
        return {"ok": True, "path": p, "content": full.read_text(encoding="utf-8", errors="replace"), "size": full.stat().st_size}

    def _code_write(self, inp: dict) -> dict:
        p = inp.get("path", "")
        content = inp.get("content", "")
        if not p:
            return {"ok": False, "error": "path 필요"}
        full = (self.root / p).resolve()
        if not str(full).startswith(str(self.root.resolve())):
            return {"ok": False, "error": "허용되지 않은 경로"}
        # py 파일은 컴파일 검사
        if full.suffix == ".py":
            try:
                compile(content, str(full), "exec")
            except SyntaxError as se:
                return {"ok": False, "error": f"문법 오류 {se.lineno}줄: {se.msg}", "line": se.lineno}
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(content, encoding="utf-8")
        return {"ok": True, "path": p, "size": len(content.encode("utf-8"))}

    def _code_exec(self, inp: dict) -> dict:
        from tools.permissions import check
        cmd = inp.get("cmd", "")
        perm = check(cmd)
        if not perm["ok"]:
            return {"ok": False, "error": perm["reason"]}
        try:
            r = subprocess.run(cmd, shell=True, cwd=str(self.root), capture_output=True, text=True, timeout=15)
            out = (r.stdout or "") + (r.stderr or "")
            if len(out) > 8000:
                out = out[:8000] + "\n... 잘림"
            return {"ok": r.returncode == 0, "cmd": cmd, "exit": r.returncode, "output": out or "(출력 없음)"}
        except subprocess.TimeoutExpired:
            return {"ok": False, "error": "타임아웃 15초"}
        except Exception as e:
            return {"ok": False, "error": str(e)}
