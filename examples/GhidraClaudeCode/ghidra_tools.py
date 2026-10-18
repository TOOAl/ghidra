"""
ghidra_tools.py — Ghidra 기능을 LLM Tool 로 노출

Claude Code가 파일시스템을 다루듯, GhidraClaudeCode는 바이너리 DB를 다룬다.
각 함수는 anthropic.types.ToolParam 스펙을 따른다.
"""
from pathlib import Path

# ---------------------------------------------------------------------------
# 1. Tool Definitions (JSON Schema) — LLM에게 노출되는 인터페이스
# ---------------------------------------------------------------------------
GHIDRA_TOOLS = [
    {
        "name": "list_functions",
        "description": "프로그램 내 모든 함수 목록 반환. 이름, 주소, 크기 포함. 먼저 전체 구조 파악할 때 사용.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filter": {"type": "string", "description": "이름 필터 (예: 'FUN_', 'main', 정규식)"},
                "limit": {"type": "integer", "description": "최대 반환 개수", "default": 50}
            }
        }
    },
    {
        "name": "decompile_function",
        "description": "특정 함수를 C 의사코드로 디컴파일. 리버싱 핵심 도구.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "함수 이름 또는 주소 (예: 'FUN_00401000', 'main')"},
                "include_xrefs": {"type": "boolean", "description": "호출자/피호출자 함께 포함", "default": False}
            },
            "required": ["name"]
        }
    },
    {
        "name": "list_strings",
        "description": "바이너리 내 문자열 검색. 암호 키, URL, 에러 메시지 탐지에 유용.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filter": {"type": "string", "description": "문자열 필터"},
                "limit": {"type": "integer", "default": 100}
            }
        }
    },
    {
        "name": "get_xrefs",
        "description": "특정 함수/주소에 대한 교차 참조 (누가 호출하는지 / 무엇을 호출하는지)",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "함수 이름 또는 주소"},
                "direction": {"type": "string", "enum": ["to", "from", "both"], "default": "both"}
            },
            "required": ["name"]
        }
    },
    {
        "name": "rename_function",
        "description": "함수 이름 변경. 분석 결과를 DB에 반영 (Claude Code의 파일 쓰기와 동일)",
        "input_schema": {
            "type": "object",
            "properties": {
                "old_name": {"type": "string"},
                "new_name": {"type": "string"}
            },
            "required": ["old_name", "new_name"]
        }
    },
    {
        "name": "set_comment",
        "description": "함수/주소에 주석 추가. 분석 지식 축적.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "comment": {"type": "string"}
            },
            "required": ["name", "comment"]
        }
    },
    {
        "name": "list_imports",
        "description": "Import 테이블 (외부 라이브러리 함수) 목록. 바이너리 행위 추론에 핵심.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "search_bytes",
        "description": "바이트 패턴 검색 (예: 암호 상수, shellcode 시그니처)",
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "hex 패턴, 예: '48 8d ?? ??'"},
            },
            "required": ["pattern"]
        }
    },
]

# ---------------------------------------------------------------------------
# 2. Tool Implementations — 실제 Ghidra API 호출
#    (PyGhidra가 설치된 환경에서는 주석 해제하여 동작)
# ---------------------------------------------------------------------------
class GhidraBackend:
    """
    PyGhidra 기반 백엔드. headless 모드로 동작하므로 GUI 불필요.
    실제 사용 시: pip install pyghidra 후 GHIDRA_INSTALL_DIR 설정.
    """
    def __init__(self, binary_path: str):
        self.binary_path = Path(binary_path)
        self.program = None
        self.flat_api = None
        self._init_ghidra()

    def _init_ghidra(self):
        # --- 실제 환경에서 활성화 ---
        # import pyghidra
        # pyghidra.start()
        # from pyghidra import open_program
        # self.flat_api = open_program(str(self.binary_path), analyze=True)
        # self.program = self.flat_api.getCurrentProgram()
        #
        # --- 데모용 mock ---
        print(f"[GhidraBackend] (mock) Loading {self.binary_path}")
        print("[GhidraBackend] pyghidra.start() → Program loaded + auto-analysis 완료")

    # 각 Tool의 실행 로직 (예시: list_functions)
    def list_functions(self, filter: str = "", limit: int = 50):
        # 실제 구현 예:
        # fm = self.program.getFunctionManager()
        # funcs = [f for f in fm.getFunctions(True) if filter in f.getName()]
        # return [{"name": f.getName(), "addr": str(f.getEntryPoint()), "size": f.getBody().getNumAddresses()} for f in funcs[:limit]]
        return {
            "mock": True,
            "functions": [
                {"name": "main", "addr": "0x004011a0", "size": 342},
                {"name": "FUN_00401200", "addr": "0x00401200", "size": 89},
                {"name": "check_license", "addr": "0x00401350", "size": 210},
            ],
            "note": "실제 환경에서는 pyghidra API가 실제 함수 목록 반환"
        }

    def decompile_function(self, name: str, include_xrefs: bool = False):
        # from ghidra.app.decompiler import DecompInterface
        # decompiler = DecompInterface()
        # decompiler.openProgram(self.program)
        # res = decompiler.decompileFunction(func, 30, monitor)
        # return res.getDecompiledFunction().getC()
        return {
            "mock": True,
            "name": name,
            "c_code": f"// Decompiled {name}\nint {name}() {{\n  // ... Ghidra decompiler output ...\n  if (license_valid == 0) return -1;\n}}",
        }

    def dispatch(self, tool_name: str, tool_input: dict):
        """LLM이 요청한 tool을 실제 Ghidra API로 라우팅"""
        fn = getattr(self, tool_name, None)
        if not fn:
            return {"error": f"Unknown tool: {tool_name}"}
        return fn(**tool_input)
