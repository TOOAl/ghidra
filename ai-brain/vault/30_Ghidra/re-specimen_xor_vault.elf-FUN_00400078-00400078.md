---
title: "FUN_00400078 (0x00400078)"
category: "역공학·분석결과"
tags: [machine-output, analyzeHeadless, specimen_xor_vault.elf]
kind: "code"
created: ""
---

# FUN_00400078 (0x00400078)

## 💡 핵심 요약
specimen_xor_vault.elf 의 FUN_00400078: 명령 7개, 니모닉 PUSH MOV XOR ROL ADD POP RET

## 🔩 기계어 진실
  00400078:	PUSH RBP
  00400079:	MOV RBP
  0040007c:	XOR AL
  0040007e:	ROL AL
  00400081:	ADD AL
  00400083:	POP RBP
  00400084:	RET <UNSUPPORTED>
디컴파일:

char FUN_00400078(void)

{
  byte in_AL;
  char unaff_BL;
  
  return ((in_AL ^ 0x5a) << 3 | (in_AL ^ 0x5a) >> 5) + unaff_BL;
}

