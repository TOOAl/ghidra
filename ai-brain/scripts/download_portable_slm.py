#!/usr/bin/env python3
"""
외장하드 전용 양자화 초소형 모델(GGUF) 다운로드 도우미.
호스트 컴퓨터의 C드라이브/홈 폴더를 전혀 건드리지 않고,
현재 외장하드(`ai-brain/models/`) 안에 4비트/8비트 압축 두뇌 파일을 직접 내려받습니다.

사용 예시 (인터넷 되는 PC에서 최초 1회만 실행):
    python3 scripts/download_portable_slm.py --list
    python3 scripts/download_portable_slm.py --tier 0.5b-q4
    python3 scripts/download_portable_slm.py --tier 0.8b-q8
"""

from __future__ import annotations

import argparse
import sys
import urllib.request
from pathlib import Path

BRAIN_ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = BRAIN_ROOT / "models"

PORTABLE_MODELS = {
    "0.5b-q4": {
        "filename": "qwen2.5-0.5b-instruct-q4_k_m.gguf",
        "approx_mb": 398,
        "desc": "초경량 0.5B (4비트 양자화) — 어떤 구형 노트북 RAM에서도 즉시 실행",
        "url": "https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf",
    },
    "0.8b-q8": {
        "filename": "Connect-C1-0.8B-v0.1-Q8_0.gguf",
        "approx_mb": 812,
        "desc": "판단·의사결정 특화 0.8B (8비트 양자화, Connect AI C1 호환)",
        "url": "https://huggingface.co/WonseokJayJung/Connect-C1-0.8B-v0.1-GGUF/resolve/main/Connect-C1-0.8B-v0.1-Q8_0.gguf",
    },
    "1.5b-q4": {
        "filename": "qwen2.5-1.5b-instruct-q4_k_m.gguf",
        "approx_mb": 1120,
        "desc": "한국어·요약 균형형 1.5B (4비트 양자화) — 일반 노트북 추천",
        "url": "https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf",
    },
    "3b-q4": {
        "filename": "qwen2.5-3b-instruct-q4_k_m.gguf",
        "approx_mb": 2100,
        "desc": "고성능 3B (4비트 양자화) — 코드·역공학 설명용 두뇌",
        "url": "https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF/resolve/main/qwen2.5-3b-instruct-q4_k_m.gguf",
    },
}


def download_file(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".gguf.part")
    print(f"⬇️ 다운로드 시작: {url}")
    print(f"📂 저장 위치 (외장하드): {dest}")
    req = urllib.request.Request(url, headers={"User-Agent": "portable-ai-brain/1.0"})
    with urllib.request.urlopen(req) as resp, open(tmp, "wb") as out:
        total = int(resp.headers.get("Content-Length", "0") or "0")
        done = 0
        while True:
            chunk = resp.read(1024 * 256)
            if not chunk:
                break
            out.write(chunk)
            done += len(chunk)
            if total > 0:
                pct = done * 100 // total
                sys.stdout.write(f"\r   진행률: {done // (1024 * 1024)} MB / {total // (1024 * 1024)} MB ({pct}%)")
                sys.stdout.flush()
    print("\n✅ 다운로드 완료!")
    tmp.replace(dest)


def main() -> None:
    parser = argparse.ArgumentParser(description="외장하드 포터블 GGUF 두뇌 다운로더")
    parser.add_argument("--list", action="store_true", help="다운로드 가능한 초경량 양자화 모델 목록 보기")
    parser.add_argument("--tier", choices=list(PORTABLE_MODELS.keys()), help="다운로드할 모델 단계 선택")
    args = parser.parse_args()

    if args.list or not args.tier:
        print("=== 📦 외장하드 서식용 초경량 양자화 모델(GGUF) 카탈로그 ===")
        for key, info in PORTABLE_MODELS.items():
            print(f"  [{key:7s}] 약 {info['approx_mb']:4d} MB | {info['desc']}")
        print("\n실행 예시: python3 scripts/download_portable_slm.py --tier 0.5b-q4")
        return

    chosen = PORTABLE_MODELS[args.tier]
    download_file(chosen["url"], MODELS_DIR / chosen["filename"])
    print("💡 이제 llama.cpp 포터블 실행기(llama-server)를 runtime/ 폴더에 두거나 Ollama/LM Studio에서 이 파일을 열면 즉시 연결됩니다!")


if __name__ == "__main__":
    main()
