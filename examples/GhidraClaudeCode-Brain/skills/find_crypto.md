---
name: find_crypto
description: 암호화 함수, 키, 상수를 찾는 스킬
triggers: ["crypto", "암호", "AES", "RSA", "키", "encrypt", "decrypt", "해시", "hash"]
---

# 암호화 찾기 스킬

악성코드는 C2 통신 전 암호화를 쓰는 경우가 많다. 상수와 호출 패턴으로 찾는다.

## 탐지 (Detection)

1. **상수 시그니처** — `search_bytes`로 암호 상수 검색:
   - AES S-box: `63 7C 77 7B F2 6B 6F C5 30 01 67 2B FE D7 AB 76`
   - SHA256 K: `428A2F98 71374491 B5C0FBCF E9B5DBA5` (리틀엔디안)
   - ChaCha20: `61707865 3320646E 79622D32 6B206574` ("expand 32-byte k")

2. **API 시그니처** — `list_imports`에서 암호 라이브러리:
   - Windows: `CryptEncrypt`, `BCryptEncrypt`, `CryptGenKey`
   - OpenSSL: `AES_encrypt`, `EVP_EncryptInit_ex`
   - 커스텀: `get_xrefs`로 루프+ XOR 패턴 추적

3. **엔트로피** — `get_bytes`로 섹션 엔트로피 측정, 7.5 이상이면 암호화된 데이터 의심

## 절차 (Workflow)

1. `search_bytes`로 상수 시그니처 스캔 → 주소 확보
2. 해당 주소를 쓰는 함수 `get_xrefs` → `decompile` 로 암호 루프 확인
3. `list_strings`에서 `AES`, `key`, `encrypt` 같은 힌트 검색
4. `search_memory`로 과거 암호 함수 기억 대조 (예: 2024 DarkGate AES)
5. `rename_function`으로 `decrypt_c2_config`, `aes_expand_key` 같이 이름 복구
6. `set_comment`로 키 길이, 모드 명시: `CONFIRMED: AES-256-CBC, key at 0x00403000`

## 도구

- `search_bytes` (상수 시그니처)
- `list_imports` (암호 API)
- `get_bytes` (엔트로피/키 덤프)
- `decompile` (루프 구조)
- `get_xrefs` (호출 관계)
- `rename_function` / `set_comment` (결과 기록)
- `search_memory` (과거 암호 사례)

## 라벨

- CONFIRMED: AES S-box + CryptEncrypt 호출 둘 다 증거 있음
- LIKELY: S-box만 있고 호출은 커스텀 루프
- POSSIBLE: 엔트로피만 높고 상수 없음

## 예시 보고서 문장

> CONFIRMED: 0x00401500 `FUN_00401500`은 AES-256 — `search_bytes`에서 S-box 발견, `decompile`에서 14라운드 루프, `list_imports`에서 `BCryptEncrypt` 호출. 키는 0x00403000에서 `get_bytes(0x00403000, 32)`로 추출 가능. → `decrypt_c2_config`로 rename 완료.
