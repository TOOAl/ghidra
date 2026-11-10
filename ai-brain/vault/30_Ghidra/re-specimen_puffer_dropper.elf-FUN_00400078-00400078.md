---
title: "FUN_00400078 (0x00400078)"
category: "역공학·분석결과"
tags: [machine-output, analyzeHeadless, specimen_puffer_dropper.elf]
kind: "code"
created: ""
---

# FUN_00400078 (0x00400078)

## 💡 핵심 요약
specimen_puffer_dropper.elf 의 FUN_00400078: 명령 7개, 니모닉 PUSH MOV CMP POP RET

## 🔩 기계어 진실
  00400078:	PUSH RBP
  00400079:	MOV RBP
  0040007c:	CMP byte ptr [RSI]
  0040007e:	CMP AH
  00400081:	MOV byte ptr [RDI]
  00400083:	POP RBP
  00400084:	RET <UNSUPPORTED>
디컴파일:

void FUN_00400078(undefined1 *param_1)

{
  undefined1 in_AH;
  
  *param_1 = in_AH;
  return;
}

