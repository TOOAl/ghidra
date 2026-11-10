---
title: "deregister_tm_clones (0x001005e0)"
category: "역공학·분석결과"
tags: [machine-output, analyzeHeadless, globalRegVars.so]
kind: "code"
created: ""
---

# deregister_tm_clones (0x001005e0)

## 💡 핵심 요약
globalRegVars.so 의 deregister_tm_clones: 명령 14개, 호출 1개, 니모닉 LEA PUSH SUB MOV CMP JA POP RET

## 🔩 기계어 진실
  001005e0:	LEA RAX
  001005e7:	LEA RDI
  001005ee:	PUSH RBP
  001005ef:	SUB RAX
  001005f2:	MOV RBP
  001005f5:	CMP RAX
  001005f9:	JA 0x001005fd
  001005fb:	POP RBP
  001005fc:	RET <UNSUPPORTED>
  001005fd:	MOV RAX
  00100604:	TEST RAX
  00100607:	JZ 0x001005fb
  00100609:	POP RBP
  0010060a:	JMP RAX
호출: _ITM_deregisterTMCloneTable
참조: DAT_0030101f completed.6355 deregister_tm_clones PTR__ITM_deregisterTMCloneTable_00300fd0 _ITM_deregisterTMCloneTable
디컴파일:

/* WARNING: Removing unreachable block (ram,0x001005fd) */
/* WARNING: Removing unreachable block (ram,0x00100609) */

void processEntry deregister_tm_clones(void)

{
  return;
}

