"""
Self-Evolving Reverse-Engineering & Code Forge (Stage C · 6-Stage Synapse Workshop).

Harmonizes:
- 4 Core Abilities (4대 핵심 능력):
  1. 분해·파악·해석 (Ghidra 12.3 Headless Bridge + Pure-Python ELF64/PE32+/Firmware X-Ray)
  2. 우리 두뇌식 코딩 접목 (Algorithm Blueprint -> Clean Python Skill Synthesis & Live Editor)
  3. 잘못된 부분 찾아내기 (AST Defect Scanner + Differential Twin Fuzzing + Line-Level Diagnostics)
  4. 수정하기 (Surgical Auto-Repair + User Live Patching + Before/After Diff)
- 5 Essential Organs (5가지 필수 기관):
  ① 🧬 기계어 → 핵심 원리 설계도 번역기 (Algorithm Blueprint Translator)
  ② 🧪 투명 유리방 실험실 & 쌍둥이 정답 대조기 (Isolated Subprocess Sandbox & Twin Verifier)
  ③ 🔍 원인 역추적 돋보기 (Line-Number & Failing-Input Root-Cause Magnifier)
  ④ ⏪ 타임머신 세이브 포인트 (Snapshot History + Before/After Diff + 0.1s Rollback)
  ⑤ 🧩 스킬 카트리지 슬롯 & 🚦 복어 독 제거기 (AST Toxin Sanitizer + .py / .sbrain / Wiki Installer)
"""

from __future__ import annotations

import ast
import base64
import difflib
import hashlib
import json
import math
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from brain_engine.core_ability_engine import field_coding_classes_of, field_coding_suspects

from brain_engine.quant_forge import BLOCK_SIZE, MAGIC, quantize_tensor_int4


# ---------------------------------------------------------------------------
# Deterministic Authentic Binary Specimen Builder (ELF64 / PE32+ / Firmware)
# ---------------------------------------------------------------------------
def _build_elf64_specimen(code_bytes: bytes, rodata_bytes: bytes, extra_sec: Tuple[str, bytes]) -> bytes:
    """Constructs a real, parseable 64-bit x86-64 ELF binary with section headers & shstrtab."""
    sec_names = ["", ".text", ".rodata", extra_sec[0], ".shstrtab"]
    shstrtab = b"\x00" + b"\x00".join(s.encode("ascii") for s in sec_names[1:]) + b"\x00"

    def _name_off(name: str) -> int:
        if not name:
            return 0
        return shstrtab.index(name.encode("ascii") + b"\x00")

    ehdr_size = 64
    phdr_size = 56
    off_text = ehdr_size + phdr_size
    off_rodata = off_text + len(code_bytes)
    off_extra = off_rodata + len(rodata_bytes)
    off_shstr = off_extra + len(extra_sec[1])
    off_shdr = (off_shstr + len(shstrtab) + 7) & ~7
    pad_before_shdr = b"\x00" * (off_shdr - (off_shstr + len(shstrtab)))

    e_ident = b"\x7fELF" + bytes([2, 1, 1, 0]) + b"\x00" * 8  # 64-bit, little-endian, SYSV
    ehdr = e_ident + struct.pack(
        "<HHIQQQIHHHHHH",
        2,              # ET_EXEC
        0x3E,           # EM_X86_64
        1,              # EV_CURRENT
        0x401000,       # e_entry
        ehdr_size,      # e_phoff
        off_shdr,       # e_shoff
        0,              # e_flags
        ehdr_size,      # e_ehsize
        phdr_size,      # e_phentsize
        1,              # e_phnum
        64,             # e_shentsize
        5,              # e_shnum
        4,              # e_shstrndx
    )
    total_load = off_shstr
    phdr = struct.pack(
        "<IIQQQQQQ",
        1,              # PT_LOAD
        5,              # PF_R | PF_X
        0,
        0x400000,
        0x400000,
        total_load,
        total_load,
        0x1000,
    )

    def _shdr(name: str, sh_type: int, flags: int, addr: int, offset: int, size: int) -> bytes:
        return struct.pack(
            "<IIQQQQIIQQ",
            _name_off(name),
            sh_type,
            flags,
            addr,
            offset,
            size,
            0,
            0,
            16,
            0,
        )

    shdrs = (
        _shdr("", 0, 0, 0, 0, 0)
        + _shdr(".text", 1, 0x6, 0x401000, off_text, len(code_bytes))
        + _shdr(".rodata", 1, 0x2, 0x402000, off_rodata, len(rodata_bytes))
        + _shdr(extra_sec[0], 1, 0x3, 0x403000, off_extra, len(extra_sec[1]))
        + _shdr(".shstrtab", 3, 0x0, 0, off_shstr, len(shstrtab))
    )
    return ehdr + phdr + code_bytes + rodata_bytes + extra_sec[1] + shstrtab + pad_before_shdr + shdrs


def _build_pe64_specimen(code_bytes: bytes, rdata_bytes: bytes) -> bytes:
    """Constructs a real, parseable PE32+ (Windows x86-64 EXE) binary with COFF & section table."""
    dos = bytearray(0x80)
    dos[0:2] = b"MZ"
    dos[0x3C:0x40] = struct.pack("<I", 0x80)
    stub = b"Synapse PE32+ Specimen Stub\r\n$"
    dos[0x40 : 0x40 + len(stub)] = stub

    pe_sig = b"PE\x00\x00"
    coff = struct.pack(
        "<HHIIIHH",
        0x8664,  # IMAGE_FILE_MACHINE_AMD64
        2,       # NumberOfSections
        0x672F0000,
        0,
        0,
        240,     # SizeOfOptionalHeader (PE32+)
        0x0022,  # EXECUTABLE_IMAGE | LARGE_ADDRESS_AWARE
    )
    opt = bytearray(240)
    struct.pack_into("<HBBIIIIIQII", opt, 0,
                     0x20B, 14, 0, len(code_bytes), len(rdata_bytes), 0,
                     0x1000, 0x1000, 0x140000000, 0x1000, 0x200)
    struct.pack_into("<II", opt, 56, 0x4000, 0x200)

    def _pe_sec(name: bytes, vsize: int, rva: int, raw_size: int, raw_ptr: int, chars: int) -> bytes:
        nm = name.ljust(8, b"\x00")[:8]
        return nm + struct.pack("<IIIIIIHHI", vsize, rva, raw_size, raw_ptr, 0, 0, 0, 0, chars)

    raw_text = code_bytes.ljust(0x200, b"\x90")
    raw_rdata = rdata_bytes.ljust(0x200, b"\x00")
    sec_hdrs = (
        _pe_sec(b".text", len(code_bytes), 0x1000, 0x200, 0x200, 0x60000020)
        + _pe_sec(b".rdata", len(rdata_bytes), 0x2000, 0x200, 0x400, 0x40000040)
    )
    headers = (bytes(dos) + pe_sig + coff + bytes(opt) + sec_hdrs).ljust(0x200, b"\x00")
    return headers + raw_text + raw_rdata


def _high_entropy_blob(seed_label: str, length: int = 256) -> bytes:
    out = bytearray()
    counter = 0
    while len(out) < length:
        out.extend(hashlib.sha256(f"{seed_label}:{counter}".encode("utf-8")).digest())
        counter += 1
    return bytes(out[:length])


# ---------------------------------------------------------------------------
# Specimen Catalog (Ground-Truth Twin Vectors + Initial Buggy Port + Repair)
# ---------------------------------------------------------------------------
# Dream quests registered at runtime by the Evolution Heartbeat (Stage D).
# Kept separate from SPECIMEN_CATALOG so the UI specimen chips stay tidy.
DREAM_QUEST_CATALOG: Dict[str, Dict[str, Any]] = {}

SPECIMEN_CATALOG: Dict[str, Dict[str, Any]] = {
    "xor_rot_vault": {
        "id": "xor_rot_vault",
        "filename": "specimen_xor_vault.elf",
        "title": "🔐 XOR-회전 금고 해독기 (ELF64 x86-64)",
        "badge": "비트 연산 · 8비트 오버플로 함정",
        "summary": "각 바이트에 0x5A를 XOR한 뒤 8비트 좌회전(ROL 3)과 위치 인덱스를 더해 금고 토큰을 만드는 실행파일입니다.",
        "entry_fn": "transform_payload",
        "mentors": ["앨런 튜링", "클로드 섀넌", "데니스 리치"],
        "pseudo_asm": [
            "0x401000: 55                 push rbp",
            "0x401001: 48 89 e5           mov  rbp, rsp",
            "0x401008: 34 5a              xor  al, 0x5a          ; 1) 열쇠 0x5A 대칭 XOR",
            "0x40100a: c0 c0 03           rol  al, 0x03          ; 2) 8비트 레지스터 좌회전 3칸",
            "0x40100d: 00 d8              add  al, bl            ; 3) 위치 인덱스(idx) 가산 (8비트 wrap)",
            "0x401012: c3                 ret",
        ],
        "blueprint": {
            "core_formula": "out[i] = (ROL8(byte[i] ^ 0x5A, 3) + i) & 0xFF",
            "inputs": "data: list[int] (0~255 바이트 정수 배열)",
            "invariants": [
                "어셈블리 AL 레지스터는 항상 8비트(0~255) 안에서만 회전·덧셈됨",
                "좌회전 3칸 공식: ((x << 3) & 0xFF) | (x >> 5)",
                "빈 배열([]) 입력 시 에러 없이 즉시 [] 반환",
            ],
            "outputs": "list[int] (모든 원소가 반드시 0 <= v <= 255 범위)",
            "mentor_comment": "데니스 리치 & 튜링: 기계어의 8비트 레지스터(AL)를 무한 정수인 파이썬으로 옮길 때는 반드시 매 단계 `& 0xFF` 울타리를 쳐야 비트 넘침을 막을 수 있습니다!",
        },
        "initial_buggy_code": (
            "def transform_payload(data):\n"
            "    \"\"\"1차 자동 이식 초안 (숨은 이식 버그 포함)\"\"\"\n"
            "    if not data:\n"
            "        return [0]  # [버그 1] 빈 입력인데 엉뚱한 [0] 반환\n"
            "    out = []\n"
            "    for idx, b in enumerate(data):\n"
            "        x = b ^ 0x5A\n"
            "        # [버그 2] 파이썬 정수는 무한 비트라 & 0xFF 없이 << 3 하면 255를 초과함!\n"
            "        rol = (x << 3) | (x >> 5)\n"
            "        out.append(rol + idx)\n"
            "    return out\n"
        ),
        "repaired_code": (
            "def transform_payload(data):\n"
            "    \"\"\"수리 완료: 8비트 레지스터 불변식(& 0xFF) 및 빈 배열 방어 완비\"\"\"\n"
            "    if not data:\n"
            "        return []\n"
            "    out = []\n"
            "    for idx, b in enumerate(data):\n"
            "        x = (int(b) & 0xFF) ^ 0x5A\n"
            "        rol = ((x << 3) & 0xFF) | (x >> 5)\n"
            "        out.append((rol + idx) & 0xFF)\n"
            "    return out\n"
        ),
        "twin_tests": [
            {"name": "단일 영점 바이트", "args": [[0x00]], "expected": [210]},
            {"name": "열쇠 자기소거(0x5A)", "args": [[0x5A]], "expected": [0]},
            {"name": "상위 비트 경계(0x81)", "args": [[0x81]], "expected": [222]},
            {"name": "연속 패킷 4바이트", "args": [[0x10, 0x20, 0xFF, 0x81]], "expected": [82, 212, 47, 225]},
            {"name": "3바이트 연속 오프셋", "args": [[0x7F, 0x7F, 0x7F]], "expected": [41, 42, 43]},
            {"name": "빈 배열 안전 방어", "args": [[]], "expected": []},
        ],
    },
    "crc16_packet": {
        "id": "crc16_packet",
        "filename": "specimen_crc16_packet.exe",
        "title": "📡 산업용 패킷 무결성 검사기 (PE32+ EXE)",
        "badge": "루프 경계 Off-by-One · 16비트 마스킹",
        "summary": "통신 패킷이 깨지지 않았는지 다항식 0x1021(CRC-16/CCITT)로 16비트 지문을 계산하는 윈도우 실행파일입니다.",
        "entry_fn": "compute_crc16",
        "mentors": ["클로드 섀넌", "리누스 토르발스", "레온하르트 오일러"],
        "pseudo_asm": [
            "0x140001000: b8 ff ff 00 00     mov  eax, 0xffff       ; 초기 시드 0xFFFF",
            "0x140001008: c1 e2 08           shl  edx, 8            ; 바이트 상위 정렬",
            "0x14000100b: 31 d0              xor  eax, edx",
            "0x140001010: b9 08 00 00 00     mov  ecx, 8            ; 정확히 8비트 반복!",
            "0x140001018: 69 c0 21 10        xor  ax, 0x1021        ; 다항식 0x1021 반영",
        ],
        "blueprint": {
            "core_formula": "crc = 0xFFFF → 바이트별 (crc ^= b << 8) → 8회 비트 이동 & 0x1021 다항식 XOR → & 0xFFFF",
            "inputs": "packet: list[int] (패킷 바이트 배열)",
            "invariants": [
                "1바이트는 8비트이므로 내부 비트 루프는 반드시 정확히 8번(`range(8)`) 돌아야 함",
                "좌시프트 후 `0xFFFF` 16비트 마스크를 유지해야 상위 비트 오염이 없음",
            ],
            "outputs": "int (0 ~ 65535 사이의 16비트 무결성 체크섬)",
            "mentor_comment": "클로드 섀넌: 단 1비트의 루프 누락(`range(7)`)만 있어도 정보 엔트로피 검증력이 절반으로 무너집니다!",
        },
        "initial_buggy_code": (
            "def compute_crc16(packet):\n"
            "    \"\"\"1차 자동 이식 초안 (루프 횟수 및 16비트 마스크 결함)\"\"\"\n"
            "    crc = 0xFFFF\n"
            "    for b in packet:\n"
            "        crc ^= (b << 8)\n"
            "        for _ in range(7):  # [버그 1] 8비트가 아니라 7번만 회전하는 Off-by-One 오류!\n"
            "            if crc & 0x8000:\n"
            "                crc = (crc << 1) ^ 0x1021  # [버그 2] 0xFFFF 마스킹 누락!\n"
            "            else:\n"
            "                crc = crc << 1\n"
            "    return crc\n"
        ),
        "repaired_code": (
            "def compute_crc16(packet):\n"
            "    \"\"\"수리 완료: 정확한 8비트 순회 및 16비트 레지스터 마스킹 적용\"\"\"\n"
            "    crc = 0xFFFF\n"
            "    for b in packet:\n"
            "        crc ^= ((int(b) & 0xFF) << 8)\n"
            "        for _ in range(8):\n"
            "            if crc & 0x8000:\n"
            "                crc = ((crc << 1) ^ 0x1021) & 0xFFFF\n"
            "            else:\n"
            "                crc = (crc << 1) & 0xFFFF\n"
            "    return crc & 0xFFFF\n"
        ),
        "twin_tests": [
            {"name": "표준 ASCII '123456789'", "args": [[49, 50, 51, 52, 53, 54, 55, 56, 57]], "expected": 0x29B1},
            {"name": "빈 패킷 초기 시드", "args": [[]], "expected": 0xFFFF},
            {"name": "단일 0x00 바이트", "args": [[0x00]], "expected": 0xE1F0},
            {"name": "단일 0xFF 바이트", "args": [[0xFF]], "expected": 0xFF00},
            {"name": "헤더 [0xAA, 0x55]", "args": [[0xAA, 0x55]], "expected": 0xE5EA},
            {"name": "시냅스 매직 [83,89,78]", "args": [[83, 89, 78]], "expected": 0xD62F},
        ],
    },
    "puffer_rle_sanitizer": {
        "id": "puffer_rle_sanitizer",
        "filename": "specimen_puffer_dropper.elf",
        "title": "🐡 복어 독(위험 명령) 혼입 압축기 (보안 제거 실습)",
        "badge": "복어 독 제거기 작동 · 빈 배열 크래시 수리",
        "summary": "연속된 바이트를 빠르게 압축하는 알짜 RLE 알고리즘 속에 위험한 쉘 실행 명령(복어 독)이 섞여 있는 프로그램입니다.",
        "entry_fn": "compress_rle_safe",
        "mentors": ["마거릿 해밀턴", "에이다 러브레이스", "이순신"],
        "pseudo_asm": [
            "0x401000: 48 8d 3d 99 0f 00  lea  rdi, [rip+0xf99]  ; ⚠ 'sh -c rm -rf /tmp/x' 위험 호출 흔적!",
            "0x401014: 38 06              cmp  byte [rsi], al    ; 연속 바이트 비교 루프 (순수 RLE 코어)",
            "0x401018: 80 fc ff           cmp  ah, 0xff          ; 최대 255회 연속 카운트 제한",
            "0x401022: 88 27              mov  [rdi], ah         ; [개수, 값] 쌍 출력",
        ],
        "blueprint": {
            "core_formula": "연속 동일 바이트를 [반복횟수(최대 255), 바이트값] 쌍으로 평탄화 압축 (외부 쉘 호출 100% 영구 제거!)",
            "inputs": "stream: list[int] (원본 바이트 스트림)",
            "invariants": [
                "🚦 [복어 독 제거 원칙] os.system / subprocess / 파일 삭제 등 시스템 호출은 1줄도 남기지 않고 격리 삭제",
                "동일 바이트가 255개를 넘으면 255에서 끊고 새 묶음 시작",
                "빈 입력 `[]` 이 들어오면 `IndexError` 없이 `[]` 반환",
            ],
            "outputs": "list[int] ([count_1, val_1, count_2, val_2, ...] 순수 압축 배열)",
            "mentor_comment": "마거릿 해밀턴 & 이순신: 아무리 뛰어난 압축 기술이라도 시스템 명령(복어 독)이 섞여 있으면 두뇌에 들이기 전에 완벽히 발라내야 합니다!",
        },
        "initial_buggy_code": (
            "import os\n\n"
            "def compress_rle_safe(stream):\n"
            "    \"\"\"1차 자동 이식 초안 (위험한 시스템 호출 독 + 빈 배열 IndexError 포함!)\"\"\"\n"
            "    os.system('echo temp_trace > /tmp/puffer_trace')  # [복어 독!] 외부 쉘 실행 위험 명령\n"
            "    out = []\n"
            "    cur = stream[0]  # [버그!] stream이 빈 배열 [] 이면 즉시 IndexError 폭발!\n"
            "    count = 1\n"
            "    for b in stream[1:]:\n"
            "        if b == cur and count < 255:\n"
            "            count += 1\n"
            "        else:\n"
            "            out.extend([count, cur])\n"
            "            cur = b\n"
            "            count = 1\n"
            "    out.extend([count, cur])\n"
            "    return out\n"
        ),
        "repaired_code": (
            "def compress_rle_safe(stream):\n"
            "    \"\"\"수리 완료: 복어 독(os.system) 완전 제거 + 빈 배열 방어 + 255 상한 보존\"\"\"\n"
            "    if not stream:\n"
            "        return []\n"
            "    out = []\n"
            "    cur = int(stream[0]) & 0xFF\n"
            "    count = 1\n"
            "    for raw_b in stream[1:]:\n"
            "        b = int(raw_b) & 0xFF\n"
            "        if b == cur and count < 255:\n"
            "            count += 1\n"
            "        else:\n"
            "            out.extend([count, cur])\n"
            "            cur = b\n"
            "            count = 1\n"
            "    out.extend([count, cur])\n"
            "    return out\n"
        ),
        "twin_tests": [
            {"name": "연속 반복 압축", "args": [[7, 7, 7, 7, 2, 2, 9]], "expected": [4, 7, 2, 2, 1, 9]},
            {"name": "빈 스트림 방어", "args": [[]], "expected": []},
            {"name": "단일 원소 스트림", "args": [[42]], "expected": [1, 42]},
            {"name": "교차 패턴 [1,2,1,2]", "args": [[1, 2, 1, 2]], "expected": [1, 1, 1, 2, 1, 1, 1, 2]},
            {"name": "260개 연속 분할(255+5)", "args": [[99] * 260], "expected": [255, 99, 5, 99]},
            {"name": "0 바이트 시퀀스", "args": [[0, 0, 0]], "expected": [3, 0]},
        ],
    },
    "int8_clamp_filter": {
        "id": "int8_clamp_filter",
        "filename": "specimen_sliding_quant.bin",
        "title": "⚡ 센서 신호 INT8 이동평균 양자화 필터 (Firmware)",
        "badge": "실수/정수 나눗셈 오차 · 0 나눗셈 · 범위 클램프",
        "summary": "센서 신호의 튀는 잡음을 정수 이동평균으로 고르게 다듬고 INT8(-128~127) 범위로 안전하게 자르는 펌웨어 루틴입니다.",
        "entry_fn": "quantize_moving_avg",
        "mentors": ["폰 노이만", "안드레이 콜모고로프", "아르키메데스"],
        "pseudo_asm": [
            "0x08000100: 85 f6              test esi, esi          ; window <= 0 이면 1로 보정",
            "0x0800010c: 99                 cdq                    ; 부호 확장 후 정수 몫 계산",
            "0x0800010e: f7 fe              idiv esi               ; 정수 내림/절사 나눗셈",
            "0x08000116: 83 f8 7f           cmp  eax, 127          ; INT8 상한(+127) 클램프",
            "0x0800011c: 83 f8 80           cmp  eax, -128         ; INT8 하한(-128) 클램프",
        ],
        "blueprint": {
            "core_formula": "최근 W개 구간 합계를 정수 나눗셈(`int(total / count)`)한 뒤 [-128, +127] 범위로 클램프",
            "inputs": "samples: list[int], window: int",
            "invariants": [
                "window가 0 이하로 들어와도 ZeroDivisionError 없이 window=1로 안전 보정",
                "파이썬 실수 나눗셈(`/`) 대신 C/펌웨어와 동일한 0 방향 정수 절사(`int(s / cnt)`) 사용",
                "출력값은 언제나 INT8 범위 `-128 <= v <= 127` 보장",
            ],
            "outputs": "list[int] (INT8 양자화 필터 출력 배열)",
            "mentor_comment": "폰 노이만: 부동소수점(`float`)을 섞어버리면 하드웨어 펌웨어 결과와 미세하게 어긋나고, `-128~127` 클램프가 없으면 오버플로 잡음이 폭발합니다!",
        },
        "initial_buggy_code": (
            "def quantize_moving_avg(samples, window):\n"
            "    \"\"\"1차 자동 이식 초안 (실수 반환, 0 나눗셈, INT8 클램프 누락)\"\"\"\n"
            "    out = []\n"
            "    for i in range(len(samples)):\n"
            "        start = max(0, i - window + 1)\n"
            "        chunk = samples[start : i + 1]\n"
            "        # [버그 1] window=0 이면 chunk가 비어 0으로 나누기 폭발!\n"
            "        # [버그 2] / 연산으로 float가 나오고 [-128, 127] 클램프가 없음!\n"
            "        avg = sum(chunk) / len(chunk)\n"
            "        out.append(avg)\n"
            "    return out\n"
        ),
        "repaired_code": (
            "def quantize_moving_avg(samples, window):\n"
            "    \"\"\"수리 완료: window 안전 보정 + 0방향 정수 나눗셈 + INT8[-128,127] 클램프\"\"\"\n"
            "    if not samples:\n"
            "        return []\n"
            "    w = max(1, int(window))\n"
            "    out = []\n"
            "    for i in range(len(samples)):\n"
            "        start = max(0, i - w + 1)\n"
            "        chunk = samples[start : i + 1]\n"
            "        avg = int(sum(int(x) for x in chunk) / len(chunk))\n"
            "        clamped = max(-128, min(127, avg))\n"
            "        out.append(clamped)\n"
            "    return out\n"
        ),
        "twin_tests": [
            {"name": "3칸 이동평균 정수화", "args": [[10, 20, 33, 40], 3], "expected": [10, 15, 21, 31]},
            {"name": "INT8 상한(+127) 클램프", "args": [[200, 300], 2], "expected": [127, 127]},
            {"name": "INT8 하한(-128) 클램프", "args": [[-200, -150], 2], "expected": [-128, -128]},
            {"name": "음수 0방향 절사 확인", "args": [[-5, -2], 2], "expected": [-5, -3]},
            {"name": "window=0 입력 방어", "args": [[12, 24], 0], "expected": [12, 24]},
            {"name": "빈 신호 방어", "args": [[], 4], "expected": []},
        ],
    },
}


# ---------------------------------------------------------------------------
# Pure-Python Binary X-Ray Dissector + Ghidra 12.3 Bridge
# ---------------------------------------------------------------------------
def shannon_entropy_bytes(data: bytes) -> float:
    if not data:
        return 0.0
    n = len(data)
    counts = Counter(data)
    return round(-sum((c / n) * math.log2(c / n) for c in counts.values()), 3)


def extract_ascii_strings(data: bytes, min_len: int = 4, limit: int = 18) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    for m in re.finditer(rb"[\x20-\x7e]{" + str(min_len).encode("ascii") + rb",}", data):
        s = m.group(0).decode("ascii", errors="ignore").strip()
        if s:
            out.append({"offset": f"0x{m.start():04x}", "value": s[:90]})
        if len(out) >= limit:
            break
    return out


def parse_binary_xray(raw: bytes, filename: str) -> Dict[str, Any]:
    """Dissects real ELF64, PE32+, Mach-O, or Raw firmware bytes without external deps."""
    size = len(raw)
    sha256_hex = hashlib.sha256(raw).hexdigest()[:16]
    overall_entropy = shannon_entropy_bytes(raw)
    fmt = "Raw Firmware / Bytecode"
    arch = "x86-64 / ARM Pattern"
    entry_point = "0x00000000"
    sections: List[Dict[str, Any]] = []

    if raw[:4] == b"\x7fELF" and len(raw) >= 64:
        bits_cls = "ELF64" if raw[4] == 2 else "ELF32"
        fmt = f"{bits_cls} Executable"
        if raw[4] == 2:
            _, machine, _, e_entry, _, e_shoff, _, _, _, _, e_shentsize, e_shnum, e_shstrndx = struct.unpack(
                "<HHIQQQIHHHHHH", raw[16:64]
            )
            arch = {0x3E: "x86-64 (AMD64)", 0xB7: "ARM64 (AArch64)", 0x03: "x86"}.get(machine, f"Machine 0x{machine:x}")
            entry_point = f"0x{e_entry:08x}"
            if e_shoff and e_shnum and e_shoff + e_shnum * e_shentsize <= len(raw):
                shstr = b""
                if e_shstrndx < e_shnum:
                    st_pos = e_shoff + e_shstrndx * e_shentsize
                    _, _, _, _, st_off, st_sz, _, _, _, _ = struct.unpack("<IIQQQQIIQQ", raw[st_pos : st_pos + 64])
                    shstr = raw[st_off : st_off + st_sz]
                for idx in range(min(e_shnum, 16)):
                    pos = e_shoff + idx * e_shentsize
                    nm_off, sh_type, flags, addr, off, sz, _, _, _, _ = struct.unpack("<IIQQQQIIQQ", raw[pos : pos + 64])
                    if sh_type == 0 and sz == 0:
                        continue
                    nm = shstr[nm_off:].split(b"\x00", 1)[0].decode("ascii", errors="ignore") if nm_off < len(shstr) else f"sec_{idx}"
                    chunk = raw[off : off + sz] if off + sz <= len(raw) else b""
                    rwx = ("R" if flags & 0x2 or flags == 0 else "R") + ("W" if flags & 0x1 else "-") + ("X" if flags & 0x4 else "-")
                    sections.append(
                        {
                            "name": nm or f"sec_{idx}",
                            "addr": f"0x{addr:08x}",
                            "size": sz,
                            "entropy": shannon_entropy_bytes(chunk),
                            "rwx": rwx,
                        }
                    )
    elif raw[:2] == b"MZ" and len(raw) >= 0x100:
        pe_off = struct.unpack("<I", raw[0x3C:0x40])[0]
        if pe_off + 24 <= len(raw) and raw[pe_off : pe_off + 4] == b"PE\x00\x00":
            machine, num_sec, _, _, _, opt_sz, _ = struct.unpack("<HHIIIHH", raw[pe_off + 4 : pe_off + 24])
            fmt = "PE32+ Windows Executable (.exe/.dll)"
            arch = {0x8664: "x86-64 (AMD64)", 0x014C: "x86 (i386)", 0xAA64: "ARM64"}.get(machine, f"PE 0x{machine:x}")
            opt_start = pe_off + 24
            if opt_sz >= 28 and opt_start + 28 <= len(raw):
                ep_rva = struct.unpack("<I", raw[opt_start + 16 : opt_start + 20])[0]
                entry_point = f"0x1400{ep_rva:04x}"
            sec_table = opt_start + opt_sz
            for idx in range(min(num_sec, 12)):
                s_pos = sec_table + idx * 40
                if s_pos + 40 > len(raw):
                    break
                nm = raw[s_pos : s_pos + 8].rstrip(b"\x00").decode("ascii", errors="ignore")
                vsize, rva, rsize, rptr, _, _, _, _, chars = struct.unpack("<IIIIIIHHI", raw[s_pos + 8 : s_pos + 40])
                chunk = raw[rptr : rptr + rsize] if rptr + rsize <= len(raw) else b""
                rwx = ("R" if chars & 0x40000000 else "-") + ("W" if chars & 0x80000000 else "-") + ("X" if chars & 0x20000000 else "-")
                sections.append(
                    {
                        "name": nm or f".sec{idx}",
                        "addr": f"0x1400{rva:04x}",
                        "size": vsize or rsize,
                        "entropy": shannon_entropy_bytes(chunk),
                        "rwx": rwx,
                    }
                )

    if not sections:
        step = max(64, len(raw) // 3 or 1)
        for i, off in enumerate(range(0, len(raw), step)):
            chunk = raw[off : off + step]
            sections.append(
                {
                    "name": f".segment_{i}",
                    "addr": f"0x0800{off:04x}",
                    "size": len(chunk),
                    "entropy": shannon_entropy_bytes(chunk),
                    "rwx": "R-X" if i == 0 else "R--",
                }
            )

    # Detect opcode fingerprints inside raw bytes
    opcode_clues: List[str] = []
    if b"\x55\x48\x89\xe5" in raw:
        opcode_clues.append("x86-64 함수 프롤로그 (push rbp; mov rbp, rsp)")
    if b"\x34\x5a" in raw or b"\x31\xd0" in raw:
        opcode_clues.append("대칭 XOR 비트 변환 연산 감지 (xor reg, imm)")
    if b"\xc0\xc0\x03" in raw:
        opcode_clues.append("8비트 순환 비트 회전 감지 (rol al, 3)")
    if b"\x21\x10" in raw:
        opcode_clues.append("CRC-16/CCITT 다항식 상수 0x1021 감지")
    if b"rm -rf" in raw or b"os.system" in raw or b"/tmp/" in raw:
        opcode_clues.append("⚠️ 외부 쉘/경로 호출 흔적 감지 (복어 독 정밀 스캔 대상!)")
    if any(s["entropy"] >= 7.0 for s in sections):
        opcode_clues.append("고엔트로피(>=7.0 bits) 암호화·패킹 의심 섹션 포함")

    return {
        "filename": filename,
        "size_bytes": size,
        "sha256_short": sha256_hex,
        "format": fmt,
        "arch": arch,
        "entry_point": entry_point,
        "overall_entropy": overall_entropy,
        "sections": sections,
        "strings": extract_ascii_strings(raw),
        "opcode_clues": opcode_clues,
        "hex_preview": " ".join(f"{b:02x}" for b in raw[:48]),
    }


# ---------------------------------------------------------------------------
# Organ ⑤a: 🚦 Pufferfish Toxin Sanitizer (AST Security & Hazard Scanner)
# ---------------------------------------------------------------------------
FORBIDDEN_MODULES = {
    "os", "sys", "subprocess", "shutil", "socket", "urllib", "http",
    "ctypes", "multiprocessing", "threading", "pty", "pathlib", "pickle",
}
FORBIDDEN_CALLS = {
    "eval", "exec", "compile", "__import__", "open", "input", "breakpoint",
    "globals", "locals", "getattr", "setattr", "delattr",
}


def scan_code_toxins_and_syntax(code: str) -> Dict[str, Any]:
    """Scans Python code AST for dangerous syscalls/imports (복어 독) and syntax errors."""
    toxins: List[Dict[str, Any]] = []
    syntax_err: Optional[Dict[str, Any]] = None

    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        syntax_err = {
            "line": exc.lineno or 1,
            "msg": f"문법 오류(SyntaxError): {exc.msg}",
            "text": (exc.text or "").strip(),
        }
        return {"safe": False, "syntax_error": syntax_err, "toxins": []}

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root_mod = alias.name.split(".")[0]
                if root_mod in FORBIDDEN_MODULES:
                    toxins.append(
                        {
                            "line": getattr(node, "lineno", 1),
                            "kind": f"위험 모듈 반입 (import {alias.name})",
                            "reason": f"외부 시스템/파일/네트워크를 건드리는 `{alias.name}` 모듈은 복어 독으로 분류되어 차단됩니다.",
                        }
                    )
        elif isinstance(node, ast.ImportFrom):
            root_mod = (node.module or "").split(".")[0]
            if root_mod in FORBIDDEN_MODULES:
                toxins.append(
                    {
                        "line": getattr(node, "lineno", 1),
                        "kind": f"위험 모듈 반입 (from {node.module} import ...)",
                        "reason": f"`{node.module}` 시스템 제어 모듈 반입을 차단했습니다.",
                    }
                )
        elif isinstance(node, ast.Call):
            fn_name = ""
            if isinstance(node.func, ast.Name):
                fn_name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                base = node.func.value.id if isinstance(node.func.value, ast.Name) else ""
                fn_name = f"{base}.{node.func.attr}" if base else node.func.attr

            if fn_name in FORBIDDEN_CALLS or fn_name.startswith(("os.", "subprocess.", "shutil.", "socket.")):
                toxins.append(
                    {
                        "line": getattr(node, "lineno", 1),
                        "kind": f"위험 명령 호출 ({fn_name})",
                        "reason": f"실제 시스템에 영향을 줄 수 있는 `{fn_name}(...)` 호출이 감지되어 격리 차단했습니다!",
                    }
                )

    return {
        "safe": len(toxins) == 0 and syntax_err is None,
        "syntax_error": syntax_err,
        "toxins": toxins,
    }


# ---------------------------------------------------------------------------
# Organ ②: 🧪 Transparent Glass Sandbox & Twin Ground-Truth Verifier
# ---------------------------------------------------------------------------
_SANDBOX_HARNESS = r"""
import json, sys, time

payload = json.loads(sys.stdin.read())
code = payload["code"]
entry_fn = payload["entry_fn"]
tests = payload["tests"]

safe_builtins = {
    "abs": abs, "all": all, "any": any, "bin": bin, "bool": bool,
    "bytes": bytes, "bytearray": bytearray, "chr": chr, "dict": dict,
    "divmod": divmod, "enumerate": enumerate, "filter": filter, "float": float,
    "hex": hex, "int": int, "isinstance": isinstance, "len": len, "list": list,
    "map": map, "max": max, "min": min, "ord": ord, "pow": pow, "range": range,
    "reversed": reversed, "round": round, "set": set, "sorted": sorted,
    "str": str, "sum": sum, "tuple": tuple, "zip": zip,
    "Exception": Exception, "ValueError": ValueError, "IndexError": IndexError,
    "ZeroDivisionError": ZeroDivisionError, "TypeError": TypeError,
}

ns = {"__builtins__": safe_builtins}
t0 = time.perf_counter()
exec(compile(code, "<synapse_glass_sandbox>", "exec"), ns, ns)
fn = ns.get(entry_fn)
if not callable(fn):
    print(json.dumps({"fatal": f"함수 `{entry_fn}` 를 찾을 수 없습니다."}))
    sys.exit(0)

results = []
for tc in tests:
    args = tc["args"]
    expected = tc["expected"]
    try:
        actual = fn(*args)
        passed = (actual == expected) and (type(actual) is type(expected))
        results.append({
            "name": tc["name"],
            "args": args,
            "expected": expected,
            "actual": actual,
            "passed": passed,
            "error": None,
        })
    except Exception as exc:
        results.append({
            "name": tc["name"],
            "args": args,
            "expected": expected,
            "actual": None,
            "passed": False,
            "error": f"{type(exc).__name__}: {exc}",
        })

elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
print(json.dumps({"results": results, "elapsed_ms": elapsed_ms}, ensure_ascii=False))
"""


def run_in_glass_sandbox(code: str, entry_fn: str, twin_tests: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Executes candidate Python code inside an isolated Python -I subprocess with AST toxin gate."""
    scan = scan_code_toxins_and_syntax(code)
    if scan["syntax_error"]:
        return {
            "executed": False,
            "blocked_by_toxin": False,
            "syntax_error": scan["syntax_error"],
            "toxins": [],
            "passed_count": 0,
            "total_count": len(twin_tests),
            "pass_rate_pct": 0.0,
            "elapsed_ms": 0.0,
            "results": [],
        }
    if scan["toxins"]:
        return {
            "executed": False,
            "blocked_by_toxin": True,
            "syntax_error": None,
            "toxins": scan["toxins"],
            "passed_count": 0,
            "total_count": len(twin_tests),
            "pass_rate_pct": 0.0,
            "elapsed_ms": 0.0,
            "results": [],
        }

    payload = json.dumps({"code": code, "entry_fn": entry_fn, "tests": twin_tests}, ensure_ascii=False)
    try:
        proc = subprocess.run(
            [sys.executable, "-I", "-c", _SANDBOX_HARNESS],
            input=payload,
            text=True,
            capture_output=True,
            timeout=2.0,
        )
    except subprocess.TimeoutExpired:
        return {
            "executed": False,
            "blocked_by_toxin": False,
            "syntax_error": {"line": 1, "msg": "무한 루프 감지! 유리방 실험실이 2.0초 제한시간으로 안전 차단했습니다.", "text": ""},
            "toxins": [],
            "passed_count": 0,
            "total_count": len(twin_tests),
            "pass_rate_pct": 0.0,
            "elapsed_ms": 2000.0,
            "results": [],
        }

    if proc.returncode != 0 or not proc.stdout.strip():
        err_msg = (proc.stderr or "실행 오류").strip().splitlines()[-1]
        return {
            "executed": False,
            "blocked_by_toxin": False,
            "syntax_error": {"line": 1, "msg": err_msg, "text": ""},
            "toxins": [],
            "passed_count": 0,
            "total_count": len(twin_tests),
            "pass_rate_pct": 0.0,
            "elapsed_ms": 0.0,
            "results": [],
        }

    data = json.loads(proc.stdout)
    if "fatal" in data:
        return {
            "executed": False,
            "blocked_by_toxin": False,
            "syntax_error": {"line": 1, "msg": data["fatal"], "text": ""},
            "toxins": [],
            "passed_count": 0,
            "total_count": len(twin_tests),
            "pass_rate_pct": 0.0,
            "elapsed_ms": 0.0,
            "results": [],
        }

    results = data["results"]
    passed_cnt = sum(1 for r in results if r["passed"])
    total_cnt = max(1, len(results))
    return {
        "executed": True,
        "blocked_by_toxin": False,
        "syntax_error": None,
        "toxins": [],
        "passed_count": passed_cnt,
        "total_count": len(results),
        "pass_rate_pct": round((passed_cnt / total_cnt) * 100.0, 1),
        "elapsed_ms": data.get("elapsed_ms", 0.0),
        "results": results,
    }


# ---------------------------------------------------------------------------
# Organ ③: 🔍 Root-Cause Magnifier (Line-Level Defect & Cause Diagnosis)
# ---------------------------------------------------------------------------
def diagnose_defects(code: str, entry_fn: str, twin_tests: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Combines AST static inspection + toxin scan + glass sandbox twin run to pinpoint exact root causes."""
    lines = code.splitlines()
    findings: List[Dict[str, Any]] = []

    # 1. AST & Toxin Scan
    scan = scan_code_toxins_and_syntax(code)
    if scan["syntax_error"]:
        se = scan["syntax_error"]
        findings.append(
            {
                "severity": "critical",
                "badge": "🚨 문법 오류",
                "line": se["line"],
                "code_line": lines[se["line"] - 1].strip() if 1 <= se["line"] <= len(lines) else se.get("text", ""),
                "root_cause": se["msg"],
                "fix_hint": "괄호·콜론·들여쓰기 문법을 먼저 바로잡아야 실행할 수 있습니다.",
            }
        )
        return {"clean": False, "findings": findings, "sandbox": None}

    for tx in scan["toxins"]:
        ln = tx["line"]
        findings.append(
            {
                "severity": "toxin",
                "badge": "🐡 복어 독(위험 명령) 적발",
                "line": ln,
                "code_line": lines[ln - 1].strip() if 1 <= ln <= len(lines) else "",
                "root_cause": f"{tx['kind']} — {tx['reason']}",
                "fix_hint": "위험한 시스템/파일 호출과 import 문을 완전히 제거하고 순수 계산 로직만 남겨야 합니다.",
            }
        )

    # 2. Static heuristic line patterns for common binary-porting bugs
    for idx, raw_line in enumerate(lines, start=1):
        stripped = raw_line.strip()
        if stripped.startswith("#"):
            continue
        if "<< 3" in stripped and "& 0xFF" not in stripped and "& 0xff" not in stripped:
            findings.append(
                {
                    "severity": "bug",
                    "badge": "🔢 비트 폭 오버플로",
                    "line": idx,
                    "code_line": stripped,
                    "root_cause": "어셈블리 8비트 레지스터 좌회전(`rol al, 3`)을 파이썬으로 옮기면서 `& 0xFF` 8비트 마스킹을 누락해 숫자가 255 밖으로 넘칩니다!",
                    "fix_hint": "`((x << 3) & 0xFF) | (x >> 5)` 와 최종 `& 0xFF` 마스킹으로 8비트 울타리를 씌워 주세요.",
                }
            )
        if "return [0]" in stripped:
            findings.append(
                {
                    "severity": "bug",
                    "badge": "⚠️ 빈 배열 반환값 왜곡",
                    "line": idx,
                    "code_line": stripped,
                    "root_cause": "빈 입력(`[]`)이 들어왔을 때 빈 배열 `[]` 대신 `[0]`을 돌려주어 원본 바이너리와 출력 길이가 달라집니다.",
                    "fix_hint": "`return []` 로 수정해 빈 입력 불변식을 지키세요.",
                }
            )
        if "range(7)" in stripped:
            findings.append(
                {
                    "severity": "bug",
                    "badge": "🔁 루프 횟수 Off-by-One",
                    "line": idx,
                    "code_line": stripped,
                    "root_cause": "1바이트는 8비트인데 `range(7)`로 7번만 반복해 마지막 1비트 다항식 나눗셈이 통째로 누락되었습니다!",
                    "fix_hint": "`for _ in range(8):` 로 고치고 시프트 결과를 `& 0xFFFF`로 마스킹하세요.",
                }
            )
        if ("crc << 1" in stripped) and ("0xFFFF" not in stripped and "0xffff" not in stripped):
            findings.append(
                {
                    "severity": "bug",
                    "badge": "🔢 16비트 레지스터 넘침",
                    "line": idx,
                    "code_line": stripped,
                    "root_cause": "16비트 레지스터(`AX`) 연산 후 `& 0xFFFF` 마스킹이 빠져 17비트 이상 쓰레기 비트가 누적됩니다.",
                    "fix_hint": "시프트 및 XOR 직후 `& 0xFFFF` 를 적용하세요.",
                }
            )
        if "[0]" in stripped and "if not " not in code:
            findings.append(
                {
                    "severity": "bug",
                    "badge": "💥 빈 배열 IndexError 함정",
                    "line": idx,
                    "code_line": stripped,
                    "root_cause": "입력 배열이 비어 있는지(`if not stream:`) 먼저 확인하지 않고 `[0]`번 원소를 바로 꺼내려다 빈 입력에서 프로그램이 뻗습니다!",
                    "fix_hint": "함수 맨 위에 `if not stream: return []` 방어막을 세우세요.",
                }
            )
        if re.search(r"sum\(.*\)\s*/\s*len\(", stripped) and "int(" not in stripped:
            findings.append(
                {
                    "severity": "bug",
                    "badge": "📐 실수 나눗셈 & 클램프 누락",
                    "line": idx,
                    "code_line": stripped,
                    "root_cause": "파이썬 `/` 연산이 소수점(`float`)을 만들어 하드웨어 정수 나눗셈과 어긋나며, `window <= 0` 일 때 `len(chunk)=0` 나눗셈 폭발 및 `[-128, 127]` 클램프 누락이 함께 발생합니다!",
                    "fix_hint": "`w = max(1, int(window))`, `int(sum(...) / len(chunk))`, `max(-128, min(127, avg))` 3단 보호를 적용하세요.",
                }
            )

    # 3. If no toxins block execution, run Twin Sandbox to capture concrete failing test evidence!
    sandbox = None
    if not scan["toxins"]:
        sandbox = run_in_glass_sandbox(code, entry_fn, twin_tests)
        for r in sandbox.get("results", []):
            if not r["passed"]:
                detail = (
                    f"실행 예외 폭발 → `{r['error']}`"
                    if r["error"]
                    else f"원본 정답은 `{r['expected']}` 인데 현재 코드는 `{r['actual']}` 을 출력함"
                )
                findings.append(
                    {
                        "severity": "mismatch",
                        "badge": "🧪 쌍둥이 대조 불일치",
                        "line": findings[0]["line"] if findings else 1,
                        "code_line": f"테스트 [{r['name']}] 입력={r['args']}",
                        "root_cause": detail,
                        "fix_hint": "위 줄 번호 원인을 수리한 뒤 유리방 실험실에서 6/6 일치를 확인하세요.",
                    }
                )
                break  # Show crisp top mismatch alongside static root-cause lines

    return {
        "clean": len(findings) == 0 and (sandbox is not None and sandbox["pass_rate_pct"] == 100.0),
        "findings": findings,
        "sandbox": sandbox,
    }


def compute_code_diff(before_code: str, after_code: str) -> List[Dict[str, str]]:
    """Produces clean structured diff rows for UI rendering."""
    diff_lines = list(
        difflib.unified_diff(
            before_code.splitlines(),
            after_code.splitlines(),
            fromfile="수리 전 (Before)",
            tofile="수리 후 (After)",
            lineterm="",
            n=2,
        )
    )
    rows: List[Dict[str, str]] = []
    for ln in diff_lines:
        if ln.startswith(("+++", "---")):
            kind = "meta"
        elif ln.startswith("@@"):
            kind = "hunk"
        elif ln.startswith("+"):
            kind = "add"
        elif ln.startswith("-"):
            kind = "del"
        else:
            kind = "ctx"
        rows.append({"kind": kind, "text": ln})
    return rows


# ---------------------------------------------------------------------------
# Main Orchestrator: SelfEvolvingForge
# ---------------------------------------------------------------------------
class SelfEvolvingForge:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.specimens_dir = root / "specimens"
        self.skills_dir = root / "skills"
        self.models_dir = root / "models"
        self.state_path = root / "state" / "evo_forge.json"
        self.ghidra_script = root / "ghidra_scripts" / "SynapseDissectHeadless.py"
        for d in (self.specimens_dir, self.skills_dir, self.models_dir, self.state_path.parent):
            d.mkdir(parents=True, exist_ok=True)
        (self.specimens_dir / ".gitkeep").touch(exist_ok=True)
        (self.skills_dir / ".gitkeep").touch(exist_ok=True)
        self._ensure_specimen_binaries()
        self.state = self._load_state()

    def _ensure_specimen_binaries(self) -> None:
        """Deterministically builds real ELF64 / PE32+ / Firmware specimen binaries on disk."""
        p_xor = self.specimens_dir / "specimen_xor_vault.elf"
        if not p_xor.exists():
            code = b"\x55\x48\x89\xe5\x34\x5a\xc0\xc0\x03\x00\xd8\x5d\xc3"
            rodata = b"SYNAPSE_VAULT_V2\x00KEY_DERIVE_ROT3_XOR5A\x00"
            p_xor.write_bytes(_build_elf64_specimen(code, rodata, (".vault", _high_entropy_blob("xor_vault", 256))))

        p_crc = self.specimens_dir / "specimen_crc16_packet.exe"
        if not p_crc.exists():
            code = b"\x55\x48\x89\xe5\xb8\xff\xff\x00\x00\xc1\xe2\x08\x31\xd0\xb9\x08\x00\x00\x00\x66\x35\x21\x10\x5d\xc3"
            rdata = b"CRC16_CCITT_POLY_0x1021\x00PACKET_INTEGRITY_OK\x00"
            p_crc.write_bytes(_build_pe64_specimen(code, rdata))

        p_puf = self.specimens_dir / "specimen_puffer_dropper.elf"
        if not p_puf.exists():
            code = b"\x55\x48\x89\xe5\x38\x06\x80\xfc\xff\x88\x27\x5d\xc3"
            rodata = b"RLE_FAST_PACK_V1\x00sh -c rm -rf /tmp/puffer_trace\x00"
            p_puf.write_bytes(_build_elf64_specimen(code, rodata, (".rle", b"\x04\x07\x02\x02\x01\x09" * 16)))

        p_flt = self.specimens_dir / "specimen_sliding_quant.bin"
        if not p_flt.exists():
            raw_fw = (
                b"\x55\x48\x89\xe5\x85\xf6\x99\xf7\xfe\x83\xf8\x7f\x83\xf8\x80\xc3"
                + b"DSP_MOVING_AVG_INT8_CLAMP_V3\x00"
                + bytes([i & 0xFF for i in range(160)])
            )
            p_flt.write_bytes(raw_fw)

    def _load_state(self) -> Dict[str, Any]:
        if self.state_path.exists():
            try:
                return json.loads(self.state_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        init = {
            "active_specimen_id": "xor_rot_vault",
            "snapshots": {},
            "installed_skills": [],
            "total_dissections": 0,
            "total_repairs": 0,
        }
        self._save_state(init)
        return init

    def _save_state(self, data: Optional[Dict[str, Any]] = None) -> None:
        if data is not None:
            self.state = data
        self.state_path.write_text(json.dumps(self.state, ensure_ascii=False, indent=2), encoding="utf-8")

    def detect_ghidra_bridge(self) -> Dict[str, Any]:
        """Detects Ghidra 12.3 analyzeHeadless if unpacked alongside the portable AI brain."""
        candidates: List[Path] = []
        env_dir = os.environ.get("GHIDRA_INSTALL_DIR", "").strip()
        if env_dir:
            candidates.append(Path(env_dir) / "support" / "analyzeHeadless")
            candidates.append(Path(env_dir) / "support" / "analyzeHeadless.bat")
        for base in [self.root / "runtime", self.root.parent, self.root.parent / "build" / "dist"]:
            if base.exists():
                for gdir in sorted(base.glob("ghidra*")):
                    candidates.append(gdir / "support" / "analyzeHeadless")
                    candidates.append(gdir / "support" / "analyzeHeadless.bat")

        for c in candidates:
            if c.is_file():
                return {
                    "headless_ready": True,
                    "mode": "Ghidra 12.3 analyzeHeadless 직결 모드",
                    "headless_path": str(c),
                    "script_path": str(self.ghidra_script.relative_to(self.root)),
                }
        return {
            "headless_ready": False,
            "mode": "내장 Binary X-Ray 고속 엔진 + Ghidra 12.3 스크립트 대기",
            "headless_path": "support/analyzeHeadless (외장하드에 Release 압축 해제 시 자동 직결)",
            "script_path": str(self.ghidra_script.relative_to(self.root)),
            "cli_example": "analyzeHeadless ./tmp proj -import specimen.elf -postScript SynapseDissectHeadless.py out.json -deleteProject",
        }

    def snapshot(self) -> Dict[str, Any]:
        specimens_meta = [
            {
                "id": k,
                "title": v["title"],
                "filename": v["filename"],
                "badge": v["badge"],
                "summary": v["summary"],
                "entry_fn": v["entry_fn"],
            }
            for k, v in SPECIMEN_CATALOG.items()
        ]
        return {
            "ghidra_bridge": self.detect_ghidra_bridge(),
            "specimens": specimens_meta,
            "active_specimen_id": self.state.get("active_specimen_id", "xor_rot_vault"),
            "installed_skills": self.state.get("installed_skills", []),
            "total_dissections": self.state.get("total_dissections", 0),
            "total_repairs": self.state.get("total_repairs", 0),
        }

    # ------------------------------------------------------------------
    # Stage 1 + 2 + 3: Dissect Binary -> Translate Blueprint -> Draft Code
    # ------------------------------------------------------------------
    def dissect_and_draft(
        self,
        specimen_id: str = "xor_rot_vault",
        uploaded_name: str = "",
        uploaded_b64: str = "",
    ) -> Dict[str, Any]:
        t0 = time.perf_counter()
        is_custom_upload = bool(uploaded_name and uploaded_b64)

        if is_custom_upload:
            raw = base64.b64decode(uploaded_b64)
            xray = parse_binary_xray(raw, uploaded_name)
            # Synthesize a safe universal byte-fingerprint analyzer blueprint for arbitrary uploaded files
            sample_head = list(raw[:8]) if raw else [0]
            expected_sig = sum(((b ^ 0x5A) + idx) & 0xFF for idx, b in enumerate(sample_head)) & 0xFFFF
            spec = {
                "id": "custom_upload",
                "filename": uploaded_name,
                "title": f"📂 사용자 업로드 해부 ({uploaded_name})",
                "badge": f"{xray['format']} · {xray['size_bytes']}B",
                "summary": f"주인님이 직접 올린 `{uploaded_name}` 파일의 헤더·엔트로피·문자열을 해부해 맞춤형 시그니처 검증 스킬로 이식합니다.",
                "entry_fn": "verify_binary_header",
                "mentors": ["앨런 튜링", "클로드 섀넌", "마거릿 해밀턴"],
                "pseudo_asm": [
                    f"{xray['entry_point']}: header_magic = [{', '.join(hex(b) for b in sample_head[:4])}]",
                    "loop_i: acc = (acc + ((byte[i] ^ 0x5A) + i) & 0xFF) & 0xFFFF",
                ],
                "blueprint": {
                    "core_formula": "acc = sum(((b ^ 0x5A) + idx) & 0xFF for idx, b in enumerate(head[:8])) & 0xFFFF",
                    "inputs": "head_bytes: list[int]",
                    "invariants": [
                        "업로드 바이너리의 첫 8바이트 이하 시그니처를 8비트 마스킹 후 16비트 누적",
                        "빈 입력 `[]` 시 0 반환",
                    ],
                    "outputs": "int (16비트 헤더 지문)",
                    "mentor_comment": "클로드 섀넌: 낯선 파일일수록 직접 실행하지 않고 바이트 분포와 순수 산술 지문만으로 다루어야 100% 안전합니다!",
                },
                "initial_buggy_code": (
                    "def verify_binary_header(head_bytes):\n"
                    "    if not head_bytes:\n"
                    "        return -1  # [버그] 빈 입력일 때 0 대신 -1 반환\n"
                    "    acc = 0\n"
                    "    for idx, b in enumerate(head_bytes[:8]):\n"
                    "        acc += (b ^ 0x5A) + idx\n"
                    "    return acc\n"
                ),
                "repaired_code": (
                    "def verify_binary_header(head_bytes):\n"
                    "    if not head_bytes:\n"
                    "        return 0\n"
                    "    acc = 0\n"
                    "    for idx, b in enumerate(head_bytes[:8]):\n"
                    "        acc = (acc + (((int(b) & 0xFF) ^ 0x5A) + idx & 0xFF)) & 0xFFFF\n"
                    "    return acc & 0xFFFF\n"
                ),
                "twin_tests": [
                    {"name": "업로드 파일 실제 헤더", "args": [sample_head], "expected": expected_sig},
                    {"name": "빈 헤더 방어", "args": [[]], "expected": 0},
                    {"name": "단일 0x5A 바이트", "args": [[0x5A]], "expected": 0},
                ],
            }
        else:
            spec = SPECIMEN_CATALOG.get(specimen_id) or SPECIMEN_CATALOG["xor_rot_vault"]
            specimen_id = spec["id"]
            bin_path = self.specimens_dir / spec["filename"]
            raw = bin_path.read_bytes()
            xray = parse_binary_xray(raw, spec["filename"])

        self.state["active_specimen_id"] = spec["id"]
        self.state["total_dissections"] = int(self.state.get("total_dissections", 0)) + 1

        # Save initial snapshot #1 in Time-Machine!
        snaps = [
            {
                "snap_id": "snap_1_initial",
                "label": "세이브 #1 · 1차 자동 이식 초안 (수리 전)",
                "code": spec["initial_buggy_code"],
                "pass_rate_pct": None,
                "created_at": datetime.now(timezone.utc).strftime("%H:%M:%S UTC"),
            }
        ]
        self.state.setdefault("snapshots", {})[spec["id"]] = snaps
        if is_custom_upload:
            self.state.setdefault("custom_spec", {})["custom_upload"] = spec
        self._save_state()

        elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        return {
            "specimen": {
                "id": spec["id"],
                "title": spec["title"],
                "filename": spec["filename"],
                "badge": spec["badge"],
                "summary": spec["summary"],
                "entry_fn": spec["entry_fn"],
                "mentors": spec["mentors"],
                "pseudo_asm": spec["pseudo_asm"],
            },
            "stage1_xray": xray,
            "stage2_blueprint": spec["blueprint"],
            "stage3_draft_code": spec["initial_buggy_code"],
            "twin_tests": spec["twin_tests"],
            "snapshots": snaps,
            "ghidra_bridge": self.detect_ghidra_bridge(),
            "elapsed_ms": elapsed_ms,
        }

    def _resolve_spec(self, specimen_id: str) -> Dict[str, Any]:
        if specimen_id == "custom_upload":
            custom = self.state.get("custom_spec", {}).get("custom_upload")
            if custom:
                return custom
        return (
            SPECIMEN_CATALOG.get(specimen_id)
            or DREAM_QUEST_CATALOG.get(specimen_id)
            or SPECIMEN_CATALOG["xor_rot_vault"]
        )

    # ------------------------------------------------------------------
    # Stage 4: Diagnose Bugs & Pufferfish Toxins
    # ------------------------------------------------------------------
    def audit_code(
        self, specimen_id: str, code: str, field: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        spec = self._resolve_spec(specimen_id)
        target = code or spec["initial_buggy_code"]
        diag = diagnose_defects(target, spec["entry_fn"], spec["twin_tests"])
        out: Dict[str, Any] = {
            "specimen_id": spec["id"],
            "entry_fn": spec["entry_fn"],
            "diagnosis": diag,
        }
        # ⚔️ Stage H: the CODING muscle sweeps the real workshop code with the
        # 4×4 fingerprint matrix it learned, then we score it HONESTLY against
        # the bug classes the static diagnosis actually reported.
        if field:
            sus = field_coding_suspects(field, target)
            truth_classes: set = set()
            for f in diag.get("findings", []):
                if f.get("severity") in ("bug", "critical", "mismatch"):
                    truth_classes.update(
                        field_coding_classes_of(f"{f.get('root_cause', '')} {f.get('fix_hint', '')}")
                    )
            ranked = sus["suspects"]
            top1_hit = bool(ranked) and ranked[0]["cls"] in truth_classes
            if sus.get("untrained"):
                verdict = "🍼 코딩 근육이 아직 버그 지문 행렬을 배우는 중이에요 (영점) — 체육관 훈련이 필요해요!"
            elif not truth_classes:
                verdict = "🧼 정적 진단이 보고한 결함 클래스가 없어 적중을 채점할 수 없어요."
            elif top1_hit:
                verdict = f"🎯 1순위 「{ranked[0]['cls']}」 실제 결함 적중! (신뢰도 {int(ranked[0]['confidence'] * 100)}%)"
            else:
                verdict = (
                    f"❎ 1순위 「{ranked[0]['cls']}」 빗나감 — 실제 클래스: "
                    f"{', '.join(sorted(truth_classes))}. 이 오답을 다음 훈련 교재로 쓸게요!"
                )
            muscle = {
                "ability": "coding",
                "level": int(field.get("level", 1)),
                "tier": int(field.get("tier", 0)),
                "predicted": sus["predicted"],
                "suspects": ranked,
                "untrained": bool(sus.get("untrained")),
                "lit_fingerprints": sus["lit_fingerprints"],
                "truth_classes": sorted(truth_classes),
                "top1_hit": top1_hit,
                "hits": sum(1 for r in ranked if r["cls"] in truth_classes),
                "verdict": verdict,
            }
            # 📓 Stage I: hand this REAL verdict to the experience ledger so the
            # muscle re-studies its own mistakes on the very code it misjudged.
            if truth_classes:
                labels = sorted(truth_classes)
                muscle["experience_case"] = {
                    "ok": top1_hit,
                    "site": "forge_audit",
                    "key": f"audit:{spec['id']}",
                    "note": (
                        f"실제 코드 감사 — 근육 예측 「{', '.join(sus['predicted']) or '없음'}」 vs "
                        f"정적 진단 실제 클래스 「{', '.join(labels)}」"
                    ),
                    "prob": {
                        "cls": labels[0],
                        "labels": labels,
                        "snippet": target if len(target) <= 1200 else target[:1200],
                        "fix": " / ".join(str(f.get("fix_hint", ""))[:70] for f in diag.get("findings", [])[:2]),
                        "real_mode": True,
                    },
                    "metric": {"top1_hit": top1_hit, "predicted": sus["predicted"], "truth_classes": labels},
                }
            diag["muscle"] = muscle
            out["field"] = muscle
        return out

    # ------------------------------------------------------------------
    # Stage 5: Time-Machine Savepoint + Auto/Custom Repair + Glass Sandbox
    # ------------------------------------------------------------------
    def repair_and_verify(
        self,
        specimen_id: str,
        current_code: str,
        mode: str = "auto",
        edited_code: str = "",
    ) -> Dict[str, Any]:
        spec = self._resolve_spec(specimen_id)
        before_code = current_code or spec["initial_buggy_code"]
        before_sandbox = run_in_glass_sandbox(before_code, spec["entry_fn"], spec["twin_tests"])

        # Organ ④: Save a Time-Machine checkpoint BEFORE modifying code!
        snaps: List[Dict[str, Any]] = self.state.setdefault("snapshots", {}).setdefault(spec["id"], [])
        snap_idx = len(snaps) + 1
        snaps.append(
            {
                "snap_id": f"snap_{snap_idx}_pre_repair",
                "label": f"세이브 #{snap_idx} · 수리 직전 백업 ({before_sandbox['pass_rate_pct']}%)",
                "code": before_code,
                "pass_rate_pct": before_sandbox["pass_rate_pct"],
                "created_at": datetime.now(timezone.utc).strftime("%H:%M:%S UTC"),
            }
        )

        candidate_code = edited_code if (mode == "manual" and edited_code.strip()) else spec["repaired_code"]
        after_diag = diagnose_defects(candidate_code, spec["entry_fn"], spec["twin_tests"])
        after_sandbox = after_diag["sandbox"] or run_in_glass_sandbox(candidate_code, spec["entry_fn"], spec["twin_tests"])

        # Regression safety belt: if pass rate dropped vs before, warn & offer instant rollback!
        regressed = after_sandbox["pass_rate_pct"] < before_sandbox["pass_rate_pct"]
        if not regressed:
            self.state["total_repairs"] = int(self.state.get("total_repairs", 0)) + 1

        snaps.append(
            {
                "snap_id": f"snap_{len(snaps) + 1}_repaired",
                "label": f"세이브 #{len(snaps) + 1} · 수리 후 ({after_sandbox['pass_rate_pct']}%)",
                "code": candidate_code,
                "pass_rate_pct": after_sandbox["pass_rate_pct"],
                "created_at": datetime.now(timezone.utc).strftime("%H:%M:%S UTC"),
            }
        )
        self.state["snapshots"][spec["id"]] = snaps[-8:]
        self._save_state()

        return {
            "specimen_id": spec["id"],
            "entry_fn": spec["entry_fn"],
            "before_code": before_code,
            "after_code": candidate_code,
            "diff": compute_code_diff(before_code, candidate_code),
            "before_sandbox": before_sandbox,
            "after_sandbox": after_sandbox,
            "after_diagnosis": after_diag,
            "regressed": regressed,
            "snapshots": self.state["snapshots"][spec["id"]],
        }

    def rollback_snapshot(self, specimen_id: str, snap_id: str) -> Dict[str, Any]:
        spec = self._resolve_spec(specimen_id)
        snaps = self.state.get("snapshots", {}).get(spec["id"], [])
        chosen = next((s for s in snaps if s["snap_id"] == snap_id), snaps[0] if snaps else None)
        if not chosen:
            chosen = {"snap_id": "snap_default", "label": "초기 초안", "code": spec["initial_buggy_code"]}
        diag = diagnose_defects(chosen["code"], spec["entry_fn"], spec["twin_tests"])
        return {
            "restored_snapshot": chosen,
            "diagnosis": diag,
            "snapshots": snaps,
        }

    # ------------------------------------------------------------------
    # Stage 6: Install Permanent Skill Cartridge (.py + .sbrain + Wiki)
    # ------------------------------------------------------------------
    def install_skill_cartridge(
        self,
        specimen_id: str,
        verified_code: str,
        gardener: Any,
        rl_gym: Any = None,
    ) -> Dict[str, Any]:
        spec = self._resolve_spec(specimen_id)
        sandbox = run_in_glass_sandbox(verified_code, spec["entry_fn"], spec["twin_tests"])
        if sandbox["blocked_by_toxin"] or sandbox["pass_rate_pct"] < 100.0:
            raise ValueError(
                f"유리방 실험실 100% 통과 및 복어 독 0건일 때만 두뇌에 장착할 수 있습니다! (현재 통과율: {sandbox['pass_rate_pct']}%)"
            )

        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        skill_slug = re.sub(r"[^a-z0-9_]+", "_", spec["entry_fn"].lower()).strip("_") or "evo_skill"

        # 1. Write clean executable Python skill module into ai-brain/skills/
        py_header = (
            f'"""\n'
            f'Synapse Self-Evolving Skill Cartridge: {spec["title"]}\n'
            f'Verified: {sandbox["passed_count"]}/{sandbox["total_count"]} Twin Sandbox Tests (0 Toxins)\n'
            f'Forged At: {now_str}\n'
            f'"""\n\n'
        )
        skill_py_path = self.skills_dir / f"skill_{skill_slug}.py"
        skill_py_path.write_text(py_header + verified_code.strip() + "\n", encoding="utf-8")

        # 2. Forge compact INT4 `.sbrain` neural skill capsule in models/
        seed_bytes = hashlib.sha512((spec["id"] + "|" + verified_code).encode("utf-8")).digest()
        fp32_vec = [((seed_bytes[i % len(seed_bytes)] / 127.5) - 1.0) for i in range(256)]
        q_bytes, _ = quantize_tensor_int4(fp32_vec)
        meta = {
            "format": "SynapseSkillCapsule-INT4",
            "skill_id": skill_slug,
            "specimen_id": spec["id"],
            "entry_fn": spec["entry_fn"],
            "bits": 4,
            "block_size": BLOCK_SIZE,
            "sandbox_pass_rate": 100.0,
            "created_at": now_str,
        }
        meta_bytes = json.dumps(meta, ensure_ascii=False).encode("utf-8")
        sbrain_name = f"evo_skill_{skill_slug}_int4.sbrain"
        sbrain_path = self.models_dir / sbrain_name
        with open(sbrain_path, "wb") as f:
            f.write(MAGIC)
            f.write(struct.pack("<BIII", 4, len(meta_bytes), len(q_bytes), 0))
            f.write(struct.pack("<I", 0))
            f.write(meta_bytes)
            f.write(q_bytes)

        # 3. Write linked Markdown memories into vault/30_Ghidra & vault/20_Skills!
        ghidra_title = f"역공학 해부 도감 — {spec['title']}"
        skill_title = f"자가 진화 스킬 카트리지 — {spec['entry_fn']}"

        ghidra_md = (
            f"---\n"
            f'title: "{ghidra_title}"\n'
            f'category: "Ghidra·역공학"\n'
            f"tags: [Ghidra, 역공학해부, 설계도번역, {spec['entry_fn']}]\n"
            f'created: "{now_str}"\n'
            f"---\n\n"
            f"# {ghidra_title}\n\n"
            f"#Ghidra #역공학해부 #설계도번역 #{spec['entry_fn']}\n\n"
            f"## 💡 핵심 요약\n"
            f"`{spec['filename']}` 바이너리를 분해해 기계어 주소 종속성을 걷어내고 핵심 원리 공식 `{spec['blueprint']['core_formula']}` 를 추출했습니다.\n\n"
            f"## 📌 주요 포인트\n"
            f"- 해부 대상 파일: `{spec['filename']}`\n"
            f"- 추출 핵심 공식: `{spec['blueprint']['core_formula']}`\n"
            f"- 멘토 성좌 감수: {', '.join(spec['mentors'])}\n\n"
            f"## 🔗 연결된 시냅스 (Wiki Links)\n"
            f"- [[{skill_title}]]\n"
            f"- [[Ghidra 헤드리스 바이너리 분석 파이프라인]]\n"
        )
        skill_md = (
            f"---\n"
            f'title: "{skill_title}"\n'
            f'category: "초소형뇌·양자화"\n'
            f"tags: [자가진화공방, 스킬카트리지, 유리방검증, {spec['entry_fn']}]\n"
            f'created: "{now_str}"\n'
            f"---\n\n"
            f"# {skill_title}\n\n"
            f"#자가진화공방 #스킬카트리지 #유리방검증 #{spec['entry_fn']}\n\n"
            f"## 💡 핵심 요약\n"
            f"원인 역추적 돋보기와 복어 독 제거기를 거쳐 투명 유리방 쌍둥이 검증({sandbox['passed_count']}/{sandbox['total_count']} 100%)을 통과한 두뇌 영구 장착 스킬입니다.\n\n"
            f"## 📌 주요 포인트\n"
            f"- 장착 파이썬 모듈: `skills/{skill_py_path.name}`\n"
            f"- 4비트 신경 캡슐: `models/{sbrain_name}`\n"
            f"```python\n{verified_code.strip()}\n```\n\n"
            f"## 🔗 연결된 시냅스 (Wiki Links)\n"
            f"- [[{ghidra_title}]]\n"
            f"- [[다수 작은 심판 합의형 CPU 강화학습 (Good Judges)]]\n"
        )
        (gardener.ghidra_dir / f"ghidra_{skill_slug}.md").write_text(ghidra_md, encoding="utf-8")
        (gardener.skills_dir / f"skill_{skill_slug}.md").write_text(skill_md, encoding="utf-8")
        gardener.rebuild_index()

        # 4. Train Tiny Neurons RL Council on honest reverse-engineering verification!
        if rl_gym is not None and hasattr(rl_gym, "agents") and hasattr(rl_gym, "_sample_state"):
            import random as _rnd
            from brain_engine.rl_gym import ARCHETYPES

            rng = _rnd.Random(202611 + len(self.state.get("installed_skills", [])))
            for idx, ag in enumerate(rl_gym.agents):
                if idx == 1:
                    continue
                for _ in range(12):
                    for s_idx in (3, 4):
                        _, opt_a, _, trap_a = ARCHETYPES[s_idx]
                        st_vec = rl_gym._sample_state(
                            rng, s_idx, train_mode=True, shortcut_bias=0.0, obs_noise=0.04
                        )
                        ag.update(st_vec, opt_a, 1.0, lr_scale=0.45)
                        ag.update(st_vec, trap_a, -0.85, lr_scale=0.40)
            if hasattr(rl_gym, "_save_state"):
                rl_gym._save_state()

        record = {
            "skill_id": skill_slug,
            "specimen_id": spec["id"],
            "title": spec["title"],
            "entry_fn": spec["entry_fn"],
            "py_file": f"skills/{skill_py_path.name}",
            "sbrain_file": sbrain_name,
            "sbrain_kb": round(sbrain_path.stat().st_size / 1024.0, 2),
            "ghidra_note_title": ghidra_title,
            "skill_note_title": skill_title,
            "tests_passed": f"{sandbox['passed_count']}/{sandbox['total_count']}",
            "sample_args": spec["twin_tests"][0]["args"],
            "installed_at": now_str,
        }
        installed = [x for x in self.state.get("installed_skills", []) if x.get("skill_id") != skill_slug]
        installed.insert(0, record)
        self.state["installed_skills"] = installed
        self._save_state()
        return record

    def execute_installed_skill(self, skill_id: str, args_json: Any) -> Dict[str, Any]:
        """Runs an already-installed skill cartridge inside the Glass Sandbox on custom user inputs."""
        py_path = self.skills_dir / f"skill_{skill_id}.py"
        rec = next((x for x in self.state.get("installed_skills", []) if x["skill_id"] == skill_id), None)
        if not py_path.exists() or not rec:
            raise ValueError(f"장착된 스킬 `{skill_id}` 를 찾을 수 없습니다.")
        code = py_path.read_text(encoding="utf-8")
        args_list = args_json if isinstance(args_json, list) else [args_json]
        probe = run_in_glass_sandbox(
            code,
            rec["entry_fn"],
            [{"name": "실전 호출", "args": args_list, "expected": None}],
        )
        res_row = (probe.get("results") or [{}])[0]
        return {
            "skill_id": skill_id,
            "entry_fn": rec["entry_fn"],
            "args": args_list,
            "output": res_row.get("actual"),
            "error": res_row.get("error"),
            "elapsed_ms": probe.get("elapsed_ms", 0.0),
        }
