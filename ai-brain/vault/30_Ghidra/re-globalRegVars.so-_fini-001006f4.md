---
title: "_fini (0x001006f4)"
category: "역공학·분석결과"
tags: [machine-output, analyzeHeadless, globalRegVars.so]
kind: "code"
created: ""
---

# _fini (0x001006f4)

## 💡 핵심 요약
globalRegVars.so 의 _fini: 명령 3개, 니모닉 SUB ADD RET

## 🔩 기계어 진실
  001006f4:	SUB RSP
  001006f8:	ADD RSP
  001006fc:	RET <UNSUPPORTED>
디컴파일:

void _fini(void)

{
  return;
}

