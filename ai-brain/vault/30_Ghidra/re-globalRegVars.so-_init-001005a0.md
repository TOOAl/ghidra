---
title: "_init (0x001005a0)"
category: "역공학·분석결과"
tags: [machine-output, analyzeHeadless, globalRegVars.so]
kind: "code"
created: ""
---

# _init (0x001005a0)

## 💡 핵심 요약
globalRegVars.so 의 _init: 명령 7개, 호출 1개, 니모닉 SUB MOV TEST JZ CALL ADD RET

## 🔩 기계어 진실
  001005a0:	SUB RSP
  001005a4:	MOV RAX
  001005ab:	TEST RAX
  001005ae:	JZ 0x001005b5
  001005b0:	CALL 0x001005d0
  001005b5:	ADD RSP
  001005b9:	RET <UNSUPPORTED>
호출: __gmon_start__
참조: PTR___gmon_start___00300fd8 __gmon_start__ _init
디컴파일:

void _init(void)

{
  if (PTR___gmon_start___00300fd8 != (undefined *)0x0) {
    __gmon_start__();
  }
  return;
}

