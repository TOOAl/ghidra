---
title: "entry (0x00401000)"
category: "역공학·분석결과"
tags: [machine-output, analyzeHeadless, specimen_xor_vault.elf]
kind: "code"
created: ""
---

# entry (0x00401000)

## 💡 핵심 요약
specimen_xor_vault.elf 의 entry: 명령 7개, 니모닉 PUSH MOV XOR ROL ADD POP RET

## 🔩 기계어 진실
  00401000:	PUSH RBP
  00401001:	MOV RBP
  00401004:	XOR AL
  00401006:	ROL AL
  00401009:	ADD AL
  0040100b:	POP RBP
  0040100c:	RET <UNSUPPORTED>
디컴파일:

char processEntry entry(void)

{
  byte in_AL;
  char in_BL;
  
  return ((in_AL ^ 0x5a) << 3 | (in_AL ^ 0x5a) >> 5) + in_BL;
}

