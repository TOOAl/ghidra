---
title: "entry (0x00401000)"
category: "역공학·분석결과"
tags: [machine-output, analyzeHeadless, specimen_puffer_dropper.elf]
kind: "code"
created: ""
---

# entry (0x00401000)

## 💡 핵심 요약
specimen_puffer_dropper.elf 의 entry: 명령 7개, 니모닉 PUSH MOV CMP POP RET

## 🔩 기계어 진실
  00401000:	PUSH RBP
  00401001:	MOV RBP
  00401004:	CMP byte ptr [RSI]
  00401006:	CMP AH
  00401009:	MOV byte ptr [RDI]
  0040100b:	POP RBP
  0040100c:	RET <UNSUPPORTED>
디컴파일:

void processEntry entry(void)

{
  undefined1 in_AH;
  undefined1 *in_RDI;
  
  *in_RDI = in_AH;
  return;
}

