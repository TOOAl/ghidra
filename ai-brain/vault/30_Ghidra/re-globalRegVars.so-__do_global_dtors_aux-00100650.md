---
title: "__do_global_dtors_aux (0x00100650)"
category: "역공학·분석결과"
tags: [machine-output, analyzeHeadless, globalRegVars.so]
kind: "code"
created: ""
---

# __do_global_dtors_aux (0x00100650)

## 💡 핵심 요약
globalRegVars.so 의 __do_global_dtors_aux: 명령 12개, 호출 2개, 니모닉 CMP JNZ PUSH MOV JZ LEA CALL POP

## 🔩 기계어 진실
  00100650:	CMP byte ptr [0x00301018]
  00100657:	JNZ 0x00100680
  00100659:	CMP qword ptr [0x00300ff8]
  00100661:	PUSH RBP
  00100662:	MOV RBP
  00100665:	JZ 0x00100673
  00100667:	LEA RDI
  0010066e:	CALL 0x001005d8
  00100673:	CALL 0x001005e0
  00100678:	POP RBP
  00100679:	MOV byte ptr [0x00301018]
  00100680:	RET <UNSUPPORTED>
호출: __cxa_finalize deregister_tm_clones
참조: completed.6355 __do_global_dtors_aux PTR___cxa_finalize_00300ff8 __dso_handle __cxa_finalize deregister_tm_clones
디컴파일:

void __do_global_dtors_aux(undefined8 param_1,undefined8 param_2,undefined8 param_3)

{
  undefined8 extraout_RDX;
  
  if (completed_6355 == '\0') {
    if (PTR___cxa_finalize_00300ff8 != (undefined *)0x0) {
      __cxa_finalize(&__dso_handle);
      param_3 = extraout_RDX;
    }
    deregister_tm_clones(param_3,0x100678);
    completed_6355 = '\x01';
  }
  return;
}

