---
title: "frame_dummy (0x00100690)"
category: "역공학·분석결과"
tags: [machine-output, analyzeHeadless, globalRegVars.so]
kind: "code"
created: ""
---

# frame_dummy (0x00100690)

## 💡 핵심 요약
globalRegVars.so 의 frame_dummy: 명령 12개, 호출 2개, 니모닉 CMP JZ MOV TEST PUSH LEA CALL POP

## 🔩 기계어 진실
  00100690:	CMP qword ptr [0x00300e30]
  00100698:	JZ 0x001006c0
  0010069a:	MOV RAX
  001006a1:	TEST RAX
  001006a4:	JZ 0x001006c0
  001006a6:	PUSH RBP
  001006a7:	LEA RDI
  001006ae:	MOV RBP
  001006b1:	CALL RAX
  001006b3:	POP RBP
  001006b4:	JMP 0x00100610
  001006c0:	JMP 0x00100610
호출: _Jv_RegisterClasses register_tm_clones
참조: __JCR_END__ frame_dummy PTR__Jv_RegisterClasses_00300fe8 _Jv_RegisterClasses register_tm_clones
디컴파일:

void frame_dummy(void)

{
  if ((__JCR_END__ == 0) || (PTR__Jv_RegisterClasses_00300fe8 == (undefined *)0x0)) {
    register_tm_clones();
    return;
  }
  (*(code *)PTR__Jv_RegisterClasses_00300fe8)(&__JCR_END__);
  register_tm_clones();
  return;
}

