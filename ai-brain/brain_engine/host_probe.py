"""
Host PC hardware & external-drive habitat sensor.
Uses ONLY Python 3 standard library so it works on Windows, macOS, and Linux
the instant an external drive is plugged in.
"""

from __future__ import annotations

import ctypes
import os
import platform
import shutil
import socket
import subprocess
from pathlib import Path
from typing import Any, Dict, List


SLM_CATALOG: List[Dict[str, Any]] = [
    {
        "id": "qwen-0.5b-q4",
        "name": "Qwen 0.5B Instruct (Q4_K_M · 4비트)",
        "params_b": 0.5,
        "bits": 4,
        "fp16_mb": 1000,
        "file_mb": 395,
        "ram_needed_gb": 0.9,
        "role": "초저사양 구형 노트북 · 초고속 분류기(정원사)",
        "speed_hint": "구형 CPU에서도 초당 25~45 토큰",
    },
    {
        "id": "qwen-0.8b-q8",
        "name": "Qwen3.5 / C1급 0.8B (Q8_0 · 8비트)",
        "params_b": 0.8,
        "bits": 8,
        "fp16_mb": 1620,
        "file_mb": 812,
        "ram_needed_gb": 1.5,
        "role": "판단·의사결정 특화 두뇌 (정확도 99.5% 보존)",
        "speed_hint": "일반 노트북 CPU에서 초당 18~35 토큰",
    },
    {
        "id": "gemma4-e2b-q4",
        "name": "Gemma 4 E2B (Q4_K_M · 4비트)",
        "params_b": 2.0,
        "bits": 4,
        "fp16_mb": 4200,
        "file_mb": 1480,
        "ram_needed_gb": 2.4,
        "role": "제2의 두뇌 주력 대화·요약 (가성비 최고 추천)",
        "speed_hint": "일반 노트북 RAM 8GB에서 쾌적 구동",
    },
    {
        "id": "gemma4-e4b-q4",
        "name": "Gemma 4 E4B (Q4_K_M · 4비트)",
        "params_b": 4.0,
        "bits": 4,
        "fp16_mb": 8200,
        "file_mb": 2750,
        "ram_needed_gb": 4.0,
        "role": "역공학(Ghidra) 코드 해석 · 심층 추론 두뇌",
        "speed_hint": "RAM 16GB 이상 또는 GPU/맥북에서 강력 추천",
    },
]


def _detect_memory_gb() -> Dict[str, float]:
    system = platform.system()
    try:
        if system == "Linux" and Path("/proc/meminfo").exists():
            info: Dict[str, int] = {}
            for line in Path("/proc/meminfo").read_text(encoding="utf-8", errors="ignore").splitlines():
                parts = line.split(":")
                if len(parts) == 2:
                    key = parts[0].strip()
                    val_parts = parts[1].strip().split()
                    if val_parts and val_parts[0].isdigit():
                        info[key] = int(val_parts[0])  # kB
            total_kb = info.get("MemTotal", 0)
            avail_kb = info.get("MemAvailable", info.get("MemFree", 0))
            if total_kb > 0:
                return {
                    "total_gb": round(total_kb / (1024 * 1024), 2),
                    "available_gb": round(avail_kb / (1024 * 1024), 2),
                }
        elif system == "Darwin":
            total_bytes = int(
                subprocess.check_output(["sysctl", "-n", "hw.memsize"], timeout=2).decode().strip()
            )
            vm_out = subprocess.check_output(["vm_stat"], timeout=2).decode()
            page_size = 4096
            for line in vm_out.splitlines():
                if "page size of" in line:
                    for token in line.split():
                        if token.isdigit():
                            page_size = int(token)
                            break
            free_pages = 0
            for line in vm_out.splitlines():
                if any(k in line for k in ("Pages free", "Pages inactive", "Pages speculative")):
                    num = line.split(":")[-1].strip().rstrip(".")
                    if num.isdigit():
                        free_pages += int(num)
            return {
                "total_gb": round(total_bytes / (1024**3), 2),
                "available_gb": round((free_pages * page_size) / (1024**3), 2),
            }
        elif system == "Windows":
            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            stat = MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(stat)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))  # type: ignore[attr-defined]
            return {
                "total_gb": round(stat.ullTotalPhys / (1024**3), 2),
                "available_gb": round(stat.ullAvailPhys / (1024**3), 2),
            }
    except Exception:
        pass
    return {"total_gb": 4.0, "available_gb": 2.0}


def _detect_cpu_name() -> str:
    system = platform.system()
    try:
        if system == "Linux" and Path("/proc/cpuinfo").exists():
            for line in Path("/proc/cpuinfo").read_text(encoding="utf-8", errors="ignore").splitlines():
                if line.lower().startswith("model name"):
                    return line.split(":", 1)[1].strip()
        elif system == "Darwin":
            return subprocess.check_output(
                ["sysctl", "-n", "machdep.cpu.brand_string"], timeout=2
            ).decode().strip()
    except Exception:
        pass
    return platform.processor() or platform.machine() or "Generic CPU"


def _detect_accelerator() -> Dict[str, str]:
    system = platform.system()
    machine = platform.machine().lower()
    if system == "Darwin" and ("arm" in machine or "aarch64" in machine):
        return {"type": "Apple Metal (Unified Memory)", "mode": "metal"}
    if shutil.which("nvidia-smi"):
        try:
            gpu_name = (
                subprocess.check_output(
                    ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                    timeout=2,
                    stderr=subprocess.DEVNULL,
                )
                .decode()
                .splitlines()[0]
                .strip()
            )
            if gpu_name:
                return {"type": f"NVIDIA GPU ({gpu_name})", "mode": "cuda"}
        except Exception:
            pass
    return {"type": "CPU 전용 모드 (데이터센터 GPU 불필요!)", "mode": "cpu"}


def probe_host(brain_root: Path) -> Dict[str, Any]:
    mem = _detect_memory_gb()
    avail = mem["available_gb"]
    accel = _detect_accelerator()
    try:
        usage = shutil.disk_usage(brain_root)
        drive_total_gb = round(usage.total / (1024**3), 1)
        drive_free_gb = round(usage.free / (1024**3), 1)
    except Exception:
        drive_total_gb, drive_free_gb = 0.0, 0.0

    # Evaluate each quantized SLM against live free RAM
    recommendations: List[Dict[str, Any]] = []
    best_model = SLM_CATALOG[0]
    for item in SLM_CATALOG:
        need = item["ram_needed_gb"]
        saved_pct = round((1.0 - item["file_mb"] / item["fp16_mb"]) * 100)
        if avail >= need * 1.25:
            fit = "optimal"
            fit_label = "쾌적 실행"
            best_model = item
        elif avail >= need * 0.9:
            fit = "tight"
            fit_label = "실행 가능 (여유 적음)"
        else:
            fit = "heavy"
            fit_label = "현재 여유 RAM 부족"
        recommendations.append(
            {
                **item,
                "saved_pct": saved_pct,
                "fit": fit,
                "fit_label": fit_label,
            }
        )

    host_fingerprint = f"{platform.system()}-{platform.machine()}-{os.cpu_count() or 1}c"
    return {
        "hostname": socket.gethostname(),
        "os": f"{platform.system()} {platform.release()}",
        "arch": platform.machine(),
        "cpu_name": _detect_cpu_name(),
        "cpu_cores": os.cpu_count() or 1,
        "ram_total_gb": mem["total_gb"],
        "ram_available_gb": avail,
        "accelerator": accel["type"],
        "accel_mode": accel["mode"],
        "habitat_path": str(brain_root),
        "drive_total_gb": drive_total_gb,
        "drive_free_gb": drive_free_gb,
        "host_fingerprint": host_fingerprint,
        "best_slm": best_model,
        "slm_matrix": recommendations,
    }
