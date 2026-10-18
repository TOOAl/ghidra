---
name: find_c2
description: 악성코드에서 C2 서버 주소 찾는 스킬
triggers: ["C2", "통신", "서버", "command and control", "콜백"]
---

# C2 찾기 스킬

이 스킬은 "C2 주소 찾아줘" 같은 요청이 오면 활성화됨.

## 절차

1. `list_strings`에서 URL/IP/도메인 패턴 검색
   - 필터: "http", "https", "tcp://", ".com", ".net", ".io"
2. 해당 문자열을 쓰는 함수 찾기 — `get_xrefs` 로 역추적
3. 그 함수 `decompile` — 소켓 생성, DNS, 암호화 여부 확인
4. `search_memory`로 "C2 통신 함수" 과거 사례 대조
5. 보고서에 CONFIRMED(코드에서 직접 보임) / LIKELY(패턴 유사) 명시

## 예시 보고서 문장

> CONFIRMED: 0x00401200 `connect_to_c2` 함수가 "http://c2.evil.com/api" 문자열을 사용해 `WSAConnect` 호출 (증거: decompile 12번째 줄)
