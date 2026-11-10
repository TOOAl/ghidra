---
title: "entry (0x140001000)"
category: "역공학·분석결과"
tags: [machine-output, analyzeHeadless, specimen_crc16_packet.exe]
kind: "code"
created: ""
---

# entry (0x140001000)

## 💡 핵심 요약
specimen_crc16_packet.exe 의 entry: 명령 9개, 니모닉 PUSH MOV SHL XOR POP RET

## 🔩 기계어 진실
  140001000:	PUSH RBP
  140001001:	MOV RBP
  140001004:	MOV EAX
  140001009:	SHL EDX
  14000100c:	XOR EAX
  14000100e:	MOV ECX
  140001013:	XOR AX
  140001017:	POP RBP
  140001018:	RET <UNSUPPORTED>
디컴파일:

uint entry(undefined8 param_1,int param_2)

{
  return CONCAT22((short)((uint)param_2 >> 8),(short)(param_2 << 8)) ^ 0xefde;
}

