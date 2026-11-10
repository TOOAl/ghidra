"""
Host PC hardware & external-drive habitat sensor.
Computes real-time workspace comfort ('환경 상태') for Synapsemong using
ONLY Python 3 standard library.
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


DONOR_BLUEPRINTS: List[Dict[str, Any]] = [
    {
        "id": "donor-qwen-0.8b",
        "name": "Qwen3.5-0.8B 해부 틀",
        "params": "0.8B (24층 · GQA)",
        "fp16_mb": 1620,
        "our_int8_mb": 812,
        "our_int4_mb": 460,
        "ram_needed_gb": 1.1,
        "takeaway": "그룹 쿼리 어텐션(GQA) 비율이 뛰어나 우리 독자 판단 두뇌의 기본 골격으로 최적",
    },
    {
        "id": "donor-gemma4-e2b",
        "name": "Gemma 4 E2B 해부 틀",
        "params": "2.0B (효율형 임베딩)",
        "fp16_mb": 4200,
        "our_int8_mb": 2150,
        "our_int4_mb": 1240,
        "ram_needed_gb": 2.1,
        "takeaway": "다국어·한국어 사전 구조와 로컬 어텐션 창 설계를 참고하기 좋은 중형 골격",
    },
    {
        "id": "custom-synapse-seed",
        "name": "Synapse-Core 독자 초경량 틀",
        "params": "Custom (내 위키 맞춤형)",
        "fp16_mb": 640,
        "our_int8_mb": 325,
        "our_int4_mb": 185,
        "ram_needed_gb": 0.5,
        "takeaway": "불필요한 잡학 상식을 덜어내고 내 위키·강화학습·역공학 시냅스만 남긴 순수 우리 두뇌",
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
                        info[key] = int(val_parts[0])
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
        return {"type": "Apple Metal 통합메모리", "mode": "metal"}
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
                return {"type": f"NVIDIA {gpu_name}", "mode": "cuda"}
        except Exception:
            pass
    return {"type": "순수 CPU 모드 (무GPU 동작)", "mode": "cpu"}


def _evaluate_environment(
    total_ram: float, avail_ram: float, cores: int, drive_free_gb: float, accel_mode: str
) -> Dict[str, Any]:
    ram_score = min(45, int(avail_ram * 12))
    core_score = min(25, cores * 5)
    disk_score = min(20, int(drive_free_gb * 1.5))
    accel_bonus = 10 if accel_mode in ("cuda", "metal") else 5
    score = max(15, min(100, ram_score + core_score + disk_score + accel_bonus))

    ram_free_pct = round((avail_ram / max(0.1, total_ram)) * 100)

    if avail_ram >= 2.5 and drive_free_gb >= 2.0:
        grade = "optimal"
        label = "쾌적 · 연구 최적"
        hot_slot = "핫슬롯 2.0B"
        note = (
            f"한 덩어리에 갇히지 않고 외장하드 성좌 모듈(.sbrain)을 필요할 때마다 소환하는 '무한 확장 두뇌' 구조예요! "
            f"현재 PC 여유 메모리({avail_ram}GB)를 동시 작업창({hot_slot})으로 쓰며 한계 없이 성장합니다."
        )
        max_custom_tier = "∞ 무제한 확장"
    elif avail_ram >= 1.2:
        grade = "balanced"
        label = "보통 · 경량 쾌속"
        hot_slot = "핫슬롯 0.8B"
        note = (
            f"외장하드 성좌 모듈 스왑 덕분에 메모리({avail_ram}GB)와 상관없이 두뇌 전체 크기는 무한 확장돼요! "
            f"한 번에 {hot_slot} 단위로 가볍게 불러와 쾌속 구동합니다."
        )
        max_custom_tier = "∞ 무제한 확장"
    else:
        grade = "tight"
        label = "절전 · 스왑 구동"
        hot_slot = "마이크로 슬롯"
        note = (
            f"현재 PC 여유 메모리({avail_ram}GB)는 좁지만 걱정 마세요! "
            f"외장하드 모듈 스왑으로 필요한 성좌만 마이크로 슬롯에 소환해 한계 없이 작동합니다."
        )
        max_custom_tier = "∞ 무제한 확장"

    return {
        "score": score,
        "grade": grade,
        "label": label,
        "ram_free_pct": ram_free_pct,
        "note": note,
        "max_custom_tier": max_custom_tier,
        "hot_slot_sub": f"성좌 모듈 스왑 ({hot_slot})",
    }


def probe_host(brain_root: Path) -> Dict[str, Any]:
    mem = _detect_memory_gb()
    avail = mem["available_gb"]
    total = mem["total_gb"]
    cores = os.cpu_count() or 1
    accel = _detect_accelerator()
    try:
        usage = shutil.disk_usage(brain_root)
        drive_total_gb = round(usage.total / (1024**3), 1)
        drive_free_gb = round(usage.free / (1024**3), 1)
    except Exception:
        drive_total_gb, drive_free_gb = 0.0, 0.0

    env_status = _evaluate_environment(total, avail, cores, drive_free_gb, accel["mode"])

    blueprints: List[Dict[str, Any]] = []
    for bp in DONOR_BLUEPRINTS:
        need = bp["ram_needed_gb"]
        saved_pct = round((1.0 - bp["our_int4_mb"] / bp["fp16_mb"]) * 100)
        if avail >= need * 1.2:
            fit, fit_label = "optimal", "쾌적 구동"
        elif avail >= need * 0.85:
            fit, fit_label = "tight", "절약 구동"
        else:
            fit, fit_label = "heavy", "메모리 부족"
        blueprints.append({**bp, "saved_pct": saved_pct, "fit": fit, "fit_label": fit_label})

    host_fingerprint = f"{platform.system()}-{platform.machine()}-{cores}c"
    return {
        "hostname": socket.gethostname(),
        "os": f"{platform.system()} {platform.release()}",
        "arch": platform.machine(),
        "cpu_name": _detect_cpu_name(),
        "cpu_cores": cores,
        "ram_total_gb": total,
        "ram_available_gb": avail,
        "accelerator": accel["type"],
        "accel_mode": accel["mode"],
        "habitat_path": str(brain_root),
        "drive_total_gb": drive_total_gb,
        "drive_free_gb": drive_free_gb,
        "host_fingerprint": host_fingerprint,
        "environment": env_status,
        "blueprints": blueprints,
    }
