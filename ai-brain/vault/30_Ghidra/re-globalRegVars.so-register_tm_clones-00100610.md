---
title: "register_tm_clones (0x00100610)"
category: "역공학·분석결과"
tags: [machine-output, analyzeHeadless, globalRegVars.so]
kind: "code"
created: ""
---

# register_tm_clones (0x00100610)

## 💡 핵심 요약
globalRegVars.so 의 register_tm_clones: 명령 16개, 니모닉 LEA PUSH SUB MOV SAR SHR ADD JNZ

## 🔩 기계어 진실
  00100610:	LEA RAX
  00100617:	LEA RDI
  0010061e:	PUSH RBP
  0010061f:	SUB RAX
  00100622:	MOV RBP
  00100625:	SAR RAX
  00100629:	MOV RDX
  0010062c:	SHR RDX
  00100630:	ADD RAX
  00100633:	SAR RAX
  00100636:	JNZ 0x0010063a
  00100638:	POP RBP
  00100639:	RET <UNSUPPORTED>
  0010063a:	MOV RDX
  00100641:	TEST RDX
  00100644:	JZ 0x00100638
참조: completed.6355 register_tm_clones PTR__ITM_registerTMCloneTable_00300ff0
디컴파일:

/* WARNING: Removing unreachable block (ram,0x0010063a) */
/* WARNING: Removing unreachable block (ram,0x00100646) */

void register_tm_clones(void)

{
  return;
}

