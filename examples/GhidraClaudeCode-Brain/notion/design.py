"""
notion/design.py — 설계 (30줄, 12살 설명)
요구사항 한 줄 → 아키텍처 블록 5개로 그려주기
"""
import json
from pathlib import Path
from notion.blocks import create_block

TEMPLATE = {
    "분석기": ["수집기", "디컴파일러", "패턴탐지", "보고서", "저장소"],
    "default": ["입력", "처리", "추론", "검증", "출력"],
}

def design(requirement: str) -> dict:
    key = "분석기" if "분석" in requirement else "default"
    blocks = TEMPLATE[key]
    ids = []
    parent = None
    for b in blocks:
        r = create_block(f"{b}: {requirement}의 {b} 담당", type="text", parent=parent)
        ids.append(r.get("id", b))
        if parent is None:
            parent = r.get("id")
    return {"ok": True, "requirement": requirement, "blocks": blocks, "ids": ids, "insight": f"'{requirement}' → 5블록 설계 완료"}

if __name__ == "__main__":
    print(design("악성코드 분석기 만들어줘"))
